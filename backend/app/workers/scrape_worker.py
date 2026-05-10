"""
scrape_worker.py
================
ARQ worker task: scrapes a single product page and updates the Product row.

Task: ``scrape_and_store(ctx, product_id)``
"""

from __future__ import annotations

import uuid
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.product import Product
from app.modules.product_scraper import scrape_product

logger = logging.getLogger(__name__)

_COMING_SOON_URL = "/static/coming-soon.svg"


async def scrape_and_store(ctx: dict, product_id: str) -> dict:
    """
    ARQ task. Fetches the Product row, runs the scraper, updates the DB.

    Parameters
    ----------
    ctx:
        ARQ context (contains redis pool etc.).
    product_id:
        UUID string of the product to scrape.

    Returns
    -------
    dict
        ``{"product_id": ..., "success": bool}``
    """
    pid = uuid.UUID(product_id)

    async with async_session_maker() as session:
        try:
            result = await session.execute(select(Product).where(Product.id == pid))
            product: Product | None = result.scalar_one_or_none()

            if product is None:
                logger.warning("scrape_and_store: product %s not found", product_id)
                return {"product_id": product_id, "success": False}

            scrape_result = await scrape_product(product.product_link)

            if scrape_result.success:
                product.scraped_name = scrape_result.product_name
                product.scraped_image_url = scrape_result.image_url
                product.scrape_failed = False
                logger.info("scrape_and_store: product %s scraped OK", product_id)
            else:
                product.scraped_image_url = _COMING_SOON_URL
                product.scrape_failed = True
                logger.warning(
                    "scrape_and_store: product %s scrape failed — %s",
                    product_id,
                    scrape_result.failure_reason,
                )

            await session.flush()
            await session.commit()

        except Exception:
            await session.rollback()
            logger.exception("scrape_and_store: unhandled error for product %s", product_id)
            return {"product_id": product_id, "success": False}

    return {"product_id": product_id, "success": scrape_result.success}
