"""
sheet_verifier.py
=================

Read-only sheet verification used by the /sheet/verify endpoint.

Accepts an optional ``_sheets_api`` argument so tests can inject a mock
Google Sheets API client without patching the google namespace packages.
"""

from __future__ import annotations

import re
from typing import Any, Optional, TypedDict

from app.modules.sheet_parser import REQUIRED_FIELDS, normalize_headers


_SPREADSHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")


class VerifyResult(TypedDict):
    ok: bool
    error_code: Optional[str]          # INVALID_URL|NOT_FOUND|NOT_SHARED|EMPTY_SHEET|MISSING_COLUMNS
    headers_found: list[str]           # canonical names of recognised columns in the sheet
    missing_columns: list[str]         # required fields not found
    row_count: int                     # data rows (header excluded)
    sheet_title: str                   # first tab title
    tab_count: int                     # total number of tabs


def _make_result(
    *,
    ok: bool,
    error_code: Optional[str] = None,
    headers_found: Optional[list[str]] = None,
    missing_columns: Optional[list[str]] = None,
    row_count: int = 0,
    sheet_title: str = "",
    tab_count: int = 0,
) -> VerifyResult:
    return VerifyResult(
        ok=ok,
        error_code=error_code,
        headers_found=headers_found or [],
        missing_columns=missing_columns or [],
        row_count=row_count,
        sheet_title=sheet_title,
        tab_count=tab_count,
    )


def verify_sheet(
    sheet_url: str,
    credentials_json: dict,
    *,
    _sheets_api: Any = None,
) -> VerifyResult:
    """
    Verify that a Google Sheet URL is accessible and contains the required columns.

    Parameters
    ----------
    sheet_url:        Full Google Sheets sharing URL.
    credentials_json: Service-account credentials dict (unused when ``_sheets_api``
                      is supplied, e.g. in tests).
    _sheets_api:      Optional pre-built ``service.spreadsheets()`` client — inject
                      a mock in tests to skip real network calls.

    Returns
    -------
    VerifyResult
        ``ok=True`` on success.  On failure ``error_code`` is one of:
        ``INVALID_URL``, ``NOT_FOUND``, ``NOT_SHARED``, ``EMPTY_SHEET``,
        ``MISSING_COLUMNS``.
    """
    # ── Step 1: URL format pre-check (no API call) ────────────────────────────
    match = _SPREADSHEET_ID_RE.search(sheet_url.strip())
    if not match:
        return _make_result(ok=False, error_code="INVALID_URL")

    spreadsheet_id = match.group(1)

    # ── Step 2: Build API client if not injected ──────────────────────────────
    if _sheets_api is None:
        from google.oauth2 import service_account  # type: ignore[import]
        from googleapiclient.discovery import build as google_build  # type: ignore[import]

        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds = service_account.Credentials.from_service_account_info(
            credentials_json, scopes=scopes
        )
        service = google_build("sheets", "v4", credentials=creds, cache_discovery=False)
        _sheets_api = service.spreadsheets()

    # ── Step 3: Fetch spreadsheet metadata ────────────────────────────────────
    try:
        meta = _sheets_api.get(spreadsheetId=spreadsheet_id).execute()
    except Exception as exc:
        status = getattr(getattr(exc, "resp", None), "status", None)
        if status == 404:
            return _make_result(ok=False, error_code="NOT_FOUND")
        if status == 403:
            return _make_result(ok=False, error_code="NOT_SHARED")
        raise

    sheets = meta.get("sheets", [])
    tab_count = len(sheets)
    first_sheet_title: str = (
        sheets[0]["properties"]["title"] if sheets else "Sheet1"
    )

    # ── Step 4: Fetch cell values ─────────────────────────────────────────────
    values_result = _sheets_api.values().get(
        spreadsheetId=spreadsheet_id,
        range=first_sheet_title,
        valueRenderOption="UNFORMATTED_VALUE",
    ).execute()

    raw_rows: list[list] = values_result.get("values", [])

    if not raw_rows:
        return _make_result(
            ok=False,
            error_code="EMPTY_SHEET",
            sheet_title=first_sheet_title,
            tab_count=tab_count,
        )

    # ── Step 5: Column validation ─────────────────────────────────────────────
    normalized = normalize_headers([str(cell) for cell in raw_rows[0]])
    headers_found = [
        name
        for name in normalized["canonical_to_index"]
    ]
    missing = normalized["missing_required"]
    data_row_count = max(0, len(raw_rows) - 1)

    if missing:
        return _make_result(
            ok=False,
            error_code="MISSING_COLUMNS",
            headers_found=headers_found,
            missing_columns=missing,
            row_count=data_row_count,
            sheet_title=first_sheet_title,
            tab_count=tab_count,
        )

    # ── Step 6: EMPTY_SHEET (headers OK, but no data rows) ───────────────────
    if data_row_count == 0:
        return _make_result(
            ok=False,
            error_code="EMPTY_SHEET",
            headers_found=headers_found,
            row_count=0,
            sheet_title=first_sheet_title,
            tab_count=tab_count,
        )

    return _make_result(
        ok=True,
        headers_found=headers_found,
        row_count=data_row_count,
        sheet_title=first_sheet_title,
        tab_count=tab_count,
    )
