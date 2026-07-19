"""Generate a minimal PastePeek icon (.ico) using built-in Pillow.

If Pillow is not installed, generates a low-res .ico using raw bytes
as a fallback.

Usage: python generate_icon.py  (creates assets/icon.ico)
"""

from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT = ROOT / "assets" / "icon.ico"


def _build_minimal_ico(output_path: Path):
    """Build a valid .ico from raw bytes — no external dependencies needed.

    Icon: 32x32, 16 colors, a simple blue circle on transparent background
    representing 'risk detection' (eye/magnifier concept).
    """

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
    """Generate icon, trying Pillow first, falling back to raw bytes."""
    try:
        from PIL import Image, ImageDraw

        Assets = ROOT / "assets"
        Assets.mkdir(parents=True, exist_ok=True)

        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Outer circle (dark blue)
        draw.ellipse([4, 4, 60, 60], fill=(27, 84, 214, 255))  # #1b54d6
        # Inner circle (medium blue)
        draw.ellipse([8, 8, 56, 56], fill=(37, 118, 192, 255))  # #2576c0
        # Center (light blue highlight)
        draw.ellipse([16, 16, 48, 48], fill=(52, 152, 217, 255))  # #3498d9

        # White "eye" pupil (simplified)
        draw.ellipse([22, 22, 42, 42], fill=(255, 255, 255, 255))
        # Blue pupil center
        draw.ellipse([28, 28, 36, 36], fill=(27, 84, 214, 255))

        img.save(str(output_path), format="ICO", sizes=[(32, 32)])
        print(f"Icon generated (Pillow): {output_path}")

    except ImportError:
        _build_minimal_ico(output_path)


if __name__ == "__main__":
    generate_icon(OUTPUT)
