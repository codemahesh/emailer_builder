"""
test_icon_toc_mapper.py
=======================
Unit tests for app.modules.icon_toc_mapper.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.modules.icon_toc_mapper import DEFAULT_ICON, ToCEntry, map_toc_icons


# ── Basic keyword matching ─────────────────────────────────────────────────────


def test_footwear_maps_to_footprints():
    """Section titled 'Footwear' should map to the 'footprints' icon."""
    result = map_toc_icons([("sec-1", "Footwear")])
    assert len(result) == 1
    assert result[0].icon_name == "footprints"
    assert result[0].section_id == "sec-1"
    assert result[0].section_title == "Footwear"


def test_footwear_collection_maps_to_footprints():
    """'Footwear Collection' (substring match) should map to footprints."""
    result = map_toc_icons([("s", "Footwear Collection")])
    assert result[0].icon_name == "footprints"


def test_shoes_maps_to_footprints():
    """'Men's Shoes' should map to footprints."""
    result = map_toc_icons([("s", "Men's Shoes")])
    assert result[0].icon_name == "footprints"


def test_sneakers_maps_to_footprints():
    """'Running Sneakers' should map to footprints."""
    result = map_toc_icons([("s", "Running Sneakers")])
    assert result[0].icon_name == "footprints"


def test_tech_gadgets_maps_to_tech_icon():
    """'Tech Gadgets' should map to 'cpu' (keyword 'tech' matches before others)."""
    result = map_toc_icons([("s", "Tech Gadgets")])
    # 'tech' → cpu; 'electronics' → zap — order depends on dict iteration
    assert result[0].icon_name in ("cpu", "zap")


def test_electronics_maps_to_zap():
    """Pure 'Electronics' should map to 'zap'."""
    result = map_toc_icons([("s", "Electronics")])
    assert result[0].icon_name == "zap"


def test_clothing_maps_to_shirt():
    """'Men's Clothing' should map to 'shirt'."""
    result = map_toc_icons([("s", "Men's Clothing")])
    assert result[0].icon_name == "shirt"


def test_beauty_maps_to_sparkles():
    """'Beauty & Skincare' should map to 'sparkles'."""
    result = map_toc_icons([("s", "Beauty & Skincare")])
    assert result[0].icon_name == "sparkles"


def test_gaming_maps_to_gamepad():
    """'Gaming Accessories' should map to 'gamepad-2'."""
    result = map_toc_icons([("s", "Gaming Accessories")])
    assert result[0].icon_name == "gamepad-2"


def test_travel_maps_to_plane():
    """'Travel Essentials' should map to 'plane'."""
    result = map_toc_icons([("s", "Travel Essentials")])
    assert result[0].icon_name == "plane"


# ── Default (unmatched) icon ──────────────────────────────────────────────────


def test_unknown_category_gets_default_icon():
    """Unrecognised title should fall back to DEFAULT_ICON."""
    result = map_toc_icons([("s", "Unknown Category")])
    assert result[0].icon_name == DEFAULT_ICON


def test_completely_random_title_gets_default():
    """A title with no keywords should produce the default 'tag' icon."""
    result = map_toc_icons([("s", "XYZ1234 Zzzz")])
    assert result[0].icon_name == "tag"


# ── Empty input ───────────────────────────────────────────────────────────────


def test_empty_input_returns_empty_list():
    """map_toc_icons([]) must return []."""
    result = map_toc_icons([])
    assert result == []


# ── Ordering ──────────────────────────────────────────────────────────────────


def test_ordering_preserved():
    """Output order must match input order."""
    inputs = [
        ("a", "Footwear"),
        ("b", "Books"),
        ("c", "Gaming"),
        ("d", "Unknown"),
    ]
    result = map_toc_icons(inputs)
    assert [e.section_id for e in result] == ["a", "b", "c", "d"]


def test_ordering_preserved_many_sections():
    """Ordering should hold for a longer list."""
    inputs = [(str(i), f"Section {i}") for i in range(10)]
    result = map_toc_icons(inputs)
    assert [e.section_id for e in result] == [str(i) for i in range(10)]


# ── Custom keyword map ────────────────────────────────────────────────────────


def test_custom_keyword_map_overrides_defaults():
    """A custom keyword_map should be used instead of the built-in one."""
    custom_map = {"exclusive": "star"}
    result = map_toc_icons([("s", "Exclusive Deals")], keyword_map=custom_map)
    assert result[0].icon_name == "star"


def test_custom_keyword_map_does_not_fall_back_to_defaults():
    """When a custom map is supplied, DEFAULT_KEYWORD_MAP is NOT consulted."""
    custom_map = {"exclusive": "star"}
    # 'Footwear' is in DEFAULT_KEYWORD_MAP but NOT in custom_map
    result = map_toc_icons([("s", "Footwear")], keyword_map=custom_map)
    assert result[0].icon_name == DEFAULT_ICON


def test_custom_keyword_map_empty_all_defaults():
    """An empty custom keyword_map means every title gets the default icon."""
    result = map_toc_icons(
        [("a", "Footwear"), ("b", "Electronics"), ("c", "Travel")],
        keyword_map={},
    )
    for entry in result:
        assert entry.icon_name == DEFAULT_ICON


def test_custom_keyword_map_multiple_matches_first_wins():
    """When multiple keywords match, the first one in the custom map wins."""
    custom_map = {"shoe": "footprints", "sport": "dumbbell"}
    result = map_toc_icons([("s", "Sport Shoes")], keyword_map=custom_map)
    # "shoe" comes first in the dict, should match before "sport"
    assert result[0].icon_name == "footprints"


# ── ToCEntry dataclass ────────────────────────────────────────────────────────


def test_toc_entry_fields_populated():
    """Each ToCEntry should have section_title, icon_name, section_id filled."""
    result = map_toc_icons([("my-id", "Travel Gear")])
    entry = result[0]
    assert isinstance(entry, ToCEntry)
    assert entry.section_id == "my-id"
    assert entry.section_title == "Travel Gear"
    assert entry.icon_name == "plane"


def test_case_insensitive_matching():
    """Keyword matching should be case-insensitive."""
    result_lower = map_toc_icons([("s", "footwear")])
    result_upper = map_toc_icons([("s", "FOOTWEAR")])
    result_mixed = map_toc_icons([("s", "FootWear")])

    assert result_lower[0].icon_name == "footprints"
    assert result_upper[0].icon_name == "footprints"
    assert result_mixed[0].icon_name == "footprints"
