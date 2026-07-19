"""常见注册非文本格式别名的两层安全矩阵。"""

import pytest

from src.clipboard import listener as listener_module
from src.manipulator import text_toolkit

REGISTERED_FORMATS = (
    "image/png",
    "JFIF",
    "image/jpeg",
    "GIF",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "application/x-qt-image",
    "FileGroupDescriptor",
    "Shell IDList Array",
    "FileName",
    "FileNameW",
    "audio/wav",
    "audio/x-wav",
)


@pytest.mark.parametrize("format_name", REGISTERED_FORMATS)
def test_registered_binary_alias_is_rejected_in_both_layers(
    monkeypatch,
    format_name,
):
    """常见非文本别名不得绕过 HUD 或执行层保护。"""
    binary_format = text_toolkit.wc.RegisterClipboardFormat(format_name)

    class Clipboard:
        CF_UNICODETEXT = 13
        CF_DIB = 8
        CF_BITMAP = 2
        CF_HDROP = 15
        CF_WAVE = 12

        def __init__(self):
            self.formats = {
                self.CF_UNICODETEXT: "第一行\n第二行",
                binary_format: b"binary",
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

        def EmptyClipboard(self):
            self.formats.clear()

        def SetClipboardText(self, text, format_id):
            self.formats[format_id] = text

    clipboard = Clipboard()
    original = dict(clipboard.formats)
    monkeypatch.setattr(listener_module, "wc", clipboard)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    snapshot = listener_module.ClipboardListener().read()
    success, message = text_toolkit.merge_lines()

    assert snapshot.has_binary is True
    assert success is False
    assert "已保留原内容" in message
    assert clipboard.formats == original
