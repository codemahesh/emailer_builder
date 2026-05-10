import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel

from app.models.product import ProductPriority


# ── Sheet verify ──────────────────────────────────────────────────────────────

class VerifyRequest(BaseModel):
    sheet_url: str


class VerifyResponse(BaseModel):
    ok: bool
    error_code: Optional[str] = None      # INVALID_URL | NOT_FOUND | NOT_SHARED | EMPTY_SHEET | MISSING_COLUMNS
    headers_found: list[str] = []
    missing_columns: list[str] = []
    row_count: int = 0
    sheet_title: str = ""
    tab_count: int = 0


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


# ── Import (Update List) ─────────────────────────────────────────────────────

class ImportRequest(BaseModel):
    phase: Literal["preflight", "commit"]


class ImportPreflightResponse(BaseModel):
    added: int = 0
    removed: int = 0
    updated: int = 0
    unchanged: int = 0
    rescrape_count: int = 0
    has_changes: bool = False


class ImportCommitResponse(BaseModel):
    job_id: str
    status: str   # "queued"


# ── File upload ──────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    ok: bool
    error_code: Optional[str] = None   # same codes as VerifyResponse + INVALID_TYPE | PARSE_ERROR | TOO_MANY_ROWS
    headers_found: list[str] = []
    missing_columns: list[str] = []
    row_count: int = 0
    version_id: Optional[str] = None   # UUID of the SheetVersion written on success
    imported_count: int = 0


# ── Sheet preview ─────────────────────────────────────────────────────────────

class SheetPreviewResponse(BaseModel):
    version: int
    fetched_at: str          # ISO datetime of the snapshot's imported_at
    row_count: int           # total rows in this version (un-paginated)
    headers: list[str]       # canonical column names derived from the data
    rows: list[dict[str, Any]]  # decoded row dicts for the requested page
    has_more: bool
    offset: int
    limit: int


# ── Sheet version ─────────────────────────────────────────────────────────────

class SheetVersionRead(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    version: int
    source: str
    source_ref: str
    imported_at: datetime
    imported_by: Optional[uuid.UUID] = None
    row_count: int
    checksum: str

    model_config = {"from_attributes": True}


# ── Replace image ─────────────────────────────────────────────────────────────

class ReplaceImagePayload(BaseModel):
    image_url: str
