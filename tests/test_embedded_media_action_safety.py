"""富文本内嵌媒体在执行层的安全契约。"""

import pytest

from src.manipulator import text_toolkit
from tests.test_text_toolkit_contract import MemoryClipboard


@pytest.mark.parametrize(
    ("rich_format", "payload"),
    [
        (text_toolkit.CF_HTML, b"<p>text</p><img src='data:image/png;base64,AA=='>"),
        (text_toolkit.CF_HTML, b"<p>text</p><object data='file.bin'></object>"),
        (text_toolkit.CF_RTF, b"{\\rtf1 text {\\pict data}}"),
        (text_toolkit.CF_RTF, b"{\\rtf1 text {\\object data}}"),
    ],
)
@pytest.mark.parametrize(
    ("action", "source"),
    [
        (text_toolkit.clean_url, "https://a.com/p?utm_source=test"),
        (text_toolkit.strip_formats, "正文"),
        (text_toolkit.merge_lines, "第一行\n第二行"),
    ],
)
def test_embedded_media_is_never_removed_by_action(
    monkeypatch,
    rich_format,
    payload,
    action,
    source,
):
    """内嵌媒体存在时三项操作都必须失败关闭。"""
    original = {
        MemoryClipboard.CF_UNICODETEXT: source,
        rich_format: payload,
    }
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = action()

    assert success is False
    assert "已保留原内容" in message
    assert clipboard.formats == original
