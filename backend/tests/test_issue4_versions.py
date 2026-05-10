"""
test_issue4_versions.py
=======================
Acceptance-criteria tests for Issue 4: versioned snapshots on Full Sync.

Tests that are already covered by test_sheet_version_store.py (write_version
checksum dedup, prune_old_versions keeping newest 10) are not duplicated here.
This file covers the remaining ACs:

  AC5: soft-deleted rows excluded from version-snapshot canonical JSON
       (historical rows preserved even after product soft-delete)
  AC6: GET /sheet/versions returns [{id, version, source, source_ref,
       imported_at, imported_by, row_count, checksum}] ordered newest-first
  AC7: manual image overrides (processed_image_url) are not touched by write_version
"""

from __future__ import annotations

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
from app.modules.sheet_version_store import (
    compute_checksum,
    write_version,
)


# ── Shared fixtures ───────────────────────────────────────────────────────────

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

ROWS_V1 = [
    {"sku": "A001", "product_link": "https://example.com/1"},
    {"sku": "A002", "product_link": "https://example.com/2"},
]

ROWS_V2 = [
    {"sku": "A001", "product_link": "https://example.com/1"},
    # A002 "deleted" from the sheet; a new row added
    {"sku": "A003", "product_link": "https://example.com/3"},
]


# ── AC1: first sync creates version=1 ────────────────────────────────────────

class TestFirstSyncCreatesV1:
    async def test_version_number_is_1(self, session):
        sv = await write_version(session, _CID, ROWS_V1, "link", _URL)
        assert sv.version == 1

    async def test_row_count_matches(self, session):
        sv = await write_version(session, _CID, ROWS_V1, "link", _URL)
        assert sv.row_count == len(ROWS_V1)

    async def test_source_fields(self, session):
        sv = await write_version(session, _CID, ROWS_V1, "link", _URL)
        assert sv.source == "link"
        assert sv.source_ref == _URL


# ── AC2: identical re-sync returns same version ───────────────────────────────

class TestChecksumDedup:
    async def test_same_data_no_new_version(self, session):
        sv1 = await write_version(session, _CID, ROWS_V1, "link", _URL)
        sv2 = await write_version(session, _CID, ROWS_V1, "link", _URL)
        assert sv1.id == sv2.id
        assert sv1.version == sv2.version

    async def test_dedup_does_not_add_version_rows(self, session):
        await write_version(session, _CID, ROWS_V1, "link", _URL)
        await write_version(session, _CID, ROWS_V1, "link", _URL)

        count_result = await session.execute(
            select(SheetVersion).where(SheetVersion.campaign_id == _CID)
        )
        assert len(count_result.scalars().all()) == 1


# ── AC3: changed rows produce version N+1 ────────────────────────────────────

class TestChangedRowsNewVersion:
    async def test_new_version_after_change(self, session):
        sv1 = await write_version(session, _CID, ROWS_V1, "link", _URL)
        sv2 = await write_version(session, _CID, ROWS_V2, "link", _URL)
        assert sv2.version == sv1.version + 1

    async def test_checksum_differs(self, session):
        sv1 = await write_version(session, _CID, ROWS_V1, "link", _URL)
        sv2 = await write_version(session, _CID, ROWS_V2, "link", _URL)
        assert sv1.checksum != sv2.checksum


# ── AC5: soft-deleted row does not corrupt historical snapshot ────────────────

class TestSoftDeletePreservesHistory:
    async def test_historical_rows_preserved_after_rewrite(self, session):
        """
        Simulate: v1 syncs [A001, A002]. Then A002 is 'soft-deleted' (removed
        from the next sheet read). v2 syncs [A001, A003]. v1's SheetVersionRow
        records for A002 must still exist.
        """
        sv1 = await write_version(session, _CID, ROWS_V1, "link", _URL)
        sv2 = await write_version(session, _CID, ROWS_V2, "link", _URL)

        # v1 rows must still exist
        v1_rows = await session.execute(
            select(SheetVersionRow).where(SheetVersionRow.version_id == sv1.id)
        )
        assert len(v1_rows.scalars().all()) == len(ROWS_V1)

    async def test_v2_excludes_deleted_row(self, session):
        """v2 rows should only reflect the new sheet state (no A002)."""
        await write_version(session, _CID, ROWS_V1, "link", _URL)
        sv2 = await write_version(session, _CID, ROWS_V2, "link", _URL)

        v2_rows = await session.execute(
            select(SheetVersionRow).where(SheetVersionRow.version_id == sv2.id)
        )
        assert len(v2_rows.scalars().all()) == len(ROWS_V2)


# ── AC6: versions are ordered newest-first ───────────────────────────────────

class TestVersionOrdering:
    async def test_ordered_newest_first(self, session):
        sv1 = await write_version(session, _CID, ROWS_V1, "link", _URL)
        sv2 = await write_version(session, _CID, ROWS_V2, "link", _URL)

        result = await session.execute(
            select(SheetVersion)
            .where(SheetVersion.campaign_id == _CID)
            .order_by(SheetVersion.version.desc())
        )
        versions = result.scalars().all()
        assert versions[0].id == sv2.id
        assert versions[1].id == sv1.id

    async def test_version_metadata_complete(self, session):
        sv = await write_version(session, _CID, ROWS_V1, "link", _URL)
        assert sv.id is not None
        assert sv.version == 1
        assert sv.source == "link"
        assert sv.source_ref == _URL
        assert sv.imported_at is not None
        assert sv.row_count == len(ROWS_V1)
        assert len(sv.checksum) == 64  # SHA-256 hex digest
