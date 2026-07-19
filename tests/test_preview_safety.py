"""场景预览的本地隐私边界测试。"""

from src.explainer.preview_renderer import ClipboardContent, PreviewRenderer


def test_chrome_preview_drops_remote_image_resources():
    """预览不得因剪贴板 HTML 加载远程图片。"""
    content = ClipboardContent(
        html=(
            '<p>正文</p><img src="https://tracker.example/pixel.png" '
            'alt="示意图">'
        ),
        content_type="rich_text",
    )

    preview = PreviewRenderer().render(content, "chrome")

    assert "正文" in preview.html
    assert "tracker.example" not in preview.html
    assert "[图片]" in preview.html


def test_chrome_preview_drops_active_content_but_keeps_document_structure():
    """预览应移除主动内容，同时保留可读文档结构。"""
    content = ClipboardContent(
        html=(
            '<style>p{background:url("https://tracker.example/bg.png")}</style>'
            '<script>fetch("https://tracker.example/collect")</script>'
            '<link rel="stylesheet" href="https://tracker.example/site.css">'
            '<meta http-equiv="refresh" content="0;url=https://tracker.example">'
            '<base href="https://tracker.example/">'
            '<iframe src="https://tracker.example/frame">隐藏框架</iframe>'
            '<object data="file:///C:/secret.txt">隐藏对象</object>'
            '<embed src="file:///C:/secret.pdf">'
            '<h2 style="background:url(file:///C:/secret.png)">标题</h2>'
            '<p onclick="fetch(\'https://tracker.example/click\')">正文</p>'
            '<ul><li><strong>重点</strong></li></ul>'
        ),
        content_type="rich_text",
    )

    preview = PreviewRenderer().render(content, "chrome")

    assert "tracker.example" not in preview.html
    assert "file:///" not in preview.html
    assert "fetch(" not in preview.html
    assert "onclick" not in preview.html
    assert "<h2>标题</h2>" in preview.html
    assert "<p>正文</p>" in preview.html
    assert "<ul><li><strong>重点</strong></li></ul>" in preview.html


def test_terminal_preview_preserves_html_paragraphs_breaks_and_lists():
    """转为纯文本时不应把文档结构挤成一行。"""
    content = ClipboardContent(
        html=(
            "<p>第一段<br>第二行</p>"
            "<p>第二段</p>"
            "<ul><li>苹果</li><li>香蕉</li></ul>"
        ),
        content_type="rich_text",
    )

    preview = PreviewRenderer().render(content, "terminal")

    assert "第一段<br>第二行" in preview.html
    assert "第二行<br><br>第二段" in preview.html
    assert "- 苹果<br>- 香蕉" in preview.html
    assert "<p>" not in preview.html
    assert "<li>" not in preview.html


def test_self_closing_blocked_tag_does_not_hide_following_plain_text():
    """自闭合危险标签被删除后，后续正文仍应进入纯文本预览。"""
    content = ClipboardContent(
        html=(
            '<iframe src="https://tracker.example/frame" />'
            '<object data="file:///C:/secret.txt" />'
            "<p>可见正文</p>"
        ),
        content_type="rich_text",
    )

    preview = PreviewRenderer().render(content, "terminal")

    assert "可见正文" in preview.html
    assert "tracker.example" not in preview.html
    assert "file:///" not in preview.html
