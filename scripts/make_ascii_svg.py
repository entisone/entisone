#!/usr/bin/env python3
"""Convert the prepped photo into a self-typing monochrome ASCII SVG.

The prepped image is downsampled to a ~100x53 character grid and each cell's
brightness picks a glyph off a density ramp. Two choices keep it clean rather
than noisy: one fill color (per-character rainbow is what makes most ASCII
portraits look like static) and high contrast (a washed-out background falls
through to the space glyph, so only the subject prints).

Animation is pure SMIL so GitHub plays it: every row is wrapped in a clip that
wipes left-to-right with a small block cursor riding the edge, staggered top to
bottom. It prints once and freezes — no looping.

    python scripts/make_ascii_svg.py            # writes ascii-portrait.svg
    STATIC=1 python scripts/make_ascii_svg.py   # frozen frame, no animation

If source-prepped.png is missing, a procedural placeholder bust is used so the
README renders. Drop in your own photo and re-run prep_photo.py to replace it.
"""

from __future__ import annotations

import os
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source-prepped.png"
OUT = ROOT / "ascii-portrait.svg"

RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense)
#        ^ leading space clears the background to nothing

COLS = 100
FONT_SIZE = 8.0
CHAR_W = FONT_SIZE * 0.6  # monospace advance; textLength pins it exactly
LINE_H = FONT_SIZE * 1.06
PAD = 14.0

INK = "#c9d1d9"  # one light gray, monochrome on purpose
CURSOR = "#39d353"
BG = "#0d1117"

ROW_DUR = 0.42  # seconds for one row to wipe in
ROW_STAGGER = 0.035  # delay added per row, top to bottom

STATIC = os.environ.get("STATIC") == "1"


def placeholder_bust(w: int = 420, h: int = 394) -> Image.Image:
    """A lit sphere-and-shoulders bust, so the ramp has real shading to chew on."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    gray = np.full((h, w), 255.0)

    # Light comes from the upper left, same as the photo pipeline assumes.
    lx, ly, lz = -0.45, -0.52, 0.72

    cx, cy, rx, ry = w * 0.5, h * 0.36, w * 0.23, h * 0.27
    u, v = (x - cx) / rx, (y - cy) / ry
    head = u * u + v * v <= 1.0
    nz = np.sqrt(np.clip(1.0 - (u * u + v * v), 0, None))
    lit = np.clip(u * lx + v * ly + nz * lz, 0, None)
    gray[head] = np.clip(38 + 205 * lit, 0, 255)[head]

    sx, sy, srx, sry = w * 0.5, h * 1.02, w * 0.46, h * 0.42
    su, sv = (x - sx) / srx, (y - sy) / sry
    shoulders = (su * su + sv * sv <= 1.0) & (y > cy + ry * 0.72)
    snz = np.sqrt(np.clip(1.0 - (su * su + sv * sv), 0, None))
    slit = np.clip(su * lx + sv * ly + snz * lz, 0, None)
    gray[shoulders] = np.clip(52 + 150 * slit, 0, 255)[shoulders]

    return Image.fromarray(gray.astype(np.uint8), mode="L")


def load_source() -> Image.Image:
    if SRC.exists():
        return Image.open(SRC).convert("L")
    print(f"note: {SRC.name} not found — using the placeholder bust.")
    print("      run scripts/prep_photo.py on your photo to replace it.")
    return placeholder_bust()


def to_rows(img: Image.Image) -> list[str]:
    """Downsample to a character grid and map brightness onto the density ramp."""
    # Characters are about twice as tall as wide, so squash the row count to match.
    rows = max(1, round(COLS * img.height / img.width * (CHAR_W / LINE_H)))
    small = np.asarray(img.resize((COLS, rows), Image.LANCZOS), dtype=np.float64)

    # Stretch whatever range the image actually uses across the full ramp.
    lo, hi = small.min(), small.max()
    if hi - lo > 1:
        small = (small - lo) * (255.0 / (hi - lo))

    idx = ((255.0 - small) / 255.0 * (len(RAMP) - 1)).round().astype(int)
    idx = np.clip(idx, 0, len(RAMP) - 1)
    return ["".join(RAMP[i] for i in row).rstrip() for row in idx]


def build_svg(rows: list[str]) -> str:
    grid_w = COLS * CHAR_W
    w = grid_w + PAD * 2
    h = len(rows) * LINE_H + PAD * 2

    defs: list[str] = []
    body: list[str] = []

    for i, line in enumerate(rows):
        if not line:
            continue
        y = PAD + i * LINE_H
        baseline = y + FONT_SIZE * 0.82
        run_w = len(line) * CHAR_W
        begin = round(i * ROW_STAGGER, 3)

        if STATIC:
            body.append(
                f'<text xml:space="preserve" x="{PAD:.2f}" y="{baseline:.2f}" '
                f'textLength="{run_w:.2f}" '
                f'lengthAdjust="spacingAndGlyphs">{escape(line)}</text>'
            )
            continue

        defs.append(
            f'<clipPath id="w{i}">'
            f'<rect x="{PAD:.2f}" y="{y:.2f}" width="0" height="{LINE_H:.2f}">'
            f'<animate attributeName="width" from="0" to="{run_w:.2f}" '
            f'begin="{begin}s" dur="{ROW_DUR}s" fill="freeze"/>'
            f"</rect></clipPath>"
        )
        body.append(
            f'<text xml:space="preserve" x="{PAD:.2f}" y="{baseline:.2f}" '
            f'textLength="{run_w:.2f}" '
            f'lengthAdjust="spacingAndGlyphs" clip-path="url(#w{i})">'
            f"{escape(line)}</text>"
        )
        # The block cursor rides the wipe edge, then blinks out.
        body.append(
            f'<rect class="cur" x="{PAD:.2f}" y="{y + 1:.2f}" '
            f'width="{CHAR_W:.2f}" height="{FONT_SIZE:.2f}" opacity="0">'
            f'<animate attributeName="x" from="{PAD:.2f}" to="{PAD + run_w:.2f}" '
            f'begin="{begin}s" dur="{ROW_DUR}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="1" begin="{begin}s"/>'
            f'<set attributeName="opacity" to="0" begin="{round(begin + ROW_DUR, 3)}s"/>'
            f"</rect>"
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.2f} {h:.2f}" role="img" aria-label="ASCII portrait">
  <title>ASCII portrait</title>
  <defs>
{chr(10).join("    " + d for d in defs)}
  </defs>
  <style>
    text {{ font-family: ui-monospace, "SFMono-Regular", "Cascadia Mono", Menlo, Consolas, monospace;
            font-size: {FONT_SIZE}px; fill: {INK}; white-space: pre; }}
    .cur {{ fill: {CURSOR}; }}
  </style>
  <rect width="100%" height="100%" rx="10" fill="{BG}"/>
{chr(10).join("  " + b for b in body)}
</svg>
"""


def main() -> int:
    rows = to_rows(load_source())
    OUT.write_text(build_svg(rows), encoding="utf-8")
    ink = sum(len(r) for r in rows)
    print(f"make_ascii_svg: {COLS}x{len(rows)} grid, {ink} glyphs"
          f"{' (static)' if STATIC else ''}")
    print(f"  -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
