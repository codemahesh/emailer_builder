"""
snapshot.py
===========
SQLAlchemy model for Snapshot — point-in-time captures of full campaign state.

Issue 16
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class Snapshot(Base):
    __tablename__ = "snapshot"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False
    )
    mjml_state_json: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON blob of full campaign state
    summary_chip: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "Full Sync", "Vibe Shift"
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
