"""
orchestrator.py
===============
FastAPI router for the VisualOrchestrator endpoints.

Endpoints
---------
POST /campaigns/{campaign_id}/orchestrate
    Generate a visual brief via GPT-4o, persist it, trigger a render, and
    return the brief + rendered HTML.

GET  /campaigns/{campaign_id}/brief
    Return the persisted VisualBrief for a campaign (404 if none yet).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.config import settings
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.product import Product, Section
from app.models.user import User
from app.models.visual_brief import VisualBrief
from app.modules.icon_toc_mapper import map_toc_icons
from app.modules.mjml_renderer import (
    ProductData,
    RenderInput,
    SectionData,
    VisualTokens,
    render_campaign,
)
from app.modules.visual_orchestrator import generate_visual_brief
from app.schemas.visual_brief import VisualBriefRead

logger = logging.getLogger(__name__)

router = APIRouter()

_COMING_SOON_URL = "/static/coming-soon.svg"


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


async def _load_sections(
    campaign_id: uuid.UUID,
    session: AsyncSession,
) -> list[Section]:
    result = await session.execute(
        select(Section)
        .where(Section.campaign_id == campaign_id)
        .order_by(Section.position)
    )
    return list(result.scalars().all())


async def _load_products(
    campaign_id: uuid.UUID,
    session: AsyncSession,
) -> list[Product]:
    result = await session.execute(
        Product.active()
        .where(Product.campaign_id == campaign_id)
        .order_by(Product.position)
    )
    return list(result.scalars().all())


def _resolve_image_url(product: Product) -> str:
    if product.processed_image_url and product.processed_image_url != _COMING_SOON_URL:
        return product.processed_image_url
    if product.scraped_image_url and product.scraped_image_url != _COMING_SOON_URL:
        return product.scraped_image_url
    return _COMING_SOON_URL


def _build_render_input_with_tokens(
    campaign: Campaign,
    sections: list[Section],
    products: list[Product],
    tokens: VisualTokens,
) -> RenderInput:
    """Build a RenderInput using supplied VisualTokens (from visual brief)."""
    section_product_map: dict[str, list[Product]] = {}
    unsectioned: list[Product] = []

    for product in products:
        if product.section_id is not None:
            key = str(product.section_id)
            section_product_map.setdefault(key, []).append(product)
        else:
            unsectioned.append(product)

    section_data_list: list[SectionData] = []

    for sec in sections:
        sec_id = str(sec.id)
        sec_products = section_product_map.get(sec_id, [])
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
                id=sec_id,
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
            SectionData(
                id="unsectioned",
                title="Other Products",
                products=product_data_list,
                locked=False,
                position=999,
            )
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


def _brief_to_visual_tokens(brief: VisualBrief) -> VisualTokens:
    """Convert a VisualBrief ORM row into the VisualTokens used by the renderer."""
    return VisualTokens(
        background_color=brief.background_color,
        section_background=brief.section_color,
        accent_color=brief.accent_color,
        button_color=brief.button_color,
        button_text_color="#FFFFFF",
        h1_size=f"{brief.h1_size}px",
        h2_size=f"{brief.h2_size}px",
        body_size=f"{brief.body_size}px",
        font_family=brief.heading_font,
        product_background=brief.product_bg_color,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


class OrchestrateResponse(VisualBriefRead):
    html: str
    size_kb: float


@router.post("/{campaign_id}/orchestrate")
async def run_orchestrator(
    campaign_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    1. Fetch campaign sections + product names from DB.
    2. Call generate_visual_brief() with OpenAI key from settings.
    3. Upsert VisualBrief record in DB (create or update for campaign).
    4. Trigger a render using the new visual tokens.
    5. Return {"brief": VisualBriefRead, "html": "...", "size_kb": N}.
    """
    campaign = await _load_campaign_owned(campaign_id, user, session)
    sections = await _load_sections(campaign_id, session)
    products = await _load_products(campaign_id, session)

    # Collect section titles and product names for the orchestrator
    section_titles = [s.title for s in sections]
    product_names = [
        p.scraped_name or p.sku
        for p in products
        if (p.scraped_name or p.sku)
    ]

    # Generate visual brief via GPT-4o (falls back to defaults silently)
    brief_output = await generate_visual_brief(
        section_titles=section_titles,
        product_names=product_names,
        openai_api_key=settings.openai_api_key,
    )

    # Upsert VisualBrief row
    existing_result = await session.execute(
        select(VisualBrief).where(VisualBrief.campaign_id == campaign_id)
    )
    brief_row = existing_result.scalar_one_or_none()

    if brief_row is None:
        brief_row = VisualBrief(campaign_id=campaign_id)
        session.add(brief_row)

    brief_row.theme_name = brief_output.theme_name
    brief_row.template_id = brief_output.template_id
    brief_row.background_color = brief_output.background_color
    brief_row.section_color = brief_output.section_color
    brief_row.accent_color = brief_output.accent_color
    brief_row.button_color = brief_output.button_color
    brief_row.product_bg_color = brief_output.product_bg_color
    brief_row.heading_font = brief_output.heading_font
    brief_row.body_font = brief_output.body_font
    brief_row.h1_size = brief_output.h1_size
    brief_row.h2_size = brief_output.h2_size
    brief_row.body_size = brief_output.body_size
    brief_row.dalle_prompt = brief_output.dalle_prompt

    await session.flush()
    await session.refresh(brief_row)

    # Build visual tokens from the brief and render
    tokens = _brief_to_visual_tokens(brief_row)
    render_input = _build_render_input_with_tokens(campaign, sections, products, tokens)

    try:
        html, size_kb = render_campaign(render_input)
    except Exception as exc:
        logger.exception(
            "run_orchestrator: render failed for campaign %s", campaign_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Render failed: {exc}",
        ) from exc

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

    return {
        "brief": brief_schema.model_dump(mode="json"),
        "html": html,
        "size_kb": size_kb,
    }


@router.get("/{campaign_id}/brief", response_model=VisualBriefRead)
async def get_visual_brief(
    campaign_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> VisualBrief:
    """Return the persisted VisualBrief for a campaign."""
    # Verify the campaign belongs to this user
    await _load_campaign_owned(campaign_id, user, session)

    result = await session.execute(
        select(VisualBrief).where(VisualBrief.campaign_id == campaign_id)
    )
    brief_row = result.scalar_one_or_none()
    if brief_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visual brief not found for this campaign",
        )
    return brief_row
