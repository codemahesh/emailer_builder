"""
sync.py
=======
FastAPI router for Google Sheets sync operations.

Endpoints
---------
POST /campaigns/{campaign_id}/sync/full   – enqueue a full sync job
GET  /campaigns/{campaign_id}/sync/status – return latest sync status
GET  /campaigns/{campaign_id}/products    – list products for a campaign
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.product import Product
from app.models.sync_job import SyncJob, SyncJobStatus
from app.models.user import User
from app.models.sheet_version import SheetVersion, SheetVersionRow
from app.modules.sheet_verifier import verify_sheet
from app.schemas.sync import (
    ProductRead,
    SheetPreviewResponse,
    SheetVersionRead,
    SyncJobResponse,
    SyncStatusResponse,
    VerifyRequest,
    VerifyResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_REDIS_KEY_PREFIX = "sync_status:"


def _status_key(campaign_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}{campaign_id}"


async def _get_campaign_or_404(
    campaign_id: uuid.UUID,
    user: User,
    session: AsyncSession,
) -> Campaign:
    result = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.owner_id == user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    return campaign


@router.post("/{campaign_id}/sheet/verify", response_model=VerifyResponse)
async def verify_sheet_connection(
    campaign_id: uuid.UUID,
    body: VerifyRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
    request: Request = None,  # type: ignore[assignment]
) -> VerifyResponse:
    """
    Read-only: verify that a Google Sheet URL is accessible and has the required columns.

    Returns the verify result without writing anything to the database.
    Fires only on explicit click — not on input change or blur (C1).
    """
    await _get_campaign_or_404(campaign_id, user, session)

    import json as _json
    from app.config import settings

    credentials_json: dict = {}
    if settings.google_sheets_credentials_json:
        try:
            credentials_json = _json.loads(settings.google_sheets_credentials_json)
        except Exception:
            logger.warning("verify_sheet_connection: could not parse GOOGLE_SHEETS_CREDENTIALS_JSON")

    try:
        result = verify_sheet(body.sheet_url, credentials_json)
    except Exception as exc:
        logger.warning("verify_sheet_connection: unexpected error for campaign %s: %s", campaign_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Google Sheets. Please try again.",
        ) from exc

    return VerifyResponse(**result)


@router.post("/{campaign_id}/sync/full", response_model=SyncJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_full_sync(
    campaign_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> SyncJobResponse:
    """
    Enqueue a full Google Sheets sync job for the given campaign.

    Returns the job ID and initial status ("queued").  The actual sync
    runs asynchronously in the ARQ worker process.
    """
    campaign = await _get_campaign_or_404(campaign_id, user, session)

    if not campaign.sheet_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campaign has no Google Sheet URL configured.",
        )

    # Create a SyncJob row so we have a persistent audit trail
    job = SyncJob(
        campaign_id=campaign_id,
        job_type="full",
        status=SyncJobStatus.queued,
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)

    job_id = str(job.id)

    # Enqueue via ARQ pool (stored in app.state.arq_pool during startup)
    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is not None:
        try:
            import json as _json
            from app.config import settings

            credentials_json: dict = {}
            if settings.google_sheets_credentials_json:
                try:
                    credentials_json = _json.loads(settings.google_sheets_credentials_json)
                except Exception:
                    logger.warning("start_full_sync: could not parse GOOGLE_SHEETS_CREDENTIALS_JSON")

            await arq_pool.enqueue_job(
                "run_full_sync",
                campaign_id=str(campaign_id),
                sheet_url=campaign.sheet_url,
                credentials_json=credentials_json,
                _job_id=job_id,
            )
            logger.info("start_full_sync: enqueued job %s for campaign %s", job_id, campaign_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "start_full_sync: ARQ enqueue failed (%s) — job created but not queued", exc
            )
    else:
        logger.warning(
            "start_full_sync: arq_pool not available — job %s created but not enqueued", job_id
        )

    return SyncJobResponse(job_id=job_id, status="queued")


@router.get("/{campaign_id}/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    campaign_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> SyncStatusResponse:
    """
    Return the latest sync status for a campaign.

    Checks the Redis progress key first; falls back to the latest SyncJob
    row in the database if Redis is unavailable or the key has expired.
    """
    await _get_campaign_or_404(campaign_id, user, session)

    cid = str(campaign_id)

    # ── Try Redis first ────────────────────────────────────────────────────────
    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        try:
            raw = await redis.get(_status_key(cid))
            if raw:
                data = json.loads(raw)
                # Normalise status names from worker ("done" -> "completed", "error" -> "failed")
                raw_status = data.get("status", "idle")
                normalised = _normalise_status(raw_status)
                return SyncStatusResponse(
                    status=normalised,
                    total=data.get("total", 0),
                    processed=data.get("imported", data.get("progress", 0)),
                    failed=data.get("failed", 0),
                    last_synced=data.get("last_synced"),
                    error_message=data.get("message") if normalised in ("failed", "partial") else None,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_sync_status: Redis read failed (%s) — falling back to DB", exc)

    # ── Fallback: latest SyncJob row ───────────────────────────────────────────
    result = await session.execute(
        select(SyncJob)
        .where(SyncJob.campaign_id == campaign_id)
        .order_by(SyncJob.created_at.desc())
        .limit(1)
    )
    job: Optional[SyncJob] = result.scalar_one_or_none()

    if job is None:
        return SyncStatusResponse(status="idle", total=0, processed=0, failed=0)

    last_synced: Optional[str] = None
    if job.completed_at is not None:
        last_synced = job.completed_at.isoformat()

    return SyncStatusResponse(
        status=job.status.value,
        total=job.total_products,
        processed=job.processed_products,
        failed=job.failed_products,
        last_synced=last_synced,
        error_message=job.error_message,
    )


@router.get("/{campaign_id}/products", response_model=list[ProductRead])
async def list_products(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> list[Product]:
    """Return all products for a campaign, ordered by position."""
    await _get_campaign_or_404(campaign_id, user, session)

    result = await session.execute(
        Product.active()
        .where(Product.campaign_id == campaign_id)
        .order_by(Product.position.asc())
    )
    return list(result.scalars().all())


@router.post(
    "/{campaign_id}/sync/fast",
    response_model=SyncJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_fast_sync(
    campaign_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> SyncJobResponse:
    """
    Enqueue a fast sync — updates only price + UTM fields from the sheet.
    Requires at least one prior full sync to exist.
    """
    campaign = await _get_campaign_or_404(campaign_id, user, session)

    if not campaign.sheet_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campaign has no Google Sheet URL configured.",
        )

    job = SyncJob(
        campaign_id=campaign_id,
        job_type="fast",
        status=SyncJobStatus.queued,
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)

    job_id = str(job.id)

    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is not None:
        try:
            await arq_pool.enqueue_job(
                "run_fast_sync",
                campaign_id=str(campaign_id),
                job_id=job_id,
                _job_id=f"fast-{job_id}",
            )
            logger.info("start_fast_sync: enqueued job %s for campaign %s", job_id, campaign_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("start_fast_sync: ARQ enqueue failed (%s)", exc)
    else:
        logger.warning("start_fast_sync: arq_pool not available — job %s not enqueued", job_id)

    await session.commit()
    return SyncJobResponse(job_id=job_id, status="queued")


@router.get("/{campaign_id}/sheet/preview", response_model=SheetPreviewResponse)
async def get_sheet_preview(
    campaign_id: uuid.UUID,
    version: str = Query("latest"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> SheetPreviewResponse:
    """
    Return a paginated preview of the latest (or specific) sheet version snapshot.

    Data is served from ``sheet_version_rows`` — no live Sheets API call.
    Soft-deleted products are excluded by filtering on ``product.deleted_at IS NULL``.
    """
    await _get_campaign_or_404(campaign_id, user, session)

    # ── Resolve the requested version ─────────────────────────────────────────
    if version == "latest":
        sv_result = await session.execute(
            select(SheetVersion)
            .where(SheetVersion.campaign_id == campaign_id)
            .order_by(SheetVersion.version.desc())
            .limit(1)
        )
        sv: Optional[SheetVersion] = sv_result.scalar_one_or_none()
    else:
        try:
            ver_int = int(version)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="version must be 'latest' or an integer",
            )
        sv_result = await session.execute(
            select(SheetVersion).where(
                SheetVersion.campaign_id == campaign_id,
                SheetVersion.version == ver_int,
            )
        )
        sv = sv_result.scalar_one_or_none()

    if sv is None:
        return SheetPreviewResponse(
            version=0,
            fetched_at="",
            row_count=0,
            headers=[],
            rows=[],
            has_more=False,
            offset=offset,
            limit=limit,
        )

    # ── Collect active (non-soft-deleted) SKUs for filtering ──────────────────
    deleted_skus_result = await session.execute(
        select(Product.sku).where(
            Product.campaign_id == campaign_id,
            Product.deleted_at.is_not(None),
        )
    )
    deleted_skus: set[str] = {r for (r,) in deleted_skus_result.all() if r}

    # ── Fetch paginated rows ───────────────────────────────────────────────────
    all_rows_result = await session.execute(
        select(SheetVersionRow)
        .where(SheetVersionRow.version_id == sv.id)
        .order_by(SheetVersionRow.position.asc())
    )
    all_rows = all_rows_result.scalars().all()

    # Decode and filter soft-deleted SKUs
    decoded: list[dict] = []
    for row in all_rows:
        try:
            data = json.loads(row.data_json)
        except Exception:
            data = {}
        if deleted_skus and data.get("sku", "") in deleted_skus:
            continue
        decoded.append(data)

    # Derive headers from the union of all row keys, preserving a stable order
    seen_keys: list[str] = []
    seen_set: set[str] = set()
    for d in decoded:
        for k in d:
            if k not in seen_set:
                seen_keys.append(k)
                seen_set.add(k)

    page = decoded[offset: offset + limit]
    has_more = (offset + limit) < len(decoded)

    return SheetPreviewResponse(
        version=sv.version,
        fetched_at=sv.imported_at.isoformat(),
        row_count=len(decoded),
        headers=seen_keys,
        rows=page,
        has_more=has_more,
        offset=offset,
        limit=limit,
    )


@router.get("/{campaign_id}/sheet/versions", response_model=list[SheetVersionRead])
async def list_sheet_versions(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> list[SheetVersion]:
    """Return all sheet versions for a campaign, ordered newest-first."""
    await _get_campaign_or_404(campaign_id, user, session)

    result = await session.execute(
        select(SheetVersion)
        .where(SheetVersion.campaign_id == campaign_id)
        .order_by(SheetVersion.version.desc())
    )
    return list(result.scalars().all())


# ── Internal helpers ──────────────────────────────────────────────────────────

def _normalise_status(raw: str) -> str:
    """Map worker status strings to the canonical SyncStatusResponse values."""
    mapping = {
        "done": "completed",
        "error": "failed",
        "partial": "partial",
        "running": "running",
        "queued": "queued",
        "completed": "completed",
        "failed": "failed",
        "idle": "idle",
    }
    return mapping.get(raw.lower(), raw.lower())
