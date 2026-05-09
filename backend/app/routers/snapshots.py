"""
snapshots.py
============
FastAPI router for campaign snapshots (Issue 16).

Endpoints
---------
GET  /campaigns/{campaign_id}/snapshots
POST /campaigns/{campaign_id}/snapshots
GET  /campaigns/{campaign_id}/snapshots/{snapshot_id}
POST /campaigns/{campaign_id}/snapshots/{snapshot_id}/restore
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
from app.models.snapshot import Snapshot
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class SnapshotCreateBody(BaseModel):
    summary_chip: str
    mjml_state_json: str


class SnapshotRestoreBody(BaseModel):
    pass  # empty body


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


def _snapshot_to_dict(snapshot: Snapshot) -> dict[str, Any]:
    return {
        "id": str(snapshot.id),
        "campaign_id": str(snapshot.campaign_id),
        "mjml_state_json": snapshot.mjml_state_json,
        "summary_chip": snapshot.summary_chip,
        "created_by": str(snapshot.created_by) if snapshot.created_by else None,
        "created_at": snapshot.created_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/campaigns/{campaign_id}/snapshots")
async def list_snapshots(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> list[dict[str, Any]]:
    """List snapshots for a campaign, ordered newest first (limit 50)."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.campaign_id == campaign_id)
        .order_by(Snapshot.created_at.desc())
        .limit(50)
    )
    snapshots = list(result.scalars().all())
    return [_snapshot_to_dict(s) for s in snapshots]


@router.post("/campaigns/{campaign_id}/snapshots", status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    campaign_id: uuid.UUID,
    body: SnapshotCreateBody,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Create a new snapshot of the current campaign state."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    snapshot = Snapshot(
        campaign_id=campaign_id,
        mjml_state_json=body.mjml_state_json,
        summary_chip=body.summary_chip,
        created_by=current_user.id,
    )
    db.add(snapshot)
    await db.flush()
    await db.refresh(snapshot)
    await db.commit()

    logger.info(
        "create_snapshot: campaign=%s snapshot=%s chip=%s by=%s",
        campaign_id,
        snapshot.id,
        body.summary_chip,
        current_user.id,
    )
    return _snapshot_to_dict(snapshot)


@router.get("/campaigns/{campaign_id}/snapshots/{snapshot_id}")
async def get_snapshot(
    campaign_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Retrieve a single snapshot by ID."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    result = await db.execute(
        select(Snapshot).where(
            Snapshot.id == snapshot_id,
            Snapshot.campaign_id == campaign_id,
        )
    )
    snapshot = result.scalar_one_or_none()
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found",
        )
    return _snapshot_to_dict(snapshot)


@router.post("/campaigns/{campaign_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot(
    campaign_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    body: SnapshotRestoreBody,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """
    Restore a snapshot.

    1. Creates a pre-restore snapshot from the latest existing snapshot.
    2. Returns the requested snapshot (client applies it).

    Returns: {snapshot: ..., pre_restore_snapshot: ...}
    """
    await _get_campaign_or_404(campaign_id, current_user, db)

    # Fetch the target snapshot
    target_result = await db.execute(
        select(Snapshot).where(
            Snapshot.id == snapshot_id,
            Snapshot.campaign_id == campaign_id,
        )
    )
    target_snapshot = target_result.scalar_one_or_none()
    if target_snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found",
        )

    # Find the latest snapshot to use as the pre-restore capture
    latest_result = await db.execute(
        select(Snapshot)
        .where(Snapshot.campaign_id == campaign_id)
        .order_by(Snapshot.created_at.desc())
        .limit(1)
    )
    latest_snapshot = latest_result.scalar_one_or_none()

    # Create a "Pre-restore" snapshot capturing the current state
    pre_restore_state = (
        latest_snapshot.mjml_state_json if latest_snapshot else "{}"
    )
    pre_restore = Snapshot(
        campaign_id=campaign_id,
        mjml_state_json=pre_restore_state,
        summary_chip="Pre-restore",
        created_by=current_user.id,
    )
    db.add(pre_restore)
    await db.flush()
    await db.refresh(pre_restore)
    await db.commit()

    logger.info(
        "restore_snapshot: campaign=%s restoring snapshot=%s pre_restore=%s by=%s",
        campaign_id,
        snapshot_id,
        pre_restore.id,
        current_user.id,
    )

    return {
        "snapshot": _snapshot_to_dict(target_snapshot),
        "pre_restore_snapshot": _snapshot_to_dict(pre_restore),
    }
