"""Windows 剪贴板格式归一化测试。"""

import pytest

from src.clipboard import listener as listener_module


class FakeWin32Clipboard:
    """提供文本与字节 HTML 的最小 Win32 剪贴板接口。"""

    CF_UNICODETEXT = 13
    CF_DIB = 8
    CF_BITMAP = 2
    CF_HDROP = 15

    def __init__(self, html=None):
        self.html = (
            "<p>正文</p>".encode() if html is None else html
        )

    def OpenClipboard(self):
        pass

    def CloseClipboard(self):
        pass

    def GetClipboardSequenceNumber(self):
        return 42

    def RegisterClipboardFormat(self, _name):
        return 99

    def IsClipboardFormatAvailable(self, format_id):
        return format_id in {self.CF_UNICODETEXT, listener_module.CF_HTML}

    def GetClipboardData(self, format_id):
        if format_id == self.CF_UNICODETEXT:
            return "正文"
        if format_id == listener_module.CF_HTML:
            return self.html
        raise AssertionError(f"未预期的格式：{format_id}")


def test_listener_decodes_cf_html_bytes_to_unicode(monkeypatch):
    """CF_HTML 字节必须在进入分析主流程前解码为字符串。"""
    monkeypatch.setattr(listener_module, "wc", FakeWin32Clipboard())

    data = listener_module.ClipboardListener().read()

    assert data.text == "正文"
    assert data.html == "<p>正文</p>"
    assert data.sequence_number == 42


def test_listener_marks_open_clipboard_failure_without_raising(monkeypatch):
    '''剪贴板暂时被占用时必须返回失败快照，供控制器保留状态。'''

    class FailingClipboard:
        def OpenClipboard(self):
            raise RuntimeError('clipboard busy')

    monkeypatch.setattr(listener_module, 'wc', FailingClipboard())

    data = listener_module.ClipboardListener().read()

    assert data.read_succeeded is False
    assert data.text == ''
    assert data.html == ''
    assert isinstance(data.html, str)


def test_listener_marks_rtf_without_requiring_html(monkeypatch):
    """RTF-only 剪贴板必须进入富文本分类所需的标志。"""

    class RtfOnlyClipboard(FakeWin32Clipboard):
        def IsClipboardFormatAvailable(self, format_id):
            return format_id in {
                self.CF_UNICODETEXT,
                listener_module.CF_RTF,
            }

    monkeypatch.setattr(listener_module, "wc", RtfOnlyClipboard())

    data = listener_module.ClipboardListener().read()

    assert data.text == "正文"
    assert data.html == ""
    assert data.has_rtf is True


def test_listener_extracts_fragment_from_standard_cf_html(monkeypatch):
    """标准 CF_HTML 头部不应进入内容分析，只返回声明的片段。"""
    fragment = "<p>正文</p>".encode()
    prefix = b"<html><body><!--StartFragment-->"
    suffix = b"<!--EndFragment--></body></html>"
    header_size = 105
    start_fragment = header_size + len(prefix)
    end_fragment = start_fragment + len(fragment)
    end_html = end_fragment + len(suffix)
    header = (
        "Version:1.0\r\n"
        f"StartHTML:{header_size:010d}\r\n"
        f"EndHTML:{end_html:010d}\r\n"
        f"StartFragment:{start_fragment:010d}\r\n"
        f"EndFragment:{end_fragment:010d}\r\n"
    ).encode("ascii")
    clipboard = FakeWin32Clipboard(header + prefix + fragment + suffix)
    monkeypatch.setattr(listener_module, "wc", clipboard)

    data = listener_module.ClipboardListener().read()

    assert data.html == "<p>正文</p>"


def test_listener_marks_dibv5_as_binary_image(monkeypatch):
    """DIBV5 图片必须在进入分析流程前标记为非文本。"""

    class DibV5Clipboard(FakeWin32Clipboard):
        CF_DIBV5 = 17
        CF_WAVE = 12

        def IsClipboardFormatAvailable(self, format_id):
            return format_id in {self.CF_UNICODETEXT, self.CF_DIBV5}

    monkeypatch.setattr(listener_module, "wc", DibV5Clipboard())

    data = listener_module.ClipboardListener().read()

    assert data.read_succeeded is True
    assert data.has_image is True
    assert data.has_binary is True


@pytest.mark.parametrize(
    ("binary_format", "is_image"),
    [(3, True), (6, True), (11, False), (14, True), (17, True)],
)
def test_listener_marks_standard_binary_formats(
    monkeypatch,
    binary_format,
    is_image,
):
    """标准图片和音频格式必须在监听层统一标记。"""

    class StandardBinaryClipboard(FakeWin32Clipboard):
        CF_WAVE = 12

        def IsClipboardFormatAvailable(self, format_id):
            return format_id in {self.CF_UNICODETEXT, binary_format}

    monkeypatch.setattr(listener_module, "wc", StandardBinaryClipboard())

    data = listener_module.ClipboardListener().read()

    assert data.read_succeeded is True
    assert data.has_image is is_image
    assert data.has_binary is True
