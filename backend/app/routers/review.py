"""
review.py
=========
FastAPI router for shareable review links (Issue 20).

Endpoints
---------
POST /campaigns/{campaign_id}/review/share
GET  /review/{token}
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.review_token import ReviewToken
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


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


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/campaigns/{campaign_id}/review/share")
async def share_review_link(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """
    Generate a shareable review token for the campaign.

    Upserts ReviewToken (deletes any existing token for campaign, inserts a new one).

    Returns: {token: str, url: str}
    """
    await _get_campaign_or_404(campaign_id, current_user, db)

    # Delete any existing token for this campaign
    await db.execute(
        delete(ReviewToken).where(ReviewToken.campaign_id == campaign_id)
    )
    await db.flush()

    # Generate a new UUID v4 token
    token_str = str(uuid.uuid4())

    review_token = ReviewToken(
        campaign_id=campaign_id,
        token=token_str,
    )
    db.add(review_token)
    await db.flush()
    await db.commit()

    logger.info(
        "share_review_link: campaign=%s token=%s by=%s",
        campaign_id,
        token_str,
        current_user.id,
    )

    return {
        "token": token_str,
        "url": f"/preview/{token_str}",
    }


@router.get("/review/{token}")
async def get_review_page(
    token: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """
    Public endpoint — no auth required.

    Looks up the ReviewToken, then loads the Campaign and renders HTML.
    Returns: {html: str, campaign_name: str, last_updated: str}
    """
    # Look up the token
    token_result = await db.execute(
        select(ReviewToken).where(ReviewToken.token == token)
    )
    review_token = token_result.scalar_one_or_none()
    if review_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review token not found",
        )

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

    # Render the campaign HTML
    from app.modules.mjml_renderer import render_campaign
    from app.routers.render import _build_render_input, _load_products, _load_sections

    sections = await _load_sections(campaign.id, db)
    products = await _load_products(campaign.id, db)
    render_input = _build_render_input(campaign, sections, products)

    try:
        html, _ = render_campaign(render_input)
    except Exception as exc:
        logger.exception("get_review_page: render failed for campaign %s", campaign.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Render failed: {exc}",
        ) from exc

    return {
        "html": html,
        "campaign_name": campaign.name,
        "last_updated": campaign.updated_at.isoformat(),
    }
