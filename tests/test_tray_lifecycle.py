"""系统托盘生命周期的用户行为测试。"""

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
from PySide6.QtWidgets import QApplication, QPushButton, QSystemTrayIcon

from src.startup import StartupManager
from src.ui.hud_window import HudWindow
from src.ui.tray_controller import TrayController


class MemoryRunRegistry:
    """只替代注册表系统边界。"""

    def __init__(self) -> None:
        self.command: str | None = None

    def read(self) -> str | None:
        return self.command

    def write(self, command: str) -> None:
        self.command = command

    def delete(self) -> None:
        self.command = None


class UnreadableRunRegistry(MemoryRunRegistry):
    """模拟被系统策略拒绝读取的注册表。"""

    def read(self) -> str | None:
        raise PermissionError("拒绝访问")


@pytest.fixture(scope="module")
def qapp():
    """提供唯一的 Qt 应用实例。"""
    app = QApplication.instance() or QApplication([])
    yield app


def test_user_can_toggle_hud_from_tray(qapp):
    """托盘入口应在显示和隐藏 HUD 之间切换。"""
    hud = HudWindow()
    hud.show()
    controller = TrayController(hud, QIcon(), tray_available=True)
    controller.start()
    qapp.processEvents()

    controller.toggle_hud()
    qapp.processEvents()
    assert not hud.isVisible()

    controller.toggle_hud()
    qapp.processEvents()
    assert hud.isVisible()

    controller.stop()
    hud.close()


def test_hud_close_button_hides_window_when_tray_is_available(qapp):
    """托盘可用时，HUD 的关闭按钮只隐藏界面。"""
    hud = HudWindow()
    hud.show()
    controller = TrayController(hud, QIcon(), tray_available=True)
    controller.start()
    close_button = next(
        button
        for button in hud.findChildren(QPushButton)
        if button.objectName() == "HideButton"
    )

    close_button.click()
    qapp.processEvents()

    assert not hud.isVisible()

    controller.stop()
    hud.close()


def test_exit_menu_requests_application_shutdown(qapp):
    """托盘退出命令应交给应用生命周期执行。"""
    hud = HudWindow()
    controller = TrayController(hud, QIcon(), tray_available=True)
    requested: list[bool] = []
    controller.exit_requested.connect(lambda: requested.append(True))
    controller.start()
    tray = controller.findChild(QSystemTrayIcon)
    exit_action = next(
        action for action in tray.contextMenu().actions() if action.text() == "退出 PastePeek"
    )

    exit_action.trigger()

    assert requested == [True]

    controller.stop()
    hud.close()


def test_clicking_tray_icon_toggles_hud(qapp):
    """单击托盘图标应切换 HUD，而右键菜单不能误触发。"""
    hud = HudWindow()
    hud.show()
    controller = TrayController(hud, QIcon(), tray_available=True)
    controller.start()
    tray = controller.findChild(QSystemTrayIcon)

    tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    qapp.processEvents()

    assert not hud.isVisible()

    controller.stop()
    hud.close()


def test_showing_hud_from_tray_restores_minimized_window(qapp):
    """从托盘显示 HUD 时应恢复完整常态尺寸。"""
    hud = HudWindow()
    hud.show()
    controller = TrayController(hud, QIcon(), tray_available=True)
    controller.start()
    minimize_button = next(
        button
        for button in hud.findChildren(QPushButton)
        if button.objectName() == "MinimizeButton"
    )
    minimize_button.click()
    qapp.processEvents()
    minimized_size = hud.size()

    controller.toggle_hud()
    controller.toggle_hud()
    qapp.processEvents()

    assert hud.isVisible()
    assert hud.width() > minimized_size.width()
    assert hud.height() > minimized_size.height()

    controller.stop()
    hud.close()


def test_activation_request_always_shows_hud(qapp):
    """重复启动的激活请求只能显示 HUD，不能切换成隐藏。"""
    hud = HudWindow()
    hud.show()
    controller = TrayController(hud, QIcon(), tray_available=True)
    controller.start()

    controller.show_hud()
    qapp.processEvents()
    assert hud.isVisible()

    hud.hide()
    controller.show_hud()
    qapp.processEvents()
    assert hud.isVisible()

    controller.stop()
    hud.close()


def test_startup_menu_toggles_real_startup_state(qapp, tmp_path):
    """托盘开关应启用和禁用当前便携 EXE 的开机启动。"""
    executable = tmp_path / "PastePeek.exe"
    executable.touch()
    registry = MemoryRunRegistry()
    startup = StartupManager(executable, frozen=True, registry=registry)
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
    assert startup_action.isChecked()
    assert startup.is_enabled()

    startup_action.trigger()
    assert not startup_action.isChecked()
    assert not startup.is_enabled()

    controller.stop()
    hud.close()


def test_startup_menu_refreshes_external_state_when_opened(qapp, tmp_path):
    """再次打开托盘菜单时，应显示当前开机启动真实状态。"""
    executable = tmp_path / "PastePeek.exe"
    executable.touch()
    registry = MemoryRunRegistry()
    startup = StartupManager(executable, frozen=True, registry=registry)
    hud = HudWindow()
    controller = TrayController(
        hud,
        QIcon(),
        tray_available=True,
        startup_manager=startup,
    )
    controller.start()
    tray = controller.findChild(QSystemTrayIcon)
    menu = tray.contextMenu()
    startup_action = next(
        action for action in menu.actions() if action.text() == "开机启动"
    )
    assert not startup_action.isChecked()

    startup.set_enabled(True)
    menu.aboutToShow.emit()
    assert startup_action.isChecked()

    startup.set_enabled(False)
    menu.aboutToShow.emit()
    assert not startup_action.isChecked()

    controller.stop()
    hud.close()


def test_background_launch_prepares_hud_without_showing_it(qapp):
    """登录启动不能闪现 HUD，但托盘仍可在之后正常显示它。"""
    hud = HudWindow()
    hud.show_at_bottom_right(visible=False)
    controller = TrayController(hud, QIcon(), tray_available=True)
    controller.start()
    qapp.processEvents()

    assert not hud.isVisible()

    controller.show_hud()
    qapp.processEvents()
    assert hud.isVisible()

    controller.stop()
    hud.close()


def test_registry_read_failure_does_not_prevent_tray_start(qapp, tmp_path):
    """读取启动项失败时应用仍应提供可用托盘。"""
    executable = tmp_path / "PastePeek.exe"
    executable.touch()
    startup = StartupManager(
        executable,
        frozen=True,
        registry=UnreadableRunRegistry(),
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
    assert not startup_action.isChecked()

    controller.stop()
    hud.close()
