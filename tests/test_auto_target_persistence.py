"""自动目标检测状态的持久化回归测试。"""

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

from src.ui import hud_window


@pytest.fixture(scope="module")
def qapp():
    """提供唯一的 Qt 应用实例。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_auto_detected_highlight_is_not_saved_as_manual_target(
    qapp, tmp_path, monkeypatch
):
    """自动高亮目标不得在保存窗口位置时变成手动覆盖。"""
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))
    window = hud_window.HudWindow()
    window._config = {"last_target": ""}
    window._icon_bar.set_current_target("code_editor")

    window._save_state()

    assert hud_window.HudWindow._load_config()["last_target"] == ""
