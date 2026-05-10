"""
pytest unit tests for app.modules.price_formatter.format_price
"""
import sys
import os

# Allow running from the backend directory directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.modules.price_formatter import format_price


# ── Edge / null cases ─────────────────────────────────────────────────────────

def test_none_returns_empty():
    assert format_price(None) == ""


def test_empty_string_returns_empty():
    assert format_price("") == ""


def test_whitespace_only_returns_empty():
    assert format_price("   ") == ""


# ── Zero ──────────────────────────────────────────────────────────────────────

def test_zero_bare():
    assert format_price("0") == "0"


# ── Bare numbers (no currency) ────────────────────────────────────────────────

def test_bare_integer():
    assert format_price("4999") == "4,999"


def test_bare_integer_with_commas():
    assert format_price("4,999") == "4,999"


def test_bare_decimal_trailing_zeros_stripped():
    assert format_price("4999.00") == "4,999"


def test_bare_decimal_significant():
    assert format_price("4999.50") == "4,999.50"


def test_bare_comma_decimal_trailing_zeros():
    assert format_price("4,999.00") == "4,999"


# ── Symbol-prefixed ───────────────────────────────────────────────────────────

def test_rupee_with_commas():
    assert format_price("₹4,999") == "₹4,999"


def test_dollar_decimal():
    assert format_price("$49.99") == "$49.99"


def test_pound_integer():
    assert format_price("£49") == "£49"


def test_euro_decimal():
    assert format_price("€12.50") == "€12.50"


def test_yen_integer():
    assert format_price("¥1500") == "¥1,500"


# ── ISO-code prefix ───────────────────────────────────────────────────────────

def test_usd_prefix():
    assert format_price("USD 49.99") == "$49.99"


def test_inr_suffix():
    assert format_price("4999.00 INR") == "₹4,999"


def test_eur_prefix():
    assert format_price("EUR 12.50") == "€12.50"


def test_gbp_prefix():
    assert format_price("GBP 9.99") == "£9.99"


def test_jpy_prefix():
    assert format_price("JPY 1500") == "¥1,500"


# ── Negative prices ───────────────────────────────────────────────────────────

def test_negative_rupee():
    assert format_price("-₹100") == "-₹100"


def test_negative_bare():
    assert format_price("-500") == "-500"


# ── Whitespace handling ───────────────────────────────────────────────────────

def test_leading_trailing_spaces():
    assert format_price("  $  1,234.50  ") == "$1,234.50"


# ── Already-formatted / re-entrant ───────────────────────────────────────────

def test_already_formatted_rupee():
    """format_price should be idempotent on already-formatted values."""
    assert format_price("₹4,999") == "₹4,999"


def test_already_formatted_dollar():
    assert format_price("$49.99") == "$49.99"


# ── Large numbers ─────────────────────────────────────────────────────────────

def test_large_rupee():
    assert format_price("1000000") == "1,000,000"


def test_large_usd():
    assert format_price("USD 1000000.99") == "$1,000,000.99"
