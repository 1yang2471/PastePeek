"""主动操作使用的完整非文本剪贴板安全检测。"""

import win32clipboard as wc

from src.clipboard.formats import (
    BinaryClipboardKinds,
    contains_embedded_binary_content,
)
from src.clipboard.formats import (
    detect_binary_clipboard_kinds as detect_known_binary_clipboard_kinds,
)

RICH_TEXT_FORMAT_IDS = frozenset(
    filter(
        None,
        (
            wc.RegisterClipboardFormat("HTML Format"),
            wc.RegisterClipboardFormat("Rich Text Format"),
        ),
    )
)


def detect_binary_clipboard_kinds(clipboard) -> BinaryClipboardKinds:
    """检测标准、注册格式及 HTML/RTF 内嵌媒体。"""
    known = detect_known_binary_clipboard_kinds(clipboard)
    if known.has_binary:
        return known

    rich_payloads = [
        clipboard.GetClipboardData(format_id)
        for format_id in RICH_TEXT_FORMAT_IDS
        if clipboard.IsClipboardFormatAvailable(format_id)
    ]
    if contains_embedded_binary_content(*rich_payloads):
        return BinaryClipboardKinds(
            has_image=True,
            has_file=False,
            has_audio=False,
        )
    return known
