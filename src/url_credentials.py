"""URL 查询参数中的签名、鉴权与完整性凭据判定。"""

import re
from collections.abc import Set

_SENSITIVE_COMPACT_MARKERS = (
    "signature",
    "signed",
    "token",
    "auth",
    "credential",
    "secret",
    "hmac",
    "jwt",
    "nonce",
    "session",
    "bearer",
    "ticket",
    "accesskey",
    "accessid",
    "apikey",
    "codechallenge",
    "codeverifier",
    "proof",
    "digest",
    "verification",
    "verify",
    "reset",
    "invite",
    "otp",
    "csrf",
    "saml",
    "assertion",
    "relaystate",
    "sigalg",
    "wresult",
    "code",
    "hash",
    "expires",
    "expiry",
    "expiration",
)

_SENSITIVE_SEGMENTS = frozenset({
    "sig",
    "sign",
    "key",
    "state",
    "policy",
    "code",
    "mac",
    "hash",
    "exp",
})


def is_sensitive_query_key(
    key: str,
    exact_keys: Set[str],
) -> bool:
    """保守识别可能参与签名、鉴权或完整性校验的参数名。"""
    lowered = key.casefold()
    if lowered in exact_keys:
        return True

    compact = re.sub(r"[^a-z0-9]", "", lowered)
    if any(marker in compact for marker in _SENSITIVE_COMPACT_MARKERS):
        return True

    segments = set(filter(None, re.split(r"[^a-z0-9]+", lowered)))
    return bool(segments & _SENSITIVE_SEGMENTS)
