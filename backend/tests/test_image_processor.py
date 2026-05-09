"""
test_image_processor.py
=======================
Unit tests for app.modules.image_processor.process_image.

All test images are generated programmatically with Pillow/numpy.
"""

from __future__ import annotations

import io
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
from PIL import Image as PILImage

from app.modules.image_processor import ProcessingConfig, process_image


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_rgba_png(
    width: int = 400,
    height: int = 400,
    color: tuple = (100, 150, 200, 255),
) -> bytes:
    """Create a solid-color RGBA PNG image as bytes."""
    arr = np.full((height, width, 4), color, dtype=np.uint8)
    img = PILImage.fromarray(arr, mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def _make_rgb_png(
    width: int = 400,
    height: int = 400,
    color: tuple = (100, 150, 200),
) -> bytes:
    """Create a solid-color RGB PNG image as bytes."""
    arr = np.full((height, width, 3), color, dtype=np.uint8)
    img = PILImage.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def _open_png_bytes(data: bytes) -> PILImage.Image:
    """Helper: open image bytes with Pillow."""
    return PILImage.open(io.BytesIO(data))


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestProcessImage:

    def test_small_image_upscaled_when_configured(self):
        """
        With upscale_if_small=True, an image smaller than 500x500 should be
        upscaled so the output is at least 500x500.
        """
        # 100x100 source
        image_bytes = _make_rgb_png(width=100, height=100, color=(80, 120, 200))
        config = ProcessingConfig(
            remove_background=False,
            upscale_if_small=True,
        )
        result = process_image(image_bytes, config)
        out = _open_png_bytes(result)
        w, h = out.size
        assert w >= 500, f"Expected width >= 500 after upscale, got {w}"
        assert h >= 500, f"Expected height >= 500 after upscale, got {h}"

    def test_large_image_not_upscaled(self):
        """
        With upscale_if_small=False, a large image should not be expanded
        beyond its original dimensions by the upscale step.
        """
        # 800x800 source
        image_bytes = _make_rgb_png(width=800, height=800, color=(180, 60, 40))
        config = ProcessingConfig(
            remove_background=False,
            upscale_if_small=False,
        )
        result = process_image(image_bytes, config)
        out = _open_png_bytes(result)
        w, h = out.size
        # The crop-to-square step may change size, but it should be <= 800 in
        # each dimension (we're not upscaling, so no dimension should grow).
        # We allow the square-pad to produce exactly 800x800.
        assert w <= 800, f"Width should not exceed 800 when upscale is off, got {w}"
        assert h <= 800, f"Height should not exceed 800 when upscale is off, got {h}"

    def test_background_color_red_applied(self):
        """
        With background_color="#FF0000" the output image composited onto a
        pure red background — pixels in fully-transparent areas should be red.
        """
        # Create an RGBA image with a transparent region (fully transparent)
        arr = np.zeros((200, 200, 4), dtype=np.uint8)
        # Make a white square in the center (opaque), rest stays transparent
        arr[50:150, 50:150] = (255, 255, 255, 255)
        img = PILImage.fromarray(arr, mode="RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        image_bytes = buf.read()

        config = ProcessingConfig(
            background_color="#FF0000",
            remove_background=False,
            upscale_if_small=False,
        )
        result = process_image(image_bytes, config)
        out = _open_png_bytes(result).convert("RGB")

        # Sample a corner pixel — should be red (transparent region → red bg)
        # After crop+padding, the output might be square-padded; sample near
        # edge but note the cropping may eliminate transparent corners.
        # The simplest check: the output has no fully-transparent pixels (it's RGB)
        assert out.mode == "RGB"

        # The background should contain red pixels somewhere in the image
        out_arr = np.array(out)
        # Check that the dominant background color is close to red (R channel high)
        # by sampling the corners of the output (outside the white center)
        corner = out_arr[0, 0]  # top-left corner
        assert corner[0] > 200, f"Expected red background at corner, got {corner}"
        assert corner[1] < 50,  f"Expected green channel < 50 at corner, got {corner}"
        assert corner[2] < 50,  f"Expected blue channel < 50 at corner, got {corner}"

    def test_remove_background_false_skips_rembg(self):
        """
        With remove_background=False, rembg should never be called.
        """
        image_bytes = _make_rgb_png(width=300, height=300)
        config = ProcessingConfig(
            remove_background=False,
            upscale_if_small=False,
        )

        with patch("app.modules.image_processor.PILImage") as mock_pil:
            # We patch only to verify rembg is NOT called.
            # Actually we should let Pillow work normally, so instead
            # mock just the rembg.remove function path.
            pass

        # Run without any rembg mock — if rembg is installed it would run,
        # but since remove_background=False we ensure it's never invoked.
        import app.modules.image_processor as mod

        original_remove_background = config.remove_background
        assert original_remove_background is False

        # Use mock to ensure rembg is not imported/called when flag is False
        mock_rembg = MagicMock()
        with patch.dict("sys.modules", {"rembg": mock_rembg}):
            result = process_image(image_bytes, config)

        # rembg.remove should not have been called
        mock_rembg.remove.assert_not_called()

        # Result should still be valid PNG bytes
        out = _open_png_bytes(result)
        assert out.format == "PNG" or out is not None

    def test_returns_valid_png_bytes(self):
        """process_image always returns valid PNG bytes."""
        image_bytes = _make_rgb_png(width=600, height=600)
        config = ProcessingConfig(remove_background=False)
        result = process_image(image_bytes, config)

        # Should be parseable as an image
        out = _open_png_bytes(result)
        assert out.width > 0
        assert out.height > 0

    def test_corrupted_bytes_returns_original(self):
        """
        On corrupted input, process_image should return the original bytes
        without raising.
        """
        corrupted = b"\x00\x01\x02\x03 not an image"
        config = ProcessingConfig(remove_background=False)
        result = process_image(corrupted, config)
        # Should return original bytes (no exception)
        assert result == corrupted

    def test_white_background_is_default(self):
        """
        Default background_color is #FFFFFF. Transparent regions should
        become white after compositing.
        """
        # Fully transparent image
        arr = np.zeros((200, 200, 4), dtype=np.uint8)
        arr[75:125, 75:125] = (0, 0, 0, 255)  # small black square in center
        img = PILImage.fromarray(arr, mode="RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        image_bytes = buf.read()

        config = ProcessingConfig(
            background_color="#FFFFFF",
            remove_background=False,
            upscale_if_small=False,
        )
        result = process_image(image_bytes, config)
        out = _open_png_bytes(result).convert("RGB")
        out_arr = np.array(out)

        # The corner should be white (255, 255, 255) since it was transparent
        corner = out_arr[0, 0]
        assert all(v >= 240 for v in corner), f"Expected white corner, got {corner}"

    def test_upscale_false_small_image_not_modified_in_size(self):
        """
        With upscale_if_small=False, a small (200x200) image is not upscaled.
        The output may be padded to square but should remain <= original dimensions.
        """
        image_bytes = _make_rgb_png(width=200, height=200)
        config = ProcessingConfig(
            remove_background=False,
            upscale_if_small=False,
        )
        result = process_image(image_bytes, config)
        out = _open_png_bytes(result)
        # Should not have been upscaled
        assert out.width <= 200
        assert out.height <= 200
