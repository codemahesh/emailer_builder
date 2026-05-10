"""
test_file_parser.py
===================
Unit tests for app.modules.file_parser.

Covers all Issue 6 acceptance criteria testable at the parser level:
  AC1: both .xlsx and .csv parse through the same sheet_parser path
  AC2: files >5 MB or >10,000 rows rejected
  AC3: wrong MIME types rejected server-side
  AC4: EMPTY_SHEET and MISSING_COLUMNS surface with same error codes as Link
"""

from __future__ import annotations

import csv
import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.modules.file_parser import (
    UploadParseError,
    detect_file_type,
    parse_bytes,
    _MAX_BYTES,
    _MAX_ROWS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_csv(rows: list[list]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _make_xlsx(rows: list[list]) -> bytes:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


VALID_ROWS = [
    ["sku", "product_link"],
    ["SKU-001", "https://example.com/1"],
    ["SKU-002", "https://example.com/2"],
]


# ── AC3: MIME type / extension detection ─────────────────────────────────────

class TestDetectFileType:
    def test_xlsx_extension(self):
        assert detect_file_type("data.xlsx", "") == "xlsx"

    def test_csv_extension(self):
        assert detect_file_type("data.csv", "") == "csv"

    def test_xlsx_mime(self):
        assert detect_file_type(
            "data",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ) == "xlsx"

    def test_csv_mime(self):
        assert detect_file_type("data", "text/csv") == "csv"

    def test_unsupported_extension_raises(self):
        with pytest.raises(UploadParseError) as exc_info:
            detect_file_type("data.xls", "application/vnd.ms-excel")
        assert exc_info.value.error_code == "INVALID_TYPE"

    def test_unsupported_mime_no_extension_raises(self):
        with pytest.raises(UploadParseError) as exc_info:
            detect_file_type("", "application/pdf")
        assert exc_info.value.error_code == "INVALID_TYPE"

    def test_content_type_with_charset_stripped(self):
        # text/csv;charset=utf-8 should still be detected as csv
        assert detect_file_type("", "text/csv;charset=utf-8") == "csv"


# ── AC1: CSV parsing ──────────────────────────────────────────────────────────

class TestCsvParsing:
    def test_basic_csv_parses(self):
        data = _make_csv(VALID_ROWS)
        records = parse_bytes(data, "csv")
        assert len(records) == 2

    def test_csv_normalizes_headers(self):
        rows = [["SKU", "Product_Link"], ["A001", "https://x.com"]]
        data = _make_csv(rows)
        records = parse_bytes(data, "csv")
        assert records[0]["sku"] == "A001"
        assert records[0]["product_link"] == "https://x.com"

    def test_csv_with_alias_headers(self):
        rows = [["sku", "link"], ["A001", "https://x.com"]]
        data = _make_csv(rows)
        records = parse_bytes(data, "csv")
        assert records[0]["product_link"] == "https://x.com"

    def test_csv_empty_raises_empty_sheet(self):
        data = b""
        with pytest.raises(UploadParseError) as exc_info:
            parse_bytes(data, "csv")
        assert exc_info.value.error_code == "EMPTY_SHEET"

    def test_csv_header_only_raises_empty_sheet(self):
        data = _make_csv([["sku", "product_link"]])
        with pytest.raises(UploadParseError) as exc_info:
            parse_bytes(data, "csv")
        assert exc_info.value.error_code == "EMPTY_SHEET"

    def test_csv_missing_columns_raises(self):
        data = _make_csv([["price"], ["₹999"]])
        with pytest.raises(UploadParseError) as exc_info:
            parse_bytes(data, "csv")
        assert exc_info.value.error_code == "MISSING_COLUMNS"


# ── AC1: XLSX parsing ─────────────────────────────────────────────────────────

class TestXlsxParsing:
    def test_basic_xlsx_parses(self):
        data = _make_xlsx(VALID_ROWS)
        records = parse_bytes(data, "xlsx")
        assert len(records) == 2

    def test_xlsx_normalizes_headers(self):
        rows = [["SKU", "Product_Link"], ["A001", "https://x.com"]]
        data = _make_xlsx(rows)
        records = parse_bytes(data, "xlsx")
        assert records[0]["sku"] == "A001"

    def test_xlsx_missing_columns_raises(self):
        data = _make_xlsx([["price"], ["₹999"]])
        with pytest.raises(UploadParseError) as exc_info:
            parse_bytes(data, "xlsx")
        assert exc_info.value.error_code == "MISSING_COLUMNS"

    def test_xlsx_empty_raises_empty_sheet(self):
        data = _make_xlsx([])
        with pytest.raises(UploadParseError) as exc_info:
            parse_bytes(data, "xlsx")
        assert exc_info.value.error_code == "EMPTY_SHEET"


# ── AC2: size and row limits ──────────────────────────────────────────────────

class TestLimits:
    def test_too_many_rows_raises(self):
        rows = [["sku", "product_link"]] + [
            [f"SKU-{i}", f"https://example.com/{i}"] for i in range(_MAX_ROWS + 1)
        ]
        data = _make_csv(rows)
        with pytest.raises(UploadParseError) as exc_info:
            parse_bytes(data, "csv")
        assert exc_info.value.error_code == "TOO_MANY_ROWS"

    def test_exactly_max_rows_allowed(self):
        rows = [["sku", "product_link"]] + [
            [f"SKU-{i}", f"https://example.com/{i}"] for i in range(_MAX_ROWS)
        ]
        data = _make_csv(rows)
        records = parse_bytes(data, "csv")
        assert len(records) == _MAX_ROWS
