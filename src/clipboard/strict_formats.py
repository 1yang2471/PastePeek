"""未知剪贴板格式的失败关闭包装。"""

import win32clipboard as wc

from src.clipboard.formats import BinaryClipboardKinds
from src.clipboard.safe_formats import (
    RICH_TEXT_FORMAT_IDS,
)
from src.clipboard.safe_formats import (
    detect_binary_clipboard_kinds as detect_known_binary_clipboard_kinds,
)

SAFE_STANDARD_TEXT_IDS = frozenset({1, 7, 13, 16, 129})
PREVIEW_SAFE_REGISTERED_NAMES = (
    "text/plain",
    "text/html",
    "text/rtf",
    "UniformResourceLocator",
    "UniformResourceLocatorW",
    "text/x-moz-url",
    "Chromium Web Custom MIME Data Format",
    "WebKit Smart Paste Format",
)
PREVIEW_SAFE_REGISTERED_FORMAT_IDS = frozenset(
    filter(
        None,
        (
            *RICH_TEXT_FORMAT_IDS,
            *(
                wc.RegisterClipboardFormat(name)
                for name in PREVIEW_SAFE_REGISTERED_NAMES
            ),
        ),
    )
)
# 主动操作的回滚实现只保证 HTML/RTF 和标准文本格式。
ROLLBACK_SAFE_REGISTERED_FORMAT_IDS = RICH_TEXT_FORMAT_IDS
# 保留原常量名，供仅做内容分类的调用方使用。
SAFE_REGISTERED_FORMAT_IDS = PREVIEW_SAFE_REGISTERED_FORMAT_IDS


def _has_unknown_format(
    clipboard,
    registered_format_ids: frozenset[int],
) -> bool:
    """枚举不可识别格式；无法枚举也按不确定处理。"""
    enum_formats = getattr(clipboard, "EnumClipboardFormats", None)
    if enum_formats is None:
        return True
    try:
        previous = 0
        seen_ids: set[int] = set()
        while True:
            format_id = int(enum_formats(previous))
            if not format_id:
                if seen_ids:
                    return False
                safe_ids = SAFE_STANDARD_TEXT_IDS | registered_format_ids
                return any(
                    clipboard.IsClipboardFormatAvailable(safe_id)
                    for safe_id in safe_ids
                )
            if format_id in seen_ids:
                return True
            if (
                format_id not in SAFE_STANDARD_TEXT_IDS
                and format_id not in registered_format_ids
            ):
                return True
            seen_ids.add(format_id)
            previous = format_id
    except Exception:
        return True

def detect_binary_clipboard_kinds(
    clipboard,
    *,
    for_active_action: bool = False,
) -> BinaryClipboardKinds:
    """检测已知非文本及未知格式。"""
    known = detect_known_binary_clipboard_kinds(clipboard)
    if known.has_binary:
        return known
    registered_format_ids = (
        ROLLBACK_SAFE_REGISTERED_FORMAT_IDS
        if for_active_action
        else PREVIEW_SAFE_REGISTERED_FORMAT_IDS
    )
    if _has_unknown_format(clipboard, registered_format_ids):
        return BinaryClipboardKinds(
            has_image=False,
            has_file=True,
            has_audio=False,
        )
    return known
