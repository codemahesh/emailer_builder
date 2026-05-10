"""
render.py
=========
FastAPI router for campaign HTML rendering.

Endpoints
---------
POST /campaigns/{campaign_id}/render
GET  /campaigns/{campaign_id}/render
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.product import Product, Section
from app.models.user import User
from app.modules.icon_toc_mapper import map_toc_icons
from app.modules.mjml_renderer import (
    ProductData,
    RenderInput,
    SectionData,
    VisualTokens,
    render_campaign,
)
from app.schemas.render import RenderResponse

logger = logging.getLogger(__name__)

router = APIRouter()

_COMING_SOON_URL = "/static/coming-soon.svg"


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _load_campaign(
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
    """Return the best available image URL for a product."""
    if product.processed_image_url and product.processed_image_url != _COMING_SOON_URL:
        return product.processed_image_url
    if product.scraped_image_url and product.scraped_image_url != _COMING_SOON_URL:
        return product.scraped_image_url
    return _COMING_SOON_URL


def _build_render_input(
    campaign: Campaign,
    sections: list[Section],
    products: list[Product],
) -> RenderInput:
    """Assemble a RenderInput from DB objects."""

    # Build a map of section_id → list of products
    section_product_map: dict[str, list[Product]] = {}
    unsectioned: list[Product] = []

    for product in products:
        if product.section_id is not None:
            key = str(product.section_id)
            section_product_map.setdefault(key, []).append(product)
        else:
            unsectioned.append(product)

    # Convert sections → SectionData
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

    # If any products are unsectioned, create a synthetic "Other" section
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

    # Build ToC entries
    toc_titles = [(s.id, s.title) for s in section_data_list]
    toc_entries = map_toc_icons(toc_titles)

    return RenderInput(
        campaign_id=str(campaign.id),
        campaign_name=campaign.name,
        sections=section_data_list,
        toc_entries=toc_entries,
        visual_tokens=VisualTokens(),
        header_html="",
        footer_html="",
        banner_url="",
        manual_overrides={},
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/campaigns/{campaign_id}/render", response_model=RenderResponse)
async def render_campaign_html(
    campaign_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> RenderResponse:
    """
    Build and return the compiled HTML for a campaign.

    1. Load campaign from DB
    2. Load sections and products
    3. Build RenderInput
    4. Map ToC icons
    5. Compile MJML → HTML
    6. Return RenderResponse
    """
    campaign = await _load_campaign(campaign_id, user, session)
    sections = await _load_sections(campaign_id, session)
    products = await _load_products(campaign_id, session)

    render_input = _build_render_input(campaign, sections, products)

    try:
        html, size_kb = render_campaign(render_input)
    except Exception as exc:
        logger.exception("render_campaign_html: render failed for campaign %s", campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Render failed: {exc}",
        ) from exc

    product_count = sum(len(s.products) for s in render_input.sections)
    section_count = len(render_input.sections)

    return RenderResponse(
        html=html,
        size_kb=size_kb,
        section_count=section_count,
        product_count=product_count,
    )


@router.get("/campaigns/{campaign_id}/render", response_model=RenderResponse)
async def get_rendered_html(
    campaign_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> RenderResponse:
    """GET variant of the render endpoint — same logic as POST."""
    return await render_campaign_html(
        campaign_id=campaign_id,
        user=user,
        session=session,
    )
