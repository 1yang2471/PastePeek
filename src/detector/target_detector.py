"""TargetDetector — detect which app the user is pasting into.

Uses win32gui to read the foreground window class name,
then maps it to a standardized target key via _map_classname.

Design: extract method for testability. get_active_target() calls
win32gui (not unit-testable), but _map_classname is pure logic.
"""

import ctypes
import os
from ctypes import wintypes
from pathlib import Path

# ── Win32 API ────────────────────────────────────────────────────────
_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
]
_kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

# ── Class name → target mapping ──────────────────────────────────────
# Each target may match multiple class names (case-insensitive).

_CLASS_TO_TARGET: dict[str, str] = {
    # ── Documents ──
    "opusapp":              "word",
    "winword":              "word",
    "xlmain":               "spreadsheet",
    "et_wnd":               "spreadsheet",   # WPS Spreadsheet
    "pptframeclass":        "presentation",  # PowerPoint
    "wpp_frame":            "presentation",  # WPS Presentation

    # ── Browsers ──
    "chrome_widgetwin_1":   "chrome",

    # ── Code Editors ──
    "vscode":               "code_editor",
    "vim":                  "code_editor",

    # ── Terminals ──
    "putty":                "terminal",
    "consolewindowclass":   "terminal",
    "mintty":               "terminal",
    "conemu":               "terminal",

    # ── Chat Apps ──
    "ct_app":               "chat_app",      # 企业微信
    "wechat_main_wnd":      "chat_app",      # 微信

    # ── Markdown Editors ──
    "typora":               "markdown_editor",
    "obsidian":             "markdown_editor",
}

# Chromium 与 Electron 应用经常共享窗口类名，必须优先依据进程名消歧。
_PROCESS_TO_TARGET: dict[str, str] = {
    # 浏览器
    "chrome.exe": "chrome",
    "msedge.exe": "chrome",
    "firefox.exe": "chrome",

    # 文档办公
    "winword.exe": "word",
    "wps.exe": "word",
    "excel.exe": "spreadsheet",
    "et.exe": "spreadsheet",
    "powerpnt.exe": "presentation",
    "wpp.exe": "presentation",

    # 代码编辑器
    "code.exe": "code_editor",
    "cursor.exe": "code_editor",
    "devenv.exe": "code_editor",
    "pycharm64.exe": "code_editor",
    "idea64.exe": "code_editor",
    "sublime_text.exe": "code_editor",
    "notepad++.exe": "code_editor",

    # 终端
    "windowsterminal.exe": "terminal",
    "wt.exe": "terminal",
    "cmd.exe": "terminal",
    "powershell.exe": "terminal",
    "pwsh.exe": "terminal",
    "putty.exe": "terminal",

    # 通讯
    "wechat.exe": "chat_app",
    "weixin.exe": "chat_app",
    "wxwork.exe": "chat_app",
    "ms-teams.exe": "chat_app",
    "teams.exe": "chat_app",
    "slack.exe": "chat_app",
    "discord.exe": "chat_app",

    # Markdown 编辑器
    "typora.exe": "markdown_editor",
    "obsidian.exe": "markdown_editor",
    "marktext.exe": "markdown_editor",
}


class TargetDetector:
    """Detect the active application to predict paste destination."""

    @staticmethod
    def get_active_target() -> str:
        """识别当前前台窗口对应的粘贴目标。"""
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return "unknown"
        return TargetDetector.get_target_for_window(hwnd)

    @staticmethod
    def _map_classname(class_name: str | None) -> str:
        """Map a Win32 window class name to a standardized target key.

        Case-insensitive. Returns 'unknown' for unmapped class names.
        """
        if not class_name:
            return "unknown"
        key = class_name.strip().lower()
        return _CLASS_TO_TARGET.get(key, "unknown")

    @staticmethod
    def _read_window_details(hwnd: int) -> tuple[str, str, str]:
        """从 Win32 句柄读取进程名、窗口类名和标题。"""
        class_buf = ctypes.create_unicode_buffer(256)
        _user32.GetClassNameW(hwnd, class_buf, len(class_buf))

        title_length = max(0, _user32.GetWindowTextLengthW(hwnd))
        title_buf = ctypes.create_unicode_buffer(title_length + 1)
        if title_length:
            _user32.GetWindowTextW(hwnd, title_buf, len(title_buf))

        process_id = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        process_name = ""
        if process_id.value:
            handle = _kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION,
                False,
                process_id.value,
            )
            if handle:
                try:
                    path_buf = ctypes.create_unicode_buffer(32768)
                    path_size = wintypes.DWORD(len(path_buf))
                    if _kernel32.QueryFullProcessImageNameW(
                        handle, 0, path_buf, ctypes.byref(path_size)
                    ):
                        process_name = os.path.basename(path_buf.value)
                finally:
                    _kernel32.CloseHandle(handle)

        return process_name, class_buf.value or "", title_buf.value or ""

    @staticmethod
    def get_target_for_window(hwnd: int) -> str:
        """识别指定窗口句柄对应的粘贴目标。"""
        if not hwnd:
            return "unknown"
        try:
            process_name, class_name, title = TargetDetector._read_window_details(hwnd)
        except (OSError, ValueError):
            return "unknown"
        return TargetDetector.classify_window(process_name, class_name, title)

    @staticmethod
    def classify_window(
        process_name: str | None,
        class_name: str | None,
        title: str = "",
    ) -> str:
        """依据进程名和窗口类名识别目标应用。"""
        process_key = Path(process_name or "").name.lower()
        if process_key in _PROCESS_TO_TARGET:
            return _PROCESS_TO_TARGET[process_key]
        return TargetDetector._map_classname(class_name)
