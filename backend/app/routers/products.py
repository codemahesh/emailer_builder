"""
products.py
===========
FastAPI router for product image management.

Endpoints
---------
PATCH /campaigns/{campaign_id}/products/{product_id}/replace-image
    Replace the product image with a URL or uploaded file.

POST  /campaigns/{campaign_id}/products/{product_id}/revert-image
    Revert image to the coming-soon placeholder.
"""

from __future__ import annotations

import logging
import mimetypes
import uuid
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.campaign import Campaign
from app.models.manual_override import ManualOverride
from app.models.product import Product
from app.models.user import User
from app.modules.image_store import image_store
from app.schemas.sync import ProductPatchRequest, ProductRead

logger = logging.getLogger(__name__)

router = APIRouter()

_COMING_SOON_URL = "/static/coming-soon.svg"
_ALLOWED_MIME_PREFIXES = ("image/",)
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_campaign_or_404(
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


async def _get_product_or_404(
    product_id: uuid.UUID,
    campaign_id: uuid.UUID,
    session: AsyncSession,
) -> Product:
    result = await session.execute(
        Product.active().where(
            Product.id == product_id,
            Product.campaign_id == campaign_id,
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


def _is_image_mime(mime: str) -> bool:
    return any(mime.lower().startswith(p) for p in _ALLOWED_MIME_PREFIXES)


def _ext_from_mime(mime: str) -> str:
    """Return a file extension for the given MIME type (e.g. 'jpg')."""
    mapping = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/svg+xml": "svg",
        "image/avif": "avif",
        "image/tiff": "tiff",
    }
    if mime.lower() in mapping:
        return mapping[mime.lower()]
    # Fallback: use mimetypes stdlib
    ext = mimetypes.guess_extension(mime.split(";")[0].strip())
    return (ext or ".bin").lstrip(".")


# ── Endpoints ─────────────────────────────────────────────────────────────────


_TEXT_FIELD_TO_TARGET_TYPE: dict[str, str] = {
    "formatted_price": "product_price",
    "scraped_name": "product_description",
    "pack_of": "product_pack_of",
    "quantity": "product_quantity",
    "discount": "product_discount",
}


@router.patch(
    "/{campaign_id}/products/{product_id}",
    response_model=ProductRead,
)
async def patch_product_text_fields(
    campaign_id: uuid.UUID,
    product_id: uuid.UUID,
    body: ProductPatchRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> Product:
    """Partially update editable text fields on a product and record ManualOverride rows."""
    await _get_campaign_or_404(campaign_id, user, session)
    product = await _get_product_or_404(product_id, campaign_id, session)

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field must be provided.",
        )

    for field, value in updates.items():
        setattr(product, field, value or None)
        target_type = _TEXT_FIELD_TO_TARGET_TYPE[field]
        await session.execute(
            delete(ManualOverride).where(
                ManualOverride.campaign_id == campaign_id,
                ManualOverride.target_type == target_type,
                ManualOverride.target_id == str(product_id),
            )
        )
        session.add(
            ManualOverride(
                campaign_id=campaign_id,
                target_type=target_type,
                target_id=str(product_id),
                override_url=value,
                created_by=user.id,
            )
        )

    await session.flush()
    await session.refresh(product)
    return product


@router.patch(
    "/{campaign_id}/products/{product_id}/replace-image",
    response_model=ProductRead,
)
async def replace_product_image(
    campaign_id: uuid.UUID,
    product_id: uuid.UUID,
    image_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> Product:
    """Replace the image for a product.

    Accepts either a URL (JSON body ``{"image_url": "..."}`` or form field)
    or a multipart file upload.  Exactly one of the two must be provided.
    """
    await _get_campaign_or_404(campaign_id, user, session)
    product = await _get_product_or_404(product_id, campaign_id, session)

    if not image_url and (file is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either 'image_url' or a file upload.",
        )

    image_bytes: bytes
    file_ext: str

    if file is not None:
        # ── File upload path ───────────────────────────────────────────────
        content_type = file.content_type or ""
        if not _is_image_mime(content_type):
            # Try to guess from filename if content-type is ambiguous
            if file.filename:
                guessed, _ = mimetypes.guess_type(file.filename)
                if guessed and _is_image_mime(guessed):
                    content_type = guessed
                else:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Uploaded file must be an image; got '{file.content_type}'.",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Uploaded file must be an image; got '{file.content_type}'.",
                )

        image_bytes = await file.read()
        if len(image_bytes) > _MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds the 10 MB limit.",
            )
        file_ext = _ext_from_mime(content_type)

    else:
        # ── Remote URL fetch path ──────────────────────────────────────────
        assert image_url is not None  # satisfied by the check above
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(image_url.strip())
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not fetch image URL: request timed out.",
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not fetch image URL: {exc}",
            )

        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Image URL returned HTTP {resp.status_code}.",
            )

        content_type = resp.headers.get("content-type", "")
        # Strip parameters (e.g. "image/jpeg; charset=…")
        mime = content_type.split(";")[0].strip()
        if not _is_image_mime(mime):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"URL does not point to an image (Content-Type: '{content_type}').",
            )

        image_bytes = resp.content
        if len(image_bytes) > _MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Remote image exceeds the 10 MB limit.",
            )
        file_ext = _ext_from_mime(mime)

    # ── Persist to image store ─────────────────────────────────────────────
    filename = f"{product_id}.{file_ext}"
    stored_url = await image_store.write(image_bytes, filename)

    product.scraped_image_url = stored_url
    product.processed_image_url = stored_url
    product.scrape_failed = False

    # ── Record ManualOverride so the "Manual" provenance pill renders, ─────
    # ── and so the override survives Fast Sync (Issue 3 AC + Issue 11). ────
    await session.execute(
        delete(ManualOverride).where(
            ManualOverride.campaign_id == campaign_id,
            ManualOverride.target_type == "product_image",
            ManualOverride.target_id == str(product_id),
        )
    )
    session.add(
        ManualOverride(
            campaign_id=campaign_id,
            target_type="product_image",
            target_id=str(product_id),
            override_url=stored_url,
            created_by=user.id,
        )
    )

    await session.flush()
    await session.refresh(product)
    return product


@router.post(
    "/{campaign_id}/products/{product_id}/revert-image",
    response_model=ProductRead,
)
async def revert_product_image(
    campaign_id: uuid.UUID,
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> Product:
    """Revert a product image to the coming-soon placeholder."""
    await _get_campaign_or_404(campaign_id, user, session)
    product = await _get_product_or_404(product_id, campaign_id, session)

    product.scraped_image_url = _COMING_SOON_URL
    product.processed_image_url = _COMING_SOON_URL
    product.scrape_failed = True

    # Clear any matching ManualOverride so the provenance pill flips back.
    await session.execute(
        delete(ManualOverride).where(
            ManualOverride.campaign_id == campaign_id,
            ManualOverride.target_type == "product_image",
            ManualOverride.target_id == str(product_id),
        )
    )

    await session.flush()
    await session.refresh(product)
    return product
