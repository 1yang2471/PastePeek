"""主动操作的 Windows 剪贴板序号安全契约。"""

from src.clipboard.listener import ClipboardData
from src.manipulator import text_toolkit
from src.ui.app import PastePeekApp
from tests.test_text_toolkit_contract import (
    MemoryClipboard,
    MutableListener,
    TerminalDetector,
)


def test_hud_action_rejects_missing_clipboard_sequence(monkeypatch):
    """无法确认剪贴板版本时不得执行旧 HUD 操作。"""
    data = ClipboardData(text="第一行\n第二行", sequence_number=None)
    listener = MutableListener(data)
    original = {MemoryClipboard.CF_UNICODETEXT: data.text}
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)
    app = PastePeekApp(listener=listener, target_detector=TerminalDetector())

    output = app.check_clipboard()
    assert output is not None
    assert output.primary_action == "merge_lines"

    success, message = app.on_action_triggered("merge_lines")

    assert success is False
    assert "无法确认剪贴板" in message
    assert clipboard.formats == original
