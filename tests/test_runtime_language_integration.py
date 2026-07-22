"""运行时语言切换的 HUD、预测器、托盘联动测试。"""

from __future__ import annotations

import json

import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from src.clipboard.listener import ClipboardData
from src.ui import hud_window
from src.ui.app import PastePeekApp
from src.ui.hud_window import HudWindow
from src.ui.tray_controller import TrayController


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))
    return config_path


class _Listener:
    def __init__(self, data: ClipboardData):
        self._data = data

    def read(self) -> ClipboardData:
        return self._data


class _Target:
    def get_active_target(self) -> str:
        return "terminal"


def _language_menu(controller: TrayController) -> object:
    tray = controller.findChild(QSystemTrayIcon)
    assert tray is not None
    menu = tray.contextMenu()
    assert menu is not None
    action = next(action for action in menu.actions() if action.text() == "语言")
    language_menu = action.menu()
    assert language_menu is not None
    return language_menu


def _contains_chinese(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def test_tray_language_selection_updates_runtime_and_restores_after_restart(
    qapp, temp_config
):
    """托盘选择语言后，HUD、预测器与新启动实例必须使用同一配置。"""
    data = ClipboardData(text="clipboard payload", sequence_number=11)
    hud = HudWindow()
    tray = None
    restored_hud = None
    restored_tray = None
    try:
        hud.show_at_bottom_right(visible=False)
        predictor = PastePeekApp(listener=_Listener(data), target_detector=_Target())
        predictor.set_language(hud.language())
        predictor.analysis_ready.connect(hud.update_result)
        tray = TrayController(hud, QIcon(), tray_available=True, language=hud.language())
        tray.language_selected.connect(hud.set_language)
        hud.language_changed.connect(predictor.set_language)
        hud.language_changed.connect(tray.set_language)
        tray.start()
        predictor.check_clipboard()

        language_menu = _language_menu(tray)
        language_menu.actions()[1].trigger()
        qapp.processEvents()

        assert (hud.language(), predictor.language(), tray.language()) == (
            "en-US",
            "en-US",
            "en-US",
        )
        assert hud._tag.text() == "Plain text"
        assert hud._target_lbl.text() == " → Terminal"
        assert hud._risk_badge.text() == "Low risk"
        assert not _contains_chinese(hud._conclusion.text())
        assert not _contains_chinese(hud._preview.toPlainText())
        assert "Exit PastePeek" in [
            action.text() for action in tray.findChild(QSystemTrayIcon).contextMenu().actions()
        ]
        assert json.loads(temp_config.read_text(encoding="utf-8"))["language"] == "en-US"

        tray.stop()
        tray = None
        hud.close()

        restored_hud = HudWindow()
        restored_hud.show_at_bottom_right(visible=False)
        restored_predictor = PastePeekApp(
            listener=_Listener(data), target_detector=_Target()
        )
        restored_predictor.set_language(restored_hud.language())
        restored_predictor.analysis_ready.connect(restored_hud.update_result)
        restored_tray = TrayController(
            restored_hud,
            QIcon(),
            tray_available=True,
            language=restored_hud.language(),
        )
        restored_tray.start()
        restored_predictor.check_clipboard()

        assert restored_hud.language() == "en-US"
        assert restored_predictor.language() == "en-US"
        assert restored_tray.language() == "en-US"
        assert restored_hud._tag.text() == "Plain text"
        assert restored_hud._target_lbl.text() == " → Terminal"
        assert not _contains_chinese(restored_hud._conclusion.text())
        restored_menu = restored_tray.findChild(QSystemTrayIcon).contextMenu()
        assert "Language" in [action.text() for action in restored_menu.actions()]
    finally:
        if restored_tray is not None:
            restored_tray.stop()
        if restored_hud is not None:
            restored_hud.close()
        if tray is not None:
            tray.stop()
        hud.close()
