"""HUD 启动偏好的公共接口测试。"""

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

from src.ui.hud_window import HudWindow


@pytest.fixture(scope="module")
def qapp():
    """提供唯一的 Qt 应用实例。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_hud_exposes_validated_startup_targets(qapp):
    """启动管线可分别读取默认目标和上次手动目标。"""
    window = HudWindow()
    window._config = {
        "default_target": "terminal",
        "last_target": "chrome",
    }

    assert window.default_target() == "terminal"
    assert window.preferred_target() == "chrome"
