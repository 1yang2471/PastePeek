"""配置只保存用户偏好，不保存瞬时界面状态。"""

from src.ui import hud_window


def test_release_config_drops_transient_expanded_state(tmp_path, monkeypatch):
    """展开状态应由 default_expand 决定，不保留重复的 expanded。"""
    config_dir = tmp_path / "config"
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(
        hud_window, "_POS_CONFIG_PATH", str(config_dir / "config.json")
    )

    assert "expanded" not in hud_window.HudWindow._load_config()
