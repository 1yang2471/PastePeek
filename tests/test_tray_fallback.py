"""系统托盘不可用时的退出行为测试。"""

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
from PySide6.QtWidgets import QApplication, QPushButton

from src.ui.hud_window import HudWindow
from src.ui.tray_controller import TrayController


@pytest.fixture(scope="module")
def qapp():
    """提供唯一的 Qt 应用实例。"""
    app = QApplication.instance() or QApplication([])
    yield app


def test_hud_close_requests_exit_when_system_tray_is_unavailable(qapp):
    """没有托盘时关闭 HUD 必须允许应用完整退出。"""
    hud = HudWindow()
    hud.show()
    controller = TrayController(hud, QIcon(), tray_available=False)
    exit_requests: list[bool] = []
    controller.exit_requested.connect(lambda: exit_requests.append(True))
    controller.start()
    close_button = next(
        button
        for button in hud.findChildren(QPushButton)
        if button.objectName() == "HideButton"
    )

    close_button.click()
    qapp.processEvents()

    assert exit_requests == [True]

    controller.stop()
    hud.close()
