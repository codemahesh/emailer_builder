"""
import_worker.py
===============
ARQ worker task: smart re-scrape only for products whose product_link changed.

Task: ``run_import_scrape(ctx, campaign_id, product_ids, job_id)``

Only re-scrapes the given product IDs; skips products with unchanged links
and always preserves ManualOverride records (no processed_image_url reset
when override exists).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from arq import ArqRedis
from sqlalchemy import select

from app.database import async_session_maker
from app.models.manual_override import ManualOverride
from app.models.product import Product
from app.models.sync_job import SyncJob, SyncJobStatus
from app.modules.product_scraper import scrape_product

logger = logging.getLogger(__name__)

_REDIS_KEY_PREFIX = "sync_status:"


async def run_import_scrape(
    ctx: dict,
    campaign_id: str,
    product_ids: list[str],
    job_id: str | None = None,
) -> dict:
    """
    ARQ task: scrape only the products listed in *product_ids*.

    Preserves ``processed_image_url`` for any product that has a
    ManualOverride record (target_type="product_image").

    Returns a summary dict.
    """
    redis: ArqRedis = ctx["redis"]
    cid = str(campaign_id)

    # Mark job running
    if job_id:
        async with async_session_maker() as session:
            result = await session.execute(
                select(SyncJob).where(SyncJob.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if job:
                job.status = SyncJobStatus.running
                job.started_at = datetime.now(timezone.utc)
                job.total_products = len(product_ids)
                await session.commit()

    imported = 0
    failed = 0

    async with async_session_maker() as session:
        # Collect product IDs that have a manual image override
        override_result = await session.execute(
            select(ManualOverride.target_id).where(
                ManualOverride.campaign_id == uuid.UUID(cid),
                ManualOverride.target_type == "product_image",
            )
        )
        overridden_ids: set[str] = {str(r) for (r,) in override_result.all() if r}

        for pid in product_ids:
            try:
                prod_result = await session.execute(
                    select(Product).where(Product.id == uuid.UUID(pid))
                )
                product = prod_result.scalar_one_or_none()
                if product is None:
                    continue

                result = await scrape_product(product.product_link)

                if result.success:
                    product.scraped_name = result.product_name
                    product.scraped_image_url = result.image_url
                    product.scrape_failed = False
                    # Only update processed_image_url if no manual override exists
                    if pid not in overridden_ids:
                        product.processed_image_url = result.image_url
                else:
                    product.scrape_failed = True
                    failed += 1

                imported += 1
                await session.flush()

            except Exception:  # noqa: BLE001
                logger.warning("run_import_scrape: failed for product %s", pid, exc_info=True)
                failed += 1

        try:
            await session.commit()
        except Exception:  # noqa: BLE001
            await session.rollback()
            logger.warning("run_import_scrape: commit failed")

    final_status = SyncJobStatus.completed if failed == 0 else SyncJobStatus.partial

    if job_id:
        async with async_session_maker() as session:
            result = await session.execute(
                select(SyncJob).where(SyncJob.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if job:
                job.status = final_status
                job.processed_products = imported
                job.failed_products = failed
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()

    # Write final status to Redis
    try:
        last_synced = datetime.now(timezone.utc).isoformat()
        await redis.set(
            f"{_REDIS_KEY_PREFIX}{cid}",
            __import__("json").dumps({
                "status": "done" if failed == 0 else "partial",
                "total": len(product_ids),
                "imported": imported,
                "failed": failed,
                "last_synced": last_synced,
            }),
            ex=3600,
        )
    except Exception:  # noqa: BLE001
        pass

    logger.info(
        "run_import_scrape: campaign %s done — %d/%d scraped, %d failed",
        cid,
        imported,
        len(product_ids),
        failed,
    )
    return {"campaign_id": cid, "imported": imported, "failed": failed}
