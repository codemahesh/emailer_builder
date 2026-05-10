"""
test_section_locking.py
=======================
Tests for Issue 10 — Section locking.

Covers:
- build_mjml with a locked section produces data-locked="true" in MJML
- build_mjml is deterministic: two calls with same locked input → identical output
- Locked vs unlocked section flag is reflected in MJML output (or absence thereof)

Note: DB-level tests (marking locked=True/False) require a running test database
and are exercised via the API integration test suite. The pure-function tests
below run without any DB/network dependencies.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.modules.mjml_renderer import (
    ProductData,
    RenderInput,
    SectionData,
    VisualTokens,
    build_mjml,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_product(
    product_id: str = "prod-1",
    priority: str = "medium",
) -> ProductData:
    return ProductData(
        id=product_id,
        sku=f"SKU-{product_id}",
        name=f"Product {product_id}",
        image_url="https://example.com/img.jpg",
        price="₹999",
        button_name="Buy Now",
        product_link="https://example.com/product",
        priority=priority,
        position=0,
    )


def _make_section(
    locked: bool = False,
    section_id: str = "sec-1",
    title: str = "Test Section",
    products: list | None = None,
) -> SectionData:
    return SectionData(
        id=section_id,
        title=title,
        products=products if products is not None else [_make_product()],
        locked=locked,
        position=0,
    )


def _make_render_input(sections: list) -> RenderInput:
    return RenderInput(
        campaign_id="camp-1",
        campaign_name="Test Campaign",
        sections=sections,
        toc_entries=[],
        visual_tokens=VisualTokens(),
        header_html="",
        footer_html="",
        banner_url="",
        manual_overrides={},
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestLockedSectionMjmlAttribute:
    """Locked sections must carry data-locked="true" in the compiled MJML."""

    def test_locked_section_has_data_locked_attribute(self):
        """
        A section with locked=True must produce `data-locked="true"` on the
        outermost <mj-section> element for that section.
        """
        section = _make_section(locked=True)
        render_input = _make_render_input([section])

        mjml = build_mjml(render_input)

        assert 'data-locked="true"' in mjml

    def test_unlocked_section_does_not_have_data_locked_attribute(self):
        """
        A section with locked=False must NOT have `data-locked="true"` in the
        generated MJML.
        """
        section = _make_section(locked=False)
        render_input = _make_render_input([section])

        mjml = build_mjml(render_input)

        assert 'data-locked="true"' not in mjml

    def test_only_locked_section_carries_attribute_when_mixed(self):
        """
        When a campaign has both locked and unlocked sections, only the locked
        section's <mj-section> element carries data-locked="true".
        """
        locked_section = _make_section(locked=True, section_id="sec-locked", title="Locked")
        unlocked_section = _make_section(locked=False, section_id="sec-unlocked", title="Unlocked")
        render_input = _make_render_input([locked_section, unlocked_section])

        mjml = build_mjml(render_input)

        # The attribute appears exactly once (for the locked section header)
        assert mjml.count('data-locked="true"') == 1

        # Both section IDs are still present
        assert "section-sec-locked" in mjml
        assert "section-sec-unlocked" in mjml


class TestLockedSectionDeterminism:
    """Locked sections must render byte-identically on repeated calls (pure function)."""

    def test_locked_section_identical_on_two_calls(self):
        """
        build_mjml called twice with the same locked-section RenderInput must
        return identical strings.
        """
        section = _make_section(locked=True)
        render_input = _make_render_input([section])

        mjml_first = build_mjml(render_input)
        mjml_second = build_mjml(render_input)

        assert mjml_first == mjml_second

    def test_unlocked_section_identical_on_two_calls(self):
        """
        build_mjml is pure — unlocked sections are also deterministic.
        """
        section = _make_section(locked=False)
        render_input = _make_render_input([section])

        assert build_mjml(render_input) == build_mjml(render_input)

    def test_multiple_products_locked_section_deterministic(self):
        """
        Determinism holds for locked sections with multiple products across
        all priority levels.
        """
        products = [
            _make_product(product_id="h1", priority="high"),
            _make_product(product_id="m1", priority="medium"),
            _make_product(product_id="m2", priority="medium"),
            _make_product(product_id="l1", priority="low"),
        ]
        section = _make_section(locked=True, products=products)
        render_input = _make_render_input([section])

        assert build_mjml(render_input) == build_mjml(render_input)


class TestLockedSectionDbFlag:
    """
    Verify that Section model's locked field defaults to False and can be
    toggled. These tests exercise the dataclass/model layer without a live DB.
    """

    def test_section_data_defaults_locked_false(self):
        """SectionData.locked defaults to False when not specified."""
        section = SectionData(
            id="sec-1",
            title="No Lock Specified",
            products=[],
        )
        assert section.locked is False

    def test_section_data_locked_true(self):
        """SectionData.locked=True is stored and reflected in MJML."""
        section = SectionData(
            id="sec-lock",
            title="Locked Section",
            products=[_make_product()],
            locked=True,
        )
        render_input = _make_render_input([section])
        mjml = build_mjml(render_input)
        assert 'data-locked="true"' in mjml

    def test_section_data_locked_false_explicit(self):
        """SectionData.locked=False produces no data-locked attribute."""
        section = SectionData(
            id="sec-unlock",
            title="Unlocked Section",
            products=[_make_product()],
            locked=False,
        )
        render_input = _make_render_input([section])
        mjml = build_mjml(render_input)
        assert 'data-locked="true"' not in mjml

    def test_locking_does_not_change_product_content(self):
        """
        Toggling locked on a section must not alter the product blocks output.
        The only difference should be the data-locked attribute presence.
        """
        products = [_make_product(product_id="p-same")]

        section_locked = _make_section(locked=True, section_id="s1", title="Widget", products=products)
        section_unlocked = _make_section(locked=False, section_id="s1", title="Widget", products=products)

        mjml_locked = build_mjml(_make_render_input([section_locked]))
        mjml_unlocked = build_mjml(_make_render_input([section_unlocked]))

        # Product image URL present in both
        assert "https://example.com/img.jpg" in mjml_locked
        assert "https://example.com/img.jpg" in mjml_unlocked

        # Locked adds exactly one extra attribute token; strip it and compare structure
        normalized_locked = mjml_locked.replace(' data-locked="true"', "")
        assert normalized_locked == mjml_unlocked
