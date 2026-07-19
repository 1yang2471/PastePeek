"""严格未知格式检测的已知文本正例。"""

from src.clipboard import listener as listener_module
from src.manipulator import text_toolkit
from src.ui.app import PastePeekApp


def test_known_text_mime_is_previewable_but_not_modified(monkeypatch):
    """已知文本 MIME 可正常预览，但无法完整回滚时不得主动修改。"""
    text_format = text_toolkit.wc.RegisterClipboardFormat("text/plain")

    class Clipboard:
        CF_UNICODETEXT = 13

        def __init__(self):
            self.formats = {
                self.CF_UNICODETEXT: "第一行\n第二行",
                text_format: b"text/plain",
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

        def EmptyClipboard(self):
            self.formats.clear()

        def SetClipboardText(self, text, format_id):
            self.formats[format_id] = text

    clipboard = Clipboard()
    monkeypatch.setattr(listener_module, "wc", clipboard)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    original = dict(clipboard.formats)
    snapshot = listener_module.ClipboardListener().read()
    success, _message = text_toolkit.merge_lines()

    class TargetDetector:
        def get_active_target(self):
            return "word"

    app = PastePeekApp(
        listener=listener_module.ClipboardListener(),
        target_detector=TargetDetector(),
    )
    app.set_manual_target("word")
    output = app.check_clipboard()

    assert snapshot.has_binary is False
    assert output is not None
    assert output.available_actions == []
    assert success is False
    assert clipboard.formats == original
