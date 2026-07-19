"""默认目标配置与控制器的集成测试。"""

from src.ui.app import PastePeekApp


def test_unknown_auto_detection_falls_back_to_configured_default(monkeypatch):
    """自动检测未知时，应使用配置的默认粘贴目标。"""
    app = PastePeekApp(default_target="terminal")
    monkeypatch.setattr(
        app._target_detector,
        "get_active_target",
        lambda: "unknown",
    )

    assert app._get_resolved_target() == "terminal"
