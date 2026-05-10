"""
sections.py
===========
FastAPI router for campaign section management.

Endpoints
---------
GET   /campaigns/{campaign_id}/sections
    List all sections for a campaign with lock state.

PATCH /campaigns/{campaign_id}/sections/{section_id}/lock
    Toggle the lock state of a section.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.product import Section
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class SectionRead(BaseModel):
    id: str
    campaign_id: str
    title: str
    position: int
    locked: bool
    created_at: str

    model_config = {"from_attributes": True}


class LockToggleBody(BaseModel):
    locked: bool


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


async def _get_section_or_404(
    section_id: uuid.UUID,
    campaign_id: uuid.UUID,
    db: AsyncSession,
) -> Section:
    result = await db.execute(
        select(Section).where(
            Section.id == section_id,
            Section.campaign_id == campaign_id,
        )
    )
    section = result.scalar_one_or_none()
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found",
        )
    return section


def _section_to_dict(section: Section) -> dict[str, Any]:
    return {
        "id": str(section.id),
        "campaign_id": str(section.campaign_id),
        "title": section.title,
        "position": section.position,
        "locked": section.locked,
        "created_at": section.created_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/{campaign_id}/sections", response_model=list[SectionRead])
async def list_sections(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> list[dict[str, Any]]:
    """List all sections for a campaign with lock state."""
    # Verify campaign belongs to current user
    await _get_campaign_or_404(campaign_id, current_user, db)

    result = await db.execute(
        select(Section)
        .where(Section.campaign_id == campaign_id)
        .order_by(Section.position)
    )
    sections = list(result.scalars().all())
    return [_section_to_dict(s) for s in sections]


@router.patch(
    "/{campaign_id}/sections/{section_id}/lock",
    response_model=SectionRead,
)
async def toggle_section_lock(
    campaign_id: uuid.UUID,
    section_id: uuid.UUID,
    body: LockToggleBody,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Toggle lock state on a section. Returns the updated section."""
    # Verify campaign belongs to current user
    await _get_campaign_or_404(campaign_id, current_user, db)

    # Verify section belongs to campaign and load it
    section = await _get_section_or_404(section_id, campaign_id, db)

    # Apply the new lock state
    section.locked = body.locked
    db.add(section)
    await db.flush()
    await db.refresh(section)

    logger.info(
        "toggle_section_lock: section %s in campaign %s set locked=%s by user %s",
        section_id,
        campaign_id,
        body.locked,
        current_user.id,
    )

    return _section_to_dict(section)
