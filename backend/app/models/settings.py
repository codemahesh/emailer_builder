import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.user import Base


class GlobalSettings(Base):
    """Single-row table — always upsert on id=SINGLETON_ID."""
    __tablename__ = "global_settings"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)  # always 1

    # Headers & Footers
    header_html: Mapped[str] = mapped_column(Text, default="")
    footer_html: Mapped[str] = mapped_column(
        Text,
        default='<div style="text-align:center;padding:16px;font-size:12px;color:#8A94A6;">{{unsubscribe_link}} | {{view_in_browser}}</div>',
    )

    # Brand Tokens
    primary_color: Mapped[str] = mapped_column(String(20), default="#2E5BFF")
    secondary_color: Mapped[str] = mapped_column(String(20), default="#1F2937")
    heading_font: Mapped[str] = mapped_column(String(255), default="Inter, Arial, sans-serif")
    body_font: Mapped[str] = mapped_column(String(255), default="Inter, Arial, sans-serif")

    # UTM
    global_utm_prefix: Mapped[str] = mapped_column(String(500), default="")

    # Service account (read-only display)
    service_account_email: Mapped[str] = mapped_column(
        String(255), default="builder@project.iam.gserviceaccount.com"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class KeywordMapping(Base):
    """Keyword -> icon mapping for Table of Contents."""
    __tablename__ = "keyword_mapping"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    keyword: Mapped[str] = mapped_column(String(100), unique=True)
    icon: Mapped[str] = mapped_column(String(50))  # icon name from icon set
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
