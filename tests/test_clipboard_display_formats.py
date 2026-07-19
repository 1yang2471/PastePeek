"""Windows 显示图片格式的主动操作安全契约。"""

import pytest

from src.clipboard import listener as listener_module
from src.manipulator import text_toolkit


@pytest.mark.parametrize("display_format", [0x0082, 0x0083, 0x008E])
def test_display_image_format_is_rejected_in_both_layers(
    monkeypatch,
    display_format,
):
    """显示位图或元文件存在时不得执行文本转换。"""

    class Clipboard:
        CF_UNICODETEXT = 13

        def __init__(self):
            self.formats = {
                self.CF_UNICODETEXT: "第一行\n第二行",
                display_format: b"image",
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
    success, _message = text_toolkit.merge_lines()

    assert snapshot.has_binary is True
    assert success is False
    assert clipboard.formats == original
