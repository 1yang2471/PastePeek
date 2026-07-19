"""PastePeek 典型用户场景的主流程集成测试。"""

import pytest

from src.clipboard.listener import ClipboardData
from src.ui.app import PastePeekApp


class ScenarioClipboardListener:
    """为单个场景提供固定剪贴板快照。"""

    def __init__(self, data: ClipboardData):
        self.data = data

    def read(self) -> ClipboardData:
        return self.data


class ScenarioTargetDetector:
    """为单个场景提供固定前台目标。"""

    def __init__(self, target: str):
        self.target = target

    def get_active_target(self) -> str:
        return self.target


SCENARIOS = [
    pytest.param(
        ClipboardData(
            text="核心功能\n格式检测\n预览功能",
            html=(
                "<h2>核心功能</h2><ul><li><b>格式检测</b></li>"
                "<li>预览功能</li></ul>"
            ),
        ),
        "word",
        "rich_text",
        "medium",
        "strip_formats",
        {"deep_headings": 1, "deep_list_count": 1},
        id="web-rich-text-to-word",
    ),
    pytest.param(
        ClipboardData(
            text="AI 回复标题\n要点一\n要点二",
            html=(
                "<h1>AI 回复标题</h1><p><strong>AI 生成</strong></p>"
                "<ul><li>要点一</li><li>要点二</li></ul>"
            ),
        ),
        "chat_app",
        "rich_text",
        "low",
        "strip_formats",
        {"deep_headings": 1, "deep_list_count": 1},
        id="ai-rich-text-to-chat",
    ),
    pytest.param(
        ClipboardData(text="明天下午三点开会"),
        "chat_app",
        "plain_text",
        "none",
        "",
        {},
        id="plain-text-to-chat",
    ),
    pytest.param(
        ClipboardData(
            text="# 项目规划\n## 背景\n- 目标用户\n- 核心需求\n> 注意事项"
        ),
        "markdown_editor",
        "structured_text",
        "none",
        "",
        {},
        id="markdown-to-markdown-editor",
    ),
    pytest.param(
        ClipboardData(
            text=(
                "def process(text):\n"
                "    result = text.strip()\n"
                "    return result"
            )
        ),
        "code_editor",
        "code",
        "none",
        "",
        {},
        id="python-to-code-editor",
    ),
    pytest.param(
        ClipboardData(
            text=(
                "const fetchData = async (url) => {\n"
                "    return await fetch(url);\n"
                "};"
            )
        ),
        "terminal",
        "code",
        "medium",
        "",
        {},
        id="javascript-to-terminal",
    ),
    pytest.param(
        ClipboardData(text="Hello World"),
        "chrome",
        "plain_text",
        "none",
        "",
        {},
        id="short-text-to-browser",
    ),
    pytest.param(
        ClipboardData(
            text="项目\t进度\nA\t完成",
            html=(
                "<table><tr><th>项目</th><th>进度</th></tr>"
                "<tr><td>A</td><td>完成</td></tr></table>"
            ),
        ),
        "spreadsheet",
        "rich_text",
        "high",
        "",
        {"deep_table_count": 1},
        id="html-table-to-spreadsheet",
    ),
    pytest.param(
        ClipboardData(
            text=(
                "https://example.com/product?"
                "utm_source=newsletter&utm_medium=email"
            )
        ),
        "chrome",
        "plain_text",
        "none",
        "clean_url",
        {},
        id="tracked-url-to-browser",
    ),
]


@pytest.mark.parametrize(
    (
        "data",
        "target",
        "expected_type",
        "expected_risk",
        "expected_action",
        "expected_metadata",
    ),
    SCENARIOS,
)
def test_user_scenario_runs_through_public_clipboard_pipeline(
    data,
    target,
    expected_type,
    expected_risk,
    expected_action,
    expected_metadata,
):
    """典型用户快照应经过同一公开主流程生成完整结果。"""
    app = PastePeekApp(
        listener=ScenarioClipboardListener(data),
        target_detector=ScenarioTargetDetector(target),
    )

    output = app.check_clipboard()

    assert output is not None
    assert output.content_type == expected_type
    assert output.target == target
    assert output.risk_level == expected_risk
    assert output.primary_action == expected_action
    assert output.raw_text == data.text
    assert output.raw_html == data.html
    for field, expected in expected_metadata.items():
        assert getattr(output, field) == expected
