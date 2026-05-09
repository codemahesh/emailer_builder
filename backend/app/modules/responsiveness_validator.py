"""
responsiveness_validator.py
===========================
Pure function module — no DB/queue/HTTP imports.

Validates compiled email HTML for responsiveness issues at mobile (375 px)
and desktop (600 px) viewports using BeautifulSoup heuristics.

Called by the Pre-Flight Auditor (Issue 19).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# ── Configurable constants (importable for tests) ─────────────────────────────

MOBILE_WIDTH: int = 375
DESKTOP_WIDTH: int = 600
MOBILE_STACK_WARN_THRESHOLD: int = 6   # table cells per implied section
MIN_FONT_SIZE_MOBILE: int = 11          # px
TALL_STACK_HEIGHT: int = 2400           # total estimated px height on mobile


# ── Enums and dataclass ───────────────────────────────────────────────────────


class IssueSeverity(str, Enum):
    warn = "warn"
    error = "error"


class Viewport(str, Enum):
    mobile = "mobile"
    desktop = "desktop"


@dataclass
class ResponsivenessIssue:
    severity: IssueSeverity
    description: str
    viewport: Viewport
    section_id: Optional[str] = None
    product_id: Optional[str] = None
    element_hint: Optional[str] = None  # CSS selector or tag hint for debugging


# ── Private helpers ───────────────────────────────────────────────────────────


def _parse_px(value: str) -> Optional[int]:
    """
    Parse a CSS/HTML width value to an integer pixel count.

    '300px' → 300
    '300'   → 300
    '50%'   → None  (relative — cannot be resolved without context)
    ''      → None
    """
    if not value:
        return None
    value = value.strip()
    if value.endswith("%"):
        return None
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(?:px)?$", value, re.IGNORECASE)
    if m:
        return int(float(m.group(1)))
    return None


def _get_section_id(element: Tag) -> Optional[str]:
    """
    Walk up the DOM tree to find the nearest ancestor (or self) that carries
    a ``data-section-id`` or ``id`` attribute.  Returns the value or None.
    """
    node = element
    for _ in range(10):  # limit traversal depth
        if not isinstance(node, Tag):
            break
        sid = node.get("data-section-id") or node.get("id")
        if sid:
            return str(sid)
        node = node.parent  # type: ignore[assignment]
    return None


def _estimate_stacked_height(html_string: str) -> int:
    """
    Estimate the total pixel height all product-like table cells would occupy
    when stacked on mobile (single-column layout).

    Uses a rough heuristic: each <td> contributes a fixed estimated height of
    200 px (image) + 80 px (text + button) = 280 px per cell row.
    """
    try:
        soup = BeautifulSoup(html_string, "lxml")
        tds = soup.find_all("td")
        # Count rows rather than raw cells — each <tr> stacks as one unit.
        trs = soup.find_all("tr")
        return len(trs) * 280
    except Exception:  # noqa: BLE001
        return 0


def _width_from_style(style_str: str) -> Optional[int]:
    """Extract a pixel width from an inline style string, e.g. 'width:300px'."""
    if not style_str:
        return None
    m = re.search(r"width\s*:\s*([\d.]+(?:px)?)", style_str, re.IGNORECASE)
    if m:
        return _parse_px(m.group(1))
    return None


def _font_size_from_style(style_str: str) -> Optional[int]:
    """Extract a pixel font-size from an inline style string."""
    if not style_str:
        return None
    m = re.search(r"font-size\s*:\s*([\d.]+)\s*px", style_str, re.IGNORECASE)
    if m:
        return int(float(m.group(1)))
    return None


# ── Main validator ────────────────────────────────────────────────────────────


def validate_responsiveness(html_string: str) -> List[ResponsivenessIssue]:
    """
    Pure function.  Parse HTML and check for layout issues at mobile (375 px)
    and desktop (600 px) viewports.

    Heuristics applied
    ------------------
    1. Images wider than container.
    2. Column (``<td>``) width sums exceeding container per ``<tr>``.
    3. Text overflow risk (``white-space: nowrap`` inside constrained containers).
    4. Excessive stacked column height on mobile.
    5. Font size too small for mobile.

    Returns
    -------
    List[ResponsivenessIssue]
        Empty list means all clear.  Never raises.
    """
    issues: List[ResponsivenessIssue] = []

    if not html_string or not html_string.strip():
        return issues

    try:
        soup = BeautifulSoup(html_string, "lxml")
    except Exception:  # noqa: BLE001
        return issues

    try:
        _check_image_widths(soup, issues)
    except Exception:  # noqa: BLE001
        logger.debug("validate_responsiveness: image-width check error", exc_info=True)

    try:
        _check_column_widths(soup, issues)
    except Exception:  # noqa: BLE001
        logger.debug("validate_responsiveness: column-width check error", exc_info=True)

    try:
        _check_nowrap_overflow(soup, issues)
    except Exception:  # noqa: BLE001
        logger.debug("validate_responsiveness: nowrap check error", exc_info=True)

    try:
        _check_stacked_height(soup, issues, html_string)
    except Exception:  # noqa: BLE001
        logger.debug("validate_responsiveness: stacked-height check error", exc_info=True)

    try:
        _check_font_sizes(soup, issues)
    except Exception:  # noqa: BLE001
        logger.debug("validate_responsiveness: font-size check error", exc_info=True)

    return issues


# ── Heuristic implementations ─────────────────────────────────────────────────


def _check_image_widths(soup: BeautifulSoup, issues: List[ResponsivenessIssue]) -> None:
    """
    Heuristic 1 — Images wider than container.

    Rules:
    - explicit px width > DESKTOP_WIDTH  → error on both viewports
    - explicit px width > MOBILE_WIDTH and <= DESKTOP_WIDTH → error on mobile only
    - width="100%" with parent td/table having explicit px width > DESKTOP_WIDTH → error
    """
    for img in soup.find_all("img"):
        if not isinstance(img, Tag):
            continue

        section_id = _get_section_id(img)

        # Gather width from attribute and style
        attr_width = img.get("width", "")
        style_width: Optional[int] = None
        style_str = img.get("style", "")
        if style_str:
            style_width = _width_from_style(style_str)

        # Prefer numeric attribute parse, then style
        px_width: Optional[int] = None
        is_percentage = False

        if attr_width:
            if "%" in str(attr_width):
                is_percentage = True
            else:
                px_width = _parse_px(str(attr_width))

        if px_width is None and not is_percentage and style_width is not None:
            px_width = style_width

        if is_percentage:
            # Check if parent container has a wider-than-desktop explicit width
            parent = img.parent
            for _ in range(5):
                if not isinstance(parent, Tag):
                    break
                parent_w = _parse_px(str(parent.get("width", ""))) or _width_from_style(
                    parent.get("style", "")
                )
                if parent_w is not None:
                    if parent_w > DESKTOP_WIDTH:
                        issues.append(ResponsivenessIssue(
                            severity=IssueSeverity.error,
                            description=(
                                f"Image with width=100% inside a container of {parent_w}px "
                                f"exceeds desktop width ({DESKTOP_WIDTH}px)"
                            ),
                            viewport=Viewport.desktop,
                            section_id=section_id,
                            element_hint="img[width='100%']",
                        ))
                        issues.append(ResponsivenessIssue(
                            severity=IssueSeverity.error,
                            description=(
                                f"Image with width=100% inside a container of {parent_w}px "
                                f"exceeds mobile width ({MOBILE_WIDTH}px)"
                            ),
                            viewport=Viewport.mobile,
                            section_id=section_id,
                            element_hint="img[width='100%']",
                        ))
                    break
                parent = parent.parent  # type: ignore[assignment]
            continue

        if px_width is None:
            continue

        if px_width > DESKTOP_WIDTH:
            issues.append(ResponsivenessIssue(
                severity=IssueSeverity.error,
                description=(
                    f"Image width {px_width}px exceeds desktop container width ({DESKTOP_WIDTH}px)"
                ),
                viewport=Viewport.desktop,
                section_id=section_id,
                element_hint=f"img[width='{px_width}']",
            ))
            issues.append(ResponsivenessIssue(
                severity=IssueSeverity.error,
                description=(
                    f"Image width {px_width}px exceeds mobile container width ({MOBILE_WIDTH}px)"
                ),
                viewport=Viewport.mobile,
                section_id=section_id,
                element_hint=f"img[width='{px_width}']",
            ))
        elif px_width > MOBILE_WIDTH:
            issues.append(ResponsivenessIssue(
                severity=IssueSeverity.error,
                description=(
                    f"Image width {px_width}px exceeds mobile container width ({MOBILE_WIDTH}px)"
                ),
                viewport=Viewport.mobile,
                section_id=section_id,
                element_hint=f"img[width='{px_width}']",
            ))


def _check_column_widths(soup: BeautifulSoup, issues: List[ResponsivenessIssue]) -> None:
    """
    Heuristic 2 — Column width sums exceeding container per ``<tr>``.

    For each ``<tr>``, sum the explicit px widths of its ``<td>`` children.
    - sum > DESKTOP_WIDTH → error on desktop AND mobile (whole row is broken
      even at the widest supported viewport, so it will also be broken when
      stacked on mobile).
    - sum > MOBILE_WIDTH but <= DESKTOP_WIDTH → normal multi-column layout;
      email clients reflow columns on narrow screens, so no issue is raised.
      (A two-column 560 px row is well-formed — each column stacks at full
      width on mobile and is fine.)

    For individual column cells that are themselves too wide for mobile when
    stacked solo (single td > MOBILE_WIDTH), a separate per-cell check is also
    applied.
    """
    for tr in soup.find_all("tr"):
        if not isinstance(tr, Tag):
            continue

        section_id = _get_section_id(tr)
        td_widths: List[int] = []
        td_elements: List[int] = []

        for td in tr.find_all("td", recursive=False):
            if not isinstance(td, Tag):
                continue
            w = _parse_px(str(td.get("width", "")))
            if w is None:
                w = _width_from_style(td.get("style", ""))
            if w is not None:
                td_widths.append(w)
                td_elements.append(w)

        if not td_widths:
            continue

        total = sum(td_widths)

        if total > DESKTOP_WIDTH:
            # Row exceeds the desktop container — broken on all viewports.
            issues.append(ResponsivenessIssue(
                severity=IssueSeverity.error,
                description=(
                    f"Column widths in a row sum to {total}px, "
                    f"exceeding desktop container width ({DESKTOP_WIDTH}px)"
                ),
                viewport=Viewport.desktop,
                section_id=section_id,
                element_hint="tr > td[width]",
            ))
            issues.append(ResponsivenessIssue(
                severity=IssueSeverity.error,
                description=(
                    f"Column widths in a row sum to {total}px, "
                    f"exceeding mobile container width ({MOBILE_WIDTH}px)"
                ),
                viewport=Viewport.mobile,
                section_id=section_id,
                element_hint="tr > td[width]",
            ))
        else:
            # Row fits on desktop.  Check individual cells: a cell wider than
            # MOBILE_WIDTH will overflow if it is forced to full-width on mobile
            # but has a hard-coded px width that the client does not override.
            for cell_w in td_elements:
                if cell_w > MOBILE_WIDTH:
                    issues.append(ResponsivenessIssue(
                        severity=IssueSeverity.error,
                        description=(
                            f"Column cell width {cell_w}px exceeds mobile container "
                            f"width ({MOBILE_WIDTH}px)"
                        ),
                        viewport=Viewport.mobile,
                        section_id=section_id,
                        element_hint="td[width]",
                    ))
                    break  # one issue per row is enough


def _check_nowrap_overflow(soup: BeautifulSoup, issues: List[ResponsivenessIssue]) -> None:
    """
    Heuristic 3 — Text overflow risk.

    Find elements with ``white-space: nowrap`` whose nearest width-constrained
    ancestor is narrower than MOBILE_WIDTH.  Emits a warning on mobile.
    """
    NOWRAP_RE = re.compile(r"white-space\s*:\s*nowrap", re.IGNORECASE)

    for el in soup.find_all(True):
        if not isinstance(el, Tag):
            continue
        style_str = el.get("style", "")
        if not style_str or not NOWRAP_RE.search(style_str):
            continue

        section_id = _get_section_id(el)

        # Walk up to find a width-constrained ancestor
        parent = el.parent
        constrained_width: Optional[int] = None
        for _ in range(8):
            if not isinstance(parent, Tag):
                break
            w = _parse_px(str(parent.get("width", ""))) or _width_from_style(
                parent.get("style", "")
            )
            if w is not None:
                constrained_width = w
                break
            parent = parent.parent  # type: ignore[assignment]

        threshold = MOBILE_WIDTH
        if constrained_width is not None and constrained_width < threshold:
            issues.append(ResponsivenessIssue(
                severity=IssueSeverity.warn,
                description=(
                    f"Element with white-space:nowrap inside a {constrained_width}px container "
                    f"may overflow on mobile (viewport width {MOBILE_WIDTH}px)"
                ),
                viewport=Viewport.mobile,
                section_id=section_id,
                element_hint=f"{el.name}[style*='nowrap']",
            ))


def _check_stacked_height(
    soup: BeautifulSoup,
    issues: List[ResponsivenessIssue],
    html_string: str,
) -> None:
    """
    Heuristic 4 — Excessive stacked column height on mobile.

    Two sub-checks:
    a) If the total number of ``<td>`` elements in any single ``<table>`` exceeds
       MOBILE_STACK_WARN_THRESHOLD, warn that mobile scroll depth may be too
       great.
    b) If the estimated total stacked height across the whole page exceeds
       TALL_STACK_HEIGHT, emit an additional warning.
    """
    for table in soup.find_all("table"):
        if not isinstance(table, Tag):
            continue
        tds = table.find_all("td")
        if len(tds) > MOBILE_STACK_WARN_THRESHOLD:
            section_id = _get_section_id(table)
            issues.append(ResponsivenessIssue(
                severity=IssueSeverity.warn,
                description=(
                    f"Table contains {len(tds)} cells — on mobile these stack vertically, "
                    f"creating excessive scroll depth (threshold: {MOBILE_STACK_WARN_THRESHOLD})"
                ),
                viewport=Viewport.mobile,
                section_id=section_id,
                element_hint="table > tr > td",
            ))

    estimated_height = _estimate_stacked_height(html_string)
    if estimated_height > TALL_STACK_HEIGHT:
        issues.append(ResponsivenessIssue(
            severity=IssueSeverity.warn,
            description=(
                f"Estimated mobile stacked content height is ~{estimated_height}px, "
                f"which exceeds the recommended maximum ({TALL_STACK_HEIGHT}px). "
                "Consider reducing the number of product rows."
            ),
            viewport=Viewport.mobile,
            element_hint="body",
        ))


def _check_font_sizes(soup: BeautifulSoup, issues: List[ResponsivenessIssue]) -> None:
    """
    Heuristic 5 — Font size too small for mobile.

    Find any element whose inline style contains ``font-size: Xpx`` where
    X < MIN_FONT_SIZE_MOBILE and emit a warning on mobile.
    """
    FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([\d.]+)\s*px", re.IGNORECASE)

    # Also check <font size="N"> legacy tags
    for el in soup.find_all(True):
        if not isinstance(el, Tag):
            continue

        style_str = el.get("style", "")
        if style_str:
            m = FONT_SIZE_RE.search(style_str)
            if m:
                size = int(float(m.group(1)))
                if size < MIN_FONT_SIZE_MOBILE:
                    section_id = _get_section_id(el)
                    issues.append(ResponsivenessIssue(
                        severity=IssueSeverity.warn,
                        description=(
                            f"Font size {size}px is below the recommended minimum "
                            f"({MIN_FONT_SIZE_MOBILE}px) for mobile readability"
                        ),
                        viewport=Viewport.mobile,
                        section_id=section_id,
                        element_hint=f"{el.name}[style*='font-size:{size}px']",
                    ))
