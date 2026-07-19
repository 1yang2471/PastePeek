"""PastePeek 系统托盘控制器。"""

from PySide6.QtCore import QObject, QSignalBlocker, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from src.startup import StartupManager


class TrayController(QObject):
    """通过系统托盘控制 HUD 的可见状态。"""

    exit_requested = Signal()

    def __init__(
        self,
        hud: QWidget,
        icon: QIcon,
        *,
        tray_available: bool | None = None,
        startup_manager: StartupManager | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._hud = hud
        self._icon = icon
        self._tray_available = (
            QSystemTrayIcon.isSystemTrayAvailable()
            if tray_available is None
            else tray_available
        )
        self._startup_manager = startup_manager
        self._tray: QSystemTrayIcon | None = None
        self._toggle_action: QAction | None = None
        self._startup_action: QAction | None = None
        self._hud_close_connected = False

    def start(self) -> None:
        """在系统托盘可用时创建并显示托盘入口。"""
        self._connect_hud_close()
        if not self._tray_available:
            self.show_hud()
            return
        if self._tray is not None:
            return

        self._tray = QSystemTrayIcon(self._icon, self)
        startup_error: OSError | None = None
        menu = QMenu()
        self._toggle_action = QAction("隐藏 PastePeek", menu)
        self._toggle_action.triggered.connect(self.toggle_hud)
        menu.addAction(self._toggle_action)
        self._sync_toggle_label()
        if self._startup_manager is not None:
            self._startup_action = QAction("开机启动", menu)
            self._startup_action.setCheckable(True)
            self._startup_action.setEnabled(self._startup_manager.supported)
            try:
                self._startup_action.setChecked(self._startup_manager.is_enabled())
            except OSError as error:
                self._startup_action.setChecked(False)
                startup_error = error
            self._startup_action.toggled.connect(self._set_startup_enabled)
            menu.addAction(self._startup_action)
            menu.aboutToShow.connect(self._refresh_startup_state)
        menu.addSeparator()
        exit_action = QAction("退出 PastePeek", menu)
        exit_action.triggered.connect(lambda _checked=False: self.exit_requested.emit())
        menu.addAction(exit_action)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.setToolTip("PastePeek")
        self._tray.show()
        if startup_error is not None:
            self._show_startup_error(startup_error)

    def stop(self) -> None:
        """移除托盘入口。"""
        if self._tray is not None:
            self._tray.hide()
            self._tray.deleteLater()
        self._tray = None
        self._toggle_action = None
        self._startup_action = None
        self._disconnect_hud_close()

    def toggle_hud(self) -> None:
        """在显示和隐藏 HUD 之间切换。"""
        if self._hud.isVisible():
            self._hud.hide()
            self._sync_toggle_label()
        else:
            self.show_hud()

    def show_hud(self) -> None:
        """幂等地恢复并显示 HUD。"""
        show_from_tray = getattr(self._hud, "show_from_tray", None)
        if callable(show_from_tray):
            show_from_tray()
        else:
            self._hud.show()
        self._sync_toggle_label()

    def handle_hud_close(self) -> None:
        """托盘可用时隐藏 HUD，否则请求退出应用。"""
        if self._tray_available:
            self._hud.hide()
            self._sync_toggle_label()
        else:
            self.exit_requested.emit()

    def _sync_toggle_label(self) -> None:
        """让菜单命令描述下一次操作。"""
        if self._toggle_action is None:
            return
        text = "隐藏 PastePeek" if self._hud.isVisible() else "显示 PastePeek"
        self._toggle_action.setText(text)

    def _connect_hud_close(self) -> None:
        """连接 HUD 的关闭请求。"""
        if self._hud_close_connected:
            return
        close_requested = getattr(self._hud, "close_requested", None)
        if close_requested is not None:
            close_requested.connect(self.handle_hud_close)
            self._hud_close_connected = True

    def _disconnect_hud_close(self) -> None:
        """停止时解除 HUD 的关闭请求连接。"""
        if not self._hud_close_connected:
            return
        close_requested = getattr(self._hud, "close_requested", None)
        if close_requested is not None:
            close_requested.disconnect(self.handle_hud_close)
        self._hud_close_connected = False

    def _on_tray_activated(
        self, reason: QSystemTrayIcon.ActivationReason
    ) -> None:
        """普通单击托盘图标时切换 HUD。"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_hud()

    def _refresh_startup_state(self) -> None:
        """打开菜单前同步当前开机启动真实状态。"""
        if self._startup_manager is None or self._startup_action is None:
            return
        try:
            enabled = self._startup_manager.is_enabled()
        except (OSError, RuntimeError) as error:
            self._show_startup_error(error)
            return
        blocker = QSignalBlocker(self._startup_action)
        self._startup_action.setChecked(enabled)
        del blocker

    def _set_startup_enabled(self, enabled: bool) -> None:
        """应用托盘开关，并在失败时恢复真实状态。"""
        if self._startup_manager is None or self._startup_action is None:
            return
        try:
            self._startup_manager.set_enabled(enabled)
        except (OSError, RuntimeError) as error:
            blocker = QSignalBlocker(self._startup_action)
            self._startup_action.setChecked(not enabled)
            del blocker
            self._show_startup_error(error)

    def _show_startup_error(self, error: OSError | RuntimeError) -> None:
        """通过托盘显示不阻塞应用的本地错误。"""
        if self._tray is None:
            return
        self._tray.showMessage(
            "PastePeek",
            f"开机启动设置失败：{error}",
            QSystemTrayIcon.MessageIcon.Warning,
            5000,
        )
