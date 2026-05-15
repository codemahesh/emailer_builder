"""
theme_plan.py
=============
FastAPI router for LLM-driven theme planning after product review approval.

Endpoints
---------
POST /campaigns/{campaign_id}/theme-plan
    Generate a theme plan (with rationale) based on product types and optional
    user feedback. Does NOT persist — returns plan for user review only.

POST /campaigns/{campaign_id}/theme-plan/apply
    Generate a theme plan with user feedback, persist it as the campaign's
    VisualBrief, render the email, and return the result.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.config import settings
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.product import Product, Section
from app.models.user import User
from app.models.visual_brief import VisualBrief
from app.modules.theme_planner import ThemePlanOutput, generate_theme_plan
from app.modules.icon_toc_mapper import map_toc_icons
from app.modules.mjml_renderer import (
    ProductData,
    RenderInput,
    SectionData,
    VisualTokens,
    render_campaign,
)
from app.schemas.visual_brief import VisualBriefRead

logger = logging.getLogger(__name__)

router = APIRouter()

_COMING_SOON_URL = "/static/coming-soon.svg"


# ── Schemas ───────────────────────────────────────────────────────────────────


class ThemePlanBody(BaseModel):
    user_feedback: str = ""


class ThemePlanResponse(BaseModel):
    theme_name: str
    rationale: str
    template_id: str
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
    dalle_prompt: str


# ── Helpers (mirrored from orchestrator.py) ───────────────────────────────────


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


async def _load_sections(campaign_id: uuid.UUID, session: AsyncSession) -> list[Section]:
    result = await session.execute(
        select(Section).where(Section.campaign_id == campaign_id).order_by(Section.position)
    )
    return list(result.scalars().all())


async def _load_products(campaign_id: uuid.UUID, session: AsyncSession) -> list[Product]:
    result = await session.execute(
        Product.active().where(Product.campaign_id == campaign_id).order_by(Product.position)
    )
    return list(result.scalars().all())


def _resolve_image_url(product: Product) -> str:
    if product.processed_image_url and product.processed_image_url != _COMING_SOON_URL:
        return product.processed_image_url
    if product.scraped_image_url and product.scraped_image_url != _COMING_SOON_URL:
        return product.scraped_image_url
    return _COMING_SOON_URL


def _plan_to_visual_tokens(plan: ThemePlanOutput) -> VisualTokens:
    return VisualTokens(
        background_color=plan.background_color,
        section_background=plan.section_color,
        accent_color=plan.accent_color,
        button_color=plan.button_color,
        button_text_color="#FFFFFF",
        h1_size=f"{plan.h1_size}px",
        h2_size=f"{plan.h2_size}px",
        body_size=f"{plan.body_size}px",
        font_family=plan.heading_font,
        product_background=plan.product_bg_color,
    )


def _build_render_input(
    campaign: Campaign,
    sections: list[Section],
    products: list[Product],
    tokens: VisualTokens,
) -> RenderInput:
    section_product_map: dict[str, list[Product]] = {}
    unsectioned: list[Product] = []

    for product in products:
        if product.section_id is not None:
            section_product_map.setdefault(str(product.section_id), []).append(product)
        else:
            unsectioned.append(product)

    section_data_list: list[SectionData] = []
    for sec in sections:
        sec_products = section_product_map.get(str(sec.id), [])
        product_data_list = [
            ProductData(
                id=str(p.id),
                sku=p.sku,
                name=p.scraped_name or p.sku,
                image_url=_resolve_image_url(p),
                price=p.formatted_price or p.raw_price or "",
                button_name=p.button_name or "Shop Now",
                product_link=p.utm_stitched or p.product_link,
                priority=p.priority.value if hasattr(p.priority, "value") else str(p.priority),
                position=p.position,
            )
            for p in sorted(sec_products, key=lambda x: x.position)
        ]
        section_data_list.append(
            SectionData(
                id=str(sec.id),
                title=sec.title,
                products=product_data_list,
                locked=sec.locked,
                position=sec.position,
            )
        )

    if unsectioned:
        product_data_list = [
            ProductData(
                id=str(p.id),
                sku=p.sku,
                name=p.scraped_name or p.sku,
                image_url=_resolve_image_url(p),
                price=p.formatted_price or p.raw_price or "",
                button_name=p.button_name or "Shop Now",
                product_link=p.utm_stitched or p.product_link,
                priority=p.priority.value if hasattr(p.priority, "value") else str(p.priority),
                position=p.position,
            )
            for p in sorted(unsectioned, key=lambda x: x.position)
        ]
        section_data_list.append(
            SectionData(id="unsectioned", title="Other Products", products=product_data_list, locked=False, position=999)
        )

    toc_titles = [(s.id, s.title) for s in section_data_list]
    toc_entries = map_toc_icons(toc_titles)

    return RenderInput(
        campaign_id=str(campaign.id),
        campaign_name=campaign.name,
        sections=section_data_list,
        toc_entries=toc_entries,
        visual_tokens=tokens,
        header_html="",
        footer_html="",
        banner_url="",
        manual_overrides={},
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/{campaign_id}/theme-plan", response_model=ThemePlanResponse)
async def preview_theme_plan(
    campaign_id: uuid.UUID,
    body: ThemePlanBody,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> ThemePlanResponse:
    """
    Generate a theme plan for the campaign without persisting it.

    Returns the theme name, colour palette, typography, and a plain-English
    rationale explaining the design choices — for display to the user before
    they commit.
    """
    campaign = await _load_campaign_owned(campaign_id, user, session)
    sections = await _load_sections(campaign_id, session)
    products = await _load_products(campaign_id, session)

    section_titles = [s.title for s in sections]
    product_names = [p.scraped_name or p.sku for p in products if (p.scraped_name or p.sku)]

    plan = await generate_theme_plan(
        section_titles=section_titles,
        product_names=product_names,
        user_feedback=body.user_feedback,
        openai_api_key=settings.openai_api_key,
    )

    logger.info("preview_theme_plan: campaign=%s theme=%s", campaign_id, plan.theme_name)
    return ThemePlanResponse(
        theme_name=plan.theme_name,
        rationale=plan.rationale,
        template_id=plan.template_id,
        background_color=plan.background_color,
        section_color=plan.section_color,
        accent_color=plan.accent_color,
        button_color=plan.button_color,
        product_bg_color=plan.product_bg_color,
        heading_font=plan.heading_font,
        body_font=plan.body_font,
        h1_size=plan.h1_size,
        h2_size=plan.h2_size,
        body_size=plan.body_size,
        dalle_prompt=plan.dalle_prompt,
    )


@router.post("/{campaign_id}/theme-plan/apply")
async def apply_theme_plan(
    campaign_id: uuid.UUID,
    body: ThemePlanBody,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Generate a theme plan (incorporating user feedback), persist it as the
    campaign's VisualBrief, render the email, and return the result.

    Returns {"brief": VisualBriefRead, "html": str, "size_kb": float}.
    """
    campaign = await _load_campaign_owned(campaign_id, user, session)
    sections = await _load_sections(campaign_id, session)
    products = await _load_products(campaign_id, session)

    section_titles = [s.title for s in sections]
    product_names = [p.scraped_name or p.sku for p in products if (p.scraped_name or p.sku)]

    plan = await generate_theme_plan(
        section_titles=section_titles,
        product_names=product_names,
        user_feedback=body.user_feedback,
        openai_api_key=settings.openai_api_key,
    )

    # Upsert VisualBrief
    existing = await session.execute(
        select(VisualBrief).where(VisualBrief.campaign_id == campaign_id)
    )
    brief_row = existing.scalar_one_or_none()
    if brief_row is None:
        brief_row = VisualBrief(campaign_id=campaign_id)
        session.add(brief_row)

    brief_row.theme_name = plan.theme_name
    brief_row.template_id = plan.template_id
    brief_row.background_color = plan.background_color
    brief_row.section_color = plan.section_color
    brief_row.accent_color = plan.accent_color
    brief_row.button_color = plan.button_color
    brief_row.product_bg_color = plan.product_bg_color
    brief_row.heading_font = plan.heading_font
    brief_row.body_font = plan.body_font
    brief_row.h1_size = plan.h1_size
    brief_row.h2_size = plan.h2_size
    brief_row.body_size = plan.body_size
    brief_row.dalle_prompt = plan.dalle_prompt

    await session.flush()
    await session.refresh(brief_row)

    # Render with the new tokens
    tokens = _plan_to_visual_tokens(plan)
    render_input = _build_render_input(campaign, sections, products, tokens)

    try:
        html, size_kb = render_campaign(render_input)
    except Exception as exc:
        logger.exception("apply_theme_plan: render failed for campaign %s", campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Render failed: {exc}",
        ) from exc

    await session.commit()

    brief_schema = VisualBriefRead(
        id=str(brief_row.id),
        campaign_id=str(brief_row.campaign_id),
        theme_name=brief_row.theme_name,
        template_id=brief_row.template_id,
        background_color=brief_row.background_color,
        section_color=brief_row.section_color,
        accent_color=brief_row.accent_color,
        button_color=brief_row.button_color,
        product_bg_color=brief_row.product_bg_color,
        heading_font=brief_row.heading_font,
        body_font=brief_row.body_font,
        h1_size=brief_row.h1_size,
        h2_size=brief_row.h2_size,
        body_size=brief_row.body_size,
        dalle_prompt=brief_row.dalle_prompt,
        pinned_theme_id=brief_row.pinned_theme_id,
        use_neutral_defaults=brief_row.use_neutral_defaults,
        created_at=brief_row.created_at,
        updated_at=brief_row.updated_at,
    )

    logger.info("apply_theme_plan: campaign=%s theme=%s size_kb=%.1f", campaign_id, plan.theme_name, size_kb)
    return {
        "brief": brief_schema.model_dump(mode="json"),
        "html": html,
        "size_kb": size_kb,
    }
