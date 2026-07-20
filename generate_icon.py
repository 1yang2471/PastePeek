"""生成 PastePeek 的 Windows 图标。

图标使用剪贴板、预览之眼和风险标记组成，适配托盘、窗口标题栏和 EXE
资源管理器视图。没有 Pillow 时仍保留低分辨率原始 ICO 回退路径。

用法：python generate_icon.py（生成 assets/icon.ico）
"""

from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT = ROOT / "assets" / "icon.ico"
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
ICON_SIZE_PAIRS = tuple((size, size) for size in ICON_SIZES)


def _draw_pastepeek_icon(size: int):
    """在高分辨率画布上绘制可缩放的剪贴板预览图标。"""
    from PIL import Image, ImageDraw

    scale = 4
    # 始终在固定高分辨率画布上绘制，再缩放到目标尺寸，避免小图标坐标越界。
    canvas_size = 256 * scale
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(left: int, top: int, right: int, bottom: int) -> tuple[int, ...]:
        return tuple(round(value * scale) for value in (left, top, right, bottom))

    def stroke(width: int) -> int:
        return max(1, round(width * scale))

    # 深色剪贴板轮廓让 16px 托盘图标仍保持清晰的外形。
    draw.rounded_rectangle(
        box(28, 30, 228, 236),
        radius=round(42 * scale),
        fill="#16324F",
    )
    draw.rounded_rectangle(
        box(54, 62, 202, 218),
        radius=round(20 * scale),
        fill="#F8FAFC",
    )

    # 顶部夹子使用产品青绿色，和 HUD 的主要操作色保持一致。
    draw.rounded_rectangle(
        box(84, 20, 172, 72),
        radius=round(22 * scale),
        fill="#16324F",
    )
    draw.rounded_rectangle(
        box(101, 27, 155, 54),
        radius=round(13 * scale),
        fill="#0F766E",
    )

    # 眼睛代表“预览”，中心瞳孔保留深色对比，缩小后不会糊成色块。
    draw.ellipse(
        box(74, 108, 182, 174),
        fill="#D8F3EE",
        outline="#0F766E",
        width=stroke(9),
    )
    draw.ellipse(box(111, 124, 145, 158), fill="#16324F")
    draw.ellipse(box(119, 128, 129, 138), fill="#FFFFFF")

    # 纸面下方的短线暗示被预览的文本内容。
    draw.rounded_rectangle(
        box(84, 188, 171, 198),
        radius=round(5 * scale),
        fill="#9AAEBD",
    )

    # 琥珀色小标记对应风险提示，不抢占剪贴板主体的视觉重量。
    draw.ellipse(box(176, 184, 216, 224), fill="#D97706")
    draw.line(
        (round(196 * scale), round(192 * scale), round(196 * scale), round(207 * scale)),
        fill="#FFFFFF",
        width=stroke(6),
    )
    draw.ellipse(box(193, 212, 199, 218), fill="#FFFFFF")

    return image.resize((size, size), Image.Resampling.LANCZOS)


def _build_minimal_ico(output_path: Path):
    """在无 Pillow 时生成一个可用的低分辨率眼睛回退图标。"""

    # ICO file format:
    # Header: reserved(2) + type(2) + count(2)
    # Entry:  w(1) h(1) colors(1) reserved(1) planes(2) bpp(2) size(4) offset(4)
    # Image data: BMP header + AND mask + XOR mask

    import struct

    width, height = 32, 32
    # 32x32 16-color BMP + XOR mask (4bpp = 2 pixels/byte)
    xor_size = width * height // 2  # 4 bits per pixel = 512 bytes
    and_size = width * height // 8  # 1 bit per pixel = 128 bytes
    data_size = xor_size + and_size + 40  # 40 = BITMAPINFOHEADER at data start

    # Build the BMP image data (embedded inside ICO entry)
    # BITMAPINFOHEADER: biSize(4) + biWidth(4) + biHeight*2(4) + biPlanes(2) + biBitCount(2)
    bmp_header = struct.pack(
        "<IiiHHIIiiII",
        40,           # biSize
        width,        # biWidth
        height * 2,   # biHeight (double for ICO: XOR + AND masks)
        1,            # biPlanes
        4,            # biBitCount (4-bit = 16 colors)
        0,            # biCompression
        data_size - 40,  # biSizeImage
        0, 0, 0, 0,  # unused
    )

    # Color palette: 16 entries (BGR0)
    palette = bytearray(4 * 16)
    # Color 0: transparent (black)
    palette[0:4] = b'\x00\x00\x00\x00'
    # Color 1: dark blue (eye outline)
    palette[4:8] = b'\xd6\x54\x1b\x00'  # #1b54d6 -> BGR
    # Color 2: medium blue
    palette[8:12] = b'\xc0\x76\x25\x00'  # #2576c0
    # Color 3: light blue (center highlight)
    palette[12:16] = b'\xd9\x98\x34\x00'  # #3498d9
    # Remaining colors: gray shades
    for i in range(4, 16):
        g = 0x44 + i * 12
        palette[i*4:(i+1)*4] = bytes([g, g, g, 0])

    xor_mask = bytearray(xor_size)
    and_mask = bytearray(and_size)

    # Draw a simple circle (eye/predictor icon)
    cx, cy, r = 16, 16, 13
    for y in range(height):
        for x in range(width):
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            idx = y * width + x
            byte_idx = idx // 2
            nibble = 3 if idx % 2 == 0 else 0  # which nibble (high/low)

            if dist <= r:
                # Inside circle: alternating blue shades for depth
                if dist < 4:
                    pixel = 3  # light blue center
                elif dist < 9:
                    pixel = 2  # medium blue
                else:
                    pixel = 1  # dark blue outline

                if nibble == 3:
                    xor_mask[byte_idx] |= (pixel << 4)
                else:
                    xor_mask[byte_idx] |= pixel

            # AND mask: 0 = draw pixel, 1 = transparent
            # Leave all 0 (visible)

    image_data = bmp_header + palette + bytes(xor_mask) + bytes(and_mask)

    # ICO file header
    ico_header = struct.pack("<HHH", 0, 1, 1)  # reserved, type=ICO, count=1
    offset = 6 + 16  # header(6) + entry(16)

    entry = struct.pack(
        "<BBBBHHII",
        width, height,
        16,  # color count (0 = 256+ colors, but we use 16)
        0,   # reserved
        1,   # planes
        4,   # bpp
        len(image_data),
        offset,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(ico_header + entry + image_data)
    print(f"Icon generated: {output_path}")


def generate_icon(output_path: Path):
    """生成多尺寸透明 ICO，Pillow 不可用时回退到原始 ICO。"""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        base = _draw_pastepeek_icon(256)
        base.save(str(output_path), format="ICO", sizes=ICON_SIZE_PAIRS)
        print(f"Icon generated (Pillow, sizes={ICON_SIZES}): {output_path}")

    except ImportError:
        _build_minimal_ico(output_path)


if __name__ == "__main__":
    generate_icon(OUTPUT)
