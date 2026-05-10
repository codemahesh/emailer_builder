"""
templates.py
============
FastAPI router for template management.

Endpoints
---------
GET    /templates
    List all templates (public, no auth required).

POST   /campaigns/{id}/templates/apply
    Apply an existing template to a campaign's visual brief.

POST   /campaigns/{id}/templates/save
    Save the current campaign brief as a new designer template.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.template import Template
from app.models.user import User
from app.models.visual_brief import VisualBrief
from app.schemas.visual_brief import VisualBriefRead

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class TemplateRead(BaseModel):
    id: str
    name: str
    source: str
    structural_pattern: str | None
    created_at: str

    model_config = {"from_attributes": True}


class ApplyTemplateBody(BaseModel):
    template_id: str


class SaveTemplateBody(BaseModel):
    name: str


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


@router.get("/templates", response_model=list[TemplateRead])
async def list_templates(
    session: AsyncSession = Depends(get_async_session),
) -> list[Template]:
    """List all templates (public catalog, no auth required)."""
    result = await session.execute(
        select(Template).order_by(Template.created_at)
    )
    templates = list(result.scalars().all())
    return [
        TemplateRead(
            id=str(t.id),
            name=t.name,
            source=t.source,
            structural_pattern=t.structural_pattern,
            created_at=t.created_at.isoformat() if t.created_at else "",
        )
        for t in templates
    ]


@router.post(
    "/campaigns/{campaign_id}/templates/apply",
    response_model=VisualBriefRead,
)
async def apply_template(
    campaign_id: uuid.UUID,
    body: ApplyTemplateBody,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> VisualBriefRead:
    """Apply an existing template to the campaign's visual brief."""
    await _load_campaign_owned(campaign_id, user, session)

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

    # Verify the template exists
    try:
        template_uuid = uuid.UUID(body.template_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template_id format",
        )

    tmpl_result = await session.execute(
        select(Template).where(Template.id == template_uuid)
    )
    template = tmpl_result.scalar_one_or_none()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    brief.template_id = body.template_id
    await session.commit()
    await session.refresh(brief)
    return _brief_to_visual_brief_read(brief)


@router.post(
    "/campaigns/{campaign_id}/templates/save",
    response_model=TemplateRead,
    status_code=status.HTTP_201_CREATED,
)
async def save_template(
    campaign_id: uuid.UUID,
    body: SaveTemplateBody,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> TemplateRead:
    """Save the current campaign brief's visual style as a new designer template."""
    await _load_campaign_owned(campaign_id, user, session)

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

    # Serialise visual style fields from the brief
    visual_style = {
        "background_color": brief.background_color,
        "section_color": brief.section_color,
        "accent_color": brief.accent_color,
        "button_color": brief.button_color,
        "product_bg_color": brief.product_bg_color,
        "heading_font": brief.heading_font,
        "body_font": brief.body_font,
        "h1_size": brief.h1_size,
        "h2_size": brief.h2_size,
        "body_size": brief.body_size,
    }

    template = Template(
        name=body.name,
        source="designer",
        visual_style_json=json.dumps(visual_style),
        created_by=user.id,
    )
    session.add(template)
    await session.flush()
    await session.refresh(template)
    await session.commit()

    return TemplateRead(
        id=str(template.id),
        name=template.name,
        source=template.source,
        structural_pattern=template.structural_pattern,
        created_at=template.created_at.isoformat() if template.created_at else "",
    )
