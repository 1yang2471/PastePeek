"""URL 净化安全策略，供分析器和剪贴板操作共同使用。"""

from urllib.parse import unquote_plus, urlsplit

from src.url_credentials import is_sensitive_query_key

TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_name", "fbclid", "gclid", "dclid", "msclkid",
    "ref_src", "ref_url", "mc_cid", "mc_eid", "mc_tc",
    "oly_anon_id", "oly_enc_id", "_ga", "_gl", "trk", "trkcampaign",
    "vero_id", "vero_conv", "wickedid", "yclid", "igshid",
})

PROTECTED_URL_PARAMS = frozenset({
    "access_token", "api_key", "apikey", "auth", "authorization",
    "client_secret", "expires", "hmac", "jwt", "nonce", "policy",
    "q-signature", "session_token", "sig", "signature", "token",
    "x-amz-credential", "x-amz-signature", "x-amz-security-token",
    "x-goog-signature",
})


def clean_url_text(url_text: str) -> tuple[str, list[str], str]:
    """保守删除追踪参数，并逐字保留其余查询片段。"""
    if not url_text or any(
        char.isspace() or ord(char) < 32 or ord(char) == 127
        for char in url_text
    ):
        return url_text, [], "not_url"

    try:
        parsed = urlsplit(url_text)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return url_text, [], "not_url"
        if parsed.username is not None or parsed.password is not None:
            return url_text, [], "protected"
        # 访问 port 会主动触发非法数字或越界端口的 ValueError；端口 0 也不作为可用 HTTP(S) 端口。
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return url_text, [], "not_url"
    except ValueError:
        return url_text, [], "not_url"

    if not parsed.query:
        return url_text, [], "no_query"
    if ";" in parsed.query:
        return url_text, [], "ambiguous"

    parts = parsed.query.split("&")
    decoded_keys = [
        unquote_plus(part.partition("=")[0]).lower()
        for part in parts
    ]
    if any(
        is_sensitive_query_key(key, PROTECTED_URL_PARAMS)
        for key in decoded_keys
    ):
        return url_text, [], "protected"

    kept: list[str] = []
    removed: list[str] = []
    for part, key in zip(parts, decoded_keys, strict=True):
        if key in TRACKING_PARAMS:
            removed.append(key)
        else:
            kept.append(part)

    if not removed:
        return url_text, [], "no_tracking"

    query_start = url_text.find("?")
    fragment_start = url_text.find("#", query_start + 1)
    prefix = url_text[:query_start]
    fragment = url_text[fragment_start:] if fragment_start >= 0 else ""
    cleaned_query = "&".join(kept)
    cleaned = (
        f"{prefix}?{cleaned_query}{fragment}"
        if cleaned_query
        else f"{prefix}{fragment}"
    )
    return cleaned, removed, "cleaned"
