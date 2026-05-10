"""
image_quality_gate.py
=====================
Pure function module for image quality assessment.

Uses Pillow for dimensions and OpenCV for blur detection (Laplacian variance).
No DB, queue, or HTTP imports.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# ── Configurable thresholds (importable for tests) ────────────────────────────

BLUR_THRESHOLD: float = 50.0   # Laplacian variance below this → too blurry
MIN_DIMENSION: int = 500        # Width or height below this → low-res warning


class QualityVerdict(str, Enum):
    PASS = "pass"
    WARN = "warn"   # low-res but upscalable (below MIN_DIMENSION)
    FAIL = "fail"   # too blurry to recover


@dataclass
class QualityResult:
    verdict: QualityVerdict
    reason: str
    width: int = 0
    height: int = 0
    blur_score: float = 0.0


def check_image_quality(image_bytes: bytes) -> QualityResult:
    """
    Pure function. Assess image quality.

    Steps:
    1. Load with Pillow to get dimensions.
    2. Convert to grayscale numpy array.
    3. Compute Laplacian variance with cv2.Laplacian.
    4. FAIL if blur_score < BLUR_THRESHOLD.
    5. WARN if width < MIN_DIMENSION OR height < MIN_DIMENSION (but not FAIL).
    6. PASS otherwise.

    Returns
    -------
    QualityResult
        Never raises — returns a FAIL result on any exception.
    """
    try:
        # ── Step 1: Load with Pillow ──────────────────────────────────────────
        try:
            from PIL import Image as PILImage
        except ImportError:
            return QualityResult(
                verdict=QualityVerdict.FAIL,
                reason="Pillow not available",
            )

        try:
            pil_img = PILImage.open(io.BytesIO(image_bytes))
            pil_img.load()  # force full decode
        except Exception as exc:  # noqa: BLE001
            return QualityResult(
                verdict=QualityVerdict.FAIL,
                reason=f"Cannot decode image: {exc}",
            )

        width, height = pil_img.size

        # ── Step 2: Convert to grayscale numpy array ──────────────────────────
        try:
            import numpy as np
        except ImportError:
            return QualityResult(
                verdict=QualityVerdict.FAIL,
                reason="numpy not available",
                width=width,
                height=height,
            )

        gray_pil = pil_img.convert("L")
        gray_array = np.array(gray_pil, dtype=np.float64)

        # ── Step 3: Compute Laplacian variance ────────────────────────────────
        try:
            import cv2  # type: ignore[import]
            gray_uint8 = gray_array.astype(np.uint8)
            laplacian = cv2.Laplacian(gray_uint8, cv2.CV_64F)
            blur_score = float(laplacian.var())
        except ImportError:
            # cv2 unavailable — skip blur check, rely on dimension check only
            logger.warning(
                "check_image_quality: cv2 not available, skipping blur detection"
            )
            blur_score = float("inf")  # treat as sharp when cv2 is missing
        except Exception as exc:  # noqa: BLE001
            logger.warning("check_image_quality: Laplacian failed (%s)", exc)
            blur_score = float("inf")

        # ── Step 4: FAIL if too blurry ────────────────────────────────────────
        if blur_score < BLUR_THRESHOLD:
            return QualityResult(
                verdict=QualityVerdict.FAIL,
                reason=f"Image too blurry (score={blur_score:.1f}, threshold={BLUR_THRESHOLD})",
                width=width,
                height=height,
                blur_score=blur_score,
            )

        # ── Step 5: WARN if low-res ───────────────────────────────────────────
        if width < MIN_DIMENSION or height < MIN_DIMENSION:
            return QualityResult(
                verdict=QualityVerdict.WARN,
                reason=(
                    f"Image resolution low ({width}x{height}), "
                    f"minimum recommended is {MIN_DIMENSION}x{MIN_DIMENSION}"
                ),
                width=width,
                height=height,
                blur_score=blur_score,
            )

        # ── Step 6: PASS ──────────────────────────────────────────────────────
        return QualityResult(
            verdict=QualityVerdict.PASS,
            reason="OK",
            width=width,
            height=height,
            blur_score=blur_score,
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("check_image_quality: unexpected error")
        return QualityResult(
            verdict=QualityVerdict.FAIL,
            reason=f"Unexpected error during quality check: {exc}",
        )
