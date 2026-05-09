"""
test_responsiveness_validator.py
=================================
Unit tests for app.modules.responsiveness_validator.validate_responsiveness.

All HTML is generated programmatically — no external file dependencies.
"""

from __future__ import annotations

import pytest

from app.modules.responsiveness_validator import (
    DESKTOP_WIDTH,
    MIN_FONT_SIZE_MOBILE,
    MOBILE_STACK_WARN_THRESHOLD,
    MOBILE_WIDTH,
    TALL_STACK_HEIGHT,
    IssueSeverity,
    Viewport,
    _parse_px,
    validate_responsiveness,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_html(body_content: str) -> str:
    """Wrap content in a minimal HTML structure."""
    return f"<html><body>{body_content}</body></html>"


# ── ParsePx helper tests ──────────────────────────────────────────────────────


class TestParsePx:
    def test_plain_number(self):
        assert _parse_px("300") == 300

    def test_px_suffix(self):
        assert _parse_px("300px") == 300

    def test_px_suffix_uppercase(self):
        assert _parse_px("300PX") == 300

    def test_float_rounds_down(self):
        assert _parse_px("299.9px") == 299

    def test_percentage_returns_none(self):
        assert _parse_px("50%") is None

    def test_empty_string_returns_none(self):
        assert _parse_px("") is None

    def test_non_numeric_returns_none(self):
        assert _parse_px("auto") is None

    def test_whitespace_stripped(self):
        assert _parse_px("  400px  ") == 400


# ── Image width tests ─────────────────────────────────────────────────────────


class TestImageWidth:
    def test_wide_image_flags_both_viewports(self):
        """700px image → error on both desktop and mobile."""
        html = make_html('<img src="test.jpg" width="700" />')
        issues = validate_responsiveness(html)
        viewports = {i.viewport for i in issues if i.severity == IssueSeverity.error}
        assert Viewport.desktop in viewports
        assert Viewport.mobile in viewports

    def test_mobile_only_wide_image(self):
        """500px image → error on mobile only (> 375px), not desktop (< 600px)."""
        html = make_html('<img src="test.jpg" width="500" />')
        issues = validate_responsiveness(html)
        mobile_errors = [
            i for i in issues if i.viewport == Viewport.mobile and i.severity == IssueSeverity.error
        ]
        desktop_errors = [
            i for i in issues if i.viewport == Viewport.desktop and i.severity == IssueSeverity.error
        ]
        assert len(mobile_errors) >= 1
        assert len(desktop_errors) == 0

    def test_small_image_no_issues(self):
        """200px image → no issues."""
        html = make_html('<img src="test.jpg" width="200" />')
        issues = validate_responsiveness(html)
        assert len(issues) == 0

    def test_image_exactly_at_desktop_width_no_error(self):
        """Image exactly at DESKTOP_WIDTH (600px) → no image overflow error."""
        html = make_html(f'<img src="test.jpg" width="{DESKTOP_WIDTH}" />')
        issues = validate_responsiveness(html)
        img_errors = [
            i for i in issues
            if i.severity == IssueSeverity.error and "image" in i.description.lower()
        ]
        assert len(img_errors) == 0

    def test_image_exactly_at_mobile_width_no_error(self):
        """Image exactly at MOBILE_WIDTH (375px) → no image overflow error."""
        html = make_html(f'<img src="test.jpg" width="{MOBILE_WIDTH}" />')
        issues = validate_responsiveness(html)
        img_errors = [
            i for i in issues
            if i.severity == IssueSeverity.error and "image" in i.description.lower()
        ]
        assert len(img_errors) == 0

    def test_image_one_px_over_desktop(self):
        """Image at DESKTOP_WIDTH + 1 → error on both viewports."""
        html = make_html(f'<img src="test.jpg" width="{DESKTOP_WIDTH + 1}" />')
        issues = validate_responsiveness(html)
        viewports = {i.viewport for i in issues if i.severity == IssueSeverity.error}
        assert Viewport.desktop in viewports
        assert Viewport.mobile in viewports

    def test_image_one_px_over_mobile(self):
        """Image at MOBILE_WIDTH + 1 → error on mobile only."""
        html = make_html(f'<img src="test.jpg" width="{MOBILE_WIDTH + 1}" />')
        issues = validate_responsiveness(html)
        mobile_errors = [
            i for i in issues if i.viewport == Viewport.mobile and i.severity == IssueSeverity.error
        ]
        desktop_errors = [
            i for i in issues if i.viewport == Viewport.desktop and i.severity == IssueSeverity.error
        ]
        assert len(mobile_errors) >= 1
        assert len(desktop_errors) == 0

    def test_percentage_width_no_false_positive(self):
        """width="100%" → no pixel overflow issue."""
        html = make_html('<img src="test.jpg" width="100%" />')
        issues = validate_responsiveness(html)
        img_issues = [
            i for i in issues
            if "image" in i.description.lower() or "img" in i.description.lower()
        ]
        assert len(img_issues) == 0

    def test_style_width_px_detected(self):
        """Width in style attribute (e.g. style='width:700px') → error on both viewports."""
        html = make_html('<img src="test.jpg" style="width:700px" />')
        issues = validate_responsiveness(html)
        viewports = {i.viewport for i in issues if i.severity == IssueSeverity.error}
        assert Viewport.desktop in viewports
        assert Viewport.mobile in viewports

    def test_multiple_wide_images_all_flagged(self):
        """Two wide images → at least 2 errors (one per image)."""
        html = make_html(
            '<img src="a.jpg" width="700" /><img src="b.jpg" width="650" />'
        )
        issues = validate_responsiveness(html)
        error_count = sum(1 for i in issues if i.severity == IssueSeverity.error)
        assert error_count >= 2

    def test_section_id_propagated(self):
        """section_id should be populated from nearest id-bearing ancestor."""
        html = make_html(
            '<div id="section-abc"><img src="test.jpg" width="700" /></div>'
        )
        issues = validate_responsiveness(html)
        ids = [i.section_id for i in issues if i.section_id is not None]
        assert any("section-abc" in sid for sid in ids)


# ── Column width tests ────────────────────────────────────────────────────────


class TestColumnWidths:
    def test_wide_table_flags_desktop(self):
        """Table cells summing to 700px → error on desktop."""
        html = make_html(
            "<table><tr><td width='350'></td><td width='350'></td></tr></table>"
        )
        issues = validate_responsiveness(html)
        desktop_errors = [
            i for i in issues if i.viewport == Viewport.desktop and i.severity == IssueSeverity.error
        ]
        assert len(desktop_errors) >= 1

    def test_wide_table_also_flags_mobile(self):
        """Table cells summing to 700px → also error on mobile."""
        html = make_html(
            "<table><tr><td width='350'></td><td width='350'></td></tr></table>"
        )
        issues = validate_responsiveness(html)
        mobile_errors = [
            i for i in issues if i.viewport == Viewport.mobile and i.severity == IssueSeverity.error
        ]
        assert len(mobile_errors) >= 1

    def test_clean_table_no_issues(self):
        """Table cells summing to 560px → no column-width issues."""
        html = make_html(
            "<table><tr><td width='280'></td><td width='280'></td></tr></table>"
        )
        issues = validate_responsiveness(html)
        col_issues = [
            i for i in issues
            if "column" in i.description.lower() or "width" in i.description.lower()
        ]
        assert len(col_issues) == 0

    def test_single_cell_exactly_at_desktop_no_error(self):
        """Single td at exactly DESKTOP_WIDTH → no column error."""
        html = make_html(
            f"<table><tr><td width='{DESKTOP_WIDTH}'></td></tr></table>"
        )
        issues = validate_responsiveness(html)
        col_errors = [
            i for i in issues
            if i.severity == IssueSeverity.error and "column" in i.description.lower()
        ]
        assert len(col_errors) == 0

    def test_three_cells_summing_over_desktop(self):
        """Three 250px cells (total 750px) → desktop error."""
        html = make_html(
            "<table><tr>"
            "<td width='250'></td>"
            "<td width='250'></td>"
            "<td width='250'></td>"
            "</tr></table>"
        )
        issues = validate_responsiveness(html)
        desktop_errors = [
            i for i in issues if i.viewport == Viewport.desktop and i.severity == IssueSeverity.error
        ]
        assert len(desktop_errors) >= 1

    def test_tds_without_width_ignored(self):
        """TDs with no explicit width are not counted in the sum."""
        html = make_html(
            "<table><tr><td></td><td></td></tr></table>"
        )
        issues = validate_responsiveness(html)
        col_issues = [
            i for i in issues if "column" in i.description.lower()
        ]
        assert len(col_issues) == 0

    def test_style_width_on_td_detected(self):
        """Width defined via style attribute on td is also detected."""
        html = make_html(
            "<table><tr>"
            "<td style='width:400px'></td>"
            "<td style='width:400px'></td>"
            "</tr></table>"
        )
        issues = validate_responsiveness(html)
        desktop_errors = [
            i for i in issues if i.viewport == Viewport.desktop and i.severity == IssueSeverity.error
        ]
        assert len(desktop_errors) >= 1


# ── Stacked height / mobile scroll tests ─────────────────────────────────────


class TestStackedHeight:
    def test_excessive_stacking_warns(self):
        """Many TDs in a table → warn about mobile scroll height."""
        cells = "".join(
            f"<tr><td width='100'>cell {i}</td><td width='100'>cell {i}b</td></tr>"
            for i in range(10)
        )
        html = make_html(f"<table>{cells}</table>")
        issues = validate_responsiveness(html)
        stack_warns = [
            i for i in issues if i.viewport == Viewport.mobile and i.severity == IssueSeverity.warn
        ]
        assert len(stack_warns) >= 1

    def test_few_rows_no_stack_warn(self):
        """2 rows → no stacking warn."""
        html = make_html("<table><tr><td>a</td></tr><tr><td>b</td></tr></table>")
        issues = validate_responsiveness(html)
        stack_warns = [
            i for i in issues
            if "stack" in i.description.lower() or "height" in i.description.lower()
        ]
        assert len(stack_warns) == 0

    def test_stack_warn_threshold_boundary(self):
        """Exactly MOBILE_STACK_WARN_THRESHOLD cells → no warn; one more → warn."""
        # Exactly at threshold — no warning expected
        cells_ok = "".join(
            f"<tr><td>cell{i}</td></tr>" for i in range(MOBILE_STACK_WARN_THRESHOLD)
        )
        html_ok = make_html(f"<table>{cells_ok}</table>")
        issues_ok = validate_responsiveness(html_ok)
        stack_warns_ok = [
            i for i in issues_ok
            if "stack" in i.description.lower() or "cells" in i.description.lower()
        ]
        assert len(stack_warns_ok) == 0

        # One more than threshold → warn
        cells_over = "".join(
            f"<tr><td>cell{i}</td></tr>" for i in range(MOBILE_STACK_WARN_THRESHOLD + 1)
        )
        html_over = make_html(f"<table>{cells_over}</table>")
        issues_over = validate_responsiveness(html_over)
        stack_warns_over = [
            i for i in issues_over
            if i.viewport == Viewport.mobile and i.severity == IssueSeverity.warn
        ]
        assert len(stack_warns_over) >= 1

    def test_stack_warn_description_mentions_threshold(self):
        """Stack warn description should reference the threshold value."""
        cells = "".join(
            f"<tr><td width='100'>cell {i}</td><td width='100'>cell {i}b</td></tr>"
            for i in range(10)
        )
        html = make_html(f"<table>{cells}</table>")
        issues = validate_responsiveness(html)
        stack_warns = [
            i for i in issues
            if i.viewport == Viewport.mobile
            and i.severity == IssueSeverity.warn
            and ("stack" in i.description.lower() or "cells" in i.description.lower())
        ]
        assert len(stack_warns) >= 1
        assert str(MOBILE_STACK_WARN_THRESHOLD) in stack_warns[0].description


# ── Nowrap overflow tests ─────────────────────────────────────────────────────


class TestNowrapOverflow:
    def test_nowrap_in_narrow_container_warns(self):
        """white-space:nowrap inside a narrow (<MOBILE_WIDTH) container → mobile warn."""
        html = make_html(
            "<table><tr><td width='200'>"
            "<span style='white-space:nowrap'>This is a very long text that will not wrap</span>"
            "</td></tr></table>"
        )
        issues = validate_responsiveness(html)
        nowrap_warns = [
            i for i in issues
            if i.viewport == Viewport.mobile
            and i.severity == IssueSeverity.warn
            and "nowrap" in i.description.lower()
        ]
        assert len(nowrap_warns) >= 1

    def test_nowrap_with_spaces_in_style(self):
        """white-space : nowrap (with spaces around colon) also caught."""
        html = make_html(
            "<table><tr><td width='200'>"
            "<span style='white-space : nowrap'>Long text here</span>"
            "</td></tr></table>"
        )
        issues = validate_responsiveness(html)
        nowrap_warns = [
            i for i in issues
            if i.viewport == Viewport.mobile and i.severity == IssueSeverity.warn
        ]
        assert len(nowrap_warns) >= 1

    def test_nowrap_without_constrained_parent_no_warn(self):
        """white-space:nowrap with no width-constrained ancestor → no warn."""
        html = make_html(
            "<div><span style='white-space:nowrap'>Short</span></div>"
        )
        issues = validate_responsiveness(html)
        nowrap_warns = [
            i for i in issues
            if "nowrap" in i.description.lower()
        ]
        assert len(nowrap_warns) == 0


# ── Font size tests ───────────────────────────────────────────────────────────


class TestFontSize:
    def test_tiny_font_warns_on_mobile(self):
        """Font size below MIN_FONT_SIZE_MOBILE → mobile warn."""
        small_size = MIN_FONT_SIZE_MOBILE - 1
        html = make_html(f"<p style='font-size:{small_size}px'>Small text</p>")
        issues = validate_responsiveness(html)
        font_warns = [
            i for i in issues
            if i.viewport == Viewport.mobile
            and i.severity == IssueSeverity.warn
            and "font" in i.description.lower()
        ]
        assert len(font_warns) >= 1

    def test_font_at_min_size_no_warn(self):
        """Font size exactly at MIN_FONT_SIZE_MOBILE → no warn."""
        html = make_html(f"<p style='font-size:{MIN_FONT_SIZE_MOBILE}px'>OK text</p>")
        issues = validate_responsiveness(html)
        font_warns = [
            i for i in issues
            if "font" in i.description.lower() and i.severity == IssueSeverity.warn
        ]
        assert len(font_warns) == 0

    def test_large_font_no_warn(self):
        """Font size well above threshold → no warn."""
        html = make_html("<p style='font-size:16px'>Normal text</p>")
        issues = validate_responsiveness(html)
        font_warns = [
            i for i in issues if "font" in i.description.lower()
        ]
        assert len(font_warns) == 0

    def test_font_warn_only_mobile_not_desktop(self):
        """Small font warn should target mobile viewport, not desktop."""
        small_size = MIN_FONT_SIZE_MOBILE - 2
        html = make_html(f"<p style='font-size:{small_size}px'>Tiny</p>")
        issues = validate_responsiveness(html)
        font_desktop = [
            i for i in issues
            if i.viewport == Viewport.desktop and "font" in i.description.lower()
        ]
        font_mobile = [
            i for i in issues
            if i.viewport == Viewport.mobile and "font" in i.description.lower()
        ]
        assert len(font_desktop) == 0
        assert len(font_mobile) >= 1

    def test_multiple_tiny_font_elements(self):
        """Multiple elements with tiny fonts → all flagged."""
        small_size = MIN_FONT_SIZE_MOBILE - 1
        html = make_html(
            f"<p style='font-size:{small_size}px'>A</p>"
            f"<span style='font-size:{small_size}px'>B</span>"
        )
        issues = validate_responsiveness(html)
        font_warns = [
            i for i in issues
            if "font" in i.description.lower() and i.severity == IssueSeverity.warn
        ]
        assert len(font_warns) >= 2


# ── Clean HTML tests ──────────────────────────────────────────────────────────


class TestCleanHtml:
    def test_clean_html_returns_empty(self):
        """Minimal well-formed email HTML → no issues."""
        html = make_html(
            "<table><tr>"
            "<td width='280'><img src='x.jpg' width='260' /></td>"
            "<td width='280'><img src='y.jpg' width='260' /></td>"
            "</tr></table>"
        )
        issues = validate_responsiveness(html)
        assert len(issues) == 0

    def test_empty_html_no_crash(self):
        """Empty string → empty list, no exception."""
        issues = validate_responsiveness("")
        assert issues == []

    def test_none_like_html_no_crash(self):
        """Minimal HTML → no crash."""
        issues = validate_responsiveness("<html></html>")
        assert issues == []

    def test_whitespace_only_no_crash(self):
        """Whitespace-only string → empty list."""
        issues = validate_responsiveness("   \n\t  ")
        assert issues == []

    def test_malformed_html_no_crash(self):
        """Malformed / truncated HTML must not raise."""
        issues = validate_responsiveness("<table><tr><td width='300'>unclosed")
        assert isinstance(issues, list)

    def test_html_with_no_tables_or_images_no_crash(self):
        """Pure text email → no crash."""
        issues = validate_responsiveness(make_html("<p>Hello world</p>"))
        assert isinstance(issues, list)

    def test_deeply_nested_html_no_crash(self):
        """Very deeply nested structure must not crash."""
        nested = "<div>" * 50 + "<img src='test.jpg' width='100' />" + "</div>" * 50
        issues = validate_responsiveness(make_html(nested))
        assert isinstance(issues, list)


# ── Constants importability test ──────────────────────────────────────────────


class TestConstants:
    def test_mobile_width_value(self):
        assert MOBILE_WIDTH == 375

    def test_desktop_width_value(self):
        assert DESKTOP_WIDTH == 600

    def test_stack_threshold_positive(self):
        assert MOBILE_STACK_WARN_THRESHOLD > 0

    def test_min_font_size_positive(self):
        assert MIN_FONT_SIZE_MOBILE > 0

    def test_tall_stack_height_positive(self):
        assert TALL_STACK_HEIGHT > 0


# ── Issue dataclass tests ─────────────────────────────────────────────────────


class TestResponsivenessIssueDataclass:
    def test_issue_fields(self):
        """ResponsivenessIssue should expose all required fields."""
        from app.modules.responsiveness_validator import ResponsivenessIssue

        issue = ResponsivenessIssue(
            severity=IssueSeverity.error,
            description="test",
            viewport=Viewport.mobile,
            section_id="sec-1",
            product_id="prod-2",
            element_hint="img",
        )
        assert issue.severity == IssueSeverity.error
        assert issue.viewport == Viewport.mobile
        assert issue.section_id == "sec-1"
        assert issue.product_id == "prod-2"
        assert issue.element_hint == "img"

    def test_issue_optional_fields_default_none(self):
        """Optional fields should default to None."""
        from app.modules.responsiveness_validator import ResponsivenessIssue

        issue = ResponsivenessIssue(
            severity=IssueSeverity.warn,
            description="test",
            viewport=Viewport.desktop,
        )
        assert issue.section_id is None
        assert issue.product_id is None
        assert issue.element_hint is None

    def test_severity_enum_values(self):
        assert IssueSeverity.warn == "warn"
        assert IssueSeverity.error == "error"

    def test_viewport_enum_values(self):
        assert Viewport.mobile == "mobile"
        assert Viewport.desktop == "desktop"


# ── Integration / combined scenarios ─────────────────────────────────────────


class TestCombinedScenarios:
    def test_multiple_issues_types_detected_together(self):
        """HTML with wide image + wide table → both issue types detected."""
        small_size = MIN_FONT_SIZE_MOBILE - 1
        html = make_html(
            f'<img src="hero.jpg" width="700" />'
            f"<table><tr><td width='400'></td><td width='400'></td></tr></table>"
            f"<p style='font-size:{small_size}px'>Fine print</p>"
        )
        issues = validate_responsiveness(html)
        severities = {i.severity for i in issues}
        viewports = {i.viewport for i in issues}
        assert IssueSeverity.error in severities
        assert Viewport.desktop in viewports
        assert Viewport.mobile in viewports

    def test_result_is_list_of_responsiveness_issues(self):
        """Return type is always a list of ResponsivenessIssue objects."""
        from app.modules.responsiveness_validator import ResponsivenessIssue

        html = make_html('<img src="t.jpg" width="700" />')
        issues = validate_responsiveness(html)
        assert isinstance(issues, list)
        for issue in issues:
            assert isinstance(issue, ResponsivenessIssue)

    def test_clean_email_layout_zero_issues(self):
        """
        A typical 2-column email at 560px total with small images and normal
        fonts should produce zero issues.
        """
        html = make_html(
            "<table>"
            "<tr>"
            "  <td width='280'>"
            "    <img src='prod1.jpg' width='260' />"
            "    <p style='font-size:14px'>Product 1</p>"
            "  </td>"
            "  <td width='280'>"
            "    <img src='prod2.jpg' width='260' />"
            "    <p style='font-size:14px'>Product 2</p>"
            "  </td>"
            "</tr>"
            "</table>"
        )
        issues = validate_responsiveness(html)
        assert len(issues) == 0
