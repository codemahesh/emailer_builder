"""
test_scrape_failure_integration.py
==================================
Issue 3 AC-8: a campaign sync where one product URL 404s ends with a
Coming-Soon product, and the manual replacement upload flow works
end-to-end (writes through ImageStore + records a ManualOverride).

Skipped when DATABASE_URL is unset.
"""

from __future__ import annotations

import io
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping scrape-failure integration test",
)

_SHEET_URL = "https://docs.google.com/spreadsheets/d/FAILTEST/edit"

_FIXTURE_RECORDS = [
    {
        "section_title": "Sale",
        "sku": "OK-1",
        "product_link": "https://example.com/p/ok",
        "priority": "medium",
        "raw_price": "$10",
        "formatted_price": "$10",
        "utm_campaign": None,
        "utm_stitched": None,
        "button_name": "Buy",
    },
    {
        "section_title": "Sale",
        "sku": "BAD-1",
        "product_link": "https://example.com/p/missing",
        "priority": "medium",
        "raw_price": "$20",
        "formatted_price": "$20",
        "utm_campaign": None,
        "utm_stitched": None,
        "button_name": "Buy",
    },
]


def _scrape_side_effect(url):
    """Return a successful result for /ok and a 404 failure for /missing."""
    from app.modules.product_scraper import ScrapeResult
    if url.endswith("/missing"):
        return ScrapeResult(success=False, failure_reason="Page not found (404)")
    return ScrapeResult(
        success=True,
        product_name="OK Product",
        image_url="https://cdn.example.com/ok.png",
    )


@pytest.mark.asyncio
async def test_404_url_yields_coming_soon_product():
    """One URL 404s → that product persists with scrape_failed=True + coming-soon URL."""
    from sqlalchemy import select, delete
    from app.database import async_session_maker
    from app.models.campaign import Campaign
    from app.models.manual_override import ManualOverride
    from app.models.product import Product, Section
    from app.models.sync_job import SyncJob
    from app.models.user import User
    from app.workers import sync_worker

    user_id = uuid.uuid4()
    campaign_id = uuid.uuid4()

    async with async_session_maker() as session:
        session.add(
            User(
                id=user_id,
                email=f"scrape_fail_{user_id}@test.local",
                hashed_password="x" * 32,
                is_active=True,
                is_superuser=False,
                is_verified=True,
            )
        )
        session.add(
            Campaign(
                id=campaign_id,
                name="Scrape Fail Fixture",
                sheet_url=_SHEET_URL,
                owner_id=user_id,
            )
        )
        job = SyncJob(campaign_id=campaign_id, job_type="full")
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = str(job.id)

    fake_redis = AsyncMock()
    fake_gateway = AsyncMock()

    async def _fake_scrape(url):
        return _scrape_side_effect(url)

    with (
        patch.object(sync_worker, "read_sheet", return_value=_FIXTURE_RECORDS),
        patch.object(sync_worker, "scrape_product", new=_fake_scrape),
        patch.object(sync_worker, "_get_sku_cache", new=AsyncMock(return_value=None)),
        patch.object(
            sync_worker,
            "_process_product_image",
            new=AsyncMock(side_effect=lambda product, cid, cache: product.scraped_image_url),
        ),
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

    assert result["imported"] == 2

    bad_product_id = None
    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(Product).where(Product.campaign_id == campaign_id)
            )
        ).scalars().all()

        ok_rows = [p for p in rows if p.sku == "OK-1"]
        bad_rows = [p for p in rows if p.sku == "BAD-1"]
        assert len(ok_rows) == 1 and len(bad_rows) == 1

        ok = ok_rows[0]
        bad = bad_rows[0]
        assert ok.scrape_failed is False
        assert bad.scrape_failed is True
        assert bad.scraped_image_url == "/static/coming-soon.svg"

        bad_product_id = bad.id

    # ── Now exercise the manual replacement flow on the failed product ─────
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        # Register + login a user that owns this campaign by hijacking its
        # owner_id. Easiest path: sync write owner directly via DB and login
        # using a fresh test user — but the endpoint requires owner match.
        # We'll log in as a fresh user, transfer ownership, then call.
        email = f"scrape_fail_user_{user_id}@test.local"
        password = "ScrapeFailTest123!"

        reg = client.post("/auth/register", json={"email": email, "password": password})
        assert reg.status_code in (201, 400)

        login = client.post(
            "/auth/jwt/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        # Get the registered user id, then transfer campaign ownership.
        me = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        ).json()
        new_owner_id = uuid.UUID(me["id"])

        async with async_session_maker() as session:
            camp = await session.get(Campaign, campaign_id)
            camp.owner_id = new_owner_id
            await session.commit()

        # Upload a tiny PNG via multipart
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f"
            b"\x00\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        upload = client.patch(
            f"/campaigns/{campaign_id}/products/{bad_product_id}/replace-image",
            files={"file": ("replacement.png", io.BytesIO(png_bytes), "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert upload.status_code == 200, upload.text
        body = upload.json()
        assert body["scrape_failed"] is False
        assert body["scraped_image_url"] != "/static/coming-soon.svg"

    # ── Verify ManualOverride was recorded ─────────────────────────────────
    async with async_session_maker() as session:
        overrides = (
            await session.execute(
                select(ManualOverride).where(
                    ManualOverride.campaign_id == campaign_id,
                    ManualOverride.target_type == "product_image",
                    ManualOverride.target_id == str(bad_product_id),
                )
            )
        ).scalars().all()
        assert len(overrides) == 1, "ManualOverride row should be recorded for the replacement"

    # ── Cleanup ────────────────────────────────────────────────────────────
    async with async_session_maker() as session:
        await session.execute(
            delete(ManualOverride).where(ManualOverride.campaign_id == campaign_id)
        )
        await session.execute(delete(Product).where(Product.campaign_id == campaign_id))
        await session.execute(delete(Section).where(Section.campaign_id == campaign_id))
        await session.execute(delete(SyncJob).where(SyncJob.campaign_id == campaign_id))
        await session.execute(delete(Campaign).where(Campaign.id == campaign_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()
