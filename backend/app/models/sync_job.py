import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class SyncJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    partial = "partial"


class SyncJob(Base):
    __tablename__ = "sync_job"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "full" or "fast"
    status: Mapped[SyncJobStatus] = mapped_column(
        SAEnum(SyncJobStatus, name="syncjobstatus"),
        default=SyncJobStatus.queued,
        nullable=False,
        server_default=SyncJobStatus.queued.value,
    )
    total_products: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_products: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_products: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
