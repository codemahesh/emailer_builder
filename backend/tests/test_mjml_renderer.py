"""
test_mjml_renderer.py
=====================
Unit tests for app.modules.mjml_renderer — pure function, no DB needed.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.modules.icon_toc_mapper import ToCEntry
from app.modules.mjml_renderer import (
    ProductData,
    RenderInput,
    SectionData,
    VisualTokens,
    build_mjml,
    render_campaign,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_product(
    priority: str = "medium",
    product_id: str = "prod-1",
    image_url: str = "https://example.com/img.jpg",
) -> ProductData:
    return ProductData(
        id=product_id,
        sku=f"SKU-{product_id}",
        name=f"Product {product_id}",
        image_url=image_url,
        price="₹999",
        button_name="Buy Now",
        product_link="https://example.com/product",
        priority=priority,
        position=0,
    )


def _make_section(
    products: list,
    section_id: str = "sec-1",
    title: str = "Test Section",
    locked: bool = False,
) -> SectionData:
    return SectionData(
        id=section_id,
        title=title,
        products=products,
        locked=locked,
        position=0,
    )


def _make_render_input(sections: list, toc_entries: list = None, overrides: dict = None) -> RenderInput:
    return RenderInput(
        campaign_id="camp-1",
        campaign_name="Test Campaign",
        sections=sections,
        toc_entries=toc_entries or [],
        visual_tokens=VisualTokens(),
        header_html="",
        footer_html="",
        banner_url="",
        manual_overrides=overrides or {},
    )


# ── Tests: priority column layout ─────────────────────────────────────────────


def test_high_priority_generates_single_column():
    """High priority product should produce a 600px (1-column) section."""
    product = _make_product(priority="high")
    section = _make_section([product])
    render_input = _make_render_input([section])

    mjml = build_mjml(render_input)

    # High priority uses full 600px width
    assert 'width="600px"' in mjml
    # Should NOT have 2-column or 3-column structure for this product
    # The mj-image for high priority product is 600px wide
    assert 'height="300px"' in mjml


def test_medium_priority_generates_two_column():
    """Medium priority products should produce 2-column (300px each) blocks."""
    products = [_make_product(priority="medium", product_id=f"p{i}") for i in range(2)]
    section = _make_section(products)
    render_input = _make_render_input([section])

    mjml = build_mjml(render_input)

    # Medium priority columns are 300px
    assert 'width="300px"' in mjml
    assert 'height="200px"' in mjml


def test_low_priority_generates_three_column():
    """Low priority products should produce 3-column (200px each) blocks."""
    products = [_make_product(priority="low", product_id=f"p{i}") for i in range(3)]
    section = _make_section(products)
    render_input = _make_render_input([section])

    mjml = build_mjml(render_input)

    # Low priority columns are 200px
    assert 'width="200px"' in mjml
    assert 'height="150px"' in mjml


def test_mixed_priorities_all_present():
    """All three priority levels should be represented in the output."""
    products = [
        _make_product(priority="high", product_id="h1"),
        _make_product(priority="medium", product_id="m1"),
        _make_product(priority="low", product_id="l1"),
    ]
    section = _make_section(products)
    render_input = _make_render_input([section])

    mjml = build_mjml(render_input)

    assert 'height="300px"' in mjml   # high
    assert 'height="200px"' in mjml   # medium
    assert 'height="150px"' in mjml   # low


# ── Tests: Table of Contents ──────────────────────────────────────────────────


def test_toc_row_contains_section_titles():
    """ToC row should include all section titles."""
    toc_entries = [
        ToCEntry(section_title="Footwear", icon_name="footprints", section_id="sec-1"),
        ToCEntry(section_title="Electronics", icon_name="zap", section_id="sec-2"),
    ]
    section = _make_section([], section_id="sec-1", title="Footwear")
    render_input = _make_render_input([section], toc_entries=toc_entries)

    mjml = build_mjml(render_input)

    assert "Footwear" in mjml
    assert "Electronics" in mjml
    assert "section-sec-1" in mjml
    assert "section-sec-2" in mjml


def test_toc_empty_when_no_entries():
    """No ToC row should appear when toc_entries is empty."""
    section = _make_section([_make_product()])
    render_input = _make_render_input([section], toc_entries=[])

    mjml = build_mjml(render_input)

    # The specific anchor pattern used in the ToC row should not be present
    assert "href=\"#section-" not in mjml


# ── Tests: Footer CleverTap tags ──────────────────────────────────────────────


def test_footer_always_contains_unsubscribe_link():
    """{{unsubscribe_link}} must always be present in rendered MJML."""
    section = _make_section([_make_product()])
    render_input = _make_render_input([section])

    mjml = build_mjml(render_input)

    assert "{{unsubscribe_link}}" in mjml


def test_footer_always_contains_view_in_browser():
    """{{view_in_browser}} must always be present in rendered MJML."""
    section = _make_section([_make_product()])
    render_input = _make_render_input([section])

    mjml = build_mjml(render_input)

    assert "{{view_in_browser}}" in mjml


def test_footer_present_even_with_empty_sections():
    """Footer tags are included even when there are no sections."""
    render_input = _make_render_input(sections=[])

    mjml = build_mjml(render_input)

    assert "{{unsubscribe_link}}" in mjml
    assert "{{view_in_browser}}" in mjml


# ── Tests: Manual overrides ───────────────────────────────────────────────────


def test_manual_override_replaces_product_image():
    """A product id in manual_overrides must use the override URL instead of image_url."""
    original_url = "https://example.com/original.jpg"
    override_url = "https://example.com/override.jpg"

    product = _make_product(product_id="prod-override", image_url=original_url)
    section = _make_section([product])
    render_input = _make_render_input(
        [section],
        overrides={"prod-override": override_url},
    )

    mjml = build_mjml(render_input)

    assert override_url in mjml
    assert original_url not in mjml


def test_manual_override_does_not_affect_other_products():
    """Override for one product should not affect other products."""
    p1 = _make_product(product_id="prod-1", image_url="https://example.com/img1.jpg")
    p2 = _make_product(product_id="prod-2", image_url="https://example.com/img2.jpg")
    override_url = "https://example.com/override.jpg"

    section = _make_section([p1, p2])
    render_input = _make_render_input([section], overrides={"prod-1": override_url})

    mjml = build_mjml(render_input)

    assert override_url in mjml
    assert "https://example.com/img2.jpg" in mjml
    assert "https://example.com/img1.jpg" not in mjml


# ── Tests: Locked sections ────────────────────────────────────────────────────


def test_locked_section_produces_identical_mjml_on_repeated_calls():
    """
    build_mjml is a pure function; calling it twice with a locked=True section
    must produce identical output (stable rendering).
    """
    product = _make_product()
    section = _make_section([product], locked=True)
    render_input = _make_render_input([section])

    mjml_first = build_mjml(render_input)
    mjml_second = build_mjml(render_input)

    assert mjml_first == mjml_second


def test_locked_and_unlocked_sections_have_same_structure():
    """
    Locked flag does not change MJML structure — it's a DB-side flag.
    Two identical sections differing only in locked should produce the same product blocks.
    """
    product = _make_product(product_id="same-product")

    section_locked = _make_section([product], section_id="sec-locked", title="Widget", locked=True)
    section_unlocked = _make_section([product], section_id="sec-unlocked", title="Widget", locked=False)

    mjml_locked = build_mjml(_make_render_input([section_locked]))
    mjml_unlocked = build_mjml(_make_render_input([section_unlocked]))

    # Both should have the product image URL
    assert "https://example.com/img.jpg" in mjml_locked
    assert "https://example.com/img.jpg" in mjml_unlocked


# ── Tests: render_campaign returns (html, size_kb) ────────────────────────────


def test_render_campaign_returns_html_and_size():
    """render_campaign must return a 2-tuple (html_string, size_kb)."""
    section = _make_section([_make_product()])
    render_input = _make_render_input([section])

    html, size_kb = render_campaign(render_input)

    assert isinstance(html, str)
    assert len(html) > 0
    assert isinstance(size_kb, float)
    assert size_kb > 0


def test_render_campaign_html_contains_product_name():
    """Rendered HTML must contain the product name from the input."""
    product = ProductData(
        id="p1",
        sku="UNIQUE-SKU-99",
        name="Super Unique Product Name",
        image_url="https://example.com/img.jpg",
        price="₹1,999",
        button_name="Shop Now",
        product_link="https://example.com",
        priority="high",
        position=0,
    )
    section = _make_section([product])
    render_input = _make_render_input([section])

    html, _ = render_campaign(render_input)

    assert "Super Unique Product Name" in html
