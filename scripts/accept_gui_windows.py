"""使用 pywinauto 对源码版与 EXE 执行真实 Windows GUI 验收。"""

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import win32api
import win32clipboard as wc
import win32gui
from pywinauto import Desktop, keyboard, mouse

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
RESULTS_DIR = CACHE / "gui_acceptance"
TEST_URL = "https://example.com/path?utm_source=codex&utm_medium=qa&id=42"
CLEAN_URL = "https://example.com/path?id=42"
TEST_TERMINAL_TITLE = "PastePeek QA Terminal"
_GUI_INPUT_MODE = "physical"
_GUI_INPUT_FALLBACK_REASON = ""

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.i18n import DEFAULT_LANGUAGE, content_type_label, target_label, translate  # noqa: E402


def reset_gui_input() -> None:
    """让每轮验收优先使用真实鼠标输入。"""
    global _GUI_INPUT_MODE, _GUI_INPUT_FALLBACK_REASON
    _GUI_INPUT_MODE = "physical"
    _GUI_INPUT_FALLBACK_REASON = ""


def gui_input_mode() -> str:
    """返回本轮实际使用的输入模式。"""
    return _GUI_INPUT_MODE


def gui_input_fallback_reason() -> str:
    """返回从真实鼠标降级的 Windows 错误。"""
    return _GUI_INPUT_FALLBACK_REASON


def _cursor_input_unavailable(error: Exception) -> bool:
    """只识别当前桌面会话明确拒绝移动鼠标的错误。"""
    winerror = getattr(error, "winerror", None)
    if winerror is None and error.args:
        winerror = error.args[0]
    return winerror == 2 and "SetCursorPos" in str(error)


def _enable_uia_fallback(error: Exception) -> None:
    """记录回退原因，禁止把 UIA 调用写成真实鼠标通过。"""
    global _GUI_INPUT_MODE, _GUI_INPUT_FALLBACK_REASON
    _GUI_INPUT_MODE = "uia-fallback"
    _GUI_INPUT_FALLBACK_REASON = str(error)


def click_control(control, *, coords: tuple[int, int] | None = None) -> None:
    """真实点击优先；仅在 SetCursorPos 不可用时调用控件。"""
    kwargs = {"coords": coords} if coords is not None else {}
    if _GUI_INPUT_MODE == "physical":
        try:
            control.click_input(**kwargs)
            return
        except Exception as error:
            if not _cursor_input_unavailable(error):
                raise
            _enable_uia_fallback(error)
    control.click(**kwargs)


def move_cursor(coords: tuple[int, int]) -> bool:
    """移动真实鼠标；不可用时切换输入模式并返回 False。"""
    if _GUI_INPUT_MODE != "physical":
        return False
    try:
        mouse.move(coords=coords)
        return True
    except Exception as error:
        if not _cursor_input_unavailable(error):
            raise
        _enable_uia_fallback(error)
        return False


def wait_until(
    description: str,
    predicate: Callable[[], object],
    timeout: float = 10,
    interval: float = 0.15,
):
    """轮询可观察状态，超时后给出具体阶段。"""
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


def open_clipboard() -> None:
    """等待应用释放剪贴板，避免测试与 300ms 轮询竞争。"""
    wait_until(
        "打开剪贴板",
        lambda: _try_open_clipboard(),
        timeout=5,
        interval=0.05,
    )


def _try_open_clipboard() -> bool:
    try:
        wc.OpenClipboard()
        return True
    except Exception:
        return False


def backup_clipboard() -> list[tuple[int, object]]:
    """备份所有可安全重放的当前剪贴板格式。"""
    open_clipboard()
    try:
        items: list[tuple[int, object]] = []
        format_id = 0
        while True:
            format_id = wc.EnumClipboardFormats(format_id)
            if not format_id:
                break
            data = wc.GetClipboardData(format_id)
            if not isinstance(data, (bytes, str, tuple)):
                raise RuntimeError(
                    f"剪贴板格式 {format_id} 的类型 {type(data).__name__} 无法安全恢复"
                )
            items.append((format_id, data))
        return items
    finally:
        wc.CloseClipboard()


def restore_clipboard(items: list[tuple[int, object]]) -> None:
    """逐格式恢复并核对原剪贴板，不保留测试内容。"""
    open_clipboard()
    try:
        wc.EmptyClipboard()
        for format_id, data in items:
            wc.SetClipboardData(format_id, data)
    finally:
        wc.CloseClipboard()

    open_clipboard()
    try:
        for format_id, expected in items:
            actual = wc.GetClipboardData(format_id)
            if actual != expected:
                raise RuntimeError(f"剪贴板格式 {format_id} 恢复后不一致")
    finally:
        wc.CloseClipboard()


def set_clipboard_text(text: str) -> None:
    """写入单一 Unicode 测试文本，模拟真实复制。"""
    open_clipboard()
    try:
        wc.EmptyClipboard()
        wc.SetClipboardData(wc.CF_UNICODETEXT, text)
    finally:
        wc.CloseClipboard()


def read_clipboard_text() -> str:
    """读取当前 Unicode 文本供操作结果断言。"""
    open_clipboard()
    try:
        if not wc.IsClipboardFormatAvailable(wc.CF_UNICODETEXT):
            return ""
        return wc.GetClipboardData(wc.CF_UNICODETEXT)
    finally:
        wc.CloseClipboard()


def monitor_work_areas() -> list[tuple[int, int, int, int]]:
    """读取所有显示器工作区。"""
    return [
        tuple(win32api.GetMonitorInfo(handle)["Work"])
        for handle, _hdc, _rect in win32api.EnumDisplayMonitors()
    ]


def assert_window_on_screen(
    window,
    stage: str,
    *,
    timeout: float = 3,
) -> None:
    """等待原生窗口完成重定位，并要求其完整位于工作区。"""
    bounds: tuple[int, int, int, int] | None = None
    work_areas = monitor_work_areas()

    def is_on_screen() -> bool:
        nonlocal bounds
        rect = window.rectangle()
        bounds = (rect.left, rect.top, rect.right, rect.bottom)
        return any(
            left <= rect.left
            and top <= rect.top
            and rect.right <= right
            and rect.bottom <= bottom
            for left, top, right, bottom in work_areas
        )

    try:
        wait_until(
            f"{stage}窗口进入显示器工作区",
            is_on_screen,
            timeout=timeout,
            interval=0.05,
        )
    except RuntimeError as error:
        raise AssertionError(f"{stage} 窗口越界：{bounds}") from error


def visible_names(window) -> list[str]:
    """读取当前可见 UIA 文本和控件名称。"""
    names: list[str] = []
    for control in window.descendants():
        try:
            if control.is_visible():
                name = control.element_info.name
                if name:
                    names.append(name)
        except Exception:
            continue
    return names


def find_control(window, name: str, control_type: str):
    """查找当前窗口内指定可见控件。"""
    def locate():
        for control in window.descendants(control_type=control_type):
            if control.element_info.name == name and control.is_visible():
                return control
        return None

    try:
        return wait_until(f"控件 {name}/{control_type}", locate)
    except RuntimeError as error:
        candidates = []
        for control in window.descendants():
            try:
                if control.element_info.name == name:
                    candidates.append(
                        {
                            "type": control.element_info.control_type,
                            "visible": control.is_visible(),
                            "rectangle": tuple(control.rectangle()),
                        }
                    )
            except Exception:
                continue
        raise RuntimeError(f"{error}；同名控件：{candidates}") from error


def find_desktop_control(name: str, control_type: str):
    """查找弹出菜单等桌面顶层控件。"""
    desktop = Desktop(backend="uia")

    def locate():
        for top in desktop.windows():
            controls = [top]
            try:
                controls.extend(top.descendants())
            except Exception:
                pass
            for control in controls:
                info = control.element_info
                if info.name == name and info.control_type == control_type:
                    return control
        return None

    return wait_until(f"桌面控件 {name}/{control_type}", locate)


def screenshot(window, mode: str, stage: str) -> Path:
    """保存真实窗口截图并拒绝空图。"""
    path = RESULTS_DIR / f"{mode}-{stage}.png"
    image = window.capture_as_image()
    if image.width < 18 or image.height < 18:
        raise AssertionError(f"{stage} 截图尺寸异常：{image.size}")
    image.save(path)
    return path


def write_isolated_config(mode: str, language: str = DEFAULT_LANGUAGE) -> Path:
    """创建不影响用户配置的确定性验收配置。"""
    local_appdata = RESULTS_DIR / f"state-{mode}"
    config_dir = local_appdata / "PastePeek"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "x": 99999,
        "y": 99999,
        "first_run": False,
        "last_target": "",
        "default_expand": False,
        "default_target": "word",
        "ui_width": 300,
        "usage_tracking_enabled": False,
        "language": language,
    }
    (config_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False),
        encoding="utf-8",
    )
    return local_appdata


def new_pastepeek_window(existing_handles: set[int]):
    """等待本轮新建的 PastePeek 顶层窗口。"""
    desktop = Desktop(backend="uia")

    def locate():
        for window in desktop.windows(title="PastePeek"):
            if window.handle not in existing_handles and window.is_visible():
                return window
        return None

    return wait_until("新的 PastePeek 窗口", locate, timeout=15)


def scaled_pixels(logical_pixels: int, scale: float) -> int:
    """按 Qt/Windows 实测的偶数取整规则换算实际像素。"""
    return round(logical_pixels * scale)


def ensure_expanded(window, *, geometry_scale: float = 1.0) -> None:
    """将 HUD 归一化为展开态。"""
    if window.rectangle().height() > scaled_pixels(100, geometry_scale):
        return
    click_points = (
        (scaled_pixels(150, geometry_scale), scaled_pixels(32, geometry_scale)),
        (scaled_pixels(150, geometry_scale), scaled_pixels(18, geometry_scale)),
    )
    last_error: RuntimeError | None = None
    for point in click_points:
        click_control(window, coords=point)
        try:
            wait_until(
                "HUD 展开",
                lambda: window.rectangle().height() > scaled_pixels(100, geometry_scale),
                timeout=2,
            )
            return
        except RuntimeError as error:
            last_error = error
    if last_error is not None:
        raise last_error


def select_auto_detection(
    window, *, language: str = DEFAULT_LANGUAGE
) -> None:
    """通过真实“更多”菜单恢复自动检测。"""
    ensure_expanded(window)
    click_control(find_control(window, "…", "Button"))
    click_control(
        find_desktop_control(translate("auto_detect", language), "MenuItem")
    )


def find_test_terminal_window():
    """查找标题包含测试标记的可见终端宿主窗口。"""
    for terminal in Desktop(backend="uia").windows():
        try:
            title = terminal.window_text() or terminal.element_info.name
            if TEST_TERMINAL_TITLE in title and terminal.is_visible():
                return terminal
        except Exception:
            continue
    return None


def start_test_terminal():
    """启动并聚焦真实 cmd 窗口，触发终端自动识别。"""
    process = subprocess.Popen(
        ["cmd.exe", "/k", f"title {TEST_TERMINAL_TITLE}"],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    try:
        terminal = wait_until(
            "测试终端窗口",
            find_test_terminal_window,
        )
        terminal.set_focus()
        return process, terminal
    except Exception:
        close_process_tree(process)
        raise


def close_process_tree(process: subprocess.Popen | None) -> None:
    """只清理本轮启动的进程树。"""
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


def hover_and_close(
    window,
    *,
    language: str = DEFAULT_LANGUAGE,
    geometry_scale: float = 1.0,
) -> None:
    """悬停显示关闭按钮并通过真实按钮隐藏 HUD。"""
    rect = window.rectangle()
    move_cursor((rect.left - 20, rect.top - 20))
    time.sleep(0.2)
    moved = move_cursor(
        (
            rect.left + rect.width() // 2,
            rect.top + scaled_pixels(10, geometry_scale),
        )
    )
    if moved:
        click_control(
            find_control(
                window,
                translate("hide_hud_accessible", language),
                "Button",
            )
        )
    else:
        window.close()
    wait_until(
        "PastePeek 窗口隐藏",
        lambda: not win32gui.IsWindowVisible(window.handle),
        timeout=10,
    )


def switch_target_with_keyboard(
    window,
    *,
    start_control_name: str,
    start_visible_name: str,
    key: str,
    expected_visible_name: str,
    attempts: int = 3,
    geometry_scale: float = 1.0,
) -> None:
    """从确定起点发送方向键，处理 Windows 焦点切换竞态。"""
    last_error: RuntimeError | None = None
    for _attempt in range(attempts):
        try:
            ensure_expanded(window, geometry_scale=geometry_scale)
            click_control(find_control(window, start_control_name, "CheckBox"))
            wait_until(
                f"复位到 {start_visible_name}",
                lambda: any(
                    start_visible_name in name for name in visible_names(window)
                ),
                timeout=3,
            )
            window.set_focus()
            wait_until(
                "HUD 获得键盘焦点",
                lambda: win32gui.GetForegroundWindow() == window.handle,
                timeout=2,
                interval=0.05,
            )
            time.sleep(0.15)
            keyboard.send_keys(key)
            wait_until(
                f"键盘切换到{expected_visible_name}",
                lambda: any(
                    expected_visible_name in name
                    for name in visible_names(window)
                ),
                timeout=3,
            )
            return
        except RuntimeError as error:
            last_error = error
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"键盘切换到{expected_visible_name}失败")

def run_scenario(
    mode: str,
    command: list[str],
    *,
    check_auto: bool,
    language: str = DEFAULT_LANGUAGE,
    geometry_scale: float = 1.0,
) -> dict:
    """对单个启动形态执行完整用户工作流。"""
    desktop = Desktop(backend="uia")
    existing = {window.handle for window in desktop.windows(title="PastePeek")}
    if existing:
        raise RuntimeError("测试前已有 PastePeek 窗口，请先关闭")

    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(write_isolated_config(mode, language))
    set_clipboard_text(TEST_URL)
    process: subprocess.Popen | None = None
    terminal_process: subprocess.Popen | None = None
    stages: dict[str, object] = {
        "mode": mode,
        "language": language,
        "geometry_scale": geometry_scale,
        "screens": monitor_work_areas(),
    }

    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            creationflags=subprocess.CREATE_NO_WINDOW,
            env=env,
        )
        window = new_pastepeek_window(existing)
        wait_until(
            "剪贴板文本分析",
            lambda: content_type_label("plain_text", language)
            in visible_names(window),
        )
        assert_window_on_screen(window, "常态")
        stages["collapsed"] = str(screenshot(window, mode, "collapsed"))

        ensure_expanded(window, geometry_scale=geometry_scale)
        assert_window_on_screen(window, "展开态")
        stages["expanded"] = str(screenshot(window, mode, "expanded"))

        switch_target_with_keyboard(
            window,
            start_control_name=target_label("chrome", language, compact=True),
            start_visible_name=target_label("chrome", language),
            key="{RIGHT}",
            expected_visible_name=target_label("code_editor", language),
            geometry_scale=geometry_scale,
        )
        switch_target_with_keyboard(
            window,
            start_control_name=target_label("code_editor", language, compact=True),
            start_visible_name=target_label("code_editor", language),
            key="{LEFT}",
            expected_visible_name=target_label("chrome", language),
            geometry_scale=geometry_scale,
        )

        if check_auto:
            select_auto_detection(window, language=language)
            terminal_process, _terminal = start_test_terminal()
            wait_until(
                "自动识别终端",
                lambda: any(
                    target_label("terminal", language) in name
                    for name in visible_names(window)
                ),
            )
            stages["auto_terminal"] = str(
                screenshot(window, mode, "auto-terminal")
            )
            close_process_tree(terminal_process)
            terminal_process = None

        ensure_expanded(window, geometry_scale=geometry_scale)
        click_control(
            find_control(
                window,
                target_label("chrome", language, compact=True),
                "CheckBox",
            )
        )
        wait_until(
            "操作前切换到浏览器",
            lambda: any(
                target_label("chrome", language) in name
                for name in visible_names(window)
            ),
        )
        find_control(window, translate("action_clean_url", language), "Button")
        window.set_focus()
        keyboard.send_keys("{ENTER}")
        wait_until("Enter 净化链接", lambda: read_clipboard_text() == CLEAN_URL)
        stages["action_result"] = read_clipboard_text()

        window.set_focus()
        keyboard.send_keys("{ESC}")
        wait_until(
            "Escape 折叠",
            lambda: window.rectangle().height() <= scaled_pixels(60, geometry_scale),
        )
        keyboard.send_keys("{ESC}")
        expected_min_width = scaled_pixels(36, geometry_scale)
        expected_min_height = scaled_pixels(18, geometry_scale)
        try:
            wait_until(
                "Escape 最小化",
                lambda: (
                    window.rectangle().width() == expected_min_width
                    and window.rectangle().height() == expected_min_height
                ),
            )
        except RuntimeError as error:
            actual = window.rectangle()
            raise RuntimeError(
                f"{error}；期望 {expected_min_width}×{expected_min_height}，"
                f"实际 {actual.width()}×{actual.height()}"
            ) from error
        assert_window_on_screen(window, "最小态")
        stages["minimized"] = str(screenshot(window, mode, "minimized"))

        click_control(
            window,
            coords=(expected_min_width // 2, expected_min_height // 2),
        )
        expected_restored_width = scaled_pixels(300, geometry_scale)
        try:
            wait_until(
                "点击恢复",
                lambda: window.rectangle().width() == expected_restored_width,
            )
        except RuntimeError as error:
            actual = window.rectangle()
            raise RuntimeError(
                f"{error}；期望宽度 {expected_restored_width}，"
                f"实际 {actual.width()}×{actual.height()}"
            ) from error
        assert_window_on_screen(window, "恢复态")
        stages["restored"] = str(screenshot(window, mode, "restored"))

        hover_and_close(
            window,
            language=language,
            geometry_scale=geometry_scale,
        )
        if process.poll() is not None:
            raise AssertionError("隐藏 HUD 后应用进程不应退出")
        stages["hidden_to_tray"] = True
        stages["input_mode"] = gui_input_mode()
        if fallback_reason := gui_input_fallback_reason():
            stages["input_fallback_reason"] = fallback_reason
        return stages
    finally:
        close_process_tree(terminal_process)
        close_process_tree(process)


def main() -> None:
    """执行两种启动形态并在任何失败下恢复剪贴板。"""
    reset_gui_input()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    clipboard_backup = backup_clipboard()
    results: dict[str, object] = {
        "clipboard_formats": [format_id for format_id, _data in clipboard_backup],
    }
    try:
        results["source"] = run_scenario(
            "source",
            [sys.executable, str(ROOT / "src" / "main.py")],
            check_auto=True,
        )
        results["exe"] = run_scenario(
            "exe",
            [str(ROOT / "dist" / "PastePeek.exe")],
            check_auto=True,
        )
        results["source_en"] = run_scenario(
            "source-en",
            [sys.executable, str(ROOT / "src" / "main.py")],
            check_auto=True,
            language="en-US",
        )
        results["exe_en"] = run_scenario(
            "exe-en",
            [str(ROOT / "dist" / "PastePeek.exe")],
            check_auto=True,
            language="en-US",
        )
        results["passed"] = True
    finally:
        restore_clipboard(clipboard_backup)
        results["clipboard_restored"] = True
        (RESULTS_DIR / "results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
