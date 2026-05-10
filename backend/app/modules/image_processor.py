"""
image_processor.py
==================
Pure function module for image processing.

Input: bytes + ProcessingConfig. Output: bytes (PNG).
No DB, queue, or HTTP imports.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ProcessingConfig:
    background_color: str = "#FFFFFF"   # hex color
    remove_background: bool = True
    upscale_if_small: bool = False      # set True if WARN from quality gate
    target_width: int = 600
    target_height: int = 600


def _parse_hex_color(hex_color: str) -> Tuple[int, int, int]:
    """Parse a hex color string (#RRGGBB or #RGB) into an (R, G, B) tuple."""
    color = hex_color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    if len(color) != 6:
        return (255, 255, 255)  # default white on bad input
    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        return (r, g, b)
    except ValueError:
        return (255, 255, 255)


def process_image(image_bytes: bytes, config: ProcessingConfig) -> bytes:
    """
    Pure function. Process an image for email use.

    Steps:
    1. Open image with Pillow.
    2. If config.upscale_if_small: upscale to 500x500 minimum using LANCZOS.
    3. If config.remove_background: remove background with rembg.
       If rembg not available (ImportError), skip and log warning.
    4. Crop to center with 10% padding (tight bbox of non-transparent pixels,
       add 10% padding, then pad to square).
    5. Composite onto background_color (parse hex, create RGB image, paste).
    6. Return PNG bytes.

    Never raises — returns original image bytes on any exception.
    """
    try:
        from PIL import Image as PILImage
    except ImportError:
        logger.error("process_image: Pillow not available, returning original bytes")
        return image_bytes

    try:
        # ── Step 1: Open image ────────────────────────────────────────────────
        try:
            img = PILImage.open(io.BytesIO(image_bytes))
            img.load()
        except Exception as exc:  # noqa: BLE001
            logger.warning("process_image: cannot open image (%s), returning original", exc)
            return image_bytes

        # Ensure RGBA for later transparency operations
        img = img.convert("RGBA")

        # ── Step 2: Upscale if small ──────────────────────────────────────────
        if config.upscale_if_small:
            min_dim = 500
            w, h = img.size
            if w < min_dim or h < min_dim:
                scale = max(min_dim / w, min_dim / h)
                new_w = max(int(w * scale), min_dim)
                new_h = max(int(h * scale), min_dim)
                try:
                    img = img.resize((new_w, new_h), PILImage.LANCZOS)
                    logger.debug(
                        "process_image: upscaled %dx%d → %dx%d", w, h, new_w, new_h
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("process_image: upscale failed (%s), continuing", exc)

        # ── Step 3: Remove background ─────────────────────────────────────────
        if config.remove_background:
            try:
                # Lazy import — rembg loads ML models on first import
                from rembg import remove as rembg_remove  # type: ignore[import]

                # rembg.remove accepts bytes and returns bytes (PNG with alpha)
                current_bytes = io.BytesIO()
                img.save(current_bytes, format="PNG")
                current_bytes.seek(0)

                removed_bytes = rembg_remove(current_bytes.read())
                img = PILImage.open(io.BytesIO(removed_bytes)).convert("RGBA")
                logger.debug("process_image: background removed")
            except ImportError:
                logger.warning(
                    "process_image: rembg not available, skipping background removal"
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "process_image: background removal failed (%s), continuing", exc
                )

        # ── Step 4: Crop to center with 10% padding ───────────────────────────
        try:
            img = _crop_with_padding(img, padding_pct=0.10)
        except Exception as exc:  # noqa: BLE001
            logger.warning("process_image: crop failed (%s), continuing", exc)

        # ── Step 5: Composite onto background color ───────────────────────────
        try:
            bg_rgb = _parse_hex_color(config.background_color)
            background = PILImage.new("RGB", img.size, bg_rgb)
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[3])  # use alpha channel
            else:
                background.paste(img)
            img = background
        except Exception as exc:  # noqa: BLE001
            logger.warning("process_image: compositing failed (%s), continuing", exc)
            # Ensure we still have a valid image to return
            try:
                img = img.convert("RGB")
            except Exception:  # noqa: BLE001
                pass

        # ── Step 6: Return PNG bytes ──────────────────────────────────────────
        output = io.BytesIO()
        img.save(output, format="PNG", optimize=True)
        output.seek(0)
        return output.read()

    except Exception as exc:  # noqa: BLE001
        logger.exception("process_image: unexpected error, returning original bytes")
        return image_bytes


def _crop_with_padding(img: "PILImage.Image", padding_pct: float = 0.10) -> "PILImage.Image":
    """
    Crop the image to the tight bounding box of non-transparent pixels,
    add padding_pct on each side, then pad to a square.

    If the image has no alpha channel or bbox is None, returns the image as-is
    (converted to RGBA).
    """
    from PIL import Image as PILImage

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Get bounding box of non-transparent pixels
    alpha = img.split()[3]  # alpha channel
    bbox = alpha.getbbox()

    if bbox is None:
        # Fully transparent or no alpha info — use full image
        return img

    left, top, right, bottom = bbox
    content_w = right - left
    content_h = bottom - top

    if content_w <= 0 or content_h <= 0:
        return img

    # Add padding
    pad_x = int(content_w * padding_pct)
    pad_y = int(content_h * padding_pct)

    img_w, img_h = img.size
    padded_left = max(0, left - pad_x)
    padded_top = max(0, top - pad_y)
    padded_right = min(img_w, right + pad_x)
    padded_bottom = min(img_h, bottom + pad_y)

    cropped = img.crop((padded_left, padded_top, padded_right, padded_bottom))

    # Pad to square
    cw, ch = cropped.size
    if cw == ch:
        return cropped

    side = max(cw, ch)
    square = PILImage.new("RGBA", (side, side), (0, 0, 0, 0))
    offset_x = (side - cw) // 2
    offset_y = (side - ch) // 2
    square.paste(cropped, (offset_x, offset_y))
    return square
