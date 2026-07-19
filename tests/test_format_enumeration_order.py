"""Windows 剪贴板格式枚举顺序不排序的兼容契约。"""

from src.clipboard import listener as listener_module
from src.manipulator import text_toolkit
from tests.test_text_toolkit_contract import MemoryClipboard


class NonMonotonicTextClipboard(MemoryClipboard):
    """模拟 Windows 以非递增顺序返回安全文本格式。"""

    order = (13, 16, 1, 7)

    def EnumClipboardFormats(self, previous):
        if previous == 0:
            return self.order[0]
        index = self.order.index(previous)
        return self.order[index + 1] if index + 1 < len(self.order) else 0


def test_non_monotonic_safe_text_formats_remain_actionable(monkeypatch):
    """格式 ID 下降不代表异常，不得误拒绝正常纯文本。"""
    clipboard = NonMonotonicTextClipboard({
        13: "第一行\n第二行",
        16: b"locale",
        1: b"ansi",
        7: b"oem",
    })
    monkeypatch.setattr(listener_module, "wc", clipboard)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    snapshot = listener_module.ClipboardListener().read()
    success, _message = text_toolkit.merge_lines()

    assert snapshot.has_binary is False
    assert success is True
    assert clipboard.formats[13] == "第一行 第二行"
