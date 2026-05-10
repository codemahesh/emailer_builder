"""
test_sheet_reader.py
====================
Unit tests for app.modules.sheet_reader.read_sheet
using mocked Google Sheets API responses (no network required).
"""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.modules.sheet_reader import read_sheet


# ── Fake credentials ──────────────────────────────────────────────────────────

_FAKE_CREDS = {"type": "service_account", "project_id": "test"}
_SHEET_URL = "https://docs.google.com/spreadsheets/d/FAKE_ID/edit#gid=0"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_sheets_service(rows: list[list]) -> MagicMock:
    """
    Build a fully-mocked Google Sheets service object.

    The mock chains:
      service.spreadsheets().get().execute() → metadata
      service.spreadsheets().values().get().execute() → values response
    """
    svc = MagicMock()

    # metadata call
    svc.spreadsheets.return_value.get.return_value.execute.return_value = {
        "sheets": [{"properties": {"title": "Sheet1"}}]
    }

    # values call
    svc.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
        "values": rows
    }

    return svc


def _patched_read(rows: list[list]):
    """
    Context manager: patches google auth + discovery inside read_sheet,
    yields the result of calling read_sheet(_SHEET_URL, _FAKE_CREDS).
    """
    mock_svc = _mock_sheets_service(rows)
    mock_creds = MagicMock()

    with (
        patch(
            "google.oauth2.service_account.Credentials.from_service_account_info",
            return_value=mock_creds,
        ),
        patch(
            "googleapiclient.discovery.build",
            return_value=mock_svc,
        ),
    ):
        return read_sheet(_SHEET_URL, _FAKE_CREDS)


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestReadSheetColumnParsing:
    """Verify that all expected columns are parsed from a sheet response."""

    def test_reads_all_standard_columns(self):
        """All standard columns map to the correct ProductRecord fields."""
        rows = [
            [
                "section_title", "sku", "product_link",
                "priority", "price", "utm_campaign", "button_name",
            ],
            [
                "Electronics", "SKU-001", "https://example.com/product/1",
                "high", "₹4,999", "summer_sale", "Buy Now",
            ],
        ]
        records = _patched_read(rows)

        assert len(records) == 1
        r = records[0]
        assert r["section_title"] == "Electronics"
        assert r["sku"] == "SKU-001"
        assert r["product_link"] == "https://example.com/product/1"
        assert r["priority"] == "high"
        assert r["raw_price"] == "₹4,999"
        assert r["utm_campaign"] == "summer_sale"
        assert r["button_name"] == "Buy Now"

    def test_price_formatting_delegated(self):
        """SheetReader delegates price formatting — formatted_price is set."""
        rows = [
            ["sku", "product_link", "price"],
            ["SKU-002", "https://example.com/p/2", "4999.00"],
        ]
        records = _patched_read(rows)

        assert len(records) == 1
        assert records[0]["formatted_price"] is not None
        assert records[0]["raw_price"] == "4999.00"

    def test_utm_stitching_delegated(self):
        """UTM stitching appends utm_campaign to the product_link."""
        rows = [
            ["sku", "product_link", "utm_campaign"],
            ["SKU-003", "https://example.com/p/3", "email_promo"],
        ]
        records = _patched_read(rows)

        assert len(records) == 1
        assert records[0]["utm_stitched"] is not None
        assert "utm_campaign=email_promo" in records[0]["utm_stitched"]

    def test_empty_sheet_returns_empty_list(self):
        """An empty sheet (no rows at all) returns an empty list."""
        records = _patched_read([])
        assert records == []

    def test_header_only_sheet_returns_empty_list(self):
        """A sheet with only a header row returns []."""
        rows = [["section_title", "sku", "product_link", "priority"]]
        records = _patched_read(rows)
        assert records == []

    def test_rows_with_empty_sku_and_link_are_skipped(self):
        """Rows where both sku and product_link are empty are skipped."""
        rows = [
            ["sku", "product_link", "section_title"],
            ["", "", "Electronics"],
            ["SKU-004", "https://e.com/4", "Electronics"],
        ]
        records = _patched_read(rows)

        assert len(records) == 1
        assert records[0]["sku"] == "SKU-004"

    def test_case_insensitive_header_matching(self):
        """Column headers are matched case-insensitively."""
        rows = [
            ["Section_Title", "SKU", "Product_Link", "PRIORITY"],
            ["Apparel", "SKU-005", "https://e.com/5", "LOW"],
        ]
        records = _patched_read(rows)

        assert len(records) == 1
        assert records[0]["section_title"] == "Apparel"
        assert records[0]["sku"] == "SKU-005"
        assert records[0]["priority"] == "low"

    def test_invalid_priority_defaults_to_medium(self):
        """Unknown priority values fall back to 'medium'."""
        rows = [
            ["sku", "product_link", "priority"],
            ["SKU-006", "https://e.com/6", "CRITICAL"],
        ]
        records = _patched_read(rows)
        assert records[0]["priority"] == "medium"

    def test_short_row_padded_gracefully(self):
        """Rows shorter than the header are padded — no IndexError raised."""
        rows = [
            ["sku", "product_link", "section_title", "priority", "price"],
            ["SKU-007", "https://e.com/7"],
        ]
        records = _patched_read(rows)

        assert len(records) == 1
        assert records[0]["sku"] == "SKU-007"
        assert records[0]["priority"] == "medium"

    def test_multiple_rows_all_returned_in_order(self):
        """Multiple data rows are all returned in insertion order."""
        rows = [
            ["sku", "product_link"],
            ["SKU-A", "https://e.com/A"],
            ["SKU-B", "https://e.com/B"],
            ["SKU-C", "https://e.com/C"],
        ]
        records = _patched_read(rows)

        assert len(records) == 3
        assert [r["sku"] for r in records] == ["SKU-A", "SKU-B", "SKU-C"]

    def test_missing_optional_columns_are_none(self):
        """Optional fields (price, utm, button) are None when columns absent."""
        rows = [
            ["sku", "product_link"],
            ["SKU-X", "https://e.com/X"],
        ]
        records = _patched_read(rows)

        assert records[0]["raw_price"] is None
        assert records[0]["utm_campaign"] is None
        assert records[0]["button_name"] is None


class TestReadSheetEdgeCases:
    def test_invalid_sheet_url_raises_value_error(self):
        """A URL without a spreadsheet ID raises ValueError immediately."""
        with pytest.raises(ValueError, match="spreadsheet ID"):
            read_sheet("https://docs.google.com/not-a-spreadsheet", _FAKE_CREDS)

    def test_default_section_title_when_missing(self):
        """When section_title column is absent, rows default to 'Default' section."""
        rows = [
            ["sku", "product_link"],
            ["SKU-D", "https://e.com/D"],
        ]
        records = _patched_read(rows)

        assert records[0]["section_title"] == "Default"
