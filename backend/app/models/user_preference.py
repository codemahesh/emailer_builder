"""
user_preference.py
==================
SQLAlchemy model for UserPreference — editor preference signals for AI personalization.

Issue 17
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class UserPreference(Base):
    __tablename__ = "user_preference"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    editor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    signal_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "explicit_positive" | "explicit_negative" | "implicit_accept" | "implicit_revert"
    asset_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g. "banner", "theme", "layout", "template"
    signal_value: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # e.g. theme name, layout type
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("campaign.id", ondelete="SET NULL"), nullable=True
    )
    weight: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False, server_default="1.0"
    )  # implicit_revert gets weight=3.0
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
