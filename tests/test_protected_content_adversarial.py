"""易被误判为普通文本的代码与结构化内容安全矩阵。"""

import pytest

from src.clipboard.listener import ClipboardData
from tests.test_active_action_safety import analyze

TARGETS = (
    "word",
    "chrome",
    "code_editor",
    "terminal",
    "chat_app",
    "markdown_editor",
    "spreadsheet",
    "presentation",
)

PROTECTED_CONTENT = (
    "API_URL=https://example.com\nDEBUG=false",
    'name = "app"\nversion = "1.0"',
    "server.port=8080\nserver.host=localhost",
    'name,description\nA,"x,y"\nB,"z,w"',
    "| name | age |\n| --- | --- |\n| Alice | 30 |",
    "1. first step\n2. second step",
    "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new",
    "build:\n\tpython -m build",
    "#define FIRST 1\n#define SECOND 2",
    "items.each do |item|\n  puts item\nend",
    "local value = 1\nprint(value)",
    "@echo off\nset NAME=PastePeek\necho %NAME%",
)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("text", PROTECTED_CONTENT)
def test_adversarial_protected_content_has_no_actions(text, target):
    """明确的代码、配置、表格和列表在全部目标中都不得被改写。"""
    output = analyze(ClipboardData(text=text), target=target)

    assert output is not None
    assert output.primary_action == ""
    assert output.available_actions == []
