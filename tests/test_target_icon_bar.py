"""HUD 目标场景条的用户行为测试。"""

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

from src.ui.hud_window import TargetIconBar


@pytest.fixture(scope="module")
def qapp():
    """为目标场景条提供唯一的 Qt 应用实例。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_auto_detection_can_be_restored(qapp):
    """用户必须能从手动场景恢复到自动目标检测。"""
    bar = TargetIconBar()
    selected = []
    bar.target_selected.connect(selected.append)
    bar.set_current_target("code_editor")

    bar.select_auto()

    assert bar.current_target() == ""
    assert selected == [""]


def test_icon_bar_fits_minimum_hud_content_width(qapp):
    """场景条在 300px HUD 的内容区内不得横向溢出。"""
    bar = TargetIconBar()
    hud_content_width = 300 - 12 - 12

    bar.ensurePolished()
    assert bar.minimumSizeHint().width() <= hud_content_width


def test_target_options_show_category_icons_without_removing_labels(qapp):
    """目标选项应同时保留可读文字和类别图标。"""
    from PySide6.QtWidgets import QPushButton

    bar = TargetIconBar()
    bar.show()
    qapp.processEvents()

    target_buttons = [
        button
        for button in bar.findChildren(QPushButton)
        if button.text() != "…"
    ]

    assert target_buttons
    assert all(button.text() for button in target_buttons)
    assert all(not button.icon().isNull() for button in target_buttons)

    bar.close()


def test_target_bar_reduces_visible_options_at_compact_width(qapp):
    """300px HUD 下目标栏应把次要场景收进更多菜单。"""
    from PySide6.QtWidgets import QPushButton

    bar = TargetIconBar()
    bar.resize(276, 28)
    bar.show()
    qapp.processEvents()

    buttons = {button.text(): button for button in bar.findChildren(QPushButton)}

    assert not buttons["MD"].isVisible()
    assert buttons["…"].isVisible()

    bar.close()


def test_visible_target_icons_and_labels_fit_inside_their_buttons(qapp):
    """目标图标和文字不得在紧凑按钮内被裁切。"""
    from PySide6.QtWidgets import QPushButton

    bar = TargetIconBar()
    bar.resize(276, 32)
    bar.show()
    qapp.processEvents()

    target_buttons = [
        button
        for button in bar.findChildren(QPushButton)
        if button.isVisible() and button.text() != "…"
    ]
    clipped = [
        (button.text(), button.sizeHint().width(), button.width())
        for button in target_buttons
        if button.sizeHint().width() > button.width()
    ]

    assert not clipped, clipped

    bar.close()


def test_target_bar_restores_all_common_options_when_space_allows(qapp):
    """400px HUD 下应恢复全部五个常用目标。"""
    from PySide6.QtWidgets import QPushButton

    bar = TargetIconBar()
    bar.resize(376, 28)
    bar.show()
    qapp.processEvents()

    buttons = {button.text(): button for button in bar.findChildren(QPushButton)}

    assert buttons["MD"].isVisible()

    bar.close()


def test_hud_minimize_button_collapses_to_compact_dot(qapp):
    """最小化后窗口必须保持为可点击的 36×18 圆点区域。"""
    from PySide6.QtWidgets import QPushButton

    from src.ui.hud_window import HudWindow

    hud = HudWindow()
    hud.show()
    qapp.processEvents()
    minimize_button = next(
        button
        for button in hud.findChildren(QPushButton)
        if button.objectName() == "MinimizeButton"
    )

    minimize_button.click()
    qapp.processEvents()

    assert (hud.width(), hud.height()) == (36, 18)


def test_window_controls_have_accessible_icon_hit_areas(qapp):
    """最小化和隐藏控件应使用清晰图标与足够点击区域。"""
    from PySide6.QtWidgets import QPushButton

    from src.ui.hud_window import HudWindow

    hud = HudWindow()
    controls = {
        button.objectName(): button
        for button in hud.findChildren(QPushButton)
    }

    minimize = controls["MinimizeButton"]
    hide = controls["HideButton"]
    assert minimize.size().width() >= 24 and minimize.size().height() >= 24
    assert hide.size().width() >= 24 and hide.size().height() >= 24
    assert not minimize.icon().isNull()
    assert not hide.icon().isNull()
    assert minimize.toolTip() == "最小化 HUD"
    assert hide.toolTip() == "隐藏 HUD，继续监听"
    assert minimize.accessibleName() == "最小化 HUD"
    assert hide.accessibleName() == "隐藏 HUD"

    hud.close()


def test_expanded_hud_minimizes_without_retaining_content_height(qapp):
    """展开内容不得在最小化后把窄窗口纵向撑开。"""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui.hud_window import HudWindow

    hud = HudWindow()
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
    assert hud.height() > 36

    minimize_button = next(
        button
        for button in hud.findChildren(QPushButton)
        if button.objectName() == "MinimizeButton"
    )
    minimize_button.click()
    qapp.processEvents()

    assert (hud.width(), hud.height()) == (36, 18)


def test_hud_displays_binary_snapshot_as_non_text(qapp):
    """纯图片或文件快照不得在 HUD 中显示为纯文本。"""
    from PySide6.QtWidgets import QLabel

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui.hud_window import HudWindow

    hud = HudWindow()
    output = OutcomePredictor().generate("plain_text", "word")
    output.has_binary = True
    output.content_type_label = "非文本"
    output.prediction = "当前剪贴板包含图片或文件，PastePeek 不会修改此内容"
    output.preview_data = {
        "summary": output.prediction,
        "risks": ["暂不提供图片或文件的效果预览"],
    }

    hud.update_result(output)

    visible_texts = {label.text() for label in hud.findChildren(QLabel)}
    assert "非文本" in visible_texts


def test_hud_names_the_risk_level_instead_of_using_color_alone(qapp):
    """风险状态应同时使用文字，不能只显示颜色圆点。"""
    from PySide6.QtWidgets import QLabel

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui.hud_window import HudWindow

    hud = HudWindow()
    output = OutcomePredictor().generate("rich_text", "terminal")
    output.risk_level = "medium"
    hud.update_result(output)
    hud.show()
    qapp.processEvents()

    visible_texts = {
        label.text()
        for label in hud.findChildren(QLabel)
        if label.isVisible()
    }

    assert "中风险" in visible_texts

    hud.close()


def test_primary_action_keeps_label_and_exposes_action_icon(qapp):
    """主操作按钮应明确显示动作名称和对应图标。"""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui.hud_window import HudWindow

    hud = HudWindow()
    output = OutcomePredictor().generate("plain_text", "chrome")
    output.primary_action = "clean_url"
    output.available_actions = ["clean_url"]
    hud.update_result(output)
    hud.show()
    qapp.processEvents()
    QTest.mouseClick(hud, Qt.MouseButton.LeftButton, pos=QPoint(280, 18))
    qapp.processEvents()

    action_button = next(
        button
        for button in hud.findChildren(QPushButton)
        if button.text() == "净化链接" and button.isVisible()
    )
    assert not action_button.icon().isNull()

    hud.close()


def test_expanded_hud_uses_readable_functional_text(qapp):
    """最小宽度展开态的功能文本不得小于 9pt 或展示快捷键提示。"""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel, QPushButton

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui.hud_window import HudWindow

    hud = HudWindow()
    output = OutcomePredictor().generate("rich_text", "terminal")
    output.raw_text = "第一段\n第二行\n- 苹果\n- 香蕉"
    output.raw_html = (
        "<p>第一段<br>第二行</p><ul><li>苹果</li><li>香蕉</li></ul>"
    )
    output.primary_action = "merge_lines"
    output.available_actions = ["merge_lines", "strip_formats"]
    hud.update_result(output)
    hud.show()
    qapp.processEvents()

    QTest.mouseClick(
        hud,
        Qt.MouseButton.LeftButton,
        pos=QPoint(280, 18),
    )
    qapp.processEvents()

    excluded = {"●", "···"}
    labels = [
        label
        for label in hud.findChildren(QLabel)
        if label.isVisible() and label.text() and label.text() not in excluded
    ]
    buttons = [
        button
        for button in hud.findChildren(QPushButton)
        if button.isVisible() and button.text() and button.text() not in excluded
    ]

    assert labels
    assert buttons
    small_labels = [
        (label.text(), label.font().pointSizeF())
        for label in labels
        if label.font().pointSizeF() < 9
    ]
    small_buttons = [
        (button.text(), button.font().pointSizeF())
        for button in buttons
        if button.font().pointSizeF() < 9
    ]
    assert not small_labels, small_labels
    assert not small_buttons, small_buttons
    assert all("Enter" not in button.text() for button in buttons)

    hud.close()


def test_hud_shows_quiet_status_when_no_safe_action_is_available(qapp):
    """没有安全主动操作时应显示状态文字，而不是伪装成可点击按钮。"""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel, QPushButton

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui.hud_window import HudWindow

    hud = HudWindow()
    output = OutcomePredictor().generate("code", "code_editor")
    output.primary_action = ""
    output.action_type = ""
    output.available_actions = []
    hud.update_result(output)
    hud.show()
    qapp.processEvents()
    QTest.mouseClick(hud, Qt.MouseButton.LeftButton, pos=QPoint(280, 18))
    qapp.processEvents()

    visible_buttons = [
        button.text()
        for button in hud.findChildren(QPushButton)
        if button.isVisible()
    ]
    visible_labels = [
        label.text()
        for label in hud.findChildren(QLabel)
        if label.isVisible()
    ]

    assert "无需处理" not in visible_buttons
    assert "当前内容无需处理" in visible_labels

    hud.close()


def test_action_error_remains_readable_until_the_next_result(qapp):
    """操作失败信息不能在用户读完前自动消失。"""
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui.hud_window import HudWindow

    hud = HudWindow()
    output = OutcomePredictor().generate("plain_text", "chrome")
    hud.update_result(output)
    hud.show()
    qapp.processEvents()

    hud.show_error("剪贴板内容已变化")
    QTest.qWait(700)
    qapp.processEvents()

    visible_texts = [
        label.text()
        for label in hud.findChildren(QLabel)
        if label.isVisible()
    ]
    assert any("操作失败: 剪贴板内容已变化" in text for text in visible_texts)
    assert hud.height() > 36

    hud.close()


def test_action_error_does_not_collapse_when_pointer_leaves(qapp):
    """鼠标移出 HUD 时，失败说明仍应保持展开可读。"""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    from src.explainer.outcome_predictor import OutcomePredictor
    from src.ui.hud_window import HudWindow

    hud = HudWindow()
    hud.update_result(OutcomePredictor().generate("plain_text", "chrome"))
    hud.show()
    qapp.processEvents()
    hud.show_error("剪贴板内容已变化")
    QApplication.sendEvent(hud, QEvent(QEvent.Type.Leave))
    qapp.processEvents()

    assert hud.height() > 36

    hud.close()
