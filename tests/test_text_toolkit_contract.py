"""主动剪贴板操作的用户可观察行为契约。"""

import random

import pytest

from src.clipboard.listener import ClipboardData
from src.manipulator import text_toolkit
from src.manipulator.text_toolkit import preview_clean_url, preview_merge_lines
from src.ui.app import PastePeekApp


class MemoryClipboard:
    """只模拟 Windows 剪贴板边界，并保留可观察的最终格式。"""

    CF_UNICODETEXT = 13
    CF_HDROP = 15
    CF_DIB = 8
    CF_BITMAP = 2
    CF_WAVE = 12

    def __init__(self, formats):
        self.formats = dict(formats)
        self.sequence_number = 0

    def OpenClipboard(self):
        pass

    def CloseClipboard(self):
        pass

    def IsClipboardFormatAvailable(self, format_id):
        return format_id in self.formats

    def GetClipboardData(self, format_id):
        return self.formats[format_id]

    def EnumClipboardFormats(self, previous):
        for format_id in sorted(self.formats):
            if format_id > previous:
                return format_id
        return 0

    def EmptyClipboard(self):
        self.formats.clear()

    def SetClipboardText(self, text, format_id):
        self.formats[format_id] = text

    def GetClipboardSequenceNumber(self):
        return self.sequence_number


class FailingWriteClipboard(MemoryClipboard):
    """第一次文本写入失败，后续写入用于验证内存回滚。"""

    def __init__(self, formats):
        super().__init__(formats)
        self.remaining_failures = 1

    def SetClipboardText(self, text, format_id):
        if self.remaining_failures:
            self.remaining_failures -= 1
            raise RuntimeError("模拟写入失败")
        super().SetClipboardText(text, format_id)

    def SetClipboardData(self, format_id, data):
        self.formats[format_id] = data


class MutableListener:
    """模拟用户在看到操作后又复制了其他内容。"""

    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data


class TerminalDetector:
    def get_active_target(self):
        return "terminal"


def test_clean_url_preserves_business_query_verbatim():
    """删除追踪参数时不得重排、合并或丢弃业务参数。"""
    url = (
        "https://a.com/p?tag=first&required=&tag=second&"
        "q=%E4%B8%AD%E6%96%87%20text&utm_source=newsletter"
    )

    result = preview_clean_url(url)

    assert result == (
        "https://a.com/p?tag=first&required=&tag=second&"
        "q=%E4%B8%AD%E6%96%87%20text"
    )


def test_merge_lines_removes_single_trailing_newline():
    """只要存在换行，合并结果中就不得残留换行符。"""
    assert preview_merge_lines("正文\r\n") == "正文"


def test_strip_formats_removes_rtf_without_html(monkeypatch):
    """只有 RTF 和配套文字时也必须真正转换为纯文本。"""
    clipboard = MemoryClipboard({
        MemoryClipboard.CF_UNICODETEXT: "正文",
        text_toolkit.CF_RTF: b"{\\rtf1 body}",
    })
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = text_toolkit.strip_formats()

    assert success is True
    assert "RTF" in message
    assert clipboard.formats == {MemoryClipboard.CF_UNICODETEXT: "正文"}


def test_rtf_only_snapshot_offers_strip_formats_through_public_pipeline():
    """只有 RTF 的真实用户快照也必须在 HUD 流程中提供清洗操作。"""
    data = ClipboardData(text="正文")
    data.has_rtf = True
    app = PastePeekApp(
        listener=MutableListener(data),
        target_detector=TerminalDetector(),
    )
    app.set_manual_target("word")

    output = app.check_clipboard()

    assert output is not None
    assert output.content_type == "rich_text"
    assert output.primary_action == "strip_formats"
    assert "strip_formats" in output.available_actions


def test_stale_merge_action_cannot_modify_new_code(monkeypatch):
    """旧的合并按钮不得处理用户随后复制的新代码。"""
    listener = MutableListener(ClipboardData(text="第一行\n第二行"))
    clipboard = MemoryClipboard({
        MemoryClipboard.CF_UNICODETEXT: "第一行\n第二行",
    })
    monkeypatch.setattr(text_toolkit, "wc", clipboard)
    app = PastePeekApp(listener=listener, target_detector=TerminalDetector())
    output = app.check_clipboard()
    assert output is not None
    assert output.primary_action == "merge_lines"

    code = "def run():\n    return 1"
    listener.data = ClipboardData(text=code)
    clipboard.formats = {MemoryClipboard.CF_UNICODETEXT: code}

    success, message = app.on_action_triggered("merge_lines")

    assert success is False
    assert "已变化" in message
    assert clipboard.formats == {MemoryClipboard.CF_UNICODETEXT: code}


def test_action_rechecks_sequence_while_clipboard_is_locked(monkeypatch):
    """执行前重读后再次变化时，即使文字相同也不得继续写入。"""
    data = ClipboardData(text="第一行\n第二行")
    data.sequence_number = 10
    listener = MutableListener(data)
    clipboard = MemoryClipboard({
        MemoryClipboard.CF_UNICODETEXT: data.text,
    })
    clipboard.sequence_number = 10
    monkeypatch.setattr(text_toolkit, "wc", clipboard)
    app = PastePeekApp(listener=listener, target_detector=TerminalDetector())
    output = app.check_clipboard()
    assert output is not None

    clipboard.sequence_number = 11
    success, message = app.on_action_triggered("merge_lines")

    assert success is False
    assert "已变化" in message
    assert clipboard.formats == {MemoryClipboard.CF_UNICODETEXT: data.text}


def test_clean_url_rechecks_sequence_while_clipboard_is_locked(monkeypatch):
    """净化链接也必须拒绝重读后发生变化的剪贴板。"""
    url = "https://a.com/p?id=1&utm_source=test"
    data = ClipboardData(text=url)
    data.sequence_number = 20
    listener = MutableListener(data)
    clipboard = MemoryClipboard({MemoryClipboard.CF_UNICODETEXT: url})
    clipboard.sequence_number = 20
    monkeypatch.setattr(text_toolkit, "wc", clipboard)
    app = PastePeekApp(listener=listener, target_detector=TerminalDetector())
    app.set_manual_target("word")
    output = app.check_clipboard()
    assert output is not None
    assert output.primary_action == "clean_url"

    clipboard.sequence_number = 21
    success, message = app.on_action_triggered("clean_url")

    assert success is False
    assert "已变化" in message
    assert clipboard.formats == {MemoryClipboard.CF_UNICODETEXT: url}


def test_strip_formats_rechecks_sequence_while_clipboard_is_locked(monkeypatch):
    """清洗格式不得删除重读后才出现的新格式。"""
    text = "正文"
    html = "<b>正文</b>"
    data = ClipboardData(text=text, html=html)
    data.sequence_number = 30
    listener = MutableListener(data)
    original_formats = {
        MemoryClipboard.CF_UNICODETEXT: text,
        text_toolkit.CF_HTML: html.encode(),
    }
    clipboard = MemoryClipboard(original_formats)
    clipboard.sequence_number = 30
    monkeypatch.setattr(text_toolkit, "wc", clipboard)
    app = PastePeekApp(listener=listener, target_detector=TerminalDetector())
    app.set_manual_target("word")
    output = app.check_clipboard()
    assert output is not None
    assert output.primary_action == "strip_formats"

    clipboard.sequence_number = 31
    success, message = app.on_action_triggered("strip_formats")

    assert success is False
    assert "已变化" in message
    assert clipboard.formats == original_formats


def test_merge_lines_restores_original_after_write_failure(monkeypatch):
    """清空后写入失败时必须从内存恢复原始剪贴板。"""
    original = {MemoryClipboard.CF_UNICODETEXT: "第一行\n第二行"}
    clipboard = FailingWriteClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = text_toolkit.merge_lines()

    assert success is False
    assert "失败" in message
    assert clipboard.formats == original


def test_clean_url_restores_original_after_write_failure(monkeypatch):
    """净化链接写入失败时必须恢复完整原 URL。"""
    original = {
        MemoryClipboard.CF_UNICODETEXT:
            "https://a.com/p?id=1&utm_source=test",
    }
    clipboard = FailingWriteClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = text_toolkit.clean_url()

    assert success is False
    assert "失败" in message
    assert clipboard.formats == original


def test_strip_formats_restores_all_text_formats_after_write_failure(monkeypatch):
    """清洗失败时必须恢复纯文字、HTML 和 RTF。"""
    original = {
        MemoryClipboard.CF_UNICODETEXT: "正文",
        text_toolkit.CF_HTML: b"<b>body</b>",
        text_toolkit.CF_RTF: b"{\\rtf1 body}",
    }
    clipboard = FailingWriteClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = text_toolkit.strip_formats()

    assert success is False
    assert "失败" in message
    assert clipboard.formats == original


@pytest.mark.parametrize(
    ("action", "text"),
    [
        (text_toolkit.strip_formats, "C:\\report.docx"),
        (
            text_toolkit.clean_url,
            "https://a.com/p?id=1&utm_source=test",
        ),
        (text_toolkit.merge_lines, "第一行\n第二行"),
    ],
)
@pytest.mark.parametrize(
    ("binary_format", "binary_data", "label"),
    [
        (MemoryClipboard.CF_HDROP, ("C:\\report.docx",), "文件"),
        (MemoryClipboard.CF_DIB, b"bitmap", "图片"),
        (MemoryClipboard.CF_WAVE, b"wave", "音频"),
    ],
)
def test_actions_never_modify_binary_clipboard(
    monkeypatch,
    action,
    text,
    binary_format,
    binary_data,
    label,
):
    """混合非文本剪贴板必须在操作层被统一拒绝。"""
    original = {
        MemoryClipboard.CF_UNICODETEXT: text,
        binary_format: binary_data,
    }
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = action()

    assert success is False
    assert label in message
    assert clipboard.formats == original


def test_merge_lines_never_removes_dibv5_image(monkeypatch):
    """DIBV5 图片与文字共存时必须拒绝合并并保留全部格式。"""
    dibv5_format = 17
    original = {
        MemoryClipboard.CF_UNICODETEXT: "第一行\n第二行",
        dibv5_format: b"dibv5-image",
    }
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = text_toolkit.merge_lines()

    assert success is False
    assert "图片" in message
    assert clipboard.formats == original


@pytest.mark.parametrize("binary_format", [3, 6, 11, 14])
@pytest.mark.parametrize(
    "action",
    [text_toolkit.clean_url, text_toolkit.strip_formats, text_toolkit.merge_lines],
)
def test_actions_never_remove_standard_binary_formats(
    monkeypatch,
    binary_format,
    action,
):
    """标准图片或音频格式存在时，所有主动操作必须失败关闭。"""
    source = "https://a.com/p?utm_source=test\n第二行"
    original = {
        MemoryClipboard.CF_UNICODETEXT: source,
        text_toolkit.CF_HTML: b"<p>rich</p>",
        binary_format: b"binary",
    }
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = action()

    assert success is False
    assert "已保留原内容" in message
    assert clipboard.formats == original


@pytest.mark.parametrize(
    "format_name",
    ["PNG", "FileGroupDescriptorW", "FileContents", "audio/mpeg"],
)
def test_merge_lines_never_removes_registered_binary_formats(
    monkeypatch,
    format_name,
):
    """常见注册图片、虚拟文件和音频格式必须失败关闭。"""
    binary_format = text_toolkit.wc.RegisterClipboardFormat(format_name)
    original = {
        MemoryClipboard.CF_UNICODETEXT: "第一行\n第二行",
        binary_format: b"binary",
    }
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = text_toolkit.merge_lines()

    assert success is False
    assert "已保留原内容" in message
    assert clipboard.formats == original


@pytest.mark.parametrize(
    ("action", "source", "extra_formats"),
    [
        (
            text_toolkit.clean_url,
            "https://a.com/p?utm_source=test&id=1",
            {},
        ),
        (
            text_toolkit.strip_formats,
            "正文",
            {text_toolkit.CF_HTML: b"<p>body</p>"},
        ),
        (
            text_toolkit.merge_lines,
            "第一行\n第二行",
            {},
        ),
    ],
)
def test_actions_reject_registered_formats_without_safe_rollback(
    monkeypatch,
    action,
    source,
    extra_formats,
):
    """无法逐格式回滚的注册格式存在时必须拒绝主动操作。"""
    registered_format = text_toolkit.wc.RegisterClipboardFormat(
        "UniformResourceLocatorW"
    )
    original = {
        MemoryClipboard.CF_UNICODETEXT: source,
        registered_format: b"registered payload",
        **extra_formats,
    }
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = action()

    assert success is False
    assert "已保留原内容" in message
    assert clipboard.formats == original


@pytest.mark.parametrize("parameter", ["ref", "from", "source"])
def test_ambiguous_url_parameters_do_not_trigger_clean_action(parameter):
    """可能具有业务意义的参数不得被分析器当成可自动删除项。"""
    url = f"https://a.com/p?id=1&{parameter}=campaign"
    app = PastePeekApp(
        listener=MutableListener(ClipboardData(text=url)),
        target_detector=TerminalDetector(),
    )
    app.set_manual_target("word")

    output = app.check_clipboard()

    assert output is not None
    assert output.has_tracking_params is False
    assert "clean_url" not in output.available_actions
    assert preview_clean_url(url) == url


@pytest.mark.parametrize(
    "protected",
    ["signature", "token", "x-amz-signature", "expires"],
)
def test_signed_urls_are_never_offered_for_cleaning(protected):
    """签名或令牌链接必须整体保持不变。"""
    url = f"https://a.com/p?utm_source=test&{protected}=secret"
    app = PastePeekApp(
        listener=MutableListener(ClipboardData(text=url)),
        target_detector=TerminalDetector(),
    )
    app.set_manual_target("word")

    output = app.check_clipboard()

    assert output is not None
    assert output.has_tracking_params is False
    assert "clean_url" not in output.available_actions
    assert preview_clean_url(url) == url


def test_google_cloud_signed_url_is_never_cleaned():
    """Google Cloud 签名链接必须整体保持不变。"""
    url = (
        "https://storage.googleapis.com/bucket/object?"
        "X-Goog-Algorithm=GOOG4-RSA-SHA256&"
        "X-Goog-Credential=credential&"
        "X-Goog-Signature=secret&utm_source=test"
    )
    app = PastePeekApp(
        listener=MutableListener(ClipboardData(text=url)),
        target_detector=TerminalDetector(),
    )
    app.set_manual_target("word")

    output = app.check_clipboard()

    assert output is not None
    assert "clean_url" not in output.available_actions
    assert preview_clean_url(url) == url


def test_tencent_cos_signed_url_is_never_cleaned():
    """腾讯 COS 签名链接必须整体保持不变。"""
    url = (
        "https://bucket.cos.ap-shanghai.myqcloud.com/object?"
        "q-signature=secret&q-ak=credential&utm_source=test"
    )
    app = PastePeekApp(
        listener=MutableListener(ClipboardData(text=url)),
        target_detector=TerminalDetector(),
    )
    app.set_manual_target("word")

    output = app.check_clipboard()

    assert output is not None
    assert "clean_url" not in output.available_actions
    assert preview_clean_url(url) == url


def test_semicolon_query_is_never_cleaned():
    """查询分隔规则不明确时不得误删分号后的业务字段。"""
    url = "https://example.com/p?utm_source=test;id=42"
    app = PastePeekApp(
        listener=MutableListener(ClipboardData(text=url)),
        target_detector=TerminalDetector(),
    )
    app.set_manual_target("word")

    output = app.check_clipboard()

    assert output is not None
    assert "clean_url" not in output.available_actions
    assert preview_clean_url(url) == url


@pytest.mark.parametrize(
    "credential_key",
    ["api_key", "client_secret", "authorization", "session_token", "nonce"],
)
def test_credential_urls_are_never_cleaned(credential_key):
    """常见鉴权参数存在时不得改写链接。"""
    url = f"https://example.com/p?utm_source=test&{credential_key}=secret"
    app = PastePeekApp(
        listener=MutableListener(ClipboardData(text=url)),
        target_detector=TerminalDetector(),
    )
    app.set_manual_target("word")

    output = app.check_clipboard()

    assert output is not None
    assert "clean_url" not in output.available_actions
    assert preview_clean_url(url) == url


@pytest.mark.parametrize(
    "parameter",
    [
        "utm_source", "utm_medium", "utm_campaign", "utm_term",
        "utm_content", "utm_id", "utm_name", "fbclid", "gclid",
        "dclid", "msclkid", "ref_src", "ref_url", "mc_cid",
        "mc_eid", "mc_tc", "oly_anon_id", "oly_enc_id", "_ga", "_gl",
        "trk", "trkCampaign", "vero_id", "vero_conv", "wickedid",
        "yclid", "igshid",
    ],
)
def test_every_high_confidence_tracking_parameter_is_cleaned(parameter):
    """全部受支持追踪参数都必须在分析和执行层保持一致。"""
    url = f"https://a.com/p?id=42&{parameter}=tracking#section"
    app = PastePeekApp(
        listener=MutableListener(ClipboardData(text=url)),
        target_detector=TerminalDetector(),
    )
    app.set_manual_target("word")

    output = app.check_clipboard()

    assert output is not None
    assert output.has_tracking_params is True
    assert output.primary_action == "clean_url"
    assert preview_clean_url(url) == "https://a.com/p?id=42#section"


@pytest.mark.parametrize(
    "url",
    [
        "https://?utm_source=test",
        "ftp://a.com/p?utm_source=test",
        "https://a.com/p?utm_source=test\nhttps://b.com/",
        " https://a.com/p?utm_source=test ",
        "\x00https://a.com/p?utm_source=test",
        "https://a.com/p?myutm_source=test",
        "https://a.com/p?utm_source_id=test",
        "https://a.com/p?utm_source%20=test",
        "https://example.com:bad/?utm_source=test&id=1",
        "https://example.com:0/?utm_source=test&id=1",
        "https://example.com:65536/?utm_source=test&id=1",
        "https://example.com:99999/?utm_source=test&id=1",
    ],
)
def test_invalid_or_lookalike_urls_are_never_cleaned(url):
    """无效地址和相似业务参数不得触发净化。"""
    app = PastePeekApp(
        listener=MutableListener(ClipboardData(text=url)),
        target_detector=TerminalDetector(),
    )
    app.set_manual_target("word")

    output = app.check_clipboard()

    assert output is not None
    assert output.has_tracking_params is False
    assert "clean_url" not in output.available_actions
    assert preview_clean_url(url) == url


def test_merge_lines_restores_rich_formats_after_write_failure(monkeypatch):
    """富文本合并失败时必须恢复纯文字、HTML 和 RTF。"""
    original = {
        MemoryClipboard.CF_UNICODETEXT: "第一行\n第二行",
        text_toolkit.CF_HTML: b"<p>first</p><p>second</p>",
        text_toolkit.CF_RTF: b"{\\rtf1 first\\par second}",
    }
    clipboard = FailingWriteClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = text_toolkit.merge_lines()

    assert success is False
    assert "失败" in message
    assert clipboard.formats == original


@pytest.mark.parametrize(
    ("action", "source", "expected"),
    [
        (
            text_toolkit.clean_url,
            "https://a.com/p?id=1&utm_source=test",
            "https://a.com/p?id=1",
        ),
        (text_toolkit.merge_lines, "第一行\n第二行", "第一行 第二行"),
    ],
)
def test_rich_text_actions_disclose_plain_text_result(
    monkeypatch,
    action,
    source,
    expected,
):
    """会移除富文本格式的操作必须在成功提示中明确说明。"""
    clipboard = MemoryClipboard({
        MemoryClipboard.CF_UNICODETEXT: source,
        text_toolkit.CF_HTML: b"<p>rich</p>",
        text_toolkit.CF_RTF: b"{\\rtf1 rich}",
    })
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = action()

    assert success is True
    assert "纯文本" in message
    assert clipboard.formats == {MemoryClipboard.CF_UNICODETEXT: expected}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("a\nb", "a b"),
        ("a\r\nb", "a b"),
        ("a\rb", "a b"),
        ("a\vb", "a b"),
        ("a\fb", "a b"),
        ("a\x1cb", "a b"),
        ("a\x1db", "a b"),
        ("a\x1eb", "a b"),
        ("a\x85b", "a b"),
        ("a\u2028b", "a b"),
        ("a\u2029b", "a b"),
        ("a\n\n\n b", "a b"),
        ("  a  \r\n\tb\t", "a b"),
        ("a  x\nb\tc", "a  x b\tc"),
        ("正文😀\n下一行", "正文😀 下一行"),
    ],
)
def test_merge_lines_handles_all_supported_line_boundaries(
    monkeypatch,
    source,
    expected,
):
    """预览和真实写入必须对所有支持换行给出同一结果。"""
    clipboard = MemoryClipboard({MemoryClipboard.CF_UNICODETEXT: source})
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, _message = text_toolkit.merge_lines()

    assert success is True
    assert preview_merge_lines(source) == expected
    assert clipboard.formats == {MemoryClipboard.CF_UNICODETEXT: expected}


def test_merge_lines_keeps_single_line_verbatim(monkeypatch):
    """没有换行时不得顺手裁剪或规范化任何空白。"""
    source = "  single\ttext  "
    clipboard = MemoryClipboard({MemoryClipboard.CF_UNICODETEXT: source})
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = text_toolkit.merge_lines()

    assert success is False
    assert "已经是单行" in message
    assert preview_merge_lines(source) == source
    assert clipboard.formats == {MemoryClipboard.CF_UNICODETEXT: source}


def test_clean_url_real_write_preserves_query_and_is_idempotent(monkeypatch):
    """真实写入必须与预览一致，重复执行不得再次改动。"""
    source = (
        "https://a.com/p?tag=first&required=&tag=second&"
        "q=%E4%B8%AD%E6%96%87%20text&utm_source=test#section"
    )
    expected = (
        "https://a.com/p?tag=first&required=&tag=second&"
        "q=%E4%B8%AD%E6%96%87%20text#section"
    )
    clipboard = MemoryClipboard({MemoryClipboard.CF_UNICODETEXT: source})
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    first_success, _message = text_toolkit.clean_url()
    second_success, second_message = text_toolkit.clean_url()

    assert first_success is True
    assert second_success is False
    assert "无追踪参数" in second_message
    assert preview_clean_url(source) == expected
    assert clipboard.formats == {MemoryClipboard.CF_UNICODETEXT: expected}


@pytest.mark.parametrize(
    "source",
    [
        "https://a.com/p?id=1",
        "https://a.com/p",
        "https://?utm_source=test",
        " https://a.com/p?utm_source=test ",
        "https://a.com/p?utm_source=test&signature=secret",
        "普通文字",
    ],
)
def test_clean_url_noop_inputs_preserve_all_formats(monkeypatch, source):
    """不适用输入必须逐格式保持原剪贴板。"""
    original = {
        MemoryClipboard.CF_UNICODETEXT: source,
        text_toolkit.CF_HTML: b"<p>original</p>",
        text_toolkit.CF_RTF: b"{\\rtf1 original}",
    }
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, _message = text_toolkit.clean_url()

    assert success is False
    assert clipboard.formats == original


def test_strip_formats_preserves_unicode_text_exactly(monkeypatch):
    """清洗只能删除格式，不能改动文字、换行或 Unicode 字符。"""
    source = "标题\r\n正文\t😀 e\u0301 العربية"
    clipboard = MemoryClipboard({
        MemoryClipboard.CF_UNICODETEXT: source,
        text_toolkit.CF_HTML: b"<p>rich</p>",
        text_toolkit.CF_RTF: b"{\\rtf1 rich}",
    })
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = text_toolkit.strip_formats()

    assert success is True
    assert "HTML" in message
    assert "RTF" in message
    assert clipboard.formats == {MemoryClipboard.CF_UNICODETEXT: source}


def test_strip_formats_keeps_existing_plain_text_verbatim(monkeypatch):
    """已经是纯文本时不得顺手规范化任何字符。"""
    source = "  正文\t😀  "
    original = {MemoryClipboard.CF_UNICODETEXT: source}
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, message = text_toolkit.strip_formats()

    assert success is False
    assert "已经是纯文本" in message
    assert clipboard.formats == original


@pytest.mark.parametrize(
    "rich_format",
    [text_toolkit.CF_HTML, text_toolkit.CF_RTF],
)
def test_strip_formats_without_plain_text_preserves_original(
    monkeypatch,
    rich_format,
):
    """没有配套纯文字时不得尝试解析或清空富文本。"""
    original = {rich_format: b"rich-only"}
    clipboard = MemoryClipboard(original)
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    with pytest.raises(text_toolkit.EmptyContentError):
        text_toolkit.strip_formats()

    assert clipboard.formats == original


def test_generated_urls_preserve_every_business_query_segment():
    """组合生成的业务参数必须逐字保留，只删除插入的追踪片段。"""
    randomizer = random.Random(20260717)
    tracking_names = ["utm_source", "FBCLID", "trkCampaign", "mc_cid"]
    for case_index in range(300):
        business = [
            f"p{index}={randomizer.choice(['', 'a+b', '%20', '中文'])}"
            for index in range(randomizer.randint(1, 8))
        ]
        business.insert(randomizer.randrange(len(business) + 1), "p0=duplicate")
        tracking = (
            f"{randomizer.choice(tracking_names)}=remove-{case_index}"
        )
        parts = list(business)
        parts.insert(randomizer.randrange(len(parts) + 1), tracking)
        source = f"https://a.com/p?{'&'.join(parts)}#keep"
        expected = f"https://a.com/p?{'&'.join(business)}#keep"

        assert preview_clean_url(source) == expected
        assert preview_clean_url(preview_clean_url(source)) == expected


def test_encoded_tracking_key_is_removed_without_reencoding_business_data():
    """追踪键可被编码，但保留值不得因此重新编码。"""
    source = "https://a.com/p?q=a%20b&%75tm_source=test&empty="

    assert preview_clean_url(source) == "https://a.com/p?q=a%20b&empty="


def test_clean_url_preserves_non_query_url_spelling_verbatim():
    """净化不得规范化协议、主机、路径或锚点的原始拼写。"""
    source = (
        "HTTPS://Example.COM/Path;Case?Id=42&utm_source=test#Section"
    )

    assert preview_clean_url(source) == (
        "HTTPS://Example.COM/Path;Case?Id=42#Section"
    )


def test_generated_multiline_text_never_loses_non_boundary_content():
    """随机混合换行只移除行边界和每行首尾空白。"""
    randomizer = random.Random(20260717)
    newline_choices = ["\n", "\r\n", "\r", "\u2028", "\x85"]
    token_choices = ["中文", "emoji😀", "a  b", "x\ty", ""]
    for _case_index in range(300):
        lines = [
            f"  {randomizer.choice(token_choices)}  "
            for _line_index in range(randomizer.randint(2, 12))
        ]
        source = lines[0]
        for line in lines[1:]:
            source += randomizer.choice(newline_choices) + line
        expected = " ".join(line.strip() for line in lines if line.strip())

        assert preview_merge_lines(source) == expected


def test_strip_formats_preserves_large_unicode_text(monkeypatch):
    """较大 Unicode 内容必须逐字保留，不以截断换取速度。"""
    source = ("中文😀 e\u0301\r\n" * 100_000) + "结束"
    clipboard = MemoryClipboard({
        MemoryClipboard.CF_UNICODETEXT: source,
        text_toolkit.CF_HTML: b"<p>large</p>",
    })
    monkeypatch.setattr(text_toolkit, "wc", clipboard)

    success, _message = text_toolkit.strip_formats()

    assert success is True
    assert clipboard.formats == {MemoryClipboard.CF_UNICODETEXT: source}
