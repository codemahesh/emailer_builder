"""
artist_agent.py
===============
Pure async module for DALL-E 3 banner image generation.

Security note: ``dalle_prompt`` passed to this function comes from the
trusted visual orchestrator output (GPT-4o controlled system prompt), NOT
from raw user input.  The orchestrator constrains and sanitises the prompt
before it reaches here, so no additional prompt-injection defence is applied
at this layer.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def generate_banners(
    dalle_prompt: str,
    openai_api_key: str,
    num_variants: int = 3,
) -> list[str]:
    """Generate *num_variants* banner images via DALL-E 3.

    Parameters
    ----------
    dalle_prompt:
        Text prompt for DALL-E 3.  Must come from the orchestrator output,
        not from raw user input (see module docstring).
    openai_api_key:
        OpenAI API key.  If empty or falsy, returns [] immediately.
    num_variants:
        Number of images to generate (default 3).  DALL-E 3 only supports
        ``n=1`` per request, so we loop this many times.

    Returns
    -------
    list[str]
        List of image URLs returned by the OpenAI API.  Returns [] if the
        key is missing or any exception occurs.
    """
    if not openai_api_key:
        logger.debug("generate_banners: no openai_api_key — returning []")
        return []

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=openai_api_key)
        urls: list[str] = []

        for i in range(num_variants):
            try:
                response = await client.images.generate(
                    model="dall-e-3",
                    prompt=dalle_prompt,
                    n=1,
                    size="1792x1024",
                    response_format="url",
                )
                url = response.data[0].url
                if url:
                    urls.append(url)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "generate_banners: variant %d failed (%s)", i, exc
                )
                # Return what we have so far rather than failing everything
                return urls

        return urls

    except Exception as exc:  # noqa: BLE001
        logger.warning("generate_banners: unexpected error (%s)", exc)
        return []
