"""
overrides.py
============
FastAPI router for manual asset and text overrides.

Issues 11 + 12

Endpoints
---------
POST   /campaigns/{campaign_id}/overrides/asset
DELETE /campaigns/{campaign_id}/overrides/asset
GET    /campaigns/{campaign_id}/overrides/asset
POST   /campaigns/{campaign_id}/overrides/text
GET    /campaigns/{campaign_id}/overrides/text
DELETE /campaigns/{campaign_id}/overrides/text/{text_override_id}
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.manual_override import ManualOverride
from app.models.text_override import TextOverride
from app.models.user import User
from app.modules import manual_asset_override

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class AssetOverrideBody(BaseModel):
    target_type: str
    target_id: Optional[str] = None
    override_url: str


class TextOverrideBody(BaseModel):
    target_id: str
    field: str
    override_value: str


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


def _override_to_dict(override: ManualOverride) -> dict[str, Any]:
    return {
        "id": str(override.id),
        "campaign_id": str(override.campaign_id),
        "target_type": override.target_type,
        "target_id": override.target_id,
        "override_url": override.override_url,
        "created_by": str(override.created_by) if override.created_by else None,
        "created_at": override.created_at.isoformat(),
    }


def _text_override_to_dict(override: TextOverride) -> dict[str, Any]:
    return {
        "id": str(override.id),
        "campaign_id": str(override.campaign_id),
        "target_id": override.target_id,
        "field": override.field,
        "override_value": override.override_value,
        "created_at": override.created_at.isoformat(),
        "updated_at": override.updated_at.isoformat(),
    }


# ── Asset Override Endpoints ──────────────────────────────────────────────────


@router.post("/campaigns/{campaign_id}/overrides/asset")
async def apply_asset_override(
    campaign_id: uuid.UUID,
    body: AssetOverrideBody,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Apply a manual image override for a campaign asset."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    try:
        override = await manual_asset_override.apply_override(
            db=db,
            campaign_id=campaign_id,
            target_type=body.target_type,
            target_id=body.target_id,
            override_url=body.override_url,
            created_by=current_user.id,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _override_to_dict(override)


@router.delete("/campaigns/{campaign_id}/overrides/asset")
async def revert_asset_override(
    campaign_id: uuid.UUID,
    target_type: str = Query(...),
    target_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict:
    """Revert (delete) a manual image override."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    await manual_asset_override.revert_override(
        db=db,
        campaign_id=campaign_id,
        target_type=target_type,
        target_id=target_id,
    )
    await db.commit()
    return {}


@router.get("/campaigns/{campaign_id}/overrides/asset")
async def list_asset_overrides(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> list[dict[str, Any]]:
    """List all manual image overrides for a campaign."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    overrides = await manual_asset_override.get_overrides(db=db, campaign_id=campaign_id)
    return [_override_to_dict(o) for o in overrides]


# ── Text Override Endpoints ───────────────────────────────────────────────────


@router.post("/campaigns/{campaign_id}/overrides/text")
async def apply_text_override(
    campaign_id: uuid.UUID,
    body: TextOverrideBody,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Apply a manual text override for a product field."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    # Upsert: delete existing matching override, insert new
    await db.execute(
        delete(TextOverride).where(
            TextOverride.campaign_id == campaign_id,
            TextOverride.target_id == body.target_id,
            TextOverride.field == body.field,
        )
    )
    await db.flush()

    override = TextOverride(
        campaign_id=campaign_id,
        target_id=body.target_id,
        field=body.field,
        override_value=body.override_value,
    )
    db.add(override)
    await db.flush()
    await db.refresh(override)
    await db.commit()

    return _text_override_to_dict(override)


@router.get("/campaigns/{campaign_id}/overrides/text")
async def list_text_overrides(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> list[dict[str, Any]]:
    """List all text overrides for a campaign."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    result = await db.execute(
        select(TextOverride)
        .where(TextOverride.campaign_id == campaign_id)
        .order_by(TextOverride.created_at)
    )
    overrides = list(result.scalars().all())
    return [_text_override_to_dict(o) for o in overrides]


@router.delete("/campaigns/{campaign_id}/overrides/text/{text_override_id}")
async def delete_text_override(
    campaign_id: uuid.UUID,
    text_override_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict:
    """Delete a specific text override."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    result = await db.execute(
        select(TextOverride).where(
            TextOverride.id == text_override_id,
            TextOverride.campaign_id == campaign_id,
        )
    )
    override = result.scalar_one_or_none()
    if override is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Text override not found",
        )

    await db.delete(override)
    await db.commit()
    return {}
