"""
file_parser.py
==============
Parse uploaded .xlsx or .csv files into canonical row dicts using sheet_parser.

Returns the same structure as sheet_reader.read_sheet so callers treat
both sources identically.
"""

from __future__ import annotations

import csv
import io
from typing import Literal

from app.modules.sheet_parser import (
    CANONICAL_FIELDS,
    normalize_headers,
    row_to_canonical_dict,
)

_MAX_BYTES = 5 * 1024 * 1024       # 5 MB
_MAX_ROWS = 10_000

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_CSV_MIMES = {"text/csv", "text/plain", "application/csv", "application/octet-stream"}

FileType = Literal["xlsx", "csv"]


class UploadParseError(Exception):
    """Raised when the uploaded file cannot be parsed for a documented reason."""

    def __init__(self, error_code: str, detail: str) -> None:
        super().__init__(detail)
        self.error_code = error_code
        self.detail = detail


def detect_file_type(filename: str, content_type: str | None) -> FileType:
    """Determine whether the file is xlsx or csv."""
    name = (filename or "").lower()
    mime = (content_type or "").split(";")[0].strip().lower()

    if name.endswith(".xlsx") or mime == _XLSX_MIME:
        return "xlsx"
    if name.endswith(".csv") or mime in _CSV_MIMES:
        return "csv"

    raise UploadParseError(
        "INVALID_TYPE",
        "Only .xlsx and .csv files are supported.",
    )


def parse_bytes(
    data: bytes,
    file_type: FileType,
) -> list[dict]:
    """
    Parse *data* (already size-checked) into a list of canonical row dicts.

    Raises UploadParseError for EMPTY_SHEET, MISSING_COLUMNS, or TOO_MANY_ROWS.
    """
    if file_type == "xlsx":
        raw_rows = _parse_xlsx(data)
    else:
        raw_rows = _parse_csv(data)

    if not raw_rows:
        raise UploadParseError("EMPTY_SHEET", "The file contains no rows.")

    header_row, data_rows = raw_rows[0], raw_rows[1:]

    if len(data_rows) > _MAX_ROWS:
        raise UploadParseError(
            "TOO_MANY_ROWS",
            f"File exceeds the {_MAX_ROWS:,}-row limit ({len(data_rows):,} rows found).",
        )

    result = normalize_headers([str(h) for h in header_row])

    if result["missing_required"]:
        raise UploadParseError(
            "MISSING_COLUMNS",
            f"Missing required columns: {', '.join(result['missing_required'])}",
        )

    if not data_rows:
        raise UploadParseError("EMPTY_SHEET", "The file has a header row but no data rows.")

    canonical_headers = result["headers"]
    records = [
        row_to_canonical_dict(canonical_headers, list(row))
        for row in data_rows
    ]
    return records


def _parse_xlsx(data: bytes) -> list[list]:
    try:
        import openpyxl
    except ImportError:
        raise UploadParseError("SERVER_ERROR", "Server is missing openpyxl; cannot parse .xlsx.")

    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise UploadParseError("PARSE_ERROR", f"Could not open .xlsx file: {exc}")

    ws = wb.worksheets[0]
    rows: list[list] = []
    for row in ws.iter_rows(values_only=True):
        rows.append([v if v is not None else "" for v in row])

    wb.close()
    return rows


def _parse_csv(data: bytes) -> list[list]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except Exception as exc:
            raise UploadParseError("PARSE_ERROR", f"Could not decode CSV: {exc}")

    reader = csv.reader(io.StringIO(text))
    try:
        return [row for row in reader if any(cell.strip() for cell in row)]
    except csv.Error as exc:
        raise UploadParseError("PARSE_ERROR", f"Could not parse CSV: {exc}")
