"""Tests for smart action recommendation based on (content_type, target).

Verifies _determine_action_type() returns the expected primary action
and available actions for various content/target combinations.
"""


from src.ui.app import _determine_action_type


class TestActionRecommendationMapping:
    """Primary action is chosen by (content_type, target)."""

    def test_rich_text_to_word_recommends_strip_formats(self):
        primary, available = _determine_action_type(
            "rich_text", "word", False, False, False,
            "line1\nline2",
        )
        assert primary == "strip_formats"
        assert "strip_formats" in available

    def test_rich_text_to_chat_app_recommends_strip_formats(self):
        primary, available = _determine_action_type(
            "rich_text", "chat_app", False, False, False,
            "line1\nline2",
        )
        assert primary == "strip_formats"

    def test_rich_text_to_markdown_editor_recommends_strip_formats(self):
        primary, available = _determine_action_type(
            "rich_text", "markdown_editor", False, False, False,
            "line1\nline2",
        )
        assert primary == "strip_formats"

    def test_rich_text_to_terminal_recommends_merge_lines(self):
        primary, available = _determine_action_type(
            "rich_text", "terminal", False, False, False,
            "line1\nline2",
        )
        assert primary == "merge_lines"
        assert "merge_lines" in available

    def test_plain_text_to_terminal_recommends_merge_lines(self):
        primary, available = _determine_action_type(
            "plain_text", "terminal", False, False, False,
            "line1\nline2",
        )
        assert primary == "merge_lines"

    def test_plain_text_single_line_to_terminal_no_action(self):
        primary, available = _determine_action_type(
            "plain_text", "terminal", False, False, False,
            "single line",
        )
        assert primary == ""
        assert "merge_lines" not in available

    def test_structured_text_with_tracked_url_recommends_clean_url(self):
        url = "https://example.com?utm_source=newsletter"
        primary, available = _determine_action_type(
            "structured_text", "word", True, True, False,
            url,
        )
        assert primary == "clean_url"
        assert "clean_url" in available

    def test_structured_text_without_url_no_action(self):
        primary, available = _determine_action_type(
            "structured_text", "word", False, False, False,
            "# Title\n- item",
        )
        assert primary == ""

    def test_code_to_any_target_is_noop(self):
        for target in ("word", "terminal", "code_editor", "markdown_editor", "chat_app"):
            primary, available = _determine_action_type(
                "code", target, False, False, False,
                "def foo():\n    pass",
            )
            assert primary == "", f"code -> {target} should have no primary action"
            assert "merge_lines" not in available

    def test_binary_content_has_no_actions(self):
        primary, available = _determine_action_type(
            "rich_text", "word", False, False, True,
            "ignored",
        )
        assert primary == ""
        assert available == []


class TestActionRecommendationAvailability:
    """Available actions reflect content characteristics."""

    def test_url_with_tracking_is_available_but_not_primary_for_unsuitable_target(self):
        url = "https://example.com?utm_source=newsletter"
        primary, available = _determine_action_type(
            "plain_text", "terminal", True, True, False,
            url,
        )
        assert primary == ""  # terminal is not a URL-suitable target
        assert "clean_url" in available

    def test_url_with_tracking_is_primary_for_suitable_target(self):
        url = "https://example.com?utm_source=newsletter"
        for target in ("word", "chrome", "chat_app", "markdown_editor"):
            primary, available = _determine_action_type(
                "plain_text", target, True, True, False,
                url,
            )
            assert primary == "clean_url", f"expected clean_url primary for {target}"
            assert "clean_url" in available

    def test_rich_text_markdown_editor_with_tracked_url_prefers_clean_url(self):
        url = "https://example.com?utm_source=newsletter"
        primary, available = _determine_action_type(
            "rich_text", "markdown_editor", True, True, False,
            url,
        )
        assert primary == "clean_url"
        assert "strip_formats" in available
        assert "clean_url" in available

    def test_rich_text_provides_strip_formats_and_merge_lines(self):
        primary, available = _determine_action_type(
            "rich_text", "terminal", False, False, False,
            "line1\nline2",
        )
        assert "strip_formats" in available
        assert "merge_lines" in available
