"""后台启动但系统托盘不可用时的可见性回退测试。"""

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
from PySide6.QtWidgets import QApplication

from src.ui.hud_window import HudWindow
from src.ui.tray_controller import TrayController


@pytest.fixture(scope="module")
def qapp():
    """提供唯一的 Qt 应用实例。"""
    app = QApplication.instance() or QApplication([])
    yield app


def test_background_launch_shows_hud_when_system_tray_is_unavailable(qapp):
    """没有托盘时后台模式必须退回可见 HUD。"""
    hud = HudWindow()
    hud.show_at_bottom_right(visible=False)
    controller = TrayController(hud, QIcon(), tray_available=False)

    controller.start()
    qapp.processEvents()

    assert hud.isVisible()

    controller.stop()
    hud.close()
