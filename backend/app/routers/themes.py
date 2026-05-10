"""
themes.py
=========
FastAPI router for theme management.

Endpoints
---------
GET    /themes
    List all themes (public, no auth required).

POST   /campaigns/{id}/themes/apply
    Apply a theme's color/font settings to the campaign's visual brief.

DELETE /campaigns/{id}/themes/pin
    Unpin the theme from the campaign's visual brief.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.theme import Theme
from app.models.user import User
from app.models.visual_brief import VisualBrief
from app.schemas.visual_brief import VisualBriefRead

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class ThemeRead(BaseModel):
    id: str
    name: str
    background_color: str
    section_color: str
    accent_color: str
    button_color: str
    product_bg_color: str
    heading_font: str
    body_font: str
    h1_size: int
    h2_size: int
    body_size: int

    model_config = {"from_attributes": True}


class ApplyThemeBody(BaseModel):
    theme_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────


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


def _brief_to_visual_brief_read(brief: VisualBrief) -> VisualBriefRead:
    return VisualBriefRead(
        id=str(brief.id),
        campaign_id=str(brief.campaign_id),
        theme_name=brief.theme_name,
        template_id=brief.template_id,
        background_color=brief.background_color,
        section_color=brief.section_color,
        accent_color=brief.accent_color,
        button_color=brief.button_color,
        product_bg_color=brief.product_bg_color,
        heading_font=brief.heading_font,
        body_font=brief.body_font,
        h1_size=brief.h1_size,
        h2_size=brief.h2_size,
        body_size=brief.body_size,
        dalle_prompt=brief.dalle_prompt,
        pinned_theme_id=brief.pinned_theme_id,
        use_neutral_defaults=brief.use_neutral_defaults,
        created_at=brief.created_at,
        updated_at=brief.updated_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/themes", response_model=list[ThemeRead])
async def list_themes(
    session: AsyncSession = Depends(get_async_session),
) -> list[ThemeRead]:
    """List all themes (public catalog, no auth required)."""
    result = await session.execute(
        select(Theme).order_by(Theme.created_at)
    )
    themes = list(result.scalars().all())
    return [
        ThemeRead(
            id=str(t.id),
            name=t.name,
            background_color=t.background_color,
            section_color=t.section_color,
            accent_color=t.accent_color,
            button_color=t.button_color,
            product_bg_color=t.product_bg_color,
            heading_font=t.heading_font,
            body_font=t.body_font,
            h1_size=t.h1_size,
            h2_size=t.h2_size,
            body_size=t.body_size,
        )
        for t in themes
    ]


@router.post(
    "/campaigns/{campaign_id}/themes/apply",
    response_model=VisualBriefRead,
)
async def apply_theme(
    campaign_id: uuid.UUID,
    body: ApplyThemeBody,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> VisualBriefRead:
    """Apply a theme's color and font settings to the campaign's visual brief."""
    await _load_campaign_owned(campaign_id, user, session)

    # Validate and load theme
    try:
        theme_uuid = uuid.UUID(body.theme_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid theme_id format",
        )

    theme_result = await session.execute(
        select(Theme).where(Theme.id == theme_uuid)
    )
    theme = theme_result.scalar_one_or_none()
    if theme is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    # Load VisualBrief
    brief_result = await session.execute(
        select(VisualBrief).where(VisualBrief.campaign_id == campaign_id)
    )
    brief = brief_result.scalar_one_or_none()
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No visual brief found — run orchestrator first",
        )

    # Copy all color/font fields from theme to brief
    brief.background_color = theme.background_color
    brief.section_color = theme.section_color
    brief.accent_color = theme.accent_color
    brief.button_color = theme.button_color
    brief.product_bg_color = theme.product_bg_color
    brief.heading_font = theme.heading_font
    brief.body_font = theme.body_font
    brief.h1_size = theme.h1_size
    brief.h2_size = theme.h2_size
    brief.body_size = theme.body_size
    brief.pinned_theme_id = str(theme.id)

    await session.commit()
    await session.refresh(brief)
    return _brief_to_visual_brief_read(brief)


@router.delete(
    "/campaigns/{campaign_id}/themes/pin",
    response_model=VisualBriefRead,
)
async def unpin_theme(
    campaign_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> VisualBriefRead:
    """Unpin the theme from the campaign's visual brief."""
    await _load_campaign_owned(campaign_id, user, session)

    brief_result = await session.execute(
        select(VisualBrief).where(VisualBrief.campaign_id == campaign_id)
    )
    brief = brief_result.scalar_one_or_none()
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No visual brief found",
        )

    brief.pinned_theme_id = None
    await session.commit()
    await session.refresh(brief)
    return _brief_to_visual_brief_read(brief)
