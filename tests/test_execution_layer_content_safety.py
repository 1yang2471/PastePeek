"""主动操作执行层对代码与结构化文本的独立保护。"""

import pytest

from src.manipulator import text_toolkit
from tests.test_text_toolkit_contract import MemoryClipboard


@pytest.mark.parametrize(
    ("action", "formats"),
    [
        (
            text_toolkit.merge_lines,
            {MemoryClipboard.CF_UNICODETEXT: "API_URL=https://a.example\nDEBUG=false"},
        ),
        (
            text_toolkit.strip_formats,
            {
                MemoryClipboard.CF_UNICODETEXT: "name = app\nversion = 1.0",
                text_toolkit.CF_HTML: b"<p>name = app</p><p>version = 1.0</p>",
            },
        ),
    ],
)
def test_execution_layer_rejects_protected_text(monkeypatch, action, formats):
    """推荐层被绕过时，执行层仍不得改写代码或结构化文本。"""
    clipboard = MemoryClipboard(formats)
    original = dict(clipboard.formats)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, _message = action()

    assert success is False
    assert clipboard.formats == original
