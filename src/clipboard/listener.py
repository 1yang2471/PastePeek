"""Clipboard listener using win32clipboard.

Reads CF_UNICODETEXT and CF_HTML clipboard formats.
Detects binary formats (CF_DIB, CF_WAVE, CF_HDROP) as flags.
"""

from dataclasses import dataclass

import win32clipboard as wc

from src.clipboard.strict_formats import detect_binary_clipboard_kinds

CF_HTML = wc.RegisterClipboardFormat("HTML Format")
CF_RTF = wc.RegisterClipboardFormat("Rich Text Format")


def _decode_cf_html(data: object) -> str:
    """将 Win32 CF_HTML 数据统一转换为 Unicode 字符串。"""
    if isinstance(data, str):
        return data
    if not isinstance(data, bytes):
        return ""

    fields: dict[str, int] = {}
    header = data[:4096].decode("ascii", errors="ignore")
    for line in header.splitlines():
        key, separator, value = line.partition(":")
        if separator and key in {"StartFragment", "EndFragment"}:
            value = value.strip()
            if value.isdigit():
                fields[key] = int(value)

    start = fields.get("StartFragment")
    end = fields.get("EndFragment")
    if (
        start is not None
        and end is not None
        and 0 <= start <= end <= len(data)
    ):
        data = data[start:end]
    return data.decode("utf-8", errors="replace")


@dataclass
class ClipboardData:
    text: str = ""
    html: str = ""
    has_binary: bool = False     # any non-text format present
    has_image: bool = False      # CF_DIB or CF_BITMAP
    has_file:  bool = False      # CF_HDROP (file drops)
    has_rtf: bool = False        # Rich Text Format
    has_unsafe_formats: bool = False  # 可预览但无法完整回滚的格式
    read_succeeded: bool = True  # 是否成功打开并读取剪贴板
    sequence_number: int | None = None  # Windows 剪贴板变化序号


class ClipboardListener:
    """Reads clipboard data for analysis.

    Opens the clipboard and retrieves plain text (CF_UNICODETEXT)
    and HTML (CF_HTML) formats.
    Also detects binary formats as flags (no data extraction).
    """

    def read(self) -> ClipboardData:
        """Read current clipboard contents."""
        result = ClipboardData()
        try:
            wc.OpenClipboard()
            try:
                get_sequence = getattr(wc, "GetClipboardSequenceNumber", None)
                if get_sequence is not None:
                    result.sequence_number = int(get_sequence())
                if wc.IsClipboardFormatAvailable(wc.CF_UNICODETEXT):
                    data = wc.GetClipboardData(wc.CF_UNICODETEXT)
                    if data:
                        result.text = data

                if wc.IsClipboardFormatAvailable(CF_HTML):
                    data = wc.GetClipboardData(CF_HTML)
                    if data:
                        result.html = _decode_cf_html(data)

                if wc.IsClipboardFormatAvailable(CF_RTF):
                    result.has_rtf = True

                binary = detect_binary_clipboard_kinds(wc)
                result.has_image = binary.has_image
                result.has_file = binary.has_file
                result.has_binary = binary.has_binary
                active_action_formats = detect_binary_clipboard_kinds(
                    wc,
                    for_active_action=True,
                )
                result.has_unsafe_formats = active_action_formats.has_binary
            finally:
                wc.CloseClipboard()
        except Exception:
            result.read_succeeded = False
        return result
