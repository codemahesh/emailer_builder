import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class VisualBrief(Base):
    __tablename__ = "visual_brief"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"), unique=True
    )

    # Theme
    theme_name: Mapped[str] = mapped_column(String(255), default="Modern Minimal")
    template_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Palette
    background_color: Mapped[str] = mapped_column(String(20), default="#FFFFFF")
    section_color: Mapped[str] = mapped_column(String(20), default="#F8F9FB")
    accent_color: Mapped[str] = mapped_column(String(20), default="#2E5BFF")
    button_color: Mapped[str] = mapped_column(String(20), default="#2E5BFF")
    product_bg_color: Mapped[str] = mapped_column(String(20), default="#F8F9FB")

    # Typography
    heading_font: Mapped[str] = mapped_column(
        String(255), default="Inter, Arial, sans-serif"
    )
    body_font: Mapped[str] = mapped_column(
        String(255), default="Inter, Arial, sans-serif"
    )
    h1_size: Mapped[int] = mapped_column(Integer, default=28)
    h2_size: Mapped[int] = mapped_column(Integer, default=20)
    body_size: Mapped[int] = mapped_column(Integer, default=14)

    # Generation
    dalle_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pinned_theme_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    use_neutral_defaults: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
