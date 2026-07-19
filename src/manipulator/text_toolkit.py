"""text_toolkit — clipboard content manipulation tools.

Operations that modify clipboard content and write changes back.

Tools:
  - clean_url()    — strip tracking params from URL in clipboard
  - strip_formats()  — convert rich text to plain text in clipboard
  - merge_lines()    — join multi-line text into single line

Design: each function reads clipboard, transforms content, writes back.
Uses urllib.parse for URL manipulation (no regex hacks).
Edge case: if both CF_UNICODETEXT and CF_HDROP exist, preserve text.
"""

import pywintypes
import win32clipboard as wc

from src.clipboard.strict_formats import detect_binary_clipboard_kinds
from src.content_safety import detect_protected_content_type
from src.url_policy import clean_url_text

# ── 自定义异常 ──────────────────────────────────────────────────────────

class ClipboardBusyError(Exception):
    """剪贴板被其他程序占用，无法访问。"""
    pass


class EmptyContentError(Exception):
    """处理后内容为空，已取消操作。"""
    pass


CF_HTML = wc.RegisterClipboardFormat("HTML Format")
CF_RTF = wc.RegisterClipboardFormat("Rich Text Format")


def _ensure_clipboard_closed():
    """安全关闭剪贴板，确保不会死锁。"""
    try:
        wc.CloseClipboard()
    except Exception:
        pass


def _is_empty(text: str | None) -> bool:
    """检查文本是否为空或仅包含空白。"""
    return not text or not text.strip()


_LINE_BREAK_CHARS = frozenset("\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029")


def _merge_line_text(text: str) -> tuple[str, bool]:
    """合并所有换行，同时保持无换行的单行文本不变。"""
    if not any(char in _LINE_BREAK_CHARS for char in text):
        return text, False
    merged = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return merged, True


def _capture_clipboard_formats(format_ids: tuple[int, ...]) -> list[tuple[int, object]]:
    """在内存中备份已知格式，供写入失败时恢复。"""
    captured = []
    for format_id in format_ids:
        if wc.IsClipboardFormatAvailable(format_id):
            captured.append((format_id, wc.GetClipboardData(format_id)))
    return captured


def _has_binary_clipboard_format() -> bool:
    """判断当前剪贴板是否包含必须保留的非文本格式。"""
    return detect_binary_clipboard_kinds(wc, for_active_action=True).has_binary


def _restore_clipboard_formats(captured: list[tuple[int, object]]) -> None:
    """在当前剪贴板锁内恢复已备份格式。"""
    wc.EmptyClipboard()
    for format_id, data in captured:
        if format_id == wc.CF_UNICODETEXT:
            wc.SetClipboardText(data, format_id)
        else:
            wc.SetClipboardData(format_id, data)


def _write_text_with_rollback(
    text: str,
    captured: list[tuple[int, object]],
) -> None:
    """写入纯文本；失败时尽最大努力恢复原剪贴板。"""
    try:
        wc.EmptyClipboard()
        wc.SetClipboardText(text, wc.CF_UNICODETEXT)
    except Exception as error:
        try:
            _restore_clipboard_formats(captured)
        except Exception as restore_error:
            if isinstance(error, pywintypes.error):
                raise ClipboardBusyError(
                    "剪贴板被其他程序占用，写入失败且无法恢复原内容"
                ) from None
            raise RuntimeError("剪贴板写入失败且无法恢复原内容") from restore_error
        if isinstance(error, pywintypes.error):
            raise ClipboardBusyError(
                "剪贴板被其他程序占用，写入失败；已恢复原内容"
            ) from None
        raise RuntimeError("剪贴板写入失败，已恢复原内容") from error


def clean_url(*, expected_sequence: int | None = None) -> tuple[bool, str]:
    """Strip tracking parameters from a URL in the clipboard.

    Reads clipboard text. If it's a valid URL with tracking params,
    removes them and writes clean URL back.

    Returns:
        (success: bool, message: str) — whether cleaned and how many params removed.

    Raises:
        ClipboardBusyError: 剪贴板被其他程序占用。
        EmptyContentError: 处理后内容为空。
    """
    try:
        wc.OpenClipboard()
        if expected_sequence is not None:
            get_sequence = getattr(wc, "GetClipboardSequenceNumber", None)
            if get_sequence is None or int(get_sequence()) != expected_sequence:
                return False, "剪贴板内容已变化，请查看最新预览后重试"
        if _has_binary_clipboard_format():
            return False, "剪贴板包含图片、文件或音频，已保留原内容"
        has_rich_format = (
            wc.IsClipboardFormatAvailable(CF_HTML)
            or wc.IsClipboardFormatAvailable(CF_RTF)
        )

        text = ""
        if wc.IsClipboardFormatAvailable(wc.CF_UNICODETEXT):
            data = wc.GetClipboardData(wc.CF_UNICODETEXT)
            if data:
                text = data
        if _is_empty(text):
            raise EmptyContentError("处理后内容为空，已取消操作")

        clean_url_str, removed, reason = clean_url_text(text)
        if reason == "not_url":
            return False, "剪贴板内容不是有效的 HTTP(S) URL"
        if reason == "no_query":
            return False, "URL 无查询参数"
        if reason == "protected":
            return False, "链接包含签名或令牌，已保留原内容"
        if reason == "ambiguous":
            return False, "URL 查询结构不明确，已保留原内容"
        if reason == "no_tracking":
            return False, "URL 无追踪参数"

        if _is_empty(clean_url_str):
            raise EmptyContentError("处理后内容为空，已取消操作")

        captured = _capture_clipboard_formats(
            (wc.CF_UNICODETEXT, CF_HTML, CF_RTF)
        )
        _write_text_with_rollback(clean_url_str, captured)

        message = f"已移除 {len(removed)} 个追踪参数: {', '.join(removed[:5])}"
        if has_rich_format:
            message += "；已转为纯文本"
        return True, message
    except ClipboardBusyError:
        raise
    except pywintypes.error:
        raise ClipboardBusyError("剪贴板被其他程序占用，请稍后重试") from None
    except EmptyContentError:
        raise
    except Exception as e:
        return False, f"URL 解析失败: {e}"
    finally:
        _ensure_clipboard_closed()


def strip_formats(*, expected_sequence: int | None = None) -> tuple[bool, str]:
    """Convert clipboard content to plain text (strip HTML/RTF).

    Reads current clipboard, writes back CF_UNICODETEXT only.
    Edge case: if CF_HDROP (files) is also present, keep text only.

    Returns:
        (success: bool, message: str)

    Raises:
        ClipboardBusyError: 剪贴板被其他程序占用。
        EmptyContentError: 处理后内容为空。
    """
    try:
        wc.OpenClipboard()
        if expected_sequence is not None:
            get_sequence = getattr(wc, "GetClipboardSequenceNumber", None)
            if get_sequence is None or int(get_sequence()) != expected_sequence:
                return False, "剪贴板内容已变化，请查看最新预览后重试"
        if _has_binary_clipboard_format():
            return False, "剪贴板包含图片、文件或音频，已保留原内容"
        text = ""
        has_files = wc.IsClipboardFormatAvailable(wc.CF_HDROP)
        has_html = wc.IsClipboardFormatAvailable(CF_HTML)
        has_rtf = wc.IsClipboardFormatAvailable(CF_RTF)

        if wc.IsClipboardFormatAvailable(wc.CF_UNICODETEXT):
            data = wc.GetClipboardData(wc.CF_UNICODETEXT)
            if data:
                text = data

        if _is_empty(text):
            raise EmptyContentError("处理后内容为空，已取消操作")
        if detect_protected_content_type(text) is not None:
            return False, "剪贴板包含代码或结构化内容，已保留原内容"
        if not has_html and not has_rtf and not has_files:
            return False, "已经是纯文本"

        captured = _capture_clipboard_formats(
            (wc.CF_UNICODETEXT, CF_HTML, CF_RTF)
        )
        _write_text_with_rollback(text, captured)
    except ClipboardBusyError:
        raise
    except pywintypes.error:
        raise ClipboardBusyError("剪贴板被其他程序占用，请稍后重试") from None
    except EmptyContentError:
        raise
    except Exception:
        return False, "剪贴板处理失败"
    finally:
        _ensure_clipboard_closed()

    removed_formats = []
    if has_html:
        removed_formats.append("HTML")
    if has_rtf:
        removed_formats.append("RTF")
    if has_files:
        removed_formats.append("文件")
    detail = f"（已移除 {'、'.join(removed_formats)} 格式）"
    return True, f"已转为纯文本{detail}"


def merge_lines(*, expected_sequence: int | None = None) -> tuple[bool, str]:
    """Merge multi-line clipboard text into a single line.

    Joins lines with spaces. Preserves single newline between paragraphs
    (consecutive newlines → single space).

    Returns:
        (success: bool, message: str)

    Raises:
        ClipboardBusyError: 剪贴板被其他程序占用。
        EmptyContentError: 处理后内容为空。
    """
    try:
        wc.OpenClipboard()
        if expected_sequence is not None:
            get_sequence = getattr(wc, "GetClipboardSequenceNumber", None)
            if get_sequence is None or int(get_sequence()) != expected_sequence:
                return False, "剪贴板内容已变化，请查看最新预览后重试"
        if _has_binary_clipboard_format():
            return False, "剪贴板包含图片、文件或音频，已保留原内容"
        has_rich_format = (
            wc.IsClipboardFormatAvailable(CF_HTML)
            or wc.IsClipboardFormatAvailable(CF_RTF)
        )

        text = ""
        if wc.IsClipboardFormatAvailable(wc.CF_UNICODETEXT):
            data = wc.GetClipboardData(wc.CF_UNICODETEXT)
            if data:
                text = data
        if _is_empty(text):
            raise EmptyContentError("处理后内容为空，已取消操作")
        if detect_protected_content_type(text) is not None:
            return False, "剪贴板包含代码或结构化内容，已保留原内容"

        merged, changed = _merge_line_text(text)
        if not changed:
            return False, "已经是单行文本"
        if _is_empty(merged):
            raise EmptyContentError("处理后内容为空，已取消操作")

        captured = _capture_clipboard_formats(
            (wc.CF_UNICODETEXT, CF_HTML, CF_RTF)
        )
        _write_text_with_rollback(merged, captured)
    except ClipboardBusyError:
        raise
    except pywintypes.error:
        raise ClipboardBusyError("剪贴板被其他程序占用，请稍后重试") from None
    except EmptyContentError:
        raise
    except Exception:
        return False, "剪贴板处理失败"
    finally:
        _ensure_clipboard_closed()

    message = "已合并为 1 行"
    if has_rich_format:
        message += "；已转为纯文本"
    return True, message


# ── Preview methods (no clipboard write, return transformed text only) ───

def preview_clean_url(url_text: str) -> str:
    """Return URL with tracking params removed, without touching clipboard.

    Args:
        url_text: Raw URL string (e.g., from clipboard text).

    Returns:
        Cleaned URL if successful, or original text if not a URL / no tracking.
    """
    cleaned, _removed, _reason = clean_url_text(url_text)
    return cleaned


def preview_strip_formats(plain_text: str) -> str:
    """Return plain text as-is (preview for strip_formats action).

    Since the clipboard API gives us the plain text side of rich text,
    the preview is the same as the input — just confirms it will work.
    """
    return plain_text


def preview_merge_lines(text: str) -> str:
    """Return text merged to single line, without touching clipboard.

    Args:
        text: Multi-line text from clipboard.

    Returns:
        Single-line merged text (first 100 chars truncated by caller).
    """
    merged, _changed = _merge_line_text(text)
    return merged
