"""
sheet_parser.py
===============

Pure header / row normalization logic shared by:
  - Google Sheet ingestion (`sheet_reader.read_sheet`)
  - File upload ingestion (Issue 6, .xlsx/.csv path)
  - Verify endpoint (Issue 2, column-presence checks)

This module has zero IO and zero external dependencies. All Google API
or file-parsing concerns live in their respective callers.
"""

from __future__ import annotations

from typing import Iterable, Optional, TypedDict


# ── Public canonical field set ────────────────────────────────────────────────

CANONICAL_FIELDS: tuple[str, ...] = (
    "section_title",
    "sku",
    "product_link",
    "priority",
    "raw_price",
    "utm_campaign",
    "button_name",
    "pack_of",
    "quantity",
    "discount",
)

REQUIRED_FIELDS: tuple[str, ...] = ("sku", "product_link")

VALID_PRIORITIES: frozenset[str] = frozenset({"high", "medium", "low"})


# ── Column aliases (lowercased) ───────────────────────────────────────────────

COLUMN_ALIASES: dict[str, str] = {
    "section": "section_title",
    "section title": "section_title",
    "section_title": "section_title",
    "sku": "sku",
    "product_link": "product_link",
    "product link": "product_link",
    "url": "product_link",
    "link": "product_link",
    "priority": "priority",
    "raw_price": "raw_price",
    "price": "raw_price",
    "raw price": "raw_price",
    "utm_campaign": "utm_campaign",
    "utm campaign": "utm_campaign",
    "campaign": "utm_campaign",
    "button_name": "button_name",
    "button name": "button_name",
    "button": "button_name",
    "cta": "button_name",
    "pack_of": "pack_of",
    "pack of": "pack_of",
    "pack": "pack_of",
    "quantity": "quantity",
    "qty": "quantity",
    "discount": "discount",
    "disc": "discount",
}


class NormalizedHeaders(TypedDict):
    """Result of normalizing a raw header row."""

    headers: list[str]            # canonical (or pass-through) header names, in input order
    canonical_to_index: dict[str, int]  # canonical name → first column index that maps to it
    missing_required: list[str]   # required canonical fields not found
    raw_to_canonical: dict[str, Optional[str]]  # raw header → canonical name (None if unknown)


def normalize_header(raw: str) -> str:
    """Map a single raw header cell to its canonical name (or trimmed lowercase fallback)."""
    key = raw.strip().lower()
    return COLUMN_ALIASES.get(key, key)


def normalize_headers(raw_headers: Iterable[str]) -> NormalizedHeaders:
    """
    Normalize a header row.

    Returns a dict so callers can both walk the canonical column list and
    answer "is `sku` present?" without re-deriving anything.
    """
    headers: list[str] = []
    canonical_to_index: dict[str, int] = {}
    raw_to_canonical: dict[str, Optional[str]] = {}

    for idx, raw in enumerate(raw_headers):
        canonical = normalize_header(str(raw))
        headers.append(canonical)
        is_known = canonical in CANONICAL_FIELDS
        raw_to_canonical[str(raw)] = canonical if is_known else None
        if is_known and canonical not in canonical_to_index:
            canonical_to_index[canonical] = idx

    missing_required = [f for f in REQUIRED_FIELDS if f not in canonical_to_index]

    return NormalizedHeaders(
        headers=headers,
        canonical_to_index=canonical_to_index,
        missing_required=missing_required,
        raw_to_canonical=raw_to_canonical,
    )


def coerce_priority(raw: Optional[str]) -> str:
    """Lowercase a priority cell; fall back to ``medium`` if unknown."""
    if not raw:
        return "medium"
    candidate = str(raw).strip().lower()
    return candidate if candidate in VALID_PRIORITIES else "medium"


def row_to_canonical_dict(
    headers: list[str], row: list,
) -> dict[str, str]:
    """
    Project a raw row (parallel to a normalized header list) into a
    ``canonical_field -> string_value`` dict. Rows shorter than the header
    are padded with empty strings; ``None`` cells become ``""``.

    Unknown header columns are dropped — callers that care about extra
    columns should consult ``NormalizedHeaders.headers`` directly.
    """
    padded = list(row) + [""] * (len(headers) - len(row))
    out: dict[str, str] = {}
    for i, header in enumerate(headers):
        if header not in CANONICAL_FIELDS:
            continue
        value = padded[i]
        out[header] = "" if value is None else str(value)
    return out
