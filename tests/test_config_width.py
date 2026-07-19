"""HUD 宽度配置的边界测试。"""

import json

import pytest

from src.ui import hud_window


@pytest.mark.parametrize(
    ("configured", "expected"),
    [(120, 300), (2000, 640)],
)
def test_ui_width_is_clamped_to_a_layout_safe_range(
    tmp_path, monkeypatch, configured, expected
):
    """异常宽度不得造成场景条溢出或生成超宽 HUD。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps({"ui_width": configured}), encoding="utf-8"
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    assert hud_window.HudWindow._load_config()["ui_width"] == expected
