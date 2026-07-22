"""PastePeek - persistent clipboard status monitor (HUD mode).

Entry point. Launches a non-intrusive floating HUD in the bottom-right
corner of the screen. Auto-updates on clipboard change. Never steals focus.

Works both as `python src/main.py` and as a PyInstaller --onefile bundle.
"""

import sys
from pathlib import Path

# Ensure project root on sys.path (after pip-installed packages)
_bundle_dir = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
if str(_bundle_dir) not in sys.path:
    sys.path.insert(0, str(_bundle_dir))

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.launch_options import parse_launch_options
from src.single_instance import SingleInstanceGuard
from src.startup import StartupManager, WindowsRunRegistry
from src.ui.app import PastePeekApp
from src.ui.hud_window import HudWindow
from src.ui.tray_controller import TrayController
from src.usage.tracker import UsageTracker


def _handle_action(app, hud, action_type: str):
    """Execute action and show success/error toast."""
    ok, msg = app.on_action_triggered(action_type)
    if ok:
        hud.show_success_toast()
    else:
        hud.show_error(msg)


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    options = parse_launch_options(sys.argv)
    app = QApplication(options.qt_arguments)
    app.setApplicationName("PastePeek")
    app.setQuitOnLastWindowClosed(False)
    app_icon = QIcon(str(_bundle_dir / "assets" / "icon.ico"))
    app.setWindowIcon(app_icon)

    instance = SingleInstanceGuard()
    if not instance.acquire(activate_existing=not options.background):
        sys.exit(0)

    # Create usage tracker (zero-interaction JSONL logger)
    tracker = UsageTracker()

    # Create persistent HUD — always visible, never steals focus
    hud = HudWindow(tracker=tracker)
    hud.show_at_bottom_right(visible=not options.background)

    # App、HUD 和托盘共享 HUD 从本地配置加载的语言；默认仍为简体中文。
    paste_peek = PastePeekApp(default_target=hud.default_target())
    paste_peek.set_language(hud.language())
    # 空字符串保留自动检测，非空值恢复上次手动场景。
    paste_peek.set_manual_target(hud.preferred_target())

    # 托盘接管 HUD 显隐；只有显式退出才结束后台监听。
    startup = StartupManager(
        Path(sys.executable),
        frozen=bool(getattr(sys, "frozen", False)),
        registry=WindowsRunRegistry(),
    )
    tray = TrayController(
        hud,
        app_icon,
        startup_manager=startup,
        language=hud.language(),
    )
    tray.exit_requested.connect(app.quit)
    tray.language_selected.connect(hud.set_language)
    hud.language_changed.connect(paste_peek.set_language)
    hud.language_changed.connect(tray.set_language)
    tray.start()
    instance.activation_requested.connect(tray.show_hud)

    # Connect: clipboard change → HUD update
    paste_peek.analysis_ready.connect(hud.update_result)
    # Connect: HUD target menu → manual override
    hud.target_override_requested.connect(paste_peek.set_manual_target)
    # Connect: HUD action button → tool execution + refresh
    hud.action_triggered.connect(lambda action: _handle_action(paste_peek, hud, action))

    # Start monitoring
    paste_peek.start()

    exit_code = app.exec()
    tray.stop()
    paste_peek.stop()
    tracker.close()
    instance.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
