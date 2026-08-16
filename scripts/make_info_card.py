#!/usr/bin/env python3
"""Hand-author the neofetch-style info card SVG.

This is the panel that sits next to the ASCII portrait: a title bar, then
colored key/value rows. Keep the *story* here — the contribution graph already
covers the GitHub numbers, so this card is for what the numbers can't tell.

Each line fades and slides in on a short stagger, so the panel looks like it's
printing beside the portrait. It plays once and freezes.

    python scripts/make_info_card.py            # writes info-card.svg
    STATIC=1 python scripts/make_info_card.py   # frozen frame for Quick Look

Everything you'd want to change lives in CONFIG below.
"""

from __future__ import annotations

import os
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "info-card.svg"

# ---------------------------------------------------------------- edit me ---
CONFIG = {
    "user": "entisone",
    "host": "github",
    "rows": [
        ("Name", "J'Francis"),
        ("Role", "Web Developer"),
        ("Now", "Makerspace Innovhub Inc."),
        ("Stack", "TypeScript · Vue · NestJS · Solidity"),
        ("Tools", "Node · Vite · Docker · Hardhat"),
        ("Web", "oneentis.dev"),
        ("Shell", "building things that ship"),
        ("Uptime", "on GitHub since Nov 2017"),
    ],
}
# -----------------------------------------------------------------------------

W, H = 620.0, 440.0
PAD = 26.0
FS = 15.0
LINE_H = 27.0
KEY_COL = 108.0  # x offset where values start

BG = "#0d1117"
BORDER = "#21262d"
KEY = "#39d353"
VAL = "#c9d1d9"
DIM = "#7d8590"
ACCENT = "#58a6ff"

FADE_DUR = 0.45
STAGGER = 0.09
START = 0.25  # let the portrait get a head start

# The neofetch color strip along the bottom.
SWATCHES = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0",
            "#58a6ff", "#c9d1d9"]

STATIC = os.environ.get("STATIC") == "1"


def anim(index: int) -> str:
    """Fade + slide-in for the nth line. Empty string in STATIC mode."""
    if STATIC:
        return ""
    begin = round(START + index * STAGGER, 3)
    return (
        f'<animate attributeName="opacity" from="0" to="1" '
        f'begin="{begin}s" dur="{FADE_DUR}s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" '
        f'from="-10 0" to="0 0" begin="{begin}s" dur="{FADE_DUR}s" fill="freeze"/>'
    )


def line(index: int, *content: str) -> str:
    opacity = "1" if STATIC else "0"
    return f'<g opacity="{opacity}">{anim(index)}{"".join(content)}</g>'


def build_svg() -> str:
    user, host = CONFIG["user"], CONFIG["host"]
    rows = CONFIG["rows"]

    y = PAD + FS
    out: list[str] = []
    i = 0

    # Title bar: user@host, the neofetch header.
    out.append(line(
        i,
        f'<text x="{PAD}" y="{y}" class="k b">{escape(user)}</text>',
        f'<text x="{PAD + len(user) * FS * 0.6:.1f}" y="{y}" class="d b">@</text>',
        f'<text x="{PAD + (len(user) + 1) * FS * 0.6:.1f}" y="{y}" class="a b">'
        f'{escape(host)}</text>',
    ))
    i += 1
    y += LINE_H * 0.72

    out.append(line(i, f'<line x1="{PAD}" y1="{y}" x2="{W - PAD}" y2="{y}" '
                       f'stroke="{BORDER}" stroke-width="1"/>'))
    i += 1
    y += LINE_H * 0.95

    for key, value in rows:
        out.append(line(
            i,
            f'<text x="{PAD}" y="{y}" class="k">{escape(key)}</text>',
            f'<text x="{PAD + KEY_COL - 12:.1f}" y="{y}" class="d">:</text>',
            f'<text x="{PAD + KEY_COL:.1f}" y="{y}" class="v">{escape(value)}</text>',
        ))
        i += 1
        y += LINE_H

    # Color strip, bottom-left, same as neofetch signs off with.
    y = H - PAD - 12
    sw, gap = 26.0, 6.0
    swatches = "".join(
        f'<rect x="{PAD + n * (sw + gap):.1f}" y="{y}" width="{sw}" height="12" '
        f'rx="3" fill="{c}"/>'
        for n, c in enumerate(SWATCHES)
    )
    out.append(line(i, swatches))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="{escape(user)}@{escape(host)} info card">
  <title>{escape(user)}@{escape(host)}</title>
  <style>
    text {{ font-family: ui-monospace, "SFMono-Regular", "Cascadia Mono", Menlo, Consolas, monospace;
            font-size: {FS}px; }}
    .k {{ fill: {KEY}; }}
    .v {{ fill: {VAL}; }}
    .d {{ fill: {DIM}; }}
    .a {{ fill: {ACCENT}; }}
    .b {{ font-weight: 700; }}
  </style>
  <rect width="100%" height="100%" rx="10" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{W - 1:.0f}" height="{H - 1:.0f}" rx="10"
        fill="none" stroke="{BORDER}"/>
{chr(10).join("  " + s for s in out)}
</svg>
"""


def main() -> int:
    OUT.write_text(build_svg(), encoding="utf-8")
    print(f"make_info_card: {len(CONFIG['rows'])} rows"
          f"{' (static)' if STATIC else ''}")
    print(f"  -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
