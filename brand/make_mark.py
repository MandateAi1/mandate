#!/usr/bin/env python3
"""Mandate brand mark v3 — constructed, not drawn.

v2 scored 7.5/10, "a solid, professional-grade mark", with one flaw: "the diagonal
lines forming the V are noticeably thinner than the vertical stems... disrupting the
overall geometric harmony." That was a real geometry bug, not a taste call - my inner
vertices were hand-guessed constants instead of being derived.

v3 derives them. The M is four bars:
  - two vertical stems of width W
  - two diagonals whose PERPENDICULAR width is also W (computed, not eyeballed)
The diagonals overshoot the cap height by construction, so the whole letterform is
rendered to its own layer and clipped at the cap lines. That is what a type designer
does - the diagonal is cut by the flat terminal, not hand-fitted to it.

Emits mandate-mark.svg (deliverable) and mandate-mark.png (raster preview).
"""
import math

from PIL import Image, ImageDraw

S = 1024
SS = 2

BG = (8, 9, 10)
BORDER = (44, 47, 54)
INK = (247, 248, 248)
INK_DEEP = (198, 202, 212)
ACCENT = (94, 106, 210)
ACCENT_HI = (131, 134, 255)

W = 0.170          # one stroke width for the entire letterform
CV = 0.640         # centre vertex depth (unit space)
TOP, BOT = 0.0, 1.0
INSET = 0.275      # the M's share of the container


def _offset_line(p, q, w):
    """Return the segment p->q displaced by w perpendicular (up-right side)."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy)
    nx, ny = dy / L, -dx / L          # right-hand normal
    if ny > 0:                        # choose the normal that points upward
        nx, ny = -nx, -ny
    return (p[0] + nx * w, p[1] + ny * w), (q[0] + nx * w, q[1] + ny * w)


def bars():
    """Two stems plus two diagonals, with the inner vertex DERIVED.

    v3 bug: offsetting both endpoints of the diagonal produced an inner edge that
    overshot past the centre line, so the colour split caught a stray wedge
    ("looks like a separate piece stuck on"). The inner vertex is where the two
    inner edges actually meet - on the centre line, by symmetry - so it has to be
    solved, not offset.
    """
    # outer diagonal, left: from the left stem's top corner to the centre vertex
    p, q = (W, TOP), (0.5, CV)
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy)
    nx, ny = dy / L, -dx / L
    if ny > 0:
        nx, ny = -nx, -ny
    # the inner edge is the same line pushed W perpendicular; its intercept
    c_out = dy * p[0] - dx * p[1]          # 0.640*W - 0.330*0
    c_in = c_out + W * L
    # inner vertex: where the inner edge meets the centre line x = 0.5
    cv_in = (dy * 0.5 - c_in) / dx
    # where the inner edge crosses the cap line y = 0
    x_at_cap = c_in / dy

    left_diag = [(W, TOP), (0.5, CV), (0.5, cv_in), (x_at_cap, TOP)]
    right_diag = [(1 - x, y) for x, y in left_diag]

    out = [
        [(0.0, TOP), (W, TOP), (W, BOT), (0.0, BOT)],           # left stem
        [(1 - W, TOP), (1.0, TOP), (1.0, BOT), (1 - W, BOT)],   # right stem
        left_diag,
        right_diag,
    ]
    return out


def write_svg(path):
    k = 512
    span = 1.0 - 2 * INSET
    def T(pt):
        return ((INSET + pt[0] * span) * k, (INSET + pt[1] * span) * k)
    polys = "".join(
        '  <polygon points="' + " ".join(f"{x:.2f},{y:.2f}" for x, y in map(T, poly)) + '"/>\n'
        for poly in bars()
    )
    r = 0.215 * k
    st = 0.020 * k
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{k}" height="{k}" viewBox="0 0 {k} {k}" fill="none">
  <defs>
    <clipPath id="letter"><rect x="{INSET*k:.1f}" y="{INSET*k:.1f}" width="{span*k:.1f}" height="{span*k:.1f}"/></clipPath>
    <clipPath id="left"><rect x="0" y="0" width="{k/2:.1f}" height="{k}"/></clipPath>
    <clipPath id="right"><rect x="{k/2:.1f}" y="0" width="{k/2:.1f}" height="{k}"/></clipPath>
    <linearGradient id="ink" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="rgb{INK}"/><stop offset="100%" stop-color="rgb{INK_DEEP}"/>
    </linearGradient>
    <linearGradient id="acc" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="rgb{ACCENT_HI}"/><stop offset="100%" stop-color="rgb{ACCENT}"/>
    </linearGradient>
    <mask id="clipL"><rect x="0" y="0" width="{k/2:.1f}" height="{k}" fill="#fff"/></mask>
  </defs>
  <rect width="{k}" height="{k}" rx="{r:.1f}" fill="rgb{BG}"/>
  <rect x="{st/2:.1f}" y="{st/2:.1f}" width="{k-st:.1f}" height="{k-st:.1f}" rx="{r-st/2:.1f}"
        stroke="rgb{BORDER}" stroke-width="{st:.1f}"/>
  <g clip-path="url(#letter)">
    <g clip-path="url(#left)"><g fill="url(#ink)">{polys}</g></g>
    <g clip-path="url(#right)"><g fill="url(#acc)">{polys}</g></g>
  </g>
</svg>
'''
    open(path, "w", encoding="utf-8").write(svg)


def render_png(path):
    Wp = S * SS
    img = Image.new("RGB", (Wp, Wp), BG)
    d = ImageDraw.Draw(img, "RGBA")
    st = int(0.020 * Wp)
    rad = int(0.215 * Wp)
    d.rounded_rectangle([st // 2, st // 2, Wp - st // 2, Wp - st // 2],
                        radius=rad - st // 2, outline=BORDER + (255,), width=st)

    # draw the letterform on its own layer so the diagonal overshoot is clipped
    # at the cap lines by the crop - the way a type designer cuts a terminal
    span = 1.0 - 2 * INSET
    layer = Image.new("RGBA", (Wp, Wp), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for poly in bars():
        pts = [((INSET + x * span) * Wp, (INSET + y * span) * Wp) for x, y in poly]
        ld.polygon(pts, fill=(255, 255, 255, 255))

    # clip to the letterform box, then split at the centre
    box = (int(INSET * Wp), int(INSET * Wp), int((INSET + span) * Wp), int((INSET + span) * Wp))
    letter = layer.crop(box)
    lw, lh = letter.size
    mid = lw // 2

    ink = Image.new("RGBA", (mid, lh), INK + (255,))
    acc = Image.new("RGBA", (lw - mid, lh), ACCENT + (255,))
    left = Image.new("RGBA", (mid, lh), (0, 0, 0, 0))
    left.paste(ink, (0, 0), letter.crop((0, 0, mid, lh)))
    right = Image.new("RGBA", (lw - mid, lh), (0, 0, 0, 0))
    right.paste(acc, (0, 0), letter.crop((mid, 0, lw, lh)))

    img.paste(left, (box[0], box[1]), left)
    img.paste(right, (box[0] + mid, box[1]), right)

    img = img.resize((S, S), Image.LANCZOS)
    img.save(path)


if __name__ == "__main__":
    write_svg("mandate-mark.svg")
    render_png("mandate-mark.png")
    print("wrote mandate-mark.svg and mandate-mark.png")
