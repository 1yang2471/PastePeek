"""前台窗口公共识别入口的回归测试。"""

from src.detector.target_detector import TargetDetector


def test_window_target_uses_process_aware_classifier(monkeypatch):
    """Win32 窗口入口必须把进程、类名和标题交给统一分类器。"""
    monkeypatch.setattr(
        TargetDetector,
        "_read_window_details",
        staticmethod(
            lambda _hwnd: ("Code.exe", "Chrome_WidgetWin_1", "main.py")
        ),
    )

    assert TargetDetector.get_target_for_window(123) == "code_editor"
