"""剪贴板格式枚举结果不可信时的失败关闭契约。"""

import pytest

from src.clipboard import listener as listener_module
from src.manipulator import text_toolkit
from tests.test_format_enumeration_failure_safety import UncertainClipboard


class EmptyEnumeratorClipboard(UncertainClipboard):
    """模拟正文存在但枚举器错误返回空。"""

    def EnumClipboardFormats(self, _previous):
        return 0


class RepeatingEnumeratorClipboard(UncertainClipboard):
    """模拟枚举器重复返回同一格式 ID。"""

    def __init__(self):
        super().__init__()
        self.calls = 0

    def EnumClipboardFormats(self, _previous):
        self.calls += 1
        return self.CF_UNICODETEXT if self.calls <= 2 else 0


@pytest.mark.parametrize(
    "clipboard_type",
    [EmptyEnumeratorClipboard, RepeatingEnumeratorClipboard],
)
def test_inconsistent_enumeration_is_rejected_in_both_layers(
    monkeypatch,
    clipboard_type,
):
    """枚举结果与已知正文格式矛盾时不得执行主动处理。"""
    clipboard = clipboard_type()
    original = dict(clipboard.formats)
    monkeypatch.setattr(listener_module, "wc", clipboard)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    snapshot = listener_module.ClipboardListener().read()
    success, _message = text_toolkit.merge_lines()

    assert snapshot.has_binary is True
    assert success is False
    assert clipboard.formats == original
