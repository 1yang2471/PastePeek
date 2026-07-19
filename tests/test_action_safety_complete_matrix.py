"""主动操作对常见代码与结构化内容的完整目标矩阵。"""

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
    "public static void main(String[] args) {\n    return;\n}",
    "public class User {\n    public string Name { get; set; }\n}",
    "for file in *.txt; do\n    echo $file\ndone",
    "$items = Get-ChildItem\n$items | Where-Object { $_.Length -gt 0 }",
    "FROM python:3.12\nCOPY . /app\nRUN python app.py",
    "<root>\n  <item id='1'>x</item>\n</root>",
    "name: app\nitems:\n  - one",
    "name,age\nAlice,30\nBob,40",
    "name\tage\nAlice\t30\nBob\t40",
    "[server]\nhost=localhost\nport=8080",
    ".card {\n  color: red;\n}",
    "resource 'x' 'y' {\n  name = 'value'\n}",
    "fun main() {\n    println()\n}",
    "function run() {\n    return true;\n}",
    "curl https://a.example \\\n  --header x \\\n  --data y",
    "# 标题\n\n- 第一项\n- 第二项",
)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("text", PROTECTED_CONTENT)
def test_protected_multiline_content_has_no_actions(text, target):
    """代码、配置和结构化数据在全部目标中都不得暴露主动操作。"""
    output = analyze(ClipboardData(text=text), target=target)

    assert output is not None
    assert output.primary_action == ""
    assert output.available_actions == []
