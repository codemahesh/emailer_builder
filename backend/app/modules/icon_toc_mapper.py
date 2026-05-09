"""
icon_toc_mapper.py
==================
Pure function module — no app imports.

Maps section titles to Lucide icon names for the email Table of Contents row.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ── Built-in keyword → Lucide icon name mapping ───────────────────────────────

DEFAULT_KEYWORD_MAP: Dict[str, str] = {
    "footwear": "footprints",
    "shoes": "footprints",
    "sneakers": "footprints",
    "apparel": "shirt",
    "clothing": "shirt",
    "fashion": "shirt",
    "electronics": "zap",
    "tech": "cpu",
    "mobile": "smartphone",
    "phone": "smartphone",
    "laptop": "laptop",
    "computers": "monitor",
    "home": "home",
    "furniture": "sofa",
    "kitchen": "utensils",
    "beauty": "sparkles",
    "skincare": "sparkles",
    "health": "heart",
    "sports": "dumbbell",
    "fitness": "dumbbell",
    "gaming": "gamepad-2",
    "toys": "gift",
    "food": "utensils",
    "grocery": "shopping-basket",
    "books": "book-open",
    "auto": "car",
    "travel": "plane",
    "jewelry": "gem",
    "bags": "briefcase",
    "accessories": "watch",
}

DEFAULT_ICON = "tag"  # fallback for unmatched titles


@dataclass
class ToCEntry:
    section_title: str
    icon_name: str
    section_id: str


def map_toc_icons(
    section_titles: List[Tuple[str, str]],  # [(section_id, title), ...]
    keyword_map: Optional[Dict[str, str]] = None,
) -> List[ToCEntry]:
    """
    Pure function. Map section titles to icons using keyword matching.

    Keyword matching: lowercase title, check if any keyword is a substring of the title.
    When multiple keywords match, the first match in keyword_map iteration order wins.
    Unmatched titles get DEFAULT_ICON.
    Preserves input order.

    Parameters
    ----------
    section_titles : list of (section_id, title) tuples
    keyword_map    : optional override for the built-in DEFAULT_KEYWORD_MAP;
                     if supplied it is used *instead of* the default map.

    Returns
    -------
    List of ToCEntry in the same order as section_titles.
    """
    effective_map: Dict[str, str] = keyword_map if keyword_map is not None else DEFAULT_KEYWORD_MAP

    entries: List[ToCEntry] = []
    for section_id, title in section_titles:
        lower_title = title.lower()
        icon_name = DEFAULT_ICON
        for keyword, icon in effective_map.items():
            if keyword in lower_title:
                icon_name = icon
                break
        entries.append(ToCEntry(section_title=title, icon_name=icon_name, section_id=section_id))

    return entries


# ── Self-tests ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Running icon_toc_mapper self-tests …\n")

    # Basic footwear mapping
    result = map_toc_icons([("s1", "Footwear Collection")])
    assert result[0].icon_name == "footprints", f"Expected footprints, got {result[0].icon_name}"
    print("PASS: 'Footwear Collection' → footprints")

    # Tech mapping
    result = map_toc_icons([("s2", "Tech Gadgets")])
    assert result[0].icon_name in ("cpu", "zap"), f"Expected cpu/zap, got {result[0].icon_name}"
    print(f"PASS: 'Tech Gadgets' → {result[0].icon_name}")

    # Unknown category falls back to default
    result = map_toc_icons([("s3", "Unknown Category")])
    assert result[0].icon_name == DEFAULT_ICON, f"Expected tag, got {result[0].icon_name}"
    print("PASS: 'Unknown Category' → tag (default)")

    # Empty input
    result = map_toc_icons([])
    assert result == [], f"Expected [], got {result}"
    print("PASS: empty input → []")

    # Order preserved
    titles = [("a", "Footwear"), ("b", "Books"), ("c", "Gaming")]
    result = map_toc_icons(titles)
    assert [e.section_id for e in result] == ["a", "b", "c"], "Order not preserved"
    print("PASS: ordering preserved")

    # Custom keyword map overrides defaults
    custom_map = {"exclusive": "star"}
    result = map_toc_icons([("s4", "Exclusive Deals")], keyword_map=custom_map)
    assert result[0].icon_name == "star", f"Expected star, got {result[0].icon_name}"
    print("PASS: custom keyword_map override works")

    # Custom map does NOT fall back to defaults (isolated)
    result2 = map_toc_icons([("s5", "Footwear")], keyword_map=custom_map)
    assert result2[0].icon_name == DEFAULT_ICON, (
        f"Custom map should not use defaults; expected tag, got {result2[0].icon_name}"
    )
    print("PASS: custom keyword_map does not bleed into DEFAULT_KEYWORD_MAP")

    print("\nAll self-tests passed.")
