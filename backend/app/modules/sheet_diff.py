"""
sheet_diff.py
=============
Pure diff computation between two sets of canonical sheet rows.

Used by the Update List / Import endpoint to compute what changed
between the latest imported version and the current live sheet.
"""

from __future__ import annotations

from typing import TypedDict
from urllib.parse import urlparse


# ── URL normalization ─────────────────────────────────────────────────────────

def normalize_url(url: str) -> str:
    """
    Canonical form for product_link comparison:
    lowercase scheme+host, strip trailing slash from path.

    Examples::

        normalize_url("https://Example.com/p/1/") == "https://example.com/p/1"
        normalize_url("https://example.com/p/1")  == "https://example.com/p/1"
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        normalized = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            path=parsed.path.rstrip("/") or "/",
        )
        return normalized.geturl()
    except Exception:
        return url.strip().rstrip("/").lower()


# ── Diff types ────────────────────────────────────────────────────────────────

class UpdatedRow(TypedDict):
    sku: str
    old: dict
    new: dict
    link_changed: bool  # True when product_link (URL-normalized) differs


class DiffResult(TypedDict):
    added: list[dict]          # new rows with no prior SKU
    removed: list[dict]        # old rows whose SKU is absent from new rows
    updated: list[UpdatedRow]  # same SKU, different canonical fields
    unchanged: list[dict]      # same SKU, identical canonical fields
    rescrape_count: int        # number of updated rows where link_changed=True


def compute_diff(old_rows: list[dict], new_rows: list[dict]) -> DiffResult:
    """
    Compute the diff between *old_rows* (latest SheetVersion snapshot) and
    *new_rows* (current live sheet rows).

    Both lists should contain canonical-field dicts
    (output of ``sheet_parser.row_to_canonical_dict``).

    SKU is the identity key.  If a SKU appears multiple times in one set
    only the first occurrence is used.
    """
    # Index old rows by SKU (first occurrence wins)
    old_by_sku: dict[str, dict] = {}
    for row in old_rows:
        sku = row.get("sku", "")
        if sku and sku not in old_by_sku:
            old_by_sku[sku] = row

    # Index new rows by SKU
    new_by_sku: dict[str, dict] = {}
    new_order: list[str] = []
    for row in new_rows:
        sku = row.get("sku", "")
        if sku and sku not in new_by_sku:
            new_by_sku[sku] = row
            new_order.append(sku)

    added: list[dict] = []
    removed: list[dict] = []
    updated: list[UpdatedRow] = []
    unchanged: list[dict] = []

    # Walk new rows in order
    for sku in new_order:
        new_row = new_by_sku[sku]
        if sku not in old_by_sku:
            added.append(new_row)
        else:
            old_row = old_by_sku[sku]
            if _rows_equal(old_row, new_row):
                unchanged.append(new_row)
            else:
                link_changed = (
                    normalize_url(old_row.get("product_link", ""))
                    != normalize_url(new_row.get("product_link", ""))
                )
                updated.append(
                    UpdatedRow(sku=sku, old=old_row, new=new_row, link_changed=link_changed)
                )

    # Rows that exist in old but not in new are removed
    for sku, old_row in old_by_sku.items():
        if sku not in new_by_sku:
            removed.append(old_row)

    rescrape_count = sum(1 for u in updated if u["link_changed"])

    return DiffResult(
        added=added,
        removed=removed,
        updated=updated,
        unchanged=unchanged,
        rescrape_count=rescrape_count,
    )


def _rows_equal(a: dict, b: dict) -> bool:
    """True iff all canonical fields have the same value in both rows."""
    from app.modules.sheet_parser import CANONICAL_FIELDS

    for field in CANONICAL_FIELDS:
        if (a.get(field) or "") != (b.get(field) or ""):
            return False
    return True
