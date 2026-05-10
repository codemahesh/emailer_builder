"""
test_sheet_version_store.py
===========================
Unit tests for compute_checksum (pure) and integration tests for
write_version / prune_old_versions using an in-memory SQLite database.
"""

from __future__ import annotations

import sys
import os
import uuid
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.user import Base
# Import all models so Base.metadata is complete
from app.models.campaign import Campaign  # noqa: F401
from app.models.product import Product, Section  # noqa: F401
from app.models.sheet_version import SheetVersion, SheetVersionRow
from app.modules.sheet_version_store import (
    compute_checksum,
    latest_version,
    prune_old_versions,
    write_version,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def session():
    """In-memory SQLite async session. Recreated per test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite doesn't enforce FK constraints by default
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as s:
        yield s

    await engine.dispose()


_CAMPAIGN_ID = uuid.uuid4()

_ROWS_A = [
    {"sku": "SKU-1", "product_link": "https://example.com/1", "raw_price": "₹999"},
    {"sku": "SKU-2", "product_link": "https://example.com/2", "raw_price": "₹1999"},
]

_ROWS_B = [
    {"sku": "SKU-1", "product_link": "https://example.com/1", "raw_price": "₹1099"},
]


# ── compute_checksum unit tests ───────────────────────────────────────────────

class TestComputeChecksum:
    def test_deterministic_same_input(self):
        assert compute_checksum(_ROWS_A) == compute_checksum(_ROWS_A)

    def test_order_independent(self):
        rows_reversed = list(reversed(_ROWS_A))
        assert compute_checksum(_ROWS_A) == compute_checksum(rows_reversed)

    def test_different_rows_produce_different_checksum(self):
        assert compute_checksum(_ROWS_A) != compute_checksum(_ROWS_B)

    def test_empty_rows_has_stable_checksum(self):
        c1 = compute_checksum([])
        c2 = compute_checksum([])
        assert c1 == c2

    def test_checksum_is_64_hex_chars(self):
        c = compute_checksum(_ROWS_A)
        assert len(c) == 64
        assert all(ch in "0123456789abcdef" for ch in c)

    def test_key_order_in_row_dict_does_not_matter(self):
        row_forward = {"sku": "A", "product_link": "https://x.com"}
        row_backward = {"product_link": "https://x.com", "sku": "A"}
        assert compute_checksum([row_forward]) == compute_checksum([row_backward])


# ── write_version integration tests ──────────────────────────────────────────

@pytest.mark.asyncio
class TestWriteVersion:
    async def test_first_write_creates_version_1(self, session):
        sv = await write_version(session, _CAMPAIGN_ID, _ROWS_A, "link", "https://sheet.url")
        assert sv.version == 1
        assert sv.row_count == len(_ROWS_A)
        assert sv.source == "link"
        assert sv.checksum == compute_checksum(_ROWS_A)

    async def test_identical_import_does_not_create_new_version(self, session):
        sv1 = await write_version(session, _CAMPAIGN_ID, _ROWS_A, "link", "https://sheet.url")
        sv2 = await write_version(session, _CAMPAIGN_ID, _ROWS_A, "link", "https://sheet.url")
        assert sv1.id == sv2.id
        assert sv1.version == sv2.version

    async def test_changed_rows_increments_version(self, session):
        sv1 = await write_version(session, _CAMPAIGN_ID, _ROWS_A, "link", "https://sheet.url")
        sv2 = await write_version(session, _CAMPAIGN_ID, _ROWS_B, "link", "https://sheet.url")
        assert sv2.version == sv1.version + 1

    async def test_version_rows_written(self, session):
        sv = await write_version(session, _CAMPAIGN_ID, _ROWS_A, "link", "https://sheet.url")
        from sqlalchemy import select as sa_select
        result = await session.execute(
            sa_select(SheetVersionRow).where(SheetVersionRow.version_id == sv.id)
        )
        rows = result.scalars().all()
        assert len(rows) == len(_ROWS_A)

    async def test_latest_version_returns_most_recent(self, session):
        await write_version(session, _CAMPAIGN_ID, _ROWS_A, "link", "https://sheet.url")
        sv2 = await write_version(session, _CAMPAIGN_ID, _ROWS_B, "link", "https://sheet.url")
        latest = await latest_version(session, _CAMPAIGN_ID)
        assert latest is not None
        assert latest.id == sv2.id

    async def test_latest_version_returns_none_for_unknown_campaign(self, session):
        result = await latest_version(session, uuid.uuid4())
        assert result is None


# ── prune_old_versions integration test ──────────────────────────────────────

@pytest.mark.asyncio
class TestPruneOldVersions:
    async def test_keeps_newest_10_deletes_rest(self, session):
        # Write 12 distinct versions by varying the row data
        for i in range(12):
            rows = [{"sku": f"SKU-{i}", "product_link": f"https://x.com/{i}"}]
            await write_version(session, _CAMPAIGN_ID, rows, "link", "https://sheet.url")

        await prune_old_versions(session, _CAMPAIGN_ID, keep=10)
        await session.flush()

        from sqlalchemy import select as sa_select, func
        count_result = await session.execute(
            sa_select(func.count()).where(SheetVersion.campaign_id == _CAMPAIGN_ID)
        )
        remaining = count_result.scalar_one()
        assert remaining == 10

    async def test_newest_versions_are_kept(self, session):
        versions = []
        for i in range(5):
            rows = [{"sku": f"SKU-{i}", "product_link": f"https://x.com/{i}"}]
            sv = await write_version(session, _CAMPAIGN_ID, rows, "link", "https://sheet.url")
            versions.append(sv)

        await prune_old_versions(session, _CAMPAIGN_ID, keep=3)
        await session.flush()

        latest = await latest_version(session, _CAMPAIGN_ID)
        assert latest is not None
        assert latest.id == versions[-1].id

    async def test_prune_with_fewer_than_keep_is_noop(self, session):
        rows = [{"sku": "SKU-X", "product_link": "https://x.com/X"}]
        await write_version(session, _CAMPAIGN_ID, rows, "link", "https://sheet.url")

        await prune_old_versions(session, _CAMPAIGN_ID, keep=10)

        from sqlalchemy import select as sa_select, func
        count_result = await session.execute(
            sa_select(func.count()).where(SheetVersion.campaign_id == _CAMPAIGN_ID)
        )
        assert count_result.scalar_one() == 1
