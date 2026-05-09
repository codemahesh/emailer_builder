"""
manual_asset_override.py
========================
ManualAssetOverride — validates and stores manual image replacements.

Public interface:
  apply_override(db, campaign_id, target_type, target_id, override_url, created_by) → ManualOverride
  revert_override(db, campaign_id, target_type, target_id) → None
  get_overrides(db, campaign_id) → list[ManualOverride]
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.manual_override import ManualOverride

logger = logging.getLogger(__name__)

_IMAGE_CONTENT_TYPE_PREFIXES = (
    "image/",
    "application/octet-stream",  # some CDNs serve images with this type
)


async def _validate_image_url(url: str) -> None:
    """
    Validate that the given URL points to an image resource.

    Performs an HTTP HEAD request with a 2-second timeout.
    Raises ValueError if the Content-Type is not an image type.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0, follow_redirects=True) as client:
            response = await client.head(url)
            content_type = response.headers.get("content-type", "")
            # Strip parameters (e.g. "image/jpeg; charset=utf-8" → "image/jpeg")
            mime_type = content_type.split(";")[0].strip().lower()
            if not mime_type.startswith("image/"):
                raise ValueError(
                    f"URL does not point to an image resource. "
                    f"Content-Type: '{content_type}' for URL: {url}"
                )
    except httpx.TimeoutException as exc:
        raise ValueError(
            f"Timeout while validating image URL (2s limit): {url}"
        ) from exc
    except httpx.RequestError as exc:
        raise ValueError(
            f"Failed to reach URL for image validation: {url} — {exc}"
        ) from exc


async def apply_override(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    target_type: str,
    target_id: Optional[str],
    override_url: str,
    created_by: Optional[uuid.UUID] = None,
) -> ManualOverride:
    """
    Validate the override URL is an image, then upsert a ManualOverride row.

    Deletes any existing ManualOverride matching (campaign_id, target_type, target_id)
    before inserting the new one.

    Parameters
    ----------
    db:
        Active async DB session.
    campaign_id:
        UUID of the owning campaign.
    target_type:
        One of "hero_banner", "offer_strip", "product_image".
    target_id:
        The product.id or section.id as a string, or None for whole-campaign targets.
    override_url:
        URL of the replacement image.
    created_by:
        UUID of the user performing the override, or None.

    Returns
    -------
    ManualOverride
        The newly created override row.

    Raises
    ------
    ValueError
        If the URL does not resolve to an image resource.
    """
    # Validate the URL resolves to an image
    await _validate_image_url(override_url)

    # Delete any existing matching override (upsert = delete + insert)
    await db.execute(
        delete(ManualOverride).where(
            ManualOverride.campaign_id == campaign_id,
            ManualOverride.target_type == target_type,
            ManualOverride.target_id == target_id,
        )
    )
    await db.flush()

    # Insert new override
    override = ManualOverride(
        campaign_id=campaign_id,
        target_type=target_type,
        target_id=target_id,
        override_url=override_url,
        created_by=created_by,
    )
    db.add(override)
    await db.flush()
    await db.refresh(override)

    logger.info(
        "apply_override: campaign=%s target_type=%s target_id=%s url=%s by=%s",
        campaign_id,
        target_type,
        target_id,
        override_url,
        created_by,
    )
    return override


async def revert_override(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    target_type: str,
    target_id: Optional[str],
) -> None:
    """
    Delete a ManualOverride row matching the given campaign/target_type/target_id.

    No-op if no matching row exists.
    """
    await db.execute(
        delete(ManualOverride).where(
            ManualOverride.campaign_id == campaign_id,
            ManualOverride.target_type == target_type,
            ManualOverride.target_id == target_id,
        )
    )
    await db.flush()
    logger.info(
        "revert_override: campaign=%s target_type=%s target_id=%s",
        campaign_id,
        target_type,
        target_id,
    )


async def get_overrides(
    db: AsyncSession,
    campaign_id: uuid.UUID,
) -> list[ManualOverride]:
    """
    Return all ManualOverride rows for a campaign, ordered by created_at ascending.
    """
    result = await db.execute(
        select(ManualOverride)
        .where(ManualOverride.campaign_id == campaign_id)
        .order_by(ManualOverride.created_at)
    )
    return list(result.scalars().all())
