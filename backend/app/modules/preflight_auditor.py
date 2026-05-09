"""
preflight_auditor.py
====================
PreFlightAuditor — checks HTML for CleverTap compliance.

Public interface:
  audit(html_string: str) → AuditReport
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import parse_qs, urlparse

# Try to import htmlmin for proper minification; fall back to regex approach
try:
    import htmlmin  # type: ignore[import]
    _HAVE_HTMLMIN = True
except ImportError:
    _HAVE_HTMLMIN = False


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class AuditItem:
    check: str
    status: Literal["pass", "warn", "hard_stop"]
    message: str


@dataclass
class AuditReport:
    items: list[AuditItem]
    size_kb: float
    has_hard_stops: bool
    minified_html: str


# ── Minification helper ───────────────────────────────────────────────────────


def _minify(html: str) -> str:
    """Minify HTML by stripping whitespace between tags."""
    if _HAVE_HTMLMIN:
        try:
            return htmlmin.minify(html, remove_empty_space=True)
        except Exception:  # noqa: BLE001
            pass
    # Fallback: strip whitespace between tags
    return re.sub(r">\s+<", "><", html)


# ── Link parser for UTM coverage check ───────────────────────────────────────


class _HrefParser(HTMLParser):
    """Collects all href attribute values from <a> tags."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            for name, value in attrs:
                if name.lower() == "href" and value:
                    self.hrefs.append(value)


def _extract_hrefs(html: str) -> list[str]:
    parser = _HrefParser()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001
        pass
    return parser.hrefs


def _has_utm_campaign(url: str) -> bool:
    """Return True if the URL contains a utm_campaign query parameter."""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return "utm_campaign" in params
    except Exception:  # noqa: BLE001
        return False


# ── Main audit function ───────────────────────────────────────────────────────


def audit(html_string: str) -> AuditReport:
    """
    Run all pre-flight checks on the given HTML string.

    Checks performed (in order):
    1. CleverTap unsubscribe tag presence — hard_stop if missing
    2. View-in-browser tag presence — hard_stop if missing
    3. File size check — hard_stop >= 102 KB, warn >= 90 KB, pass otherwise
    4. UTM coverage on external links — warn if any http link lacks utm_campaign
    5. Responsiveness — delegates to ResponsivenessValidator

    Returns
    -------
    AuditReport
        Aggregated result of all checks.
    """
    items: list[AuditItem] = []

    # ── Minify first so size check uses the real delivery size ────────────────
    minified = _minify(html_string)
    size_kb = len(minified.encode("utf-8")) / 1024

    # ── Check 1: CleverTap unsubscribe tag ────────────────────────────────────
    if "{{unsubscribe_link}}" in html_string:
        items.append(AuditItem(
            check="unsubscribe_link",
            status="pass",
            message="{{unsubscribe_link}} tag found.",
        ))
    else:
        items.append(AuditItem(
            check="unsubscribe_link",
            status="hard_stop",
            message=(
                "HARD STOP: {{unsubscribe_link}} tag is missing. "
                "CleverTap requires this for CAN-SPAM/GDPR compliance."
            ),
        ))

    # ── Check 2: View-in-browser tag ─────────────────────────────────────────
    if "{{view_in_browser}}" in html_string:
        items.append(AuditItem(
            check="view_in_browser",
            status="pass",
            message="{{view_in_browser}} tag found.",
        ))
    else:
        items.append(AuditItem(
            check="view_in_browser",
            status="hard_stop",
            message=(
                "HARD STOP: {{view_in_browser}} tag is missing. "
                "CleverTap requires this for proper email client rendering."
            ),
        ))

    # ── Check 3: File size ────────────────────────────────────────────────────
    if size_kb >= 102:
        items.append(AuditItem(
            check="file_size",
            status="hard_stop",
            message=(
                f"HARD STOP: Minified HTML is {size_kb:.1f} KB, "
                f"which meets or exceeds the 102 KB hard limit. "
                f"Gmail and other clients will clip the email."
            ),
        ))
    elif size_kb >= 90:
        items.append(AuditItem(
            check="file_size",
            status="warn",
            message=(
                f"WARNING: Minified HTML is {size_kb:.1f} KB, "
                f"approaching the 102 KB Gmail clip limit."
            ),
        ))
    else:
        items.append(AuditItem(
            check="file_size",
            status="pass",
            message=f"File size is {size_kb:.1f} KB — within safe limits.",
        ))

    # ── Check 4: UTM coverage ─────────────────────────────────────────────────
    hrefs = _extract_hrefs(html_string)
    http_links = [h for h in hrefs if h.startswith("http")]
    missing_utm = [h for h in http_links if not _has_utm_campaign(h)]

    if missing_utm:
        sample = missing_utm[:3]
        sample_str = ", ".join(sample)
        items.append(AuditItem(
            check="utm_coverage",
            status="warn",
            message=(
                f"WARNING: {len(missing_utm)} link(s) are missing utm_campaign parameter. "
                f"Examples: {sample_str}"
            ),
        ))
    else:
        items.append(AuditItem(
            check="utm_coverage",
            status="pass",
            message=(
                f"All {len(http_links)} external link(s) contain utm_campaign parameter."
                if http_links
                else "No external links found."
            ),
        ))

    # ── Check 5: Responsiveness ───────────────────────────────────────────────
    try:
        from app.modules.responsiveness_validator import (
            IssueSeverity,
            validate_responsiveness,
        )

        resp_issues = validate_responsiveness(html_string)
        if not resp_issues:
            items.append(AuditItem(
                check="responsiveness",
                status="pass",
                message="No responsiveness issues detected.",
            ))
        else:
            for issue in resp_issues:
                if issue.severity == IssueSeverity.error:
                    audit_status: Literal["pass", "warn", "hard_stop"] = "hard_stop"
                else:
                    audit_status = "warn"
                items.append(AuditItem(
                    check="responsiveness",
                    status=audit_status,
                    message=f"[{issue.viewport.value.upper()}] {issue.description}",
                ))
    except Exception as exc:  # noqa: BLE001
        items.append(AuditItem(
            check="responsiveness",
            status="warn",
            message=f"Responsiveness check could not be completed: {exc}",
        ))

    has_hard_stops = any(item.status == "hard_stop" for item in items)

    return AuditReport(
        items=items,
        size_kb=round(size_kb, 2),
        has_hard_stops=has_hard_stops,
        minified_html=minified,
    )
