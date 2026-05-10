"""
image_store.py
==============
ImageStore interface with local filesystem adapter.

Stores images in ./static/images/ and serves them via /static/images/<filename>.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import aiofiles


class ImageStoreProtocol(Protocol):
    async def write(self, data: bytes, filename: str) -> str: ...
    async def read(self, url: str) -> bytes: ...


class LocalImageStore:
    """Stores images in ./static/images/ and serves via /static/images/<filename>"""

    def __init__(
        self,
        base_dir: str = "static/images",
        base_url: str = "/static/images",
    ) -> None:
        self.base_dir = Path(base_dir)
        self.base_url = base_url.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def write(self, data: bytes, filename: str) -> str:
        """Write bytes to file, return URL path.

        Parameters
        ----------
        data:
            Raw bytes of the image.
        filename:
            Target filename (e.g. ``"abc123.jpg"``).

        Returns
        -------
        str
            The URL path under which the image is served
            (e.g. ``"/static/images/abc123.jpg"``).
        """
        dest = self.base_dir / filename
        async with aiofiles.open(dest, "wb") as f:
            await f.write(data)
        return f"{self.base_url}/{filename}"

    async def read(self, url: str) -> bytes:
        """Read bytes from file path derived from URL.

        Parameters
        ----------
        url:
            URL path returned by :meth:`write`
            (e.g. ``"/static/images/abc123.jpg"``).

        Returns
        -------
        bytes
            Raw image bytes.
        """
        # Strip base_url prefix to get the filename
        filename = url
        if filename.startswith(self.base_url):
            filename = filename[len(self.base_url):].lstrip("/")
        filepath = self.base_dir / filename
        async with aiofiles.open(filepath, "rb") as f:
            return await f.read()


# Singleton for use across the app
image_store = LocalImageStore()
