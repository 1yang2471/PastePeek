"""托盘开机启动写入失败时的回滚测试。"""

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

from src.startup import StartupManager
from src.ui.hud_window import HudWindow
from src.ui.tray_controller import TrayController


class RejectingRunRegistry:
    """模拟被系统策略拒绝写入的注册表。"""

    def read(self) -> str | None:
        return None

    def write(self, command: str) -> None:
        raise PermissionError("拒绝访问")

    def delete(self) -> None:
        return


@pytest.fixture(scope="module")
def qapp():
    """提供唯一的 Qt 应用实例。"""
    app = QApplication.instance() or QApplication([])
    yield app


def test_failed_startup_write_rolls_back_checked_state(qapp, tmp_path):
    """注册失败后菜单必须恢复为未启用。"""
    executable = tmp_path / "PastePeek.exe"
    executable.touch()
    startup = StartupManager(
        executable,
        frozen=True,
        registry=RejectingRunRegistry(),
    )
    hud = HudWindow()
    controller = TrayController(
        hud,
        QIcon(),
        tray_available=True,
        startup_manager=startup,
    )
    controller.start()
    tray = controller.findChild(QSystemTrayIcon)
    startup_action = next(
        action for action in tray.contextMenu().actions() if action.text() == "开机启动"
    )

    startup_action.trigger()
    qapp.processEvents()

    assert not startup_action.isChecked()
    assert not startup.is_enabled()

    controller.stop()
    hud.close()
