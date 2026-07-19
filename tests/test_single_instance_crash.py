"""单实例主进程异常退出后的恢复测试。"""

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from PySide6.QtCore import QCoreApplication

from src.single_instance import SingleInstanceGuard

ROOT = Path(__file__).resolve().parents[1]
_CRASHING_PRIMARY_CODE = """
import sys
import time
from PySide6.QtCore import QCoreApplication
from src.single_instance import SingleInstanceGuard

app = QCoreApplication([])
guard = SingleInstanceGuard(sys.argv[1])
if not guard.acquire():
    raise SystemExit(2)
print("READY", flush=True)
time.sleep(30)
"""


@pytest.fixture(scope="module")
def core_app():
    """为恢复后的本地服务提供 Qt 应用实例。"""
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


def test_new_instance_recovers_after_primary_process_crashes(core_app):
    """主进程被强制终止后，陈旧锁和端点不得阻止重启。"""
    server_name = f"PastePeek-crash-test-{uuid4().hex}"
    environment = os.environ.copy()
    python_path = [str(ROOT)]
    if environment.get("PYTHONPATH"):
        python_path.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_path)
    crashed = subprocess.Popen(
        [sys.executable, "-c", _CRASHING_PRIMARY_CODE, server_name],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert crashed.stdout is not None
        assert crashed.stdout.readline().strip() == "READY"
        crashed.kill()
        crashed.wait(timeout=5)

        replacement = SingleInstanceGuard(server_name)
        assert replacement.acquire()
        replacement.close()
    finally:
        if crashed.poll() is None:
            crashed.kill()
            crashed.wait(timeout=5)
