"""
test_product_active.py
======================
Confirms Product.active() filters soft-deleted rows.
Uses in-memory SQLite to avoid any external DB dependency.
"""

from __future__ import annotations

import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.user import Base
from app.models.campaign import Campaign  # noqa: F401 — needed for Base.metadata
from app.models.product import Product, Section  # noqa: F401


@pytest.fixture
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

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as s:
        yield s

    await engine.dispose()


_CAMPAIGN_ID = uuid.uuid4()


def _make_product(*, deleted: bool = False) -> Product:
    return Product(
        campaign_id=_CAMPAIGN_ID,
        sku=f"SKU-{uuid.uuid4().hex[:6]}",
        product_link="https://example.com/p",
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )


@pytest.mark.asyncio
async def test_active_excludes_soft_deleted(session: AsyncSession):
    live = _make_product(deleted=False)
    dead = _make_product(deleted=True)
    session.add(live)
    session.add(dead)
    await session.flush()

    result = await session.execute(
        Product.active().where(Product.campaign_id == _CAMPAIGN_ID)
    )
    rows = result.scalars().all()

    ids = {r.id for r in rows}
    assert live.id in ids
    assert dead.id not in ids


@pytest.mark.asyncio
async def test_active_includes_all_non_deleted(session: AsyncSession):
    products = [_make_product(deleted=False) for _ in range(3)]
    for p in products:
        session.add(p)
    await session.flush()

    result = await session.execute(
        Product.active().where(Product.campaign_id == _CAMPAIGN_ID)
    )
    rows = result.scalars().all()
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_active_returns_empty_when_all_deleted(session: AsyncSession):
    for _ in range(2):
        session.add(_make_product(deleted=True))
    await session.flush()

    result = await session.execute(
        Product.active().where(Product.campaign_id == _CAMPAIGN_ID)
    )
    rows = result.scalars().all()
    assert rows == []
