import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.product import ProductPriority


# ── Sync job / status ─────────────────────────────────────────────────────────

class SyncJobResponse(BaseModel):
    """Response returned when a sync job is enqueued."""
    job_id: str
    status: str  # "queued"


class SyncStatusResponse(BaseModel):
    """Current sync status, sourced from Redis or the latest SyncJob row."""
    status: str           # "queued" | "running" | "completed" | "failed" | "partial" | "idle"
    total: int = 0        # total products expected from the sheet
    processed: int = 0    # products successfully imported
    failed: int = 0       # products that could not be imported
    last_synced: Optional[str] = None   # ISO datetime of last completed sync
    error_message: Optional[str] = None  # human-readable error (status=failed only)


# ── Product / Section reads ───────────────────────────────────────────────────

class SectionRead(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    title: str
    position: int
    locked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductRead(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    section_id: Optional[uuid.UUID] = None
    sku: str
    product_link: str
    priority: ProductPriority
    raw_price: Optional[str] = None
    formatted_price: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_stitched: Optional[str] = None
    button_name: Optional[str] = None
    scraped_name: Optional[str] = None
    scraped_image_url: Optional[str] = None
    processed_image_url: Optional[str] = None
    scrape_failed: bool
    position: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Replace image ─────────────────────────────────────────────────────────────

class ReplaceImagePayload(BaseModel):
    image_url: str
