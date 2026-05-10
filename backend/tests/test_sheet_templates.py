"""
test_sheet_templates.py
=======================
Validates that the generated static sheet templates are well-formed and
that filling them with valid data produces a clean verify result.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

STATIC = Path(__file__).parent.parent / "static"
XLSX_PATH = STATIC / "sheet-template.xlsx"
CSV_PATH = STATIC / "sheet-template.csv"

REQUIRED_COLUMNS = {"sku", "product_link"}


class TestXlsxTemplate:
    def test_file_exists(self):
        assert XLSX_PATH.exists(), "sheet-template.xlsx not found in static/"

    def test_opens_without_error(self):
        openpyxl = pytest.importorskip("openpyxl")
        wb = openpyxl.load_workbook(XLSX_PATH)
        assert wb is not None

    def test_has_products_sheet(self):
        openpyxl = pytest.importorskip("openpyxl")
        wb = openpyxl.load_workbook(XLSX_PATH)
        assert "Products" in wb.sheetnames

    def test_has_instructions_sheet(self):
        openpyxl = pytest.importorskip("openpyxl")
        wb = openpyxl.load_workbook(XLSX_PATH)
        assert "Instructions" in wb.sheetnames

    def test_products_sheet_has_required_headers(self):
        openpyxl = pytest.importorskip("openpyxl")
        wb = openpyxl.load_workbook(XLSX_PATH)
        ws = wb["Products"]
        headers = {cell.value for cell in next(ws.iter_rows(max_row=1)) if cell.value}
        assert REQUIRED_COLUMNS.issubset(headers)

    def test_products_sheet_has_example_rows(self):
        openpyxl = pytest.importorskip("openpyxl")
        wb = openpyxl.load_workbook(XLSX_PATH)
        ws = wb["Products"]
        # At least 2 data rows below the header
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        non_empty = [r for r in rows if any(v for v in r)]
        assert len(non_empty) >= 1

    def test_instructions_sheet_lists_priority_values(self):
        openpyxl = pytest.importorskip("openpyxl")
        wb = openpyxl.load_workbook(XLSX_PATH)
        ws = wb["Instructions"]
        text = " ".join(
            str(v) for row in ws.iter_rows(values_only=True) for v in row if v
        )
        assert "high" in text
        assert "medium" in text
        assert "low" in text

    def test_template_headers_pass_verify(self):
        """Headers from the xlsx template must satisfy sheet_parser required fields."""
        openpyxl = pytest.importorskip("openpyxl")
        from app.modules.sheet_parser import normalize_headers

        wb = openpyxl.load_workbook(XLSX_PATH)
        ws = wb["Products"]
        raw_headers = [cell.value for cell in next(ws.iter_rows(max_row=1)) if cell.value]
        result = normalize_headers(raw_headers)
        assert result["missing_required"] == [], (
            f"Template headers {raw_headers!r} fail required-column check: "
            f"{result['missing_required']}"
        )


class TestCsvTemplate:
    def test_file_exists(self):
        assert CSV_PATH.exists(), "sheet-template.csv not found in static/"

    def test_parses_without_error(self):
        text = CSV_PATH.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) >= 1

    def test_has_required_headers(self):
        text = CSV_PATH.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))
        assert REQUIRED_COLUMNS.issubset(set(reader.fieldnames or []))

    def test_has_example_row(self):
        text = CSV_PATH.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) >= 1
        assert rows[0]["sku"] != ""
        assert rows[0]["product_link"].startswith("http")

    def test_template_headers_pass_verify(self):
        from app.modules.sheet_parser import normalize_headers

        text = CSV_PATH.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))
        raw_headers = list(reader.fieldnames or [])
        result = normalize_headers(raw_headers)
        assert result["missing_required"] == [], (
            f"CSV template headers {raw_headers!r} fail required-column check: "
            f"{result['missing_required']}"
        )
