"""
preferences.py
==============
FastAPI router for editor preference signals (Issue 17).

Endpoints
---------
GET    /preferences
POST   /preferences/signal
DELETE /preferences
DELETE /preferences/{preference_id}
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
from app.models.user import User
from app.models.user_preference import UserPreference
from app.modules import preference_memory

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class SignalBody(BaseModel):
    signal_type: str
    asset_type: str
    signal_value: str
    campaign_id: Optional[str] = None
    weight: float = 1.0


# ── Helpers ───────────────────────────────────────────────────────────────────


def _preference_to_dict(pref: UserPreference) -> dict[str, Any]:
    return {
        "id": str(pref.id),
        "editor_id": str(pref.editor_id),
        "signal_type": pref.signal_type,
        "asset_type": pref.asset_type,
        "signal_value": pref.signal_value,
        "campaign_id": str(pref.campaign_id) if pref.campaign_id else None,
        "weight": pref.weight,
        "created_at": pref.created_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/preferences")
async def list_preferences(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> list[dict[str, Any]]:
    """List all preference signals for the current user."""
    result = await db.execute(
        select(UserPreference)
        .where(UserPreference.editor_id == current_user.id)
        .order_by(UserPreference.weight.desc(), UserPreference.created_at.desc())
    )
    preferences = list(result.scalars().all())
    return [_preference_to_dict(p) for p in preferences]


@router.post("/preferences/signal", status_code=status.HTTP_201_CREATED)
async def record_preference_signal(
    body: SignalBody,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Record a new editor preference signal."""
    campaign_uuid: Optional[uuid.UUID] = None
    if body.campaign_id:
        try:
            campaign_uuid = uuid.UUID(body.campaign_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid campaign_id format",
            )

    preference = await preference_memory.record_signal(
        db=db,
        editor_id=current_user.id,
        signal_type=body.signal_type,
        asset_type=body.asset_type,
        signal_value=body.signal_value,
        campaign_id=campaign_uuid,
        weight=body.weight,
    )
    await db.commit()
    return _preference_to_dict(preference)


@router.delete("/preferences", status_code=status.HTTP_200_OK)
async def reset_preferences(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Delete all preference signals for the current user."""
    deleted = await preference_memory.reset(db=db, editor_id=current_user.id)
    await db.commit()
    return {"deleted": deleted}


@router.delete("/preferences/{preference_id}")
async def delete_preference(
    preference_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict:
    """Delete a single preference signal owned by the current user."""
    result = await db.execute(
        select(UserPreference).where(
            UserPreference.id == preference_id,
            UserPreference.editor_id == current_user.id,
        )
    )
    preference = result.scalar_one_or_none()
    if preference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preference not found",
        )

    await db.delete(preference)
    await db.commit()
    return {}
