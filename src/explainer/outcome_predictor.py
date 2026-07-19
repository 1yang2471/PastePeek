"""OutcomePredictor — per-target paste outcome prediction engine.

Core principle: static mapping of (content_type × target).
No AI, no rules engine, no real app simulation — pure dict lookup (<1ms).

Pipeline:
  content_type + target → OutcomePredictor → AppOutput
                               │
                  ┌────────────┼────────────┐
                  ▼            ▼            ▼
            prediction(WHAT)  why(WHY)  suggestion(DO)

Lookup strategy:
  1. COMPATIBILITY_MATRIX[(content_type, target)]  — specific
  2. _OUTCOME_MAP[content_type]                     — fallback (Word default)
"""

from src.models.types import CONTENT_TYPES, AppOutput

# ── Static mapping: content_type → per-target outcome ─────────────────
# Primary target (Word) is shown in hover; other info feeds breakdown.

_OUTCOME_MAP: dict[str, dict] = {
    "rich_text": {
        "risk_level": "medium",
        "prediction": "Word 中格式可能异常",
        "why": "检测到 <ul>/<ol>/<table> 等 HTML 结构，Word 解析规则不同",
        "suggestion": "Ctrl+Shift+V 粘贴为纯文本",
        "breakdown": [
            "列表缩进可能丢失",
            "横线变为段落边框",
            "字体样式被剥离",
        ],
    },
    "plain_text": {
        "risk_level": "none",
        "prediction": "所有场景均正常",
        "why": "仅含纯文本字符，无隐藏格式标记",
        "suggestion": "Ctrl+V 直接粘贴",
        "breakdown": [],
    },
    "structured_text": {
        "risk_level": "low",
        "prediction": "Word 中缩进和列表可能变化",
        "why": "检测到 Markdown 标记（#/-/*），Word 不会解析这些语法",
        "suggestion": "Ctrl+Shift+V 后手动调整缩进",
        "breakdown": [
            "列表缩进偏移",
            "标题样式丢失",
        ],
    },
    "code": {
        "risk_level": "low",
        "prediction": "Word 中缩进和格式可能丢失",
        "why": "检测到代码模式（def/class/import），Word 会重排空格缩进",
        "suggestion": "Ctrl+Shift+V 保留原始缩进",
        "breakdown": [
            "空格缩进可能丢失",
            "代码高亮被剥离",
        ],
    },
}

# ── Compatibility Matrix: (content_type, target) → per-target outcome ─
# Specific overrides for the default _OUTCOME_MAP.
# Key = (content_type, target), Value = outcome dict.
# Targets: word, chrome, code_editor, unknown

COMPATIBILITY_MATRIX: dict[tuple[str, str], dict] = {
    # ── rich_text ──────────────────────────────────────────────────
    ("rich_text", "word"): {
        "risk_level": "medium",
        "prediction": "Word 中格式可能异常",
        "why": "检测到 <ul>/<ol>/<table> 等 HTML 结构，Word 解析规则不同",
        "suggestion": "Ctrl+Shift+V 粘贴为纯文本",
        "breakdown": [
            "列表缩进可能丢失",
            "横线变为段落边框",
            "字体样式被剥离",
        ],
    },
    ("rich_text", "chrome"): {
        "risk_level": "low",
        "prediction": "浏览器中格式正常保留",
        "why": "Chrome 原生支持 HTML 粘贴，格式渲染一致",
        "suggestion": "Ctrl+V 直接粘贴",
        "breakdown": [],
    },
    ("rich_text", "code_editor"): {
        "risk_level": "high",
        "prediction": "代码编辑器会粘贴纯文本，排版结构可能改变",
        "why": "代码编辑器通常读取剪贴板纯文本格式，不会写入 HTML 标签",
        "suggestion": "Ctrl+V 粘贴后检查列表、表格与换行",
        "breakdown": [
            "HTML 标签由剪贴板协商剥离，富文本样式随之丢失",
            "列表与表格会转成普通文本",
            "多段内容可能不适合作为源代码",
        ],
    },

    # ── plain_text ─────────────────────────────────────────────────
    ("plain_text", "word"): {
        "risk_level": "none",
        "prediction": "Word 中正常粘贴",
        "why": "仅含纯文本字符，无隐藏格式标记",
        "suggestion": "Ctrl+V 直接粘贴",
        "breakdown": [],
    },
    ("plain_text", "chrome"): {
        "risk_level": "none",
        "prediction": "浏览器中正常粘贴",
        "why": "纯文本内容，所有应用处理一致",
        "suggestion": "Ctrl+V 直接粘贴",
        "breakdown": [],
    },
    ("plain_text", "code_editor"): {
        "risk_level": "none",
        "prediction": "代码编辑器中正常粘贴",
        "why": "纯文本内容，代码编辑器完全兼容",
        "suggestion": "Ctrl+V 直接粘贴",
        "breakdown": [],
    },

    # ── structured_text ────────────────────────────────────────────
    ("structured_text", "word"): {
        "risk_level": "low",
        "prediction": "Word 中缩进和列表可能变化",
        "why": "检测到 Markdown 标记（#/-/*），Word 不会解析这些语法",
        "suggestion": "Ctrl+Shift+V 后手动调整缩进",
        "breakdown": [
            "列表缩进偏移",
            "标题样式丢失",
        ],
    },
    ("structured_text", "chrome"): {
        "risk_level": "low",
        "prediction": "Chrome 中输入框不解析 Markdown",
        "why": "Markdown 标记（#/-/*）在聊天框/输入框中不渲染",
        "suggestion": "确认目标支持 Markdown；否则 Ctrl+Shift+V",
        "breakdown": [
            "#标题 可能显示为纯文本 #",
            "列表标记（-/*）不渲染为列表",
        ],
    },
    ("structured_text", "code_editor"): {
        "risk_level": "low",
        "prediction": "代码编辑器中正常显示",
        "why": "Markdown 本质是纯文本，代码编辑器完全兼容",
        "suggestion": "Ctrl+V 直接粘贴",
        "breakdown": [],
    },

    # ── code ───────────────────────────────────────────────────────
    ("code", "word"): {
        "risk_level": "medium",
        "prediction": "Word 中缩进和格式可能丢失",
        "why": "检测到代码模式（def/class/import），Word 会重排空格缩进",
        "suggestion": "Ctrl+Shift+V 保留原始缩进",
        "breakdown": [
            "空格缩进可能丢失",
            "代码高亮被剥离",
        ],
    },
    ("code", "chrome"): {
        "risk_level": "low",
        "prediction": "Chrome 输入框可能丢缩进",
        "why": "浏览器文本框通常对空格缩进处理不一致",
        "suggestion": "粘贴后检查缩进，必要时手动修复",
        "breakdown": [
            "前导空格可能被裁剪",
        ],
    },
    ("code", "code_editor"): {
        "risk_level": "none",
        "prediction": "代码编辑器中正常粘贴",
        "why": "代码编辑器原生支持缩进和高亮",
        "suggestion": "Ctrl+V 直接粘贴",
        "breakdown": [],
    },

    # ═════════════════════════════════════════════════════════════════
    # New targets — 20 entries (4 content_types × 5 targets)
    # ═════════════════════════════════════════════════════════════════

    # ── terminal ──────────────────────────────────────────────────
    ("rich_text", "terminal"): {
        "risk_level": "high",
        "prediction": "终端会粘贴纯文本，多行内容可能被执行",
        "why": "终端读取剪贴板纯文本；富文本格式会丢失，换行仍可能触发命令",
        "suggestion": "先在文本编辑器检查纯文本内容，再按需逐行粘贴",
        "breakdown": [
            "字体、颜色和链接等富文本样式丢失",
            "列表与表格会转成普通文本",
            "自动执行风险：粘贴内容含换行可能触发命令",
        ],
    },
    ("plain_text", "terminal"): {
        "risk_level": "low",
        "prediction": "终端中正常粘贴，注意多行内容可能自动执行",
        "why": "纯文本内容，终端完全兼容；多行时每行视为独立命令",
        "suggestion": "多行内容先粘贴到文本编辑器确认，再复制进终端",
        "breakdown": [
            "多行内容可能逐行自动执行",
            "末尾换行符触发立即执行",
        ],
    },
    ("structured_text", "terminal"): {
        "risk_level": "medium",
        "prediction": "终端不解析 Markdown，多行有自动执行风险",
        "why": "检测到 Markdown 标记（#/-/*），终端不解析，且多行会逐行执行",
        "suggestion": "Ctrl+Shift+V 粘贴纯文本，多行内容务必检查",
        "breakdown": [
            "# 标题和列表标记原样显示",
            "每行可能被终端解释为独立命令",
        ],
    },
    ("code", "terminal"): {
        "risk_level": "medium",
        "prediction": "终端中代码可能被误解为命令",
        "why": "检测到代码模式，终端会逐行解释，可能意外执行命令",
        "suggestion": "确保代码是完整的脚本文件，而非逐行粘贴到终端",
        "breakdown": [
            "代码行可能被终端逐行执行",
            "特殊字符（$、|、>）触发管道/重定向",
        ],
    },

    # ── chat_app ──────────────────────────────────────────────────
    ("rich_text", "chat_app"): {
        "risk_level": "low",
        "prediction": "聊天应用中格式基本保留，图片可能转为文件发送",
        "why": "检测到 HTML 格式，聊天应用通常支持部分富文本，但图片需单独处理",
        "suggestion": "Ctrl+V 直接粘贴，如图片未粘贴请手动上传",
        "breakdown": [
            "内嵌图片可能丢失或转为文件",
            "表格结构可能塌缩为纯文本",
        ],
    },
    ("plain_text", "chat_app"): {
        "risk_level": "none",
        "prediction": "聊天应用中正常粘贴",
        "why": "纯文本内容，所有聊天应用完全兼容",
        "suggestion": "Ctrl+V 直接粘贴",
        "breakdown": [],
    },
    ("structured_text", "chat_app"): {
        "risk_level": "low",
        "prediction": "聊天应用中 Markdown 显示为源码",
        "why": "检测到 Markdown 标记（#/-/*），多数聊天应用不渲染 Markdown",
        "suggestion": "确认目标应用支持 Markdown（如 Slack/Discord），否则 Ctrl+Shift+V",
        "breakdown": [
            "#标题 显示为纯文本 #",
            "列表标记（-/*）不渲染为列表",
            "代码块标记 ``` 原样显示",
        ],
    },
    ("code", "chat_app"): {
        "risk_level": "low",
        "prediction": "聊天应用中代码格式丢失",
        "why": "代码缩进和语法高亮在聊天应用中不保留",
        "suggestion": "用代码块包裹 Ctrl+V 粘贴，或发送代码文件",
        "breakdown": [
            "缩进可能被聊天框裁剪",
            "代码高亮完全丢失",
            "建议用三个反引号包裹",
        ],
    },

    # ── markdown_editor ───────────────────────────────────────────
    ("rich_text", "markdown_editor"): {
        "risk_level": "medium",
        "prediction": "Markdown 编辑器通常会把基础富文本转换为 Markdown",
        "why": "Typora、Obsidian 等会转换常见标题、列表和强调格式，复杂样式支持不一致",
        "suggestion": "直接粘贴后检查表格、嵌套列表和图片",
        "breakdown": [
            "标题、列表和强调通常会转换为 Markdown",
            "复杂表格和嵌套列表可能需要手动调整",
            "内联样式和 class 属性不会保留",
        ],
    },
    ("plain_text", "markdown_editor"): {
        "risk_level": "none",
        "prediction": "Markdown 编辑器中正常粘贴",
        "why": "纯文本内容，Markdown 编辑器完全兼容",
        "suggestion": "Ctrl+V 直接粘贴",
        "breakdown": [],
    },
    ("structured_text", "markdown_editor"): {
        "risk_level": "none",
        "prediction": "Markdown 编辑器中完美粘贴",
        "why": "Markdown 编辑器原生支持 #/-/* 等语法，内容直接可编辑",
        "suggestion": "Ctrl+V 直接粘贴，无需额外处理",
        "breakdown": [],
    },
    ("code", "markdown_editor"): {
        "risk_level": "low",
        "prediction": "Markdown 编辑器中正常粘贴，建议包裹代码块",
        "why": "代码内容可正常粘贴，但建议用 ``` 包裹以保留格式",
        "suggestion": "Ctrl+V 粘贴后用 Ctrl+K 或手动添加代码块标记",
        "breakdown": [
            "建议用 ``` 包裹代码块以保留语法高亮",
            "行内代码用 ` 包裹",
        ],
    },

    # ── spreadsheet ───────────────────────────────────────────────
    ("rich_text", "spreadsheet"): {
        "risk_level": "high",
        "prediction": "表格中多列数据可能错位，换行符触发多行",
        "why": "检测到 <table>/<ul> 结构，粘贴到表格时列映射和换行处理复杂",
        "suggestion": "Ctrl+Shift+V 粘贴纯文本后手动调整列，或使用「分列」功能",
        "breakdown": [
            "<table> 多列可能坍为一列",
            "单元格内换行可能跳转到下一行",
            "Tab 分隔的数据需用「数据→分列」",
        ],
    },
    ("plain_text", "spreadsheet"): {
        "risk_level": "low",
        "prediction": "表格中正常粘贴，Tab 分隔的数据自动分列",
        "why": "纯文本粘贴，Tab 键自动识别为列分隔符，换行识别为行",
        "suggestion": "Ctrl+V 直接粘贴；若无 Tab 分隔，使用数据→分列",
        "breakdown": [
            "需带 Tab 分隔的文本才能自动分列",
            "逗号分隔的数据不会自动分列",
        ],
    },
    ("structured_text", "spreadsheet"): {
        "risk_level": "medium",
        "prediction": "表格中 Markdown 标记不解析，列表映射为多行",
        "why": "检测到 Markdown 列表标记（-/*），粘贴到表格时每项变成一行",
        "suggestion": "粘贴后使用「数据→分列」拆分列表标记，或先粘贴到文本编辑器整理",
        "breakdown": [
            "Markdown 列表每项会占据一个单元格行",
            "# 标题不自动变大，需手动设置格式",
        ],
    },
    ("code", "spreadsheet"): {
        "risk_level": "medium",
        "prediction": "表格中代码缩进丢失，多行代码映射为多行单元格",
        "why": "检测到代码模式，粘贴到表格时每行代码映射到一行单元格",
        "suggestion": "不推荐代码粘贴到表格；如必须，Ctrl+Shift+V 保留缩进",
        "breakdown": [
            "代码缩进（空格/Tab）在表格单元格中丢失",
            "代码高亮和语法着色完全丢失",
            "建议代码放在单独的代码编辑器中",
        ],
    },

    # ── presentation ──────────────────────────────────────────────
    ("rich_text", "presentation"): {
        "risk_level": "medium",
        "prediction": "演示文稿中字体可能丢失，文本框可能溢出",
        "why": "检测到 HTML 格式，演示文稿使用本地字体，非系统字体将回退",
        "suggestion": "粘贴后检查字体和文本框大小，必要时用「保留源格式」",
        "breakdown": [
            "非系统字体可能回退为默认字体（宋体/等线）",
            "文本框内容可能溢出边框",
            "段落间距规则与网页不同",
        ],
    },
    ("plain_text", "presentation"): {
        "risk_level": "none",
        "prediction": "演示文稿中正常粘贴",
        "why": "纯文本内容，演示文稿完全兼容",
        "suggestion": "Ctrl+V 直接粘贴，可按需调整字号",
        "breakdown": [],
    },
    ("structured_text", "presentation"): {
        "risk_level": "medium",
        "prediction": "演示文稿不解析 Markdown，显示为纯文本源码",
        "why": "检测到 Markdown 标记（#/-/*），演示文稿不渲染这些语法",
        "suggestion": "先粘贴到 Word 格式化后再复制到 PPT，或手动排版",
        "breakdown": [
            "# 标题显示为普通文本（不自动变大）",
            "列表标记（-/*）直接出现在幻灯片上",
            "代码块格式完全丢失",
        ],
    },
    ("code", "presentation"): {
        "risk_level": "low",
        "prediction": "演示文稿中代码以纯文本粘贴，无高亮",
        "why": "演示文稿不支持代码语法高亮，将作为普通文本处理",
        "suggestion": "Ctrl+Shift+V 粘贴纯文本，手动设置等宽字体",
        "breakdown": [
            "代码高亮完全丢失",
            "缩进保留但需手动设置为等宽字体（如 Consolas）",
        ],
    },
}

# ── Risk label display ─────────────────────────────────────────────────

_RISK_LABELS: dict[str, str] = {
    "high":   "⚠",
    "medium": "⚠",
    "low":    "⚠",
    "none":   "✓",
}

# Targets that can render a faithful visual preview.
_REAL_RENDER_TARGETS: set[str] = {"chrome", "markdown_editor", "terminal", "code_editor"}


def _build_preview_data(entry: dict, content_type: str, target: str) -> dict:
    """Build scenario preview metadata from an outcome entry.

    Returns:
        dict with summary, risks, render_type, suggestion.
    """
    breakdown = entry.get("breakdown", [])
    risks = list(breakdown)
    if not risks:
        risks = ["当前内容在该场景下风险较低"]

    render_type = "real" if target in _REAL_RENDER_TARGETS else "checklist"

    return {
        "summary": entry["prediction"],
        "risks": risks[:3],
        "render_type": render_type,
        "suggestion": entry["suggestion"],
    }


class OutcomePredictor:
    """Predict paste outcome for clipboard content.

    Input:  content_type (str), target (str)
    Output: AppOutput with prediction/why/suggestion/breakdown

    Lookup: COMPATIBILITY_MATRIX[(content_type, target)] first,
            fall back to _OUTCOME_MAP[content_type] otherwise.

    Performance: <1ms (two dict lookups max, zero IO, zero parsing)
    """

    def generate(
        self, content_type: str, target: str = "word",
    ) -> AppOutput:
        # 1. Matrix lookup (content_type × target) — specific
        matrix_key = (content_type, target)
        if matrix_key in COMPATIBILITY_MATRIX:
            entry = COMPATIBILITY_MATRIX[matrix_key]
        else:
            # 2. Fallback: content_type-only default (Word behavior)
            entry = _OUTCOME_MAP.get(content_type)

        if entry is None:
            entry = _OUTCOME_MAP["plain_text"]
            content_type = "plain_text"

        type_label = CONTENT_TYPES.get(content_type, content_type)
        risk_label = _RISK_LABELS.get(entry["risk_level"], "●")

        preview_data = _build_preview_data(entry, content_type, target)

        return AppOutput(
            risk_level=entry["risk_level"],
            risk_label=risk_label,
            content_type=content_type,
            content_type_label=type_label,
            target=target,
            primary_target=target,
            prediction=entry["prediction"],
            why=entry["why"],
            suggestion=entry["suggestion"],
            breakdown=entry.get("breakdown", []),
            preview_data=preview_data,
        )
