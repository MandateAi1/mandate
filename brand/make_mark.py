#!/usr/bin/env python3
"""Mandate brand mark v4 — stroked, not filled. Soft joins, round terminals.

v3 scored 10/10 on construction, but the letterform was a filled polygon, so every
corner was a hard vertex: a needle point at the centre of the M, and sharp cuts where
the diagonals met the cap line. Geometrically correct, unpleasant to look at.

v4 draws the letterform as ONE stroked polyline:

    left stem base -> left shoulder -> centre vertex -> right shoulder -> right stem base

one stroke width throughout, ROUND joins at every corner, ROUND caps at both ends.
The centre vertex becomes an arc instead of a point; the shoulders become soft turns
instead of mitres. Nothing in the mark is sharp.

Because it is a stroked path, weight is uniform by construction - the v2/v3 problem of
diagonals reading thinner than the stems cannot recur.

Emits mandate-mark.svg (deliverable) and mandate-mark.png (raster preview).
"""
from PIL import Image, ImageDraw

S = 1024
SS = 2

BG = (8, 9, 10)
BORDER = (44, 47, 54)
INK = (247, 248, 248)
INK_DEEP = (200, 204, 214)
ACCENT = (94, 106, 210)
ACCENT_HI = (131, 134, 255)

# --- geometry (unit space) ---------------------------------------------------
W = 0.150          # stroke width, used everywhere
INSET = 0.275      # the letterform's share of the container
CV = 0.700         # how deep the centre vertex dips
SHOULDER = 0.115   # how far below the cap the shoulders turn


def path():
    """One polyline traced left to right. Endpoints are the two stem bases."""
    x0, x1 = W / 2, 1 - W / 2
    return [
        (x0, 1.00),      # left stem base   (round cap)
        (x0, SHOULDER),  # left shoulder    (round join)
        (0.5, CV),       # centre vertex    (round join)
        (x1, SHOULDER),  # right shoulder   (round join)
        (x1, 1.00),      # right stem base  (round cap)
    ]


def _map(pts, k, inset=INSET):
    span = 1.0 - 2 * inset
    return [((inset + x * span) * k, (inset + y * span) * k) for x, y in pts]


def write_svg(out):
    k = 512
    pts = _map(path(), k)
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    r = 0.215 * k
    st = 0.020 * k
    lw = W * (1 - 2 * INSET) * k
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{k}" height="{k}" viewBox="0 0 {k} {k}" fill="none">
  <defs>
    <linearGradient id="ink" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="rgb{INK}"/><stop offset="100%" stop-color="rgb{INK_DEEP}"/>
    </linearGradient>
    <linearGradient id="acc" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="rgb{ACCENT_HI}"/><stop offset="100%" stop-color="rgb{ACCENT}"/>
    </linearGradient>
    <clipPath id="left"><rect x="0" y="0" width="{k/2:.1f}" height="{k}"/></clipPath>
    <clipPath id="right"><rect x="{k/2:.1f}" y="0" width="{k/2:.1f}" height="{k}"/></clipPath>
  </defs>
  <rect width="{k}" height="{k}" rx="{r:.1f}" fill="rgb{BG}"/>
  <rect x="{st/2:.1f}" y="{st/2:.1f}" width="{k-st:.1f}" height="{k-st:.1f}" rx="{r-st/2:.1f}"
        stroke="rgb{BORDER}" stroke-width="{st:.1f}"/>
  <g clip-path="url(#left)">
    <path d="{d}" stroke="url(#ink)" stroke-width="{lw:.1f}" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <g clip-path="url(#right)">
    <path d="{d}" stroke="url(#acc)" stroke-width="{lw:.1f}" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>
'''
    open(out, "w", encoding="utf-8").write(svg)


def render_png(out):
    Wp = S * SS
    img = Image.new("RGB", (Wp, Wp), BG)
    d = ImageDraw.Draw(img, "RGBA")
    st = int(0.020 * Wp)
    rad = int(0.215 * Wp)
    d.rounded_rectangle([st // 2, st // 2, Wp - st // 2, Wp - st // 2],
                        radius=rad - st // 2, outline=BORDER + (255,), width=st)

    pts = _map(path(), Wp)
    lw = int(W * (1 - 2 * INSET) * Wp)

    # the stroke goes on its own layer, so the colour split stays clean
    layer = Image.new("L", (Wp, Wp), 0)
    ld = ImageDraw.Draw(layer)
    ld.line(pts, fill=255, width=lw, joint="curve")      # rounds every corner
    for (x, y) in (pts[0], pts[-1]):                     # round the two terminals
        r = lw / 2
        ld.ellipse([x - r, y - r, x + r, y + r], fill=255)

    mid = Wp // 2
    for side, (x0, x1, top, bot) in (("L", (0, mid, INK, INK_DEEP)),
                                     ("R", (mid, Wp, ACCENT_HI, ACCENT))):
        m = layer.crop((x0, 0, x1, Wp))
        w = x1 - x0
        # vertical gradient inside the stroke: lighter at the top, deeper below
        grad = Image.new("RGB", (w, Wp))
        gd = ImageDraw.Draw(grad)
        for y in range(Wp):
            t = y / Wp
            gd.line([0, y, w, y], fill=(int(top[0] + (bot[0] - top[0]) * t),
                                        int(top[1] + (bot[1] - top[1]) * t),
                                        int(top[2] + (bot[2] - top[2]) * t)))
        img.paste(grad, (x0, 0), m)

    img = img.resize((S, S), Image.LANCZOS)
    img.save(out)


if __name__ == "__main__":
    write_svg("mandate-mark.svg")
    render_png("mandate-mark.png")
    print("wrote mandate-mark.svg and mandate-mark.png")
