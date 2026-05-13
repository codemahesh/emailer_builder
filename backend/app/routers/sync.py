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
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.product import Product
from app.models.sync_job import SyncJob, SyncJobStatus
from app.models.user import User
from app.models.sheet_version import SheetVersion, SheetVersionRow
from app.modules.file_parser import UploadParseError, detect_file_type, parse_bytes
from app.modules.sheet_diff import compute_diff
from app.modules.sheet_reader import read_sheet
from app.modules.sheet_verifier import verify_sheet
from app.modules.sheet_version_store import write_version
from app.schemas.sync import (
    ImportCommitResponse,
    ImportPreflightResponse,
    ImportRequest,
    ProductRead,
    SheetPreviewResponse,
    SheetVersionRead,
    SyncJobResponse,
    SyncStatusResponse,
    UploadResponse,
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


@router.post(
    "/{campaign_id}/sheet/import",
    responses={
        200: {"model": ImportPreflightResponse},
        202: {"model": ImportCommitResponse},
    },
)
async def import_sheet(
    campaign_id: uuid.UUID,
    body: ImportRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """
    Two-phase Update List endpoint.

    phase="preflight"  — computes diff between live sheet and latest version.
                         Returns 200 ImportPreflightResponse. No DB writes.
    phase="commit"     — writes new version, upserts products, soft-deletes
                         removed SKUs, enqueues smart re-scrape.
                         Returns 202 ImportCommitResponse.
    """
    from app.models.product import Product, ProductPriority, Section
    from app.config import settings

    campaign = await _get_campaign_or_404(campaign_id, user, session)

    if not campaign.sheet_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campaign has no Google Sheet URL configured.",
        )

    # ── Load credentials ──────────────────────────────────────────────────────
    import json as _json
    credentials_json: dict = {}
    if settings.google_sheets_credentials_json:
        try:
            credentials_json = _json.loads(settings.google_sheets_credentials_json)
        except Exception:
            logger.warning("import_sheet: could not parse GOOGLE_SHEETS_CREDENTIALS_JSON")

    # ── Read live sheet ───────────────────────────────────────────────────────
    try:
        new_records = read_sheet(campaign.sheet_url, credentials_json)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not read Google Sheet: {exc}",
        ) from exc

    # ── Fetch latest version rows (old_records) ───────────────────────────────
    sv_result = await session.execute(
        select(SheetVersion)
        .where(SheetVersion.campaign_id == campaign_id)
        .order_by(SheetVersion.version.desc())
        .limit(1)
    )
    latest_sv: Optional[SheetVersion] = sv_result.scalar_one_or_none()

    old_records: list[dict] = []
    if latest_sv is not None:
        rows_result = await session.execute(
            select(SheetVersionRow)
            .where(SheetVersionRow.version_id == latest_sv.id)
            .order_by(SheetVersionRow.position.asc())
        )
        old_records = [json.loads(r.data_json) for r in rows_result.scalars().all()]

    # ── Compute diff ──────────────────────────────────────────────────────────
    diff = compute_diff(old_records, new_records)

    if body.phase == "preflight":
        has_changes = bool(diff["added"] or diff["removed"] or diff["updated"])
        return ImportPreflightResponse(
            added=len(diff["added"]),
            removed=len(diff["removed"]),
            updated=len(diff["updated"]),
            unchanged=len(diff["unchanged"]),
            rescrape_count=diff["rescrape_count"],
            has_changes=has_changes,
        )

    # ── phase == "commit" ─────────────────────────────────────────────────────

    # Write new SheetVersion (checksum dedup handles unchanged sheets)
    sv = await write_version(
        session,
        campaign_id=campaign_id,
        rows=new_records,
        source="link",
        source_ref=campaign.sheet_url,
        imported_by=user.id,
    )

    now = datetime.now(timezone.utc)
    rescrape_product_ids: list[str] = []

    # Upsert products by SKU
    all_active_result = await session.execute(
        select(Product).where(
            Product.campaign_id == campaign_id,
            Product.deleted_at.is_(None),
        )
    )
    existing_by_sku: dict[str, Product] = {
        p.sku: p for p in all_active_result.scalars().all()
    }

    # Apply removed → soft-delete
    for row in diff["removed"]:
        sku = row.get("sku", "")
        if sku in existing_by_sku:
            existing_by_sku[sku].deleted_at = now

    # Apply updated → update fields, track link changes for re-scrape
    for update in diff["updated"]:
        sku = update["sku"]
        new_row = update["new"]
        if sku in existing_by_sku:
            prod = existing_by_sku[sku]
            raw_prio = new_row.get("priority", "medium") or "medium"
            try:
                prio = ProductPriority(raw_prio.lower())
            except ValueError:
                prio = ProductPriority.medium
            prod.raw_price = new_row.get("raw_price") or None
            prod.utm_campaign = new_row.get("utm_campaign") or None
            prod.button_name = new_row.get("button_name") or None
            prod.pack_of = new_row.get("pack_of") or None
            prod.quantity = new_row.get("quantity") or None
            prod.discount = new_row.get("discount") or None
            prod.priority = prio
            if update["link_changed"]:
                prod.product_link = new_row.get("product_link", "")
                prod.scraped_name = None
                prod.scraped_image_url = None
                prod.scrape_failed = True
                rescrape_product_ids.append(str(prod.id))
            prod.updated_at = now

    # Apply added → create new products
    # Rebuild section map from existing active sections
    sec_result = await session.execute(
        select(Section).where(Section.campaign_id == campaign_id)
    )
    sections_by_title: dict[str, Section] = {
        s.title: s for s in sec_result.scalars().all()
    }
    section_pos = max((s.position for s in sections_by_title.values()), default=-1) + 1

    max_pos_result = await session.execute(
        select(Product.position)
        .where(Product.campaign_id == campaign_id)
        .order_by(Product.position.desc())
        .limit(1)
    )
    pos_row = max_pos_result.scalar_one_or_none()
    next_pos = (pos_row or 0) + 1

    for new_row in diff["added"]:
        title = new_row.get("section_title", "Default") or "Default"
        if title not in sections_by_title:
            sec = Section(campaign_id=campaign_id, title=title, position=section_pos)
            session.add(sec)
            await session.flush()
            sections_by_title[title] = sec
            section_pos += 1

        raw_prio = new_row.get("priority", "medium") or "medium"
        try:
            prio = ProductPriority(raw_prio.lower())
        except ValueError:
            prio = ProductPriority.medium

        prod = Product(
            campaign_id=campaign_id,
            section_id=sections_by_title[title].id,
            sku=new_row.get("sku", "") or "",
            product_link=new_row.get("product_link", "") or "",
            priority=prio,
            raw_price=new_row.get("raw_price") or None,
            utm_campaign=new_row.get("utm_campaign") or None,
            button_name=new_row.get("button_name") or None,
            pack_of=new_row.get("pack_of") or None,
            quantity=new_row.get("quantity") or None,
            discount=new_row.get("discount") or None,
            position=next_pos,
            scrape_failed=True,
        )
        session.add(prod)
        await session.flush()
        rescrape_product_ids.append(str(prod.id))
        next_pos += 1

    # Check for soft-deleted products being restored (SKU returning)
    all_deleted_result = await session.execute(
        select(Product).where(
            Product.campaign_id == campaign_id,
            Product.deleted_at.is_not(None),
        )
    )
    deleted_by_sku: dict[str, Product] = {
        p.sku: p for p in all_deleted_result.scalars().all()
    }
    for new_row in diff["added"]:
        sku = new_row.get("sku", "")
        if sku in deleted_by_sku:
            # Restore soft-deleted product
            prod = deleted_by_sku[sku]
            prod.deleted_at = None
            prod.product_link = new_row.get("product_link", "")
            prod.raw_price = new_row.get("raw_price") or None
            prod.scrape_failed = True
            prod.updated_at = now
            rescrape_product_ids.append(str(prod.id))

    # Create SyncJob for the re-scrape
    from app.models.sync_job import SyncJob, SyncJobStatus
    job = SyncJob(
        campaign_id=campaign_id,
        job_type="import",
        status=SyncJobStatus.queued,
        total_products=len(rescrape_product_ids),
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)
    job_id = str(job.id)

    await session.commit()

    # Enqueue smart re-scrape (only for link-changed + added products)
    if rescrape_product_ids:
        arq_pool = getattr(request.app.state, "arq_pool", None)
        if arq_pool is not None:
            try:
                await arq_pool.enqueue_job(
                    "run_import_scrape",
                    campaign_id=str(campaign_id),
                    product_ids=rescrape_product_ids,
                    job_id=job_id,
                    _job_id=f"import-{job_id}",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("import_sheet: ARQ enqueue failed (%s)", exc)

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"job_id": job_id, "status": "queued"},
    )


_MAX_UPLOAD_BYTES = 5 * 1024 * 1024   # 5 MB


@router.post("/{campaign_id}/sheet/upload", response_model=UploadResponse)
async def upload_sheet_file(
    campaign_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> UploadResponse:
    """
    Parse an uploaded .xlsx or .csv file, validate columns, write a SheetVersion
    and create/replace Products for this campaign.

    Enforces:
    - 5 MB file size cap (checked before full read)
    - Allowed MIME types / extensions only (.xlsx, .csv)
    - Max 10,000 data rows
    - Required columns: sku, product_link (alias-aware via sheet_parser)
    """
    from app.models.product import Product, ProductPriority, Section
    from app.modules.sheet_parser import CANONICAL_FIELDS

    await _get_campaign_or_404(campaign_id, user, session)

    filename = file.filename or ""
    content_type = file.content_type or ""

    # ── Detect file type (rejects unsupported extensions/mimes early) ─────────
    try:
        file_type = detect_file_type(filename, content_type)
    except UploadParseError as exc:
        return UploadResponse(ok=False, error_code=exc.error_code)

    # ── Read up to MAX+1 bytes to enforce size cap ────────────────────────────
    data = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(data) > _MAX_UPLOAD_BYTES:
        return UploadResponse(ok=False, error_code="FILE_TOO_LARGE")

    # ── Parse + validate ──────────────────────────────────────────────────────
    try:
        records = parse_bytes(data, file_type)
    except UploadParseError as exc:
        return UploadResponse(
            ok=False,
            error_code=exc.error_code,
            missing_columns=(
                [c for c in ["sku", "product_link"] if c in exc.detail]
                if exc.error_code == "MISSING_COLUMNS"
                else []
            ),
        )

    # Derive headers_found from canonical fields present in the first record
    headers_found = [k for k in (records[0].keys() if records else []) if k in CANONICAL_FIELDS]

    # ── DB: write version + upsert products ───────────────────────────────────
    try:
        from sqlalchemy import delete as sa_delete

        # Write the immutable snapshot first
        sv = await write_version(
            session,
            campaign_id=campaign_id,
            rows=records,
            source="upload",
            source_ref=filename,
            imported_by=user.id,
        )

        # Hard-delete existing products for a clean reimport
        await session.execute(
            sa_delete(Product).where(Product.campaign_id == campaign_id)
        )
        await session.execute(
            sa_delete(Section).where(Section.campaign_id == campaign_id)
        )
        await session.flush()

        # Insert products grouped by section
        sections_seen: dict[str, Section] = {}
        section_pos = 0

        for idx, record in enumerate(records):
            title = record.get("section_title", "Default") or "Default"

            if title not in sections_seen:
                sec = Section(campaign_id=campaign_id, title=title, position=section_pos)
                session.add(sec)
                await session.flush()
                sections_seen[title] = sec
                section_pos += 1

            raw_prio = record.get("priority", "medium") or "medium"
            try:
                prio = ProductPriority(raw_prio.lower())
            except ValueError:
                prio = ProductPriority.medium

            session.add(
                Product(
                    campaign_id=campaign_id,
                    section_id=sections_seen[title].id,
                    sku=record.get("sku", "") or "",
                    product_link=record.get("product_link", "") or "",
                    priority=prio,
                    raw_price=record.get("raw_price") or None,
                    utm_campaign=record.get("utm_campaign") or None,
                    button_name=record.get("button_name") or None,
                    pack_of=record.get("pack_of") or None,
                    quantity=record.get("quantity") or None,
                    discount=record.get("discount") or None,
                    position=idx,
                    scrape_failed=True,   # no scraping for upload path yet
                )
            )

        await session.commit()

    except Exception as exc:
        await session.rollback()
        logger.exception("upload_sheet_file: DB write failed for campaign %s", campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save uploaded sheet.",
        ) from exc

    return UploadResponse(
        ok=True,
        headers_found=headers_found,
        row_count=len(records),
        version_id=str(sv.id),
        imported_count=len(records),
    )


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
    "/{campaign_id}/sheet/quick-price",
    response_model=SyncJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_quick_price_update(
    campaign_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> SyncJobResponse:
    """
    Enqueue a quick price update — updates only price + UTM fields from the sheet.
    Requires at least one prior full sync to exist. Never touches images.
    """
    campaign = await _get_campaign_or_404(campaign_id, user, session)

    if not campaign.sheet_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campaign has no Google Sheet URL configured.",
        )

    job = SyncJob(
        campaign_id=campaign_id,
        job_type="quick_price",
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
                _job_id=f"quick-price-{job_id}",
            )
            logger.info("start_quick_price_update: enqueued job %s for campaign %s", job_id, campaign_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("start_quick_price_update: ARQ enqueue failed (%s)", exc)
    else:
        logger.warning("start_quick_price_update: arq_pool not available — job %s not enqueued", job_id)

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
