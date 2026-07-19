"""跨目标应用真实粘贴验收的内存剪贴板事务服务。

服务进程只在内存中保存启动时的剪贴板快照，按控制目录中的动作准备
测试剪贴板；收到退出动作后恢复原剪贴板。控制文件不包含剪贴板正文。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import win32clipboard as wc

ROOT = Path(__file__).resolve().parents[1]
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
    """读取可安全在内存中恢复的剪贴板格式。"""
    open_clipboard()
    try:
        items: list[tuple[int, object]] = []
        format_id = 0
        while True:
            format_id = wc.EnumClipboardFormats(format_id)
            if not format_id:
                return items
            data = wc.GetClipboardData(format_id)
            if not isinstance(data, (bytes, str, tuple)):
                raise RuntimeError(f"格式 {format_id} 无法安全恢复")
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
    """读取当前 Unicode 文本。"""
    open_clipboard()
    try:
        return wc.GetClipboardData(wc.CF_UNICODETEXT)
    finally:
        wc.CloseClipboard()


def has_format(format_id: int) -> bool:
    """判断当前剪贴板是否仍包含指定格式。"""
    open_clipboard()
    try:
        return bool(wc.IsClipboardFormatAvailable(format_id))
    finally:
        wc.CloseClipboard()


def run_action(action: str) -> dict[str, object]:
    """准备一项已知测试内容并执行对应主动操作。"""
    if action == "inspect_text":
        actual = read_text()
        return {
            "success": True,
            "actual": actual,
            "code_points": [f"U+{ord(character):04X}" for character in actual],
            "correct": True,
        }

    if action == "clean_url":
        source = "https://example.com/p?id=42&required=&utm_source=test#section"
        expected = "https://example.com/p?id=42&required=#section"
        replace_formats([(wc.CF_UNICODETEXT, source)])
        success, message = clean_url()
        actual = read_text()
        return {
            "success": success,
            "message": message,
            "expected": expected,
            "actual": actual,
            "correct": success and actual == expected,
        }

    if action == "merge_lines":
        source = "第一行\r\n第二行\n\n第三行"
        expected = "第一行 第二行 第三行"
        replace_formats([(wc.CF_UNICODETEXT, source)])
        success, message = merge_lines()
        actual = read_text()
        return {
            "success": success,
            "message": message,
            "expected": expected,
            "actual": actual,
            "correct": success and actual == expected,
        }

    if action == "strip_formats":
        source = "标题\r\n正文😀"
        replace_formats(
            [
                (wc.CF_UNICODETEXT, source),
                (CF_HTML, b"<h1>title</h1><p>body</p>"),
                (CF_RTF, b"{\\rtf1 title\\par body}"),
            ]
        )
        success, message = strip_formats()
        actual = read_text()
        return {
            "success": success,
            "message": message,
            "expected": source,
            "actual": actual,
            "html_removed": not has_format(CF_HTML),
            "rtf_removed": not has_format(CF_RTF),
            "correct": success
            and actual == source
            and not has_format(CF_HTML)
            and not has_format(CF_RTF),
        }

    raise ValueError(f"未知验收动作: {action}")


def write_json(path: Path, value: object) -> None:
    """原子写入控制结果。"""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-dir", type=Path, required=True)
    args = parser.parse_args()
    control_dir = args.control_dir
    control_dir.mkdir(parents=True, exist_ok=True)
    command_path = control_dir / "command.json"
    result_path = control_dir / "result.json"
    original = read_all_formats()
    write_json(control_dir / "ready.json", {"ready": True})
    try:
        while True:
            if command_path.exists():
                # Windows PowerShell 可能给控制文件加 UTF-8 BOM，写入瞬间也可能暂时占锁。
                try:
                    command = json.loads(
                        command_path.read_text(encoding="utf-8-sig")
                    )
                except (FileNotFoundError, PermissionError, json.JSONDecodeError):
                    time.sleep(0.05)
                    continue
                command_path.unlink()
                action = command.get("action")
                if action == "exit":
                    write_json(result_path, {"action": action, "ok": True})
                    break
                try:
                    result = run_action(str(action))
                    result.update({"action": action, "ok": bool(result.get("correct"))})
                except Exception as error:
                    result = {"action": action, "ok": False, "error": str(error)}
                write_json(result_path, result)
            time.sleep(0.05)
    finally:
        restored = False
        restore_error = ""
        try:
            replace_formats(original)
            restored = read_all_formats() == original
        except Exception as error:
            restore_error = str(error)
        write_json(
            control_dir / "restored.json",
            {"restored": restored, "error": restore_error},
        )


if __name__ == "__main__":
    main()
