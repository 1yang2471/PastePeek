"""公开发布版配置契约测试。"""

from src.ui import hud_window


def test_release_config_drops_unused_ui_height(tmp_path, monkeypatch):
    """没有用户行为对应的 ui_height 不应继续持久化。"""
    config_dir = tmp_path / "config"
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(
        hud_window, "_POS_CONFIG_PATH", str(config_dir / "config.json")
    )

    assert "ui_height" not in hud_window.HudWindow._load_config()
