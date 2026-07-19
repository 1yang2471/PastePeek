"""前台窗口钩子的启动与清理契约测试。"""

from src.listener.window_hook import WindowFocusMonitor


class FakeWin32Api:
    """记录钩子注册和清理调用的 Win32 测试边界。"""

    def __init__(self, hook: int) -> None:
        self.hook = hook
        self.set_calls = 0
        self.unhooked: list[int] = []

    def SetWinEventHook(self, *_args) -> int:
        self.set_calls += 1
        return self.hook

    def UnhookWinEvent(self, hook: int) -> None:
        self.unhooked.append(hook)


def test_start_returns_false_when_windows_rejects_hook():
    api = FakeWin32Api(hook=0)
    monitor = WindowFocusMonitor(win32_api=api)

    assert monitor.start() is False


def test_start_returns_true_when_hook_is_registered():
    api = FakeWin32Api(hook=41)
    monitor = WindowFocusMonitor(win32_api=api)

    assert monitor.start() is True


def test_start_is_idempotent_after_success():
    api = FakeWin32Api(hook=41)
    monitor = WindowFocusMonitor(win32_api=api)

    assert monitor.start() is True
    assert monitor.start() is True
    assert api.set_calls == 1


def test_stop_cleans_hook_once_and_allows_restart():
    api = FakeWin32Api(hook=41)
    monitor = WindowFocusMonitor(win32_api=api)

    assert monitor.start() is True
    monitor.stop()
    monitor.stop()

    assert api.unhooked == [41]
    assert monitor.start() is True
    assert api.set_calls == 2
