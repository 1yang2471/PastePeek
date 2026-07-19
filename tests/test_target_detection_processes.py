"""常用 Windows 应用的进程级目标识别测试。"""

import pytest

from src.detector.target_detector import TargetDetector


@pytest.mark.parametrize(
    ("process_name", "expected"),
    [
        ("chrome.exe", "chrome"),
        ("msedge.exe", "chrome"),
        ("Cursor.exe", "code_editor"),
        ("WindowsTerminal.exe", "terminal"),
        ("EXCEL.EXE", "spreadsheet"),
        ("POWERPNT.EXE", "presentation"),
        ("WeChat.exe", "chat_app"),
        ("ms-teams.exe", "chat_app"),
        ("Typora.exe", "markdown_editor"),
        ("Obsidian.exe", "markdown_editor"),
    ],
)
def test_common_processes_are_classified_before_shared_window_class(
    process_name, expected
):
    """常用应用必须覆盖 Chromium/Electron 共用类名造成的歧义。"""
    assert TargetDetector.classify_window(
        process_name, "Chrome_WidgetWin_1"
    ) == expected
