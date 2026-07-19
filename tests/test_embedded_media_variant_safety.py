"""富文本内嵌媒体变体的双层失败关闭契约。"""

import pytest

from src.clipboard import listener as listener_module
from src.manipulator import text_toolkit
from tests.test_active_action_safety import analyze
from tests.test_text_toolkit_contract import MemoryClipboard


@pytest.mark.parametrize(
    ("rich_format", "payload"),
    [
        (
            text_toolkit.CF_HTML,
            b"<p style='background-image:url(data:image/png;base64,AA==)'>text</p>",
        ),
        (
            text_toolkit.CF_HTML,
            b"<picture><source srcset='data:image/webp;base64,AA=='></picture>",
        ),
        (text_toolkit.CF_RTF, b"{\\rtf1 text {\\*\\shppict data}}"),
        (text_toolkit.CF_RTF, b"{\\rtf1 text {\\*\\objdata data}}"),
    ],
)
def test_embedded_media_variants_are_rejected_in_both_layers(
    monkeypatch,
    rich_format,
    payload,
):
    """非典型媒体载荷也不得被文本转换静默删除。"""
    text = "第一行\n第二行"
    original = {
        MemoryClipboard.CF_UNICODETEXT: text,
        rich_format: payload,
    }
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(listener_module, "wc", clipboard)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    snapshot = listener_module.ClipboardListener().read()
    output = analyze(snapshot, target="terminal")
    success, _message = text_toolkit.merge_lines()

    assert output is not None
    assert output.available_actions == []
    assert success is False
    assert clipboard.formats == original
