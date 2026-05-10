"""
banners.py
==========
FastAPI router for banner generation and management.

Endpoints
---------
POST /campaigns/{campaign_id}/banners/generate
    Create 3 Banner rows with pending status and enqueue an artist job.

GET  /campaigns/{campaign_id}/banners
    List banners for a campaign ordered by variant_index.

PATCH /campaigns/{campaign_id}/banners/{banner_id}/activate
    Set a banner as the active one for its campaign.
"""

from __future__ import annotations

import uuid

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.config import settings
from app.database import get_async_session
from app.models.banner import Banner
from app.models.campaign import Campaign
from app.models.user import User
from app.models.visual_brief import VisualBrief

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class BannerRead(BaseModel):
    id: str
    campaign_id: str
    variant_index: int
    image_url: str
    is_active: bool
    generation_status: str

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────


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


async def _load_campaign_owned(
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


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/{campaign_id}/banners/generate", status_code=status.HTTP_201_CREATED)
async def generate_banners_for_campaign(
    campaign_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Create 3 pending Banner rows and enqueue the artist generation job."""
    await _load_campaign_owned(campaign_id, user, session)

    # Load VisualBrief — required before generating banners
    brief_result = await session.execute(
        select(VisualBrief).where(VisualBrief.campaign_id == campaign_id)
    )
    brief = brief_result.scalar_one_or_none()
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No visual brief found — run orchestrator first",
        )

    dalle_prompt = brief.dalle_prompt or ""

    # Create 3 Banner rows with pending status
    banner_ids: list[str] = []
    for i in range(3):
        banner = Banner(
            campaign_id=campaign_id,
            variant_index=i,
            generation_status="pending",
            image_url="/static/coming-soon.svg",
            is_active=False,
        )
        session.add(banner)
        await session.flush()
        banner_ids.append(str(banner.id))

    await session.commit()

    # Enqueue artist generation job
    try:
        redis_settings = _parse_redis_url(settings.redis_url)
        arq_redis = await create_pool(redis_settings)
        await arq_redis.enqueue_job(
            "run_artist_generation",
            campaign_id=str(campaign_id),
            dalle_prompt=dalle_prompt,
        )
        await arq_redis.close()
    except Exception:  # noqa: BLE001
        # Job enqueueing failure is non-fatal — banners are already created
        pass

    return {"job_id": "pending", "banner_ids": banner_ids}


@router.get("/{campaign_id}/banners", response_model=list[BannerRead])
async def list_banners(
    campaign_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[Banner]:
    """List all banners for a campaign ordered by variant_index."""
    await _load_campaign_owned(campaign_id, user, session)

    result = await session.execute(
        select(Banner)
        .where(Banner.campaign_id == campaign_id)
        .order_by(Banner.variant_index)
    )
    return list(result.scalars().all())


@router.patch(
    "/{campaign_id}/banners/{banner_id}/activate",
    response_model=BannerRead,
)
async def activate_banner(
    campaign_id: uuid.UUID,
    banner_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> Banner:
    """Set a banner as active; deactivate all others for the same campaign."""
    await _load_campaign_owned(campaign_id, user, session)

    # Load the target banner
    result = await session.execute(
        select(Banner).where(
            Banner.id == banner_id,
            Banner.campaign_id == campaign_id,
        )
    )
    banner = result.scalar_one_or_none()
    if banner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Banner not found",
        )

    # Deactivate all banners for this campaign
    all_result = await session.execute(
        select(Banner).where(Banner.campaign_id == campaign_id)
    )
    for b in all_result.scalars().all():
        b.is_active = False

    # Activate the selected banner
    banner.is_active = True
    await session.commit()
    await session.refresh(banner)
    return banner
