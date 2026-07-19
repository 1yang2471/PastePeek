"""便携 EXE 路径变化后的开机启动状态测试。"""

from src.startup import StartupManager


class MemoryRunRegistry:
    """只替代注册表系统边界。"""

    def __init__(self, command: str) -> None:
        self.command: str | None = command

    def read(self) -> str | None:
        return self.command

    def write(self, command: str) -> None:
        self.command = command

    def delete(self) -> None:
        self.command = None


def test_moved_exe_is_disabled_until_user_enables_current_path(tmp_path):
    """旧路径不能误报启用，重新启用后应更新到当前路径。"""
    current_executable = tmp_path / "new" / "PastePeek.exe"
    current_executable.parent.mkdir()
    current_executable.touch()
    registry = MemoryRunRegistry('"C:\\Old\\PastePeek.exe" --background')
    manager = StartupManager(
        current_executable,
        frozen=True,
        registry=registry,
    )

    assert not manager.is_enabled()

    manager.set_enabled(True)
    assert manager.is_enabled()
    assert registry.command == f'"{current_executable.resolve()}" --background'
