"""Tests for TargetDetector + COMPATIBILITY_MATRIX — dual-axis content × target prediction.

TDD slice: content_type + target → specific outcome.
"""

import pytest

from src.detector.target_detector import TargetDetector
from src.explainer.outcome_predictor import COMPATIBILITY_MATRIX, OutcomePredictor


class TestCompatibilityMatrix:
    """COMPATIBILITY_MATRIX maps (content_type, target) → per-target outcome."""

    # ── T1: Matrix existence and structure ─────────────────────────

    def test_matrix_exists(self):
        """Matrix is a dict with (content_type, target) tuple keys."""
        assert isinstance(COMPATIBILITY_MATRIX, dict)
        assert len(COMPATIBILITY_MATRIX) > 0
        first_key = next(iter(COMPATIBILITY_MATRIX))
        assert isinstance(first_key, tuple)
        assert len(first_key) == 2

    def test_matrix_entry_has_required_fields(self):
        """Each matrix entry has risk_level, prediction, why, suggestion, breakdown."""
        for key, val in COMPATIBILITY_MATRIX.items():
            assert "risk_level" in val, f"Missing risk_level in {key}"
            assert "prediction" in val, f"Missing prediction in {key}"
            assert "why" in val, f"Missing why in {key}"
            assert "suggestion" in val, f"Missing suggestion in {key}"
            assert "breakdown" in val, f"Missing breakdown in {key}"
            assert val["risk_level"] in ("high", "medium", "low", "none")

    # ── T1: Key entries ────────────────────────────────────────────

    def test_rich_text_to_word_medium(self):
        """Rich text → Word: medium risk, HTML structure concern."""
        entry = COMPATIBILITY_MATRIX[("rich_text", "word")]
        assert entry["risk_level"] == "medium"
        assert "HTML" in entry["why"]
        assert "Ctrl+Shift+V" in entry["suggestion"]

    def test_rich_text_to_code_editor_high(self):
        """Rich text → code editor: HIGH risk, HTML pollution of source code."""
        entry = COMPATIBILITY_MATRIX[("rich_text", "code_editor")]
        assert entry["risk_level"] == "high"
        assert "HTML" in entry["why"] or "标签" in entry["why"]
        assert any("标签" in item for item in entry["breakdown"])

    def test_code_to_word_medium(self):
        """Code → Word: medium risk, indentation loss."""
        entry = COMPATIBILITY_MATRIX[("code", "word")]
        assert entry["risk_level"] in ("medium", "low")
        assert "缩进" in entry["prediction"] or "缩进" in entry["why"]

    def test_plain_text_to_all_safe(self):
        """Plain text → any target: no risk."""
        for target in ("word", "chrome", "code_editor", "unknown"):
            entry = COMPATIBILITY_MATRIX.get(("plain_text", target))
            if entry:
                assert entry["risk_level"] == "none"

    def test_code_to_code_editor_safe(self):
        """Code → code editor: none risk, just paste normally."""
        entry = COMPATIBILITY_MATRIX[("code", "code_editor")]
        assert entry["risk_level"] == "none"

    def test_structured_text_to_chrome(self):
        """Markdown → Chrome (chat box): low risk."""
        entry = COMPATIBILITY_MATRIX[("structured_text", "chrome")]
        assert entry["risk_level"] == "low"


class TestTargetDetectorMapping:
    """TargetDetector._map_classname maps Win32 class names → standard targets."""

    @pytest.fixture
    def detector(self):
        return TargetDetector()

    # ── T2: Class name → target mapping ────────────────────────────

    def test_opus_app_is_word(self, detector):
        assert detector._map_classname("OpusApp") == "word"

    def test_winword_is_word(self, detector):
        assert detector._map_classname("WINWORD") == "word"

    def test_xlmain_is_spreadsheet(self, detector):
        """Excel process → spreadsheet target (not Word)."""
        assert detector._map_classname("XLMAIN") == "spreadsheet"

    def test_chrome_is_chrome(self, detector):
        assert detector._map_classname("Chrome_WidgetWin_1") == "chrome"

    def test_edge_is_chrome(self, detector):
        """Edge uses Chromium — maps to chrome."""
        assert detector._map_classname("Chrome_WidgetWin_1") == "chrome"  # Edge same class

    def test_vscode_is_code_editor(self, detector):
        assert detector._map_classname("VSCode") == "code_editor"

    def test_vim_is_code_editor(self, detector):
        assert detector._map_classname("Vim") == "code_editor"

    def test_putty_is_terminal(self, detector):
        """PuTTY → terminal (not code_editor)."""
        assert detector._map_classname("PuTTY") == "terminal"

    def test_unknown_class_is_unknown(self, detector):
        assert detector._map_classname("SomeRandomApp123") == "unknown"

    def test_empty_class_is_unknown(self, detector):
        assert detector._map_classname("") == "unknown"

    def test_none_class_is_unknown(self, detector):
        assert detector._map_classname(None) == "unknown"

    # ── T2: Case-insensitive matching ──────────────────────────────

    def test_case_insensitive(self, detector):
        assert detector._map_classname("opusapp") == "word"
        assert detector._map_classname("winword") == "word"
        assert detector._map_classname("vscode") == "code_editor"
        assert detector._map_classname("vim") == "code_editor"


class TestOutcomePredictorWithTarget:
    """OutcomePredictor.generate() with target parameter — matrix lookup + fallback."""

    @pytest.fixture
    def predictor(self):
        return OutcomePredictor()

    # ── T3: Target parameter ───────────────────────────────────────

    def test_accepts_target_parameter(self, predictor):
        """generate() accepts optional target parameter, defaults to 'word'."""
        output = predictor.generate("rich_text", target="word")
        assert output.prediction != ""

    def test_rich_text_to_code_editor_high_risk(self, predictor):
        """Matrix lookup: rich_text + code_editor → high risk."""
        output = predictor.generate("rich_text", target="code_editor")
        assert output.risk_level == "high"
        assert "标签" in output.why or "HTML" in output.why

    def test_code_to_code_editor_none_risk(self, predictor):
        """Matrix lookup: code + code_editor → none risk."""
        output = predictor.generate("code", target="code_editor")
        assert output.risk_level == "none"

    def test_unknown_target_falls_back_to_default(self, predictor):
        """Target not in matrix → fall back to content_type-only default (Word)."""
        output = predictor.generate("rich_text", target="notepad")
        assert output.risk_level == "medium"

    def test_default_target_is_word(self, predictor):
        """Without target arg, behaves same as target='word'."""
        no_target = predictor.generate("rich_text")
        with_target = predictor.generate("rich_text", target="word")
        assert no_target.risk_level == with_target.risk_level
        assert no_target.prediction == with_target.prediction

    def test_target_field_in_output(self, predictor):
        """AppOutput carries the target field."""
        output = predictor.generate("rich_text", target="code_editor")
        assert output.target == "code_editor"

    def test_unknown_target_preserved_in_output(self, predictor):
        """Unknown target still recorded in output for debugging."""
        output = predictor.generate("plain_text", target="photoshop")
        assert output.target == "photoshop"
        assert output.risk_level == "none"
