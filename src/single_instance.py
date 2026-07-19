"""同一 Windows 用户会话中的 PastePeek 单实例协调。"""

import hashlib
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QIODevice, QLockFile, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

_ACTIVATE_COMMAND = b"SHOW\n"
_ACKNOWLEDGEMENT = b"OK\n"
# 给便携 EXE 完成 HUD 与托盘初始化留出响应窗口。
_CONNECT_TIMEOUT_MS = 2_000


def default_server_name() -> str:
    """生成不泄露用户路径的会话级服务名。"""
    identity = f"{Path.home()}|{os.environ.get('SESSIONNAME', '')}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"PastePeek-{digest}"


class SingleInstanceGuard(QObject):
    """取得主实例所有权，或通知已经运行的实例显示 HUD。"""

    activation_requested = Signal()

    def __init__(
        self,
        server_name: str | None = None,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._server_name = server_name or default_server_name()
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._accept_connections)
        self._owns_server = False
        lock_digest = hashlib.sha256(self._server_name.encode("utf-8")).hexdigest()[:20]
        self._lock = QLockFile(str(Path(tempfile.gettempdir()) / f"{lock_digest}.lock"))
        self._last_error = ""

    def acquire(self, *, activate_existing: bool = True) -> bool:
        """主实例返回真；通知已有实例后返回假。"""
        if self._owns_server:
            return True
        if self._lock.tryLock(0):
            self._start_server()
            self._owns_server = True
            return True
        if activate_existing and self._notify_existing_instance():
            return False

        # 无法连接主实例时，尝试清理异常退出留下的锁。
        if self._lock.removeStaleLockFile() and self._lock.tryLock(0):
            self._start_server()
            self._owns_server = True
            return True
        if not activate_existing:
            return False
        if self._notify_existing_instance():
            return False
        detail = f"：{self._last_error}" if self._last_error else ""
        raise RuntimeError(f"无法建立 PastePeek 单实例通信{detail}")

    def close(self) -> None:
        """释放主实例端点。"""
        if self._server.isListening():
            self._server.close()
        if self._owns_server:
            QLocalServer.removeServer(self._server_name)
        self._owns_server = False
        if self._lock.isLocked():
            self._lock.unlock()

    def _start_server(self) -> None:
        """在取得进程锁后建立激活通信端点。"""
        QLocalServer.removeServer(self._server_name)
        if not self._server.listen(self._server_name):
            self._lock.unlock()
            raise RuntimeError("无法监听 PastePeek 单实例通信")

    def _notify_existing_instance(self) -> bool:
        """发送显示请求，并等待主实例确认接收。"""
        socket = QLocalSocket()
        socket.connectToServer(
            self._server_name,
            QIODevice.OpenModeFlag.ReadWrite,
        )
        if not socket.waitForConnected(_CONNECT_TIMEOUT_MS):
            self._last_error = socket.errorString()
            socket.abort()
            return False
        if socket.write(_ACTIVATE_COMMAND) != len(_ACTIVATE_COMMAND):
            self._last_error = socket.errorString()
            socket.abort()
            return False
        socket.flush()
        if socket.bytesToWrite() and not socket.waitForBytesWritten(_CONNECT_TIMEOUT_MS):
            self._last_error = socket.errorString()
            socket.abort()
            return False
        if not socket.waitForReadyRead(_CONNECT_TIMEOUT_MS):
            self._last_error = socket.errorString()
            socket.abort()
            return False
        acknowledged = bytes(socket.readAll()).strip() == _ACKNOWLEDGEMENT.strip()
        socket.disconnectFromServer()
        return acknowledged

    def _accept_connections(self) -> None:
        """读取所有等待中的激活请求。"""
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue
            socket.readyRead.connect(
                lambda connected_socket=socket: self._read_command(connected_socket)
            )
            if socket.bytesAvailable():
                self._read_command(socket)

    def _read_command(self, socket: QLocalSocket) -> None:
        """把有效命令转换成公开激活信号，并确认接收。"""
        command = bytes(socket.readAll()).strip()
        if command != _ACTIVATE_COMMAND.strip():
            return
        self.activation_requested.emit()
        socket.write(_ACKNOWLEDGEMENT)
        socket.flush()
        if socket.bytesToWrite():
            socket.waitForBytesWritten(_CONNECT_TIMEOUT_MS)
        socket.disconnectFromServer()
