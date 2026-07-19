"""不常见鉴权参数与 URL 用户信息的失败关闭契约。"""

import pytest

from src.clipboard.listener import ClipboardData
from src.manipulator.text_toolkit import preview_clean_url
from tests.test_active_action_safety import analyze


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/p?utm_source=test&oobCode=secret",
        "https://example.com/p?utm_source=test&resetCode=secret",
        "https://example.com/p?utm_source=test&verificationCode=secret",
        "https://example.com/p?utm_source=test&RelayState=secret",
        "https://example.com/p?utm_source=test&SAMLRequest=secret",
        "https://example.com/p?utm_source=test&SigAlg=secret",
        "https://example.com/p?utm_source=test&csrf=secret",
        "https://example.com/p?utm_source=test&otp=secret",
        "https://user:password@example.com/p?utm_source=test",
    ],
)
def test_adversarial_credential_urls_are_never_cleaned(url):
    """无法证明安全的鉴权参数或用户信息存在时必须原样保留。"""
    output = analyze(ClipboardData(text=url), target="word")

    assert output is not None
    assert "clean_url" not in output.available_actions
    assert preview_clean_url(url) == url
