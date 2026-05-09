"""
sku_cache.py
============
Redis-based SKU → processed image URL cache.

TTL defaults to 30 days. Manual overrides are stored with a "manual:" key
prefix so they can be distinguished from auto-processed results.
"""

from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "sku_image:"
_MANUAL_PREFIX = "sku_image:manual:"


class SKUCache:
    """Redis-backed cache mapping SKU strings to processed image URLs."""

    def __init__(self, redis_client: aioredis.Redis, ttl: int = 86400 * 30) -> None:
        """
        Parameters
        ----------
        redis_client:
            An async redis.asyncio client instance.
        ttl:
            Time-to-live in seconds. Defaults to 30 days.
        """
        self.redis = redis_client
        self.ttl = ttl

    def _key(self, sku: str) -> str:
        return f"{_KEY_PREFIX}{sku}"

    def _manual_key(self, sku: str) -> str:
        return f"{_MANUAL_PREFIX}{sku}"

    async def get(self, sku: str) -> Optional[str]:
        """
        Return the cached processed image URL for *sku*, or ``None`` if not cached.

        Checks manual override key first, then the auto-processed key.
        """
        try:
            # Check manual override first
            value = await self.redis.get(self._manual_key(sku))
            if value is not None:
                return str(value)
            # Fall back to auto-processed
            value = await self.redis.get(self._key(sku))
            if value is not None:
                return str(value)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("SKUCache.get: Redis error for sku=%s (%s)", sku, exc)
            return None

    async def set(self, sku: str, url: str) -> None:
        """Cache the auto-processed image URL for *sku*."""
        try:
            await self.redis.set(self._key(sku), url, ex=self.ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SKUCache.set: Redis error for sku=%s (%s)", sku, exc)

    async def delete(self, sku: str) -> None:
        """
        Remove both the auto-processed and manual override cache entries for *sku*.

        Called when a manual override is being cleared or product is removed.
        """
        try:
            await self.redis.delete(self._key(sku), self._manual_key(sku))
        except Exception as exc:  # noqa: BLE001
            logger.warning("SKUCache.delete: Redis error for sku=%s (%s)", sku, exc)

    async def set_override(self, sku: str, url: str) -> None:
        """
        Write a manual override URL directly to the cache.

        Uses a ``"manual:"`` prefix so it can be distinguished from
        auto-processed results. Manual overrides bypass normal processing.
        """
        try:
            await self.redis.set(self._manual_key(sku), url, ex=self.ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "SKUCache.set_override: Redis error for sku=%s (%s)", sku, exc
            )
