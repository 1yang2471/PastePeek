"""目标应用识别的 v2.0 回归测试。"""

from src.detector.target_detector import TargetDetector


def test_vscode_electron_window_uses_process_name():
    """Electron 共用窗口类名时，应优先依据进程识别 VS Code。"""
    assert TargetDetector.classify_window(
        "Code.exe", "Chrome_WidgetWin_1"
    ) == "code_editor"
