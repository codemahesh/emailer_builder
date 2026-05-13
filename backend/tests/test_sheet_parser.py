"""
test_sheet_parser.py
====================
Unit tests for app.modules.sheet_parser — pure, no IO.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.modules.sheet_parser import (
    CANONICAL_FIELDS,
    COLUMN_ALIASES,
    REQUIRED_FIELDS,
    coerce_priority,
    normalize_header,
    normalize_headers,
    row_to_canonical_dict,
)


class TestNormalizeHeader:
    def test_known_alias_maps_to_canonical(self):
        assert normalize_header("price") == "raw_price"
        assert normalize_header("link") == "product_link"
        assert normalize_header("cta") == "button_name"
        assert normalize_header("section") == "section_title"
        assert normalize_header("campaign") == "utm_campaign"

    def test_strips_whitespace(self):
        assert normalize_header("  price  ") == "raw_price"
        assert normalize_header("\tsku\t") == "sku"

    def test_case_insensitive(self):
        assert normalize_header("PRICE") == "raw_price"
        assert normalize_header("Product_Link") == "product_link"
        assert normalize_header("Section_Title") == "section_title"

    def test_unknown_header_returned_lowercased(self):
        assert normalize_header("Custom_Column") == "custom_column"
        assert normalize_header("FOOBAR") == "foobar"


class TestNormalizeHeaders:
    """Round-trip all entries in COLUMN_ALIASES."""

    @pytest.mark.parametrize("raw_alias,expected_canonical", COLUMN_ALIASES.items())
    def test_all_aliases_resolve_correctly(self, raw_alias: str, expected_canonical: str):
        result = normalize_headers([raw_alias])
        assert result["headers"] == [expected_canonical]
        assert expected_canonical in result["canonical_to_index"]

    def test_missing_required_fields_reported(self):
        result = normalize_headers(["section_title", "priority"])
        assert set(result["missing_required"]) == set(REQUIRED_FIELDS)

    def test_no_missing_required_when_both_present(self):
        result = normalize_headers(["sku", "product_link", "price"])
        assert result["missing_required"] == []

    def test_first_occurrence_wins_for_duplicate_canonical(self):
        # Both "price" and "raw_price" map to raw_price; first column wins
        result = normalize_headers(["price", "raw_price"])
        assert result["canonical_to_index"]["raw_price"] == 0

    def test_unknown_headers_have_none_in_raw_to_canonical(self):
        result = normalize_headers(["sku", "product_link", "MyCustomCol"])
        assert result["raw_to_canonical"]["MyCustomCol"] is None

    def test_known_headers_have_canonical_in_raw_to_canonical(self):
        result = normalize_headers(["sku", "product_link"])
        assert result["raw_to_canonical"]["sku"] == "sku"
        assert result["raw_to_canonical"]["product_link"] == "product_link"

    def test_empty_header_list(self):
        result = normalize_headers([])
        assert result["headers"] == []
        assert result["missing_required"] == list(REQUIRED_FIELDS)

    def test_order_preserved(self):
        raw = ["button_name", "sku", "product_link"]
        result = normalize_headers(raw)
        assert result["headers"] == ["button_name", "sku", "product_link"]


class TestRowToCanonicalDict:
    def test_basic_projection(self):
        headers = ["sku", "product_link", "raw_price"]
        row = ["SKU-1", "https://example.com", "₹999"]
        out = row_to_canonical_dict(headers, row)
        assert out == {"sku": "SKU-1", "product_link": "https://example.com", "raw_price": "₹999"}

    def test_unknown_headers_dropped(self):
        headers = ["sku", "product_link", "custom_col"]
        row = ["SKU-2", "https://example.com", "ignored"]
        out = row_to_canonical_dict(headers, row)
        assert "custom_col" not in out

    def test_short_row_padded(self):
        headers = ["sku", "product_link", "raw_price"]
        row = ["SKU-3"]
        out = row_to_canonical_dict(headers, row)
        assert out["sku"] == "SKU-3"
        assert out["product_link"] == ""
        assert out["raw_price"] == ""

    def test_none_cells_become_empty_string(self):
        headers = ["sku", "product_link"]
        row = [None, None]
        out = row_to_canonical_dict(headers, row)
        assert out["sku"] == ""
        assert out["product_link"] == ""


class TestNewOptionalFields:
    def test_new_columns_present_are_parsed(self):
        headers = ["sku", "product_link", "pack_of", "quantity", "discount"]
        row = ["SKU-1", "https://example.com", "6 pack", "500ml", "10%"]
        out = row_to_canonical_dict(headers, row)
        assert out["pack_of"] == "6 pack"
        assert out["quantity"] == "500ml"
        assert out["discount"] == "10%"

    def test_new_columns_absent_leaves_them_missing_not_error(self):
        headers = ["sku", "product_link", "raw_price"]
        row = ["SKU-2", "https://example.com", "₹999"]
        out = row_to_canonical_dict(headers, row)
        assert "pack_of" not in out
        assert "quantity" not in out
        assert "discount" not in out

    def test_new_columns_not_in_required_fields(self):
        result = normalize_headers(["sku", "product_link"])
        assert result["missing_required"] == []

    def test_new_columns_in_canonical_fields(self):
        assert "pack_of" in CANONICAL_FIELDS
        assert "quantity" in CANONICAL_FIELDS
        assert "discount" in CANONICAL_FIELDS

    def test_aliases_resolve_correctly(self):
        assert normalize_header("pack") == "pack_of"
        assert normalize_header("pack of") == "pack_of"
        assert normalize_header("qty") == "quantity"
        assert normalize_header("disc") == "discount"


class TestCoercePriority:
    def test_valid_values_pass_through(self):
        assert coerce_priority("high") == "high"
        assert coerce_priority("medium") == "medium"
        assert coerce_priority("low") == "low"

    def test_case_insensitive(self):
        assert coerce_priority("HIGH") == "high"
        assert coerce_priority("Low") == "low"

    def test_invalid_falls_back_to_medium(self):
        assert coerce_priority("critical") == "medium"
        assert coerce_priority("urgent") == "medium"
        assert coerce_priority("") == "medium"

    def test_none_falls_back_to_medium(self):
        assert coerce_priority(None) == "medium"

    def test_whitespace_stripped(self):
        assert coerce_priority("  high  ") == "high"
