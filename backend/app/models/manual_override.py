"""
manual_override.py
==================
SQLAlchemy model for ManualOverride — manual replacements for campaign assets.

``override_url`` stores the replacement value for all target types:
- For image target types (``product_image``, ``hero_banner``, etc.) it is the image URL.
- For text target types (``product_price``, ``product_description``, ``product_pack_of``,
  ``product_quantity``, ``product_discount``) it stores the literal text value verbatim.
  The field name ``override_url`` is intentionally reused rather than renamed, to avoid
  a breaking migration; a future cleanup may rename it to ``override_value``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class ManualOverride(Base):
    __tablename__ = "manual_override"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "hero_banner" | "offer_strip" | "product_image"
    target_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # product.id or section.id as string
    override_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
