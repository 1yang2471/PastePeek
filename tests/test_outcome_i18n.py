"""OutcomePredictor 运行时语言切换测试。"""

from src.explainer.outcome_predictor import OutcomePredictor


def test_english_prediction_contains_no_generated_chinese():
    output = OutcomePredictor().generate("rich_text", "terminal", language="en-US")
    generated = " ".join(
        [
            output.content_type_label,
            output.prediction,
            output.why,
            output.suggestion,
            *output.breakdown,
        ]
    )
    assert "Rich text" in generated
    assert "Terminal" in generated
    assert not any("\u4e00" <= char <= "\u9fff" for char in generated)


def test_language_does_not_change_risk_or_action_keys():
    zh = OutcomePredictor().generate("plain_text", "terminal", language="zh-CN")
    en = OutcomePredictor().generate("plain_text", "terminal", language="en-US")
    assert (zh.risk_level, zh.primary_target) == (en.risk_level, en.primary_target)


def test_english_matrix_preserves_risk_level_for_code_in_word():
    zh = OutcomePredictor().generate("code", "word", language="zh-CN")
    en = OutcomePredictor().generate("code", "word", language="en-US")
    assert (zh.risk_level, en.risk_level) == ("medium", "medium")


def test_unknown_content_type_falls_back_without_chinese_in_english():
    output = OutcomePredictor().generate("unknown_type", "word", language="en-US")
    generated = " ".join(
        [output.content_type_label, output.prediction, output.why, output.suggestion]
    )
    assert output.content_type == "plain_text"
    assert not any("\u4e00" <= char <= "\u9fff" for char in generated)
