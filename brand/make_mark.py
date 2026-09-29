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
W = 0.115          # stroke width, used everywhere
INSET = 0.275      # the letterform's share of the container
X_L, X_R = 0.10, 0.90      # the two stem centres
TOP, BOT = 0.06, 0.94      # how far the stems run
REACH = 0.36       # how far each diagonal travels toward the centre


def paths():
    """Two disconnected halves with a gap between them.

    Each half is one polyline: a full-height stem that turns into a diagonal.
    The LEFT diagonal leaves the stem's top and travels down-right; the RIGHT
    diagonal leaves the centre and travels down-right into the stem's bottom.

    The result is point-symmetric: rotating the mark 180 degrees about its centre
    maps each half exactly onto the other. That is what makes it read as an M
    while being a single repeated gesture rather than two mirrored letters.

    The gap is deliberate - the halves never touch.
    """
    left = [(X_L, BOT), (X_L, TOP), (X_L + REACH, TOP + REACH)]
    right = [(X_R, TOP), (X_R, BOT), (X_R - REACH, BOT - REACH)]
    return [left, right]


def _map(pts, k, inset=INSET):
    span = 1.0 - 2 * inset
    return [((inset + x * span) * k, (inset + y * span) * k) for x, y in pts]


def write_svg(out):
    k = 512
    ds = []
    for pl in paths():
        pts = _map(pl, k)
        ds.append("M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts))
    r = 0.215 * k
    st = 0.020 * k
    lw = W * (1 - 2 * INSET) * k
    # One continuous gradient across the letterform instead of two hard-clipped
    # halves. The direction still carries the meaning - ink on the left, accent on
    # the right - but with no seam, which is what dates a two-tone mark.
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{k}" height="{k}" viewBox="0 0 {k} {k}" fill="none">
  <defs>
    <linearGradient id="body" x1="0" y1="0" x2="1" y2="0.35">
      <stop offset="0%"   stop-color="#ffffff"/>
      <stop offset="38%"  stop-color="#e9ecff"/>
      <stop offset="70%"  stop-color="#c3caff"/>
      <stop offset="100%" stop-color="#a4adff"/>
    </linearGradient>
    <linearGradient id="shell" x1="0" y1="0" x2="0.6" y2="1">
      <stop offset="0%"   stop-color="#15171d"/>
      <stop offset="100%" stop-color="#0a0b0e"/>
    </linearGradient>
    <radialGradient id="lift" cx="34%" cy="26%" r="72%">
      <stop offset="0%"   stop-color="#5e6ad2" stop-opacity="0.30"/>
      <stop offset="100%" stop-color="#5e6ad2" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{k}" height="{k}" rx="{r:.1f}" fill="url(#shell)"/>
  <rect width="{k}" height="{k}" rx="{r:.1f}" fill="url(#lift)"/>
  <rect x="{st/2:.1f}" y="{st/2:.1f}" width="{k-st:.1f}" height="{k-st:.1f}" rx="{r-st/2:.1f}"
        stroke="rgba(255,255,255,0.17)" stroke-width="{st:.1f}"/>
  <path d="{ds[0]}" stroke="url(#body)" stroke-width="{lw:.1f}" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="{ds[1]}" stroke="url(#body)" stroke-width="{lw:.1f}" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
'''
    open(out, "w", encoding="utf-8").write(svg)


def render_png(out):
    Wp = S * SS
    img = Image.new("RGB", (Wp, Wp), (10, 11, 14))
    d = ImageDraw.Draw(img, "RGBA")
    st = int(0.020 * Wp)
    rad = int(0.215 * Wp)

    # shell: a subtle diagonal gradient, lighter at the top-left
    shell = Image.new("RGB", (Wp, Wp), (10, 11, 14))
    sh = ImageDraw.Draw(shell)
    for y in range(Wp):
        for x in range(0, Wp, 8):
            t = (x / Wp * 0.6 + y / Wp * 0.4)
            c = (int(21 - 11 * t), int(23 - 12 * t), int(29 - 15 * t))
            sh.rectangle([x, y, x + 8, y + 1], fill=c)
    mask = Image.new("L", (Wp, Wp), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, Wp, Wp], radius=rad, fill=255)
    img.paste(shell, (0, 0), mask)

    # lift: a soft indigo glow from the upper-left, so the shell is not flat
    lift = Image.new("RGB", (Wp, Wp), (0, 0, 0))
    ld0 = ImageDraw.Draw(lift, "RGBA")
    for r in range(int(Wp * 0.85), 0, -10):
        a = int(58 * (1 - r / (Wp * 0.85)) ** 2)
        ld0.ellipse([Wp * 0.34 - r, Wp * 0.26 - r, Wp * 0.34 + r, Wp * 0.26 + r],
                    fill=(94, 106, 210, a))
    img = Image.blend(img, Image.composite(lift, img, mask), 0.55)
    d = ImageDraw.Draw(img, "RGBA")

    d.rounded_rectangle([st // 2, st // 2, Wp - st // 2, Wp - st // 2],
                        radius=rad - st // 2, outline=(255, 255, 255, 44), width=st)

    lw = int(W * (1 - 2 * INSET) * Wp)

    # each half goes on its own layer; round caps on all four terminals
    layer = Image.new("L", (Wp, Wp), 0)
    ld = ImageDraw.Draw(layer)
    for pl in paths():
        pts = _map(pl, Wp)
        ld.line(pts, fill=255, width=lw, joint="curve")
        for (x, y) in (pts[0], pts[-1]):
            r = lw / 2
            ld.ellipse([x - r, y - r, x + r, y + r], fill=255)

    # one continuous gradient across the letterform, left to right
    stops = [(0.00, (255, 255, 255)), (0.38, (233, 236, 255)),
             (0.70, (195, 202, 255)), (1.00, (164, 173, 255))]
    body = Image.new("RGB", (Wp, Wp))
    bd = ImageDraw.Draw(body)
    for x in range(Wp):
        t = x / (Wp - 1)
        for i in range(len(stops) - 1):
            a, ca = stops[i]
            b, cb = stops[i + 1]
            if a <= t <= b:
                k2 = (t - a) / (b - a) if b > a else 0
                col = tuple(int(ca[j] + (cb[j] - ca[j]) * k2) for j in range(3))
                break
        else:
            col = stops[-1][1]
        bd.line([x, 0, x, Wp], fill=col)
    img.paste(body, (0, 0), layer)

    img = img.resize((S, S), Image.LANCZOS)
    img.save(out)


if __name__ == "__main__":
    write_svg("mandate-mark.svg")
    render_png("mandate-mark.png")
    print("wrote mandate-mark.svg and mandate-mark.png")
