"""开机启动的安全边界测试。"""

import pytest

from src.startup import StartupManager, StartupUnsupportedError


class MemoryRunRegistry:
    """只替代注册表系统边界。"""

    def __init__(self) -> None:
        self.command: str | None = None

    def read(self) -> str | None:
        return self.command

    def write(self, command: str) -> None:
        self.command = command

    def delete(self) -> None:
        self.command = None


def test_source_run_cannot_register_python_as_startup_command(tmp_path):
    """源码运行不得污染正式开机启动项。"""
    registry = MemoryRunRegistry()
    manager = StartupManager(
        tmp_path / "python.exe",
        frozen=False,
        registry=registry,
    )

    with pytest.raises(StartupUnsupportedError, match="便携 EXE"):
        manager.set_enabled(True)
    assert registry.command is None
    assert not manager.is_enabled()
