"""URL 鉴权与签名参数命名变体的安全矩阵。"""

import pytest

from src.clipboard.listener import ClipboardData
from src.manipulator.text_toolkit import preview_clean_url
from tests.test_active_action_safety import analyze


@pytest.mark.parametrize(
    "credential_key",
    [
        "x-goog-credential",
        "x-goog-expires",
        "q-sign-time",
        "AWSAccessKeyId",
        "GoogleAccessId",
        "Key-Pair-Id",
        "auth_token",
        "bearer",
        "access_key",
        "secret_key",
        "sessionid",
        "_wpnonce",
        "code_challenge",
        "state",
        "ticket",
        "digest",
        "proof",
    ],
)
def test_credential_key_variant_never_allows_cleaning(credential_key):
    """疑似鉴权或完整性参数存在时，链接必须整体保持不变。"""
    url = f"https://example.com/p?utm_source=test&{credential_key}=secret"

    output = analyze(ClipboardData(text=url), target="word")

    assert output is not None
    assert "clean_url" not in output.available_actions
    assert preview_clean_url(url) == url
