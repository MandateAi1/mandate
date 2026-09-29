#!/usr/bin/env python3
"""X profile assets for Mandate: avatar (400x400) and banner (1500x500).

The avatar is rendered WITHOUT the rounded-square container, on a circular field.
X crops avatars to a circle, so shipping the square version would clip the
container's corners and leave four dark notches. Rendering the mark on a disc
means the crop is invisible.

The banner follows the same system: Linear's near-black canvas, one accent, the
mark at the left, the wordmark and a single honest line of copy. Nothing busy -
banners get cropped differently on mobile, so the content stays centred.
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
import make_mark as m

BG = (8, 9, 10)
INK = (247, 248, 248)
INK_DIM = (138, 143, 152)
ACCENT = (94, 106, 210)
ACCENT_HI = (131, 134, 255)
LINE = (35, 37, 42)


def load_font(size, bold=False):
    """Try a few likely fonts; fall back to the default so this never crashes."""
    for name in (("Inter-Bold.ttf", "arialbd.ttf", "segoeuib.ttf") if bold
                 else ("Inter-Regular.ttf", "arial.ttf", "segoeui.ttf")):
        for base in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu", "."):
            try:
                return ImageFont.truetype(f"{base}\\{name}" if "\\" in base else f"{base}/{name}", size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_mark(d, cx, cy, size, split=True):
    """Draw the letterform centred on (cx, cy) at the given height."""
    pts = m.path()
    k = size
    span = 1.0 - 2 * m.INSET
    def T(p):
        return (cx - k * span / 2 + p[0] * k * span, cy - k * span / 2 + p[1] * k * span)
    mapped = [T(p) for p in pts]
    lw = int(m.W * span * k)

    layer = Image.new("L", d._image.size, 0)
    ld = ImageDraw.Draw(layer)
    ld.line(mapped, fill=255, width=lw, joint="curve")
    for (x, y) in (mapped[0], mapped[-1]):
        r = lw / 2
        ld.ellipse([x - r, y - r, x + r, y + r], fill=255)

    W, H = d._image.size
    mid = int(cx)
    left = Image.new("RGB", (mid, H), INK)
    right = Image.new("RGB", (W - mid, H), ACCENT)
    d._image.paste(left, (0, 0), layer.crop((0, 0, mid, H)))
    d._image.paste(right, (mid, 0), layer.crop((mid, 0, W, H)))


def avatar(out="x-avatar.png", S=400):
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img, "RGBA")
    # circular field with a faint rim, so the crop lands on the edge
    d.ellipse([6, 6, S - 6, S - 6], fill=(11, 12, 14, 255), outline=LINE + (255,), width=3)
    glow = Image.new("RGB", (S, S), BG)
    gd = ImageDraw.Draw(glow, "RGBA")
    for r in range(S // 2, 0, -6):
        a = int(26 * (1 - r / (S / 2)) ** 2)
        gd.ellipse([S/2 - r, S/2 - r, S/2 + r, S/2 + r], fill=ACCENT + (a,))
    img = Image.blend(img, glow, 0.55)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([6, 6, S - 6, S - 6], outline=LINE + (255,), width=3)
    draw_mark(d, S / 2, S / 2, S * 1.10)
    img.save(out)
    return out


def banner(out="x-banner.png", W=1500, H=500):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")

    # a tighter glow behind the mark - the previous one read as muddy
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow, "RGBA")
    for r in range(420, 0, -8):
        a = int(38 * (1 - r / 420) ** 3)
        gd.ellipse([286 - r, H/2 - r, 286 + r, H/2 + r], fill=ACCENT + (a,))
    img = Image.blend(img, glow, 0.7)
    d = ImageDraw.Draw(img, "RGBA")

    d.rectangle([0, 0, W - 1, H - 1], outline=LINE + (255,), width=2)

    # the mark
    draw_mark(d, 286, H / 2, 290)

    f_big = load_font(62, bold=True)
    f_small = load_font(24)
    x = 500

    # Everything sits inside the central band (y 165..335) so X's mobile crop
    # - which trims to roughly the middle 600x200 - cannot cut it off.
    l1 = "Permission slips for AI agents."
    l2 = "Scoped, capped, expiring, revocable - recorded on-chain."
    d.text((x, 176), "Mandate", font=f_big, fill=INK)
    d.text((x, 254), l1, font=f_small, fill=INK_DIM)
    d.text((x, 288), l2, font=f_small, fill=INK_DIM)

    # the accent rule, aligned to the text block's true left edge: PIL draws from
    # the glyph origin, so the visible P starts a little to the right of x. Measure
    # it rather than guessing.
    left_edge = d.textbbox((x, 254), l1, font=f_small)[0]
    d.rectangle([left_edge, 240, left_edge + 88, 243], fill=ACCENT_HI)

    img.save(out)
    return out


if __name__ == "__main__":
    a = avatar()
    b = banner()
    print("wrote", a, "and", b)
