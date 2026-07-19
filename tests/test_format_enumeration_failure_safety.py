"""剪贴板格式无法完整枚举时的失败关闭契约。"""

import pytest

from src.clipboard import listener as listener_module
from src.manipulator import text_toolkit


class UncertainClipboard:
    """模拟正文可读、但无法确认全部格式的剪贴板。"""

    CF_UNICODETEXT = 13
    EnumClipboardFormats = None

    def __init__(self):
        self.formats = {self.CF_UNICODETEXT: "第一行\n第二行"}

    def OpenClipboard(self):
        pass

    def CloseClipboard(self):
        pass

    def GetClipboardSequenceNumber(self):
        return 42

    def IsClipboardFormatAvailable(self, format_id):
        return format_id in self.formats

    def GetClipboardData(self, format_id):
        return self.formats[format_id]

    def EmptyClipboard(self):
        self.formats.clear()

    def SetClipboardText(self, text, format_id):
        self.formats[format_id] = text


class FailingEnumeratorClipboard(UncertainClipboard):
    """模拟 Windows 在枚举格式时返回错误。"""

    def EnumClipboardFormats(self, _previous):
        raise RuntimeError("枚举失败")


@pytest.mark.parametrize(
    "clipboard_type",
    [UncertainClipboard, FailingEnumeratorClipboard],
)
def test_unverifiable_formats_are_rejected_in_both_layers(
    monkeypatch,
    clipboard_type,
):
    """不确定格式存在时，HUD 与执行层都不得允许主动处理。"""
    clipboard = clipboard_type()
    original = dict(clipboard.formats)
    monkeypatch.setattr(listener_module, "wc", clipboard)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    snapshot = listener_module.ClipboardListener().read()
    success, _message = text_toolkit.merge_lines()

    assert snapshot.has_binary is True
    assert success is False
    assert clipboard.formats == original
