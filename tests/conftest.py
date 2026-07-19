"""测试级共享资源清理。"""

from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def close_qt_top_level_widgets():
    """每个测试后销毁顶层 Qt 控件，避免跨用例原生资源污染。"""
    yield
    if "PySide6.QtWidgets" not in sys.modules:
        return

    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
