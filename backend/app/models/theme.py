from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class Theme(Base):
    __tablename__ = "theme"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    background_color: Mapped[str] = mapped_column(String(20), default="#FFFFFF")
    section_color: Mapped[str] = mapped_column(String(20), default="#F8F9FB")
    accent_color: Mapped[str] = mapped_column(String(20), default="#2E5BFF")
    button_color: Mapped[str] = mapped_column(String(20), default="#2E5BFF")
    product_bg_color: Mapped[str] = mapped_column(String(20), default="#F8F9FB")
    heading_font: Mapped[str] = mapped_column(
        String(255), default="Inter, Arial, sans-serif"
    )
    body_font: Mapped[str] = mapped_column(
        String(255), default="Inter, Arial, sans-serif"
    )
    h1_size: Mapped[int] = mapped_column(Integer, default=28)
    h2_size: Mapped[int] = mapped_column(Integer, default=20)
    body_size: Mapped[int] = mapped_column(Integer, default=14)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
