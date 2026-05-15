"""
comments.py
===========
FastAPI router for reviewer comments (Issue 21).

Endpoints
---------
POST  /review/{token}/comments         (no auth)
GET   /campaigns/{campaign_id}/comments
PATCH /campaigns/{campaign_id}/comments/{comment_id}/resolve
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
from app.models.comment import Comment
from app.models.review_token import ReviewToken
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class CommentCreateBody(BaseModel):
    section_id: Optional[str] = None
    author_name: str
    body: str
    parent_id: Optional[str] = None


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


def _comment_to_dict(comment: Comment) -> dict[str, Any]:
    return {
        "id": str(comment.id),
        "campaign_id": str(comment.campaign_id),
        "section_id": comment.section_id,
        "author_name": comment.author_name,
        "body": comment.body,
        "resolved": comment.resolved,
        "parent_id": str(comment.parent_id) if comment.parent_id else None,
        "created_at": comment.created_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/review/{token}/comments")
async def list_review_comments(
    token: str,
    db: AsyncSession = Depends(get_async_session),
) -> list[dict[str, Any]]:
    """
    Public endpoint — no auth required.

    Return all unresolved comments for the campaign associated with this token.
    """
    review_token = await _validate_token(token, db)

    result = await db.execute(
        select(Comment)
        .where(
            Comment.campaign_id == review_token.campaign_id,
            Comment.resolved == False,  # noqa: E712
        )
        .order_by(Comment.created_at.asc())
    )
    comments = list(result.scalars().all())
    return [_comment_to_dict(c) for c in comments]


@router.post("/review/{token}/comments", status_code=status.HTTP_201_CREATED)
async def create_comment(
    token: str,
    body: CommentCreateBody,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """
    Public endpoint — no auth required.

    Validate the review token, then create a Comment associated with the campaign.
    """
    review_token = await _validate_token(token, db)

    # Parse optional parent_id
    parent_uuid: Optional[uuid.UUID] = None
    if body.parent_id:
        try:
            parent_uuid = uuid.UUID(body.parent_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid parent_id format",
            )

    comment = Comment(
        campaign_id=review_token.campaign_id,
        section_id=body.section_id,
        author_name=body.author_name,
        body=body.body,
        parent_id=parent_uuid,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    await db.commit()

    logger.info(
        "create_comment: campaign=%s comment=%s author=%s",
        review_token.campaign_id,
        comment.id,
        body.author_name,
    )
    return _comment_to_dict(comment)


@router.get("/campaigns/{campaign_id}/comments")
async def list_comments(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> list[dict[str, Any]]:
    """List all unresolved comments for a campaign, ordered newest first."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    result = await db.execute(
        select(Comment)
        .where(
            Comment.campaign_id == campaign_id,
            Comment.resolved == False,  # noqa: E712
        )
        .order_by(Comment.created_at.desc())
    )
    comments = list(result.scalars().all())
    return [_comment_to_dict(c) for c in comments]


@router.patch("/campaigns/{campaign_id}/comments/{comment_id}/resolve")
async def resolve_comment(
    campaign_id: uuid.UUID,
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Mark a comment as resolved."""
    await _get_campaign_or_404(campaign_id, current_user, db)

    result = await db.execute(
        select(Comment).where(
            Comment.id == comment_id,
            Comment.campaign_id == campaign_id,
        )
    )
    comment = result.scalar_one_or_none()
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    comment.resolved = True
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    await db.commit()

    logger.info(
        "resolve_comment: campaign=%s comment=%s by=%s",
        campaign_id,
        comment_id,
        current_user.id,
    )
    return _comment_to_dict(comment)
