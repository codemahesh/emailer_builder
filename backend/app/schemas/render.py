"""
render.py
=========
Pydantic schemas for the campaign render endpoint.
"""

from pydantic import BaseModel


class RenderResponse(BaseModel):
    html: str
    size_kb: float
    section_count: int
    product_count: int
