"""前台目标切换时的控制器稳定性测试。"""

from src.explainer.outcome_predictor import OutcomePredictor
from src.ui.app import PastePeekApp


def test_unknown_focus_does_not_replace_last_known_target():
    """点击 HUD 或系统弹窗时，不应丢失最后一个已知粘贴目标。"""
    app = PastePeekApp()
    app._last_text = "hello"
    app._last_content_type = "plain_text"
    app._last_target = "code_editor"
    app._last_output = OutcomePredictor().generate(
        "plain_text", target="code_editor"
    )
    emitted = []
    app.analysis_ready.connect(emitted.append)

    app._on_target_switched("unknown")

    assert app._last_target == "code_editor"
    assert emitted == []
