"""
visual_brief.py
===============
Pydantic schemas for the VisualBrief resource.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class VisualBriefRead(BaseModel):
    id: str
    campaign_id: str
    theme_name: str
    template_id: Optional[str]
    background_color: str
    section_color: str
    accent_color: str
    button_color: str
    product_bg_color: str
    heading_font: str
    body_font: str
    h1_size: int
    h2_size: int
    body_size: int
    dalle_prompt: Optional[str]
    pinned_theme_id: Optional[str]
    use_neutral_defaults: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
