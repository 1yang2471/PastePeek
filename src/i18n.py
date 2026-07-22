"""PastePeek 运行时本地化资源。

本模块只保存由 PastePeek 生成的文案，不处理用户剪贴板正文。所有语言值
都经过白名单归一化，调用方不需要自行处理非法配置。
"""

from __future__ import annotations

SUPPORTED_LANGUAGES: tuple[str, ...] = ("zh-CN", "en-US")
DEFAULT_LANGUAGE = "zh-CN"


_MESSAGES: dict[str, dict[str, str]] = {
    "zh-CN": {
        "language_menu": "语言",
        "language_zh": "简体中文",
        "language_en": "English",
        "more_targets": "更多目标",
        "auto_detect": "自动检测",
        "minimize_hud": "最小化 HUD",
        "hide_hud_tooltip": "隐藏 HUD，继续监听",
        "hide_hud_accessible": "隐藏 HUD",
        "ready_tip": "提示：已就绪，等待剪贴板内容",
        "no_action": "当前内容无需处理",
        "more_actions": "其他操作",
        "action_strip_primary": "清洗为纯文本",
        "action_clean_url": "净化链接",
        "action_merge_primary": "合并为一行",
        "action_strip_more": "清洗格式",
        "action_merge_more": "合并换行",
        "operation_failed": "操作失败",
        "non_text_tag": "非文本",
        "non_text_prediction": "当前剪贴板包含图片、文件或音频，PastePeek 不会修改此内容",
        "non_text_why": "非文本内容由目标应用直接处理",
        "non_text_suggestion": "请在目标应用中粘贴后确认结果",
        "non_text_breakdown": "暂不提供图片、文件或音频的效果预览",
        "tray_hide": "隐藏 PastePeek",
        "tray_show": "显示 PastePeek",
        "tray_startup": "开机启动",
        "tray_exit": "退出 PastePeek",
        "startup_error": "开机启动设置失败：{error}",
        "startup_unsupported": "当前运行方式不支持开机启动",
        "removed_tracking": "已移除 {count} 个追踪参数: {names}",
        "rich_text_converted": "；已转为纯文本",
        "sequence_changed": "剪贴板内容已变化，请查看最新预览后重试",
        "clipboard_unavailable": "无法确认剪贴板当前内容，请稍后重试",
        "sequence_unavailable": "无法确认剪贴板版本，请稍后重试",
        "not_applicable": "当前内容不适用此操作，已保留原剪贴板",
        "unknown_action": "未知操作: {action}",
        "binary_preserved": "剪贴板包含图片、文件或音频，已保留原内容",
        "empty_content": "处理后内容为空，已取消操作",
        "invalid_url": "剪贴板内容不是有效的 HTTP(S) URL",
        "url_no_query": "URL 无查询参数",
        "url_protected": "链接包含签名或令牌，已保留原内容",
        "url_ambiguous": "URL 查询结构不明确，已保留原内容",
        "url_no_tracking": "URL 无追踪参数",
        "url_parse_failed": "URL 解析失败: {error}",
        "clipboard_busy": "剪贴板被其他程序占用，请稍后重试",
        "clipboard_busy_restored": "剪贴板被其他程序占用，写入失败；已恢复原内容",
        "clipboard_busy_unrestored": "剪贴板被其他程序占用，写入失败且无法恢复原内容",
        "clipboard_write_failed": "剪贴板写入失败，已恢复原内容",
        "clipboard_write_unrestored": "剪贴板写入失败且无法恢复原内容",
        "protected_content": "剪贴板包含代码或结构化内容，已保留原内容",
        "already_plain": "已经是纯文本",
        "action_failed": "剪贴板处理失败",
        "removed_formats": "（已移除 {formats} 格式）",
        "converted_plain": "已转为纯文本{detail}",
        "merged_lines": "已合并为 1 行",
        "already_single_line": "已经是单行文本",
        "preview_ready": "预览生成完成",
        "preview_failed": "预览生成失败，已切换为结构化清单",
        "preview_empty": "（无内容）",
        "image_placeholder": "[图片]",
        "markdown_preview": "Markdown 源码预览",
        "terminal_preview": "终端预览（等宽字体）",
        "code_preview": "代码编辑器预览",
        "word_checklist": "Word 粘贴清单",
        "kept_structure": "保留的结构",
        "lost_format": "可能丢失的格式",
        "slide_outline": "幻灯片大纲",
        "chat_preview": "聊天应用预览",
        "chat_hint": "提示：部分格式可能转为纯文本或文件",
        "spreadsheet_info": "电子表格结构说明",
        "estimated_rows": "预计行数：约 {rows} 行",
        "column_mapping": "列映射：依赖 Tab/逗号分隔符",
        "spreadsheet_risk": "风险：多列可能错位，单元格内换行会拆分",
        "unknown_preview": "未知目标预览",
        "default_preview_risk_1": "目标应用可能不保留所有格式",
        "default_preview_risk_2": "建议先在小范围测试粘贴效果",
        "low_risk_note": "当前内容在该场景下风险较低",
    },
    "en-US": {
        "language_menu": "Language",
        "language_zh": "Simplified Chinese",
        "language_en": "English",
        "more_targets": "More targets",
        "auto_detect": "Auto-detect",
        "minimize_hud": "Minimize HUD",
        "hide_hud_tooltip": "Hide HUD and keep monitoring",
        "hide_hud_accessible": "Hide HUD",
        "ready_tip": "Ready - waiting for clipboard content",
        "no_action": "No action needed for this content",
        "more_actions": "More actions",
        "action_strip_primary": "Convert to plain text",
        "action_clean_url": "Clean link",
        "action_merge_primary": "Merge into one line",
        "action_strip_more": "Strip formatting",
        "action_merge_more": "Merge lines",
        "operation_failed": "Operation failed",
        "non_text_tag": "Non-text",
        "non_text_prediction": "The clipboard contains an image, file, or audio; PastePeek will not modify it",
        "non_text_why": "Non-text content is handled directly by the target app",
        "non_text_suggestion": "Paste in the target app and confirm the result",
        "non_text_breakdown": "Visual previews for images, files, and audio are not available",
        "tray_hide": "Hide PastePeek",
        "tray_show": "Show PastePeek",
        "tray_startup": "Start with Windows",
        "tray_exit": "Exit PastePeek",
        "startup_error": "Failed to update startup setting",
        "startup_unsupported": "Startup is available only for the portable EXE",
        "removed_tracking": "Removed {count} tracking parameters: {names}",
        "rich_text_converted": "; converted to plain text",
        "sequence_changed": "Clipboard content changed; review the latest preview and try again",
        "clipboard_unavailable": "Unable to verify the current clipboard; try again later",
        "sequence_unavailable": "Unable to verify the clipboard version; try again later",
        "not_applicable": "This action does not apply; the original clipboard was preserved",
        "unknown_action": "Unknown action: {action}",
        "binary_preserved": "The clipboard contains an image, file, or audio; the original was preserved",
        "empty_content": "The result would be empty; the action was cancelled",
        "invalid_url": "Clipboard content is not a valid HTTP(S) URL",
        "url_no_query": "The URL has no query parameters",
        "url_protected": "The link contains a signature or token; the original was preserved",
        "url_ambiguous": "The URL query structure is ambiguous; the original was preserved",
        "url_no_tracking": "The URL has no tracking parameters",
        "url_parse_failed": "URL parsing failed: {error}",
        "clipboard_busy": "The clipboard is in use by another app; try again later",
        "clipboard_busy_restored": "The clipboard is in use; writing failed and the original was restored",
        "clipboard_busy_unrestored": "The clipboard is in use; writing failed and the original could not be restored",
        "clipboard_write_failed": "Clipboard write failed; the original was restored",
        "clipboard_write_unrestored": "Clipboard write failed and the original could not be restored",
        "protected_content": "The clipboard contains code or structured content; the original was preserved",
        "already_plain": "The content is already plain text",
        "action_failed": "Clipboard processing failed",
        "removed_formats": " (removed {formats} formats)",
        "converted_plain": "Converted to plain text{detail}",
        "merged_lines": "Merged into 1 line",
        "already_single_line": "The content is already a single line",
        "preview_ready": "Preview ready",
        "preview_failed": "Preview failed; switched to a structured checklist",
        "preview_empty": "(empty)",
        "image_placeholder": "[Image]",
        "markdown_preview": "Markdown source preview",
        "terminal_preview": "Terminal preview (monospace)",
        "code_preview": "Code editor preview",
        "word_checklist": "Word paste checklist",
        "kept_structure": "Preserved structure",
        "lost_format": "Formatting that may be lost",
        "slide_outline": "Slide outline",
        "chat_preview": "Chat app preview",
        "chat_hint": "Note: some formatting may become plain text or a file",
        "spreadsheet_info": "Spreadsheet structure",
        "estimated_rows": "Estimated rows: about {rows}",
        "column_mapping": "Column mapping: depends on Tab/comma separators",
        "spreadsheet_risk": "Risk: columns may shift and cell line breaks may split rows",
        "unknown_preview": "Unknown target preview",
        "default_preview_risk_1": "The target app may not preserve all formatting",
        "default_preview_risk_2": "Test the paste in a small area first",
        "low_risk_note": "This content has low risk in this scenario",
    },
}


_CONTENT_TYPES = {
    "zh-CN": {
        "rich_text": "富文本",
        "plain_text": "纯文本",
        "structured_text": "结构化",
        "code": "代码",
    },
    "en-US": {
        "rich_text": "Rich text",
        "plain_text": "Plain text",
        "structured_text": "Structured text",
        "code": "Code",
    },
}

_TARGET_LABELS = {
    "zh-CN": {
        "word": "Word",
        "chrome": "浏览器",
        "code_editor": "代码编辑器",
        "terminal": "终端",
        "chat_app": "聊天应用",
        "markdown_editor": "Markdown",
        "spreadsheet": "表格",
        "presentation": "演示",
        "unknown": "未知应用",
    },
    "en-US": {
        "word": "Word",
        "chrome": "Browser",
        "code_editor": "Code editor",
        "terminal": "Terminal",
        "chat_app": "Chat app",
        "markdown_editor": "Markdown",
        "spreadsheet": "Spreadsheet",
        "presentation": "Presentation",
        "unknown": "Unknown app",
    },
}

_TARGET_COMPACT = {
    "zh-CN": {
        "word": "Word",
        "chrome": "浏览器",
        "code_editor": "代码",
        "terminal": "终端",
        "markdown_editor": "MD",
    },
    "en-US": {
        "word": "Word",
        "chrome": "Web",
        "code_editor": "Code",
        "terminal": "Term",
        "markdown_editor": "MD",
    },
}

_TARGET_GROUPS = {
    "zh-CN": {
        "document": "文档办公",
        "editor": "编辑器",
        "communication": "通讯",
    },
    "en-US": {
        "document": "Documents",
        "editor": "Editors",
        "communication": "Communication",
    },
}

_RISK_LABELS = {
    "zh-CN": {
        "high": "高风险",
        "medium": "中风险",
        "low": "低风险",
        "none": "无明显风险",
    },
    "en-US": {
        "high": "High risk",
        "medium": "Medium risk",
        "low": "Low risk",
        "none": "No obvious risk",
    },
}


def normalize_language(value: object) -> str:
    """把配置或外部输入归一化为受支持的语言值。"""
    if value in SUPPORTED_LANGUAGES:
        return str(value)
    if isinstance(value, str) and value.strip().lower() in {"en", "en-us"}:
        return "en-US"
    if isinstance(value, str) and value.strip().lower() in {"zh", "zh-cn"}:
        return DEFAULT_LANGUAGE
    return DEFAULT_LANGUAGE


def translate(key: str, language: str = DEFAULT_LANGUAGE, **kwargs: object) -> str:
    """返回固定文案；未知键安全回退到产品名而不是暴露内部 key。"""
    locale = normalize_language(language)
    template = _MESSAGES.get(locale, {}).get(key)
    if template is None:
        template = _MESSAGES[DEFAULT_LANGUAGE].get(key, "PastePeek")
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return template


def content_type_label(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    locale = normalize_language(language)
    return _CONTENT_TYPES.get(locale, _CONTENT_TYPES[DEFAULT_LANGUAGE]).get(key, key)


def target_label(
    key: str,
    language: str = DEFAULT_LANGUAGE,
    *,
    compact: bool = False,
) -> str:
    locale = normalize_language(language)
    labels = _TARGET_COMPACT if compact else _TARGET_LABELS
    return labels.get(locale, labels[DEFAULT_LANGUAGE]).get(key, key)


def target_group_label(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    locale = normalize_language(language)
    return _TARGET_GROUPS.get(locale, _TARGET_GROUPS[DEFAULT_LANGUAGE]).get(key, key)


def risk_label(level: str, language: str = DEFAULT_LANGUAGE) -> str:
    locale = normalize_language(language)
    return _RISK_LABELS.get(locale, _RISK_LABELS[DEFAULT_LANGUAGE]).get(level, level)
