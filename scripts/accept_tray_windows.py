"""使用 Windows UIA 验收便携 EXE 的中英文托盘生命周期。"""

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import win32gui
from pywinauto import Desktop, mouse

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "PastePeek.exe"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.i18n import DEFAULT_LANGUAGE, translate  # noqa: E402


def wait_until(
    description: str,
    predicate: Callable[[], object],
    *,
    timeout: float = 15,
    interval: float = 0.1,
):
    """轮询真实桌面状态，超时后报告具体阶段。"""
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


def visible_pastepeek_handles() -> list[int]:
    """枚举当前可见的 PastePeek 顶层窗口。"""
    handles: list[int] = []

    def collect(handle: int, _extra: object) -> None:
        if win32gui.IsWindowVisible(handle) and win32gui.GetWindowText(handle) == "PastePeek":
            handles.append(handle)

    win32gui.EnumWindows(collect, None)
    return handles


def visible_window():
    """返回唯一可见的 PastePeek UIA 窗口。"""
    handles = visible_pastepeek_handles()
    if len(handles) != 1:
        return None
    return Desktop(backend="uia").window(handle=handles[0])


def close_button(window, language: str = DEFAULT_LANGUAGE):
    """悬停 HUD 后定位关闭按钮。"""
    rect = window.rectangle()
    mouse.move(coords=(rect.left - 20, rect.top - 20))
    time.sleep(0.2)
    mouse.move(coords=(rect.left + rect.width() // 2, rect.top + 10))

    def locate():
        for control in window.descendants(control_type="Button"):
            if (
                control.element_info.name
                == translate("hide_hud_accessible", language)
                and control.is_visible()
            ):
                return control
        return None

    return wait_until("HUD 关闭按钮", locate)


def isolated_environment(language: str) -> dict[str, str]:
    """使用隔离配置，避免修改用户的 HUD 偏好。"""
    environment = os.environ.copy()
    state = ROOT / ".cache" / f"tray_acceptance_state-{language}"
    config_dir = state / "PastePeek"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(
        json.dumps({"language": language}, ensure_ascii=False),
        encoding="utf-8",
    )
    environment["LOCALAPPDATA"] = str(state)
    return environment


def stop_process_tree(process: subprocess.Popen | None) -> None:
    """只清理本轮启动的主实例进程树。"""
    if process is None or process.poll() is not None:
        return
    subprocess.run(
        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
        capture_output=True,
        check=False,
    )
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def launch_secondary(environment: dict[str, str]) -> None:
    """启动手动第二实例并确认它完成唤醒后退出。"""
    secondary = subprocess.Popen(
        [str(EXE)],
        cwd=ROOT,
        env=environment,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    secondary.wait(timeout=15)
    if secondary.returncode != 0:
        raise RuntimeError(f"手动第二实例退出码异常：{secondary.returncode}")


def run_scenario(language: str) -> None:
    """以指定语言执行后台启动、唤醒和隐藏验收。"""
    environment = isolated_environment(language)
    primary: subprocess.Popen | None = None
    try:
        primary = subprocess.Popen(
            [str(EXE), "--background"],
            cwd=ROOT,
            env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        time.sleep(4)
        if primary.poll() is not None:
            raise RuntimeError(f"后台主实例提前退出：{primary.returncode}")
        if visible_pastepeek_handles():
            raise AssertionError("后台启动不应显示 HUD")

        launch_secondary(environment)
        window = wait_until("第二次启动恢复 HUD", visible_window)
        first_handle = window.handle

        close_button(window, language).click_input()
        wait_until("关闭按钮隐藏 HUD", lambda: not visible_pastepeek_handles())
        if primary.poll() is not None:
            raise AssertionError("隐藏 HUD 后主实例不应退出")

        launch_secondary(environment)
        restored = wait_until("再次启动恢复隐藏 HUD", visible_window)
        if restored.handle != first_handle:
            raise AssertionError("重复启动创建了新的 HUD 窗口")
        if primary.poll() is not None:
            raise AssertionError("重复启动后主实例不应退出")

        print(
            "tray_acceptance=ok "
            f"language={language} primary_pid={primary.pid} hud_handle={first_handle}"
        )
    finally:
        stop_process_tree(primary)

    wait_until("验收进程清理", lambda: not visible_pastepeek_handles())
    print(f"tray_acceptance_cleanup=ok language={language}")


def main() -> None:
    """分别验收默认中文与持久化英文的托盘生命周期。"""
    if not EXE.exists():
        raise FileNotFoundError(f"缺少便携 EXE：{EXE}")
    if visible_pastepeek_handles():
        raise RuntimeError("验收前已有可见 PastePeek 窗口")

    for language in (DEFAULT_LANGUAGE, "en-US"):
        run_scenario(language)


if __name__ == "__main__":
    main()
