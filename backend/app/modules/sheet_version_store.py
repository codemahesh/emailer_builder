"""
sheet_version_store.py
======================

Persistence helpers for immutable sheet-import snapshots.

Each successful import writes a ``SheetVersion`` header row and one
``SheetVersionRow`` per product. A SHA-256 checksum over the canonical
row set enables cheap deduplication: identical successive imports do not
create a new version.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sheet_version import SheetVersion, SheetVersionRow


def compute_checksum(rows: list[dict]) -> str:
    """
    SHA-256 over the canonical sorted JSON of *rows*.

    Order-independent: the same set of rows produces the same digest
    regardless of their input order.
    """
    normalized = sorted(
        json.dumps(dict(sorted(r.items())), sort_keys=True, ensure_ascii=False)
        for r in rows
    )
    payload = json.dumps(normalized, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


async def latest_version(
    session: AsyncSession,
    campaign_id: uuid.UUID,
) -> Optional[SheetVersion]:
    """Return the most recent SheetVersion for a campaign, or None."""
    result = await session.execute(
        select(SheetVersion)
        .where(SheetVersion.campaign_id == campaign_id)
        .order_by(SheetVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def write_version(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    rows: list[dict],
    source: str,
    source_ref: str,
    imported_by: Optional[uuid.UUID] = None,
) -> SheetVersion:
    """
    Persist a new SheetVersion + per-row snapshots.

    If the checksum matches the latest existing version the write is
    skipped and the existing version is returned unchanged.

    Parameters
    ----------
    session:     Active async SQLAlchemy session.
    campaign_id: Campaign this version belongs to.
    rows:        Normalized product-row dicts (canonical field names).
    source:      ``"link"`` or ``"upload"``.
    source_ref:  Sheet URL or uploaded filename.
    imported_by: User UUID who triggered the import (optional).
    """
    checksum = compute_checksum(rows)

    prior = await latest_version(session, campaign_id)
    if prior is not None and prior.checksum == checksum:
        return prior

    # Determine next version number
    version_num_result = await session.execute(
        select(func.max(SheetVersion.version)).where(
            SheetVersion.campaign_id == campaign_id
        )
    )
    max_version: Optional[int] = version_num_result.scalar_one_or_none()
    next_version = (max_version or 0) + 1

    sv = SheetVersion(
        campaign_id=campaign_id,
        version=next_version,
        source=source,
        source_ref=source_ref,
        imported_by=imported_by,
        row_count=len(rows),
        checksum=checksum,
    )
    session.add(sv)
    await session.flush()
    await session.refresh(sv)

    for position, row in enumerate(rows):
        session.add(
            SheetVersionRow(
                version_id=sv.id,
                position=position,
                data_json=json.dumps(row, ensure_ascii=False),
            )
        )

    return sv


async def prune_old_versions(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    keep: int = 10,
) -> None:
    """
    Delete all but the newest *keep* versions for *campaign_id*.

    Executes in a single DELETE statement. Child ``sheet_version_rows``
    rows are removed via CASCADE.
    """
    # Subquery: IDs of the newest `keep` versions (ordered newest-first)
    newest_ids_sq = (
        select(SheetVersion.id)
        .where(SheetVersion.campaign_id == campaign_id)
        .order_by(SheetVersion.version.desc())
        .limit(keep)
        .scalar_subquery()
    )

    await session.execute(
        delete(SheetVersion).where(
            SheetVersion.campaign_id == campaign_id,
            SheetVersion.id.not_in(newest_ids_sq),
        )
    )
