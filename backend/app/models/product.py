import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, Select, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class Section(Base):
    __tablename__ = "section"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProductPriority(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Product(Base):
    __tablename__ = "product"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("section.id", ondelete="SET NULL"), nullable=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    product_link: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[ProductPriority] = mapped_column(
        SAEnum(ProductPriority, name="productpriority"),
        default=ProductPriority.medium,
        nullable=False,
        server_default=ProductPriority.medium.value,
    )
    raw_price: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    formatted_price: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_stitched: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    button_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scraped_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scraped_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pack_of: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    discount: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scrape_failed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @classmethod
    def active(cls) -> "Select":
        """Return a Select filtered to non-soft-deleted products."""
        return select(cls).where(cls.deleted_at.is_(None))
