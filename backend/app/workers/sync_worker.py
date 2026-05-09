"""
sync_worker.py
==============
ARQ worker task: full Google Sheets sync for a campaign.

Task: ``run_full_sync(ctx, campaign_id, sheet_url, credentials_json)``

Workflow
--------
1. Update SyncJob status → running, write running status to Redis.
2. Read rows from Google Sheet via ``read_sheet``.
3. Delete existing Section + Product rows for this campaign.
4. Create new Section + Product rows grouped by ``section_title``.
5. Scrape each product page + run image quality gate + processing pipeline.
6. Update SyncJob: status=completed, write final status to Redis.
7. Touch ``campaign.updated_at``.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from arq import ArqRedis
from arq.connections import RedisSettings
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_maker
from app.models.campaign import Campaign
from app.models.product import Product, ProductPriority, Section
from app.models.sync_job import SyncJob, SyncJobStatus
from app.models.visual_brief import VisualBrief
from app.modules.sheet_reader import read_sheet
from app.modules.product_scraper import scrape_product
from app.modules.image_quality_gate import check_image_quality, QualityVerdict
from app.modules.image_processor import process_image, ProcessingConfig
from app.modules.image_store import image_store
from app.modules.visual_orchestrator import generate_visual_brief
from app.ws.gateway import gateway

logger = logging.getLogger(__name__)

_REDIS_KEY_PREFIX = "sync_status:"


def _status_key(campaign_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}{campaign_id}"


async def _write_status(redis: ArqRedis, campaign_id: str, payload: dict) -> None:
    """Write sync progress JSON to Redis with a 1-hour TTL."""
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


async def _get_sku_cache():
    """
    Build a SKUCache backed by the app's Redis connection, or return None if
    Redis is unavailable.

    We construct a fresh aioredis client here because the worker runs in a
    separate process and cannot access ``app.state``.
    """
    try:
        import redis.asyncio as aioredis
        from app.modules.sku_cache import SKUCache

        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await redis_client.ping()
        return SKUCache(redis_client)
    except Exception as exc:  # noqa: BLE001
        logger.warning("_get_sku_cache: cannot connect to Redis (%s), cache disabled", exc)
        return None


async def _download_image(url: str) -> bytes | None:
    """Download image bytes from a URL. Returns None on failure."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.content
            logger.debug("_download_image: HTTP %d for %s", response.status_code, url)
            return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("_download_image: failed for %s (%s)", url, exc)
        return None


async def _process_product_image(
    product: Product,
    campaign_id: str,
    sku_cache,
) -> str:
    """
    Download, quality-check, process, and cache the image for *product*.

    Returns the URL to use as ``processed_image_url``.
    Emits a WebSocket event with the outcome.

    Never raises.
    """
    pid = str(product.id)
    sku = product.sku or ""
    scraped_url = product.scraped_image_url or ""

    # ── SKU cache hit ─────────────────────────────────────────────────────────
    if sku_cache is not None and sku:
        cached_url = await sku_cache.get(sku)
        if cached_url:
            logger.debug("_process_product_image: cache hit for sku=%s", sku)
            await gateway.send_progress(
                campaign_id,
                "image_processed",
                {
                    "product_id": pid,
                    "url": cached_url,
                    "verdict": QualityVerdict.PASS.value,
                    "cached": True,
                },
            )
            return cached_url

    # ── Download ──────────────────────────────────────────────────────────────
    if not scraped_url or scraped_url == "/static/coming-soon.svg":
        await gateway.send_progress(
            campaign_id,
            "image_processed",
            {
                "product_id": pid,
                "url": "/static/coming-soon.svg",
                "verdict": QualityVerdict.FAIL.value,
                "reason": "No image URL available",
            },
        )
        return "/static/coming-soon.svg"

    image_bytes = await _download_image(scraped_url)
    if image_bytes is None:
        await gateway.send_progress(
            campaign_id,
            "image_processed",
            {
                "product_id": pid,
                "url": "/static/coming-soon.svg",
                "verdict": QualityVerdict.FAIL.value,
                "reason": "Failed to download image",
            },
        )
        return "/static/coming-soon.svg"

    # ── Quality gate ──────────────────────────────────────────────────────────
    quality = check_image_quality(image_bytes)

    if quality.verdict == QualityVerdict.FAIL:
        logger.debug(
            "_process_product_image: FAIL for product %s — %s", pid, quality.reason
        )
        await gateway.send_progress(
            campaign_id,
            "image_processed",
            {
                "product_id": pid,
                "url": "/static/coming-soon.svg",
                "verdict": QualityVerdict.FAIL.value,
                "reason": quality.reason,
            },
        )
        return "/static/coming-soon.svg"

    # ── Image processing (PASS or WARN) ───────────────────────────────────────
    upscale = quality.verdict == QualityVerdict.WARN
    proc_config = ProcessingConfig(
        background_color="#FFFFFF",
        remove_background=True,
        upscale_if_small=upscale,
        target_width=600,
        target_height=600,
    )

    try:
        processed_bytes = process_image(image_bytes, proc_config)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "_process_product_image: processing failed for %s (%s)", pid, exc
        )
        processed_bytes = image_bytes  # fall back to original

    # ── Store processed image ─────────────────────────────────────────────────
    try:
        filename = f"{sku}_processed.png" if sku else f"{pid}_processed.png"
        processed_url = await image_store.write(processed_bytes, filename)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "_process_product_image: image_store.write failed for %s (%s)", pid, exc
        )
        # Fall back to the scraped URL
        processed_url = scraped_url

    # ── Cache result ──────────────────────────────────────────────────────────
    if sku_cache is not None and sku and processed_url != scraped_url:
        await sku_cache.set(sku, processed_url)

    # ── Emit WebSocket event ──────────────────────────────────────────────────
    await gateway.send_progress(
        campaign_id,
        "image_processed",
        {
            "product_id": pid,
            "url": processed_url,
            "verdict": quality.verdict.value,
            "reason": quality.reason,
            "width": quality.width,
            "height": quality.height,
        },
    )

    return processed_url


async def _run_orchestrator(campaign_id: str) -> None:
    """
    Generate (or refresh) a VisualBrief for *campaign_id* by calling
    GPT-4o via ``generate_visual_brief``, then upsert the result into the
    ``visual_brief`` table.

    Called at the end of every full sync.  Errors are the caller's problem.
    """
    cid = str(campaign_id)

    async with async_session_maker() as session:
        # Collect section titles + product names
        sections_result = await session.execute(
            select(Section).where(Section.campaign_id == uuid.UUID(cid))
        )
        sections = sections_result.scalars().all()
        section_titles = [s.title for s in sections]

        products_result = await session.execute(
            select(Product).where(Product.campaign_id == uuid.UUID(cid))
        )
        products = products_result.scalars().all()
        product_names = [
            p.scraped_name or p.sku or "" for p in products if p.scraped_name or p.sku
        ]

    # Call GPT-4o (or get default brief if no key configured)
    brief_output = await generate_visual_brief(
        section_titles=section_titles,
        product_names=product_names,
        openai_api_key=settings.openai_api_key,
    )

    # Upsert into visual_brief (one row per campaign, unique constraint)
    async with async_session_maker() as session:
        existing_result = await session.execute(
            select(VisualBrief).where(VisualBrief.campaign_id == uuid.UUID(cid))
        )
        brief_row = existing_result.scalar_one_or_none()

        if brief_row is None:
            brief_row = VisualBrief(campaign_id=uuid.UUID(cid))
            session.add(brief_row)

        brief_row.theme_name = brief_output.theme_name
        brief_row.template_id = brief_output.template_id
        brief_row.background_color = brief_output.background_color
        brief_row.section_color = brief_output.section_color
        brief_row.accent_color = brief_output.accent_color
        brief_row.button_color = brief_output.button_color
        brief_row.product_bg_color = brief_output.product_bg_color
        brief_row.heading_font = brief_output.heading_font
        brief_row.body_font = brief_output.body_font
        brief_row.h1_size = brief_output.h1_size
        brief_row.h2_size = brief_output.h2_size
        brief_row.body_size = brief_output.body_size
        brief_row.dalle_prompt = brief_output.dalle_prompt
        brief_row.updated_at = datetime.now(timezone.utc)

        await session.commit()

    logger.info("_run_orchestrator: visual brief upserted for campaign %s", cid)


async def run_full_sync(
    ctx: dict,
    campaign_id: str,
    sheet_url: str,
    credentials_json: dict,
    job_id: str | None = None,
) -> dict:
    """
    ARQ task: full sync from Google Sheets for *campaign_id*.

    Parameters
    ----------
    ctx:
        ARQ context (``ctx["redis"]`` is an ``ArqRedis`` instance).
    campaign_id:
        UUID string of the campaign to sync.
    sheet_url:
        Google Spreadsheet URL.
    credentials_json:
        Service-account credentials dict.
    job_id:
        Optional UUID string of the SyncJob row to update.

    Returns
    -------
    dict
        Summary of the sync result.
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
            "message": "Reading sheet…",
            "imported": 0,
            "failed": 0,
            "last_synced": None,
        },
    )

    async with async_session_maker() as session:
        # Update SyncJob → running
        if job_id:
            await _update_sync_job(
                session,
                job_id,
                status=SyncJobStatus.running,
                started_at=started,
            )
            await session.commit()

    # ── 1. Read sheet ──────────────────────────────────────────────────────────
    try:
        records = read_sheet(sheet_url, credentials_json)
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_full_sync: sheet read failed for campaign %s", cid)
        error_msg = f"Could not read sheet: {exc}"
        await _write_status(
            redis,
            cid,
            {
                "status": "error",
                "progress": 0,
                "total": 0,
                "message": error_msg,
                "imported": 0,
                "failed": 0,
                "last_synced": None,
            },
        )
        if job_id:
            async with async_session_maker() as session:
                await _update_sync_job(
                    session,
                    job_id,
                    status=SyncJobStatus.failed,
                    error_message=error_msg,
                    completed_at=datetime.now(timezone.utc),
                )
                await session.commit()
        return {"campaign_id": cid, "status": "error", "error": str(exc)}

    total = len(records)
    await _write_status(
        redis,
        cid,
        {
            "status": "running",
            "progress": 0,
            "total": total,
            "message": f"Importing 0/{total} products…",
            "imported": 0,
            "failed": 0,
            "last_synced": None,
        },
    )

    # ── 2. DB writes ───────────────────────────────────────────────────────────
    imported = 0
    failed = 0
    product_ids: list[str] = []

    async with async_session_maker() as session:
        try:
            # Verify campaign exists
            camp_result = await session.execute(
                select(Campaign).where(Campaign.id == uuid.UUID(cid))
            )
            campaign = camp_result.scalar_one_or_none()
            if campaign is None:
                raise ValueError(f"Campaign {cid} not found")

            # Delete existing products and sections for a clean full sync
            await session.execute(
                delete(Product).where(Product.campaign_id == uuid.UUID(cid))
            )
            await session.execute(
                delete(Section).where(Section.campaign_id == uuid.UUID(cid))
            )
            await session.flush()

            # Group records by section title, preserving insertion order
            sections_seen: dict[str, Section] = {}
            section_position = 0

            for idx, record in enumerate(records):
                section_title = record.get("section_title", "Default") or "Default"

                # Create section row on first encounter of this title
                if section_title not in sections_seen:
                    section = Section(
                        campaign_id=uuid.UUID(cid),
                        title=section_title,
                        position=section_position,
                    )
                    session.add(section)
                    await session.flush()  # populate generated id
                    sections_seen[section_title] = section
                    section_position += 1

                current_section = sections_seen[section_title]

                # Map priority string → enum value
                raw_prio = record.get("priority", "medium") or "medium"
                try:
                    prio = ProductPriority(raw_prio.lower())
                except ValueError:
                    prio = ProductPriority.medium

                product = Product(
                    campaign_id=uuid.UUID(cid),
                    section_id=current_section.id,
                    sku=record.get("sku", "") or "",
                    product_link=record.get("product_link", "") or "",
                    priority=prio,
                    raw_price=record.get("raw_price"),
                    formatted_price=record.get("formatted_price"),
                    utm_campaign=record.get("utm_campaign"),
                    utm_stitched=record.get("utm_stitched"),
                    button_name=record.get("button_name"),
                    position=idx,
                )
                session.add(product)
                await session.flush()
                product_ids.append(str(product.id))
                imported += 1

                # Emit intermediate progress every 5 rows
                if imported % 5 == 0:
                    await _write_status(
                        redis,
                        cid,
                        {
                            "status": "running",
                            "progress": imported,
                            "total": total,
                            "message": f"Reading sheet… {imported}/{total} products",
                            "imported": imported,
                            "failed": failed,
                            "last_synced": None,
                        },
                    )

            # Touch campaign.updated_at
            campaign.updated_at = datetime.now(timezone.utc)

            # Update SyncJob totals before final commit
            if job_id:
                result_job = await session.execute(
                    select(SyncJob).where(SyncJob.id == uuid.UUID(job_id))
                )
                job_row = result_job.scalar_one_or_none()
                if job_row:
                    job_row.total_products = total
                    job_row.processed_products = imported
                    job_row.failed_products = failed

            await session.flush()
            await session.commit()

        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            logger.exception("run_full_sync: DB write failed for campaign %s", cid)
            error_msg = f"Database error: {exc}"
            await _write_status(
                redis,
                cid,
                {
                    "status": "error",
                    "progress": 0,
                    "total": total,
                    "message": error_msg,
                    "imported": 0,
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

    # ── 3. Scrape + quality gate + image processing ────────────────────────────
    sku_cache = await _get_sku_cache()
    scrape_failed_count = 0

    async with async_session_maker() as scrape_session:
        for scrape_idx, pid in enumerate(product_ids):
            try:
                # Re-fetch the product so we have the ORM object and product_link
                prod_result = await scrape_session.execute(
                    select(Product).where(Product.id == uuid.UUID(pid))
                )
                product_row = prod_result.scalar_one_or_none()
                if product_row is None:
                    continue

                # ── Scrape product page ───────────────────────────────────────
                result = await scrape_product(product_row.product_link)

                if result.success:
                    product_row.scraped_name = result.product_name
                    product_row.scraped_image_url = result.image_url
                    product_row.scrape_failed = False
                else:
                    product_row.scraped_image_url = "/static/coming-soon.svg"
                    product_row.scrape_failed = True
                    scrape_failed_count += 1
                    logger.debug(
                        "run_full_sync: scrape failed for product %s — %s",
                        pid,
                        result.failure_reason,
                    )

                await scrape_session.flush()

                # ── Image quality gate + processing pipeline ──────────────────
                processed_url = await _process_product_image(
                    product_row, cid, sku_cache
                )
                product_row.processed_image_url = processed_url
                await scrape_session.flush()

                # ── Emit overall sync progress ────────────────────────────────
                await _write_status(
                    redis,
                    cid,
                    {
                        "status": "running",
                        "progress": scrape_idx + 1,
                        "total": len(product_ids),
                        "message": f"Processing {scrape_idx + 1}/{len(product_ids)} products…",
                        "imported": imported,
                        "failed": failed,
                        "last_synced": None,
                    },
                )

                # Emit sync_progress WebSocket event
                await gateway.send_progress(
                    cid,
                    "sync_progress",
                    {
                        "status": "running",
                        "processed": scrape_idx + 1,
                        "total": len(product_ids),
                        "failed": scrape_failed_count,
                    },
                )

            except Exception:  # noqa: BLE001
                logger.warning(
                    "run_full_sync: unexpected error scraping product %s", pid, exc_info=True
                )

        try:
            await scrape_session.commit()
        except Exception:  # noqa: BLE001
            await scrape_session.rollback()
            logger.warning("run_full_sync: failed to commit scrape results")

    # ── 4. Write final status ──────────────────────────────────────────────────
    last_synced = datetime.now(timezone.utc).isoformat()
    final_status = "done" if failed == 0 else "partial"
    final_status_db = SyncJobStatus.completed if failed == 0 else SyncJobStatus.partial

    await _write_status(
        redis,
        cid,
        {
            "status": final_status,
            "progress": imported,
            "total": total,
            "message": f"{imported} of {total} imported",
            "imported": imported,
            "failed": failed,
            "last_synced": last_synced,
        },
    )

    # Emit final WebSocket event
    await gateway.send_progress(
        cid,
        "sync_progress",
        {
            "status": final_status,
            "processed": imported,
            "total": total,
            "failed": failed,
        },
    )

    # Persist final SyncJob state
    if job_id:
        async with async_session_maker() as fin_session:
            await _update_sync_job(
                fin_session,
                job_id,
                status=final_status_db,
                total_products=total,
                processed_products=imported,
                failed_products=failed,
                completed_at=datetime.now(timezone.utc),
            )
            await fin_session.commit()

    logger.info(
        "run_full_sync: campaign %s done — %d imported, %d failed",
        cid,
        imported,
        failed,
    )

    # ── 5. Auto-trigger VisualOrchestrator ────────────────────────────────────
    # Runs best-effort after every successful (or partial) full sync.
    # Errors are swallowed so they never block the sync result.
    try:
        await _run_orchestrator(cid)
    except Exception:  # noqa: BLE001
        logger.warning("run_full_sync: orchestrator failed for campaign %s", cid, exc_info=True)

    return {
        "campaign_id": cid,
        "status": final_status,
        "imported": imported,
        "failed": failed,
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
    """ARQ worker configuration — run with ``arq app.workers.sync_worker.WorkerSettings``."""

    from app.workers.fast_sync_worker import run_fast_sync
    functions = [run_full_sync, run_fast_sync]
    redis_settings = _parse_redis_url(settings.redis_url)
    max_jobs = 10
    job_timeout = 600  # 10 minutes per sync job
    keep_result = 3600  # keep results for 1 hour
