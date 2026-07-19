"""主动操作失败关闭的公开流程契约。"""

from src.clipboard.listener import ClipboardData
from src.ui.app import PastePeekApp


class FixedClipboard:
    """返回固定剪贴板快照。"""

    def __init__(self, data: ClipboardData):
        self.data = data

    def read(self) -> ClipboardData:
        return self.data


class FixedTarget:
    """返回固定目标应用。"""

    def __init__(self, target: str):
        self.target = target

    def get_active_target(self) -> str:
        return self.target


def analyze(data: ClipboardData, target: str = "word"):
    """通过公开检查流程返回用户可见结果。"""
    return PastePeekApp(
        listener=FixedClipboard(data),
        target_detector=FixedTarget(target),
    ).check_clipboard()


def test_html_without_plain_text_never_offers_actions():
    """没有可验证纯文字时不得提供会失败的主动操作。"""
    output = analyze(ClipboardData(html="<p>正文</p>"))

    assert output is not None
    assert output.primary_action == ""
    assert output.available_actions == []


def test_whitespace_rich_text_never_offers_actions():
    """只有空白正文的富文本不得提供主动操作。"""
    output = analyze(
        ClipboardData(text="\n  \n", html="<p><br></p>"),
        target="terminal",
    )

    assert output is not None
    assert output.primary_action == ""
    assert output.available_actions == []
