"""后台启动时托盘菜单文案测试。"""

import os
import site

import pytest


def _system_pyside_platforms() -> str | None:
    """定位系统 PySide6 的 Qt 平台插件。"""
    for base in site.getsitepackages() + [site.getusersitepackages()]:
        platforms = os.path.join(base, "PySide6", "plugins", "platforms")
        if os.path.isdir(platforms):
            return platforms
    return None


if platforms := _system_pyside_platforms():
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", platforms)

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from src.ui.hud_window import HudWindow
from src.ui.tray_controller import TrayController


@pytest.fixture(scope="module")
def qapp():
    """提供唯一的 Qt 应用实例。"""
    app = QApplication.instance() or QApplication([])
    yield app


def test_background_launch_menu_offers_to_show_hidden_hud(qapp):
    """HUD 初始隐藏时，托盘菜单应描述下一步为显示。"""
    hud = HudWindow()
    hud.show_at_bottom_right(visible=False)
    controller = TrayController(hud, QIcon(), tray_available=True)

    controller.start()
    qapp.processEvents()
    tray = controller.findChild(QSystemTrayIcon)
    toggle_action = tray.contextMenu().actions()[0]

    assert toggle_action.text() == "显示 PastePeek"

    controller.stop()
    hud.close()
