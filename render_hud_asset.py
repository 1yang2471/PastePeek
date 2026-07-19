"""生成 README 使用的真实 300px HUD 截图。"""

import argparse
import os
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "assets" / "hud-expanded-300.png"


def _system_pyside_platforms() -> str | None:
    """定位系统 PySide6 的 Qt 平台插件。"""
    for base in site.getsitepackages() + [site.getusersitepackages()]:
        platforms = os.path.join(base, "PySide6", "plugins", "platforms")
        if os.path.isdir(platforms):
            return platforms
    return None


if platforms := _system_pyside_platforms():
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", platforms)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.explainer.outcome_predictor import OutcomePredictor  # noqa: E402
from src.ui import hud_window  # noqa: E402
from src.ui.hud_window import HudWindow  # noqa: E402


def _register_cjk_font() -> str:
    # 离屏 Qt 不会自动枚举系统字体，需要显式注册一个中文字体。
    fonts_dir = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    for filename in ('msyh.ttc', 'simhei.ttf', 'simsun.ttc'):
        font_id = QFontDatabase.addApplicationFont(str(fonts_dir / filename))
        if font_id < 0:
            continue
        for family in QFontDatabase.applicationFontFamilies(font_id):
            if QFontMetrics(QFont(family, 9)).inFontUcs4(0x4E2D):
                return family
    raise RuntimeError('CJK font unavailable')


def render_hud_asset(
    output_path: Path,
    ui_width: int = 300,
) -> tuple[int, int, int, int, str, bool]:
    """渲染展开态 HUD，并返回宽、高、有效像素数和颜色数。"""
    app = QApplication.instance() or QApplication([])
    font_family = _register_cjk_font()
    font = QFont(font_family, 9)
    cjk_supported = QFontMetrics(font).inFontUcs4(0x4E2D)
    if not cjk_supported:
        raise RuntimeError('CJK font unavailable')
    app.setFont(font)
    hud_window._FONT_FAMILY = font_family

    hud = HudWindow()
    hud._width = ui_width
    hud.setFixedSize(ui_width, hud_window._H_IDLE)
    output = OutcomePredictor().generate("rich_text", "terminal")
    output.raw_text = "项目计划\n- 核心功能\n- 质量测试"
    output.raw_html = (
        "<h2>项目计划</h2><ul><li><b>核心功能</b></li>"
        "<li>质量测试</li></ul>"
    )
    output.primary_action = "merge_lines"
    output.available_actions = ["merge_lines", "strip_formats"]
    hud.update_result(output)
    hud.show()
    app.processEvents()
    QTest.mouseClick(
        hud,
        Qt.MouseButton.LeftButton,
        pos=QPoint(ui_width - 20, 18),
    )
    app.processEvents()

    image = hud.grab().toImage()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(output_path), "PNG"):
        raise RuntimeError("HUD 截图保存失败")

    colors: set[int] = set()
    nontransparent = 0
    for y in range(image.height()):
        for x in range(image.width()):
            pixel = image.pixelColor(x, y)
            colors.add(pixel.rgba())
            if pixel.alpha() > 0:
                nontransparent += 1

    width, height = image.width(), image.height()
    if (width, height) != (ui_width, hud.height()):
        raise RuntimeError("HUD 截图尺寸与窗口不一致")
    if nontransparent < width * height * 0.5:
        raise RuntimeError("HUD 截图有效像素不足")
    if len(colors) < 16:
        raise RuntimeError("HUD 截图颜色层次异常")

    hud.close()
    return width, height, nontransparent, len(colors), font_family, cjk_supported


def _parse_args() -> argparse.Namespace:
    """解析截图输出路径。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="PNG 输出路径，默认覆盖 README 使用的截图",
    )
    parser.add_argument(
        "--width",
        type=int,
        choices=(300, 400, 640),
        default=300,
        help="HUD 视觉复核宽度，默认 300",
    )
    return parser.parse_args()


def main() -> None:
    """生成截图并输出可供自动化读取的验收数据。"""
    args = _parse_args()
    output_path = args.output.resolve()
    width, height, nontransparent, colors, font_family, cjk_supported = (
        render_hud_asset(output_path, args.width)
    )
    print(f'font={font_family} cjk_supported={str(cjk_supported).lower()}')
    print(
        f"rendered={output_path} size={width}x{height} "
        f"nontransparent={nontransparent} colors={colors}"
    )


if __name__ == "__main__":
    main()
