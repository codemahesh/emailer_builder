"""
orchestrator_worker.py
======================
ARQ background task: run visual brief generation + first render after sync.

Task: ``run_orchestration(ctx, campaign_id)``

Workflow
--------
1. Load campaign sections and products from DB.
2. Call ``generate_visual_brief()`` with the OpenAI key from settings.
3. Upsert the VisualBrief row in the DB.
4. Run a render using the new visual tokens.
5. Emit a WebSocket event so the frontend can pick up the new brief.
6. Return a summary dict.

Failures are handled silently at each step — the worker never raises so that
ARQ does not retry unnecessarily.  Raw OpenAI errors are logged at WARNING
level but never propagated.
"""

from __future__ import annotations

import logging
import uuid as _uuid

from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models.campaign import Campaign
from app.models.product import Product, Section
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
from app.ws.gateway import gateway

logger = logging.getLogger(__name__)

_COMING_SOON_URL = "/static/coming-soon.svg"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve_image_url(product: Product) -> str:
    if product.processed_image_url and product.processed_image_url != _COMING_SOON_URL:
        return product.processed_image_url
    if product.scraped_image_url and product.scraped_image_url != _COMING_SOON_URL:
        return product.scraped_image_url
    return _COMING_SOON_URL


def _brief_to_visual_tokens(brief: VisualBrief) -> VisualTokens:
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
                priority=(
                    p.priority.value if hasattr(p.priority, "value") else str(p.priority)
                ),
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
                priority=(
                    p.priority.value if hasattr(p.priority, "value") else str(p.priority)
                ),
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


# ── ARQ task ──────────────────────────────────────────────────────────────────


async def run_orchestration(ctx: dict, campaign_id: str) -> dict:
    """
    ARQ background task.  Called after ``run_full_sync`` completes.

    Generates a visual brief via GPT-4o, persists it, and performs the first
    render using the new visual tokens.  Emits a ``brief_ready`` WebSocket
    event on success.

    Parameters
    ----------
    ctx:
        ARQ context dict (``ctx["redis"]`` is an ArqRedis instance).
    campaign_id:
        UUID string of the campaign to orchestrate.

    Returns
    -------
    dict
        Summary with keys ``campaign_id``, ``status``, ``theme_name``,
        ``size_kb``.  ``status`` is either ``"done"`` or ``"failed"``.
    """
    cid = str(campaign_id)
    logger.info("run_orchestration: starting for campaign %s", cid)

    # ── 1. Load campaign data ─────────────────────────────────────────────────
    try:
        async with async_session_maker() as session:
            camp_result = await session.execute(
                select(Campaign).where(Campaign.id == _uuid.UUID(cid))
            )
            campaign = camp_result.scalar_one_or_none()
            if campaign is None:
                logger.warning("run_orchestration: campaign %s not found", cid)
                return {"campaign_id": cid, "status": "failed", "error": "Campaign not found"}

            sec_result = await session.execute(
                select(Section)
                .where(Section.campaign_id == _uuid.UUID(cid))
                .order_by(Section.position)
            )
            sections = list(sec_result.scalars().all())

            prod_result = await session.execute(
                select(Product)
                .where(Product.campaign_id == _uuid.UUID(cid))
                .order_by(Product.position)
            )
            products = list(prod_result.scalars().all())
    except Exception as exc:  # noqa: BLE001
        logger.warning("run_orchestration: DB load failed for %s (%s)", cid, exc)
        return {"campaign_id": cid, "status": "failed", "error": str(exc)}

    # ── 2. Generate visual brief ──────────────────────────────────────────────
    section_titles = [s.title for s in sections]
    product_names = [
        p.scraped_name or p.sku for p in products if (p.scraped_name or p.sku)
    ]

    brief_output = await generate_visual_brief(
        section_titles=section_titles,
        product_names=product_names,
        openai_api_key=settings.openai_api_key,
    )

    # ── 3. Upsert VisualBrief ─────────────────────────────────────────────────
    try:
        async with async_session_maker() as session:
            existing = await session.execute(
                select(VisualBrief).where(VisualBrief.campaign_id == _uuid.UUID(cid))
            )
            brief_row = existing.scalar_one_or_none()
            if brief_row is None:
                brief_row = VisualBrief(campaign_id=_uuid.UUID(cid))
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
            await session.commit()

            # Keep a copy of the brief values for the render step
            brief_snapshot = {
                "id": str(brief_row.id),
                "theme_name": brief_row.theme_name,
                "template_id": brief_row.template_id,
                "background_color": brief_row.background_color,
                "section_color": brief_row.section_color,
                "accent_color": brief_row.accent_color,
                "button_color": brief_row.button_color,
                "product_bg_color": brief_row.product_bg_color,
                "heading_font": brief_row.heading_font,
                "body_font": brief_row.body_font,
                "h1_size": brief_row.h1_size,
                "h2_size": brief_row.h2_size,
                "body_size": brief_row.body_size,
                "dalle_prompt": brief_row.dalle_prompt,
                "pinned_theme_id": brief_row.pinned_theme_id,
                "use_neutral_defaults": brief_row.use_neutral_defaults,
                "created_at": brief_row.created_at.isoformat() if brief_row.created_at else None,
                "updated_at": brief_row.updated_at.isoformat() if brief_row.updated_at else None,
            }

    except Exception as exc:  # noqa: BLE001
        logger.warning("run_orchestration: DB upsert failed for %s (%s)", cid, exc)
        return {"campaign_id": cid, "status": "failed", "error": str(exc)}

    # ── 4. First render with new tokens ──────────────────────────────────────
    tokens = VisualTokens(
        background_color=brief_output.background_color,
        section_background=brief_output.section_color,
        accent_color=brief_output.accent_color,
        button_color=brief_output.button_color,
        button_text_color="#FFFFFF",
        h1_size=f"{brief_output.h1_size}px",
        h2_size=f"{brief_output.h2_size}px",
        body_size=f"{brief_output.body_size}px",
        font_family=brief_output.heading_font,
        product_background=brief_output.product_bg_color,
    )

    size_kb = 0.0
    try:
        # Re-fetch campaign object (expired after first session closed)
        async with async_session_maker() as render_session:
            camp_res = await render_session.execute(
                select(Campaign).where(Campaign.id == _uuid.UUID(cid))
            )
            campaign_obj = camp_res.scalar_one_or_none()
            if campaign_obj is not None:
                render_input = _build_render_input(
                    campaign_obj, sections, products, tokens
                )
                _html, size_kb = render_campaign(render_input)
    except Exception as exc:  # noqa: BLE001
        logger.warning("run_orchestration: render failed for %s (%s)", cid, exc)

    # ── 5. Notify frontend via WebSocket ──────────────────────────────────────
    try:
        await gateway.send_progress(
            cid,
            "brief_ready",
            {
                "campaign_id": cid,
                "brief": brief_snapshot,
                "size_kb": size_kb,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("run_orchestration: WebSocket notify failed for %s (%s)", cid, exc)

    logger.info(
        "run_orchestration: done for campaign %s — theme=%s size_kb=%.1f",
        cid,
        brief_output.theme_name,
        size_kb,
    )
    return {
        "campaign_id": cid,
        "status": "done",
        "theme_name": brief_output.theme_name,
        "size_kb": size_kb,
    }
