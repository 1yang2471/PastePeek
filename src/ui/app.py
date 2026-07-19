"""PastePeekApp — main application controller.

Pipeline: clipboard → content classifier → target detector
         → outcome predictor → UI.

Core principle: dual-axis prediction (content_type × target).
No source detector, no WordSimulator, no DiffExplainer — pure static mapping.
"""

import re

from PySide6.QtCore import QObject, QTimer, Signal

from src.analyzer.deep_analyzer import DeepAnalyzer
from src.clipboard.formats import contains_embedded_binary_content
from src.clipboard.listener import ClipboardListener
from src.content_safety import detect_protected_content_type
from src.detector.target_detector import TargetDetector
from src.explainer.outcome_predictor import OutcomePredictor
from src.listener.window_hook import WindowFocusMonitor
from src.manipulator.text_toolkit import (
    ClipboardBusyError,
    EmptyContentError,
    clean_url,
    merge_lines,
    strip_formats,
)
from src.models.types import TARGET_APPS, AppOutput

CHECK_INTERVAL_MS = 300

# ── Content type: code patterns ────────────────────────────────────────
_CODE_PATTERNS: list[str] = [
    "def ", "class ", "import ", "from ", "function ",
    "const ", "let ", "var ", "=>", "// ", "/*",
    "fn ", "impl ", "trait ", "pub ", "use ",
    "#include", "printf", "cout", "System.out", "print(",
]

# 单独出现即可确认的行级代码结构，避免短函数被误判为纯文本。
_STRONG_CODE_PATTERNS: tuple[str, ...] = (
    r"(?m)^\s*(?:async\s+)?(?:def|class)\s+[A-Za-z_]\w*",
    r"(?m)^\s*(?:from\s+\S+\s+import|import)\s+\S+",
    r"(?m)^\s*(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=",
    r"(?im)^\s*(?:fn|func)\s+[A-Za-z_]\w*\s*\(",
    r"(?im)^\s*(?:select|with|insert|update|delete|create|alter|drop)\b",
    r"(?m)^\s*(?:int|void|char|float|double|bool|string)\s+\w+\s*\(",
)

# ── Content type: markdown patterns ────────────────────────────────────
_MD_PATTERNS: list[str] = [
    "\n## ", "\n# ", "\n- ", "\n* ", "\n1. ",
    "```", "| ", "\n> ",
]

# ── Classifiers ────────────────────────────────────────────────────────

def _detect_content_type(
    text: str,
    html: str | None,
    has_rtf: bool = False,
) -> str:
    """Classify clipboard content type.

    Priority: code > rich_text > structured_text > plain_text
    """
    if text:
        protected_type = detect_protected_content_type(text, html)
        if protected_type is not None:
            return protected_type
        if html and re.search(r"<\s*(?:pre|code)\b", html, re.IGNORECASE):
            return "code"
        for pattern in _STRONG_CODE_PATTERNS:
            if re.search(pattern, text):
                return "code"

    if (html and html.strip()) or has_rtf:
        return "rich_text"

    if not text:
        return "plain_text"

    for pattern in _STRONG_CODE_PATTERNS:
        if re.search(pattern, text):
            return "code"

    code_score = 0
    for p in _CODE_PATTERNS:
        if p in text:
            code_score += 1
            if code_score >= 2:
                return "code"

    stripped = text.strip()
    if (
        (stripped.startswith("{") and stripped.endswith("}"))
        or (stripped.startswith("[") and stripped.endswith("]"))
        or len(re.findall(r"(?m)^\s*[\w.-]+\s*:\s*\S+", text)) >= 2
    ):
        return "structured_text"

    md_score = 0
    for p in _MD_PATTERNS:
        if re.search(re.escape(p), text):
            md_score += 1
            if md_score >= 2:
                return "structured_text"

    return "plain_text"


# Targets where a tracked URL is meaningful enough to become the primary action.
_URL_PRIMARY_TARGETS = {"chrome", "markdown_editor", "chat_app", "word"}


def _determine_action_type(
    content_type: str,
    target: str,
    is_url: bool,
    has_tracking: bool,
    has_binary: bool,
    text: str,
    has_unsafe_formats: bool = False,
) -> tuple[str, list[str]]:
    """Recommend primary action and all applicable actions for HUD.

    Decision is based on the dual-axis (content_type, target).
    Returns:
        (primary_action, available_actions)
    """
    if has_binary or has_unsafe_formats:
        return "", []
    if not text or not text.strip():
        return "", []
    if detect_protected_content_type(text) == "structured_text":
        return "", []

    actions: list[str] = []
    lines = text.splitlines() if text else []
    is_multi_line = len(lines) > 1

    # Build available actions from content characteristics.
    if content_type == "rich_text":
        actions.append("strip_formats")

    if is_url and has_tracking:
        actions.append("clean_url")

    if is_multi_line and content_type not in {"code", "structured_text"}:
        actions.append("merge_lines")

    # Primary action follows the (content_type, target) mapping.
    primary = ""
    if content_type == "code":
        primary = ""  # code is protected, never auto-clean
    elif content_type == "structured_text":
        if is_url and has_tracking and "clean_url" in actions:
            primary = "clean_url"
    elif content_type == "rich_text":
        if target == "terminal" and is_multi_line and "merge_lines" in actions:
            primary = "merge_lines"
        elif target == "markdown_editor" and is_url and has_tracking and "clean_url" in actions:
            primary = "clean_url"
        elif target in ("word", "chat_app", "markdown_editor") and "strip_formats" in actions:
            primary = "strip_formats"
    elif content_type == "plain_text":
        if target == "terminal" and is_multi_line and "merge_lines" in actions:
            primary = "merge_lines"
        elif is_url and has_tracking and target in _URL_PRIMARY_TARGETS and "clean_url" in actions:
            primary = "clean_url"

    return primary, actions


# ── App ────────────────────────────────────────────────────────────────

class PastePeekApp(QObject):
    """Main controller orchestrating clipboard analysis pipeline.

    Pipeline: clipboard → content classifier → target detector
             → outcome predictor → UI.
    Plus: real-time target switching via WindowFocusMonitor.
    """

    analysis_ready = Signal(object)  # AppOutput
    action_triggered = Signal(str, str)  # (action_type, result_message)

    def __init__(
        self,
        parent=None,
        *,
        default_target: str = "word",
        listener=None,
        target_detector=None,
    ):
        super().__init__(parent)
        self._default_target = (
            default_target
            if default_target in TARGET_APPS and default_target != "unknown"
            else "word"
        )
        self._listener = (
            listener if listener is not None else ClipboardListener()
        )
        self._predictor = OutcomePredictor()
        self._target_detector = (
            target_detector if target_detector is not None else TargetDetector()
        )
        self._deep_analyzer = DeepAnalyzer()

        # Remember last clipboard + prediction for target-switch re-analysis
        self._last_text = ""
        self._last_html = None
        self._last_binary = False
        self._last_rtf = False
        self._last_unsafe_formats = False
        self._last_sequence: int | None = None
        self._last_content_type = "plain_text"
        self._last_target = "unknown"

        # Manual target override (set via HUD dropdown)
        # Empty string = auto-detect; any valid target key = override
        self._manual_target: str = ""

        # Last output for field preservation across target switches
        self._last_output: AppOutput | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self.check_clipboard)

        # Real-time foreground window monitor
        self._focus_monitor = WindowFocusMonitor(self)
        self._focus_monitor.target_changed.connect(self._on_target_switched)

    def start(self):
        self._timer.start()
        self._focus_monitor.start()

    def stop(self):
        self._timer.stop()
        self._focus_monitor.stop()

    def check_clipboard(self) -> AppOutput | None:
        """读取一次剪贴板；仅在内容变化时返回并发出分析结果。"""
        data = self._listener.read()
        if not data.read_succeeded:
            return None
        current_text = data.text or ""
        current_html = data.html
        current_binary = bool(data.has_binary)
        current_rtf = bool(data.has_rtf)
        current_unsafe_formats = bool(data.has_unsafe_formats)
        current_sequence = data.sequence_number

        if (
            current_text == self._last_text
            and current_html == self._last_html
            and current_binary == self._last_binary
            and current_rtf == self._last_rtf
            and current_unsafe_formats == self._last_unsafe_formats
        ):
            self._last_sequence = current_sequence
            return None
        self._last_text = current_text
        self._last_html = current_html
        self._last_binary = current_binary
        self._last_rtf = current_rtf
        self._last_unsafe_formats = current_unsafe_formats
        self._last_sequence = current_sequence

        if not current_text and not current_html and not current_binary:
            return None

        # 1. Content type
        content_type = _detect_content_type(
            current_text, current_html, current_rtf
        )

        # 2. Target detection (foreground window — where user will paste)
        #    Manual override takes priority over auto-detection
        target = self._get_resolved_target()

        # Store for target-switch re-analysis
        self._last_content_type = content_type
        self._last_target = target

        # 3. Outcome prediction (content_type × target, <1ms)
        output = self._predictor.generate(content_type, target=target)

        if current_binary and not current_text and not current_html:
            self._apply_binary_only_state(output)

        # 4. Deep analysis metadata (structural fingerprint, ~0.2ms)
        deep = self._deep_analyzer.analyze(html=current_html or "", text=current_text)
        output.deep_image_count = deep.image_count
        output.deep_table_count = deep.table_count
        output.deep_link_count = deep.link_count
        output.deep_list_count = deep.list_count
        output.deep_font_count = len(deep.font_families)
        output.deep_headings = deep.heading_count
        output.deep_complexity = deep.complexity
        output.deep_has_analysis = deep.has_html

        # Binary / URL / tracking detection
        output.has_binary = bool(data.has_binary) or contains_embedded_binary_content(
            current_html,
        )
        output.has_unsafe_formats = current_unsafe_formats
        output.is_url = deep.is_url
        output.has_tracking_params = deep.has_tracking_params

        # Smart action recommendation based on (content_type, target)
        primary, available = _determine_action_type(
            content_type, target, output.is_url, output.has_tracking_params,
            output.has_binary, current_text, output.has_unsafe_formats,
        )
        output.primary_action = primary
        output.available_actions = available
        output.action_type = primary  # backward compatibility
        output.raw_text = current_text
        output.raw_html = current_html or ""

        self._last_output = output
        self.analysis_ready.emit(output)
        return output

    def _check_clipboard(self) -> AppOutput | None:
        """兼容旧的内部调用名称。"""
        return self.check_clipboard()

    @staticmethod
    def _apply_binary_only_state(output: AppOutput) -> None:
        '''统一非文本快照的用户说明和安全操作状态。'''
        output.content_type_label = '非文本'
        output.prediction = '当前剪贴板包含图片、文件或音频，PastePeek 不会修改此内容'
        output.why = '非文本内容由目标应用直接处理'
        output.suggestion = '请在目标应用中粘贴后确认结果'
        output.breakdown = ['暂不提供图片、文件或音频的效果预览']
        output.preview_data = {
            'summary': output.prediction,
            'risks': output.breakdown,
            'render_type': 'checklist',
            'suggestion': output.suggestion,
        }
        output.primary_action = ''
        output.available_actions = []
        output.action_type = ''

    def _refresh_prediction_for_target(self, target: str) -> None:
        """基于缓存快照重建目标预测并发送更新。"""
        self._last_target = target
        output = self._predictor.generate(
            self._last_content_type,
            target=target,
        )
        output.is_new_clipboard = False

        if self._last_output:
            for field_name in (
                "deep_image_count",
                "deep_table_count",
                "deep_link_count",
                "deep_list_count",
                "deep_font_count",
                "deep_headings",
                "deep_complexity",
                "deep_has_analysis",
                "has_binary",
                "has_unsafe_formats",
                "is_url",
                "has_tracking_params",
                "raw_text",
                "raw_html",
            ):
                setattr(output, field_name, getattr(self._last_output, field_name))
            self._recompute_action(output)

        if output.has_binary and not output.raw_text and not output.raw_html:
            self._apply_binary_only_state(output)
        self._last_output = output
        self.analysis_ready.emit(output)

    # ── Real-time target switching ─────────────────────────────────

    def _on_target_switched(self, new_target: str):
        """Foreground window changed — re-analyze with new target if different."""
        # Don't react to auto-detection if user has manual override
        if self._manual_target:
            return
        # 点击 HUD 或系统弹窗时可能短暂无法识别目标，保留最后已知场景。
        if new_target == "unknown":
            return
        # Ignore if no clipboard content yet
        if not self._last_text and not self._last_html and not self._last_binary:
            return
        # Skip if same target (no actual change)
        if new_target == self._last_target:
            return
        self._refresh_prediction_for_target(new_target)

    def _get_resolved_target(self) -> str:
        """Return manual target if set, otherwise auto-detect."""
        if self._manual_target:
            return self._manual_target
        detected = self._target_detector.get_active_target()
        return self._default_target if detected == "unknown" else detected

    def _recompute_action(self, output: AppOutput) -> None:
        """Recompute primary/available actions when target changes."""
        primary, available = _determine_action_type(
            output.content_type,
            output.target,
            output.is_url,
            output.has_tracking_params,
            output.has_binary,
            output.raw_text,
            output.has_unsafe_formats,
        )
        output.primary_action = primary
        output.available_actions = available
        output.action_type = primary  # backward compatibility

    def set_manual_target(self, target: str):
        """Set a manual target override from HUD dropdown.

        Empty string = restore auto-detection.
        """
        self._manual_target = target.strip() if target else ""
        # Reset last_target so next auto-detection will fire
        if not self._manual_target:
            self._last_target = ""
            return
        # Immediately re-run prediction with the new manual target
        if not self._last_text and not self._last_html and not self._last_binary:
            return
        target = self._get_resolved_target()
        if target == self._last_target:
            return
        self._refresh_prediction_for_target(target)

    def on_action_triggered(self, action_type: str) -> tuple[bool, str]:
        """Execute a clipboard manipulation action and refresh pipeline.

        Returns:
            (success: bool, message: str)
        """
        known_actions = {"strip_formats", "clean_url", "merge_lines"}
        if action_type not in known_actions:
            return False, f"未知操作: {action_type}"

        if self._last_output is None or action_type not in self._last_output.available_actions:
            return False, "当前内容不适用此操作，已保留原剪贴板"

        current = self._listener.read()
        if not current.read_succeeded:
            return False, "无法确认剪贴板当前内容，请稍后重试"
        if (
            (current.text or "") != self._last_text
            or current.html != self._last_html
            or bool(current.has_binary) != self._last_binary
            or bool(current.has_rtf) != self._last_rtf
            or bool(current.has_unsafe_formats) != self._last_unsafe_formats
            or (
                self._last_sequence is not None
                and current.sequence_number is not None
                and current.sequence_number != self._last_sequence
            )
        ):
            return False, "剪贴板内容已变化，请查看最新预览后重试"
        if (
            self._last_sequence is None
            or current.sequence_number is None
            or current.sequence_number <= 0
        ):
            return False, "无法确认剪贴板版本，请稍后重试"

        try:
            if action_type == "strip_formats":
                ok, msg = strip_formats(expected_sequence=self._last_sequence)
            elif action_type == "clean_url":
                ok, msg = clean_url(expected_sequence=self._last_sequence)
            elif action_type == "merge_lines":
                ok, msg = merge_lines(expected_sequence=self._last_sequence)
        except ClipboardBusyError as e:
            return False, str(e)
        except EmptyContentError as e:
            return False, str(e)

        if ok:
            # Clear cached clipboard so next timer tick re-reads transformed content
            self._last_text = ""
            self._last_html = None
            self._last_rtf = False
            self._last_unsafe_formats = False
            self._last_sequence = None
            self._last_output = None
        return ok, msg
