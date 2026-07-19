"""当前用户开机启动管理的行为测试。"""

import winreg
from uuid import uuid4

from src.startup import StartupManager, WindowsRunRegistry


class MemoryRunRegistry:
    """只替代 Windows 注册表这一系统边界。"""

    def __init__(self) -> None:
        self.command: str | None = None

    def read(self) -> str | None:
        return self.command

    def write(self, command: str) -> None:
        self.command = command

    def delete(self) -> None:
        self.command = None


def test_enabling_startup_registers_quoted_portable_exe(tmp_path):
    """启用开机启动时应写入当前 EXE 的静默启动命令。"""
    executable = tmp_path / "Paste Peek" / "PastePeek.exe"
    executable.parent.mkdir()
    executable.touch()
    registry = MemoryRunRegistry()
    manager = StartupManager(executable, frozen=True, registry=registry)

    manager.set_enabled(True)

    assert registry.command == f'"{executable.resolve()}" --background'
    assert manager.is_enabled()


def test_windows_registry_boundary_round_trip():
    """当前用户注册表边界应能真实写入、读取并幂等删除。"""
    key_path = f"Software\\PastePeek\\Tests\\{uuid4().hex}"
    registry = WindowsRunRegistry(key_path=key_path, value_name="PastePeekTest")

    try:
        assert registry.read() is None
        registry.write('"C:\\Tools\\PastePeek.exe" --background')
        assert registry.read() == '"C:\\Tools\\PastePeek.exe" --background'
        registry.delete()
        registry.delete()
        assert registry.read() is None
    finally:
        registry.delete()
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            pass
