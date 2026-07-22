"""系统托盘运行时语言切换测试。"""

import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon

from src.ui.hud_window import HudWindow
from src.ui.tray_controller import TrayController


class _MessageTray:
    """收集托盘通知，避免依赖真实系统托盘。"""

    def __init__(self):
        self.messages: list[tuple[object, ...]] = []

    def showMessage(self, *args):
        self.messages.append(args)


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])

def test_tray_language_switch_updates_existing_menu(qapp):
    hud = HudWindow()
    hud.show()
    controller = TrayController(hud, QIcon(), tray_available=True)
    controller.start()

    tray = controller.findChild(QSystemTrayIcon)
    menu = tray.contextMenu()
    exit_action = next(action for action in menu.actions() if "PastePeek" in action.text() and "退出" in action.text())
    controller.set_language("en-US")

    labels = [action.text() for action in menu.actions() if not action.isSeparator()]
    assert "Exit PastePeek" in labels
    assert "启动 PastePeek" not in labels
    assert exit_action.text() == "Exit PastePeek"

    controller.stop()
    hud.close()


def test_tray_language_menu_updates_check_state_and_emits_selection(qapp):
    hud = HudWindow()
    controller = TrayController(hud, QIcon(), tray_available=True)
    selected: list[str] = []
    controller.language_selected.connect(selected.append)
    controller.start()

    menu = controller.findChild(QSystemTrayIcon).contextMenu()
    language_action = next(action for action in menu.actions() if action.text() == "语言")
    language_menu = language_action.menu()
    assert language_menu.title() == "语言"
    assert language_menu.actions()[0].text() == "简体中文"
    assert language_menu.actions()[0].isChecked()

    controller.set_language("en-US")
    assert language_menu.title() == "Language"
    assert language_menu.actions()[0].text() == "Simplified Chinese"
    assert language_menu.actions()[1].text() == "English"
    assert language_menu.actions()[1].isChecked()

    language_menu.actions()[0].trigger()
    assert selected == ["zh-CN"]
    assert controller.language() == "zh-CN"

    controller.stop()
    hud.close()


def test_english_startup_error_does_not_embed_system_language(qapp):
    """英文托盘不能把中文系统错误拼进产品文案。"""
    hud = HudWindow()
    controller = TrayController(hud, QIcon(), language="en-US")
    message_tray = _MessageTray()
    controller._tray = message_tray

    controller._show_startup_error(PermissionError("拒绝访问"))

    assert message_tray.messages[0][1] == "Failed to update startup setting"
    hud.close()
