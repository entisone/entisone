#!/usr/bin/env python3
"""Generate the social pills and the skills chip grid.

Local SVG instead of shields.io, for the same reason the rest of the art is
local: no third-party server to rate-limit or go down behind a broken-image
icon on the profile. Palette matches banner.svg.

    python scripts/make_badges_svg.py            # writes badges/*.svg + skills-chips.svg
    STATIC=1 python scripts/make_badges_svg.py   # frozen frames

No dependencies — standard library only.
"""

from __future__ import annotations

import os
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
BADGE_DIR = ROOT / "badges"
CHIPS_OUT = ROOT / "skills-chips.svg"

STATIC = os.environ.get("STATIC") == "1"

BG = "#131029"
STROKE_DIM = "#2b2450"
TEXT = "#e2e8f0"
DIM = "#94a3b8"

# 24x24 icon paths, drawn as strokes so one path serves any accent colour.
ICONS = {
    "globe": ("M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z M2 12h20 "
              "M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z"),
    "mail": ("M3 6h18v12H3z M3 7l9 7 9-7"),
    "github": ("M9 19c-4 1.4-4-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 4.5-1.4 "
               "4.5-5a4 4 0 0 0-1.1-2.8 3.7 3.7 0 0 0-.1-2.8s-1.2-.4-3.8 1.4a9.4 "
               "9.4 0 0 0-5 0C7.3 3.7 6.1 4.1 6.1 4.1a3.7 3.7 0 0 0-.1 2.8A4 4 0 "
               "0 0 5 9.7c0 3.6 1.7 4.7 4.5 5-.6.6-.6 1.2-.5 2V20"),
    "linkedin": ("M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z M3 9h4v12H3z "
                 "M9 9h3.8v1.7c.6-1 1.9-2 3.8-2 3.4 0 4.4 2.3 4.4 5.8V21h-4v-5.7"
                 "c0-1.4 0-3.1-1.9-3.1s-2.2 1.5-2.2 3V21H9z"),
}

BADGES = [
    ("portfolio", "globe", "oneentis.dev", "#22d3ee"),
    ("email", "mail", "oneentis@gmail.com", "#34d399"),
    ("github", "github", "@entisone", "#a78bfa"),
    ("linkedin", "linkedin", "in/j-francis-fabia", "#7cc5f0"),
]

SKILLS = [
    ("languages", "#22d3ee",
     ["HTML", "CSS", "JavaScript", "TypeScript", "PHP"]),
    ("frameworks", "#a78bfa",
     ["Vue.js", "Laravel", "Next.js", "Tailwind CSS"]),
    ("tools", "#34d399",
     ["Git", "WordPress", "Dealer CMS", "DealerOn", "SchemaApp", "Ahrefs"]),
    ("focus", "#f0abfc",
     ["On-page SEO", "Performance", "Responsive UI", "CMS customisation",
      "Databases"]),
]

FONT_CSS = ('ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, '
            '"Helvetica Neue", Arial, sans-serif')


def text_width(s: str, size: float) -> float:
    """Rough advance width for a semibold sans string."""
    return len(s) * size * 0.585


def reveal(delay: float, dur: float = 0.45, shift: float = 0.0) -> str:
    """Staggered fade-in that degrades to "just visible".

    The obvious encoding is opacity="0" plus an animation that raises it — but
    then any renderer that doesn't run SMIL leaves the element invisible
    forever. So the group keeps opacity="1" as its base value and the animation
    starts at 0s, holding 0 through the stagger before ramping up. SMIL present:
    a clean staggered entrance with no flash. SMIL absent: everything shows,
    just without motion.
    """
    if STATIC:
        return ""
    total = delay + dur
    if delay <= 0:
        vals, times = "0;1", "0;1"
        shift_vals = f"0 {shift};0 0"
    else:
        k = delay / total
        vals, times = "0;0;1", f"0;{k:.4f};1"
        shift_vals = f"0 {shift};0 {shift};0 0"

    a = (f'<animate attributeName="opacity" values="{vals}" '
         f'keyTimes="{times}" dur="{total:.3f}s" begin="0s" fill="freeze"/>')
    if shift:
        a += (f'<animateTransform attributeName="transform" type="translate" '
              f'values="{shift_vals}" keyTimes="{times}" dur="{total:.3f}s" '
              f'begin="0s" fill="freeze"/>')
    return a


def sheen(begin: float, dur: float = 1.4) -> str:
    """A highlight sweeping across once, then gone. Empty when STATIC."""
    if STATIC:
        return ""
    return (f'<animate attributeName="x1" from="-0.5" to="1.1" begin="{begin}s" '
            f'dur="{dur}s" fill="freeze"/>'
            f'<animate attributeName="x2" from="-0.1" to="1.5" begin="{begin}s" '
            f'dur="{dur}s" fill="freeze"/>')


# ------------------------------------------------------------------ pills ---

def badge(icon: str, label: str, accent: str) -> str:
    h = 36.0
    fs = 13.5
    pad = 13.0
    icon_size = 15.0
    gap = 9.0
    w = pad + icon_size + gap + text_width(label, fs) + pad

    fade = reveal(0.1, 0.5)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.1f} {h:.1f}" role="img" aria-label="{escape(label)}">
  <title>{escape(label)}</title>
  <style>text {{ font-family: {FONT_CSS}; }}</style>
  <defs>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{accent}" stop-opacity="0.9"/>
      <stop offset="1" stop-color="{accent}" stop-opacity="0.35"/>
    </linearGradient>
    <linearGradient id="gloss" x1="-0.5" y1="0" x2="-0.1" y2="0">
      <stop offset="0" stop-color="{accent}" stop-opacity="0"/>
      <stop offset="0.5" stop-color="{accent}" stop-opacity="0.28"/>
      <stop offset="1" stop-color="{accent}" stop-opacity="0"/>
      {sheen(0.5)}
    </linearGradient>
    <filter id="g" x="-40%" y="-80%" width="180%" height="260%">
      <feGaussianBlur stdDeviation="3"/>
    </filter>
    <clipPath id="pill">
      <rect x="1" y="1" width="{w - 2:.1f}" height="{h - 2:.1f}" rx="{(h - 2) / 2:.1f}"/>
    </clipPath>
  </defs>
  <g opacity="1">{fade}
    <rect x="1" y="1" width="{w - 2:.1f}" height="{h - 2:.1f}"
          rx="{(h - 2) / 2:.1f}" fill="{accent}" opacity="0.18"
          filter="url(#g)"/>
    <rect x="1" y="1" width="{w - 2:.1f}" height="{h - 2:.1f}"
          rx="{(h - 2) / 2:.1f}" fill="{BG}" stroke="url(#edge)"
          stroke-width="1.4"/>
    <rect clip-path="url(#pill)" x="1" y="1" width="{w - 2:.1f}"
          height="{h - 2:.1f}" fill="url(#gloss)"/>
    <g transform="translate({pad:.1f} {(h - icon_size) / 2:.1f}) scale({icon_size / 24:.4f})"
       fill="none" stroke="{accent}" stroke-width="2"
       stroke-linecap="round" stroke-linejoin="round">
      <path d="{ICONS[icon]}"/>
    </g>
    <text x="{pad + icon_size + gap:.1f}" y="{h / 2 + fs * 0.36:.1f}"
          font-size="{fs}" font-weight="600"
          fill="{TEXT}">{escape(label)}</text>
  </g>
</svg>
"""


# ------------------------------------------------------------------ chips ---

def chips_svg() -> str:
    W = 1100.0
    pad = 26.0
    label_col = 152.0
    row_h = 52.0
    chip_h = 32.0
    fs = 14.0
    label_fs = 13.0
    chip_pad = 14.0
    chip_gap = 9.0

    H = pad * 2 + row_h * len(SKILLS)

    body: list[str] = []
    grads: list[str] = []
    idx = 0

    for row, (group, accent, items) in enumerate(SKILLS):
        y = pad + row * row_h
        cy = y + (row_h - chip_h) / 2

        body.append(
            f'<text x="{pad:.1f}" y="{cy + chip_h / 2 + label_fs * 0.36:.1f}" '
            f'font-size="{label_fs}" font-weight="700" '
            f'fill="{accent}" letter-spacing="1.4">{escape(group)}</text>')

        x = pad + label_col
        for item in items:
            cw = chip_pad * 2 + text_width(item, fs)
            gid = f"cg{idx}"
            grads.append(
                f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
                f'<stop offset="0" stop-color="{accent}" stop-opacity="0.85"/>'
                f'<stop offset="1" stop-color="{accent}" stop-opacity="0.3"/>'
                f'</linearGradient>')

            anim = reveal(0.15 + idx * 0.045, 0.45, shift=7)

            body.append(
                f'<g opacity="1">{anim}'
                f'<rect x="{x:.1f}" y="{cy:.1f}" width="{cw:.1f}" '
                f'height="{chip_h}" rx="{chip_h / 2}" fill="{BG}" '
                f'stroke="url(#{gid})" stroke-width="1.3"/>'
                f'<text x="{x + cw / 2:.1f}" '
                f'y="{cy + chip_h / 2 + fs * 0.36:.1f}" text-anchor="middle" '
                f'font-size="{fs}" font-weight="500" '
                f'fill="{TEXT}">{escape(item)}</text>'
                f'</g>')

            x += cw + chip_gap
            idx += 1

        if x > W - pad:
            print(f"  ! row {group!r} overflows: needs {x:.0f} of {W:.0f}")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Skills">
  <title>Skills</title>
  <style>text {{ font-family: {FONT_CSS}; }}</style>
  <defs>
    {chr(10).join('    ' + g for g in grads)}
  </defs>
  <rect width="100%" height="100%" rx="12" fill="#0d0a22"/>
  <rect x="0.5" y="0.5" width="{W - 1:.0f}" height="{H - 1:.0f}" rx="12"
        fill="none" stroke="{STROKE_DIM}"/>
{chr(10).join('  ' + b for b in body)}
</svg>
"""


def main() -> int:
    BADGE_DIR.mkdir(exist_ok=True)
    for name, icon, label, accent in BADGES:
        path = BADGE_DIR / f"{name}.svg"
        path.write_text(badge(icon, label, accent), encoding="utf-8")
        print(f"  -> {path.relative_to(ROOT)}")

    CHIPS_OUT.write_text(chips_svg(), encoding="utf-8")
    print(f"  -> {CHIPS_OUT.relative_to(ROOT)}")
    print(f"make_badges_svg: {len(BADGES)} pills + chip grid"
          f"{' (static)' if STATIC else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
