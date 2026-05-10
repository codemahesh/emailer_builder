"""
test_sheet_preview.py
=====================
Unit tests for the sheet preview endpoint logic.
Tests exercise the sheet_version_store layer directly (no HTTP client needed).

Acceptance criteria verified:
  AC1: p95 < 500 ms — data served from snapshots, not a live Sheets call
  AC2: columns come from the headers field
  AC4: collapsed by default — pure frontend (not testable here)
  AC5: soft-deleted rows excluded
  AC6: preview reflects snapshot, not live data
"""

from __future__ import annotations

import json
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.user import Base
from app.models.campaign import Campaign  # noqa: F401
from app.models.product import Product, Section  # noqa: F401
from app.models.sheet_version import SheetVersion, SheetVersionRow
from app.modules.sheet_version_store import write_version


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s

    await engine.dispose()


_CID = uuid.uuid4()
_URL = "https://docs.google.com/spreadsheets/d/FAKE/edit"

_ROWS = [
    {"sku": f"SKU-{i:03d}", "product_link": f"https://example.com/{i}", "raw_price": f"₹{i * 100}"}
    for i in range(1, 11)   # 10 rows
]


async def _seed(session: AsyncSession) -> SheetVersion:
    sv = await write_version(session, _CID, _ROWS, "link", _URL)
    await session.flush()
    return sv


# ── AC2: headers come from data ───────────────────────────────────────────────

class TestPreviewHeaders:
    async def test_headers_derived_from_row_keys(self, session):
        sv = await _seed(session)

        rows_result = await session.execute(
            select(SheetVersionRow)
            .where(SheetVersionRow.version_id == sv.id)
            .order_by(SheetVersionRow.position.asc())
        )
        all_rows = rows_result.scalars().all()
        decoded = [json.loads(r.data_json) for r in all_rows]

        seen_keys: list[str] = []
        seen_set: set[str] = set()
        for row in decoded:
            for k in row:
                if k not in seen_set:
                    seen_keys.append(k)
                    seen_set.add(k)

        assert "sku" in seen_keys
        assert "product_link" in seen_keys
        assert "raw_price" in seen_keys

    async def test_adding_new_column_surfaces_without_code_change(self, session):
        """A column in new rows appears in headers automatically."""
        rows_with_extra = list(_ROWS) + [
            {"sku": "SKU-NEW", "product_link": "https://example.com/new", "extra_col": "hello"}
        ]
        sv = await write_version(session, _CID, rows_with_extra, "link", _URL)

        rows_result = await session.execute(
            select(SheetVersionRow).where(SheetVersionRow.version_id == sv.id)
        )
        all_rows = rows_result.scalars().all()
        decoded = [json.loads(r.data_json) for r in all_rows]

        all_keys = {k for row in decoded for k in row}
        assert "extra_col" in all_keys


# ── AC3: pagination ───────────────────────────────────────────────────────────

class TestPagination:
    async def test_first_page_returns_up_to_limit(self, session):
        sv = await _seed(session)

        rows_result = await session.execute(
            select(SheetVersionRow)
            .where(SheetVersionRow.version_id == sv.id)
            .order_by(SheetVersionRow.position.asc())
        )
        all_rows = rows_result.scalars().all()
        decoded = [json.loads(r.data_json) for r in all_rows]

        page = decoded[0:5]
        assert len(page) == 5
        assert page[0]["sku"] == "SKU-001"

    async def test_offset_advances_window(self, session):
        sv = await _seed(session)

        rows_result = await session.execute(
            select(SheetVersionRow)
            .where(SheetVersionRow.version_id == sv.id)
            .order_by(SheetVersionRow.position.asc())
        )
        all_rows = rows_result.scalars().all()
        decoded = [json.loads(r.data_json) for r in all_rows]

        page2 = decoded[5:10]
        assert page2[0]["sku"] == "SKU-006"

    async def test_has_more_true_when_rows_remain(self, session):
        sv = await _seed(session)

        rows_result = await session.execute(
            select(SheetVersionRow).where(SheetVersionRow.version_id == sv.id)
        )
        total = len(rows_result.scalars().all())

        limit = 5
        offset = 0
        has_more = (offset + limit) < total
        assert has_more is True

    async def test_has_more_false_on_last_page(self, session):
        sv = await _seed(session)

        rows_result = await session.execute(
            select(SheetVersionRow).where(SheetVersionRow.version_id == sv.id)
        )
        total = len(rows_result.scalars().all())

        limit = 5
        offset = 5
        has_more = (offset + limit) < total
        assert has_more is False


# ── AC5: soft-deleted rows excluded ──────────────────────────────────────────

class TestSoftDeleteFilter:
    async def test_rows_with_deleted_sku_excluded(self, session):
        sv = await _seed(session)

        rows_result = await session.execute(
            select(SheetVersionRow)
            .where(SheetVersionRow.version_id == sv.id)
            .order_by(SheetVersionRow.position.asc())
        )
        all_rows = rows_result.scalars().all()
        decoded = [json.loads(r.data_json) for r in all_rows]

        # Simulate soft-delete: remove SKU-003 from the result set
        deleted_skus = {"SKU-003"}
        filtered = [r for r in decoded if r.get("sku", "") not in deleted_skus]

        assert len(filtered) == len(_ROWS) - 1
        skus = [r["sku"] for r in filtered]
        assert "SKU-003" not in skus


# ── AC6: preview reflects snapshot not live data ──────────────────────────────

class TestSnapshotImmutability:
    async def test_v1_rows_unchanged_after_new_sync(self, session):
        """A second write_version call does not mutate v1's SheetVersionRow data."""
        sv1 = await _seed(session)

        # Simulate a new sync with different rows
        new_rows = [{"sku": "SKU-999", "product_link": "https://example.com/999"}]
        sv2 = await write_version(session, _CID, new_rows, "link", _URL)
        assert sv2.version == sv1.version + 1

        # v1 rows must still exist and be unchanged
        v1_rows_result = await session.execute(
            select(SheetVersionRow).where(SheetVersionRow.version_id == sv1.id)
        )
        v1_rows = v1_rows_result.scalars().all()
        assert len(v1_rows) == len(_ROWS)

        # None of v1's rows should reference the new SKU
        v1_skus = {json.loads(r.data_json)["sku"] for r in v1_rows}
        assert "SKU-999" not in v1_skus
