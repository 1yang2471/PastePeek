"""PastePeek 单实例协调的行为测试。"""

import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest
from PySide6.QtCore import QCoreApplication, QEventLoop

from src.single_instance import SingleInstanceGuard

ROOT = Path(__file__).resolve().parents[1]
_SECOND_INSTANCE_CODE = """
import sys
from PySide6.QtCore import QCoreApplication
from src.single_instance import SingleInstanceGuard

app = QCoreApplication([])
guard = SingleInstanceGuard(sys.argv[1])
is_primary = guard.acquire()
guard.close()
raise SystemExit(2 if is_primary else 0)
"""


@pytest.fixture(scope="module")
def core_app():
    """为 Qt 本地通信提供事件循环。"""
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


def test_second_launch_requests_existing_instance_to_show(core_app):
    """第二次启动应通知已有实例，而不是成为新的主实例。"""
    server_name = f"PastePeek-test-{uuid4().hex}"
    primary = SingleInstanceGuard(server_name)
    activations: list[bool] = []
    primary.activation_requested.connect(lambda: activations.append(True))

    assert primary.acquire()
    core_app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 100)
    environment = os.environ.copy()
    python_path = [str(ROOT)]
    if environment.get("PYTHONPATH"):
        python_path.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_path)
    secondary = subprocess.Popen(
        [sys.executable, "-c", _SECOND_INSTANCE_CODE, server_name],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 5
    while secondary.poll() is None and time.monotonic() < deadline:
        core_app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        time.sleep(0.01)
    core_app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 100)
    if secondary.poll() is None:
        secondary.kill()
    stdout, stderr = secondary.communicate(timeout=2)

    assert secondary.returncode == 0, f"stdout={stdout}\nstderr={stderr}"
    assert activations == [True]

    primary.close()


def test_second_launch_waits_for_primary_startup_to_finish(core_app):
    """主实例初始化稍慢时，第二次启动仍应完成唤醒而不是报错。"""
    server_name = f"PastePeek-test-{uuid4().hex}"
    primary = SingleInstanceGuard(server_name)
    activations: list[bool] = []
    primary.activation_requested.connect(lambda: activations.append(True))
    secondary = None

    try:
        assert primary.acquire()
        environment = os.environ.copy()
        python_path = [str(ROOT)]
        if environment.get("PYTHONPATH"):
            python_path.append(environment["PYTHONPATH"])
        environment["PYTHONPATH"] = os.pathsep.join(python_path)
        secondary = subprocess.Popen(
            [sys.executable, "-c", _SECOND_INSTANCE_CODE, server_name],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # 模拟便携 EXE 已取得单实例锁，但 HUD 和托盘仍在初始化。
        time.sleep(1.2)
        deadline = time.monotonic() + 5
        while secondary.poll() is None and time.monotonic() < deadline:
            core_app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            time.sleep(0.01)
        core_app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 100)
        if secondary.poll() is None:
            secondary.kill()
        stdout, stderr = secondary.communicate(timeout=2)

        assert secondary.returncode == 0, f"stdout={stdout}\nstderr={stderr}"
        assert activations == [True]
    finally:
        if secondary is not None and secondary.poll() is None:
            secondary.kill()
            secondary.wait(timeout=2)
        primary.close()


def test_new_instance_can_start_after_primary_closes(core_app):
    """主实例正常退出后应立即释放所有权。"""
    server_name = f"PastePeek-test-{uuid4().hex}"
    first = SingleInstanceGuard(server_name)
    replacement = SingleInstanceGuard(server_name)

    assert first.acquire()
    first.close()
    assert replacement.acquire()

    replacement.close()


def test_background_launch_does_not_show_existing_instance(core_app):
    """登录任务重复启动时应静默退出，不发送显示请求。"""
    server_name = f"PastePeek-test-{uuid4().hex}"
    primary = SingleInstanceGuard(server_name)
    background = SingleInstanceGuard(server_name)
    activations: list[bool] = []
    primary.activation_requested.connect(lambda: activations.append(True))

    assert primary.acquire()
    assert not background.acquire(activate_existing=False)
    core_app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 100)
    assert activations == []

    background.close()
    primary.close()
