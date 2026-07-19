"""当前前台窗口识别入口的集成测试。"""

from src.detector import target_detector
from src.detector.target_detector import TargetDetector


class _ForegroundWindowBoundary:
    """只暴露测试所需的 Win32 前台窗口边界。"""

    @staticmethod
    def GetForegroundWindow():
        return 321


def test_active_target_uses_process_aware_window_api(monkeypatch):
    """前台识别必须复用包含进程信息的窗口公共入口。"""
    monkeypatch.setattr(target_detector, "_user32", _ForegroundWindowBoundary())
    monkeypatch.setattr(
        TargetDetector,
        "get_target_for_window",
        staticmethod(lambda hwnd: "code_editor" if hwnd == 321 else "unknown"),
    )

    assert TargetDetector.get_active_target() == "code_editor"
