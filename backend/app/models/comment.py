"""
comment.py
==========
SQLAlchemy model for Comment — reviewer comments on campaign sections.

Issue 21
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # section.id as string — survives snapshot restores
    author_name: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("comment.id", ondelete="SET NULL"), nullable=True
    )  # for replies
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
