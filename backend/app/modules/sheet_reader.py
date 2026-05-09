"""
sheet_reader.py
===============
Isolated from HTTP/DB layers.

Reads product data from a Google Spreadsheet using a service-account
credentials JSON dict and returns a list of ``ProductRecord`` instances.

Expected sheet layout (first row = headers, case-insensitive):
    section_title | sku | product_link | priority | raw_price | utm_campaign | button_name

Missing or extra columns are handled gracefully.
"""

from __future__ import annotations

import re
from typing import Optional, TypedDict

from app.modules.price_formatter import format_price
from app.modules.utm_builder import build_utm


# ── Public record type ────────────────────────────────────────────────────────

class ProductRecord(TypedDict, total=False):
    section_title: str
    sku: str
    product_link: str
    priority: str          # "high" | "medium" | "low"
    raw_price: Optional[str]
    formatted_price: Optional[str]
    utm_campaign: Optional[str]
    utm_stitched: Optional[str]
    button_name: Optional[str]


# ── Internal helpers ──────────────────────────────────────────────────────────

_SPREADSHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")
_VALID_PRIORITIES = {"high", "medium", "low"}

_COLUMN_ALIASES: dict[str, str] = {
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
}


def _extract_spreadsheet_id(sheet_url: str) -> str:
    match = _SPREADSHEET_ID_RE.search(sheet_url)
    if not match:
        raise ValueError(
            f"Could not extract spreadsheet ID from URL: {sheet_url!r}. "
            "Expected a URL like https://docs.google.com/spreadsheets/d/<ID>/..."
        )
    return match.group(1)


def _normalise_header(raw: str) -> str:
    return _COLUMN_ALIASES.get(raw.strip().lower(), raw.strip().lower())


def _build_product_record(
    row_dict: dict[str, str],
) -> ProductRecord:
    """Convert a raw header→value dict into a typed ``ProductRecord``."""

    section_title = row_dict.get("section_title", "").strip() or "Default"
    sku = row_dict.get("sku", "").strip()
    product_link = row_dict.get("product_link", "").strip()
    raw_priority = row_dict.get("priority", "medium").strip().lower()
    priority = raw_priority if raw_priority in _VALID_PRIORITIES else "medium"
    raw_price = row_dict.get("raw_price", "").strip() or None
    formatted_price = format_price(raw_price) if raw_price else None
    utm_campaign = row_dict.get("utm_campaign", "").strip() or None
    utm_stitched = build_utm(utm_campaign, product_link) if product_link else None
    button_name = row_dict.get("button_name", "").strip() or None

    return ProductRecord(
        section_title=section_title,
        sku=sku,
        product_link=product_link,
        priority=priority,
        raw_price=raw_price,
        formatted_price=formatted_price,
        utm_campaign=utm_campaign,
        utm_stitched=utm_stitched,
        button_name=button_name,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def read_sheet(sheet_url: str, credentials_json: dict) -> list[ProductRecord]:
    """
    Fetch all rows from the first visible sheet in a Google Spreadsheet.

    Parameters
    ----------
    sheet_url:
        Full URL of the Google Spreadsheet, e.g.
        ``https://docs.google.com/spreadsheets/d/<ID>/edit#gid=0``.
    credentials_json:
        Service-account credentials as a dict (loaded from the JSON key file).

    Returns
    -------
    list[ProductRecord]
        One entry per data row (header row excluded).  Rows where *both*
        ``sku`` and ``product_link`` are empty are skipped.

    Raises
    ------
    ValueError
        If the spreadsheet ID cannot be extracted from *sheet_url*.
    google.auth.exceptions.TransportError
        On network failure communicating with Google APIs.
    googleapiclient.errors.HttpError
        On API-level errors (e.g. 403 Forbidden, 404 Not Found).
    """
    # Import here so the module can be imported without these packages installed
    # in environments that don't need Google Sheets support.
    from google.oauth2 import service_account
    from googleapiclient.discovery import build as google_build

    spreadsheet_id = _extract_spreadsheet_id(sheet_url)

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = service_account.Credentials.from_service_account_info(
        credentials_json, scopes=scopes
    )

    service = google_build("sheets", "v4", credentials=creds, cache_discovery=False)
    sheets_api = service.spreadsheets()  # type: ignore[attr-defined]

    # Get spreadsheet metadata to find the first sheet name
    meta = sheets_api.get(spreadsheetId=spreadsheet_id).execute()
    first_sheet_title: str = meta["sheets"][0]["properties"]["title"]

    # Fetch all data from the first sheet
    result = (
        sheets_api.values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=first_sheet_title,
            valueRenderOption="UNFORMATTED_VALUE",
            dateTimeRenderOption="FORMATTED_STRING",
        )
        .execute()
    )

    raw_rows: list[list] = result.get("values", [])
    if not raw_rows:
        return []

    # First row is headers
    header_row = [_normalise_header(str(cell)) for cell in raw_rows[0]]

    records: list[ProductRecord] = []
    for row in raw_rows[1:]:
        # Pad short rows with empty strings
        padded = list(row) + [""] * (len(header_row) - len(row))
        row_dict: dict[str, str] = {
            header_row[i]: str(padded[i]) if padded[i] is not None else ""
            for i in range(len(header_row))
        }

        # Skip entirely empty rows
        sku = row_dict.get("sku", "").strip()
        product_link = row_dict.get("product_link", "").strip()
        if not sku and not product_link:
            continue

        records.append(_build_product_record(row_dict))

    return records
