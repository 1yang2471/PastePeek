"""PreviewRenderer — scenario-based paste preview renderer.

Produces a visual preview of how clipboard content will look when pasted
into a specific target application.

High-fidelity targets are rendered as-is:
  chrome          → raw HTML in QTextBrowser
  markdown_editor → HTML → Markdown source / simple rendering
  terminal        → plain text, monospaced, newlines preserved
  code_editor     → monospaced code block, indentation preserved

Low-fidelity targets fall back to a structured checklist:
  word            → retained/lost format checklist
  presentation    → outline-style content list
  chat_app        → simplified rich text / plain text + risk notes
  spreadsheet     → table structure description + risk notes
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class ClipboardContent:
    """Minimal clipboard snapshot passed to the preview renderer."""

    text: str = ""
    html: str = ""
    content_type: str = "plain_text"


@dataclass
class RenderedPreview:
    """Result of a preview render operation."""

    html: str = ""
    is_rendered: bool = False
    summary: str = ""
    risks: list[str] = field(default_factory=list)


class _PreviewHtmlSanitizer(HTMLParser):
    """保留文档结构，同时切断剪贴板 HTML 的主动内容与资源引用。"""

    _ALLOWED_TAGS = {
        "a",
        "b",
        "blockquote",
        "br",
        "code",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "sub",
        "sup",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "u",
        "ul",
    }
    _BLOCKED_CONTENT_TAGS = {"script", "style", "iframe", "object"}
    _VOID_TAGS = {"br", "hr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self._blocked_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._blocked_stack:
            if tag in self._BLOCKED_CONTENT_TAGS:
                self._blocked_stack.append(tag)
            return
        if tag in self._BLOCKED_CONTENT_TAGS:
            self._blocked_stack.append(tag)
            return
        if tag == "img":
            self.parts.append("<span>[图片]</span>")
            return
        if tag in self._ALLOWED_TAGS:
            self.parts.append(f"<{tag}>")

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.lower()
        if self._blocked_stack or tag in self._BLOCKED_CONTENT_TAGS:
            return
        if tag == "img":
            self.parts.append("<span>[图片]</span>")
            return
        if tag in self._ALLOWED_TAGS:
            self.parts.append(f"<{tag}>")
            if tag not in self._VOID_TAGS:
                self.parts.append(f"</{tag}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._blocked_stack:
            if tag == self._blocked_stack[-1]:
                self._blocked_stack.pop()
            return
        if tag in self._ALLOWED_TAGS and tag not in self._VOID_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self._blocked_stack:
            self.parts.append(html.escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if not self._blocked_stack:
            self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self._blocked_stack:
            self.parts.append(f"&#{name};")

    def get_html(self) -> str:
        return "".join(self.parts)


class _HtmlToPlainTextParser(HTMLParser):
    """把 HTML 转为保留段落、列表和表格边界的纯文本。"""

    _BLOCKED_CONTENT_TAGS = {"script", "style", "iframe", "object"}
    _PARAGRAPH_TAGS = {
        "blockquote",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "pre",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._blocked_stack: list[str] = []
        self._table_cell_index = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._blocked_stack:
            if tag in self._BLOCKED_CONTENT_TAGS:
                self._blocked_stack.append(tag)
            return
        if tag in self._BLOCKED_CONTENT_TAGS:
            self._blocked_stack.append(tag)
            return
        if tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self._ensure_newlines(1)
            self.parts.append("- ")
        elif tag == "tr":
            self._ensure_newlines(1)
            self._table_cell_index = 0
        elif tag in {"td", "th"}:
            if self._table_cell_index:
                self.parts.append("\t")
            self._table_cell_index += 1
        elif tag == "img":
            self.parts.append("[图片]")
        elif tag in self._PARAGRAPH_TAGS:
            self._ensure_newlines(2)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.lower()
        if self._blocked_stack or tag in self._BLOCKED_CONTENT_TAGS:
            return
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._blocked_stack:
            if tag == self._blocked_stack[-1]:
                self._blocked_stack.pop()
            return
        if tag == "li":
            self._ensure_newlines(1)
        elif tag == "tr":
            self._ensure_newlines(1)
            self._table_cell_index = 0
        elif tag in self._PARAGRAPH_TAGS or tag in {"ol", "ul"}:
            self._ensure_newlines(2)

    def handle_data(self, data: str) -> None:
        if not self._blocked_stack:
            self.parts.append(data)

    def _ensure_newlines(self, count: int) -> None:
        current = "".join(self.parts)
        trailing = len(current) - len(current.rstrip("\n"))
        if trailing < count and current:
            self.parts.append("\n" * (count - trailing))

    def get_text(self) -> str:
        text = "".join(self.parts).replace("\xa0", " ")
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()


# Targets where we can render a faithful preview.
_HIGH_FIDELITY_TARGETS: set[str] = {
    "chrome",
    "markdown_editor",
    "terminal",
    "code_editor",
}

# Targets where only a structured checklist is practical.
_LOW_FIDELITY_TARGETS: set[str] = {
    "word",
    "presentation",
    "chat_app",
    "spreadsheet",
}

# Default preview copy (used when no preview_data is supplied).
_DEFAULT_SUMMARY = "预览生成完成"
_DEFAULT_RISKS = [
    "目标应用可能不保留所有格式",
    "建议先在小范围测试粘贴效果",
]


class PreviewRenderer:
    """Render a target-scenario preview for clipboard content.

    The renderer never raises; if rendering fails it falls back to a
    safe structured checklist.
    """

    def render(
        self,
        content: ClipboardContent,
        target: str,
        preview_data: dict | None = None,
    ) -> RenderedPreview:
        """Render a preview for ``content`` pasted into ``target``.

        Args:
            content: Clipboard snapshot (text/html/type).
            target: Target application key (e.g. "chrome", "word").
            preview_data: Optional copy from OutcomePredictor containing
                ``summary``, ``risks``, ``render_type``, ``suggestion``.

        Returns:
            RenderedPreview with HTML, render mode, summary and risks.
        """
        try:
            return self._render_safe(content, target, preview_data)
        except Exception:
            return self._fallback_checklist(content, target, preview_data)

    # ── Internal dispatch ──────────────────────────────────────────────

    def _render_safe(
        self,
        content: ClipboardContent,
        target: str,
        preview_data: dict | None,
    ) -> RenderedPreview:
        summary, risks = self._extract_summary_and_risks(preview_data)

        if target == "chrome":
            html_preview = self._render_chrome(content)
        elif target == "markdown_editor":
            html_preview = self._render_markdown(content)
        elif target == "terminal":
            html_preview = self._render_terminal(content)
        elif target == "code_editor":
            html_preview = self._render_code_editor(content)
        elif target in _LOW_FIDELITY_TARGETS:
            html_preview = self._render_structured_checklist(content, target)
        else:
            html_preview = self._render_unknown(content)

        is_rendered = target in _HIGH_FIDELITY_TARGETS
        return RenderedPreview(
            html=html_preview,
            is_rendered=is_rendered,
            summary=summary,
            risks=risks,
        )

    def _fallback_checklist(
        self,
        content: ClipboardContent,
        target: str,
        preview_data: dict | None,
    ) -> RenderedPreview:
        """Graceful fallback when a real render fails."""
        summary, risks = self._extract_summary_and_risks(preview_data)
        return RenderedPreview(
            html=self._render_structured_checklist(content, target),
            is_rendered=False,
            summary=summary or "预览生成失败，已切换为结构化清单",
            risks=risks or _DEFAULT_RISKS,
        )

    # ── High-fidelity renderers ────────────────────────────────────────

    def _render_chrome(self, content: ClipboardContent) -> str:
        """Chrome can render the raw HTML directly."""
        source = (content.html or content.text).strip()
        if not source:
            return self._wrap_html("<p style='color:#888;'>（无内容）</p>")

        # If we only have plain text, present it as a simple document.
        if not content.html:
            return self._wrap_html(f"<pre style='white-space:pre-wrap;'>{html.escape(source)}</pre>")

        sanitizer = _PreviewHtmlSanitizer()
        sanitizer.feed(source)
        sanitizer.close()
        return self._wrap_html(sanitizer.get_html())

    def _render_markdown(self, content: ClipboardContent) -> str:
        """Render as Markdown source (HTML → Markdown if HTML is present)."""
        if content.html:
            md = HtmlToMarkdown().convert(content.html)
        else:
            md = content.text

        md = md.strip() or "（无内容）"
        escaped = html.escape(md).replace("\n", "<br>")
        body = (
            "<div style='color:#666; font-size:9pt; margin-bottom:4px;'>"
            "Markdown 源码预览</div>"
            f"<pre style='white-space:pre-wrap; word-wrap:break-word; margin:0;'>"
            f"{escaped}</pre>"
        )
        return self._wrap_html(body)

    def _render_terminal(self, content: ClipboardContent) -> str:
        """Terminal: plain text, monospaced, newlines preserved."""
        text = self._extract_plain_text(content)
        if not text:
            return self._wrap_html("<p style='color:#888;'>（无内容）</p>")

        escaped = html.escape(text).replace("\n", "<br>")
        body = (
            "<div style='color:#666; font-size:9pt; margin-bottom:4px;'>"
            "终端预览（等宽字体）</div>"
            f"<pre style='white-space:pre-wrap; word-wrap:break-word; font-family:Consolas,monospace; margin:0;'>"
            f"{escaped}</pre>"
        )
        return self._wrap_html(body)

    def _render_code_editor(self, content: ClipboardContent) -> str:
        """Code editor: monospaced code block, indentation preserved."""
        text = self._extract_plain_text(content)
        if not text:
            return self._wrap_html("<p style='color:#888;'>（无内容）</p>")

        escaped = html.escape(text).replace("\n", "<br>")
        body = (
            "<div style='color:#666; font-size:9pt; margin-bottom:4px;'>"
            "代码编辑器预览</div>"
            f"<pre style='white-space:pre-wrap; word-wrap:break-word; font-family:Consolas,monospace; background:#f5f5f5; padding:4px; border-radius:3px; margin:0;'>"
            f"{escaped}</pre>"
        )
        return self._wrap_html(body)

    # ── Low-fidelity structured checklists ─────────────────────────────

    def _render_structured_checklist(self, content: ClipboardContent, target: str) -> str:
        """Build a structured checklist for low-fidelity targets."""
        if target == "word":
            return self._render_word_checklist(content)
        if target == "presentation":
            return self._render_presentation_checklist(content)
        if target == "chat_app":
            return self._render_chat_checklist(content)
        if target == "spreadsheet":
            return self._render_spreadsheet_checklist(content)
        return self._render_unknown(content)

    def _render_word_checklist(self, content: ClipboardContent) -> str:
        retained = [
            "纯文本字符",
            "基本段落结构",
            "部分加粗/斜体",
        ]
        lost = [
            "复杂列表缩进",
            "HTML 表格样式",
            "内联 CSS 样式",
        ]
        return self._build_checklist("Word", "保留的结构", retained, "可能丢失的格式", lost)

    def _render_presentation_checklist(self, content: ClipboardContent) -> str:
        outline = self._extract_outline(content)
        lines = ["<b>幻灯片大纲</b>"]
        for item in outline[:8]:
            lines.append(f"• {html.escape(item)}")
        if len(outline) > 8:
            lines.append("...")
        body = "<br>".join(lines)
        return self._wrap_html(body)

    def _render_chat_checklist(self, content: ClipboardContent) -> str:
        text = self._extract_plain_text(content)
        snippet = text[:300].strip() or "（无内容）"
        escaped = html.escape(snippet).replace("\n", "<br>")
        body = (
            "<b>聊天应用预览</b><br>"
            f"<div style='white-space:pre-wrap; word-wrap:break-word; margin-top:4px;'>"
            f"{escaped}</div>"
            "<div style='color:#666; font-size:9pt; margin-top:4px;'>"
            "提示：部分格式可能转为纯文本或文件</div>"
        )
        return self._wrap_html(body)

    def _render_spreadsheet_checklist(self, content: ClipboardContent) -> str:
        rows = self._estimate_table_rows(content)
        body = (
            "<b>电子表格结构说明</b><br>"
            f"预计行数：约 {rows} 行<br>"
            "列映射：依赖 Tab/逗号分隔符<br>"
            "<span style='color:#666; font-size:9pt;'>"
            "风险：多列可能错位，单元格内换行会拆分</span>"
        )
        return self._wrap_html(body)

    def _render_unknown(self, content: ClipboardContent) -> str:
        text = self._extract_plain_text(content)[:300] or "（无内容）"
        escaped = html.escape(text).replace("\n", "<br>")
        return self._wrap_html(
            f"<b>未知目标预览</b><br>"
            f"<pre style='white-space:pre-wrap; margin:0;'>{escaped}</pre>"
        )

    # ── Helpers ────────────────────────────────────────────────────────

    def _extract_summary_and_risks(
        self, preview_data: dict | None
    ) -> tuple[str, list[str]]:
        if preview_data:
            summary = preview_data.get("summary", "")
            risks = preview_data.get("risks", [])
        else:
            summary, risks = "", []
        if not summary:
            summary = _DEFAULT_SUMMARY
        if not risks:
            risks = list(_DEFAULT_RISKS)
        return summary, risks[:3]

    def _extract_plain_text(self, content: ClipboardContent) -> str:
        if content.text:
            return content.text
        if content.html:
            return HtmlToMarkdown(strip=True).convert(content.html)
        return ""

    def _extract_outline(self, content: ClipboardContent) -> list[str]:
        text = self._extract_plain_text(content).strip()
        if not text:
            return []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines

    def _estimate_table_rows(self, content: ClipboardContent) -> int:
        text = self._extract_plain_text(content)
        if not text:
            return 0
        return max(1, len([line for line in text.splitlines() if line.strip()]))

    def _build_checklist(
        self,
        title: str,
        kept_label: str,
        kept: list[str],
        lost_label: str,
        lost: list[str],
    ) -> str:
        kept_items = "<br>".join(f"✓ {html.escape(item)}" for item in kept)
        lost_items = "<br>".join(f"✗ {html.escape(item)}" for item in lost)
        body = (
            f"<b>{html.escape(title)} 粘贴清单</b><br><br>"
            f"<div style='color:#00aa55;'>{html.escape(kept_label)}</div>"
            f"<div style='margin-left:8px;'>{kept_items}</div><br>"
            f"<div style='color:#D32F2F;'>{html.escape(lost_label)}</div>"
            f"<div style='margin-left:8px;'>{lost_items}</div>"
        )
        return self._wrap_html(body)

    def _wrap_html(self, body: str) -> str:
        return (
            "<html><body style='font-family:Segoe UI,Microsoft YaHei,sans-serif; "
            "font-size:9pt; color:#1a1a1a; margin:0;'>"
            f"{body}"
            "</body></html>"
        )


# ── HTML → Markdown converter ──────────────────────────────────────────

class HtmlToMarkdown:
    """Lightweight HTML → Markdown converter using the standard library.

    Handles common tags: p, br, strong/b, em/i, a, ul, ol, li, h1-h6,
    code, pre, blockquote, table.
    """

    def __init__(self, strip: bool = False):
        """Args:
            strip: If True, return plain text instead of Markdown.
        """
        self.strip = strip

    def convert(self, html_text: str) -> str:
        text = html_text
        # Strip scripts/styles first.
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", text, flags=re.I)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.I)

        if self.strip:
            return self._plain_text(text)

        # Headings
        for level in range(6, 0, -1):
            tag = f"h{level}"
            text = re.sub(
                rf"<{tag}[^>]*>([\s\S]*?)</{tag}>",
                lambda m, lvl=level: f"{'#' * lvl} {self._inline(m.group(1))}\n\n",
                text,
                flags=re.I,
            )

        # Block elements
        text = re.sub(
            r"<pre[^>]*>([\s\S]*?)</pre>",
            lambda m: f"```\n{self._strip_tags(m.group(1)).strip()}\n```\n\n",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"<blockquote[^>]*>([\s\S]*?)</blockquote>",
            lambda m: self._quote_block(m.group(1)),
            text,
            flags=re.I,
        )
        text = re.sub(
            r"<table[^>]*>([\s\S]*?)</table>",
            lambda m: self._table_block(m.group(1)),
            text,
            flags=re.I,
        )
        text = re.sub(
            r"<ul[^>]*>([\s\S]*?)</ul>",
            lambda m: self._list_block(m.group(1), unordered=True),
            text,
            flags=re.I,
        )
        text = re.sub(
            r"<ol[^>]*>([\s\S]*?)</ol>",
            lambda m: self._list_block(m.group(1), unordered=False),
            text,
            flags=re.I,
        )
        text = re.sub(
            r"<p[^>]*>([\s\S]*?)</p>",
            lambda m: f"{self._inline(m.group(1))}\n\n",
            text,
            flags=re.I,
        )

        # Convert remaining inline markup (links, bold, italic, code) and
        # strip any leftover tags (div, span, etc.).
        text = self._inline(text)
        text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
        return text

    def _plain_text(self, html_text: str) -> str:
        parser = _HtmlToPlainTextParser()
        parser.feed(html_text)
        parser.close()
        return parser.get_text()

    def _strip_tags(self, text: str) -> str:
        return re.sub(r"<[^>]+>", "", text)

    def _inline(self, text: str) -> str:
        # Bold / italic
        text = re.sub(
            r"<(strong|b)[^>]*>([\s\S]*?)</\1>",
            r"**\2**",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"<(em|i)[^>]*>([\s\S]*?)</\1>",
            r"*\2*",
            text,
            flags=re.I,
        )
        # Code inline
        text = re.sub(
            r"<code[^>]*>([\s\S]*?)</code>",
            r"`\1`",
            text,
            flags=re.I,
        )
        # Links
        text = re.sub(
            r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>([\s\S]*?)</a>",
            r"[\2](\1)",
            text,
            flags=re.I,
        )
        # Line breaks inside inline context
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        return self._strip_tags(text).strip()

    def _quote_block(self, html_text: str) -> str:
        inner = self.convert(html_text).strip()
        lines = [f"> {line}" for line in inner.splitlines()]
        return "\n".join(lines) + "\n\n"

    def _list_block(self, html_text: str, unordered: bool) -> str:
        items = re.findall(r"<li[^>]*>([\s\S]*?)</li>", html_text, flags=re.I)
        lines: list[str] = []
        for i, item in enumerate(items, start=1):
            marker = "-" if unordered else f"{i}."
            lines.append(f"{marker} {self._inline(item)}")
        return "\n".join(lines) + "\n\n"

    def _table_block(self, html_text: str) -> str:
        """Convert an HTML table fragment to a Markdown table."""
        rows: list[list[str]] = []
        for tr_match in re.finditer(r"<tr[^>]*>([\s\S]*?)</tr>", html_text, flags=re.I):
            tr = tr_match.group(1)
            th_cells = re.findall(r"<th[^>]*>([\s\S]*?)</th>", tr, flags=re.I)
            td_cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr, flags=re.I)
            cells = th_cells if th_cells else td_cells
            if cells:
                rows.append([self._inline(cell).strip() for cell in cells])
        if not rows:
            return ""
        lines: list[str] = []
        lines.append("| " + " | ".join(rows[0]) + " |")
        lines.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
        start = 1
        for row in rows[start:]:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines) + "\n\n"
