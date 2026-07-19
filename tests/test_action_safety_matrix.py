"""代码与结构化内容的主动操作安全矩阵。"""

import pytest

from src.clipboard.listener import ClipboardData
from tests.test_active_action_safety import analyze


@pytest.mark.parametrize(
    ("data",),
    [
        (ClipboardData(
            text="def run():\n    return 1",
            html="<pre>def run():\n    return 1</pre>",
        ),),
        (ClipboardData(text="fn main() {\n    println!();\n}"),),
        (ClipboardData(text="SELECT id\nFROM users\nWHERE active = 1;"),),
        (ClipboardData(text="{\n  name: x,\n  items: [1, 2]\n}"),),
    ],
)
def test_code_or_structured_content_never_offers_actions(data):
    """代码或结构化内容不得暴露会破坏结构的主动操作。"""
    output = analyze(data, target="terminal")

    assert output is not None
    assert output.primary_action == ""
    assert output.available_actions == []
