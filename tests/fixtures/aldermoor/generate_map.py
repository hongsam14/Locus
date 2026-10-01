"""Generate a stylized demo world map (Aldermoor) PNG for VLM ingestion testing.

Reproducible: `python examples/demo_world/generate_map.py` -> examples/demo_world/map.png

The map intentionally renders the features described in memo.txt / map.json so the
VLM can extract them: two provinces (Greenvale, Frostreach) split by the Spine
Mountains, the Aldwen River, a western coast, and two towns (Riverton, Highcrag).
"""

from __future__ import annotations

import math
import os

from PIL import Image, ImageColor, ImageDraw, ImageFont

W, H = 1024, 720
OUT = os.path.join(os.path.dirname(__file__), "map.png")

PARCHMENT = (239, 226, 192)
GREENVALE = (197, 214, 165)
FROSTREACH = (200, 214, 224)
SEA = (150, 186, 200)
RIVER = (90, 150, 190)
MOUNTAIN = (120, 110, 96)
MOUNTAIN_SNOW = (245, 245, 245)
INK = (60, 48, 36)


def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _text(d: ImageDraw.ImageDraw, xy, s, size, fill=INK, anchor="mm"):
    d.text(xy, s, font=_font(size), fill=fill, anchor=anchor)


def main() -> None:
    img = Image.new("RGB", (W, H), PARCHMENT)
    d = ImageDraw.Draw(img)

    # Sea (west coast) + land split into two provinces by the central mountains.
    d.rectangle([0, 0, 140, H], fill=SEA)
    d.polygon([(140, 0), (520, 0), (470, H), (140, H)], fill=GREENVALE)  # Greenvale (west)
    d.polygon([(520, 0), (W, 0), (W, H), (470, H)], fill=FROSTREACH)  # Frostreach (east)

    # Spine Mountains — a vertical band of peaks between the provinces.
    for i in range(9):
        cy = 40 + i * 80
        cx = 500 + (10 if i % 2 else -10)
        d.polygon(
            [(cx - 55, cy + 45), (cx, cy - 50), (cx + 55, cy + 45)], fill=MOUNTAIN
        )
        d.polygon([(cx - 18, cy + 2), (cx, cy - 50), (cx + 18, cy + 2)], fill=MOUNTAIN_SNOW)

    # Aldwen River — flows through Greenvale to the western coast.
    river = [(330, 30), (310, 160), (270, 300), (250, 430), (200, 560), (140, 610)]
    d.line(river, fill=RIVER, width=10, joint="curve")

    # Towns.
    def town(x, y, name, label_dx=14):
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(150, 60, 50), outline="white", width=3)
        _text(d, (x + label_dx, y), name, 26, anchor="lm")

    town(255, 360, "Riverton")  # in Greenvale, by the river
    town(760, 300, "Highcrag")  # in Frostreach, beyond the mountains

    # Labels.
    _text(d, (W // 2, 28), "Kingdom of Aldermoor", 34)
    _text(d, (330, 120), "Greenvale", 28, fill=(70, 90, 50))
    _text(d, (800, 120), "Frostreach", 28, fill=(70, 90, 110))
    _text(d, (505, H - 28), "Spine Mountains", 22, fill=INK)
    _text(d, (70, H // 2), "Sea", 24, fill=(40, 70, 85))
    # river label, rotated-ish via small caption
    _text(d, (300, 230), "Aldwen R.", 18, fill=(40, 80, 110), anchor="lm")

    # subtle border
    d.rectangle([4, 4, W - 5, H - 5], outline=INK, width=3)

    img.save(OUT)
    print(f"wrote {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
