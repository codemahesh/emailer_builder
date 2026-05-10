"""
test_sync_integration.py
========================
End-to-end integration test for the full-sync pipeline (Issue 2 AC-9).

Runs ``run_full_sync`` against a real Postgres test DB with the Sheets API,
product scraper, image pipeline, orchestrator, Redis, and WebSocket gateway
all stubbed. Asserts that the worker imports the expected number of products
and groups them into the correct sections.

Skipped when ``DATABASE_URL`` is not configured (mirrors test_smoke.py).
"""

from __future__ import annotations

import os
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping sync integration test",
)


_SHEET_URL = "https://docs.google.com/spreadsheets/d/FIXTURE_ID/edit"

_FIXTURE_RECORDS: list[dict[str, Any]] = [
    {
        "section_title": "Electronics",
        "sku": "ELEC-001",
        "product_link": "https://example.com/elec/1",
        "priority": "high",
        "raw_price": "$199.99",
        "formatted_price": "$199.99",
        "utm_campaign": "summer",
        "utm_stitched": "https://example.com/elec/1?utm_campaign=summer",
        "button_name": "Buy Now",
    },
    {
        "section_title": "Electronics",
        "sku": "ELEC-002",
        "product_link": "https://example.com/elec/2",
        "priority": "medium",
        "raw_price": "$49.00",
        "formatted_price": "$49",
        "utm_campaign": "summer",
        "utm_stitched": "https://example.com/elec/2?utm_campaign=summer",
        "button_name": "Shop",
    },
    {
        "section_title": "Apparel",
        "sku": "APP-001",
        "product_link": "https://example.com/app/1",
        "priority": "low",
        "raw_price": "₹1,299",
        "formatted_price": "₹1,299",
        "utm_campaign": "summer",
        "utm_stitched": "https://example.com/app/1?utm_campaign=summer",
        "button_name": "View",
    },
]


@pytest.mark.asyncio
async def test_full_sync_persists_products_and_sections():
    """
    Run ``run_full_sync`` against the test DB with all external calls stubbed.
    Verify final state: SyncJob completed, 3 products, 2 sections.
    """
    from sqlalchemy import select, delete
    from app.database import async_session_maker
    from app.models.campaign import Campaign
    from app.models.product import Product, Section
    from app.models.sync_job import SyncJob, SyncJobStatus
    from app.models.user import User
    from app.workers import sync_worker

    user_id = uuid.uuid4()
    campaign_id = uuid.uuid4()

    # ── Seed user + campaign ────────────────────────────────────────────────
    async with async_session_maker() as session:
        session.add(
            User(
                id=user_id,
                email=f"sync_int_{user_id}@test.local",
                hashed_password="x" * 32,
                is_active=True,
                is_superuser=False,
                is_verified=True,
            )
        )
        session.add(
            Campaign(
                id=campaign_id,
                name="Sync Integration Fixture",
                sheet_url=_SHEET_URL,
                owner_id=user_id,
            )
        )
        job = SyncJob(campaign_id=campaign_id, job_type="full")
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = str(job.id)

    # ── Stub everything outside the DB ──────────────────────────────────────
    fake_redis = AsyncMock()
    fake_redis.set = AsyncMock(return_value=True)

    fake_scrape = MagicMock()
    fake_scrape.success = True
    fake_scrape.product_name = "Stub Product"
    fake_scrape.image_url = "/static/coming-soon.svg"
    fake_scrape.failure_reason = None

    fake_gateway = AsyncMock()
    fake_gateway.send_progress = AsyncMock()

    with (
        patch.object(sync_worker, "read_sheet", return_value=_FIXTURE_RECORDS),
        patch.object(sync_worker, "scrape_product", new=AsyncMock(return_value=fake_scrape)),
        patch.object(sync_worker, "_get_sku_cache", new=AsyncMock(return_value=None)),
        patch.object(sync_worker, "_process_product_image", new=AsyncMock(return_value="/static/coming-soon.svg")),
        patch.object(sync_worker, "_run_orchestrator", new=AsyncMock(return_value=None)),
        patch.object(sync_worker, "gateway", fake_gateway),
    ):
        result = await sync_worker.run_full_sync(
            ctx={"redis": fake_redis},
            campaign_id=str(campaign_id),
            sheet_url=_SHEET_URL,
            credentials_json={},
            job_id=job_id,
        )

    # ── Assert worker return value ──────────────────────────────────────────
    assert result["status"] == "done"
    assert result["imported"] == 3
    assert result["failed"] == 0
    assert result["total"] == 3

    # ── Assert DB state ────────────────────────────────────────────────────
    async with async_session_maker() as session:
        prod_rows = (
            await session.execute(
                select(Product).where(Product.campaign_id == campaign_id)
            )
        ).scalars().all()
        section_rows = (
            await session.execute(
                select(Section).where(Section.campaign_id == campaign_id)
            )
        ).scalars().all()
        job_row = (
            await session.execute(select(SyncJob).where(SyncJob.id == uuid.UUID(job_id)))
        ).scalar_one()

        assert len(prod_rows) == 3, "all 3 fixture products should be persisted"
        assert {s.title for s in section_rows} == {"Electronics", "Apparel"}
        assert len(section_rows) == 2, "two distinct sections expected"
        assert job_row.status == SyncJobStatus.completed
        assert job_row.total_products == 3
        assert job_row.processed_products == 3

        # ── Cleanup ─────────────────────────────────────────────────────────
        await session.execute(delete(Product).where(Product.campaign_id == campaign_id))
        await session.execute(delete(Section).where(Section.campaign_id == campaign_id))
        await session.execute(delete(SyncJob).where(SyncJob.campaign_id == campaign_id))
        await session.execute(delete(Campaign).where(Campaign.id == campaign_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()
