"""HUD 多屏位置恢复测试。"""

import json

import pytest
from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QApplication

from src.ui import hud_window


class _Screen:
    """提供位置恢复所需的屏幕几何信息。"""

    def __init__(self, geometry: QRect, available_geometry: QRect | None = None):
        self._geometry = geometry
        self._available_geometry = available_geometry or geometry

    def geometry(self) -> QRect:
        return self._geometry

    def availableGeometry(self) -> QRect:
        return self._available_geometry


class _WindowHandle:
    """让 HUD 在测试中读取指定屏幕。"""

    def __init__(self, screen: _Screen):
        self._screen = screen

    def screen(self) -> _Screen:
        return self._screen


@pytest.fixture(scope="module")
def qapp():
    """为 HUD 创建共享 Qt 应用。"""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize(
    ("saved_position", "screen_geometry"),
    [
        (QPoint(-1900, 100), QRect(-1920, 0, 1920, 1080)),
        (QPoint(100, -1000), QRect(0, -1080, 1920, 1080)),
    ],
    ids=("left-screen", "upper-screen"),
)
def test_show_restores_saved_position_on_negative_coordinate_screen(
    qapp,
    tmp_path,
    monkeypatch,
    saved_position,
    screen_geometry,
):
    """左侧或上方副屏上的合法负坐标应原样恢复。"""
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"
    config_dir.mkdir()
    config_path.write_text(
        json.dumps(
            {
                "x": saved_position.x(),
                "y": saved_position.y(),
                "first_run": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    screen = _Screen(screen_geometry)

    class _GuiApplication:
        @staticmethod
        def screens():
            return [screen]

    monkeypatch.setattr(QtGui, "QGuiApplication", _GuiApplication)
    window = hud_window.HudWindow()

    window.show_at_bottom_right(visible=False)

    assert window.pos() == saved_position


@pytest.mark.parametrize(
    ("saved_position", "available_geometry"),
    [
        (QPoint(20, 100), QRect(80, 0, 1840, 1040)),
        (QPoint(100, 10), QRect(0, 40, 1920, 1000)),
    ],
    ids=("left-taskbar", "top-taskbar"),
)
def test_saved_position_in_taskbar_area_falls_back_to_available_work_area(
    qapp,
    tmp_path,
    monkeypatch,
    saved_position,
    available_geometry,
):
    """位于任务栏占用区域的保存坐标不能被当作可用位置。"""
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"
    config_dir.mkdir()
    config_path.write_text(
        json.dumps(
            {
                "x": saved_position.x(),
                "y": saved_position.y(),
                "first_run": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    screen = _Screen(QRect(0, 0, 1920, 1080), available_geometry)

    class _GuiApplication:
        @staticmethod
        def screens():
            return [screen]

    class _WidgetsApplication:
        @staticmethod
        def primaryScreen():
            return screen

    monkeypatch.setattr(QtGui, "QGuiApplication", _GuiApplication)
    monkeypatch.setattr(QtWidgets, "QApplication", _WidgetsApplication)
    window = hud_window.HudWindow()

    window.show_at_bottom_right(visible=False)

    assert window.pos() == QPoint(
        available_geometry.right() - window.width() - 16,
        available_geometry.bottom() - window.height() - 16,
    )


@pytest.mark.parametrize(
    "start_position",
    [QPoint(10, 10), QPoint(1900, 1050)],
    ids=("left-top", "right-bottom"),
)
def test_tray_restore_clamps_window_to_all_available_work_area_edges(
    qapp,
    monkeypatch,
    start_position,
):
    """任务栏位置变化后，从托盘恢复应重新约束工作区四边。"""
    available_geometry = QRect(80, 40, 1840, 1000)
    screen = _Screen(QRect(0, 0, 1920, 1080), available_geometry)
    window = hud_window.HudWindow()
    monkeypatch.setattr(window, "windowHandle", lambda: _WindowHandle(screen))
    window.move(start_position)

    window.show_from_tray()
    qapp.processEvents()

    assert window.x() >= available_geometry.left()
    assert window.y() >= available_geometry.top()
    assert window.x() + window.width() - 1 <= available_geometry.right()
    assert window.y() + window.height() - 1 <= available_geometry.bottom()


def test_show_moves_fully_offscreen_saved_position_to_primary_screen(
    qapp,
    tmp_path,
    monkeypatch,
):
    """保存位置完全离屏时应回到主屏右下角。"""
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"
    config_dir.mkdir()
    config_path.write_text(
        json.dumps({"x": -2500, "y": -1200, "first_run": False}),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    primary_geometry = QRect(0, 0, 1920, 1040)
    primary_screen = _Screen(primary_geometry)

    class _GuiApplication:
        @staticmethod
        def screens():
            return [primary_screen]

    class _WidgetsApplication:
        @staticmethod
        def primaryScreen():
            return primary_screen

    monkeypatch.setattr(QtGui, "QGuiApplication", _GuiApplication)
    monkeypatch.setattr(QtWidgets, "QApplication", _WidgetsApplication)
    window = hud_window.HudWindow()

    window.show_at_bottom_right(visible=False)

    assert window.pos() == QPoint(
        primary_geometry.right() - window.width() - 16,
        primary_geometry.bottom() - window.height() - 16,
    )


def test_expanded_hud_keeps_rounding_margin_inside_work_area(
    qapp,
    tmp_path,
    monkeypatch,
):
    """展开重定位应为高 DPI 原生外框取整额外保留一个逻辑像素。"""
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"
    config_dir.mkdir()
    config_path.write_text(
        json.dumps(
            {
                "x": None,
                "y": None,
                "first_run": False,
                "default_expand": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    primary_geometry = QRect(0, 0, 1920, 1032)
    primary_screen = _Screen(primary_geometry)

    class _GuiApplication:
        @staticmethod
        def screens():
            return [primary_screen]

    class _WidgetsApplication:
        @staticmethod
        def primaryScreen():
            return primary_screen

    monkeypatch.setattr(QtGui, "QGuiApplication", _GuiApplication)
    monkeypatch.setattr(QtWidgets, "QApplication", _WidgetsApplication)
    window = hud_window.HudWindow()
    monkeypatch.setattr(
        window,
        "windowHandle",
        lambda: _WindowHandle(primary_screen),
    )

    window.show_at_bottom_right(visible=False)

    assert window.y() + window.height() <= primary_geometry.bottom() - 17


def test_background_default_expand_is_repositioned_after_tray_restore(
    qapp,
    tmp_path,
    monkeypatch,
):
    """后台默认展开的 HUD 从托盘显示后必须完整位于工作区。"""
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"
    config_dir.mkdir()
    config_path.write_text(
        json.dumps(
            {
                "x": None,
                "y": None,
                "first_run": False,
                "default_expand": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hud_window, "_POS_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hud_window, "_POS_CONFIG_PATH", str(config_path))

    work_area = QRect(0, 0, 800, 800)
    screen = _Screen(work_area)

    class _GuiApplication:
        @staticmethod
        def screens():
            return [screen]

    class _WidgetsApplication:
        @staticmethod
        def primaryScreen():
            return screen

    monkeypatch.setattr(QtGui, "QGuiApplication", _GuiApplication)
    monkeypatch.setattr(QtWidgets, "QApplication", _WidgetsApplication)
    window = hud_window.HudWindow()
    real_window_handle = window.windowHandle

    # 隐藏启动时保留真实的无句柄状态；显示后提供对应工作区。
    monkeypatch.setattr(
        window,
        "windowHandle",
        lambda: _WindowHandle(screen) if window.isVisible() else None,
    )

    window.show_at_bottom_right(visible=False)

    assert real_window_handle() is None
    assert window.y() + window.height() - 1 > work_area.bottom()

    window.show_from_tray()
    qapp.processEvents()

    assert window.isVisible()
    assert window.x() >= work_area.left()
    assert window.y() >= work_area.top()
    assert window.x() + window.width() - 1 <= work_area.right()
    assert window.y() + window.height() - 1 <= work_area.bottom()
