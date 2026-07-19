"""真实 Windows 剪贴板上的三项主动操作验收。"""

import json
import sys
import time
from pathlib import Path

import win32clipboard as wc

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.manipulator.text_toolkit import (  # noqa: E402
    CF_HTML,
    CF_RTF,
    clean_url,
    merge_lines,
    strip_formats,
)


def open_clipboard() -> None:
    """短暂占用时重试打开剪贴板。"""
    for _attempt in range(50):
        try:
            wc.OpenClipboard()
            return
        except Exception:
            time.sleep(0.02)
    raise RuntimeError("无法打开 Windows 剪贴板")


def read_all_formats() -> list[tuple[int, object]]:
    """读取所有可安全在内存中恢复的格式。"""
    open_clipboard()
    try:
        items = []
        format_id = 0
        while True:
            format_id = wc.EnumClipboardFormats(format_id)
            if not format_id:
                return items
            data = wc.GetClipboardData(format_id)
            if not isinstance(data, (bytes, str, tuple)):
                raise RuntimeError(
                    f"格式 {format_id} 无法安全恢复，验收未修改剪贴板"
                )
            items.append((format_id, data))
    finally:
        wc.CloseClipboard()


def replace_formats(items: list[tuple[int, object]]) -> None:
    """用给定格式替换剪贴板。"""
    open_clipboard()
    try:
        wc.EmptyClipboard()
        for format_id, data in items:
            if format_id == wc.CF_UNICODETEXT:
                wc.SetClipboardText(data, format_id)
            else:
                wc.SetClipboardData(format_id, data)
    finally:
        wc.CloseClipboard()


def read_text() -> str:
    open_clipboard()
    try:
        return wc.GetClipboardData(wc.CF_UNICODETEXT)
    finally:
        wc.CloseClipboard()


def has_format(format_id: int) -> bool:
    open_clipboard()
    try:
        return bool(wc.IsClipboardFormatAvailable(format_id))
    finally:
        wc.CloseClipboard()


def assert_restored(expected: list[tuple[int, object]]) -> None:
    """恢复后逐格式核对，不让测试内容残留。"""
    actual = read_all_formats()
    if actual != expected:
        raise RuntimeError("原剪贴板恢复后格式或内容不一致")


def main() -> None:
    original = read_all_formats()
    results = {}
    try:
        source_url = (
            "https://example.com/p?id=42&required=&"
            "utm_source=test#section"
        )
        replace_formats([(wc.CF_UNICODETEXT, source_url)])
        success, _message = clean_url()
        expected_url = "https://example.com/p?id=42&required=#section"
        if not success or read_text() != expected_url:
            raise RuntimeError("真实净化链接验收失败")
        results["clean_url"] = expected_url

        replace_formats([(wc.CF_UNICODETEXT, "第一行\r\n第二行\n\n第三行")])
        success, _message = merge_lines()
        expected_line = "第一行 第二行 第三行"
        if not success or read_text() != expected_line:
            raise RuntimeError("真实合并换行验收失败")
        results["merge_lines"] = expected_line

        rich_text = "标题\r\n正文😀"
        replace_formats([
            (wc.CF_UNICODETEXT, rich_text),
            (CF_HTML, b"<h1>title</h1><p>body</p>"),
            (CF_RTF, b"{\\rtf1 title\\par body}"),
        ])
        success, message = strip_formats()
        if (
            not success
            or read_text() != rich_text
            or has_format(CF_HTML)
            or has_format(CF_RTF)
        ):
            raise RuntimeError("真实清洗格式验收失败")
        results["strip_formats"] = message
    finally:
        replace_formats(original)
        assert_restored(original)

    results["clipboard_restored"] = True
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
