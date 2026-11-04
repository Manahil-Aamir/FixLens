from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path("assets/branding")
OUT.mkdir(parents=True, exist_ok=True)

BG = (17, 24, 39)      # #111827
CYAN = (6, 182, 212)   # #06B6D4
SIZE = 1024


def glyph(draw: ImageDraw.ImageDraw, scale: float = 1.0) -> None:
    """A scan frame (four corner brackets) with a lens ring in the middle."""
    c = SIZE // 2
    half, t, arm = int(280 * scale), int(56 * scale), int(170 * scale)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = c + sx * half, c + sy * half
            h_xs, h_ys = sorted([x, x - sx * arm]), sorted([y, y - sy * t])
            v_xs, v_ys = sorted([x, x - sx * t]), sorted([y, y - sy * arm])
            draw.rounded_rectangle((h_xs[0], h_ys[0], h_xs[1], h_ys[1]), radius=t // 2, fill=CYAN)
            draw.rounded_rectangle((v_xs[0], v_ys[0], v_xs[1], v_ys[1]), radius=t // 2, fill=CYAN)
    ring, w, dot = int(110 * scale), int(44 * scale), int(34 * scale)
    draw.ellipse((c - ring, c - ring, c + ring, c + ring), outline=CYAN, width=w)
    draw.ellipse((c - dot, c - dot, c + dot, c + dot), fill=CYAN)


# App icon: solid background, no transparency (iOS requires that)
icon = Image.new("RGB", (SIZE, SIZE), BG)
glyph(ImageDraw.Draw(icon), 1.15)
icon.save(OUT / "icon.png")

# Android adaptive icon foreground and splash image: transparent, artwork in the middle
for name in ("adaptive-icon.png", "splash-icon.png"):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glyph(ImageDraw.Draw(img), 1.0)
    img.save(OUT / name)

print("Created:", *sorted(p.name for p in OUT.iterdir()))