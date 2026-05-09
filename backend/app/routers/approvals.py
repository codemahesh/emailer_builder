"""
approvals.py
============
FastAPI router for campaign approvals (Issue 22).

Endpoints
---------
POST /review/{token}/approve      (no auth)
GET  /campaigns/{campaign_id}/approval
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.approval_event import ApprovalEvent
from app.models.campaign import Campaign, CampaignStatus
from app.models.review_token import ReviewToken
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class ApproveBody(BaseModel):
    reviewer_name: str
    viewport_confirmed: str  # "desktop" | "mobile" | "both"


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


async def _validate_token(token: str, db: AsyncSession) -> ReviewToken:
    """Look up a ReviewToken or raise 404."""
    result = await db.execute(
        select(ReviewToken).where(ReviewToken.token == token)
    )
    review_token = result.scalar_one_or_none()
    if review_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review token not found",
        )
    return review_token


def _approval_event_to_dict(event: ApprovalEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "campaign_id": str(event.campaign_id),
        "reviewer_name": event.reviewer_name,
        "approved_at": event.approved_at.isoformat(),
        "viewport_confirmed": event.viewport_confirmed,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/review/{token}/approve", status_code=status.HTTP_201_CREATED)
async def approve_campaign(
    token: str,
    body: ApproveBody,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """
    Public endpoint — no auth required.

    Validates the review token, creates an ApprovalEvent, and updates
    campaign.status to 'approved'.

    Returns the created ApprovalEvent as a dict.
    """
    review_token = await _validate_token(token, db)

    # Load the campaign
    campaign_result = await db.execute(
        select(Campaign).where(Campaign.id == review_token.campaign_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Create ApprovalEvent
    approval = ApprovalEvent(
        campaign_id=review_token.campaign_id,
        reviewer_name=body.reviewer_name,
        approved_at=datetime.now(timezone.utc),
        viewport_confirmed=body.viewport_confirmed,
    )
    db.add(approval)
    await db.flush()

    # Update campaign status to approved
    campaign.status = CampaignStatus.approved
    campaign.updated_at = datetime.now(timezone.utc)
    db.add(campaign)

    await db.flush()
    await db.refresh(approval)
    await db.commit()

    logger.info(
        "approve_campaign: campaign=%s reviewer=%s viewport=%s",
        review_token.campaign_id,
        body.reviewer_name,
        body.viewport_confirmed,
    )
    return _approval_event_to_dict(approval)


@router.get("/campaigns/{campaign_id}/approval")
async def get_approval(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """
    Return the latest ApprovalEvent for a campaign, or null if none.

    Returns: {approved: bool, event: ApprovalEvent | null}
    """
    await _get_campaign_or_404(campaign_id, current_user, db)

    result = await db.execute(
        select(ApprovalEvent)
        .where(ApprovalEvent.campaign_id == campaign_id)
        .order_by(ApprovalEvent.approved_at.desc())
        .limit(1)
    )
    event = result.scalar_one_or_none()

    if event is None:
        return {"approved": False, "event": None}

    return {
        "approved": True,
        "event": _approval_event_to_dict(event),
    }
