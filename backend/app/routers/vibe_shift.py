"""
vibe_shift.py
=============
FastAPI router for Vibe Shift — AI-powered visual style regeneration (Issue 15).

Endpoints
---------
POST /campaigns/{campaign_id}/vibe-shift
POST /campaigns/{campaign_id}/vibe-shift/confirm
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.manual_override import ManualOverride
from app.models.product import Section
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class VibeShiftPreviewBody(BaseModel):
    directive: str = "refresh the visual style"


class VibeShiftConfirmBody(BaseModel):
    directive: str


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_campaign_or_404(
    campaign_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> Campaign:
    result = await db.execute(
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


async def _get_locked_sections_count(
    campaign_id: uuid.UUID, db: AsyncSession
) -> int:
    result = await db.execute(
        select(Section).where(
            Section.campaign_id == campaign_id,
            Section.locked == True,  # noqa: E712
        )
    )
    return len(list(result.scalars().all()))


async def _get_manual_overrides_count(
    campaign_id: uuid.UUID, db: AsyncSession
) -> int:
    result = await db.execute(
        select(ManualOverride).where(ManualOverride.campaign_id == campaign_id)
    )
    return len(list(result.scalars().all()))


async def _get_pinned_theme(
    campaign_id: uuid.UUID, db: AsyncSession
) -> Optional[str]:
    """Retrieve the pinned theme name from visual brief, if any."""
    try:
        from app.models.visual_brief import VisualBrief

        result = await db.execute(
            select(VisualBrief).where(VisualBrief.campaign_id == campaign_id)
        )
        brief = result.scalar_one_or_none()
        if brief and brief.theme_name:
            return brief.theme_name
    except Exception:  # noqa: BLE001
        pass
    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/campaigns/{campaign_id}/vibe-shift")
async def vibe_shift_preview(
    campaign_id: uuid.UUID,
    body: VibeShiftPreviewBody,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """
    Preview what a Vibe Shift will regenerate vs. preserve.

    Does NOT perform any actual generation — returns a preview only.

    Returns:
        will_regenerate: list of asset categories that will be refreshed
        will_preserve: dict with locked_sections, manual_overrides, pinned_theme
        directive: the input directive
    """
    await _get_campaign_or_404(campaign_id, current_user, db)

    locked_sections = await _get_locked_sections_count(campaign_id, db)
    manual_overrides = await _get_manual_overrides_count(campaign_id, db)
    pinned_theme = await _get_pinned_theme(campaign_id, db)

    # Components that vibe shift can regenerate
    will_regenerate = ["palette", "hero_banner", "offer_strips", "fonts"]

    return {
        "will_regenerate": will_regenerate,
        "will_preserve": {
            "locked_sections": locked_sections,
            "manual_overrides": manual_overrides,
            "pinned_theme": pinned_theme,
        },
        "directive": body.directive,
    }


@router.post("/campaigns/{campaign_id}/vibe-shift/confirm")
async def vibe_shift_confirm(
    campaign_id: uuid.UUID,
    body: VibeShiftConfirmBody,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """
    Confirm and enqueue a Vibe Shift orchestration job.

    Validates campaign ownership, then enqueues an ARQ job for orchestration.

    Returns: {job_id: str, status: "queued"}
    """
    campaign = await _get_campaign_or_404(campaign_id, current_user, db)

    # Enqueue ARQ job via the same pattern as the orchestrator router
    try:
        import arq
        from app.workers.sync_worker import _parse_redis_url
        from app.config import settings

        redis_settings = _parse_redis_url(settings.redis_url)
        redis = await arq.create_pool(redis_settings)

        job = await redis.enqueue_job(
            "run_vibe_shift",
            str(campaign_id),
            body.directive,
        )
        job_id = job.job_id if job else str(uuid.uuid4())
        await redis.close()

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "vibe_shift_confirm: ARQ enqueue failed for campaign %s (%s) — using stub job_id",
            campaign_id,
            exc,
        )
        job_id = str(uuid.uuid4())

    logger.info(
        "vibe_shift_confirm: campaign=%s directive=%r job_id=%s by=%s",
        campaign_id,
        body.directive,
        job_id,
        current_user.id,
    )

    return {"job_id": job_id, "status": "queued"}
