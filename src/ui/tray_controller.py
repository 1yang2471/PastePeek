"""PastePeek 系统托盘控制器。"""

from PySide6.QtCore import QObject, QSignalBlocker, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from src.i18n import DEFAULT_LANGUAGE, normalize_language, translate
from src.startup import StartupManager, StartupUnsupportedError


class TrayController(QObject):
    """通过系统托盘控制 HUD 的可见状态。"""

    exit_requested = Signal()
    language_selected = Signal(str)

    def __init__(
        self,
        hud: QWidget,
        icon: QIcon,
        *,
        tray_available: bool | None = None,
        startup_manager: StartupManager | None = None,
        language: str = DEFAULT_LANGUAGE,
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
        self._language = normalize_language(language)
        self._tray: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None
        self._toggle_action: QAction | None = None
        self._startup_action: QAction | None = None
        self._language_menu: QMenu | None = None
        self._language_menu_action: QAction | None = None
        self._language_actions: dict[str, QAction] = {}
        self._exit_action: QAction | None = None
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
        # QSystemTrayIcon 不保证持有 Python 包装对象，控制器必须保留根菜单。
        self._menu = menu
        self._toggle_action = QAction(menu)
        self._toggle_action.triggered.connect(self.toggle_hud)
        menu.addAction(self._toggle_action)
        self._sync_toggle_label()
        if self._startup_manager is not None:
            self._startup_action = QAction(menu)
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

        # 语言菜单只负责发出选择信号，真正的持久化由 HUD 统一处理。
        self._language_menu = menu.addMenu(translate("language_menu", self._language))
        # PySide 需要同时持有子菜单对应的 QAction 包装对象。
        self._language_menu_action = self._language_menu.menuAction()
        self._language_actions = {}
        for language, key in (("zh-CN", "language_zh"), ("en-US", "language_en")):
            action = self._language_menu.addAction(translate(key, self._language))
            action.setCheckable(True)
            action.triggered.connect(
                lambda _checked=False, value=language: self._select_language(value)
            )
            self._language_actions[language] = action

        menu.addSeparator()
        self._exit_action = QAction(menu)
        self._exit_action.triggered.connect(
            lambda _checked=False: self.exit_requested.emit()
        )
        menu.addAction(self._exit_action)
        self._refresh_menu_labels()
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
        self._menu = None
        self._toggle_action = None
        self._startup_action = None
        self._language_menu = None
        self._language_menu_action = None
        self._language_actions = {}
        self._exit_action = None
        self._disconnect_hud_close()

    def language(self) -> str:
        """返回托盘当前语言。"""
        return self._language

    def set_language(self, language: str) -> str:
        """刷新现有托盘菜单文案并返回归一化语言。"""
        self._language = normalize_language(language)
        self._refresh_menu_labels()
        return self._language

    def _select_language(self, language: str) -> None:
        """处理菜单选择，并把语言切换交给 HUD 统一持久化。"""
        normalized = self.set_language(language)
        self.language_selected.emit(normalized)

    def _refresh_menu_labels(self) -> None:
        """集中刷新菜单标题、操作标签和当前语言勾选状态。"""
        self._sync_toggle_label()
        if self._startup_action is not None:
            self._startup_action.setText(translate("tray_startup", self._language))
        if self._exit_action is not None:
            self._exit_action.setText(translate("tray_exit", self._language))
        if self._language_menu is not None:
            self._language_menu.setTitle(translate("language_menu", self._language))
        for language, action in self._language_actions.items():
            key = "language_zh" if language == "zh-CN" else "language_en"
            action.setText(translate(key, self._language))
            action.setChecked(language == self._language)

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
        key = "tray_hide" if self._hud.isVisible() else "tray_show"
        self._toggle_action.setText(translate(key, self._language))

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
        if isinstance(error, StartupUnsupportedError):
            message = translate("startup_unsupported", self._language)
        elif self._language == "en-US":
            # Windows 本地异常文本受系统显示语言影响，英文模式不混入它。
            message = translate("startup_error", self._language)
        else:
            message = translate("startup_error", self._language, error=error)
        self._tray.showMessage(
            "PastePeek",
            message,
            QSystemTrayIcon.MessageIcon.Warning,
            5000,
        )
