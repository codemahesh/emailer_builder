"""
audit.py
========
FastAPI router for pre-flight HTML auditing (Issue 19).

Endpoints
---------
POST /campaigns/{campaign_id}/audit
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
from app.models.user import User
from app.modules.preflight_auditor import AuditReport, audit

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class AuditBody(BaseModel):
    html: Optional[str] = None


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


async def _render_campaign_html(
    campaign_id: uuid.UUID,
    db: AsyncSession,
    campaign: Campaign,
) -> str:
    """Render campaign to HTML using the same logic as render.py."""
    from app.models.product import Product, Section
    from app.modules.mjml_renderer import render_campaign
    from app.routers.render import _build_render_input, _load_products, _load_sections

    sections = await _load_sections(campaign_id, db)
    products = await _load_products(campaign_id, db)
    render_input = _build_render_input(campaign, sections, products)

    try:
        html, _ = render_campaign(render_input)
        return html
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Render failed: {exc}",
        ) from exc


def _audit_report_to_dict(report: AuditReport) -> dict[str, Any]:
    return {
        "items": [
            {
                "check": item.check,
                "status": item.status,
                "message": item.message,
            }
            for item in report.items
        ],
        "size_kb": report.size_kb,
        "has_hard_stops": report.has_hard_stops,
        "minified_html": report.minified_html,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/campaigns/{campaign_id}/audit")
async def audit_campaign(
    campaign_id: uuid.UUID,
    body: AuditBody,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """
    Run pre-flight audit checks on campaign HTML.

    If `html` is provided in the request body, audit that HTML directly.
    Otherwise, renders the campaign and audits the result.

    Returns AuditReport as JSON.
    """
    campaign = await _get_campaign_or_404(campaign_id, current_user, db)

    if body.html:
        html_to_audit = body.html
    else:
        html_to_audit = await _render_campaign_html(campaign_id, db, campaign)

    report = audit(html_to_audit)

    logger.info(
        "audit_campaign: campaign=%s size_kb=%.2f has_hard_stops=%s by=%s",
        campaign_id,
        report.size_kb,
        report.has_hard_stops,
        current_user.id,
    )

    return _audit_report_to_dict(report)
