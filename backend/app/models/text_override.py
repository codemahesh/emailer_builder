"""
text_override.py
================
SQLAlchemy model for TextOverride — manual text replacements for product fields.

Issue 12
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class TextOverride(Base):
    __tablename__ = "text_override"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # product.id as string
    field: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "product_name" | "button_label"
    override_value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
