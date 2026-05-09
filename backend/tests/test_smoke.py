"""
test_smoke.py
=============
End-to-end smoke test: register → login → create campaign → list campaigns.

Uses httpx.AsyncClient against the FastAPI app in-process.
Requires a running PostgreSQL test DB (configured via DATABASE_URL env var).

Run with: pytest tests/test_smoke.py -v
"""

from __future__ import annotations

import os

import pytest

# Skip this test suite if DATABASE_URL is not set (prevents CI failures when
# the test DB is not available, e.g. pure unit-test runs).
pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping smoke tests",
)

import httpx
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Synchronous TestClient for smoke tests (no event-loop fixture needed)."""
    import sys, os as _os
    _os.chdir(_os.path.join(_os.path.dirname(__file__), ".."))

    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


_TEST_EMAIL = "smoke_test_user@example.com"
_TEST_PASSWORD = "SmokeTestPass123!"


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSmokeFlow:
    """
    Sequential smoke test: register → login → create → list.

    Each test depends on the previous one (run in order).
    """

    _token: str = ""
    _campaign_id: str = ""

    def test_register_user(self, client: TestClient):
        """POST /auth/register creates a new editor account."""
        resp = client.post(
            "/auth/register",
            json={
                "email": _TEST_EMAIL,
                "password": _TEST_PASSWORD,
            },
        )
        # 201 Created or 400 if user already exists (idempotent for repeated CI runs)
        assert resp.status_code in (201, 400), f"Unexpected status {resp.status_code}: {resp.text}"
        if resp.status_code == 201:
            data = resp.json()
            assert data["email"] == _TEST_EMAIL

    def test_login(self, client: TestClient):
        """POST /auth/jwt/login returns an access token."""
        resp = client.post(
            "/auth/jwt/login",
            data={"username": _TEST_EMAIL, "password": _TEST_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        TestSmokeFlow._token = data["access_token"]

    def test_get_me(self, client: TestClient):
        """GET /auth/me returns the current user."""
        resp = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {TestSmokeFlow._token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == _TEST_EMAIL

    def test_create_campaign(self, client: TestClient):
        """POST /campaigns creates a campaign and returns it with status=draft."""
        resp = client.post(
            "/campaigns",
            json={"name": "Smoke Test Campaign", "sheet_url": ""},
            headers={"Authorization": f"Bearer {TestSmokeFlow._token}"},
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        data = resp.json()
        assert data["name"] == "Smoke Test Campaign"
        assert data["status"] == "draft"
        TestSmokeFlow._campaign_id = data["id"]

    def test_list_campaigns(self, client: TestClient):
        """GET /campaigns lists the created campaign."""
        resp = client.get(
            "/campaigns",
            headers={"Authorization": f"Bearer {TestSmokeFlow._token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1
        ids = [c["id"] for c in data["items"]]
        assert TestSmokeFlow._campaign_id in ids

    def test_get_campaign(self, client: TestClient):
        """GET /campaigns/:id returns the specific campaign."""
        resp = client.get(
            f"/campaigns/{TestSmokeFlow._campaign_id}",
            headers={"Authorization": f"Bearer {TestSmokeFlow._token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == TestSmokeFlow._campaign_id
        assert data["name"] == "Smoke Test Campaign"

    def test_logout(self, client: TestClient):
        """POST /auth/jwt/logout invalidates the session."""
        resp = client.post(
            "/auth/jwt/logout",
            headers={"Authorization": f"Bearer {TestSmokeFlow._token}"},
        )
        # FastAPI-Users returns 200 or 204 depending on version
        assert resp.status_code in (200, 204)
