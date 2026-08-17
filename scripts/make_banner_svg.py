#!/usr/bin/env python3
"""Hand-author the neon signature banner SVG.

A dark starfield panel wrapped in a glowing hand-drawn-looking border, with the
name in a teal-to-violet gradient, corner brackets and a couple of lightning
zigzags. Same rules as the rest of the art: everything self-contained, all the
motion inside the file, because GitHub runs SVG animation but strips scripts.

    python scripts/make_banner_svg.py            # writes banner.svg
    STATIC=1 python scripts/make_banner_svg.py   # frozen frame, no animation

Everything worth changing lives in CONFIG.
"""

from __future__ import annotations

import math
import os
import random
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "banner.svg"

# ---------------------------------------------------------------- edit me ---
CONFIG = {
    "label": "ENTISONE",
    "name": "J'Francis",
    # oneentis.dev calls this "Web Developer"; the banner mockup said
    # "FULL-STACK DEVELOPER · BUILDER". Pick whichever you'd rather lead with.
    "tagline": "FULL-STACK DEVELOPER  ·  BUILDER",
}
# -----------------------------------------------------------------------------

W, H = 1100.0, 370.0

# Border wobble is deterministic so the file only changes when you mean it to.
SEED = 20260817

BG = "#0a0a12"
PANEL_TOP = "#1b1440"
PANEL_BOT = "#0d0a22"
BRACKET = "#34d399"
LABEL = "#34d399"
TAGLINE = "#cbd5e1"

GLOW_A = "#22d3ee"  # cyan, top-left of the border gradient
GLOW_B = "#a78bfa"  # violet, bottom-right

# Horizontal gradient across the name, sampled off the reference.
NAME_STOPS = [
    (0.00, "#45d6c0"), (0.18, "#7cc5f0"), (0.40, "#a78bfa"),
    (0.58, "#9b8afb"), (0.78, "#6ee7d5"), (1.00, "#34d399"),
]

PANEL_INSET = 34.0   # panel edge, in from the canvas
BORDER_INSET = 18.0  # wobbly neon border, in from the canvas
BRACKET_INSET = 22.0  # brackets, in from the panel edge
BRACKET_LEN = 34.0
PANEL_RADIUS = 18.0

STAR_COUNT = 46

# Keep the neon breathing after the entrance. Set False for a dead-still frame.
LOOP_GLOW = True

STATIC = os.environ.get("STATIC") == "1"


# --------------------------------------------------------------- geometry ---

def rounded_rect_walk(x: float, y: float, w: float, h: float, r: float,
                      n: int) -> list[tuple[float, float, float, float]]:
    """Sample a rounded rect by arc length -> [(px, py, nx, ny), ...].

    The normal comes back with each point so the wobble can push outward.
    """
    sw, sh = w - 2 * r, h - 2 * r
    arc = math.pi * r / 2
    # top, TR arc, right, BR arc, bottom, BL arc, left, TL arc
    segs = [sw, arc, sh, arc, sw, arc, sh, arc]
    total = sum(segs)

    out: list[tuple[float, float, float, float]] = []
    for i in range(n):
        s = total * i / n
        for idx, seg_len in enumerate(segs):
            if s <= seg_len or idx == len(segs) - 1:
                break
            s -= seg_len
        t = s / seg_len if seg_len else 0.0

        if idx == 0:      # top edge, left -> right
            out.append((x + r + sw * t, y, 0.0, -1.0))
        elif idx == 2:    # right edge, top -> bottom
            out.append((x + w, y + r + sh * t, 1.0, 0.0))
        elif idx == 4:    # bottom edge, right -> left
            out.append((x + r + sw * (1 - t), y + h, 0.0, 1.0))
        elif idx == 6:    # left edge, bottom -> top
            out.append((x, y + r + sh * (1 - t), -1.0, 0.0))
        else:             # one of the four corner arcs
            corner = {1: (x + w - r, y + r, -math.pi / 2),
                      3: (x + w - r, y + h - r, 0.0),
                      5: (x + r, y + h - r, math.pi / 2),
                      7: (x + r, y + r, math.pi)}[idx]
            cx, cy, a0 = corner
            a = a0 + (math.pi / 2) * t
            nx, ny = math.cos(a), math.sin(a)
            out.append((cx + r * nx, cy + r * ny, nx, ny))
    return out


def wobble_path(x: float, y: float, w: float, h: float, r: float,
                samples: int = 260) -> str:
    """A closed, smooth, irregular outline — the hand-drawn neon frame.

    Amplitude is a sum of sines at integer frequencies, so the noise wraps
    seamlessly where the path closes instead of leaving a seam.
    """
    rng = random.Random(SEED)
    # (frequency, amplitude) — a few slow undulations plus fine jitter.
    waves = [(3, 1.9), (5, 1.5), (8, 1.4), (13, 1.2), (21, 1.0), (34, 0.8),
             (55, 0.55), (89, 0.35)]
    phases = [rng.uniform(0, math.tau) for _ in waves]

    pts: list[tuple[float, float]] = []
    for i, (px, py, nx, ny) in enumerate(rounded_rect_walk(x, y, w, h, r, samples)):
        t = i / samples
        d = sum(a * math.sin(math.tau * f * t + ph)
                for (f, a), ph in zip(waves, phases))
        pts.append((px + nx * d, py + ny * d))

    return catmull_rom_closed(pts)


def catmull_rom_closed(pts: list[tuple[float, float]]) -> str:
    """Closed Catmull-Rom through the points, emitted as cubic beziers."""
    n = len(pts)
    d = [f"M {pts[0][0]:.2f} {pts[0][1]:.2f}"]
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C {c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} "
                 f"{p2[0]:.2f} {p2[1]:.2f}")
    d.append("Z")
    return " ".join(d)


def lightning(x: float, y: float, height: float, width: float,
              zigs: int = 4) -> str:
    """A thin vertical zigzag, like the bolts flanking the reference."""
    step = height / zigs
    pts = [(x, y)]
    for i in range(zigs):
        pts.append((x + (width if i % 2 == 0 else -width), y + step * (i + 0.5)))
    pts.append((x, y + height))
    return "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)


def stars() -> str:
    """Scattered dots inside the panel, some of them twinkling."""
    rng = random.Random(SEED + 1)
    x0, y0 = PANEL_INSET + 8, PANEL_INSET + 8
    x1, y1 = W - PANEL_INSET - 8, H - PANEL_INSET - 8

    out = []
    for i in range(STAR_COUNT):
        cx = rng.uniform(x0, x1)
        cy = rng.uniform(y0, y1)
        # Keep the middle clear so stars don't sit behind the name.
        if abs(cx - W / 2) < 300 and abs(cy - H / 2) < 70:
            continue
        r = rng.uniform(0.7, 1.9)
        base = rng.uniform(0.25, 0.9)
        twinkle = ""
        if not STATIC and rng.random() < 0.55:
            dur = rng.uniform(2.2, 4.8)
            twinkle = (
                f'<animate attributeName="opacity" '
                f'values="{base:.2f};{min(1.0, base + 0.45):.2f};{base:.2f}" '
                f'dur="{dur:.2f}s" begin="{rng.uniform(0, 3):.2f}s" '
                f'repeatCount="indefinite"/>'
            )
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" '
                   f'fill="#e9d5ff" opacity="{base:.2f}">{twinkle}</circle>')
    return "\n    ".join(out)


# ------------------------------------------------------------- animation ----

def enter(begin: float, dur: float = 0.7, shift: float = 0.0,
          extra: str = "") -> str:
    """Open a group that fades (and optionally slides) in, then freezes.

    The group always opens with opacity="1" as its base value. Encoding the
    start state as opacity="0" and relying on animation to raise it would leave
    the banner blank forever in any client that doesn't run SMIL — reduced-motion
    setups, some in-app browsers, static thumbnailers. Instead the animation
    begins at 0s and holds 0 through the stagger before fading up: identical
    result where animation works, still legible where it doesn't.
    """
    if STATIC:
        return f'<g opacity="1">{extra}'
    total = round(begin + dur, 3)
    if begin <= 0:
        vals, times = "0;1", "0;1"
        shift_vals = f"0 {shift};0 0"
    else:
        k = begin / total
        vals, times = "0;0;1", f"0;{k:.4f};1"
        shift_vals = f"0 {shift};0 {shift};0 0"
    a = (f'<animate attributeName="opacity" values="{vals}" keyTimes="{times}" '
         f'dur="{total}s" begin="0s" fill="freeze"/>')
    if shift:
        a += (f'<animateTransform attributeName="transform" type="translate" '
              f'values="{shift_vals}" keyTimes="{times}" dur="{total}s" '
              f'begin="0s" fill="freeze"/>')
    return f'<g opacity="1">{extra}{a}'


def build_svg() -> str:
    label = CONFIG["label"]
    name = CONFIG["name"]
    tagline = CONFIG["tagline"]

    border = wobble_path(BORDER_INSET, BORDER_INSET,
                         W - 2 * BORDER_INSET, H - 2 * BORDER_INSET, 30.0)

    px0, py0 = PANEL_INSET, PANEL_INSET
    pw, ph = W - 2 * PANEL_INSET, H - 2 * PANEL_INSET

    # Corner brackets, inset from the panel.
    bx0, by0 = px0 + BRACKET_INSET, py0 + BRACKET_INSET
    bx1, by1 = px0 + pw - BRACKET_INSET, py0 + ph - BRACKET_INSET
    L = BRACKET_LEN
    brackets = [
        f"M {bx0} {by0 + L} L {bx0} {by0} L {bx0 + L} {by0}",
        f"M {bx1 - L} {by0} L {bx1} {by0} L {bx1} {by0 + L}",
        f"M {bx0} {by1 - L} L {bx0} {by1} L {bx0 + L} {by1}",
        f"M {bx1 - L} {by1} L {bx1} {by1} L {bx1} {by1 - L}",
    ]

    name_stops = "".join(
        f'<stop offset="{o}" stop-color="{c}"/>' for o, c in NAME_STOPS)

    cx = W / 2
    glow_pulse = ""
    if LOOP_GLOW and not STATIC:
        glow_pulse = (
            '<animate attributeName="opacity" values="0.55;0.95;0.55" '
            'dur="4.5s" begin="1.6s" repeatCount="indefinite"/>')

    # Shimmer: a highlight sweeping once across the name after it lands.
    shimmer = "" if STATIC else (
        '<animate attributeName="x1" from="-0.6" to="1.0" begin="1.5s" '
        'dur="1.6s" fill="freeze"/>'
        '<animate attributeName="x2" from="-0.2" to="1.6" begin="1.5s" '
        'dur="1.6s" fill="freeze"/>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="{escape(name)} — {escape(tagline)}">
  <title>{escape(name)} — {escape(tagline)}</title>
  <defs>
    <linearGradient id="panel" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0" stop-color="{PANEL_TOP}"/>
      <stop offset="1" stop-color="{PANEL_BOT}"/>
    </linearGradient>
    <linearGradient id="neon" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{GLOW_A}"/>
      <stop offset="0.5" stop-color="#8b7bf0"/>
      <stop offset="1" stop-color="{GLOW_B}"/>
    </linearGradient>
    <linearGradient id="nameFill" x1="0" y1="0" x2="1" y2="0">
      {name_stops}
    </linearGradient>
    <linearGradient id="sheen" x1="-0.6" y1="0" x2="-0.2" y2="0">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="0.5" stop-color="#ffffff" stop-opacity="0.75"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
      {shimmer}
    </linearGradient>
    <!-- userSpaceOnUse: the rule is a horizontal line, so its object bounding
         box has zero height and an objectBoundingBox gradient degenerates. -->
    <linearGradient id="rule" gradientUnits="userSpaceOnUse"
                    x1="{cx - 211}" y1="0" x2="{cx + 211}" y2="0">
      <stop offset="0" stop-color="{GLOW_A}" stop-opacity="0.25"/>
      <stop offset="0.5" stop-color="#a78bfa"/>
      <stop offset="1" stop-color="{GLOW_A}" stop-opacity="0.25"/>
    </linearGradient>

    <filter id="bigGlow" x="-25%" y="-60%" width="150%" height="220%">
      <feGaussianBlur stdDeviation="9"/>
    </filter>
    <filter id="midGlow" x="-25%" y="-60%" width="150%" height="220%">
      <feGaussianBlur stdDeviation="3.4"/>
    </filter>
    <filter id="textGlow" x="-30%" y="-80%" width="160%" height="260%">
      <feGaussianBlur stdDeviation="7"/>
    </filter>

    <clipPath id="panelClip">
      <rect x="{px0}" y="{py0}" width="{pw}" height="{ph}" rx="{PANEL_RADIUS}"/>
    </clipPath>
  </defs>

  <style>
    .ui {{ font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI",
           Roboto, "Helvetica Neue", Arial, sans-serif; }}
    .name {{ font-size: 104px; font-weight: 700; letter-spacing: 1px; }}
    .label {{ font-size: 17px; font-weight: 600; letter-spacing: 7px; }}
    .tag {{ font-size: 19px; font-weight: 600; letter-spacing: 5.5px; }}
  </style>

  <rect width="100%" height="100%" fill="{BG}"/>

  <!-- panel + its contents -->
  <rect x="{px0}" y="{py0}" width="{pw}" height="{ph}" rx="{PANEL_RADIUS}"
        fill="url(#panel)"/>
  <g clip-path="url(#panelClip)">
    <path d="{lightning(px0 + 118, py0 + 6, ph - 12, 26)}" fill="none"
          stroke="#3b4b8f" stroke-width="2.4" stroke-linecap="round"
          opacity="0.55"/>
    <path d="{lightning(px0 + pw - 118, py0 + 6, ph - 12, 26)}" fill="none"
          stroke="#7c3aed" stroke-width="2.6" stroke-linecap="round"
          opacity="0.75"/>
    {stars()}
  </g>

  <!-- neon border: wide blur, tight blur, then the crisp stroke -->
  {enter(0.0, 0.9)}
    <g opacity="0.75">{glow_pulse}
      <path d="{border}" fill="none" stroke="url(#neon)" stroke-width="11"
            filter="url(#bigGlow)"/>
    </g>
    <path d="{border}" fill="none" stroke="url(#neon)" stroke-width="4.5"
          filter="url(#midGlow)" opacity="0.9"/>
    <path d="{border}" fill="none" stroke="url(#neon)" stroke-width="1.9"
          stroke-linejoin="round"/>
  </g>

  <!-- corner brackets -->
  {enter(0.45, 0.6, extra='')}<g fill="none" stroke="{BRACKET}" stroke-width="2.6"
     stroke-linecap="square">
    {chr(10).join(f'    <path d="{d}"/>' for d in brackets)}
  </g></g>

  <!-- label -->
  {enter(0.7, 0.6, shift=8)}
    <text class="ui label" x="{cx}" y="{H * 0.34:.1f}" fill="{LABEL}"
          text-anchor="middle">&#8249;&#160;{escape(label)}&#160;&#8250;</text>
  </g>

  <!-- name: glow copy behind, gradient fill, then the sheen sweep -->
  {enter(0.95, 0.8, shift=14)}
    <text class="ui name" x="{cx}" y="{H * 0.585:.1f}" fill="url(#nameFill)"
          text-anchor="middle" filter="url(#textGlow)" opacity="0.75"
          >{escape(name)}</text>
    <text class="ui name" x="{cx}" y="{H * 0.585:.1f}" fill="url(#nameFill)"
          text-anchor="middle">{escape(name)}</text>
    <text class="ui name" x="{cx}" y="{H * 0.585:.1f}" fill="url(#sheen)"
          text-anchor="middle">{escape(name)}</text>
  </g>

  <!-- dashed rule -->
  {enter(1.25, 0.5)}
    <line x1="{cx - 211}" y1="{H * 0.658:.1f}" x2="{cx + 211}"
          y2="{H * 0.658:.1f}" stroke="url(#rule)" stroke-width="3.2"
          stroke-dasharray="12 9" stroke-linecap="round"/>
  </g>

  <!-- tagline -->
  {enter(1.45, 0.6, shift=8)}
    <text class="ui tag" x="{cx}" y="{H * 0.781:.1f}" fill="{TAGLINE}"
          text-anchor="middle">{escape(tagline)}</text>
  </g>
</svg>
"""


def main() -> int:
    OUT.write_text(build_svg(), encoding="utf-8")
    print(f"make_banner_svg: {W:.0f}x{H:.0f}"
          f"{' (static)' if STATIC else ''}")
    print(f"  -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
