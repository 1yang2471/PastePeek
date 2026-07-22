"""HUD 运行时语言切换测试。"""

import os
import site
from unittest.mock import Mock

import pytest


def _system_pyside_platforms() -> str | None:
    for base in site.getsitepackages() + [site.getusersitepackages()]:
        platforms = os.path.join(base, "PySide6", "plugins", "platforms")
        if os.path.isdir(platforms):
            return platforms
    return None


if platforms := _system_pyside_platforms():
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", platforms)


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))
    return config_path

from src.models.types import AppOutput
from src.ui import hud_window


def test_hud_language_defaults_to_chinese_and_persists_english(qapp, temp_config):
    window = hud_window.HudWindow(tracker=Mock())
    assert hud_window.HudWindow._load_config()["language"] == "zh-CN"
    window.show_at_bottom_right(visible=False)

    assert window.set_language("en-US") == "en-US"
    window._save_state()

    assert hud_window.HudWindow._load_config()["language"] == "en-US"
    window.close()


def test_hud_switch_refreshes_owned_labels(qapp, temp_config):
    window = hud_window.HudWindow(tracker=Mock())
    window.show_at_bottom_right(visible=False)
    window.update_result(
        AppOutput(
            content_type="plain_text",
            content_type_label="纯文本",
            risk_level="none",
            target="word",
            primary_action="",
            available_actions=[],
        )
    )

    window.set_language("en-US")

    assert window._action_status.text() == "No action needed for this content"
    assert window._more_actions_btn.text() == "More actions"
    assert window._min_btn.toolTip() == "Minimize HUD"
    window.close()
