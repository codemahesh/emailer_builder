"""
price_formatter.py
==================
Pure function — no DB or HTTP dependencies.

Parses raw price strings in various formats and returns a normalised,
human-readable price string.

Supported input forms
---------------------
- "₹4,999"         -> "₹4,999"
- "$49.99"          -> "$49.99"
- "£49"             -> "£49"
- "4999"            -> "4,999"          (no symbol assumed bare number)
- "4,999.00"        -> "4,999"          (bare, trailing .00 stripped)
- "4999.00 INR"     -> "₹4,999"         (ISO suffix)
- "USD 49.99"       -> "$49.99"         (ISO prefix)
- "EUR 12.50"       -> "€12.50"
- "-₹100"           -> "-₹100"          (negative preserved)
- ""  / None        -> ""

Doctests
--------
>>> format_price("₹4,999")
'₹4,999'
>>> format_price("$49.99")
'$49.99'
>>> format_price("£49")
'£49'
>>> format_price("4999")
'4,999'
>>> format_price("4,999.00")
'4,999'
>>> format_price("4999.00 INR")
'₹4,999'
>>> format_price("USD 49.99")
'$49.99'
>>> format_price("EUR 12.50")
'€12.50'
>>> format_price("-₹100")
'-₹100'
>>> format_price("")
''
>>> format_price(None)
''
>>> format_price("  $  1,234.50  ")
'$1,234.50'
>>> format_price("GBP 9.99")
'£9.99'
>>> format_price("JPY 1500")
'¥1,500'
"""

from __future__ import annotations

import re
from typing import Optional

# ── Symbol ↔ ISO mappings ─────────────────────────────────────────────────────

_ISO_TO_SYMBOL: dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "JPY": "¥",
    "CAD": "CA$",
    "AUD": "A$",
    "CNY": "¥",
    "MXN": "MX$",
    "BRL": "R$",
    "SGD": "S$",
    "CHF": "CHF",
    "HKD": "HK$",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "NZD": "NZ$",
    "ZAR": "R",
    "AED": "AED",
    "SAR": "SAR",
}

# Reverse mapping: symbol -> canonical ISO (first match wins for shared symbols)
_SYMBOL_TO_ISO: dict[str, str] = {}
for _iso, _sym in _ISO_TO_SYMBOL.items():
    if _sym not in _SYMBOL_TO_ISO:
        _SYMBOL_TO_ISO[_sym] = _iso

# Regex: optional minus, optional currency symbol/code, digits with commas/periods
_PRICE_RE = re.compile(
    r"""
    ^
    (-)?                            # optional leading minus
    \s*
    (                               # currency prefix — symbol or ISO code
        [£$€₹¥]                     # single-char symbols
        |(?:CA|A|S|HK|NZ|MX|R)\$   # multi-char dollar variants
        |R\b                        # Rand
        |kr\b                       # Scandinavian
        |CHF|AED|SAR|R\$            # word codes / BRL
        |[A-Z]{3}                   # generic 3-letter ISO
    )?
    \s*
    ([\d,]+(?:\.\d+)?)              # numeric value
    \s*
    (                               # currency suffix — ISO code
        [A-Z]{3}
    )?
    $
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _strip_trailing_zeros(value_str: str) -> str:
    """Remove .00 or .0 suffix but keep meaningful decimals."""
    if "." in value_str:
        integer_part, decimal_part = value_str.rsplit(".", 1)
        if all(c == "0" for c in decimal_part):
            return integer_part
    return value_str


def _format_number(raw_numeric: str) -> str:
    """Re-format a numeric string with correct comma grouping."""
    # Remove existing commas first
    clean = raw_numeric.replace(",", "")
    stripped = _strip_trailing_zeros(clean)
    if "." in stripped:
        integer_part, decimal_part = stripped.split(".", 1)
        formatted_int = f"{int(integer_part):,}"
        return f"{formatted_int}.{decimal_part}"
    else:
        return f"{int(stripped):,}"


def format_price(raw: Optional[str]) -> str:
    """
    Parse *raw* and return a formatted price string.

    Parameters
    ----------
    raw:
        Raw price string from a spreadsheet cell. May be None or empty.

    Returns
    -------
    str
        Formatted price (e.g. "₹4,999", "$49.99") or empty string if
        *raw* is blank/None.
    """
    if not raw:
        return ""

    text = raw.strip()
    if not text:
        return ""

    # Extract leading minus sign before parsing
    negative = text.startswith("-")
    if negative:
        text = text[1:].strip()

    match = _PRICE_RE.match(text)
    if not match:
        # Cannot parse — return original (trimmed)
        return ("-" if negative else "") + raw.strip()

    _, prefix, numeric, suffix = match.groups()

    # Resolve the display symbol
    symbol = ""
    iso_code = None

    if prefix:
        prefix_upper = prefix.strip().upper()
        # Check if it's a 3-letter ISO code
        if re.fullmatch(r"[A-Z]{3}", prefix_upper) and prefix_upper in _ISO_TO_SYMBOL:
            iso_code = prefix_upper
            symbol = _ISO_TO_SYMBOL[iso_code]
        else:
            # It's a currency symbol (keep as-is)
            symbol = prefix.strip()
    elif suffix:
        suffix_upper = suffix.strip().upper()
        if suffix_upper in _ISO_TO_SYMBOL:
            iso_code = suffix_upper
            symbol = _ISO_TO_SYMBOL[iso_code]
        else:
            # Unknown suffix — append as-is
            symbol = suffix_upper + " "

    formatted_number = _format_number(numeric)
    sign = "-" if negative else ""
    return f"{sign}{symbol}{formatted_number}"


if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)
