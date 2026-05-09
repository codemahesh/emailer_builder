"""
mjml_renderer.py
================
Pure function module — no app/DB imports.

Generates MJML markup from structured campaign data and compiles it to HTML.

Priority layout rules
---------------------
- high   → 1-column full-width hero block  (600 px)
- medium → 2-column block                  (300 px each)
- low    → 3-column block                  (200 px each)

The footer ALWAYS contains the CleverTap template tags:
  {{unsubscribe_link}} and {{view_in_browser}}
"""

from __future__ import annotations

import json
import logging
import subprocess
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class ProductData:
    id: str
    sku: str
    name: str
    image_url: str       # processed_image_url if available, else scraped, else coming-soon
    price: str           # formatted_price
    button_name: str
    product_link: str
    priority: str        # "high" | "medium" | "low"
    position: int


@dataclass
class SectionData:
    id: str
    title: str
    products: List[ProductData]
    locked: bool = False
    position: int = 0


@dataclass
class VisualTokens:
    background_color: str = "#F8F9FB"
    section_background: str = "#FFFFFF"
    accent_color: str = "#2E5BFF"
    button_color: str = "#2E5BFF"
    button_text_color: str = "#FFFFFF"
    h1_size: str = "28px"
    h2_size: str = "20px"
    body_size: str = "14px"
    font_family: str = "Inter, Arial, sans-serif"
    product_background: str = "#FFFFFF"


@dataclass
class RenderInput:
    campaign_id: str
    campaign_name: str
    sections: List[SectionData]
    toc_entries: List[Any]           # ToCEntry list from icon_toc_mapper
    visual_tokens: VisualTokens = field(default_factory=VisualTokens)
    header_html: str = ""
    footer_html: str = ""
    banner_url: str = ""             # empty until Issue 7
    manual_overrides: Dict[str, str] = field(default_factory=dict)  # product_id → override_url


# ── MJML builder helpers ──────────────────────────────────────────────────────


def _safe_url(url: str) -> str:
    """Return url, falling back to a transparent 1×1 gif if blank."""
    return url.strip() if url and url.strip() else "https://via.placeholder.com/600x400?text=No+Image"


def _escape(text: str) -> str:
    """Minimal XML entity escaping for text nodes."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def _product_card_high(product: ProductData, tokens: VisualTokens) -> str:
    """1-column full-width hero block (high priority)."""
    return textwrap.dedent(f"""\
        <mj-section background-color="{tokens.product_background}" padding="0 0 24px 0">
          <mj-column width="600px">
            <mj-image
              src="{_safe_url(product.image_url)}"
              alt="{_escape(product.name)}"
              width="600px"
              height="300px"
              padding="0"
              fluid-on-mobile="true"
            />
            <mj-text
              font-size="{tokens.h2_size}"
              font-family="{tokens.font_family}"
              color="#1A2340"
              font-weight="600"
              padding="16px 24px 4px"
            >{_escape(product.name)}</mj-text>
            <mj-text
              font-size="{tokens.body_size}"
              font-family="{tokens.font_family}"
              color="#4A5568"
              font-weight="700"
              padding="0 24px 12px"
            >{_escape(product.price)}</mj-text>
            <mj-button
              background-color="{tokens.button_color}"
              color="{tokens.button_text_color}"
              font-family="{tokens.font_family}"
              font-size="14px"
              font-weight="600"
              border-radius="6px"
              padding="0 24px 20px"
              inner-padding="12px 28px"
              href="{product.product_link}"
            >{_escape(product.button_name or "Shop Now")}</mj-button>
          </mj-column>
        </mj-section>""")


def _product_card_medium(products: List[ProductData], tokens: VisualTokens) -> str:
    """2-column block (medium priority). Accepts 1 or 2 products."""
    cols = []
    for product in products[:2]:
        cols.append(textwrap.dedent(f"""\
            <mj-column width="300px" background-color="{tokens.product_background}">
              <mj-image
                src="{_safe_url(product.image_url)}"
                alt="{_escape(product.name)}"
                width="300px"
                height="200px"
                padding="0"
                fluid-on-mobile="true"
              />
              <mj-text
                font-size="15px"
                font-family="{tokens.font_family}"
                color="#1A2340"
                font-weight="600"
                padding="12px 16px 4px"
              >{_escape(product.name)}</mj-text>
              <mj-text
                font-size="{tokens.body_size}"
                font-family="{tokens.font_family}"
                color="#4A5568"
                font-weight="700"
                padding="0 16px 10px"
              >{_escape(product.price)}</mj-text>
              <mj-button
                background-color="{tokens.button_color}"
                color="{tokens.button_text_color}"
                font-family="{tokens.font_family}"
                font-size="13px"
                font-weight="600"
                border-radius="6px"
                padding="0 16px 16px"
                inner-padding="10px 20px"
                href="{product.product_link}"
              >{_escape(product.button_name or "Shop Now")}</mj-button>
            </mj-column>"""))
    # If only 1 product, add an empty column to maintain 2-col layout
    if len(products) == 1:
        cols.append(f'<mj-column width="300px" background-color="{tokens.product_background}"></mj-column>')

    return (
        f'<mj-section background-color="{tokens.product_background}" padding="0 0 24px 0">\n'
        + "\n".join(cols)
        + "\n</mj-section>"
    )


def _product_card_low(products: List[ProductData], tokens: VisualTokens) -> str:
    """3-column block (low priority). Accepts 1–3 products."""
    cols = []
    for product in products[:3]:
        cols.append(textwrap.dedent(f"""\
            <mj-column width="200px" background-color="{tokens.product_background}">
              <mj-image
                src="{_safe_url(product.image_url)}"
                alt="{_escape(product.name)}"
                width="200px"
                height="150px"
                padding="0"
                fluid-on-mobile="true"
              />
              <mj-text
                font-size="13px"
                font-family="{tokens.font_family}"
                color="#1A2340"
                font-weight="600"
                padding="10px 12px 4px"
              >{_escape(product.name)}</mj-text>
              <mj-text
                font-size="12px"
                font-family="{tokens.font_family}"
                color="#4A5568"
                font-weight="700"
                padding="0 12px 8px"
              >{_escape(product.price)}</mj-text>
              <mj-button
                background-color="{tokens.button_color}"
                color="{tokens.button_text_color}"
                font-family="{tokens.font_family}"
                font-size="12px"
                font-weight="600"
                border-radius="6px"
                padding="0 12px 14px"
                inner-padding="8px 16px"
                href="{product.product_link}"
              >{_escape(product.button_name or "Shop Now")}</mj-button>
            </mj-column>"""))
    # Pad with empty columns to keep 3-col grid stable
    while len(cols) < 3:
        cols.append(f'<mj-column width="200px" background-color="{tokens.product_background}"></mj-column>')

    return (
        f'<mj-section background-color="{tokens.product_background}" padding="0 0 24px 0">\n'
        + "\n".join(cols)
        + "\n</mj-section>"
    )


def _build_product_blocks(
    products: List[ProductData],
    tokens: VisualTokens,
    manual_overrides: Dict[str, str],
) -> str:
    """
    Group products by priority (preserving per-priority order) and emit MJML blocks.
    Applies manual_overrides before rendering.
    """

    def apply_override(p: ProductData) -> ProductData:
        if p.id in manual_overrides:
            return ProductData(
                id=p.id,
                sku=p.sku,
                name=p.name,
                image_url=manual_overrides[p.id],
                price=p.price,
                button_name=p.button_name,
                product_link=p.product_link,
                priority=p.priority,
                position=p.position,
            )
        return p

    high_products = [apply_override(p) for p in products if p.priority == "high"]
    medium_products = [apply_override(p) for p in products if p.priority == "medium"]
    low_products = [apply_override(p) for p in products if p.priority == "low"]

    parts: List[str] = []

    # High priority: one card per product (1-col)
    for p in high_products:
        parts.append(_product_card_high(p, tokens))

    # Medium priority: 2 per row
    for i in range(0, len(medium_products), 2):
        batch = medium_products[i : i + 2]
        parts.append(_product_card_medium(batch, tokens))

    # Low priority: 3 per row
    for i in range(0, len(low_products), 3):
        batch = low_products[i : i + 3]
        parts.append(_product_card_low(batch, tokens))

    return "\n".join(parts)


def _build_toc_row(toc_entries: List[Any], tokens: VisualTokens) -> str:
    """Horizontal Table of Contents row with icon + label pairs."""
    if not toc_entries:
        return ""

    # Build inline icon SVG stubs (text-only fallback; frontend replaces with Lucide at view time)
    items_html = ""
    for entry in toc_entries:
        section_id = getattr(entry, "section_id", "")
        title = _escape(getattr(entry, "section_title", ""))
        icon = _escape(getattr(entry, "icon_name", "tag"))
        items_html += (
            f'<a href="#section-{section_id}" '
            f'style="display:inline-block;text-align:center;margin:0 12px;'
            f'text-decoration:none;color:#4A5568;font-size:12px;font-family:Inter,Arial,sans-serif;">'
            f'<span style="display:block;font-size:18px;margin-bottom:4px;" '
            f'data-lucide="{icon}">&#9641;</span>'
            f'<span>{title}</span>'
            f'</a>'
        )

    return textwrap.dedent(f"""\
        <mj-section background-color="{tokens.section_background}" padding="16px 24px">
          <mj-column>
            <mj-text
              align="center"
              font-size="12px"
              font-family="{tokens.font_family}"
              color="#4A5568"
              padding="0"
            >{items_html}</mj-text>
          </mj-column>
        </mj-section>""")


# ── Main MJML builder ─────────────────────────────────────────────────────────


def build_mjml(render_input: RenderInput) -> str:
    """
    Pure function. Build MJML markup string from RenderInput.

    Structure
    ---------
    1. <mjml><mj-head>  — styles, fonts, brand tokens
    2. Table of Contents row (if toc_entries not empty)
    3. Header section (if header_html provided)
    4. For each section: mj-section with title, then product blocks grouped by priority
    5. Footer with CleverTap tags (ALWAYS included)
    """
    t = render_input.visual_tokens
    campaign_name = _escape(render_input.campaign_name)

    # ── Head ─────────────────────────────────────────────────────────────────
    head = textwrap.dedent(f"""\
        <mj-head>
          <mj-font name="Inter" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" />
          <mj-attributes>
            <mj-all font-family="{t.font_family}" />
            <mj-body background-color="{t.background_color}" />
            <mj-section background-color="{t.section_background}" />
            <mj-text font-size="{t.body_size}" color="#1A2340" line-height="1.5" />
            <mj-button background-color="{t.button_color}" color="{t.button_text_color}" border-radius="6px" />
          </mj-attributes>
          <mj-style>
            .section-title {{ font-weight: 700; color: {t.accent_color}; }}
            a {{ color: {t.accent_color}; }}
          </mj-style>
          <mj-preview>{campaign_name} — Email Preview</mj-preview>
        </mj-head>""")

    body_parts: List[str] = []

    # ── Banner (placeholder for Issue 7) ─────────────────────────────────────
    if render_input.banner_url:
        body_parts.append(textwrap.dedent(f"""\
            <mj-section padding="0">
              <mj-column>
                <mj-image
                  src="{_safe_url(render_input.banner_url)}"
                  alt="Banner"
                  width="600px"
                  padding="0"
                />
              </mj-column>
            </mj-section>"""))

    # ── Table of Contents ─────────────────────────────────────────────────────
    toc_row = _build_toc_row(render_input.toc_entries, t)
    if toc_row:
        body_parts.append(toc_row)

    # ── Custom header ─────────────────────────────────────────────────────────
    if render_input.header_html:
        body_parts.append(textwrap.dedent(f"""\
            <mj-section padding="0 0 8px 0">
              <mj-column>
                <mj-raw>{render_input.header_html}</mj-raw>
              </mj-column>
            </mj-section>"""))

    # ── Sections ─────────────────────────────────────────────────────────────
    for section in sorted(render_input.sections, key=lambda s: s.position):
        section_title = _escape(section.title)
        section_id = section.id

        # Locked sections get a data-locked attribute for deterministic rendering
        locked_attr = ' data-locked="true"' if section.locked else ""

        product_blocks = _build_product_blocks(
            section.products,
            t,
            render_input.manual_overrides,
        )

        body_parts.append(textwrap.dedent(f"""\
            <!-- Section: {section_title} -->
            <mj-section
              id="section-{section_id}"{locked_attr}
              background-color="{t.background_color}"
              padding="24px 0 4px"
            >
              <mj-column>
                <mj-text
                  font-size="{t.h2_size}"
                  font-weight="700"
                  color="{t.accent_color}"
                  padding="0 24px 12px"
                  css-class="section-title"
                >{section_title}</mj-text>
              </mj-column>
            </mj-section>
            {product_blocks}"""))

    # ── Footer (CleverTap tags ALWAYS included) ───────────────────────────────
    custom_footer_block = ""
    if render_input.footer_html:
        custom_footer_block = f"<mj-raw>{render_input.footer_html}</mj-raw>"

    body_parts.append(textwrap.dedent(f"""\
        <mj-section background-color="#1A2340" padding="24px">
          <mj-column>
            {custom_footer_block}
            <mj-text
              align="center"
              font-size="12px"
              color="#A0AEC0"
              font-family="{t.font_family}"
              padding="8px 0 4px"
            >You are receiving this email because you subscribed to our newsletter.</mj-text>
            <mj-text
              align="center"
              font-size="12px"
              color="#A0AEC0"
              font-family="{t.font_family}"
              padding="4px 0"
            >
              <a href="{{{{view_in_browser}}}}" style="color:#A0AEC0;text-decoration:underline;">View in Browser</a>
              &nbsp;&bull;&nbsp;
              <a href="{{{{unsubscribe_link}}}}" style="color:#A0AEC0;text-decoration:underline;">Unsubscribe</a>
            </mj-text>
          </mj-column>
        </mj-section>"""))

    body_content = "\n".join(body_parts)

    mjml = textwrap.dedent(f"""\
        <mjml>
          {head}
          <mj-body background-color="{t.background_color}">
        {textwrap.indent(body_content, '    ')}
          </mj-body>
        </mjml>""")

    return mjml


# ── MJML compiler ─────────────────────────────────────────────────────────────


def compile_mjml(mjml_markup: str) -> str:
    """
    Compile MJML markup to HTML.

    Tries (in order):
    1. Python ``mjml`` package:  mjml.mjml(markup)['html']
    2. mjml CLI via subprocess:  mjml -i --json
    3. Basic HTML fallback (preserves content without MJML compilation)
    """
    # Attempt 1: Python package
    try:
        import mjml as mjml_pkg  # type: ignore[import]
        result = mjml_pkg.mjml(mjml_markup)
        if isinstance(result, dict) and "html" in result:
            return result["html"]
        # Some versions return an object with .html attribute
        if hasattr(result, "html"):
            return result.html
    except ImportError:
        logger.debug("compile_mjml: Python mjml package not available, trying CLI")
    except Exception as exc:
        logger.warning("compile_mjml: Python mjml package error: %s — trying CLI", exc)

    # Attempt 2: mjml CLI
    try:
        proc = subprocess.run(
            ["mjml", "-i", "--json"],
            input=mjml_markup.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        if proc.returncode == 0:
            output = json.loads(proc.stdout.decode("utf-8"))
            if "html" in output:
                return output["html"]
        logger.warning("compile_mjml: CLI returned code %s", proc.returncode)
    except FileNotFoundError:
        logger.debug("compile_mjml: mjml CLI not found, using HTML fallback")
    except subprocess.TimeoutExpired:
        logger.warning("compile_mjml: mjml CLI timed out, using HTML fallback")
    except Exception as exc:
        logger.warning("compile_mjml: CLI error: %s — using HTML fallback", exc)

    # Attempt 3: Basic HTML fallback
    logger.info("compile_mjml: using basic HTML fallback (no MJML compiler available)")
    return _basic_html_fallback(mjml_markup)


def _basic_html_fallback(mjml_markup: str) -> str:
    """
    Generate a basic HTML document from MJML markup.
    Strips MJML tags and wraps in minimal responsive HTML.
    """
    import re

    # Extract text content between tags (very rough but functional)
    # Remove all XML/MJML tags, keep text + anchor hrefs
    # Convert mj-button href to <a> tags
    content = mjml_markup

    # Replace mj-image with img tags
    content = re.sub(
        r'<mj-image[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>',
        r'<img src="\1" alt="\2" style="max-width:100%;height:auto;" />',
        content,
    )

    # Replace mj-button with anchor tags
    content = re.sub(
        r'<mj-button[^>]*href="([^"]*)"[^>]*>(.*?)</mj-button>',
        r'<a href="\1" style="display:inline-block;padding:10px 24px;background:#2E5BFF;'
        r'color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">\2</a>',
        content,
        flags=re.DOTALL,
    )

    # Replace mj-text with div
    content = re.sub(r"<mj-text[^>]*>(.*?)</mj-text>", r"<div>\1</div>", content, flags=re.DOTALL)

    # Remove remaining MJML tags
    content = re.sub(r"</?mj-[^>]+>", "", content)
    content = re.sub(r"</?mjml[^>]*>", "", content)

    return textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>Email Preview</title>
          <style>
            body {{ margin: 0; padding: 0; font-family: Inter, Arial, sans-serif; background: #F8F9FB; }}
            .wrapper {{ max-width: 600px; margin: 0 auto; background: #fff; }}
            img {{ max-width: 100%; height: auto; display: block; }}
            a {{ color: #2E5BFF; }}
          </style>
        </head>
        <body>
          <div class="wrapper">
            {content}
          </div>
        </body>
        </html>""")


# ── Main entry point ──────────────────────────────────────────────────────────


def render_campaign(render_input: RenderInput) -> Tuple[str, float]:
    """
    Main entry point.

    Parameters
    ----------
    render_input : RenderInput

    Returns
    -------
    (html_string, size_in_kb)
    """
    mjml_markup = build_mjml(render_input)
    html = compile_mjml(mjml_markup)
    size_kb = round(len(html.encode("utf-8")) / 1024, 2)
    return html, size_kb
