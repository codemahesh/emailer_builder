"""
artist_worker.py
================
ARQ worker task: generate DALL-E 3 banner images for a campaign.

Task: ``run_artist_generation(ctx, campaign_id, dalle_prompt, job_id)``

Workflow
--------
1. Call ``generate_banners(dalle_prompt, settings.openai_api_key)``.
2. For each returned URL (up to 3):
   a. Download image bytes via httpx.
   b. Persist to image_store as ``banner_{campaign_id}_{i}.png``.
   c. Update the matching Banner row (variant_index=i) → status "ready".
   d. Emit ``banner_ready`` WebSocket event.
3. If generate_banners returns [] (no key / API error):
   - Mark all Banner rows for this campaign as "failed".
   - Emit ``banner_ready`` with url="" for each variant.

All errors are caught; the task never raises.
"""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime, timezone

import httpx
from arq.connections import RedisSettings
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models.banner import Banner
from app.modules.artist_agent import generate_banners
from app.modules.image_store import image_store
from app.ws.gateway import gateway

logger = logging.getLogger(__name__)

_MAX_VARIANTS = 3


def _parse_redis_url(url: str) -> RedisSettings:
    """Parse redis://host:port[/db] into an ARQ RedisSettings."""
    import re

    m = re.match(r"redis://([^:/]+)(?::(\d+))?(?:/(\d+))?", url)
    if m:
        host = m.group(1) or "localhost"
        port = int(m.group(2)) if m.group(2) else 6379
        database = int(m.group(3)) if m.group(3) else 0
        return RedisSettings(host=host, port=port, database=database)
    return RedisSettings(host="localhost", port=6379)


async def _download_image_bytes(url: str) -> bytes | None:
    """Download image bytes from *url*.  Returns None on any failure."""
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.content
            logger.warning(
                "_download_image_bytes: HTTP %d for %s", response.status_code, url
            )
            return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("_download_image_bytes: failed for %s (%s)", url, exc)
        return None


async def run_artist_generation(
    ctx: dict,
    campaign_id: str,
    dalle_prompt: str,
    job_id: str | None = None,
) -> dict:
    """
    ARQ task: generate banner images for *campaign_id*.

    Parameters
    ----------
    ctx:
        ARQ context dict.
    campaign_id:
        UUID string of the campaign.
    dalle_prompt:
        DALL-E prompt from the visual orchestrator output.
    job_id:
        Optional job identifier (unused, reserved for future tracking).

    Returns
    -------
    dict
        Summary with keys ``campaign_id``, ``status``, ``variants``.
    """
    cid = str(campaign_id)
    logger.info("run_artist_generation: starting for campaign %s", cid)

    try:
        urls = await generate_banners(dalle_prompt, settings.openai_api_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "run_artist_generation: generate_banners raised unexpectedly (%s)", exc
        )
        urls = []

    if not urls:
        # No key or API error — mark all Banner rows as failed
        logger.warning(
            "run_artist_generation: no images generated for campaign %s", cid
        )
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Banner).where(Banner.campaign_id == _uuid.UUID(cid))
                )
                banners = result.scalars().all()
                for banner in banners:
                    banner.generation_status = "failed"
                    banner.updated_at = datetime.now(timezone.utc)
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "run_artist_generation: failed to mark banners as failed (%s)", exc
            )

        # Emit banner_ready with empty url for each variant
        for i in range(_MAX_VARIANTS):
            try:
                await gateway.send_progress(
                    cid,
                    "banner_ready",
                    {"variant_index": i, "url": "", "campaign_id": cid},
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "run_artist_generation: WS emit failed for variant %d (%s)", i, exc
                )

        return {"campaign_id": cid, "status": "failed", "variants": 0}

    # Process each generated URL (up to _MAX_VARIANTS)
    processed = 0
    for i, raw_url in enumerate(urls[:_MAX_VARIANTS]):
        try:
            # Download image bytes
            image_bytes = await _download_image_bytes(raw_url)
            if image_bytes is None:
                logger.warning(
                    "run_artist_generation: download failed for variant %d", i
                )
                continue

            # Persist to image store
            filename = f"banner_{cid}_{i}.png"
            stored_url = await image_store.write(image_bytes, filename)

            # Update Banner row in DB
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Banner).where(
                        Banner.campaign_id == _uuid.UUID(cid),
                        Banner.variant_index == i,
                    )
                )
                banner = result.scalar_one_or_none()
                if banner is not None:
                    banner.image_url = stored_url
                    banner.generation_status = "ready"
                    banner.updated_at = datetime.now(timezone.utc)
                    await session.commit()
                else:
                    logger.warning(
                        "run_artist_generation: Banner row not found for "
                        "campaign %s variant_index %d",
                        cid,
                        i,
                    )

            # Emit WebSocket event
            await gateway.send_progress(
                cid,
                "banner_ready",
                {"variant_index": i, "url": stored_url, "campaign_id": cid},
            )
            processed += 1

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "run_artist_generation: error processing variant %d for campaign %s (%s)",
                i,
                cid,
                exc,
            )

    logger.info(
        "run_artist_generation: done for campaign %s — %d/%d variants processed",
        cid,
        processed,
        len(urls),
    )
    return {"campaign_id": cid, "status": "done", "variants": processed}


# ── ARQ WorkerSettings ────────────────────────────────────────────────────────


class WorkerSettings:
    """ARQ worker configuration — run with ``arq app.workers.artist_worker.WorkerSettings``."""

    functions = [run_artist_generation]
    redis_settings = _parse_redis_url(settings.redis_url)
    max_jobs = 5
    job_timeout = 300  # 5 minutes per generation job
    keep_result = 3600  # keep results for 1 hour
