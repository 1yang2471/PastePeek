"""注册二进制格式的监听安全矩阵。"""

import pytest

from src.clipboard import listener as listener_module


@pytest.mark.parametrize(
    ("format_name", "kind"),
    [
        ("PNG", "image"),
        ("FileGroupDescriptorW", "file"),
        ("FileContents", "file"),
        ("audio/mpeg", "audio"),
    ],
)
def test_listener_marks_registered_binary_format(monkeypatch, format_name, kind):
    """注册图片、虚拟文件、音频格式必须进入非文本状态。"""
    binary_format = listener_module.wc.RegisterClipboardFormat(format_name)

    class RegisteredBinaryClipboard:
        CF_UNICODETEXT = 13
        CF_DIB = 8
        CF_BITMAP = 2
        CF_HDROP = 15
        CF_WAVE = 12

        def OpenClipboard(self):
            pass

        def CloseClipboard(self):
            pass

        def GetClipboardSequenceNumber(self):
            return 42

        def IsClipboardFormatAvailable(self, format_id):
            return format_id in {self.CF_UNICODETEXT, binary_format}

        def GetClipboardData(self, format_id):
            return "正文" if format_id == self.CF_UNICODETEXT else b"binary"

    monkeypatch.setattr(listener_module, "wc", RegisteredBinaryClipboard())

    data = listener_module.ClipboardListener().read()

    assert data.read_succeeded is True
    assert data.has_binary is True
    assert data.has_image is (kind == "image")
    assert data.has_file is (kind == "file")
