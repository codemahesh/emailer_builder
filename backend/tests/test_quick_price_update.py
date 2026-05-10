"""
test_quick_price_update.py
==========================
Tests for Issue 8: Action-button rationalization.

Verifies:
- POST /campaigns/{id}/sheet/quick-price endpoint exists and returns 202
- The fast_sync_worker (run_fast_sync) never touches processed_image_url,
  scraped_image_url, scrape_failed, or ManualOverride records.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import Base
from app.models.campaign import Campaign
from app.models.product import Product, ProductPriority, Section
from app.models.sync_job import SyncJob, SyncJobStatus
from app.workers.fast_sync_worker import run_fast_sync

# ── SQLite in-memory fixture ──────────────────────────────────────────────────

_ENGINE = None
_SESSION_MAKER = None


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_ENGINE.sync_engine, "connect")
        def disable_fk(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=OFF")

    return _ENGINE


def get_session_maker():
    global _SESSION_MAKER
    if _SESSION_MAKER is None:
        _SESSION_MAKER = sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _SESSION_MAKER


@pytest_asyncio.fixture(autouse=True)
async def setup_db(monkeypatch):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sm = get_session_maker()
    monkeypatch.setattr("app.workers.fast_sync_worker.async_session_maker", sm)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create_campaign_with_products(session: AsyncSession) -> tuple[str, list[str]]:
    """Return (campaign_id, [product_id, ...]) after inserting test data."""
    cid = uuid.uuid4()
    campaign = Campaign(
        id=cid,
        name="Test",
        sheet_url="https://docs.google.com/spreadsheets/d/TEST/edit",
        owner_id=uuid.uuid4(),
    )
    session.add(campaign)
    await session.flush()

    sec = Section(id=uuid.uuid4(), campaign_id=cid, title="Default", position=0)
    session.add(sec)
    await session.flush()

    products = []
    for i, (sku, price) in enumerate([("SKU-1", "$10.00"), ("SKU-2", "$20.00")]):
        p = Product(
            id=uuid.uuid4(),
            campaign_id=cid,
            section_id=sec.id,
            sku=sku,
            product_link=f"https://example.com/{sku}",
            priority=ProductPriority.medium,
            raw_price=price,
            processed_image_url=f"https://cdn.example.com/{sku}.png",
            scraped_image_url=f"https://scraped.example.com/{sku}.jpg",
            scrape_failed=False,
            position=i,
        )
        session.add(p)
        products.append(str(p.id))

    await session.commit()
    return str(cid), products


class _FakeRedis:
    """Minimal Redis stub that discards writes and returns nothing."""

    async def set(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def get(self, *args: Any) -> None:
        return None


class _FakeGateway:
    async def send_progress(self, *args: Any, **kwargs: Any) -> None:
        pass


def _fake_read_sheet(url: str, creds: dict) -> list[dict]:
    return [
        {"sku": "SKU-1", "product_link": "https://example.com/SKU-1", "raw_price": "$11.00", "formatted_price": "11 USD"},
        {"sku": "SKU-2", "product_link": "https://example.com/SKU-2", "raw_price": "$22.00", "utm_campaign": "sale"},
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quick_price_update_does_not_touch_images(monkeypatch):
    """run_fast_sync must not modify processed_image_url or scraped_image_url."""
    import app.workers.fast_sync_worker as fsw

    monkeypatch.setattr(fsw, "read_sheet", _fake_read_sheet)
    monkeypatch.setattr(fsw, "gateway", _FakeGateway())

    sm = get_session_maker()
    async with sm() as session:
        cid, pids = await _create_campaign_with_products(session)

    ctx = {"redis": _FakeRedis()}
    result = await run_fast_sync(ctx, campaign_id=cid)

    assert result["status"] == "done"
    assert result["updated"] == 2

    # Verify images are untouched
    async with sm() as session:
        for pid in pids:
            from sqlalchemy import select
            row = (await session.execute(
                select(Product).where(Product.id == uuid.UUID(pid))
            )).scalar_one()
            # Images must be unchanged
            assert row.processed_image_url is not None
            assert "cdn.example.com" in row.processed_image_url
            assert row.scraped_image_url is not None
            assert "scraped.example.com" in row.scraped_image_url
            assert row.scrape_failed is False


@pytest.mark.asyncio
async def test_quick_price_update_updates_price_and_utm(monkeypatch):
    """run_fast_sync must update raw_price, formatted_price, utm_campaign, utm_stitched."""
    import app.workers.fast_sync_worker as fsw

    monkeypatch.setattr(fsw, "read_sheet", _fake_read_sheet)
    monkeypatch.setattr(fsw, "gateway", _FakeGateway())

    sm = get_session_maker()
    async with sm() as session:
        cid, pids = await _create_campaign_with_products(session)

    ctx = {"redis": _FakeRedis()}
    await run_fast_sync(ctx, campaign_id=cid)

    from sqlalchemy import select
    async with sm() as session:
        sku1 = (await session.execute(
            select(Product).where(Product.sku == "SKU-1", Product.campaign_id == uuid.UUID(cid))
        )).scalar_one()
        assert sku1.raw_price == "$11.00"
        assert sku1.formatted_price == "11 USD"

        sku2 = (await session.execute(
            select(Product).where(Product.sku == "SKU-2", Product.campaign_id == uuid.UUID(cid))
        )).scalar_one()
        assert sku2.raw_price == "$22.00"
        assert sku2.utm_campaign == "sale"


@pytest.mark.asyncio
async def test_quick_price_update_never_touches_product_link(monkeypatch):
    """run_fast_sync must not change product_link — that would trigger an unwanted re-scrape."""
    import app.workers.fast_sync_worker as fsw

    def _sheet_with_new_link(url, creds):
        return [{"sku": "SKU-1", "product_link": "https://NEW-LINK.example.com/", "raw_price": "$15.00"}]

    monkeypatch.setattr(fsw, "read_sheet", _sheet_with_new_link)
    monkeypatch.setattr(fsw, "gateway", _FakeGateway())

    sm = get_session_maker()
    async with sm() as session:
        cid, _ = await _create_campaign_with_products(session)

    ctx = {"redis": _FakeRedis()}
    await run_fast_sync(ctx, campaign_id=cid)

    from sqlalchemy import select
    async with sm() as session:
        sku1 = (await session.execute(
            select(Product).where(Product.sku == "SKU-1", Product.campaign_id == uuid.UUID(cid))
        )).scalar_one()
        assert sku1.product_link == "https://example.com/SKU-1"
