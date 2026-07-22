"""PreviewRenderer 运行时语言切换测试。"""

from src.explainer.preview_renderer import ClipboardContent, PreviewRenderer


def test_english_preview_localizes_renderer_owned_labels_but_keeps_user_text():
    result = PreviewRenderer().render(
        ClipboardContent(text="用户原文", content_type="plain_text"),
        "terminal",
        {"summary": "Pastes as plain text", "risks": [], "render_type": "real"},
        language="en-US",
    )
    assert "Terminal preview" in result.html
    assert "用户原文" in result.html
    assert "终端预览" not in result.html


def test_english_preview_checklist_translates_fixed_labels_only():
    result = PreviewRenderer().render(
        ClipboardContent(text="第一行\n第二行", content_type="plain_text"),
        "word",
        language="en-US",
    )
    assert "Word paste checklist" in result.html
    assert "Preserved structure" in result.html
    assert "Formatting that may be lost" in result.html


def test_english_preview_localizes_image_placeholder():
    content = ClipboardContent(
        html='<p>Hello</p><img src="clipboard-image.png">',
        content_type="rich_text",
    )
    chrome = PreviewRenderer().render(content, "chrome", language="en-US")
    terminal = PreviewRenderer().render(content, "terminal", language="en-US")

    for result in (chrome, terminal):
        assert "[Image]" in result.html
        assert "[图片]" not in result.html
