"""WindowFocusMonitor — real-time foreground window change detection.

Uses Win32 SetWinEventHook to listen for EVENT_SYSTEM_FOREGROUND.
Emits a Qt Signal with the new target key on every switch.

Design:
  - Hook registered on PySide6 main thread (has message pump).
  - Callback runs on system hook thread → Signal.emit() (thread-safe).
  - Class name → target mapping delegated to TargetDetector._map_classname.
  - No new dependencies (ctypes only, already in TargetDetector).

Performance: callback fires only on actual foreground change (<1ms).
"""

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal

from src.detector.target_detector import TargetDetector

# ── Win32 constants ───────────────────────────────────────────────────
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT  = 0x0000

_user32 = ctypes.windll.user32

# WinEvent callback type: 7 args, returns void
_WinEventProc = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,   # hWinEventHook
    wintypes.DWORD,    # event
    wintypes.HWND,     # hwnd
    wintypes.LONG,     # idObject
    wintypes.LONG,     # idChild
    wintypes.DWORD,    # dwEventThread
    wintypes.DWORD,    # dwmsEventTime
)


class WindowFocusMonitor(QObject):
    """Monitor foreground window changes via WinEvent hook.

    Usage:
        monitor = WindowFocusMonitor()
        monitor.target_changed.connect(on_target_switched)
        monitor.start()
        ...
        monitor.stop()

    Signal: target_changed(str) — emits standardized target key
            on every foreground window switch.
    """

    target_changed = Signal(str)

    def __init__(self, parent: QObject | None = None, *, win32_api=None):
        super().__init__(parent)
        self._hook: int | None = None
        self._proc: _WinEventProc | None = None
        self._win32_api = win32_api if win32_api is not None else _user32
        self._detector = TargetDetector()

    # ── Public API ─────────────────────────────────────────────────

    def start(self) -> bool:
        """注册前台窗口钩子；系统拒绝时返回假并允许主功能继续。"""
        if self._hook is not None:
            return True

        @_WinEventProc
        def _callback(
            hWinEventHook: wintypes.HANDLE,
            event: wintypes.DWORD,
            hwnd: wintypes.HWND,
            idObject: wintypes.LONG,
            idChild: wintypes.LONG,
            dwEventThread: wintypes.DWORD,
            dwmsEventTime: wintypes.DWORD,
        ) -> None:
            # Runs on system hook thread — Signal.emit() is thread-safe in PySide6
            if not hwnd:
                return
            target = TargetDetector.get_target_for_window(hwnd)
            # emit() is reentrant-safe, PySide6 queues it to receiver's thread
            self.target_changed.emit(target)

        self._proc = _callback  # prevent GC
        self._hook = self._win32_api.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_SYSTEM_FOREGROUND,
            0,                   # hmodWinEventProc (NULL = current process)
            self._proc,
            0,                   # idProcess (0 = all processes)
            0,                   # idThread  (0 = all threads)
            WINEVENT_OUTOFCONTEXT,
        )
        if not self._hook:
            self._hook = None
            self._proc = None
            return False
        return True

    def stop(self) -> None:
        """Unregister hook. Idempotent."""
        if self._hook is not None:
            self._win32_api.UnhookWinEvent(self._hook)
            self._hook = None
        self._proc = None

    def __del__(self):
        self.stop()
