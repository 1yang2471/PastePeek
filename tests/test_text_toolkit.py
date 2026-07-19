"""测试 text_toolkit 错误处理和鲁棒性增强。"""
from unittest import mock

import pytest
import pywintypes

from src.manipulator import text_toolkit
from src.manipulator.text_toolkit import (
    ClipboardBusyError,
    EmptyContentError,
    clean_url,
    merge_lines,
    preview_clean_url,
    preview_merge_lines,
    preview_strip_formats,
    strip_formats,
)


def _only_formats(*allowed):
    """构造只报告指定剪贴板格式存在的系统边界。"""
    return lambda format_id: format_id in allowed


@pytest.fixture(autouse=True)
def _enumerate_mocked_formats(monkeypatch):
    """让格式枚举与每个用例模拟的可用格式保持一致。"""
    candidates = sorted({
        text_toolkit.wc.CF_UNICODETEXT,
        text_toolkit.CF_HTML,
        text_toolkit.CF_RTF,
    })

    def enumerate_formats(previous):
        for format_id in candidates:
            if (
                format_id > previous
                and text_toolkit.wc.IsClipboardFormatAvailable(format_id)
            ):
                return format_id
        return 0

    monkeypatch.setattr(
        text_toolkit.wc,
        "EnumClipboardFormats",
        enumerate_formats,
    )


class TestCustomExceptions:
    """验证自定义异常类存在且可正常使用。"""

    def test_clipboard_busy_error_is_exception(self):
        """ClipboardBusyError 是 Exception 子类。"""
        assert issubclass(ClipboardBusyError, Exception)

    def test_empty_content_error_is_exception(self):
        """EmptyContentError 是 Exception 子类。"""
        assert issubclass(EmptyContentError, Exception)

    def test_clipboard_busy_error_message(self):
        """ClipboardBusyError 携带友好提示信息。"""
        err = ClipboardBusyError("剪贴板被其他程序占用，请稍后重试")
        assert "剪贴板被其他程序占用" in str(err)

    def test_empty_content_error_message(self):
        """EmptyContentError 携带友好提示信息。"""
        err = EmptyContentError("处理后内容为空，已取消操作")
        assert "处理后内容为空" in str(err)


class TestStripFormatsRobustness:
    """strip_formats() 的异常处理与空内容检测。"""

    def test_raises_clipboard_busy_on_openclipboard_failure(self):
        """OpenClipboard 因 pywintypes.error 失败时抛出 ClipboardBusyError。"""
        with mock.patch("src.manipulator.text_toolkit.wc.OpenClipboard") as m_open:
            m_open.side_effect = pywintypes.error(5, "OpenClipboard", "拒绝访问")
            # _ensure_clipboard_closed 在 pywintypes.error 捕获前会调用 CloseClipboard
            with mock.patch("src.manipulator.text_toolkit.wc.CloseClipboard"):
                with pytest.raises(ClipboardBusyError, match="剪贴板被其他程序占用"):
                    strip_formats()

    def test_raises_clipboard_busy_on_write_failure(self):
        """写入剪贴板时 pywintypes.error → ClipboardBusyError。"""
        with mock.patch("src.manipulator.text_toolkit.wc.OpenClipboard"):
            with mock.patch("src.manipulator.text_toolkit.wc.CloseClipboard"):
                # 模拟：CF_UNICODETEXT 有数据，CF_HTML 也有（has_html=True 进入写路径）
                with mock.patch("src.manipulator.text_toolkit.wc.IsClipboardFormatAvailable") as m_avail:
                    m_avail.side_effect = _only_formats(
                        text_toolkit.wc.CF_UNICODETEXT,
                        text_toolkit.CF_HTML,
                    )
                    with mock.patch("src.manipulator.text_toolkit.wc.GetClipboardData", return_value="hello"):
                        with mock.patch("src.manipulator.text_toolkit.wc.EmptyClipboard"):
                            with mock.patch("src.manipulator.text_toolkit.wc.SetClipboardText") as m_set:
                                m_set.side_effect = pywintypes.error(5, "SetClipboardText", "拒绝访问")
                                with pytest.raises(ClipboardBusyError, match="剪贴板被其他程序占用"):
                                    strip_formats()

    def test_raises_empty_content_when_text_is_whitespace(self):
        """剪贴板仅含空白文本时抛出 EmptyContentError。"""
        with mock.patch("src.manipulator.text_toolkit.wc.OpenClipboard"):
            with mock.patch("src.manipulator.text_toolkit.wc.CloseClipboard"):
                with mock.patch("src.manipulator.text_toolkit.wc.IsClipboardFormatAvailable") as m_avail:
                    m_avail.side_effect = _only_formats(
                        text_toolkit.wc.CF_UNICODETEXT,
                        text_toolkit.CF_HTML,
                    )
                    with mock.patch("src.manipulator.text_toolkit.wc.GetClipboardData", return_value="   \n  "):
                        with pytest.raises(EmptyContentError, match="处理后内容为空"):
                            strip_formats()


class TestMergeLinesRobustness:
    """merge_lines() 的异常处理与空内容检测。"""

    def test_raises_clipboard_busy_on_openclipboard_failure(self):
        """OpenClipboard 因 pywintypes.error 失败时抛出 ClipboardBusyError。"""
        with mock.patch("src.manipulator.text_toolkit.wc.OpenClipboard") as m_open:
            m_open.side_effect = pywintypes.error(5, "OpenClipboard", "拒绝访问")
            with mock.patch("src.manipulator.text_toolkit.wc.CloseClipboard"):
                with pytest.raises(ClipboardBusyError, match="剪贴板被其他程序占用"):
                    merge_lines()

    def test_raises_clipboard_busy_on_write_failure(self):
        """写入剪贴板时 pywintypes.error → ClipboardBusyError。"""
        with mock.patch("src.manipulator.text_toolkit.wc.OpenClipboard"):
            with mock.patch("src.manipulator.text_toolkit.wc.CloseClipboard"):
                with mock.patch("src.manipulator.text_toolkit.wc.IsClipboardFormatAvailable") as m_avail:
                    m_avail.side_effect = _only_formats(
                        text_toolkit.wc.CF_UNICODETEXT,
                    )
                    # 多行文本 → 进入 merge 路径 → 进入写路径
                    with mock.patch("src.manipulator.text_toolkit.wc.GetClipboardData", return_value="line1\nline2"):
                        with mock.patch("src.manipulator.text_toolkit.wc.EmptyClipboard"):
                            with mock.patch("src.manipulator.text_toolkit.wc.SetClipboardText") as m_set:
                                m_set.side_effect = pywintypes.error(5, "SetClipboardText", "拒绝访问")
                                with pytest.raises(ClipboardBusyError, match="剪贴板被其他程序占用"):
                                    merge_lines()

    def test_raises_empty_content_when_merged_becomes_empty(self):
        """合并后内容全为空白时抛出 EmptyContentError。"""
        with mock.patch("src.manipulator.text_toolkit.wc.OpenClipboard"):
            with mock.patch("src.manipulator.text_toolkit.wc.CloseClipboard"):
                with mock.patch("src.manipulator.text_toolkit.wc.IsClipboardFormatAvailable") as m_avail:
                    m_avail.side_effect = _only_formats(
                        text_toolkit.wc.CF_UNICODETEXT,
                    )
                    with mock.patch("src.manipulator.text_toolkit.wc.GetClipboardData", return_value="\n\n\n   \n"):
                        with pytest.raises(EmptyContentError, match="处理后内容为空"):
                            merge_lines()


class TestCleanUrlRobustness:
    """clean_url() 的异常处理与空内容检测。"""

    def test_raises_clipboard_busy_on_openclipboard_failure(self):
        """OpenClipboard 因 pywintypes.error 失败时抛出 ClipboardBusyError。"""
        with mock.patch("src.manipulator.text_toolkit.wc.OpenClipboard") as m_open:
            m_open.side_effect = pywintypes.error(5, "OpenClipboard", "拒绝访问")
            with mock.patch("src.manipulator.text_toolkit.wc.CloseClipboard"):
                with pytest.raises(ClipboardBusyError, match="剪贴板被其他程序占用"):
                    clean_url()

    def test_raises_clipboard_busy_on_write_failure(self):
        """写入剪贴板时 pywintypes.error → ClipboardBusyError。"""
        with mock.patch("src.manipulator.text_toolkit.wc.OpenClipboard"):
            with mock.patch("src.manipulator.text_toolkit.wc.CloseClipboard"):
                with mock.patch("src.manipulator.text_toolkit.wc.IsClipboardFormatAvailable") as m_avail:
                    m_avail.side_effect = _only_formats(
                        text_toolkit.wc.CF_UNICODETEXT,
                    )
                    # URL + 追踪参数 → 进入写入路径
                    with mock.patch("src.manipulator.text_toolkit.wc.GetClipboardData",
                                    return_value="https://example.com?utm_source=test"):
                        with mock.patch("src.manipulator.text_toolkit.wc.EmptyClipboard"):
                            with mock.patch("src.manipulator.text_toolkit.wc.SetClipboardText") as m_set:
                                m_set.side_effect = pywintypes.error(5, "SetClipboardText", "拒绝访问")
                                with pytest.raises(ClipboardBusyError, match="剪贴板被其他程序占用"):
                                    clean_url()

    def test_raises_empty_content_when_clipboard_is_whitespace(self):
        """剪贴板仅含空白时抛出 EmptyContentError。"""
        with mock.patch("src.manipulator.text_toolkit.wc.OpenClipboard"):
            with mock.patch("src.manipulator.text_toolkit.wc.CloseClipboard"):
                with mock.patch("src.manipulator.text_toolkit.wc.IsClipboardFormatAvailable") as m_avail:
                    m_avail.side_effect = _only_formats(
                        text_toolkit.wc.CF_UNICODETEXT,
                    )
                    with mock.patch("src.manipulator.text_toolkit.wc.GetClipboardData", return_value="   "):
                        with pytest.raises(EmptyContentError, match="处理后内容为空"):
                            clean_url()


class TestPreviewFunctionsUnaffected:
    """preview 函数不受此次改动影响。"""

    def test_preview_clean_url_strips_tracking(self):
        result = preview_clean_url("https://a.com/p?utm_source=x")
        assert "utm_source" not in result

    def test_preview_clean_url_preserves_normal_url(self):
        result = preview_clean_url("https://a.com/p?id=1&page=2")
        assert "id=1" in result
        assert "page=2" in result

    def test_preview_strip_formats_returns_unchanged(self):
        assert preview_strip_formats("hello world") == "hello world"

    def test_preview_merge_lines(self):
        result = preview_merge_lines("a\nb\nc")
        assert result == "a b c"


class TestToolkitFunctionsAvailable:
    """工具函数签名保持不变且可调用。"""

    def test_strip_formats_is_callable(self):
        assert callable(strip_formats)

    def test_merge_lines_is_callable(self):
        assert callable(merge_lines)

    def test_clean_url_is_callable(self):
        assert callable(clean_url)
