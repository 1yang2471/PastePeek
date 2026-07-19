"""在本地 Edge 页面中真实回贴三项主动操作结果。"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from accept_real_apps_windows import (
    read_all_formats,
    read_text,
    replace_formats,
    run_action,
)
from pywinauto import Desktop, keyboard

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "edge_acceptance.html"
RESULTS_DIR = ROOT / ".cache" / "edge_acceptance"
TARGET_NAME = "PastePeek Edge 验收输入区"
EDGE_PATHS = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)


def wait_until(
    description: str,
    predicate: Callable[[], object],
    timeout: float = 15,
    interval: float = 0.15,
):
    """轮询可观察状态，超时后报告具体阶段。"""
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except Exception as error:
            last_error = error
        time.sleep(interval)
    suffix = f"，最后异常：{last_error}" if last_error else ""
    raise RuntimeError(f"等待超时：{description}{suffix}")


def find_edge_path() -> Path:
    """返回当前机器上已安装的 Edge 路径。"""
    for path in EDGE_PATHS:
        if path.is_file():
            return path
    raise RuntimeError("未找到 Microsoft Edge")


def edge_windows():
    """返回当前可见的 Edge 顶层窗口。"""
    windows = []
    for window in Desktop(backend="uia").windows():
        try:
            title = window.window_text()
            if "Microsoft" in title and "Edge" in title and window.is_visible():
                windows.append(window)
        except Exception:
            continue
    return windows


def start_isolated_edge():
    """启动只访问本地验收页的新 Edge 窗口。"""
    existing_handles = {window.handle for window in edge_windows()}
    process = subprocess.Popen(
        [
            str(find_edge_path()),
            "--new-window",
            FIXTURE.as_uri(),
            "--no-first-run",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def locate():
        for window in edge_windows():
            if window.handle not in existing_handles:
                return window
        return None

    window = wait_until("新的 Edge 验收窗口", locate, timeout=20)
    wait_until("Edge 本地验收页", lambda: "PastePeek Edge Acceptance" in window.window_text())
    return process, window


def find_target(window):
    """查找本地页面中的唯一文本输入区。"""
    def locate():
        controls = [
            control
            for control in window.descendants(control_type="Edit")
            if control.element_info.name == TARGET_NAME and control.is_visible()
        ]
        if len(controls) > 1:
            raise RuntimeError(f"Edge 验收输入区不唯一：{len(controls)}")
        return controls[0] if controls else None

    return wait_until("Edge 验收输入区", locate)


def copy_target_text(window, target) -> str:
    """从 Edge 输入区复制并读取 Unicode 文本。"""
    window.set_focus()
    target.click_input()
    keyboard.send_keys("^a^c", pause=0.08)
    return wait_until("Edge 回读剪贴板", read_text, timeout=5, interval=0.05)


def clear_target(window, target) -> None:
    """只清空本轮临时页面中的测试文字。"""
    window.set_focus()
    target.click_input()
    keyboard.send_keys("^a{BACKSPACE}", pause=0.08)


def close_test_window(window) -> None:
    """关闭本轮创建的 Edge 窗口。"""
    handle = window.handle
    window.close()
    wait_until(
        "Edge 验收窗口关闭",
        lambda: all(candidate.handle != handle for candidate in edge_windows()),
    )


def main() -> None:
    original = read_all_formats()
    process = None
    window = None
    restored = False
    results: dict[str, object] = {}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        process, window = start_isolated_edge()
        target = find_target(window)
        for action in ("clean_url", "merge_lines", "strip_formats"):
            action_result = run_action(action)
            if not action_result.get("correct"):
                raise AssertionError(f"{action} 主动操作结果错误：{action_result}")
            clear_target(window, target)
            keyboard.send_keys("^v", pause=0.08)
            time.sleep(0.3)
            image_path = RESULTS_DIR / f"{action}.png"
            window.capture_as_image().save(image_path)
            actual = copy_target_text(window, target)
            expected = str(action_result["expected"])
            if actual != expected:
                raise AssertionError(
                    f"{action} Edge 回读不一致：expected={expected!r}, actual={actual!r}"
                )
            results[action] = {
                "expected": expected,
                "actual": actual,
                "screenshot": str(image_path),
            }
        clear_target(window, target)
    finally:
        try:
            if window is not None:
                close_test_window(window)
        finally:
            replace_formats(original)
            restored = read_all_formats() == original

    results.update(
        {
            "passed": True,
            "clipboard_restored": restored,
            "edge_launcher_pid": process.pid if process is not None else None,
        }
    )
    if not restored:
        raise AssertionError("原剪贴板逐格式恢复后不一致")
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
