"""首次运行提示的真实 Qt 布局测试。"""

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


@pytest.fixture(scope="module")
def qapp():
    """为 HUD 几何验收提供唯一 Qt 应用实例。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_first_run_status_fits_inside_300px_hud(qapp, tmp_path, monkeypatch):
    """首次提示文字在最小宽度 HUD 中不得被裁切。"""
    from PySide6.QtWidgets import QLabel

    from src.ui import hud_window

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps({"first_run": True, "ui_width": 300}),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    hud = hud_window.HudWindow()
    hud.show_at_bottom_right()
    qapp.processEvents()
    tip_label = next(
        label
        for label in hud.findChildren(QLabel)
        if "提示：" in label.text()
    )

    assert tip_label.sizeHint().width() <= tip_label.width()
    assert tip_label.sizeHint().height() <= tip_label.height()

    hud.close()
