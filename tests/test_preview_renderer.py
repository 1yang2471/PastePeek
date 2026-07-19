"""Tests for PreviewRenderer — scenario-based paste preview rendering.

Covers high-fidelity targets (real render) and low-fidelity targets
(structured checklist), plus the HTML → Markdown converter.
"""

import pytest

from src.explainer.preview_renderer import (
    ClipboardContent,
    HtmlToMarkdown,
    PreviewRenderer,
    RenderedPreview,
)


@pytest.fixture
def renderer():
    return PreviewRenderer()


@pytest.fixture
def sample_html():
    return (
        "<html><body>"
        "<h2>核心功能</h2>"
        "<ul><li><b>格式检测</b> — 识别所有格式层</li>"
        "<li><a href='/preview'>预览</a>功能</li></ul>"
        "<hr>"
        "<p>了解更多信息</p>"
        "</body></html>"
    )


@pytest.fixture
def sample_markdown_text():
    return (
        "# 项目规划\n"
        "- 目标用户：内容创作者\n"
        "- 核心需求：格式预测\n"
        "> 注意：纯文本粘贴最安全\n"
    )


@pytest.fixture
def sample_code():
    return (
        "def process_clipboard(text: str) -> dict:\n"
        "    result = {}\n"
        "    for line in text.strip().split('\\n'):\n"
        "        if 'class ' in line:\n"
        "            result['class'] = line\n"
        "    return result\n"
    )


class TestRenderedPreviewTypes:
    """Basic dataclass sanity checks."""

    def test_rendered_preview_defaults(self):
        preview = RenderedPreview()
        assert preview.html == ""
        assert preview.is_rendered is False
        assert preview.summary == ""
        assert preview.risks == []

    def test_clipboard_content_defaults(self):
        content = ClipboardContent()
        assert content.text == ""
        assert content.html == ""
        assert content.content_type == "plain_text"


class TestHighFidelityTargets:
    """High-fidelity targets should produce is_rendered=True previews."""

    def test_chrome_renders_raw_html(self, renderer, sample_html):
        content = ClipboardContent(html=sample_html, content_type="rich_text")
        preview = renderer.render(content, "chrome")

        assert preview.is_rendered is True
        assert "<b>格式检测</b>" in preview.html
        assert "<ul>" in preview.html
        assert preview.summary != ""
        assert len(preview.risks) >= 1

    def test_markdown_editor_converts_html(self, renderer, sample_html):
        content = ClipboardContent(html=sample_html, content_type="rich_text")
        preview = renderer.render(content, "markdown_editor")

        assert preview.is_rendered is True
        assert "## 核心功能" in preview.html
        assert "**格式检测**" in preview.html
        assert "[预览](/preview)" in preview.html
        assert preview.summary != ""
        assert len(preview.risks) >= 1

    def test_terminal_renders_plain_text(self, renderer, sample_markdown_text):
        content = ClipboardContent(text=sample_markdown_text, content_type="structured_text")
        preview = renderer.render(content, "terminal")

        assert preview.is_rendered is True
        assert "# 项目规划" in preview.html
        assert "<pre" in preview.html
        assert preview.summary != ""
        assert len(preview.risks) >= 1

    def test_code_editor_preserves_indentation(self, renderer, sample_code):
        content = ClipboardContent(text=sample_code, content_type="code")
        preview = renderer.render(content, "code_editor")

        assert preview.is_rendered is True
        assert "def process_clipboard" in preview.html
        assert "<pre" in preview.html
        assert "    result = {}" in preview.html
        assert preview.summary != ""
        assert len(preview.risks) >= 1


class TestLowFidelityTargets:
    """Low-fidelity targets should produce structured checklists."""

    def test_word_returns_checklist(self, renderer, sample_html):
        content = ClipboardContent(html=sample_html, content_type="rich_text")
        preview = renderer.render(content, "word")

        assert preview.is_rendered is False
        assert "Word 粘贴清单" in preview.html
        assert "保留的结构" in preview.html
        assert "可能丢失的格式" in preview.html
        assert preview.summary != ""
        assert len(preview.risks) >= 1

    def test_presentation_returns_outline(self, renderer, sample_markdown_text):
        content = ClipboardContent(text=sample_markdown_text, content_type="structured_text")
        preview = renderer.render(content, "presentation")

        assert preview.is_rendered is False
        assert "幻灯片大纲" in preview.html
        assert "项目规划" in preview.html
        assert preview.summary != ""
        assert len(preview.risks) >= 1

    def test_chat_app_returns_plain_preview(self, renderer, sample_code):
        content = ClipboardContent(text=sample_code, content_type="code")
        preview = renderer.render(content, "chat_app")

        assert preview.is_rendered is False
        assert "聊天应用预览" in preview.html
        assert "def process_clipboard" in preview.html
        assert preview.summary != ""
        assert len(preview.risks) >= 1

    def test_spreadsheet_returns_structure_note(self, renderer, sample_markdown_text):
        content = ClipboardContent(text=sample_markdown_text, content_type="structured_text")
        preview = renderer.render(content, "spreadsheet")

        assert preview.is_rendered is False
        assert "电子表格结构说明" in preview.html
        assert "预计行数" in preview.html
        assert preview.summary != ""
        assert len(preview.risks) >= 1


class TestPreviewDataIntegration:
    """Preview data from OutcomePredictor should drive summary and risks."""

    def test_preview_data_summary_and_risks(self, renderer):
        content = ClipboardContent(text="hello", content_type="plain_text")
        preview_data = {
            "summary": "所有场景均正常",
            "risks": ["无风险", "可直接粘贴"],
            "render_type": "real",
            "suggestion": "Ctrl+V 直接粘贴",
        }
        preview = renderer.render(content, "chrome", preview_data=preview_data)

        assert preview.summary == "所有场景均正常"
        assert preview.risks == ["无风险", "可直接粘贴"]

    def test_preview_data_risks_capped_at_three(self, renderer):
        content = ClipboardContent(text="hello", content_type="plain_text")
        preview_data = {
            "summary": "测试",
            "risks": ["a", "b", "c", "d", "e"],
        }
        preview = renderer.render(content, "word", preview_data=preview_data)
        assert len(preview.risks) == 3


class TestFallbackBehavior:
    """Renderer must not crash and should fall back to a checklist."""

    def test_empty_content_does_not_crash(self, renderer):
        content = ClipboardContent()
        preview = renderer.render(content, "chrome")

        assert "无内容" in preview.html
        assert preview.summary != ""

    def test_unknown_target_falls_back(self, renderer):
        content = ClipboardContent(text="hello", content_type="plain_text")
        preview = renderer.render(content, "some_unknown_target")

        assert preview.is_rendered is False
        assert "未知目标预览" in preview.html
        assert "hello" in preview.html


class TestHtmlToMarkdown:
    """HTML → Markdown converter sanity tests."""

    def test_headings(self):
        md = HtmlToMarkdown().convert("<h1>Title</h1><h2>Subtitle</h2>")
        assert "# Title" in md
        assert "## Subtitle" in md

    def test_bold_and_italic(self):
        md = HtmlToMarkdown().convert("<p><strong>bold</strong> and <em>italic</em></p>")
        assert "**bold**" in md
        assert "*italic*" in md

    def test_link(self):
        md = HtmlToMarkdown().convert('<a href="https://example.com">link</a>')
        assert "[link](https://example.com)" in md

    def test_list(self):
        md = HtmlToMarkdown().convert("<ul><li>one</li><li>two</li></ul>")
        assert "- one" in md
        assert "- two" in md

    def test_ordered_list(self):
        md = HtmlToMarkdown().convert("<ol><li>first</li><li>second</li></ol>")
        assert "1. first" in md
        assert "2. second" in md

    def test_code_block(self):
        md = HtmlToMarkdown().convert("<pre>code line</pre>")
        assert "```" in md
        assert "code line" in md

    def test_blockquote(self):
        md = HtmlToMarkdown().convert("<blockquote>quote</blockquote>")
        assert "> quote" in md

    def test_strip_mode(self):
        text = HtmlToMarkdown(strip=True).convert("<p>plain <b>text</b></p>")
        assert text == "plain text"


@pytest.mark.parametrize(
    "target",
    [
        "chrome",
        "markdown_editor",
        "terminal",
        "code_editor",
        "word",
        "chat_app",
        "spreadsheet",
        "presentation",
    ],
)
def test_preview_html_uses_readable_explicit_typography(renderer, target):
    """场景预览的显式字号不得低于 9pt。"""
    content = ClipboardContent(
        text="标题\n正文",
        html="<h2>标题</h2><p>正文</p>",
        content_type="rich_text",
    )

    rendered = renderer.render(content, target)

    assert "font-size:8px" not in rendered.html
    assert "font-size:9px" not in rendered.html
