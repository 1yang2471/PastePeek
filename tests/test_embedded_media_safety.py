"""富文本内嵌媒体的主动操作安全契约。"""

from src.clipboard.listener import ClipboardData
from tests.test_active_action_safety import analyze


def test_html_image_with_text_never_offers_actions():
    """HTML 内嵌图片与正文共存时不得提供文本转换。"""
    data = ClipboardData(
        text="第一行\n第二行",
        html="<p>第一行</p><img src='data:image/png;base64,AA=='>",
    )

    output = analyze(data, target="terminal")

    assert output is not None
    assert output.primary_action == ""
    assert output.available_actions == []
