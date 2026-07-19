"""HUD 默认展开偏好的端到端界面测试。"""

import json
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


def test_default_expand_opens_the_second_layer(qapp, tmp_path, monkeypatch):
    """启动偏好为真时，第二层必须实际显示。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps({"default_expand": True, "first_run": False}),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    window = hud_window.HudWindow()
    window.show_at_bottom_right()
    qapp.processEvents()

    assert window._expanded_panel.isVisible()
    assert window.height() > hud_window._H_IDLE
    window.close()
