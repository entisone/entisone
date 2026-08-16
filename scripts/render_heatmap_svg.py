#!/usr/bin/env python3
"""Render data/contributions.json as an animated 53-week heatmap SVG.

The classic 53x7 calendar of rounded boxes, revealed once with a diagonal
line-after-line slide-down (CSS keyframes that play on load, then freeze — no
looping glow), plus a Less->More legend and a stats footer.

    python scripts/render_heatmap_svg.py            # writes contrib-heatmap.svg
    STATIC=1 python scripts/render_heatmap_svg.py   # frozen frame
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

PALETTE = ["#161b22", "#0e4429", "#006d32",
           "#26a641", "#39d353", "#69f0a0"]
#          none -> brightest (level 5 is a neon top end)

CELL = 12.0
GAP = 3.0
PITCH = CELL + GAP
RADIUS = 2.5
WEEKS = 53

PAD = 20.0
GUTTER = 30.0  # left column for Mon/Wed/Fri
MONTH_H = 18.0
LEGEND_H = 26.0
FOOTER_H = 24.0

BG = "#0d1117"
BORDER = "#21262d"
TEXT = "#c9d1d9"
DIM = "#7d8590"
ACCENT = "#39d353"
FS = 11.0

CELL_DUR = 0.5
DIAG_STAGGER = 0.022  # delay per diagonal, so it sweeps down-and-right
START = 0.15

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

STATIC = os.environ.get("STATIC") == "1"


def load() -> dict:
    if not SRC.exists():
        print(f"error: {SRC.relative_to(ROOT)} missing — run "
              "scripts/fetch_contributions.py first.", file=sys.stderr)
        raise SystemExit(1)
    return json.loads(SRC.read_text(encoding="utf-8"))


def sunday_index(d: date) -> int:
    """Weekday with Sunday = 0, matching GitHub's calendar rows."""
    return (d.weekday() + 1) % 7


def place(days: list[dict]) -> tuple[dict[tuple[int, int], dict], date]:
    """Map each day onto (week, weekday) cells anchored to the first Sunday."""
    first = date.fromisoformat(days[0]["date"])
    origin = first - timedelta(days=sunday_index(first))

    grid: dict[tuple[int, int], dict] = {}
    for entry in days:
        d = date.fromisoformat(entry["date"])
        week = (d - origin).days // 7
        if 0 <= week < WEEKS:
            grid[(week, sunday_index(d))] = entry
    return grid, origin


def level_of(entry: dict, hot: int) -> int:
    """GitHub gives 0-4; promote the standout days to the neon level 5."""
    level = min(4, max(0, entry.get("level", 0)))
    if level == 4 and hot and entry["count"] >= hot:
        return 5
    return level


def month_labels(origin: date, grid: dict) -> list[tuple[float, str]]:
    """One label per month, at the first week that month occupies."""
    labels: list[tuple[float, str]] = []
    seen: set[tuple[int, int]] = set()
    for week in range(WEEKS):
        start = origin + timedelta(days=week * 7)
        key = (start.year, start.month)
        if key in seen:
            continue
        # Only label a month once it actually owns most of a column.
        if start.day > 7 and labels:
            continue
        seen.add(key)
        labels.append((week * PITCH, MONTHS[start.month - 1]))
    return labels


def build_svg(payload: dict) -> str:
    days = payload["days"]
    stats = payload["stats"]
    grid, origin = place(days)

    counts = sorted((d["count"] for d in days if d["count"] > 0), reverse=True)
    hot = counts[max(0, len(counts) // 20)] if counts else 0

    grid_w = WEEKS * PITCH - GAP
    grid_h = 7 * PITCH - GAP
    grid_x = PAD + GUTTER
    grid_y = PAD + MONTH_H

    w = grid_x + grid_w + PAD
    h = grid_y + grid_h + LEGEND_H + FOOTER_H + PAD

    parts: list[str] = []

    for x, label in month_labels(origin, grid):
        parts.append(f'<text x="{grid_x + x:.1f}" y="{PAD + FS:.1f}" '
                     f'class="dim">{label}</text>')

    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = grid_y + row * PITCH + CELL * 0.82
        parts.append(f'<text x="{PAD:.1f}" y="{y:.1f}" class="dim">{label}</text>')

    max_diag = 0
    for (week, day), entry in sorted(grid.items()):
        x = grid_x + week * PITCH
        y = grid_y + day * PITCH
        lvl = level_of(entry, hot)
        diag = week + day
        max_diag = max(max_diag, diag)
        cls = "cell" if STATIC else f"cell d{diag}"
        plural = "" if entry["count"] == 1 else "s"
        parts.append(
            f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{CELL}" '
            f'height="{CELL}" rx="{RADIUS}" fill="{PALETTE[lvl]}">'
            f'<title>{entry["count"]} contribution{plural} on {entry["date"]}</title>'
            f"</rect>"
        )

    # Legend, bottom right of the grid.
    legend_y = grid_y + grid_h + LEGEND_H * 0.55
    legend_w = 5 * (CELL + 4) - 4
    legend_x = grid_x + grid_w - legend_w
    parts.append(f'<text x="{legend_x - 8:.1f}" y="{legend_y + CELL * 0.82:.1f}" '
                 f'class="dim" text-anchor="end">Less</text>')
    for n, color in enumerate(PALETTE[:5]):
        parts.append(f'<rect class="c" x="{legend_x + n * (CELL + 4):.1f}" '
                     f'y="{legend_y:.1f}" width="{CELL}" height="{CELL}" '
                     f'rx="{RADIUS}" fill="{color}"/>')
    parts.append(f'<text x="{legend_x + legend_w + 8:.1f}" '
                 f'y="{legend_y + CELL * 0.82:.1f}" class="dim">More</text>')

    # Footer stats.
    total = f"{stats['total']:,}"
    footer_y = grid_y + grid_h + LEGEND_H + FOOTER_H * 0.72
    parts.append(
        f'<text x="{PAD:.1f}" y="{footer_y:.1f}" class="txt">'
        f'<tspan class="hot">{total}</tspan> contributions in the last year'
        f'</text>'
    )
    parts.append(
        f'<text x="{grid_x + grid_w:.1f}" y="{footer_y:.1f}" class="dim" '
        f'text-anchor="end">'
        f'current streak {stats["current_streak"]}d · '
        f'longest {stats["longest_streak"]}d · '
        f'best {stats["best_day"]["count"]} on {stats["best_day"]["date"]}'
        f'</text>'
    )

    delays = "" if STATIC else "\n".join(
        f"    .d{n} {{ animation-delay: {START + n * DIAG_STAGGER:.3f}s; }}"
        for n in range(max_diag + 1)
    )
    motion = "" if STATIC else f"""
    @keyframes pop {{
      from {{ opacity: 0; transform: translateY(-7px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}
    rect.cell {{ animation: pop {CELL_DUR}s ease-out 1 both; }}
{delays}"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="{total} contributions in the last year">
  <title>{payload['username']} — {total} contributions in the last year</title>
  <style>
    text {{ font-family: ui-monospace, "SFMono-Regular", "Cascadia Mono", Menlo, Consolas, monospace;
            font-size: {FS}px; }}
    .dim {{ fill: {DIM}; }}
    .txt {{ fill: {TEXT}; }}
    .hot {{ fill: {ACCENT}; font-weight: 700; }}
{motion}
  </style>
  <rect width="100%" height="100%" rx="10" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{w - 1:.0f}" height="{h - 1:.0f}" rx="10"
        fill="none" stroke="{BORDER}"/>
{chr(10).join("  " + p for p in parts)}
</svg>
"""


def main() -> int:
    payload = load()
    OUT.write_text(build_svg(payload), encoding="utf-8")
    print(f"render_heatmap_svg: {payload['stats']['total']} contributions, "
          f"{len(payload['days'])} days{' (static)' if STATIC else ''}")
    print(f"  -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
