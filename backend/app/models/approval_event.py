"""
approval_event.py
=================
SQLAlchemy model for ApprovalEvent — reviewer approval records.

Issue 22
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class ApprovalEvent(Base):
    __tablename__ = "approval_event"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    viewport_confirmed: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "desktop" | "mobile" | "both"
