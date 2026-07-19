"""Tests for OutcomePredictor — per-target paste outcome prediction.

Tests verify static mappings of content-type → per-target outcomes.
No parsing, no AI, no rules engine — pure dict lookup.
"""

from src.explainer.outcome_predictor import OutcomePredictor


class TestOutcomePredictor:
    """OutcomePredictor maps content_type → AppOutput with prediction/why/suggestion."""

    def test_rich_text_risk(self):
        engine = OutcomePredictor()
        output = engine.generate("rich_text")
        assert output.risk_level == "medium"
        assert "⚠" in output.risk_label
        assert output.content_type_label == "富文本"

    def test_rich_text_prediction(self):
        """Rich text → prediction mentions 'Word 中'."""
        engine = OutcomePredictor()
        output = engine.generate("rich_text")
        assert "Word" in output.prediction

    def test_rich_text_why(self):
        """Rich text → why mentions 'HTML'."""
        engine = OutcomePredictor()
        output = engine.generate("rich_text")
        assert "HTML" in output.why

    def test_rich_text_suggestion(self):
        """Rich text → suggestion mentions Ctrl+Shift+V."""
        engine = OutcomePredictor()
        output = engine.generate("rich_text")
        assert "Ctrl+Shift+V" in output.suggestion

    def test_plain_text_no_risk(self):
        engine = OutcomePredictor()
        output = engine.generate("plain_text")
        assert output.risk_level == "none"
        assert "✓" in output.risk_label
        assert output.content_type_label == "纯文本"

    def test_plain_text_prediction(self):
        engine = OutcomePredictor()
        output = engine.generate("plain_text")
        assert "正常" in output.prediction

    def test_plain_text_suggestion(self):
        engine = OutcomePredictor()
        output = engine.generate("plain_text")
        assert "直接粘贴" in output.suggestion

    def test_structured_text_low_risk(self):
        engine = OutcomePredictor()
        output = engine.generate("structured_text")
        assert output.risk_level == "low"
        assert output.content_type_label == "结构化"

    def test_structured_text_prediction(self):
        engine = OutcomePredictor()
        output = engine.generate("structured_text")
        assert "缩进" in output.prediction or "列表" in output.prediction

    def test_code_low_risk(self):
        engine = OutcomePredictor()
        output = engine.generate("code")
        assert output.risk_level in ("low", "medium")  # medium in COMPATIBILITY_MATRIX
        assert output.content_type_label == "代码"

    def test_code_suggestion(self):
        engine = OutcomePredictor()
        output = engine.generate("code")
        assert "保留原始缩进" in output.suggestion

    def test_unknown_type_falls_back(self):
        engine = OutcomePredictor()
        output = engine.generate("unknown_type_xyz")
        assert output.risk_level == "none"
        assert output.content_type_label == "纯文本"

    def test_all_types_have_output(self):
        engine = OutcomePredictor()
        for ct in ["rich_text", "plain_text", "structured_text", "code"]:
            output = engine.generate(ct)
            assert output.risk_label != ""
            assert output.prediction != ""
            assert output.why != ""
            assert output.suggestion != ""

    def test_rich_text_breakdown(self):
        engine = OutcomePredictor()
        output = engine.generate("rich_text")
        assert len(output.breakdown) == 3
        assert any("缩进" in item for item in output.breakdown)
        assert any("横线" in item for item in output.breakdown)

    def test_plain_text_no_breakdown(self):
        engine = OutcomePredictor()
        output = engine.generate("plain_text")
        assert output.breakdown == []

    def test_structured_text_breakdown(self):
        engine = OutcomePredictor()
        output = engine.generate("structured_text")
        assert len(output.breakdown) == 2

    def test_code_breakdown(self):
        engine = OutcomePredictor()
        output = engine.generate("code")
        assert len(output.breakdown) == 2
        assert any("缩进" in item for item in output.breakdown)

    def test_rich_text_predictions_match_clipboard_plain_text_fallback(self):
        """纯文本目标不会把剪贴板 HTML 标签原样贴出。"""
        engine = OutcomePredictor()

        for target in ("terminal", "code_editor"):
            output = engine.generate("rich_text", target)
            copy = " ".join(
                [output.prediction, output.why, output.suggestion, *output.breakdown]
            )
            assert "标签会" not in copy
            assert "标签原样" not in copy
            assert "纯文本" in copy

        markdown = engine.generate("rich_text", "markdown_editor")
        markdown_copy = " ".join(
            [
                markdown.prediction,
                markdown.why,
                markdown.suggestion,
                *markdown.breakdown,
            ]
        )
        assert "转换" in markdown_copy
        assert "标签会显示为源码" not in markdown_copy
