"""
utm_builder.py
==============
Pure function — no DB or HTTP dependencies.

Builds a UTM-stitched URL by appending a ``utm_campaign`` parameter to a
product URL that already carries a global query-string prefix.

Rules
-----
- If *product_link* is empty/None, returns "".
- If *utm_campaign* is empty/None, returns *product_link* unchanged (after
  stripping whitespace).
- If *global_prefix* is empty/None, appends "?utm_campaign=<value>" directly.
- If *product_link* already contains "?", appends "&utm_campaign=<value>".
- If *global_prefix* already contains "?", appends "&utm_campaign=<value>" to it,
  then uses that as the query string for the product link.
- The *global_prefix* is appended to the product link first, then
  utm_campaign is added.

Typical usage
-------------
>>> build_utm("summer_sale", "https://example.com/product?ref=email")
'https://example.com/product?ref=email&utm_campaign=summer_sale'

>>> build_utm("summer_sale", "https://example.com/product")
'https://example.com/product?utm_campaign=summer_sale'

>>> build_utm("", "https://example.com/product")
'https://example.com/product'

>>> build_utm(None, "https://example.com/product")
'https://example.com/product'

>>> build_utm("q1_promo", "")
''

>>> build_utm("q1_promo", None)
''

>>> build_utm("  ", "https://example.com/p")
'https://example.com/p'

>>> build_utm("launch", "https://example.com/p?source=ig")
'https://example.com/p?source=ig&utm_campaign=launch'
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse, urljoin


def build_utm(utm_campaign: Optional[str], product_link: Optional[str]) -> str:
    """
    Build a UTM-stitched URL.

    Parameters
    ----------
    utm_campaign:
        The value for the ``utm_campaign`` query parameter.  Pass None or an
        empty/whitespace-only string to skip appending UTM params.
    product_link:
        The base product URL.  Pass None or empty to receive "".

    Returns
    -------
    str
        The product URL with ``utm_campaign`` appended, or the URL unchanged
        if *utm_campaign* is blank, or "" if *product_link* is blank.
    """
    # Guard: no URL → nothing to do
    if not product_link or not product_link.strip():
        return ""

    base_url = product_link.strip()

    # Guard: no campaign value → return URL unchanged
    if not utm_campaign or not utm_campaign.strip():
        return base_url

    campaign_value = utm_campaign.strip()

    # Determine the correct separator
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}utm_campaign={campaign_value}"


if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)
