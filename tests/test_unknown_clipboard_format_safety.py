"""未知 Windows 剪贴板格式的失败关闭契约。"""

from src.clipboard import listener as listener_module
from src.manipulator import text_toolkit


class EnumeratingClipboard:
    """提供真实枚举语义的内存剪贴板。"""

    CF_UNICODETEXT = 13

    def __init__(self, custom_format: int, custom_name: str):
        self.custom_format = custom_format
        self.custom_name = custom_name
        self.formats = {
            self.CF_UNICODETEXT: "第一行\n第二行",
            custom_format: b"custom",
        }

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

    def EnumClipboardFormats(self, previous):
        for format_id in sorted(self.formats):
            if format_id > previous:
                return format_id
        return 0

    def GetClipboardFormatName(self, format_id):
        return self.custom_name if format_id == self.custom_format else ""

    def EmptyClipboard(self):
        self.formats.clear()

    def SetClipboardText(self, text, format_id):
        self.formats[format_id] = text


def test_unknown_registered_format_is_rejected_in_both_layers(monkeypatch):
    """未知厂商格式存在时不得尝试文本转换。"""
    clipboard = EnumeratingClipboard(0xD001, "Vendor Custom Binary")
    original = dict(clipboard.formats)
    monkeypatch.setattr(listener_module, "wc", clipboard)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    snapshot = listener_module.ClipboardListener().read()
    success, _message = text_toolkit.merge_lines()

    assert snapshot.has_binary is True
    assert success is False
    assert clipboard.formats == original
