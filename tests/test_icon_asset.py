"""PastePeek 应用图标的发行资产契约测试。"""

from pathlib import Path

from PIL import Image

import generate_icon

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SIZES = set(generate_icon.ICON_SIZES)


def _read_icon_sizes(path: Path) -> dict[tuple[int, int], Image.Image]:
    """读取 ICO 中的全部尺寸，确保每个尺寸都实际可解码。"""
    icon = Image.open(path)
    return {size: icon.ico.getimage(size) for size in icon.ico.sizes()}


def test_generated_icon_contains_all_release_sizes_and_alpha(tmp_path):
    """生成器必须输出所有 Windows 场景所需的透明 RGBA 尺寸。"""
    output = tmp_path / "icon.ico"

    generate_icon.generate_icon(output)
    images = _read_icon_sizes(output)

    assert set(images) == {(size, size) for size in EXPECTED_SIZES}
    for size, image in images.items():
        assert image.mode == "RGBA", size
        alpha_min, alpha_max = image.getchannel("A").getextrema()
        assert alpha_min == 0, size
        assert alpha_max > 0, size


def test_checked_in_icon_has_visible_16px_foreground():
    """仓库中的托盘图标不能是全透明或仅有极少可见像素。"""
    images = _read_icon_sizes(ROOT / "assets" / "icon.ico")
    image = images[(16, 16)]
    alpha = image.getchannel("A")
    visible_pixels = sum(alpha.histogram()[1:])

    assert visible_pixels >= 16 * 16 * 0.20
