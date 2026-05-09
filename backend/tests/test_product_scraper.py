"""
test_product_scraper.py
=======================
Unit tests for app.modules.product_scraper using httpx + respx mocking.
"""

from __future__ import annotations

import pytest
import respx
import httpx

from app.modules.product_scraper import scrape_product, ScrapeResult


# ── Fixtures / helpers ────────────────────────────────────────────────────────

_PRODUCT_URL = "https://example.com/products/widget-pro"

_HTML_WITH_OG = """
<!DOCTYPE html>
<html>
<head>
  <meta property="og:title" content="Widget Pro Deluxe" />
  <meta property="og:image" content="https://cdn.example.com/images/widget-pro.jpg" />
  <title>Widget Pro Deluxe | Example Store</title>
</head>
<body>
  <h1>Widget Pro Deluxe</h1>
</body>
</html>
"""

_HTML_WITHOUT_IMAGES = """
<!DOCTYPE html>
<html>
<head>
  <title>Widget Pro | Example Store</title>
</head>
<body>
  <h1>Widget Pro</h1>
  <p>No images on this page.</p>
</body>
</html>
"""

_HTML_NO_NAME_NO_IMAGE = """
<!DOCTYPE html>
<html>
<head></head>
<body><p>Nothing here</p></body>
</html>
"""


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_scrape_product_returns_og_image_and_name():
    """When page has og:image and og:title, scrape_product returns them."""
    respx.get(_PRODUCT_URL).mock(
        return_value=httpx.Response(
            200,
            text=_HTML_WITH_OG,
            headers={"content-type": "text/html; charset=utf-8"},
        )
    )

    result = await scrape_product(_PRODUCT_URL)

    assert result.success is True
    assert result.image_url == "https://cdn.example.com/images/widget-pro.jpg"
    assert result.product_name == "Widget Pro Deluxe"
    assert result.failure_reason is None


@pytest.mark.asyncio
@respx.mock
async def test_scrape_product_no_images_returns_failure():
    """When the page has no images at all, returns ScrapeResult(success=False)."""
    respx.get(_PRODUCT_URL).mock(
        return_value=httpx.Response(
            200,
            text=_HTML_NO_NAME_NO_IMAGE,
            headers={"content-type": "text/html; charset=utf-8"},
        )
    )

    result = await scrape_product(_PRODUCT_URL)

    assert result.success is False
    assert result.image_url is None
    assert result.product_name is None
    assert result.failure_reason is not None


@pytest.mark.asyncio
@respx.mock
async def test_scrape_product_connection_error():
    """On connection error, returns ScrapeResult(success=False) with a reason."""
    respx.get(_PRODUCT_URL).mock(side_effect=httpx.ConnectError("Connection refused"))

    result = await scrape_product(_PRODUCT_URL)

    assert result.success is False
    assert result.failure_reason is not None
    assert "connection" in result.failure_reason.lower() or "connect" in result.failure_reason.lower()


@pytest.mark.asyncio
@respx.mock
async def test_scrape_product_404_response():
    """On 404 response, returns ScrapeResult(success=False, failure_reason contains '404')."""
    respx.get(_PRODUCT_URL).mock(
        return_value=httpx.Response(
            404,
            text="Not Found",
            headers={"content-type": "text/html"},
        )
    )

    result = await scrape_product(_PRODUCT_URL)

    assert result.success is False
    assert result.failure_reason is not None
    assert "404" in result.failure_reason


@pytest.mark.asyncio
@respx.mock
async def test_scrape_product_timeout():
    """On timeout, returns ScrapeResult(success=False) with a timeout reason."""
    respx.get(_PRODUCT_URL).mock(side_effect=httpx.TimeoutException("Read timeout"))

    result = await scrape_product(_PRODUCT_URL)

    assert result.success is False
    assert result.failure_reason is not None
    assert "time" in result.failure_reason.lower() or "timeout" in result.failure_reason.lower()


@pytest.mark.asyncio
@respx.mock
async def test_scrape_product_has_name_but_no_image():
    """When page has a product name but no image, success is still True (partial data)."""
    respx.get(_PRODUCT_URL).mock(
        return_value=httpx.Response(
            200,
            text=_HTML_WITHOUT_IMAGES,
            headers={"content-type": "text/html; charset=utf-8"},
        )
    )

    result = await scrape_product(_PRODUCT_URL)

    # The page has a title but no images — success because we got a name
    assert result.success is True
    assert result.product_name is not None
    assert result.image_url is None


@pytest.mark.asyncio
async def test_scrape_product_empty_url():
    """Empty URL returns ScrapeResult(success=False) immediately."""
    result = await scrape_product("")
    assert result.success is False
    assert result.failure_reason is not None


@pytest.mark.asyncio
@respx.mock
async def test_scrape_product_non_html_content_type():
    """Non-HTML content-type returns failure."""
    respx.get(_PRODUCT_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"GIF89a...",
            headers={"content-type": "image/gif"},
        )
    )

    result = await scrape_product(_PRODUCT_URL)

    assert result.success is False
    assert result.failure_reason is not None
