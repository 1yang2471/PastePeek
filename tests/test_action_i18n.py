"""主动操作和应用控制器的英文反馈测试。"""

import pytest

from src.clipboard.listener import ClipboardData
from src.manipulator import text_toolkit
from src.ui.app import PastePeekApp


class _Clipboard:
    CF_UNICODETEXT = 13
    CF_DIB = 8

    def __init__(self, formats):
        self.formats = dict(formats)
        self.sequence_number = 1

    def OpenClipboard(self):
        pass

    def CloseClipboard(self):
        pass

    def IsClipboardFormatAvailable(self, format_id):
        return format_id in self.formats

    def GetClipboardData(self, format_id):
        return self.formats[format_id]

    def EnumClipboardFormats(self, previous):
        for format_id in sorted(self.formats):
            if format_id > previous:
                return format_id
        return 0

    def EmptyClipboard(self):
        self.formats.clear()

    def SetClipboardText(self, text, format_id):
        self.formats[format_id] = text

    def GetClipboardSequenceNumber(self):
        return self.sequence_number


def test_merge_lines_uses_requested_language(monkeypatch):
    clipboard = _Clipboard({_Clipboard.CF_UNICODETEXT: "first\nsecond"})
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    ok, message = text_toolkit.merge_lines(language="en-US")

    assert ok is True
    assert message == "Merged into 1 line"


def test_binary_action_refusal_is_localized_and_preserves_clipboard(monkeypatch):
    original = {
        _Clipboard.CF_UNICODETEXT: "image description",
        _Clipboard.CF_DIB: b"pixels",
    }
    clipboard = _Clipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    ok, message = text_toolkit.merge_lines(language="en-US")

    assert ok is False
    assert "original was preserved" in message
    assert clipboard.formats == original


class _Listener:
    def __init__(self, data):
        self.data = data
        self.reads = 0

    def read(self):
        self.reads += 1
        return self.data


class _Target:
    def get_active_target(self):
        return "terminal"


def test_app_language_switch_reemits_cached_output_without_clipboard_read():
    listener = _Listener(ClipboardData(has_binary=True, has_image=True))
    app = PastePeekApp(listener=listener, target_detector=_Target())
    emitted = []
    app.analysis_ready.connect(emitted.append)
    app.check_clipboard()
    assert emitted

    reads = 0
    original_read = listener.read

    def forbidden_read():
        nonlocal reads
        reads += 1
        return original_read()

    listener.read = forbidden_read
    assert app.set_language("en-US") == "en-US"
    assert reads == 0
    output = emitted[-1]
    generated = " ".join(
        [output.content_type_label, output.prediction, output.why, output.suggestion, *output.breakdown]
    )
    assert "Non-text" in generated
    assert not any("\u4e00" <= char <= "\u9fff" for char in generated)


@pytest.mark.parametrize(
    ("text", "html"),
    [
        ("中文正文\r\n第二行", ""),
        ("# 中文标题\n- 清单项目", ""),
        ("def 示例():\n    return '中文值'", ""),
        ("https://example.com/p?name=中文&ref=保留", ""),
        ("", "<p>中文 <strong>HTML</strong></p><pre>代码</pre>"),
    ],
)
def test_language_switch_never_rewrites_cached_clipboard_content(text, html):
    """切换显示语言只能重建文案，不能重读、翻译或改写用户内容。"""
    data = ClipboardData(text=text, html=html, sequence_number=7)
    listener = _Listener(data)
    app = PastePeekApp(listener=listener, target_detector=_Target())
    emitted = []
    app.analysis_ready.connect(emitted.append)

    original = app.check_clipboard()
    assert original is not None
    before = (original.raw_text, original.raw_html)

    app.set_language("en-US")

    refreshed = emitted[-1]
    assert listener.reads == 1
    assert (refreshed.raw_text, refreshed.raw_html) == before
    assert (data.text, data.html) == (text, html)
