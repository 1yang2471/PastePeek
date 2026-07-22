"""运行时本地化核心契约。"""

from src import i18n
from src.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    content_type_label,
    normalize_language,
    risk_label,
    target_group_label,
    target_label,
    translate,
)


def test_language_values_and_invalid_fallback():
    assert SUPPORTED_LANGUAGES == ("zh-CN", "en-US")
    assert DEFAULT_LANGUAGE == "zh-CN"
    assert normalize_language("en-US") == "en-US"
    assert normalize_language("en") == "en-US"
    assert normalize_language("invalid") == DEFAULT_LANGUAGE
    assert normalize_language(None) == DEFAULT_LANGUAGE


def test_static_labels_follow_language():
    assert content_type_label("rich_text", "zh-CN") == "富文本"
    assert content_type_label("rich_text", "en-US") == "Rich text"
    assert target_label("code_editor", "en-US") == "Code editor"
    assert target_label("code_editor", "en-US", compact=True) == "Code"
    assert target_label("chrome", "en-US", compact=True) == "Web"
    assert target_group_label("document", "en-US") == "Documents"
    assert risk_label("high", "en-US") == "High risk"
    assert "Language" in translate("language_menu", "en-US")


def test_formatting_does_not_leak_internal_key():
    message = translate("removed_tracking", "en-US", count=2, names="utm_source, ref")
    assert message == "Removed 2 tracking parameters: utm_source, ref"
    assert translate("missing_key", "en-US") == "PastePeek"


def test_english_resource_catalog_is_complete_and_contains_no_chinese_copy():
    """英文运行时资源必须与中文键同步，且不能遗漏中文固定文案。"""
    catalogs = (
        i18n._MESSAGES,
        i18n._CONTENT_TYPES,
        i18n._TARGET_LABELS,
        i18n._TARGET_COMPACT,
        i18n._TARGET_GROUPS,
        i18n._RISK_LABELS,
    )

    for catalog in catalogs:
        assert set(catalog["zh-CN"]) == set(catalog["en-US"])
        assert not any(
            "\u4e00" <= char <= "\u9fff"
            for value in catalog["en-US"].values()
            for char in value
        )
