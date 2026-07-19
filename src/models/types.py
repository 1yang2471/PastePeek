"""PastePeek data types — Clipboard Outcome Predictor.

Core principle: predict paste outcome per target, not just flag risk.
"""

from dataclasses import dataclass, field

# ── Internal pipeline types (retained) ─────────────────────────────────

@dataclass
class TextRun:
    text: str
    bold: bool = False
    italic: bool = False
    font_family: str | None = None
    font_size_pt: float | None = None
    color_hex: str | None = None
    link_url: str | None = None


@dataclass
class Paragraph:
    text_runs: list[TextRun] = field(default_factory=list)


@dataclass
class ListItem:
    text_runs: list[TextRun] = field(default_factory=list)
    level: int = 0
    marker: str = "•"


@dataclass
class HorizontalRule:
    pass


@dataclass
class StructuredContent:
    plain_text: str = ""
    paragraphs: list[Paragraph] = field(default_factory=list)
    lists: list[ListItem] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)
    horizontal_rules: list[HorizontalRule] = field(default_factory=list)
    has_html: bool = False


@dataclass
class Anomaly:
    category: str = ""
    severity: str = ""
    description: str = ""
    source: str = ""
    target: str = ""


@dataclass
class Prediction:
    target_app: str
    risk_level: str
    rendered_text: str = ""
    anomalies: list[Anomaly] = field(default_factory=list)


@dataclass
class DiffItem:
    item: str = ""
    status: str = ""
    reason: str = ""


# ── Outcome types (UI-facing) ──────────────────────────────────────────

CONTENT_TYPES = {
    "rich_text":      "富文本",
    "plain_text":     "纯文本",
    "structured_text": "结构化",
    "code":           "代码",
}

TARGET_APPS = {
    "word":           "Word",
    "chrome":         "Chrome",
    "code_editor":    "代码编辑器",
    "terminal":       "终端",
    "chat_app":       "聊天应用",
    "markdown_editor": "Markdown 编辑器",
    "spreadsheet":    "电子表格",
    "presentation":   "演示文稿",
    "unknown":        "未知应用",
}

TARGET_LABELS = {
    "word":           "Word",
    "chrome":         "Chrome",
    "code_editor":    "代码编辑器",
    "terminal":       "终端",
    "chat_app":       "聊天应用",
    "markdown_editor": "Markdown",
    "spreadsheet":    "表格",
    "presentation":   "演示",
    "unknown":        "未知应用",
}

# Target menu groups for dropdown
TARGET_GROUPS: list[tuple[str, list[str]]] = [
    ("文档办公", ["word", "spreadsheet", "presentation"]),
    ("编辑器",   ["code_editor", "terminal", "markdown_editor"]),
    ("通讯",     ["chrome", "chat_app"]),
]

# Default primary target for hover prediction
_DEFAULT_TARGET = "word"


@dataclass
class AppOutput:
    """Clipboard Outcome Predictor — 2-layer scenario-based preview.

    Layer 1 (idle):   ● {type_tag} → {target}       (1 line)
    Layer 2 (expanded): target icon bar + preview + conclusion + risks + actions
    """

    risk_level: str = ""              # "high" | "medium" | "low" | "none"
    risk_label: str = ""              # "⚠" | "✓" — for display
    content_type: str = ""            # internal key
    content_type_label: str = ""      # display name

    # Per-target outcome prediction
    target: str = _DEFAULT_TARGET     # "word" | "chrome" | "code_editor" | "unknown"
    primary_target: str = _DEFAULT_TARGET
    prediction: str = ""              # WHAT — e.g. "Word中列表可能丢失"
    why: str = ""                     # WHY — e.g. "检测到<ul>/<ol>结构"
    suggestion: str = ""              # DO  — e.g. "Ctrl+Shift+V 纯文本粘贴"
    breakdown: list[str] = field(default_factory=list)  # BREAK items
    details: list[str] = field(default_factory=list)     # retained for compat

    # Deep analysis metadata (set externally after prediction)
    deep_image_count: int = 0
    deep_table_count: int = 0
    deep_link_count: int = 0
    deep_list_count: int = 0
    deep_font_count: int = 0
    deep_headings: int = 0
    deep_complexity: str = ""        # "low" | "medium" | "high"
    deep_has_analysis: bool = False

    # URL / tracking detection
    is_url: bool = False
    has_tracking_params: bool = False

    # Binary / non-text formats
    has_binary: bool = False
    has_unsafe_formats: bool = False

    # Smart action hint for HUD button (deprecated, use primary_action)
    action_type: str = ""  # "strip_formats" | "clean_url" | "merge_lines" | ""

    # Primary recommended action for the current (content_type, target)
    primary_action: str = ""  # "strip_formats" | "clean_url" | "merge_lines" | ""

    # All actions applicable to the current content (excluding noop)
    available_actions: list[str] = field(default_factory=list)

    # Raw clipboard text (for preview generation in HUD)
    raw_text: str = ""
    raw_html: str = ""

    # Scenario preview metadata (populated by OutcomePredictor)
    preview_data: dict = field(default_factory=dict)

    # 仅新剪贴板内容开始统计会话；目标切换复用当前会话。
    is_new_clipboard: bool = True
