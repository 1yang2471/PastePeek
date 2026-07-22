"""Tests for HUD configuration persistence and usage tracking switch.

Covers default config generation, save/load round-trips, missing-field
fallbacks, last-target memory, and the usage_tracking_enabled toggle.
"""

import json
import os
import site
from unittest.mock import Mock

import pytest


# 定位正式安装的 Qt 平台插件，确保测试进程可以创建 QApplication。
def _system_pyside_platforms() -> str | None:
    for base in site.getsitepackages() + [site.getusersitepackages()]:
        platforms = os.path.join(base, "PySide6", "plugins", "platforms")
        if os.path.isdir(platforms):
            return platforms
    return None


_pyside_platforms = _system_pyside_platforms()
if _pyside_platforms:
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", _pyside_platforms)

from PySide6.QtCore import QPointF
from PySide6.QtGui import QEnterEvent

from src.models.types import AppOutput
from src.ui import hud_window
from src.usage.tracker import UsageTracker


@pytest.fixture(scope="session")
def qapp():
    """Provide a single QApplication for Qt widget tests."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    """Redirect hud_window config paths to a temporary directory."""
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))
    return config_path


@pytest.fixture
def window(qapp, temp_config):
    """Create a HudWindow with a mock tracker for config-only tests."""
    return hud_window.HudWindow(tracker=Mock())


@pytest.fixture
def sample_output():
    """Minimal AppOutput usable by HudWindow.update_result."""
    return AppOutput(
        content_type="rich_text",
        content_type_label="富文本",
        risk_level="medium",
        target="word",
        prediction="Word 中列表可能丢失",
        preview_data={},
        primary_action="strip_formats",
        available_actions=["strip_formats"],
    )


class TestConfigDefaults:
    """Default config is returned when no config file exists."""

    def test_default_config_has_all_fields(self, temp_config):
        config = hud_window.HudWindow._load_config()
        assert config["x"] is None
        assert config["y"] is None
        assert config["first_run"] is True
        assert config["last_target"] == ""
        assert config["default_expand"] is False
        assert config["default_target"] == "word"
        assert config["ui_width"] == hud_window._W
        assert config["usage_tracking_enabled"] is False
        assert config["language"] == "zh-CN"


class TestConfigReadWrite:
    """Known fields survive a save/load round-trip."""

    def test_save_and_load_config(self, window, temp_config):
        window.move(100, 200)
        window._first_run = False
        window._width = 350
        window._config = {
            "last_target": "chrome",
            "default_expand": True,
            "default_target": "code_editor",
            "usage_tracking_enabled": False,
        }
        window._save_state()

        loaded = hud_window.HudWindow._load_config()
        assert loaded["x"] == 100
        assert loaded["y"] == 200
        assert loaded["first_run"] is False
        assert loaded["last_target"] == "chrome"
        assert loaded["default_expand"] is True
        assert loaded["default_target"] == "code_editor"
        assert loaded["ui_width"] == 350
        assert loaded["usage_tracking_enabled"] is False
        assert loaded["language"] == "zh-CN"

    def test_missing_fields_use_defaults(self, temp_config):
        temp_config.parent.mkdir(parents=True, exist_ok=True)
        temp_config.write_text(
            json.dumps({"x": 50, "last_target": "terminal"}, ensure_ascii=False),
            encoding="utf-8",
        )
        loaded = hud_window.HudWindow._load_config()
        assert loaded["x"] == 50
        assert loaded["y"] is None
        assert loaded["first_run"] is True
        assert loaded["last_target"] == "terminal"
        assert loaded["default_expand"] is False
        assert loaded["default_target"] == "word"
        assert loaded["ui_width"] == hud_window._W
        assert loaded["usage_tracking_enabled"] is False
        assert loaded["language"] == "zh-CN"

    def test_corrupt_file_falls_back_to_defaults(self, temp_config):
        temp_config.parent.mkdir(parents=True, exist_ok=True)
        temp_config.write_text("not json", encoding="utf-8")
        loaded = hud_window.HudWindow._load_config()
        assert loaded["first_run"] is True
        assert loaded["usage_tracking_enabled"] is False


class TestLastTargetMemory:
    """User-selected target is persisted as last_target."""

    def test_target_selection_persists_last_target(self, window, temp_config):
        window._on_target_selected("chrome")
        loaded = hud_window.HudWindow._load_config()
        assert loaded["last_target"] == "chrome"

    def test_last_target_from_more_menu(self, window, temp_config):
        window._on_target_selected("chat_app")
        loaded = hud_window.HudWindow._load_config()
        assert loaded["last_target"] == "chat_app"


class TestUsageTrackingSwitch:
    """usage_tracking_enabled controls whether tracker hooks fire."""

    def test_tracking_enabled_calls_on_update(self, window, sample_output):
        window._config["usage_tracking_enabled"] = True
        window.update_result(sample_output)
        window._tracker.on_update.assert_called_once_with("rich_text", "medium")

    def test_tracking_disabled_skips_on_update(self, window, sample_output):
        window._config["usage_tracking_enabled"] = False
        window.update_result(sample_output)
        window._tracker.on_update.assert_not_called()

    def test_tracking_enabled_calls_on_viewed(self, window):
        event = QEnterEvent(QPointF(0, 0), QPointF(0, 0), QPointF(0, 0))
        window._config["usage_tracking_enabled"] = True
        window.enterEvent(event)
        window._tracker.on_viewed.assert_called_once()

    def test_tracking_disabled_skips_on_viewed(self, window):
        event = QEnterEvent(QPointF(0, 0), QPointF(0, 0), QPointF(0, 0))
        window._config["usage_tracking_enabled"] = False
        window.enterEvent(event)
        window._tracker.on_viewed.assert_not_called()

    def test_disabled_tracking_does_not_create_usage_log(
        self, qapp, temp_config, tmp_path, sample_output
    ):
        tracker = UsageTracker(log_dir=tmp_path)
        window = hud_window.HudWindow(tracker=tracker)
        window._config["usage_tracking_enabled"] = False
        window.update_result(sample_output)
        assert not (tmp_path / "usage.jsonl").exists()
