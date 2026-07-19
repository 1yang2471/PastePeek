"""GUI 验收快捷键焦点竞态的重试契约。"""

import sys
from types import ModuleType, SimpleNamespace

try:
    import pywinauto  # noqa: F401
except ModuleNotFoundError:
    pywinauto = ModuleType("pywinauto")
    pywinauto.Desktop = None
    pywinauto.keyboard = SimpleNamespace()
    pywinauto.mouse = SimpleNamespace()
    sys.modules["pywinauto"] = pywinauto

from scripts import accept_gui_windows


class FakeControl:
    def __init__(self):
        self.clicks = 0

    def click_input(self):
        self.clicks += 1


class FakeWindow:
    handle = 123

    def __init__(self):
        self.focuses = 0

    def set_focus(self):
        self.focuses += 1


def test_keyboard_target_switch_retries_from_known_start(monkeypatch):
    """首次焦点竞态超时时，应重置起点后只再发送一次按键。"""
    control = FakeControl()
    window = FakeWindow()
    sent = []
    expanded = []
    expected_waits = 0

    monkeypatch.setattr(
        accept_gui_windows,
        "find_control",
        lambda *_args: control,
    )

    def fake_wait(description, _predicate, **_kwargs):
        nonlocal expected_waits
        if description == "键盘切换到代码编辑器":
            expected_waits += 1
            if expected_waits == 1:
                raise RuntimeError("首次焦点未生效")
        return True

    monkeypatch.setattr(accept_gui_windows, "wait_until", fake_wait)
    monkeypatch.setattr(
        accept_gui_windows.keyboard,
        "send_keys",
        sent.append,
        raising=False,
    )
    monkeypatch.setattr(
        accept_gui_windows,
        "ensure_expanded",
        lambda *_args, **_kwargs: expanded.append(True),
    )

    accept_gui_windows.switch_target_with_keyboard(
        window,
        start_control_name="浏览器",
        start_visible_name="Chrome",
        key="{RIGHT}",
        expected_visible_name="代码编辑器",
    )

    assert control.clicks == 2
    assert window.focuses == 2
    assert sent == ["{RIGHT}", "{RIGHT}"]
    assert expanded == [True, True]
