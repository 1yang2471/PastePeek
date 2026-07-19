"""为 HUD 生成轻量 Lucide 线性图标。"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# 路径数据来自 Lucide，使用 ISC License。
_ICON_BODIES = {
    "file-text": (
        '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>'
    ),
    "globe": (
        '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/>'
        '<path d="M12 2a15.3 15.3 0 0 1 0 20 15.3 15.3 0 0 1 0-20z"/>'
    ),
    "code": (
        '<path d="m18 16 4-4-4-4"/><path d="m6 8-4 4 4 4"/>'
        '<path d="m14.5 4-5 16"/>'
    ),
    "terminal": '<path d="M4 17 10 11 4 5"/><path d="M12 19h8"/>',
    "eraser": (
        '<path d="m7 21-4.3-4.3c-.9-.9-.9-2.3 0-3.2L13.4 2.8c.9-.9 2.3-.9 3.2 0l4.6 4.6c.9.9.9 2.3 0 3.2L11.8 20c-.6.6-1.3 1-2.2 1H7Z"/>'
        '<path d="m5 11 9 9"/><path d="M5 21h14"/>'
    ),
    "link": (
        '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
        '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'
    ),
    "rows": '<path d="M3 6h18"/><path d="M3 12h18"/><path d="M3 18h18"/>',
    "minus": '<path d="M5 12h14"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
}


def lucide_icon(name: str, color: str = "#334155", size: int = 16) -> QIcon:
    """把内置 Lucide 路径渲染为适合 Qt 按钮使用的图标。"""
    body = _ICON_BODIES.get(name)
    if body is None:
        return QIcon()
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</svg>"
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
