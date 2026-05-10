"""
test_sheet_verifier.py
======================
Unit tests for app.modules.sheet_verifier.verify_sheet.

All five error codes are exercised against a mock Sheets API client
injected via the ``_sheets_api`` keyword argument — no real network
calls or Google package imports required.
"""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.modules.sheet_verifier import verify_sheet


# ── Fixtures ──────────────────────────────────────────────────────────────────

_URL = "https://docs.google.com/spreadsheets/d/FAKE_ID/edit#gid=0"
_CREDS = {}


def _make_api(*, meta: dict | None = None, values: list[list] | None = None, get_error=None):
    """Build a minimal mock Sheets API client."""
    api = MagicMock()

    if get_error is not None:
        # Simulate HttpError on spreadsheets.get()
        api.get.return_value.execute.side_effect = get_error
    else:
        api.get.return_value.execute.return_value = meta or {
            "sheets": [{"properties": {"title": "Sheet1"}}]
        }
        api.values.return_value.get.return_value.execute.return_value = {
            "values": values if values is not None else []
        }

    return api


def _http_error(status_code: int) -> Exception:
    """Create a minimal exception that looks like a googleapiclient HttpError."""
    exc = Exception("Simulated HTTP error")
    exc.resp = MagicMock()        # type: ignore[attr-defined]
    exc.resp.status = status_code  # type: ignore[attr-defined]
    return exc


# ── Error code tests ──────────────────────────────────────────────────────────

class TestInvalidUrl:
    def test_missing_spreadsheets_path(self):
        result = verify_sheet("https://docs.google.com/not-a-sheet", _CREDS)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_URL"

    def test_empty_string(self):
        result = verify_sheet("", _CREDS)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_URL"

    def test_plain_text(self):
        result = verify_sheet("just some text", _CREDS)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_URL"

    def test_invalid_url_returns_zero_fields(self):
        result = verify_sheet("not-a-url", _CREDS)
        assert result["row_count"] == 0
        assert result["sheet_title"] == ""
        assert result["tab_count"] == 0


class TestNotFound:
    def test_404_returns_not_found(self):
        api = _make_api(get_error=_http_error(404))
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["ok"] is False
        assert result["error_code"] == "NOT_FOUND"

    def test_not_found_has_no_headers(self):
        api = _make_api(get_error=_http_error(404))
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["headers_found"] == []
        assert result["missing_columns"] == []


class TestNotShared:
    def test_403_returns_not_shared(self):
        api = _make_api(get_error=_http_error(403))
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["ok"] is False
        assert result["error_code"] == "NOT_SHARED"


class TestEmptySheet:
    def test_no_rows_at_all(self):
        api = _make_api(values=[])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_SHEET"

    def test_header_row_only_no_data(self):
        api = _make_api(values=[["sku", "product_link"]])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_SHEET"
        assert result["row_count"] == 0

    def test_empty_sheet_returns_sheet_title(self):
        api = _make_api(
            meta={"sheets": [{"properties": {"title": "Products"}}]},
            values=[],
        )
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["sheet_title"] == "Products"

    def test_empty_sheet_returns_tab_count(self):
        api = _make_api(
            meta={"sheets": [
                {"properties": {"title": "Sheet1"}},
                {"properties": {"title": "Sheet2"}},
            ]},
            values=[],
        )
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["tab_count"] == 2


class TestMissingColumns:
    def test_sku_missing(self):
        api = _make_api(values=[
            ["product_link"],
            ["https://example.com/1"],
        ])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["ok"] is False
        assert result["error_code"] == "MISSING_COLUMNS"
        assert "sku" in result["missing_columns"]

    def test_product_link_missing(self):
        api = _make_api(values=[
            ["sku"],
            ["SKU-001"],
        ])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["ok"] is False
        assert result["error_code"] == "MISSING_COLUMNS"
        assert "product_link" in result["missing_columns"]

    def test_both_required_missing(self):
        api = _make_api(values=[
            ["price", "button_name"],
            ["₹999", "Buy Now"],
        ])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert set(result["missing_columns"]) == {"sku", "product_link"}

    def test_missing_columns_includes_row_count(self):
        api = _make_api(values=[
            ["sku"],
            ["SKU-1"],
            ["SKU-2"],
        ])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["row_count"] == 2

    def test_alias_columns_satisfy_requirements(self):
        # "link" is an alias for "product_link"
        api = _make_api(values=[
            ["sku", "link"],
            ["SKU-001", "https://example.com"],
        ])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["ok"] is True
        assert result["error_code"] is None


class TestSuccess:
    def test_basic_success(self):
        api = _make_api(values=[
            ["sku", "product_link"],
            ["SKU-001", "https://example.com/1"],
        ])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["ok"] is True
        assert result["error_code"] is None

    def test_success_returns_row_count(self):
        api = _make_api(values=[
            ["sku", "product_link"],
            ["SKU-001", "https://example.com/1"],
            ["SKU-002", "https://example.com/2"],
            ["SKU-003", "https://example.com/3"],
        ])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["row_count"] == 3

    def test_success_returns_sheet_title(self):
        api = _make_api(
            meta={"sheets": [{"properties": {"title": "Q4 Catalog"}}]},
            values=[
                ["sku", "product_link"],
                ["SKU-001", "https://example.com/1"],
            ],
        )
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["sheet_title"] == "Q4 Catalog"

    def test_success_returns_tab_count(self):
        api = _make_api(
            meta={"sheets": [
                {"properties": {"title": "Sheet1"}},
                {"properties": {"title": "Instructions"}},
            ]},
            values=[
                ["sku", "product_link"],
                ["SKU-001", "https://example.com/1"],
            ],
        )
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["tab_count"] == 2

    def test_success_returns_detected_headers(self):
        api = _make_api(values=[
            ["sku", "product_link", "price"],
            ["SKU-001", "https://example.com/1", "₹999"],
        ])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert "sku" in result["headers_found"]
        assert "product_link" in result["headers_found"]
        assert "raw_price" in result["headers_found"]

    def test_success_missing_columns_empty(self):
        api = _make_api(values=[
            ["sku", "product_link"],
            ["SKU-001", "https://example.com/1"],
        ])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["missing_columns"] == []

    def test_case_insensitive_headers(self):
        api = _make_api(values=[
            ["SKU", "Product_Link"],
            ["SKU-001", "https://example.com/1"],
        ])
        result = verify_sheet(_URL, _CREDS, _sheets_api=api)
        assert result["ok"] is True
