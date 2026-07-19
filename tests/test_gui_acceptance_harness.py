"""Windows GUI 验收工具自身的进程与窗口识别契约。"""

import sys
from types import ModuleType, SimpleNamespace

import pytest

try:
    import pywinauto  # noqa: F401
except ModuleNotFoundError:
    pywinauto = ModuleType("pywinauto")
    pywinauto.Desktop = None
    pywinauto.keyboard = SimpleNamespace()
    pywinauto.mouse = SimpleNamespace()
    sys.modules["pywinauto"] = pywinauto

from scripts import accept_gui_windows


@pytest.fixture(autouse=True)
def reset_gui_input_mode():
    """每个用例从真实输入模式开始，避免回退状态串扰。"""
    accept_gui_windows.reset_gui_input()
    yield
    accept_gui_windows.reset_gui_input()


class FakeProcess:
    """只表示成功创建的测试终端进程。"""

    pid = 12345


class FakeWindow:
    """模拟 Windows Terminal 为标签标题附加宿主名称。"""

    def window_text(self):
        return "管理员: PastePeek QA Terminal - Windows Terminal"

    def is_visible(self):
        return True


class FakeDesktop:
    def __init__(self, window):
        self.window = window

    def windows(self):
        return [self.window]


def test_test_terminal_title_allows_host_prefix_and_suffix(monkeypatch):
    """终端宿主附加标题时仍应定位本轮测试窗口。"""
    window = FakeWindow()
    monkeypatch.setattr(
        accept_gui_windows,
        "Desktop",
        lambda backend: FakeDesktop(window),
    )

    assert accept_gui_windows.find_test_terminal_window() is window


def test_test_terminal_start_failure_cleans_created_process(monkeypatch):
    """终端窗口等待失败时不得遗留刚创建的 cmd 进程树。"""
    process = FakeProcess()
    cleaned = []
    monkeypatch.setattr(
        accept_gui_windows.subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )

    def fail_wait(*_args, **_kwargs):
        raise RuntimeError("等待失败")

    monkeypatch.setattr(accept_gui_windows, "wait_until", fail_wait)
    monkeypatch.setattr(
        accept_gui_windows,
        "close_process_tree",
        cleaned.append,
    )

    with pytest.raises(RuntimeError, match="等待失败"):
        accept_gui_windows.start_test_terminal()

    assert cleaned == [process]


@pytest.mark.parametrize(
    ("logical_pixels", "scale", "expected"),
    [
        (36, 1.0, 36),
        (36, 1.25, 45),
        (18, 1.25, 22),
        (300, 1.5, 450),
        (300, 2.0, 600),
    ],
)
def test_scaled_pixels_uses_observed_qt_windows_rounding(
    logical_pixels,
    scale,
    expected,
):
    """Qt 逻辑尺寸应按实际平台在半像素处取最近偶数。"""
    assert accept_gui_windows.scaled_pixels(logical_pixels, scale) == expected


def test_ensure_expanded_scales_click_coordinates(monkeypatch):
    """200% 缩放下展开点击应落在 HUD 的逻辑中心。"""
    class Rectangle:
        def __init__(self, height):
            self._height = height

        def height(self):
            return self._height

    class Window:
        def __init__(self):
            self.expanded = False
            self.clicks = []

        def rectangle(self):
            return Rectangle(300 if self.expanded else 72)

        def click_input(self, *, coords):
            self.clicks.append(coords)
            self.expanded = True

    window = Window()
    monkeypatch.setattr(
        accept_gui_windows,
        "wait_until",
        lambda _description, predicate, **_kwargs: predicate(),
    )

    accept_gui_windows.ensure_expanded(window, geometry_scale=2.0)

    assert window.clicks == [(300, 64)]


def test_window_boundary_check_waits_for_native_reposition(monkeypatch):
    """EXE 原生窗口短暂越界后归位时，验收不应提前误判失败。"""
    class Rectangle:
        left = 1603
        right = 1903

        def __init__(self, top, bottom):
            self.top = top
            self.bottom = bottom

    class Window:
        def __init__(self):
            self.measurements = 0

        def rectangle(self):
            self.measurements += 1
            if self.measurements == 1:
                return Rectangle(745, 1053)
            return Rectangle(708, 1016)

    window = Window()
    monkeypatch.setattr(
        accept_gui_windows,
        "monitor_work_areas",
        lambda: [(0, 0, 1920, 1032)],
    )

    accept_gui_windows.assert_window_on_screen(window, "展开态", timeout=0.1)

    assert window.measurements >= 2


def test_click_falls_back_only_when_windows_cursor_is_unavailable():
    """SetCursorPos 不可用时应回退到不移动鼠标的控件调用。"""
    class CursorUnavailableError(Exception):
        winerror = 2

        def __str__(self):
            return "SetCursorPos: 系统找不到指定的文件"

    class Control:
        def __init__(self):
            self.fallback_clicks = []

        def click_input(self, *, coords):
            raise CursorUnavailableError()

        def click(self, *, coords):
            self.fallback_clicks.append(coords)

    control = Control()

    accept_gui_windows.click_control(control, coords=(12, 34))

    assert control.fallback_clicks == [(12, 34)]
    assert accept_gui_windows.gui_input_mode() == "uia-fallback"


def test_click_does_not_hide_unrelated_input_failures():
    """非鼠标会话错误必须直接失败，不能降低验收强度。"""
    class Control:
        def click_input(self):
            raise RuntimeError("控件已失效")

        def click(self):
            raise AssertionError("不应回退")

    with pytest.raises(RuntimeError, match="控件已失效"):
        accept_gui_windows.click_control(Control())
