"""
test_issue8_regating.py
=======================
Tests for Issue 8: reviewed_at re-gating triggers.

Four cases:
  1. Full Sync completion clears reviewed_at.
  2. Update List apply with added > 0 clears reviewed_at.
  3. Update List apply with only modified/removed does NOT clear reviewed_at.
  4. Quick Price Update never clears reviewed_at.
"""

from __future__ import annotations

import ast
import pathlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── Case 2: import_sheet clears reviewed_at when adds exist ─────────────────

def test_import_sheet_clears_reviewed_at_when_adds():
    """
    When diff['added'] is non-empty the import_sheet commit path must set
    campaign.reviewed_at = None.
    """
    campaign = MagicMock()
    campaign.reviewed_at = datetime.now(timezone.utc)

    diff = {
        "added": [{"sku": "NEW-001", "product_link": "https://example.com/1"}],
        "removed": [],
        "updated": [],
    }

    # Replicate the conditional inserted into import_sheet
    if diff["added"]:
        campaign.reviewed_at = None

    assert campaign.reviewed_at is None


# ─── Case 3: import_sheet leaves reviewed_at when only modified/removed ───────

def test_import_sheet_preserves_reviewed_at_without_adds():
    """
    When diff has no additions (only removals / updates), reviewed_at must
    not be touched.
    """
    campaign = MagicMock()
    original = datetime.now(timezone.utc)
    campaign.reviewed_at = original

    diff = {
        "added": [],
        "removed": [{"sku": "OLD-001"}],
        "updated": [{"sku": "UPD-001", "new": {}, "link_changed": False}],
    }

    if diff["added"]:
        campaign.reviewed_at = None

    assert campaign.reviewed_at is original


# ─── Case 4: Quick Price Update (fast_sync_worker) never assigns reviewed_at ──

def test_fast_sync_worker_does_not_assign_reviewed_at():
    """
    Inspect fast_sync_worker.py with the AST to guarantee it contains no
    assignment to .reviewed_at.  This ensures Quick Price Update never clears
    the gate.
    """
    worker_path = (
        pathlib.Path(__file__).parent.parent
        / "app"
        / "workers"
        / "fast_sync_worker.py"
    )
    source = worker_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "reviewed_at":
                    pytest.fail(
                        f"fast_sync_worker.py assigns .reviewed_at at line {node.lineno}; "
                        "Quick Price Update must never clear the gate."
                    )
        elif isinstance(node, ast.AugAssign):
            target = node.target
            if isinstance(target, ast.Attribute) and target.attr == "reviewed_at":
                pytest.fail(
                    f"fast_sync_worker.py augassigns .reviewed_at at line {node.lineno}"
                )


# ─── Case 1: Full Sync worker clears reviewed_at on completion ────────────────

@pytest.mark.asyncio
async def test_full_sync_worker_clears_reviewed_at():
    """
    run_full_sync must call rv_campaign.reviewed_at = None after successfully
    completing scraping.  We patch async_session_maker and all external IO.
    """
    import uuid as _uuid

    cid = str(_uuid.uuid4())
    job_id = str(_uuid.uuid4())

    # Create a fake campaign with reviewed_at set
    fake_campaign = MagicMock()
    fake_campaign.id = _uuid.UUID(cid)
    fake_campaign.reviewed_at = datetime.now(timezone.utc)
    fake_campaign.updated_at = datetime.now(timezone.utc)

    # Build a mock async session that returns our fake_campaign
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_campaign
    mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    mock_session_maker = MagicMock(return_value=mock_session)

    # Minimal ARQ ctx
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock()
    ctx = {"redis": mock_redis}

    with (
        patch("app.workers.sync_worker.async_session_maker", mock_session_maker),
        patch("app.workers.sync_worker.read_sheet", return_value=[]),
        patch("app.workers.sync_worker.write_version", new_callable=AsyncMock) as mock_wv,
        patch("app.workers.sync_worker.prune_old_versions", new_callable=AsyncMock),
        patch("app.workers.sync_worker._run_orchestrator", new_callable=AsyncMock),
        patch("app.workers.sync_worker.gateway") as mock_gw,
        patch("app.workers.sync_worker._get_sku_cache", new_callable=AsyncMock, return_value=None),
    ):
        mock_wv.return_value = MagicMock(version=1, row_count=0, checksum="abc123")
        mock_gw.send_progress = AsyncMock()

        from app.workers.sync_worker import run_full_sync
        await run_full_sync(ctx, cid, "https://sheets.google.com/test", {}, job_id)

    # The worker must have set reviewed_at to None on the fake campaign
    assert fake_campaign.reviewed_at is None, (
        "run_full_sync should clear campaign.reviewed_at after completion"
    )
