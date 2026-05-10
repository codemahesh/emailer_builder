"""
product_scraper.py
==================
Pure async scraper — no DB dependencies.

Uses ``httpx`` + ``BeautifulSoup`` to extract a product name and primary
image URL from any product page URL.  Never raises: returns a
``ScrapeResult`` with ``success=False`` on every error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import httpx
from bs4 import BeautifulSoup

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_REQUEST_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


@dataclass
class ScrapeResult:
    success: bool
    product_name: Optional[str] = None
    image_url: Optional[str] = None
    failure_reason: Optional[str] = None


def _extract_name(soup: BeautifulSoup) -> Optional[str]:
    """Try several common patterns to extract a product name."""
    # 1. og:title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):  # type: ignore[union-attr]
        name = str(og_title["content"]).strip()  # type: ignore[index]
        if name:
            return name

    # 2. <title> tag (before first "|" or "-" separator)
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        raw = title_tag.string.strip()
        # Truncate at common page-title separators
        for sep in ["|", " - ", " – ", " — "]:
            if sep in raw:
                raw = raw.split(sep)[0].strip()
                break
        if raw:
            return raw

    # 3. <h1> (first, or with product-related class)
    for selector in [
        "h1.product-title",
        "h1.product_title",
        "h1.productTitle",
        "h1[itemprop='name']",
        "h1",
    ]:
        tag = soup.select_one(selector)
        if tag:
            name = tag.get_text(strip=True)
            if name:
                return name

    return None


def _extract_image(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Try several common patterns to find the best product image URL."""
    from urllib.parse import urljoin

    # 1. og:image
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):  # type: ignore[union-attr]
        url = str(og_image["content"]).strip()  # type: ignore[index]
        if url:
            return urljoin(base_url, url)

    # 2. Twitter card image
    twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter_image and twitter_image.get("content"):  # type: ignore[union-attr]
        url = str(twitter_image["content"]).strip()  # type: ignore[index]
        if url:
            return urljoin(base_url, url)

    # 3. Product-specific image selectors
    img_selectors = [
        "img.product-image",
        "img.product_image",
        "img.productImage",
        "img[itemprop='image']",
        ".product-gallery img",
        ".product__media img",
        "#product-image img",
        "img.wp-post-image",
    ]
    for sel in img_selectors:
        tag = soup.select_one(sel)
        if tag:
            src = tag.get("src") or tag.get("data-src") or tag.get("data-lazy-src")
            if src:
                return urljoin(base_url, str(src))

    # 4. Largest <img> by declared width attribute (> 200px)
    best_img: Optional[str] = None
    best_width = 200  # minimum threshold
    for img in soup.find_all("img"):
        try:
            w = int(img.get("width", 0))
        except (ValueError, TypeError):
            w = 0
        if w > best_width:
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not str(src).startswith("data:"):
                best_width = w
                best_img = urljoin(base_url, str(src))

    return best_img


async def scrape_product(url: str) -> ScrapeResult:
    """
    Scrape product name and primary image from *url*.

    Parameters
    ----------
    url:
        Full product page URL.

    Returns
    -------
    ScrapeResult
        Always returns a result; never raises.
        ``success=True`` when at least one of name/image was found.
    """
    if not url or not url.strip():
        return ScrapeResult(success=False, failure_reason="Empty URL")

    try:
        async with httpx.AsyncClient(
            headers=_REQUEST_HEADERS,
            timeout=15.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(url.strip())
    except httpx.TimeoutException:
        return ScrapeResult(success=False, failure_reason="Request timed out")
    except httpx.TooManyRedirects:
        return ScrapeResult(success=False, failure_reason="Too many redirects")
    except httpx.ConnectError as exc:
        return ScrapeResult(success=False, failure_reason=f"Connection error: {exc}")
    except httpx.RequestError as exc:
        return ScrapeResult(success=False, failure_reason=f"Request error: {exc}")

    if response.status_code == 404:
        return ScrapeResult(success=False, failure_reason="Page not found (404)")
    if response.status_code == 403:
        return ScrapeResult(success=False, failure_reason="Access forbidden (403)")
    if response.status_code >= 400:
        return ScrapeResult(
            success=False,
            failure_reason=f"HTTP error {response.status_code}",
        )

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        return ScrapeResult(
            success=False,
            failure_reason=f"Non-HTML content-type: {content_type}",
        )

    try:
        soup = BeautifulSoup(response.text, "lxml")
    except Exception as exc:  # noqa: BLE001
        try:
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as exc2:  # noqa: BLE001
            return ScrapeResult(
                success=False,
                failure_reason=f"HTML parse error: {exc2}",
            )

    base_url = str(response.url)
    product_name = _extract_name(soup)
    image_url = _extract_image(soup, base_url)

    if not product_name and not image_url:
        return ScrapeResult(
            success=False,
            failure_reason="No product name or image found on page",
        )

    return ScrapeResult(
        success=True,
        product_name=product_name,
        image_url=image_url,
    )
