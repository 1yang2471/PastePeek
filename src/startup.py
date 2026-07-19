"""PastePeek 当前用户开机启动管理。"""

import winreg
from pathlib import Path
from typing import Protocol

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "PastePeek"


class RunRegistry(Protocol):
    """当前用户 Run 注册值的最小系统边界。"""

    def read(self) -> str | None:
        """读取当前命令；不存在时返回空。"""

    def write(self, command: str) -> None:
        """写入当前命令。"""

    def delete(self) -> None:
        """删除当前命令；不存在时正常完成。"""


class WindowsRunRegistry:
    """读写当前 Windows 用户的单个 Run 注册值。"""

    def __init__(
        self,
        *,
        key_path: str = _RUN_KEY,
        value_name: str = _VALUE_NAME,
    ) -> None:
        self._key_path = key_path
        self._value_name = value_name

    def read(self) -> str | None:
        """读取注册命令；键或值不存在时返回空。"""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self._key_path,
                0,
                winreg.KEY_QUERY_VALUE,
            ) as key:
                command, _value_type = winreg.QueryValueEx(key, self._value_name)
        except FileNotFoundError:
            return None
        return str(command)

    def write(self, command: str) -> None:
        """写入当前用户的字符串启动命令。"""
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            self._key_path,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, self._value_name, 0, winreg.REG_SZ, command)

    def delete(self) -> None:
        """幂等删除 PastePeek 自己的注册值。"""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self._key_path,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, self._value_name)
        except FileNotFoundError:
            return


class StartupUnsupportedError(RuntimeError):
    """当前运行方式不支持注册正式开机启动项。"""


class StartupManager:
    """管理当前便携 EXE 对应的开机启动状态。"""

    def __init__(
        self,
        executable: Path,
        *,
        frozen: bool,
        registry: RunRegistry,
    ) -> None:
        self._executable = executable.resolve()
        self._frozen = frozen
        self._registry = registry

    @property
    def supported(self) -> bool:
        """只有打包后的 Windows EXE 可以注册。"""
        return self._frozen and self._executable.suffix.casefold() == ".exe"

    def is_enabled(self) -> bool:
        """注册命令与当前 EXE 完全匹配时才视为启用。"""
        if not self.supported:
            return False
        command = self._registry.read()
        return bool(command) and command.strip().casefold() == self._command().casefold()

    def set_enabled(self, enabled: bool) -> None:
        """启用或禁用当前用户的开机启动。"""
        if enabled:
            if not self.supported:
                raise StartupUnsupportedError("仅便携 EXE 支持开机启动")
            self._registry.write(self._command())
        else:
            self._registry.delete()

    def _command(self) -> str:
        """生成 Windows Run 使用的静默启动命令。"""
        return f'"{self._executable}" --background'
