"""
pytest unit tests for app.modules.utm_builder.build_utm
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.modules.utm_builder import build_utm


# ── Null / empty guard cases ──────────────────────────────────────────────────

def test_none_product_link_returns_empty():
    assert build_utm("summer_sale", None) == ""


def test_empty_product_link_returns_empty():
    assert build_utm("summer_sale", "") == ""


def test_whitespace_product_link_returns_empty():
    assert build_utm("summer_sale", "   ") == ""


def test_none_utm_returns_url_unchanged():
    url = "https://example.com/product"
    assert build_utm(None, url) == url


def test_empty_utm_returns_url_unchanged():
    url = "https://example.com/product"
    assert build_utm("", url) == url


def test_whitespace_utm_returns_url_unchanged():
    url = "https://example.com/product"
    assert build_utm("   ", url) == url


# ── Basic UTM appending ───────────────────────────────────────────────────────

def test_appends_utm_no_existing_params():
    result = build_utm("summer_sale", "https://example.com/product")
    assert result == "https://example.com/product?utm_campaign=summer_sale"


def test_appends_utm_with_existing_params():
    result = build_utm("summer_sale", "https://example.com/product?ref=email")
    assert result == "https://example.com/product?ref=email&utm_campaign=summer_sale"


def test_appends_utm_url_with_question_mark_trailing():
    """URL already has '?' but no params — use & separator."""
    result = build_utm("launch", "https://example.com/p?source=ig")
    assert result == "https://example.com/p?source=ig&utm_campaign=launch"


def test_utm_with_special_characters_in_value():
    """utm_campaign value should be preserved as-is (no encoding applied)."""
    result = build_utm("q1-promo_2026", "https://example.com/")
    assert result == "https://example.com/?utm_campaign=q1-promo_2026"


def test_strips_whitespace_from_inputs():
    result = build_utm("  campaign  ", "  https://example.com/product  ")
    assert result == "https://example.com/product?utm_campaign=campaign"


# ── Edge: both empty ──────────────────────────────────────────────────────────

def test_both_empty_returns_empty():
    assert build_utm("", "") == ""


def test_both_none_returns_empty():
    assert build_utm(None, None) == ""


# ── Idempotency: utm already in URL ──────────────────────────────────────────

def test_url_already_has_utm_still_appends():
    """build_utm does not deduplicate — appends regardless."""
    result = build_utm("new_campaign", "https://example.com/?utm_campaign=old")
    assert "utm_campaign=new_campaign" in result
    assert result.count("utm_campaign") == 2


# ── Global prefix concatenation (Tech PRD module 15) ────────────────────────

def test_global_prefix_prepended_to_slug():
    """global_prefix is concatenated in front of the per-row utm slug."""
    result = build_utm("summer_sale", "https://example.com/p", "EMAIL_")
    assert result == "https://example.com/p?utm_campaign=EMAIL_summer_sale"


def test_global_prefix_alone_when_slug_empty():
    """An empty slug + non-empty prefix still appends utm_campaign=<prefix>."""
    result = build_utm(None, "https://example.com/p", "EMAIL_2026")
    assert result == "https://example.com/p?utm_campaign=EMAIL_2026"


def test_blank_prefix_and_blank_slug_returns_url_unchanged():
    """Both prefix and slug blank → URL is returned untouched."""
    assert build_utm("", "https://example.com/p", "") == "https://example.com/p"
    assert build_utm(None, "https://example.com/p", None) == "https://example.com/p"


def test_global_prefix_with_existing_query_uses_amp_separator():
    result = build_utm("sale", "https://example.com/p?ref=ig", "Q1_")
    assert result == "https://example.com/p?ref=ig&utm_campaign=Q1_sale"


# ── Long / realistic URL ─────────────────────────────────────────────────────

def test_realistic_product_url():
    url = "https://shop.example.com/collections/summer/products/blue-tee?color=blue&size=M"
    result = build_utm("email_may2026", url)
    assert result == (
        "https://shop.example.com/collections/summer/products/blue-tee"
        "?color=blue&size=M&utm_campaign=email_may2026"
    )
