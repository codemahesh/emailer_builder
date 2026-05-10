"""
preference_memory.py
====================
PreferenceMemory — stores and retrieves editor preference signals.

Public interface:
  record_signal(db, editor_id, signal_type, asset_type, signal_value, campaign_id, weight) → UserPreference
  get_context(db, editor_id) → str  # natural language, max 10 signals
  reset(db, editor_id) → int  # rows deleted
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preference import UserPreference

logger = logging.getLogger(__name__)

# Map signal types to human-readable sentiment markers
_SIGNAL_SENTIMENT: dict[str, str] = {
    "explicit_positive": "+",
    "implicit_accept": "+",
    "explicit_negative": "-",
    "implicit_revert": "-",
}

_SIGNAL_VERB: dict[str, str] = {
    "explicit_positive": "Prefers",
    "implicit_accept": "Accepted",
    "explicit_negative": "Avoids",
    "implicit_revert": "Reverted from",
}


async def record_signal(
    db: AsyncSession,
    editor_id: uuid.UUID,
    signal_type: str,
    asset_type: str,
    signal_value: str,
    campaign_id: Optional[uuid.UUID] = None,
    weight: float = 1.0,
) -> UserPreference:
    """
    Insert a new UserPreference signal row.

    Parameters
    ----------
    db:
        Active async DB session.
    editor_id:
        UUID of the editor generating the signal.
    signal_type:
        One of "explicit_positive", "explicit_negative", "implicit_accept", "implicit_revert".
    asset_type:
        Type of asset, e.g. "banner", "theme", "layout", "template".
    signal_value:
        Descriptive value, e.g. a theme name or layout type.
    campaign_id:
        Optional campaign context.
    weight:
        Signal weight. implicit_revert should use 3.0.

    Returns
    -------
    UserPreference
        The newly created preference row.
    """
    preference = UserPreference(
        editor_id=editor_id,
        signal_type=signal_type,
        asset_type=asset_type,
        signal_value=signal_value,
        campaign_id=campaign_id,
        weight=weight,
    )
    db.add(preference)
    await db.flush()
    await db.refresh(preference)

    logger.info(
        "record_signal: editor=%s signal_type=%s asset_type=%s value=%s weight=%s",
        editor_id,
        signal_type,
        asset_type,
        signal_value,
        weight,
    )
    return preference


async def get_context(db: AsyncSession, editor_id: uuid.UUID) -> str:
    """
    Retrieve the top 10 preference signals for the editor (by weight DESC, created_at DESC)
    and return a natural-language summary string.

    Returns "No preferences recorded." if no signals exist.
    """
    result = await db.execute(
        select(UserPreference)
        .where(UserPreference.editor_id == editor_id)
        .order_by(UserPreference.weight.desc(), UserPreference.created_at.desc())
        .limit(10)
    )
    preferences = list(result.scalars().all())

    if not preferences:
        return "No preferences recorded."

    parts: list[str] = []
    for pref in preferences:
        verb = _SIGNAL_VERB.get(pref.signal_type, "Interacted with")
        sentiment = _SIGNAL_SENTIMENT.get(pref.signal_type, "")
        sentiment_str = f" ({sentiment})" if sentiment else ""
        part = f"{verb} {pref.signal_value} {pref.asset_type}{sentiment_str}"
        parts.append(part)

    return "Preferences: " + ". ".join(parts) + "."


async def reset(db: AsyncSession, editor_id: uuid.UUID) -> int:
    """
    Delete all UserPreference rows for the given editor.

    Returns
    -------
    int
        Number of rows deleted.
    """
    # Count before delete
    count_result = await db.execute(
        select(func.count()).where(UserPreference.editor_id == editor_id)
    )
    count = count_result.scalar_one() or 0

    await db.execute(
        delete(UserPreference).where(UserPreference.editor_id == editor_id)
    )
    await db.flush()

    logger.info("reset: deleted %d preferences for editor=%s", count, editor_id)
    return count
