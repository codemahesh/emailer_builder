"""
fast_sync_worker.py
===================
ARQ worker task: fast (price-only) sync from Google Sheets for a campaign.

Task: ``run_fast_sync(ctx, campaign_id)``

Workflow
--------
1. Read Sheet via SheetReader.
2. Get existing products for campaign from DB.
3. For each sheet row matching an existing product by SKU: update only
   raw_price, formatted_price, utm_campaign, utm_stitched.
4. Do NOT touch: processed_image_url, scrape_failed, manual overrides,
   locked sections, visual brief.
5. Emit WebSocket progress events via gateway.send_progress.
6. Update SyncJob status if a job_id is provided.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from arq import ArqRedis
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_maker
from app.models.campaign import Campaign
from app.models.product import Product
from app.models.snapshot import Snapshot
from app.models.sync_job import SyncJob, SyncJobStatus
from app.modules.override_applicator import apply_text_overrides
from app.modules.sheet_reader import read_sheet
from app.ws.gateway import gateway

logger = logging.getLogger(__name__)

_REDIS_KEY_PREFIX = "fast_sync_status:"


def _status_key(campaign_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}{campaign_id}"


async def _write_status(redis: ArqRedis, campaign_id: str, payload: dict) -> None:
    """Write fast-sync progress JSON to Redis with a 1-hour TTL."""
    try:
        await redis.set(_status_key(campaign_id), json.dumps(payload), ex=3600)
    except Exception as exc:  # noqa: BLE001
        logger.warning("_write_status: Redis write failed (%s)", exc)


async def _update_sync_job(
    session: AsyncSession,
    job_id: str,
    *,
    status: SyncJobStatus,
    total_products: int = 0,
    processed_products: int = 0,
    failed_products: int = 0,
    error_message: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    """Persist SyncJob state changes."""
    result = await session.execute(
        select(SyncJob).where(SyncJob.id == uuid.UUID(job_id))
    )
    job = result.scalar_one_or_none()
    if job is None:
        logger.warning("_update_sync_job: SyncJob %s not found", job_id)
        return
    job.status = status
    job.total_products = total_products
    job.processed_products = processed_products
    job.failed_products = failed_products
    if error_message is not None:
        job.error_message = error_message
    if started_at is not None:
        job.started_at = started_at
    if completed_at is not None:
        job.completed_at = completed_at
    await session.flush()


async def run_fast_sync(
    ctx: dict,
    campaign_id: str,
    job_id: str | None = None,
) -> dict:
    """
    ARQ task: fast sync — updates only price and UTM fields for existing products.

    Parameters
    ----------
    ctx:
        ARQ context (``ctx["redis"]`` is an ``ArqRedis`` instance).
    campaign_id:
        UUID string of the campaign to sync.
    job_id:
        Optional UUID string of the SyncJob row to update.

    Returns
    -------
    dict
        Summary of the fast sync result.
    """
    redis: ArqRedis = ctx["redis"]
    cid = str(campaign_id)
    started = datetime.now(timezone.utc)

    await _write_status(
        redis,
        cid,
        {
            "status": "running",
            "progress": 0,
            "total": 0,
            "message": "Fast sync: reading sheet…",
            "updated": 0,
            "failed": 0,
            "last_synced": None,
        },
    )

    async with async_session_maker() as session:
        if job_id:
            await _update_sync_job(
                session,
                job_id,
                status=SyncJobStatus.running,
                started_at=started,
            )
            await session.commit()

    # ── 1. Load campaign to get sheet URL ─────────────────────────────────────
    async with async_session_maker() as session:
        camp_result = await session.execute(
            select(Campaign).where(Campaign.id == uuid.UUID(cid))
        )
        campaign = camp_result.scalar_one_or_none()
        if campaign is None:
            error_msg = f"Campaign {cid} not found"
            await _write_status(
                redis,
                cid,
                {
                    "status": "error",
                    "progress": 0,
                    "total": 0,
                    "message": error_msg,
                    "updated": 0,
                    "failed": 0,
                    "last_synced": None,
                },
            )
            if job_id:
                async with async_session_maker() as err_session:
                    await _update_sync_job(
                        err_session,
                        job_id,
                        status=SyncJobStatus.failed,
                        error_message=error_msg,
                        completed_at=datetime.now(timezone.utc),
                    )
                    await err_session.commit()
            return {"campaign_id": cid, "status": "error", "error": error_msg}

        sheet_url = campaign.sheet_url

    # ── 1b. Create pre-sync snapshot ─────────────────────────────────────────
    try:
        async with async_session_maker() as snap_session:
            latest_snap_result = await snap_session.execute(
                select(Snapshot)
                .where(Snapshot.campaign_id == uuid.UUID(cid))
                .order_by(Snapshot.created_at.desc())
                .limit(1)
            )
            latest_snap = latest_snap_result.scalar_one_or_none()
            pre_sync_state = latest_snap.mjml_state_json if latest_snap else "{}"
            pre_sync_snapshot = Snapshot(
                campaign_id=uuid.UUID(cid),
                mjml_state_json=pre_sync_state,
                summary_chip="Before Fast Sync",
            )
            snap_session.add(pre_sync_snapshot)
            await snap_session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("run_fast_sync: could not create pre-sync snapshot: %s", exc)

    # ── 2. Read the sheet ─────────────────────────────────────────────────────
    try:
        import json as json_mod
        credentials_json: dict = {}
        raw_creds = settings.google_sheets_credentials_json
        if raw_creds:
            try:
                credentials_json = json_mod.loads(raw_creds)
            except Exception:  # noqa: BLE001
                credentials_json = {}

        records = read_sheet(sheet_url, credentials_json)
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_fast_sync: sheet read failed for campaign %s", cid)
        error_msg = f"Could not read sheet: {exc}"
        await _write_status(
            redis,
            cid,
            {
                "status": "error",
                "progress": 0,
                "total": 0,
                "message": error_msg,
                "updated": 0,
                "failed": 0,
                "last_synced": None,
            },
        )
        if job_id:
            async with async_session_maker() as err_session:
                await _update_sync_job(
                    err_session,
                    job_id,
                    status=SyncJobStatus.failed,
                    error_message=error_msg,
                    completed_at=datetime.now(timezone.utc),
                )
                await err_session.commit()
        return {"campaign_id": cid, "status": "error", "error": str(exc)}

    total = len(records)

    await _write_status(
        redis,
        cid,
        {
            "status": "running",
            "progress": 0,
            "total": total,
            "message": f"Fast sync: matching {total} sheet rows to existing products…",
            "updated": 0,
            "failed": 0,
            "last_synced": None,
        },
    )
    await gateway.send_progress(
        cid,
        "sync_progress",
        {
            "status": "running",
            "processed": 0,
            "total": total,
            "failed": 0,
        },
    )

    # ── 3. Build SKU → record map from sheet ──────────────────────────────────
    # Only keep the last occurrence of each SKU (sheet may have duplicates)
    sku_to_record: dict[str, dict] = {}
    for record in records:
        sku = (record.get("sku") or "").strip()
        if sku:
            sku_to_record[sku] = record

    # ── 4. Update existing products by SKU ────────────────────────────────────
    updated = 0
    failed = 0

    async with async_session_maker() as session:
        try:
            # Load existing products for this campaign
            products_result = await session.execute(
                select(Product).where(Product.campaign_id == uuid.UUID(cid))
            )
            existing_products = list(products_result.scalars().all())

            for idx, product in enumerate(existing_products):
                sku = (product.sku or "").strip()
                if not sku or sku not in sku_to_record:
                    continue

                record = sku_to_record[sku]

                # Update ONLY price and UTM fields — nothing else
                if record.get("raw_price") is not None:
                    product.raw_price = record["raw_price"]
                if record.get("formatted_price") is not None:
                    product.formatted_price = record["formatted_price"]
                if record.get("utm_campaign") is not None:
                    product.utm_campaign = record["utm_campaign"]
                if record.get("utm_stitched") is not None:
                    product.utm_stitched = record["utm_stitched"]

                session.add(product)
                updated += 1

                # Emit progress every 5 products
                if updated % 5 == 0:
                    await _write_status(
                        redis,
                        cid,
                        {
                            "status": "running",
                            "progress": updated,
                            "total": len(existing_products),
                            "message": f"Fast sync: updated {updated}/{len(existing_products)} products…",
                            "updated": updated,
                            "failed": failed,
                            "last_synced": None,
                        },
                    )
                    await gateway.send_progress(
                        cid,
                        "sync_progress",
                        {
                            "status": "running",
                            "processed": updated,
                            "total": len(existing_products),
                            "failed": failed,
                        },
                    )

            # Apply text ManualOverride values — these win over the new sheet prices
            updated_ids = [p.id for p in existing_products if (p.sku or "").strip() in sku_to_record]
            await apply_text_overrides(session, uuid.UUID(cid), updated_ids)

            # Touch campaign.updated_at
            camp_result2 = await session.execute(
                select(Campaign).where(Campaign.id == uuid.UUID(cid))
            )
            campaign_row = camp_result2.scalar_one_or_none()
            if campaign_row:
                campaign_row.updated_at = datetime.now(timezone.utc)

            if job_id:
                job_result = await session.execute(
                    select(SyncJob).where(SyncJob.id == uuid.UUID(job_id))
                )
                job_row = job_result.scalar_one_or_none()
                if job_row:
                    job_row.total_products = len(existing_products)
                    job_row.processed_products = updated
                    job_row.failed_products = failed

            await session.commit()

        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            logger.exception("run_fast_sync: DB update failed for campaign %s", cid)
            error_msg = f"Database error: {exc}"
            await _write_status(
                redis,
                cid,
                {
                    "status": "error",
                    "progress": 0,
                    "total": total,
                    "message": error_msg,
                    "updated": 0,
                    "failed": 0,
                    "last_synced": None,
                },
            )
            if job_id:
                async with async_session_maker() as err_session:
                    await _update_sync_job(
                        err_session,
                        job_id,
                        status=SyncJobStatus.failed,
                        error_message=error_msg,
                        completed_at=datetime.now(timezone.utc),
                    )
                    await err_session.commit()
            return {"campaign_id": cid, "status": "error", "error": str(exc)}

    # ── 5. Write final status ─────────────────────────────────────────────────
    last_synced = datetime.now(timezone.utc).isoformat()
    final_status = "done"
    final_status_db = SyncJobStatus.completed

    await _write_status(
        redis,
        cid,
        {
            "status": final_status,
            "progress": updated,
            "total": total,
            "message": f"Fast sync: {updated} products updated",
            "updated": updated,
            "failed": failed,
            "last_synced": last_synced,
        },
    )

    await gateway.send_progress(
        cid,
        "sync_progress",
        {
            "status": final_status,
            "processed": updated,
            "total": total,
            "failed": failed,
        },
    )

    if job_id:
        async with async_session_maker() as fin_session:
            await _update_sync_job(
                fin_session,
                job_id,
                status=final_status_db,
                total_products=total,
                processed_products=updated,
                failed_products=failed,
                completed_at=datetime.now(timezone.utc),
            )
            await fin_session.commit()

    logger.info(
        "run_fast_sync: campaign %s done — %d products updated",
        cid,
        updated,
    )

    return {
        "campaign_id": cid,
        "status": final_status,
        "updated": updated,
        "total": total,
    }


# ── ARQ WorkerSettings ────────────────────────────────────────────────────────


def _parse_redis_url(url: str) -> RedisSettings:
    """Parse redis://host:port[/db] into an ARQ RedisSettings."""
    import re

    m = re.match(r"redis://([^:/]+)(?::(\d+))?(?:/(\d+))?", url)
    if m:
        host = m.group(1) or "localhost"
        port = int(m.group(2)) if m.group(2) else 6379
        database = int(m.group(3)) if m.group(3) else 0
        return RedisSettings(host=host, port=port, database=database)
    return RedisSettings(host="localhost", port=6379)


class WorkerSettings:
    """ARQ worker configuration — run with ``arq app.workers.fast_sync_worker.WorkerSettings``."""

    functions = [run_fast_sync]
    redis_settings = _parse_redis_url(settings.redis_url)
    max_jobs = 10
    job_timeout = 300  # 5 minutes per fast sync
    keep_result = 3600  # keep results for 1 hour
