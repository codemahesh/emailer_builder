"""
test_image_quality_gate.py
==========================
Unit tests for app.modules.image_quality_gate.check_image_quality.

Images are generated programmatically so the tests have no external
file dependencies.
"""

from __future__ import annotations

import io

import numpy as np
import pytest

try:
    import cv2  # type: ignore[import]
    _CV2_AVAILABLE = True
except ImportError:
    cv2 = None  # type: ignore[assignment]
    _CV2_AVAILABLE = False

from PIL import Image as PILImage

from app.modules.image_quality_gate import (
    BLUR_THRESHOLD,
    MIN_DIMENSION,
    QualityVerdict,
    check_image_quality,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_solid_png(width: int = 600, height: int = 600, color: tuple = (200, 150, 100)) -> bytes:
    """Generate a solid-color PNG image as bytes."""
    arr = np.full((height, width, 3), color, dtype=np.uint8)
    img = PILImage.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def _make_blurry_png(width: int = 600, height: int = 600, kernel_size: int = 51) -> bytes:
    """
    Generate a blurry PNG: start with a sharp gradient, then apply a large
    Gaussian blur so the Laplacian variance drops well below BLUR_THRESHOLD.
    """
    if cv2 is None:
        pytest.skip("cv2 not available — cannot generate blurry image")

    # Create a gradient image with visible edges
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for i in range(width):
        arr[:, i, :] = int(i * 255 / width)

    # Apply a heavy Gaussian blur
    blurred = cv2.GaussianBlur(arr, (kernel_size, kernel_size), 0)
    img = PILImage.fromarray(blurred, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCheckImageQuality:

    def test_sharp_image_passes(self):
        """A sharp image at or above MIN_DIMENSION should PASS."""
        # Use a checkerboard pattern which gives a high Laplacian variance
        arr = np.zeros((600, 600, 3), dtype=np.uint8)
        arr[::2, ::2] = 255   # alternating white squares
        arr[1::2, 1::2] = 255
        img = PILImage.fromarray(arr, mode="RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        image_bytes = buf.read()

        result = check_image_quality(image_bytes)

        assert result.verdict == QualityVerdict.PASS, (
            f"Expected PASS, got {result.verdict}: {result.reason}"
        )
        assert result.width == 600
        assert result.height == 600

    def test_tiny_image_warns(self):
        """An image below MIN_DIMENSION on either axis should WARN, not FAIL."""
        # 100x100 is small but still a valid sharp image (checkerboard = high sharpness)
        size = 100
        arr = np.zeros((size, size, 3), dtype=np.uint8)
        arr[::2, ::2] = 255
        arr[1::2, 1::2] = 255
        img = PILImage.fromarray(arr, mode="RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        image_bytes = buf.read()

        result = check_image_quality(image_bytes)

        # If cv2 is not available, blur check is skipped and we go straight to
        # dimension check, so WARN is still expected.
        assert result.verdict == QualityVerdict.WARN, (
            f"Expected WARN, got {result.verdict}: {result.reason}"
        )
        assert result.width == size
        assert result.height == size
        assert "resolution" in result.reason.lower() or "low" in result.reason.lower()

    @pytest.mark.skipif(not _CV2_AVAILABLE, reason="cv2 required to generate blurry image")
    def test_blurry_image_fails(self):
        """A heavily blurred image should FAIL the quality gate."""
        image_bytes = _make_blurry_png(width=600, height=600, kernel_size=99)
        result = check_image_quality(image_bytes)
        assert result.verdict == QualityVerdict.FAIL, (
            f"Expected FAIL, got {result.verdict} (blur_score={result.blur_score:.2f})"
        )
        assert result.blur_score < BLUR_THRESHOLD
        assert "blur" in result.reason.lower()

    def test_corrupted_bytes_fails_without_exception(self):
        """Passing garbage bytes must return FAIL — never raise."""
        corrupted = b"\x00\x01\x02\x03\xFF\xFE garbage data that is not a valid image"
        result = check_image_quality(corrupted)
        assert result.verdict == QualityVerdict.FAIL
        # Must not raise

    def test_empty_bytes_fails_without_exception(self):
        """Empty bytes must return FAIL — never raise."""
        result = check_image_quality(b"")
        assert result.verdict == QualityVerdict.FAIL

    def test_result_fields_populated_on_pass(self):
        """QualityResult should have populated width, height, blur_score on PASS."""
        arr = np.zeros((600, 600, 3), dtype=np.uint8)
        arr[::2, ::2] = 255
        arr[1::2, 1::2] = 255
        img = PILImage.fromarray(arr, mode="RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        result = check_image_quality(buf.read())

        assert result.width > 0
        assert result.height > 0

    def test_image_exactly_at_min_dimension_passes(self):
        """An image exactly at MIN_DIMENSION should PASS (not WARN)."""
        size = MIN_DIMENSION
        arr = np.zeros((size, size, 3), dtype=np.uint8)
        arr[::2, ::2] = 255
        arr[1::2, 1::2] = 255
        img = PILImage.fromarray(arr, mode="RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        result = check_image_quality(buf.read())

        # Should PASS (not WARN) because the threshold is < MIN_DIMENSION (strict less-than)
        assert result.verdict == QualityVerdict.PASS, (
            f"Expected PASS at exactly {size}x{size}, got {result.verdict}"
        )

    def test_wide_but_short_image_warns(self):
        """An image that is wide enough but too short should WARN."""
        # 800 wide but only 200 tall
        arr = np.zeros((200, 800, 3), dtype=np.uint8)
        arr[::2, ::2] = 255
        arr[1::2, 1::2] = 255
        img = PILImage.fromarray(arr, mode="RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        result = check_image_quality(buf.read())
        assert result.verdict == QualityVerdict.WARN
