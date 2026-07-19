"""Windows 剪贴板非文本格式的统一安全判定。"""

from dataclasses import dataclass

import win32clipboard as wc


def _register_format(name: str) -> int:
    """注册并返回稳定格式 ID；失败时用 0 表示不可检测。"""
    try:
        return int(wc.RegisterClipboardFormat(name))
    except Exception:
        return 0


def _format_ids(*values: int) -> frozenset[int]:
    return frozenset(value for value in values if value > 0)


IMAGE_FORMAT_IDS = _format_ids(
    2,   # CF_BITMAP
    3,   # CF_METAFILEPICT
    6,   # CF_TIFF
    8,   # CF_DIB
    9,   # CF_PALETTE
    14,  # CF_ENHMETAFILE
    17,  # CF_DIBV5
    0x0082,  # CF_DSPBITMAP
    0x0083,  # CF_DSPMETAFILEPICT
    0x008E,  # CF_DSPENHMETAFILE
    _register_format("PNG"),
    _register_format("image/png"),
    _register_format("JFIF"),
    _register_format("image/jpeg"),
    _register_format("GIF"),
    _register_format("image/gif"),
    _register_format("image/webp"),
    _register_format("image/svg+xml"),
    _register_format("application/x-qt-image"),
)

FILE_FORMAT_IDS = _format_ids(
    15,  # CF_HDROP
    _register_format("FileGroupDescriptor"),
    _register_format("FileGroupDescriptorW"),
    _register_format("FileContents"),
    _register_format("Shell IDList Array"),
    _register_format("FileName"),
    _register_format("FileNameW"),
)

AUDIO_FORMAT_IDS = _format_ids(
    11,  # CF_RIFF
    12,  # CF_WAVE
    _register_format("audio/mpeg"),
    _register_format("audio/wav"),
    _register_format("audio/x-wav"),
)


_EMBEDDED_BINARY_MARKERS = (
    "<img", "<svg", "<object", "<embed", "<video", "<audio", "<iframe",
    "<picture", "<source", "<canvas", "<math",
    "data:image/", "data:audio/", "data:video/",
    "data:application/octet-stream",
    r"\pict", r"\shppict", r"\nonshppict",
    r"\object", r"\objdata", r"\objemb", r"\objlink",
)


def contains_embedded_binary_content(*values: object) -> bool:
    """检测 HTML/RTF 中会被纯文本转换删除的内嵌媒体。"""
    for value in values:
        if isinstance(value, bytes):
            text = value.decode("latin-1", errors="ignore")
        elif isinstance(value, str):
            text = value
        else:
            continue
        lowered = text.lower()
        if any(marker in lowered for marker in _EMBEDDED_BINARY_MARKERS):
            return True
    return False


@dataclass(frozen=True)
class BinaryClipboardKinds:
    """主动操作需要拒绝的非文本内容类别。"""

    has_image: bool
    has_file: bool
    has_audio: bool

    @property
    def has_binary(self) -> bool:
        return self.has_image or self.has_file or self.has_audio


def detect_binary_clipboard_kinds(clipboard) -> BinaryClipboardKinds:
    """在剪贴板已打开时检测必须保留的非文本格式。"""

    def has_any(format_ids: frozenset[int]) -> bool:
        return any(
            clipboard.IsClipboardFormatAvailable(format_id)
            for format_id in format_ids
        )

    return BinaryClipboardKinds(
        has_image=has_any(IMAGE_FORMAT_IDS),
        has_file=has_any(FILE_FORMAT_IDS),
        has_audio=has_any(AUDIO_FORMAT_IDS),
    )
