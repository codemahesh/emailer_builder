import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, field_validator
from app.models.campaign import CampaignStatus


class CampaignBase(BaseModel):
    name: str
    sheet_url: str = ""


class CampaignCreate(CampaignBase):
    name: str
    sheet_url: str = ""

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Campaign name cannot be empty")
        return v.strip()


class CampaignUpdate(BaseModel):
    name: str | None = None
    sheet_url: str | None = None
    status: CampaignStatus | None = None


class CampaignOwnerRead(BaseModel):
    id: uuid.UUID
    email: str

    model_config = {"from_attributes": True}


class CampaignRead(CampaignBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime] = None
    owner: CampaignOwnerRead | None = None

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    items: list[CampaignRead]
    total: int
