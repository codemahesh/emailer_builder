"""
test_artist_agent.py
====================
Tests for the ``generate_banners`` async function in
``app.modules.artist_agent``.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_generate_banners_returns_empty_when_no_key():
    """generate_banners returns [] immediately when openai_api_key is empty string."""
    from app.modules.artist_agent import generate_banners

    result = await generate_banners("a cool banner", "")
    assert result == []


@pytest.mark.asyncio
async def test_generate_banners_returns_empty_when_key_is_none():
    """generate_banners returns [] when openai_api_key is None (coerced to falsy)."""
    from app.modules.artist_agent import generate_banners

    # None is falsy — same early-return path as empty string
    result = await generate_banners("a cool banner", None)  # type: ignore[arg-type]
    assert result == []


@pytest.mark.asyncio
async def test_generate_banners_returns_empty_when_openai_raises():
    """generate_banners returns [] when the OpenAI client raises an exception."""
    from app.modules.artist_agent import generate_banners

    mock_image_data = MagicMock()
    mock_image_data.url = "https://example.com/image.png"

    mock_response = MagicMock()
    mock_response.data = [mock_image_data]

    # Simulate the client raising on the first call
    mock_images = MagicMock()
    mock_images.generate = AsyncMock(side_effect=RuntimeError("API error"))

    mock_client = MagicMock()
    mock_client.images = mock_images

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        result = await generate_banners("a cool banner", "sk-fake-key", num_variants=3)

    assert result == []


@pytest.mark.asyncio
async def test_generate_banners_returns_urls_on_success():
    """generate_banners returns a list of URLs when calls succeed."""
    from app.modules.artist_agent import generate_banners

    mock_image_data = MagicMock()
    mock_image_data.url = "https://example.com/banner.png"

    mock_response = MagicMock()
    mock_response.data = [mock_image_data]

    mock_images = MagicMock()
    mock_images.generate = AsyncMock(return_value=mock_response)

    mock_client = MagicMock()
    mock_client.images = mock_images

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        result = await generate_banners("a cool banner", "sk-fake-key", num_variants=2)

    assert len(result) == 2
    assert all(url == "https://example.com/banner.png" for url in result)
