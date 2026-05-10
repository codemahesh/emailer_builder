"""
test_sheet_diff.py
==================
Unit tests for app.modules.sheet_diff.

Covers all Issue 7 acceptance criteria testable at the diff-computation level:
  AC1: non-link field edit → updated=1, rescrape_count=0
  AC2: product_link change → rescrape_count=1
  AC3: removed row → removed=1
  AC4: empty diff (identical rows) → has_changes=False
  AC5: URL normalization: trailing slash is ignored
  AC6: cancel (no commit) — pure logic, no side effects to test
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.modules.sheet_diff import compute_diff, normalize_url


_BASE_ROW = {
    "sku": "SKU-001",
    "product_link": "https://example.com/product/1",
    "raw_price": "₹999",
    "priority": "high",
}


# ── normalize_url ─────────────────────────────────────────────────────────────

class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/p/1/") == normalize_url("https://example.com/p/1")

    def test_lowercases_host(self):
        assert normalize_url("https://Example.COM/p/1") == normalize_url("https://example.com/p/1")

    def test_empty_string_returns_empty(self):
        assert normalize_url("") == ""

    def test_unchanged_path_unchanged(self):
        url = "https://example.com/p/1"
        assert normalize_url(url) == url


# ── compute_diff ──────────────────────────────────────────────────────────────

class TestEmptyDiff:
    def test_identical_rows_no_changes(self):
        rows = [_BASE_ROW]
        diff = compute_diff(rows, rows)
        assert diff["added"] == []
        assert diff["removed"] == []
        assert diff["updated"] == []
        assert len(diff["unchanged"]) == 1
        assert diff["rescrape_count"] == 0

    def test_empty_both_sides(self):
        diff = compute_diff([], [])
        assert diff["added"] == []
        assert diff["removed"] == []


class TestAddedRows:
    def test_new_sku_is_added(self):
        old_rows = [_BASE_ROW]
        new_row = {"sku": "SKU-002", "product_link": "https://example.com/2"}
        new_rows = [_BASE_ROW, new_row]
        diff = compute_diff(old_rows, new_rows)
        assert len(diff["added"]) == 1
        assert diff["added"][0]["sku"] == "SKU-002"

    def test_added_does_not_count_as_rescrape_in_base_count(self):
        old_rows = [_BASE_ROW]
        new_rows = [_BASE_ROW, {"sku": "SKU-NEW", "product_link": "https://example.com/new"}]
        diff = compute_diff(old_rows, new_rows)
        # rescrape_count only counts *updated* rows with link changes
        assert diff["rescrape_count"] == 0


class TestRemovedRows:
    def test_missing_sku_is_removed(self):
        old_rows = [_BASE_ROW, {"sku": "SKU-002", "product_link": "https://example.com/2"}]
        new_rows = [_BASE_ROW]
        diff = compute_diff(old_rows, new_rows)
        assert len(diff["removed"]) == 1
        assert diff["removed"][0]["sku"] == "SKU-002"


class TestUpdatedRows:
    def test_non_link_change_updated_no_rescrape(self):
        """AC1: editing price → updated=1, rescrape_count=0"""
        old_rows = [_BASE_ROW]
        new_row = {**_BASE_ROW, "raw_price": "₹1099"}
        diff = compute_diff(old_rows, [new_row])
        assert len(diff["updated"]) == 1
        assert diff["rescrape_count"] == 0
        assert diff["updated"][0]["link_changed"] is False

    def test_link_change_updated_with_rescrape(self):
        """AC2: changing product_link → rescrape_count=1"""
        old_rows = [_BASE_ROW]
        new_row = {**_BASE_ROW, "product_link": "https://example.com/product/NEW"}
        diff = compute_diff(old_rows, [new_row])
        assert len(diff["updated"]) == 1
        assert diff["rescrape_count"] == 1
        assert diff["updated"][0]["link_changed"] is True

    def test_url_normalization_trailing_slash(self):
        """AC5: trailing slash treated as same URL → no rescrape."""
        old_rows = [{"sku": "A", "product_link": "https://example.com/p/1"}]
        new_rows = [{"sku": "A", "product_link": "https://example.com/p/1/"}]
        diff = compute_diff(old_rows, new_rows)
        # product_link differs only by trailing slash — same URL after normalization
        assert diff["rescrape_count"] == 0

    def test_case_insensitive_host_same_link(self):
        """Uppercase host is the same URL."""
        old_rows = [{"sku": "A", "product_link": "https://Example.COM/p/1"}]
        new_rows = [{"sku": "A", "product_link": "https://example.com/p/1"}]
        diff = compute_diff(old_rows, new_rows)
        assert diff["rescrape_count"] == 0


class TestMultipleChanges:
    def test_mixed_diff(self):
        old_rows = [
            {"sku": "A", "product_link": "https://a.com/1", "raw_price": "₹100"},
            {"sku": "B", "product_link": "https://b.com/1"},
            {"sku": "C", "product_link": "https://c.com/1"},
        ]
        new_rows = [
            {"sku": "A", "product_link": "https://a.com/1", "raw_price": "₹200"},  # updated (price)
            {"sku": "C", "product_link": "https://c.com/2"},                          # updated (link)
            {"sku": "D", "product_link": "https://d.com/1"},                          # added
            # B removed
        ]
        diff = compute_diff(old_rows, new_rows)
        assert len(diff["added"]) == 1
        assert diff["added"][0]["sku"] == "D"
        assert len(diff["removed"]) == 1
        assert diff["removed"][0]["sku"] == "B"
        assert len(diff["updated"]) == 2
        assert diff["rescrape_count"] == 1   # only C (link changed)
        assert len(diff["unchanged"]) == 0

    def test_rescrape_count_counts_only_link_changes(self):
        old_rows = [
            {"sku": "A", "product_link": "https://a.com/1", "raw_price": "₹100"},
            {"sku": "B", "product_link": "https://b.com/1"},
        ]
        new_rows = [
            {"sku": "A", "product_link": "https://a.com/NEW"},   # link changed
            {"sku": "B", "product_link": "https://b.com/1", "raw_price": "₹500"},  # non-link
        ]
        diff = compute_diff(old_rows, new_rows)
        assert diff["rescrape_count"] == 1
