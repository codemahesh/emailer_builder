from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class GlobalSettingsRead(BaseModel):
    id: int
    header_html: str
    footer_html: str
    primary_color: str
    secondary_color: str
    heading_font: str
    body_font: str
    global_utm_prefix: str
    service_account_email: str
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class GlobalSettingsUpdate(BaseModel):
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    heading_font: Optional[str] = None
    body_font: Optional[str] = None
    global_utm_prefix: Optional[str] = None
    service_account_email: Optional[str] = None


class KeywordMappingRead(BaseModel):
    id: str
    keyword: str
    icon: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class KeywordMappingCreate(BaseModel):
    keyword: str
    icon: str


class KeywordMappingUpdate(BaseModel):
    keyword: Optional[str] = None
    icon: Optional[str] = None
