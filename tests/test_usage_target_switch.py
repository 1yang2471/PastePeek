'''目标切换与本地使用统计的集成测试。'''

import os
import site
from unittest.mock import Mock

import pytest


def _system_pyside_platforms() -> str | None:
    for base in site.getsitepackages() + [site.getusersitepackages()]:
        platforms = os.path.join(base, 'PySide6', 'plugins', 'platforms')
        if os.path.isdir(platforms):
            return platforms
    return None


if platforms := _system_pyside_platforms():
    os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', platforms)

from src.clipboard.listener import ClipboardData
from src.ui.app import PastePeekApp
from src.ui.hud_window import HudWindow


class FixedClipboardListener:
    def read(self):
        return ClipboardData(text='同一份剪贴板内容')


class FixedTargetDetector:
    def get_active_target(self):
        return 'word'


@pytest.fixture(scope='module')
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_target_switch_does_not_start_another_usage_session(qapp):
    '''同一剪贴板内切换目标时，本地统计只能开始一次会话。'''
    tracker = Mock()
    hud = HudWindow(tracker=tracker)
    hud._config = {'usage_tracking_enabled': True}
    app = PastePeekApp(
        listener=FixedClipboardListener(),
        target_detector=FixedTargetDetector(),
    )
    app.analysis_ready.connect(hud.update_result)

    app.check_clipboard()
    app.set_manual_target('terminal')

    tracker.on_update.assert_called_once_with('plain_text', 'none')
    hud.close()
