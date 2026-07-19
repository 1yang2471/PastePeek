"""三项主动操作在全部目标应用中的公开流程矩阵。"""

import pytest

from src.clipboard.listener import ClipboardData
from src.ui.app import PastePeekApp

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


class FixedClipboard:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data


class FixedTarget:
    def __init__(self, target):
        self.target = target

    def get_active_target(self):
        return self.target


def analyze(data, target):
    return PastePeekApp(
        listener=FixedClipboard(data),
        target_detector=FixedTarget(target),
    ).check_clipboard()


@pytest.mark.parametrize("target", TARGETS)
def test_code_never_exposes_destructive_actions(target):
    output = analyze(
        ClipboardData(text="def run():\n    return 1"),
        target,
    )

    assert output is not None
    assert output.content_type == "code"
    assert output.primary_action == ""
    assert output.available_actions == []


@pytest.mark.parametrize("target", TARGETS)
def test_binary_content_never_exposes_text_actions(target):
    output = analyze(
        ClipboardData(has_binary=True, has_image=True),
        target,
    )

    assert output is not None
    assert output.primary_action == ""
    assert output.available_actions == []


@pytest.mark.parametrize("target", TARGETS)
def test_rich_multiline_action_matrix(target):
    output = analyze(
        ClipboardData(
            text="第一行\n第二行",
            html="<p>第一行</p><p>第二行</p>",
        ),
        target,
    )
    expected_primary = {
        "word": "strip_formats",
        "terminal": "merge_lines",
        "chat_app": "strip_formats",
        "markdown_editor": "strip_formats",
    }.get(target, "")

    assert output is not None
    assert output.primary_action == expected_primary
    assert output.available_actions == ["strip_formats", "merge_lines"]


@pytest.mark.parametrize("target", TARGETS)
def test_plain_multiline_action_matrix(target):
    output = analyze(ClipboardData(text="第一行\n第二行"), target)

    assert output is not None
    assert output.primary_action == (
        "merge_lines" if target == "terminal" else ""
    )
    assert output.available_actions == ["merge_lines"]


@pytest.mark.parametrize("target", TARGETS)
def test_tracked_url_action_matrix(target):
    output = analyze(
        ClipboardData(text="https://a.com/p?id=1&utm_source=test"),
        target,
    )
    primary_targets = {
        "word", "chrome", "chat_app", "markdown_editor",
    }

    assert output is not None
    assert output.primary_action == (
        "clean_url" if target in primary_targets else ""
    )
    assert output.available_actions == ["clean_url"]


@pytest.mark.parametrize("target", TARGETS)
def test_structured_multiline_action_matrix(target):
    output = analyze(
        ClipboardData(text="说明\n## 标题\n- 第一项\n- 第二项"),
        target,
    )

    assert output is not None
    assert output.content_type == "structured_text"
    assert output.primary_action == ""
    assert output.available_actions == []
