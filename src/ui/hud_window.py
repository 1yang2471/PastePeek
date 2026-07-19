"""HudWindow — clipboard outcome predictor layer.

2-layer interaction model:
  Layer 1 (idle): compact 1-line chip showing content type → target + risk dot.
  Layer 2 (expanded): target icon bar, preview placeholder, conclusion,
                      2-3 risk items, primary action + "more actions" menu.

Monochrome pill-shaped HUD (bottom-right corner).
Supports minimize, close, drag, first-run tip, success/error toasts,
and position memory across screens.
"""

import json
import os
from math import ceil

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QEnterEvent, QFont, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.explainer.preview_renderer import ClipboardContent, PreviewRenderer
from src.models.types import CONTENT_TYPES, TARGET_LABELS, AppOutput
from src.ui.icons import lucide_icon
from src.usage.tracker import UsageTracker

# ── Dimensions ────────────────────────────────────────────────────────
_W          = 300          # expanded width (configurable)
_MIN_WIDTH  = 300
_MAX_WIDTH  = 640
_W_MIN      = 36
_H_MIN      = 18
_H_IDLE     = 36
_H_TIP      = 28           # first-run tip banner height
_H_ICON_BAR = 32
_H_PREVIEW_MIN = 56
_H_PREVIEW  = 120          # max preview height
_H_ACTION   = 34
_H_ITEM     = 18
_H_CONCLUSION = 18

# ── Palette ───────────────────────────────────────────────────────────
_CLR_BG        = "#ffffff"
_CLR_SURFACE   = "#F6F8FA"
_CLR_BORDER    = "#D8DEE6"
_CLR_BORDER_HV = "#95A1B2"
_CLR_TEXT      = "#19232D"
_CLR_TEXT_DIM  = "#667085"
_CLR_PULSE     = "#0F766E"
_CLR_BREAK     = "#526071"
_CLR_BTN       = "#98A2B3"
_CLR_BTN_HV    = "#475467"
_CLR_MIN_DOT   = "#98A2B3"
_CLR_SUCCESS   = "#13795B"
_CLR_SUCCESS_BG = "#E7F5F0"
_CLR_ERROR      = "#B42318"
_CLR_ERROR_BG   = "#FEECEB"
_CLR_TIP_BG    = "#F0F7F5"
_CLR_TIP_TEXT  = "#365F58"
_CLR_ACCENT    = "#0F766E"
_CLR_ACCENT_HV = "#0B5F59"

_RISK = {
    "high":   ("#B42318", "●"),
    "medium": ("#A15C00", "●"),
    "low":    ("#13795B", "●"),
    "none":   ("#667085", "●"),
}

_RISK_BADGE = {
    "high": ("高风险", "#B42318", "#FEECEB"),
    "medium": ("中风险", "#A15C00", "#FFF3DC"),
    "low": ("低风险", "#13795B", "#E7F5F0"),
    "none": ("无明显风险", "#667085", "#EEF1F4"),
}

# Short labels for the horizontal icon bar
_ICON_LABEL = {
    "word":           "Word",
    "chrome":         "浏览器",
    "code_editor":    "代码",
    "terminal":       "终端",
    "markdown_editor": "MD",
}

_TARGET_ICON = {
    "word": "file-text",
    "chrome": "globe",
    "code_editor": "code",
    "terminal": "terminal",
    "markdown_editor": "file-text",
}

_ACTION_ICON = {
    "strip_formats": "eraser",
    "clean_url": "link",
    "merge_lines": "rows",
}

# Full target label for the idle line
_TARGET_LABEL = {
    "word":           "Word",
    "chrome":         "Chrome",
    "code_editor":    "代码编辑器",
    "terminal":       "终端",
    "chat_app":       "聊天应用",
    "markdown_editor": "Markdown",
    "spreadsheet":    "表格",
    "presentation":   "演示",
    "unknown":        "",
}

_FONT_FAMILY = "Segoe UI"
_MAX_BREAKDOWN_ITEMS = 3

_POS_CONFIG_DIR  = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "PastePeek")
_POS_CONFIG_PATH = os.path.join(_POS_CONFIG_DIR, "config.json")

# Targets shown as fixed icons; the rest live in the "more" menu.
_COMMON_TARGETS = ["word", "chrome", "code_editor", "terminal", "markdown_editor"]


class TargetIconBar(QFrame):
    """Horizontal bar of target-application icons/buttons.

    Shows the five common targets directly; remaining targets are tucked into
    a "更多" dropdown. Emits ``target_selected`` when the user clicks a target.
    """

    target_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._current_target = ""
        self._buttons: dict[str, QPushButton] = {}
        self._more_btn: QPushButton | None = None
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("TargetIconBar")
        self.setStyleSheet("QFrame#TargetIconBar { background: transparent; border: none; }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        for target in _COMMON_TARGETS:
            btn = self._make_icon_button(target, _ICON_LABEL.get(target, target))
            layout.addWidget(btn)
            self._buttons[target] = btn

        layout.addStretch()

        self._more_btn = QPushButton("…")
        self._more_btn.setFixedSize(28, 26)
        self._more_btn.setToolTip("更多目标")
        self._more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._more_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._more_btn.setFont(self._font(12, False))
        self._update_button_appearance(self._more_btn, False)
        self._more_btn.clicked.connect(self._show_more_menu)
        layout.addWidget(self._more_btn)

    def _make_icon_button(self, target: str, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setFixedSize(58, 26)
        btn.setIcon(lucide_icon(_TARGET_ICON[target], _CLR_TEXT, 12))
        btn.setIconSize(QSize(12, 12))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setFont(self._font(9, False))
        btn.setToolTip(TARGET_LABELS.get(target, label))
        btn.clicked.connect(lambda _checked=False, t=target: self._select(t))
        self._update_button_appearance(btn, False)
        return btn

    def set_current_target(self, target: str):
        """Highlight the given target and update the "more" button state."""
        self._current_target = target or ""
        for t, btn in self._buttons.items():
            selected = t == self._current_target
            btn.setChecked(selected)
            btn.setIcon(
                lucide_icon(
                    _TARGET_ICON[t],
                    "#ffffff" if selected else _CLR_TEXT,
                    12,
                )
            )
            self._update_button_appearance(btn, selected)
        # Highlight the "more" button if the current target is hidden inside it.
        self._update_button_appearance(
            self._more_btn,
            self._current_target in self._remaining_targets(),
        )

    def resizeEvent(self, event):
        """在紧凑宽度下隐藏次要目标，避免按钮被压缩。"""
        super().resizeEvent(event)
        markdown_button = self._buttons.get("markdown_editor")
        if markdown_button is not None:
            markdown_button.setVisible(self.width() >= 340)

    def select_auto(self):
        """清除手动场景选择并恢复自动目标检测。"""
        if not self._current_target:
            return
        self.set_current_target("")
        self.target_selected.emit("")

    def _select(self, target: str):
        if target == self._current_target:
            return
        self.set_current_target(target)
        self.target_selected.emit(target)

    def _update_button_appearance(self, btn: QPushButton, selected: bool):
        if selected:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {_CLR_ACCENT};
                    color: #ffffff;
                    border: 1px solid {_CLR_ACCENT};
                    border-radius: 4px;
                    font-family: "{_FONT_FAMILY}";
                    font-size: 9pt;
                    padding: 0 2px;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {_CLR_BG};
                    color: {_CLR_TEXT};
                    border: 1px solid {_CLR_BORDER};
                    border-radius: 4px;
                    font-family: "{_FONT_FAMILY}";
                    font-size: 9pt;
                    padding: 0 2px;
                }}
                QPushButton:hover {{
                    background-color: {_CLR_SURFACE};
                    border-color: {_CLR_BTN_HV};
                    color: {_CLR_TEXT};
                }}
            """)

    def current_target(self) -> str:
        """Return the currently selected target key."""
        return self._current_target

    def minimumSizeHint(self) -> QSize:
        """以 300px HUD 的紧凑布局作为场景条最小宽度声明。"""
        hint = super().minimumSizeHint()
        compact_width = _MIN_WIDTH - 24
        return QSize(min(hint.width(), compact_width), hint.height())

    def _remaining_targets(self) -> list[str]:
        return [
            t for t in TARGET_LABELS
            if t not in _COMMON_TARGETS and t != "unknown"
        ]

    def _show_more_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {_CLR_BG};
                border: 1px solid {_CLR_BORDER};
                border-radius: 4px;
                padding: 2px;
            }}
            QMenu::item {{
                padding: 3px 16px;
                font-family: "{_FONT_FAMILY}";
                font-size: 9pt;
                color: {_CLR_TEXT};
            }}
            QMenu::item:selected {{ background-color: #f0f0f0; }}
            QMenu::separator {{
                height: 1px; background: {_CLR_BORDER}; margin: 2px 8px;
            }}
        """)
        auto_action = menu.addAction("自动检测")
        auto_action.setCheckable(True)
        auto_action.setChecked(not self._current_target)
        auto_action.triggered.connect(
            lambda _checked=False: self.select_auto()
        )
        menu.addSeparator()
        for target in self._remaining_targets():
            label = TARGET_LABELS.get(target, target)
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(target == self._current_target)
            action.triggered.connect(lambda _checked=False, t=target: self._select(t))

        if self._more_btn is not None:
            pos = self._more_btn.mapToGlobal(QPoint(0, self._more_btn.height()))
            menu.exec(pos)

    def select_next(self):
        order = list(_COMMON_TARGETS) + self._remaining_targets()
        if not order:
            return
        try:
            idx = order.index(self._current_target)
        except ValueError:
            idx = -1
        self._select(order[(idx + 1) % len(order)])

    def select_previous(self):
        order = list(_COMMON_TARGETS) + self._remaining_targets()
        if not order:
            return
        try:
            idx = order.index(self._current_target)
        except ValueError:
            idx = 0
        self._select(order[(idx - 1) % len(order)])

    @staticmethod
    def _font(size: float, bold: bool) -> QFont:
        f = QFont(_FONT_FAMILY, round(size))
        f.setBold(bold)
        return f


class HudWindow(QFrame):
    """Clipboard outcome predictor — never interrupts, always available."""

    target_override_requested = Signal(str)   # user selected target from icon bar
    action_triggered = Signal(str)            # user clicked an action button
    close_requested = Signal()                # 用户请求关闭 HUD

    def __init__(self, parent: QWidget | None = None, tracker: UsageTracker | None = None):
        super().__init__(parent)
        self.setObjectName("HudWindow")

        self._output: AppOutput | None = None
        self._current_text = ""
        self._hovered = False
        self._expanded = False
        self._minimized = False
        self._dragging = False
        self._drag_offset: QPoint | None = None
        self._tracker = tracker
        self._viewed_logged = False
        self._first_run = True
        self._tip_frame: QFrame | None = None
        self._width = _W
        self._config: dict = {}
        self._current_action = ""
        self._error_active = False
        self._preview_height = _H_PREVIEW_MIN
        self._preview_renderer = PreviewRenderer()

        self._setup_window()
        self._setup_ui()

    # ── Window ──────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowTitle("PastePeek")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(_W, _H_IDLE)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)

        self._apply_style()

    def _apply_style(self):
        if self._error_active:
            self.setStyleSheet(
                f"#HudWindow {{ background-color: {_CLR_ERROR_BG}; "
                f"border: 1px solid {_CLR_ERROR}; border-radius: 8px; }}"
            )
            return
        border = _CLR_BORDER_HV if self._hovered else _CLR_BORDER
        self.setStyleSheet(f"""
            #HudWindow {{
                background-color: {_CLR_BG};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)

    # ── Layout ──────────────────────────────────────────────────────

    def _setup_ui(self):
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(12, 6, 12, 6)
        self._outer.setSpacing(4)

        # ── Layer 1: idle header row ───────────────────────────────
        r1 = QHBoxLayout()
        r1.setSpacing(6)
        r1.setContentsMargins(0, 0, 0, 0)

        self._dot = QLabel("")
        self._dot.setFixedWidth(12)
        self._dot.setFont(self._font(9, True))
        self._dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r1.addWidget(self._dot)

        self._tag = QLabel("PastePeek")
        self._tag.setFont(self._font(10, False))
        r1.addWidget(self._tag)

        self._target_lbl = QLabel("")
        self._target_lbl.setFont(self._font(9, False))
        self._target_lbl.setStyleSheet(f"color: {_CLR_TEXT_DIM};")
        r1.addWidget(self._target_lbl)

        r1.addStretch()

        self._risk_badge = QLabel("")
        self._risk_badge.setFont(self._font(9, False))
        self._risk_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r1.addWidget(self._risk_badge)

        self._min_btn = QPushButton()
        self._min_btn.setObjectName("MinimizeButton")
        self._min_btn.setFixedSize(24, 24)
        self._min_btn.setIcon(lucide_icon("minus", _CLR_BTN_HV, 14))
        self._min_btn.setIconSize(QSize(14, 14))
        self._min_btn.setToolTip("最小化 HUD")
        self._min_btn.setAccessibleName("最小化 HUD")
        self._min_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._min_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._min_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                border-radius: 4px;
                padding: 0;
            }}
            QPushButton:hover {{ background-color: {_CLR_SURFACE}; }}
        """)
        self._min_btn.clicked.connect(self._toggle_minimize)
        self._min_btn.setVisible(False)
        r1.addWidget(self._min_btn)

        self._close_btn = QPushButton()
        self._close_btn.setObjectName("HideButton")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setIcon(lucide_icon("x", _CLR_BTN_HV, 14))
        self._close_btn.setIconSize(QSize(14, 14))
        self._close_btn.setToolTip("隐藏 HUD，继续监听")
        self._close_btn.setAccessibleName("隐藏 HUD")
        self._close_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                border-radius: 4px;
                padding: 0;
            }}
            QPushButton:hover {{ background-color: {_CLR_ERROR_BG}; }}
        """)
        self._close_btn.clicked.connect(self._quit_app)
        self._close_btn.setVisible(False)
        r1.addWidget(self._close_btn)

        self._outer.addLayout(r1)

        # ── First-run tip banner ───────────────────────────────────
        self._setup_tip_frame()

        # ── Layer 2: expanded panel ────────────────────────────────
        self._expanded_panel = QFrame(self)
        self._expanded_panel.setObjectName("ExpandedPanel")
        self._expanded_panel.setStyleSheet("QFrame#ExpandedPanel { background: transparent; border: none; }")
        expanded_layout = QVBoxLayout(self._expanded_panel)
        expanded_layout.setContentsMargins(0, 0, 0, 0)
        expanded_layout.setSpacing(4)

        # Target icon bar
        self._icon_bar = TargetIconBar(self._expanded_panel)
        self._icon_bar.target_selected.connect(self._on_target_selected)
        expanded_layout.addWidget(self._icon_bar)

        # Preview placeholder (scrollable, no visible scrollbar)
        self._preview = QTextEdit(self._expanded_panel)
        self._preview.setObjectName("PreviewArea")
        self._preview.setReadOnly(True)
        self._preview.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._preview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._preview.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._preview.setMaximumHeight(_H_PREVIEW)
        self._preview.setStyleSheet(f"""
            QTextEdit#PreviewArea {{
                background-color: {_CLR_SURFACE};
                border: 1px solid {_CLR_BORDER};
                border-radius: 4px;
                color: {_CLR_TEXT_DIM};
                font-family: "Consolas", "{_FONT_FAMILY}";
                font-size: 9pt;
                padding: 4px;
            }}
        """)
        expanded_layout.addWidget(self._preview)

        # Conclusion line
        self._conclusion = QLabel("")
        self._conclusion.setFont(self._font(10, True))
        self._conclusion.setWordWrap(True)
        self._conclusion.setStyleSheet(f"color: {_CLR_TEXT}; padding-left: 2px;")
        expanded_layout.addWidget(self._conclusion)

        # Risk items
        self._breakdown_labels: list[QLabel] = []
        for _ in range(_MAX_BREAKDOWN_ITEMS):
            lbl = QLabel("")
            lbl.setFont(self._font(9, False))
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {_CLR_BREAK}; padding-left: 8px;")
            self._breakdown_labels.append(lbl)
            expanded_layout.addWidget(lbl)

        # Action row
        self._action_row = QHBoxLayout()
        self._action_row.setSpacing(6)
        self._action_row.setContentsMargins(0, 0, 0, 0)

        self._action_status = QLabel("当前内容无需处理")
        self._action_status.setFont(self._font(9, False))
        self._action_status.setStyleSheet(
            f"color: {_CLR_TEXT_DIM}; padding-left: 2px;"
        )
        self._action_status.setVisible(False)
        self._action_row.addWidget(self._action_status)

        self._action_btn = QPushButton("")
        self._action_btn.setFixedHeight(28)
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_CLR_ACCENT}; border: 1px solid {_CLR_ACCENT};
                border-radius: 4px; color: #ffffff;
                font-family: "{_FONT_FAMILY}"; font-size: 9pt;
                padding: 2px 10px;
            }}
            QPushButton:hover {{
                background-color: {_CLR_ACCENT_HV}; border-color: {_CLR_ACCENT_HV};
            }}
        """)
        self._action_btn.clicked.connect(self._on_action_clicked)
        self._action_row.addWidget(self._action_btn)

        self._more_actions_btn = QPushButton("其他操作")
        self._more_actions_btn.setFixedHeight(28)
        self._more_actions_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._more_actions_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._more_actions_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid {_CLR_BORDER};
                background-color: transparent;
                border-radius: 4px; color: {_CLR_TEXT_DIM};
                font-family: "{_FONT_FAMILY}"; font-size: 9pt;
                padding: 2px 6px;
            }}
            QPushButton:hover {{
                border-color: {_CLR_BTN_HV}; color: {_CLR_TEXT};
            }}
        """)
        self._more_actions_btn.clicked.connect(self._show_more_actions_menu)
        self._more_actions_btn.setVisible(False)
        self._action_row.addWidget(self._more_actions_btn)

        self._action_row.addStretch()
        expanded_layout.addLayout(self._action_row)

        self._outer.addWidget(self._expanded_panel)
        self._expanded_panel.setVisible(False)

        self._outer.addStretch()

        # ── Minimized dot ──────────────────────────────────────────
        self._min_label = QLabel("···", self)
        self._min_label.setFont(self._font(9, True))
        self._min_label.setStyleSheet(
            f"color: {_CLR_MIN_DOT}; background: transparent;"
        )
        self._min_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._min_label.setVisible(False)

    # ── Position ────────────────────────────────────────────────────

    def show_at_bottom_right(self, *, visible: bool = True):
        """Position HUD at bottom-right of primary screen, or last saved position.

        Multi-screen aware: validates saved (x, y) against ALL currently
        connected screens.  If the saved position is off-screen (e.g. a
        secondary monitor was disconnected), resets to the primary screen
        bottom-right corner.
        """
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication

        self._config = self._load_config()
        sx, sy = self._config.get("x"), self._config.get("y")
        self._first_run = self._config.get("first_run", True)
        self._expanded = self._config.get("default_expand", False)
        self._width = self._config.get("ui_width", _W)
        self.setFixedSize(self._width, _H_IDLE)
        self._update_preview_height()

        # 左侧或上方副屏使用负坐标，是否有效只由当前屏幕几何范围决定。
        if sx is not None and sy is not None:
            for scr in QGuiApplication.screens():
                g = scr.availableGeometry()
                if (g.x() <= sx <= g.right() - self._width and
                        g.y() <= sy <= g.bottom() - _H_MIN):
                    self.move(sx, sy)
                    if visible:
                        self.show()
                    self._show_tip_if_first_run()
                    self._apply_expand()
                    return

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.right() - self._width - 16,
                geo.bottom() - _H_IDLE - 16,
            )
        if visible:
            self.show()
        self._show_tip_if_first_run()
        self._apply_expand()

    # ── Minimize / Restore ─────────────────────────────────────────

    def _toggle_minimize(self):
        if self._minimized:
            self._restore()
        else:
            self._minimize()

    def _quit_app(self):
        self.close_requested.emit()

    # ── First-Run Guidance ─────────────────────────────────────────

    def _setup_tip_frame(self):
        """Create the first-run tip banner (hidden by default)."""
        self._tip_frame = QFrame(self)
        self._tip_frame.setStyleSheet(
            f"QFrame {{ background-color: {_CLR_TIP_BG}; border-radius: 4px; padding: 0px; }}"
        )
        tip_layout = QHBoxLayout(self._tip_frame)
        tip_layout.setContentsMargins(6, 2, 6, 2)
        tip_layout.setSpacing(4)

        self._tip_label = QLabel("提示：已就绪，等待剪贴板内容")
        self._tip_label.setFont(self._font(9, False))
        self._tip_label.setStyleSheet(f"color: {_CLR_TIP_TEXT}; background: transparent;")
        tip_layout.addWidget(self._tip_label)

        tip_layout.addStretch()

        self._tip_close_btn = QLabel("\u00d7")
        self._tip_close_btn.setFont(self._font(11, True))
        self._tip_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tip_close_btn.setStyleSheet(
            f"color: {_CLR_TIP_TEXT}; background: transparent; padding: 0px 4px;"
        )
        self._tip_close_btn.mousePressEvent = self._on_tip_close
        tip_layout.addWidget(self._tip_close_btn)

        self._tip_frame.setVisible(False)
        self._outer.addWidget(self._tip_frame)

    def _show_tip_if_first_run(self):
        """Show tip banner if this is the first run."""
        if self._first_run and self._tip_frame is not None:
            self._tip_frame.setVisible(True)
            self.setFixedSize(self._width, _H_IDLE + _H_TIP)

    def _on_tip_close(self, event):
        """Handle click on tip [×] close button."""
        self._dismiss_tip()

    def _dismiss_tip(self):
        """Hide the tip banner and persist first_run = False."""
        self._first_run = False
        if self._tip_frame is not None:
            self._tip_frame.setVisible(False)
        if not self._expanded:
            self.setFixedSize(self._width, _H_IDLE)
        self._save_state()

    # ── Config Management ─────────────────────────────────────────────

    def _save_state(self):
        """Persist current window state and user preferences."""
        pos = self.pos()
        config = {
            "x": pos.x(),
            "y": pos.y(),
            "first_run": self._first_run,
            "last_target": self._config.get("last_target", ""),
            "default_expand": self._config.get("default_expand", False),
            "default_target": self._config.get("default_target", "word"),
            "ui_width": self._width,
            "usage_tracking_enabled": self._config.get("usage_tracking_enabled", False),
        }
        self._save_config(config)

    def _save_config(self, config: dict):
        """Save full configuration dict to config.json."""
        try:
            os.makedirs(_POS_CONFIG_DIR, exist_ok=True)
            self._config.update(config)
            with open(_POS_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._config, f)
        except Exception:
            pass  # never block UI for config write failures

    @staticmethod
    def _load_config() -> dict:
        """Load full configuration dict from config.json.

        Returns:
            dict with position, first_run, expanded, last_target, and defaults.
        """
        defaults = {
            "x": None,
            "y": None,
            "first_run": True,
            "last_target": "",
            "default_expand": False,
            "default_target": "word",
            "ui_width": _W,
            "usage_tracking_enabled": False,
        }
        try:
            if not os.path.exists(_POS_CONFIG_PATH):
                return dict(defaults)
            with open(_POS_CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            result = dict(defaults)
            for key in defaults:
                if key in data:
                    expected_type = type(defaults[key])
                    if expected_type is bool:
                        result[key] = bool(data[key])
                    elif expected_type is int:
                        result[key] = int(data[key])
                    elif expected_type is str:
                        result[key] = str(data[key])
                    else:
                        result[key] = data[key]
            result["ui_width"] = max(
                _MIN_WIDTH, min(_MAX_WIDTH, result["ui_width"])
            )
            return result
        except Exception:
            return dict(defaults)

    def default_target(self) -> str:
        """返回自动检测失败时使用的默认目标。"""
        target = self._config.get("default_target", "word")
        if target in TARGET_LABELS and target != "unknown":
            return target
        return "word"

    def preferred_target(self) -> str:
        """返回上次手动选择；空字符串表示保持自动检测。"""
        target = self._config.get("last_target", "")
        if target in TARGET_LABELS and target != "unknown":
            return target
        return ""

    # ── Target handling ─────────────────────────────────────────────

    def _on_target_selected(self, target: str):
        """User picked a target from the icon bar."""
        self._config["last_target"] = target
        self._icon_bar.set_current_target(target)
        self._save_state()
        self.target_override_requested.emit(target)

    def _minimize(self):
        self._minimized = True
        self._hovered = False
        self._expanded = False
        self._dot.setVisible(False)
        self._tag.setVisible(False)
        self._target_lbl.setVisible(False)
        self._min_btn.setVisible(False)
        self._close_btn.setVisible(False)
        if self._tip_frame is not None:
            self._tip_frame.setVisible(False)
        self._expanded_panel.setVisible(False)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.invalidate()
        self._outer.activate()
        self.setFixedSize(_W_MIN, _H_MIN)
        self._min_label.setVisible(True)
        self._min_label.setGeometry(0, 0, _W_MIN, _H_MIN)
        self._apply_style()

    def _restore(self):
        self._minimized = False
        self._min_label.setVisible(False)
        self._min_label.setGeometry(0, 0, 0, 0)
        self._outer.setContentsMargins(12, 6, 12, 6)
        self._dot.setVisible(True)
        self._tag.setVisible(True)
        if self._target_lbl.text():
            self._target_lbl.setVisible(True)
        tip_h = 0
        if self._first_run and self._tip_frame is not None:
            self._tip_frame.setVisible(True)
            tip_h = _H_TIP
        self.setFixedSize(self._width, _H_IDLE + tip_h)
        self._apply_style()

    # ── Public API ──────────────────────────────────────────────────

    def show_from_tray(self) -> None:
        """从用户主动操作恢复并显示 HUD。"""
        if self._minimized:
            self._restore()
        self.show()
        # 后台启动时首次定位没有原生窗口句柄，显示后需要重新执行防遮挡。
        self._apply_expand()
        self.raise_()
        self.activateWindow()

    def update_result(self, output: AppOutput):
        self._error_active = False
        self._output = output
        self._current_text = getattr(output, "raw_text", "") or ""

        risk_color, dot = _RISK.get(output.risk_level, ("#cccccc", "●"))
        if output.has_binary:
            tag = output.content_type_label or "非文本"
        else:
            tag = CONTENT_TYPES.get(
                output.content_type, output.content_type_label
            )

        # Tracker: log previous session, start new one
        if (
            self._tracker
            and self._config.get("usage_tracking_enabled", False)
            and output.is_new_clipboard
        ):
            self._tracker.on_update(output.content_type, output.risk_level)
        self._viewed_logged = False

        dot_size = {
            "high": "11px",
            "medium": "10px",
            "low": "9px",
            "none": "8px",
        }.get(output.risk_level, "9px")
        dot_weight = "bold" if output.risk_level in ("high", "medium") else "normal"

        self._dot.setText(dot)
        self._dot.setStyleSheet(
            f"color: {risk_color}; font-size: {dot_size}; font-weight: {dot_weight};"
        )
        self._tag.setText(tag)

        risk_text, risk_text_color, risk_background = _RISK_BADGE.get(
            output.risk_level,
            _RISK_BADGE["none"],
        )
        self._risk_badge.setText(risk_text)
        self._risk_badge.setStyleSheet(
            f"color: {risk_text_color}; background-color: {risk_background}; "
            "border-radius: 4px; padding: 1px 6px;"
        )

        # Target display: compact label (hidden for "unknown")
        target_value = getattr(output, "target", "") or ""
        target_label = _TARGET_LABEL.get(target_value, "")
        if target_label:
            self._target_lbl.setText(f" → {target_label}")
            self._target_lbl.setVisible(True)
        else:
            self._target_lbl.setText("")
            self._target_lbl.setVisible(False)

        # Icon bar highlight
        self._icon_bar.set_current_target(target_value)

        # Expanded panel content
        content = ClipboardContent(
            text=self._current_text,
            html=getattr(output, "raw_html", "") or "",
            content_type=output.content_type,
        )
        preview = self._preview_renderer.render(
            content, output.target, preview_data=output.preview_data
        )

        self._preview.setHtml(preview.html)
        self._update_preview_height()
        self._conclusion.setText(preview.summary or output.prediction)

        items = preview.risks[:_MAX_BREAKDOWN_ITEMS]
        for i, lbl in enumerate(self._breakdown_labels):
            if i < len(items):
                lbl.setText(f"• {items[i]}")
            else:
                lbl.setText("")

        # Smart action button
        primary = getattr(output, "primary_action", "") or getattr(output, "action_type", "")
        available = getattr(output, "available_actions", []) or []
        self._configure_action_button(primary, available)

        if not self._minimized and output.risk_level in ("medium", "high"):
            self._pulse()
        else:
            self._apply_style()

    # ── Action Button ────────────────────────────────────────────────

    def _configure_action_button(self, primary: str, available: list[str]):
        """Set primary action button and "more actions" menu."""
        primary_labels = {
            "strip_formats": "清洗为纯文本",
            "clean_url":     "净化链接",
            "merge_lines":   "合并为一行",
        }
        more_labels = {
            "strip_formats": "清洗格式",
            "clean_url":     "净化链接",
            "merge_lines":   "合并换行",
        }

        self._current_action = primary if primary in primary_labels else ""
        if self._current_action:
            self._action_btn.setText(primary_labels[self._current_action])
            self._action_btn.setIcon(
                lucide_icon(_ACTION_ICON[self._current_action], "#ffffff", 14)
            )
            self._action_btn.setIconSize(QSize(14, 14))
        else:
            self._action_btn.setText("")
            self._action_btn.setIcon(QIcon())
        self._action_btn.setVisible(bool(self._current_action))
        self._action_status.setVisible(not self._current_action)

        # Build "more actions" menu with available actions other than the primary one.
        self._more_actions_menu = QMenu(self)
        self._more_actions_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {_CLR_BG};
                border: 1px solid {_CLR_BORDER};
                border-radius: 4px;
                padding: 2px;
            }}
            QMenu::item {{
                padding: 3px 16px;
                font-family: "{_FONT_FAMILY}";
                font-size: 9pt;
                color: {_CLR_TEXT};
            }}
            QMenu::item:selected {{ background-color: #f0f0f0; }}
        """)
        other_actions = [a for a in available if a != self._current_action and a in more_labels]
        for action in other_actions:
            menu_action = self._more_actions_menu.addAction(more_labels[action])
            menu_action.triggered.connect(
                lambda _checked=False, k=action: self.action_triggered.emit(k)
            )
        self._more_actions_btn.setVisible(bool(other_actions) and bool(self._current_action))

    def _on_action_clicked(self):
        """Emit action_triggered with current action_type."""
        if self._output and self._current_action:
            self.action_triggered.emit(self._current_action)

    def _show_more_actions_menu(self):
        pos = self._more_actions_btn.mapToGlobal(
            QPoint(0, self._more_actions_btn.height())
        )
        self._more_actions_menu.exec(pos)

    def _update_preview_height(self) -> None:
        """让短预览保持紧凑，同时限制长内容的最大高度。"""
        document = self._preview.document()
        document.setTextWidth(max(120, self._width - 36))
        text = document.toPlainText()
        chars_per_line = max(18, (self._width - 48) // 8)
        estimated_lines = sum(
            max(1, ceil(len(line) / chars_per_line))
            for line in (text.splitlines() or [""])
        )
        content_height = 28 + estimated_lines * 20
        self._preview_height = max(
            _H_PREVIEW_MIN,
            min(_H_PREVIEW, content_height),
        )
        self._preview.setFixedHeight(self._preview_height)

    # ── Keyboard Shortcuts ─────────────────────────────────────────

    def keyPressEvent(self, event):
        """Handle keyboard navigation when HUD has focus.

        ← / →  : switch target in the icon bar.
        Enter  : trigger primary action.
        Escape : collapse to Layer 1 (or hide if minimized).
        """
        key = event.key()
        if key in (Qt.Key_Left, Qt.Key_Right):
            if self._expanded and not self._minimized:
                if key == Qt.Key_Right:
                    self._icon_bar.select_next()
                else:
                    self._icon_bar.select_previous()
                return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if self._current_action and self._action_btn.isVisible():
                self.action_triggered.emit(self._current_action)
                return
        if key == Qt.Key_Escape:
            if self._minimized:
                return
            if self._expanded:
                self._expanded = False
                self._apply_expand()
            else:
                self._minimize()
            return
        super().keyPressEvent(event)

    # ── Success Toast ──────────────────────────────────────────────

    def show_success_toast(self):
        """Brief green flash + ✓ toast on successful action execution."""
        if self._minimized:
            self._restore()

        self.setStyleSheet(
            f"#HudWindow {{ background-color: {_CLR_SUCCESS_BG}; "
            f"border: 1px solid {_CLR_SUCCESS}; border-radius: 8px; }}"
        )
        current = self._tag.text()
        self._tag.setText(f"\u2713 {current}")

        QTimer.singleShot(300, self._clear_success_toast)

    def _clear_success_toast(self):
        """Restore original style and refresh."""
        self._apply_style()
        if self._output:
            tag = CONTENT_TYPES.get(self._output.content_type, self._output.content_type_label)
            self._tag.setText(f"{tag}")

    # ── Error Toast ──────────────────────────────────────────────────

    def show_error(self, message: str):
        """持续显示操作失败信息，直到收到下一份剪贴板结果。"""
        if self._minimized:
            self._restore()

        self._error_active = True
        self._conclusion.setText(f"⚠ 操作失败: {message}")
        self._expanded = True
        self._apply_expand()

    # ── Pulse ───────────────────────────────────────────────────────

    def _pulse(self):
        """Border pulse on clipboard change (medium/high risk only)."""
        self._set_border(_CLR_PULSE)
        QTimer.singleShot(120, self._apply_style)

    def _pulse_reload(self):
        """Quick double-pulse on target switch — signals prediction changed."""
        self._set_border("#666666")
        QTimer.singleShot(80, lambda: self._set_border(_CLR_PULSE))
        QTimer.singleShot(200, self._apply_style)

    def _set_border(self, color_hex: str):
        self.setStyleSheet(f"""
            #HudWindow {{
                background-color: {_CLR_BG};
                border: 1px solid {color_hex};
                border-radius: 8px;
            }}
        """)

    # ── Drag ────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._drag_offset = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_offset is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        pos = event.globalPosition().toPoint()
        delta = pos - self.frameGeometry().topLeft() - self._drag_offset
        if abs(delta.x()) > 3 or abs(delta.y()) > 3:
            self._dragging = True
            self.move(pos - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        was_dragging = self._dragging
        if self._drag_offset is not None:
            if not self._dragging:
                if self._minimized:
                    self._restore()
                else:
                    self._expanded = not self._expanded
                    self._apply_expand()
                    self.setFocus()
        self._dragging = False
        self._drag_offset = None
        if was_dragging:
            self._save_state()
            if self._first_run:
                self._dismiss_tip()

    def enterEvent(self, event: QEnterEvent):
        self._hovered = True
        if not self._minimized:
            self._min_btn.setVisible(True)
            self._close_btn.setVisible(True)
        self._apply_style()
        if self._tracker and self._config.get("usage_tracking_enabled", False) and not self._viewed_logged:
            self._tracker.on_viewed()
            self._viewed_logged = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        # Don't collapse while a menu popup is open (e.g. "更多" dropdown).
        if QApplication.activePopupWidget() is not None:
            self._apply_style()
            super().leaveEvent(event)
            return
        if not self._minimized:
            self._min_btn.setVisible(False)
            self._close_btn.setVisible(False)
            if self._expanded and not self._error_active:
                self._expanded = False
                self._apply_expand()
        self._apply_style()
        super().leaveEvent(event)

    # ── State → size + visibility ───────────────────────────────────

    def _apply_expand(self):
        if self._minimized:
            return
        tip_h = _H_TIP if (self._first_run and self._tip_frame is not None and self._tip_frame.isVisible()) else 0

        if self._expanded:
            self._expanded_panel.setVisible(True)
            h = _H_IDLE + tip_h + _H_ICON_BAR + self._preview_height + _H_CONCLUSION
            n = sum(1 for lbl in self._breakdown_labels if lbl.text())
            h += n * _H_ITEM
            if self._action_btn.isVisible() or self._more_actions_btn.isVisible():
                h += _H_ACTION
            h += 28  # 外边距与布局间距缓冲
        else:
            self._expanded_panel.setVisible(False)
            h = _H_IDLE + tip_h

        self.setFixedSize(self._width, h)

        # Expand anti-occlusion: keep the whole HUD on screen.
        wh = self.windowHandle()
        scr = wh.screen() if wh else None
        if scr:
            avail = scr.availableGeometry()
            # 任务栏可位于任意边；右/下额外留出逻辑像素吸收原生外框取整。
            max_x = max(avail.left(), avail.right() - self.width())
            max_y = max(avail.top(), avail.bottom() - self.height() - 17)
            new_x = min(max(self.x(), avail.left()), max_x)
            new_y = min(max(self.y(), avail.top()), max_y)
            if new_x != self.x() or new_y != self.y():
                self.move(new_x, new_y)

        self._apply_style()

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _font(size: float, bold: bool) -> QFont:
        f = QFont(_FONT_FAMILY, round(size))
        f.setBold(bold)
        return f
