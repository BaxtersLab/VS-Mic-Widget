#!/usr/bin/env python3
"""Generate the VS Mic Widget icon: a microphone on the house ground.

The app dictates speech into whichever window you target, so a microphone is
the shape it should carry. StreamCast Tuner deliberately does NOT use one --
headphones there -- so the two stay distinguishable at tray size, where a small
mic and a small anything-else-vertical look alike.

Ground is #010101, measured from soc-master-widget, so this reads as one set
with the lettermarks beside it. Every size is drawn natively: stroke widths are
fractions of the canvas, because downscaling one master leaves a grey smudge at
16px -- legible where you inspect it, invisible where it is used.

Usage:  python3 packaging/generate_icon.py [--outdir DIR] [--color '#FFD23F']
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

GROUND = (1, 1, 1, 255)
COLOR = (255, 210, 63, 255)       # amber: distinct from hot-rod-tuner's orange
SS = 8
SIZES = [16, 24, 32, 48, 64, 128, 256, 512]


def draw_icon(size: int, color=COLOR) -> Image.Image:
    s = size * SS
    img = Image.new("RGBA", (s, s), GROUND)
    d = ImageDraw.Draw(img)
    cx = s / 2
    cap_w, cap_h, cap_top = s * 0.20, s * 0.34, s * 0.16
    d.rounded_rectangle([cx - cap_w/2, cap_top, cx + cap_w/2, cap_top + cap_h],
                        radius=cap_w/2, fill=color)
    lw = max(1, int(s * 0.055))
    r = s * 0.20
    cy = cap_top + cap_h * 0.72
    d.arc([cx - r, cy - r, cx + r, cy + r], start=0, end=180, fill=color, width=lw)
    d.line([cx, cy + r, cx, s * 0.80], fill=color, width=lw)
    foot = s * 0.15
    d.line([cx - foot, s * 0.80, cx + foot, s * 0.80], fill=color, width=lw)
    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="packaging/icons")
    ap.add_argument("--color", default=None)
    a = ap.parse_args()
    color = COLOR
    if a.color:
        c = a.color.lstrip("#")
        color = (int(c[0:2],16), int(c[2:4],16), int(c[4:6],16), 255)
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    for n in SIZES:
        p = out / f"vs-mic-widget_{n}x{n}.png"
        draw_icon(n, color).save(p, optimize=True)
        assert Image.open(p).size == (n, n), f"{p} is not {n}x{n}"
    print(f"  wrote and verified {len(SIZES)} sizes to {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
