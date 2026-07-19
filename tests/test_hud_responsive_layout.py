"""HUD 多宽度展开态的真实 Qt 响应式布局测试。"""

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
    """为多宽度 HUD 验收提供唯一 Qt 应用实例。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("width", [300, 400, 640])
def test_expanded_hud_reflows_new_result_without_clipping(
    qapp,
    tmp_path,
    monkeypatch,
    width,
):
    """已展开 HUD 收到新结果后，所有可见内容必须保持在窗口内。"""
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui import hud_window

    config_dir = tmp_path / f"config-{width}"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "first_run": False,
                "default_expand": True,
                "ui_width": width,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    hud = hud_window.HudWindow()
    hud.show_at_bottom_right()
    output = OutcomePredictor().generate("rich_text", "terminal")
    output.raw_text = "第一段\n第二行\n- 苹果\n- 香蕉"
    output.raw_html = (
        "<p>第一段<br>第二行</p><ul><li>苹果</li><li>香蕉</li></ul>"
    )
    output.primary_action = "merge_lines"
    output.available_actions = ["merge_lines", "strip_formats"]

    hud.update_result(output)
    qapp.processEvents()

    widgets = (
        hud.findChildren(QLabel)
        + hud.findChildren(QPushButton)
        + hud.findChildren(QTextEdit)
    )
    for widget in widgets:
        if not widget.isVisible():
            continue
        top_left = widget.mapTo(hud, QPoint(0, 0))
        bounds = QRect(top_left, widget.size()).adjusted(0, 0, -1, -1)
        assert hud.rect().contains(bounds), (
            widget.text() if hasattr(widget, "text") else type(widget).__name__,
            bounds,
            hud.rect(),
        )
        if isinstance(widget, QLabel) and widget.wordWrap():
            required_height = widget.heightForWidth(widget.width())
            assert widget.height() >= required_height, (
                widget.text(),
                widget.height(),
                required_height,
            )

    hud.close()


def test_short_preview_does_not_keep_the_maximum_blank_height(qapp, tmp_path, monkeypatch):
    """短内容展开时，预览区不应占满长内容的最大高度。"""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui import hud_window

    config_dir = tmp_path / "config-short-preview"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps({"first_run": False, "ui_width": 300}),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    hud = hud_window.HudWindow()
    output = OutcomePredictor().generate("plain_text", "code_editor")
    output.raw_text = "一行短文本"
    output.raw_html = ""
    output.primary_action = ""
    output.available_actions = []
    hud.update_result(output)
    hud.show()
    qapp.processEvents()
    QTest.mouseClick(hud, Qt.MouseButton.LeftButton, pos=QPoint(280, 18))
    qapp.processEvents()

    assert hud._preview.height() <= 72

    hud.close()


def test_expanded_action_row_stays_close_to_the_window_bottom(
    qapp, tmp_path, monkeypatch
):
    """展开态操作区下方只保留稳定的小间距。"""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui import hud_window

    config_dir = tmp_path / "config-action-gap"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps({"first_run": False, "ui_width": 300}),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    hud = hud_window.HudWindow()
    output = OutcomePredictor().generate("rich_text", "terminal")
    output.raw_text = "第一段\n第二行\n- 苹果\n- 香蕉"
    output.raw_html = "<p>第一段<br>第二行</p><ul><li>苹果</li><li>香蕉</li></ul>"
    output.primary_action = "merge_lines"
    output.available_actions = ["merge_lines", "strip_formats"]
    hud.update_result(output)
    hud.show()
    qapp.processEvents()
    QTest.mouseClick(hud, Qt.MouseButton.LeftButton, pos=QPoint(280, 18))
    qapp.processEvents()

    action = next(
        button
        for button in hud.findChildren(QPushButton)
        if button.text() == "合并为一行" and button.isVisible()
    )
    top_left = action.mapTo(hud, QPoint(0, 0))
    bottom_gap = hud.height() - (top_left.y() + action.height())

    assert bottom_gap <= 32, bottom_gap

    hud.close()


def test_rendered_preview_text_is_not_hidden_below_the_viewport(
    qapp, tmp_path, monkeypatch
):
    """渲染器加入标题后，短预览也必须完整显示而不产生隐藏滚动区。"""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui import hud_window

    config_dir = tmp_path / "config-preview-viewport"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps({"first_run": False, "ui_width": 300}),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    hud = hud_window.HudWindow()
    output = OutcomePredictor().generate("plain_text", "chat_app")
    output.raw_text = "https://example.com/path?utm_source=codex&utm_medium=qa&id=42"
    output.primary_action = "clean_url"
    output.available_actions = ["clean_url"]
    hud.update_result(output)
    hud.show()
    qapp.processEvents()
    QTest.mouseClick(hud, Qt.MouseButton.LeftButton, pos=QPoint(280, 18))
    qapp.processEvents()

    assert hud._preview.verticalScrollBar().maximum() == 0

    hud.close()
