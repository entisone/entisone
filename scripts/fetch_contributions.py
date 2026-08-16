#!/usr/bin/env python3
"""Scrape the public contribution calendar — no token, no GraphQL.

GitHub serves the calendar as public HTML at
https://github.com/users/<username>/contributions — the same fragment the
profile page itself renders. Fetch it, parse the day cells, and write
data/contributions.json with the raw days plus derived stats.

    python scripts/fetch_contributions.py
    python scripts/fetch_contributions.py someoneelse
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import OrderedDict
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"

USERNAME = os.environ.get("GH_USERNAME", "entisone")
URL = "https://github.com/users/{}/contributions"
HEADERS = {
    "User-Agent": "profile-art/1.0 (+https://github.com/{})",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "text/html",
}
TIMEOUT = 30


def fetch_html(user: str) -> str:
    headers = dict(HEADERS, **{"User-Agent": HEADERS["User-Agent"].format(user)})
    resp = requests.get(URL.format(user), headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def parse_reported_total(html: str) -> int | None:
    """GitHub prints its own headline total. Use it to catch parser drift."""
    soup = BeautifulSoup(html, "html.parser")
    for h2 in soup.select("h2"):
        text = " ".join(h2.get_text(" ", strip=True).split())
        match = re.match(r"^([\d,]+)\s+contributions?\s+in the last year$", text)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def parse_days(html: str) -> list[dict]:
    """Pull (date, count, level) out of the calendar table cells."""
    soup = BeautifulSoup(html, "html.parser")
    days: list[dict] = []

    for cell in soup.select("td.ContributionCalendar-day[data-date]"):
        day = cell.get("data-date")
        if not day:
            continue
        # The count lives in a sibling tooltip keyed by the cell id, and on
        # newer markup also directly on the cell.
        count = cell.get("data-count")
        if count is None:
            tip = soup.select_one(f'tool-tip[for="{cell.get("id")}"]')
            text = tip.get_text(strip=True) if tip else ""
            first = text.split(" ", 1)[0].replace(",", "")
            count = first if first.isdigit() else "0"
        days.append({
            "date": day,
            "count": int(count),
            "level": int(cell.get("data-level") or 0),
        })

    days.sort(key=lambda d: d["date"])
    return days


def derive_stats(days: list[dict]) -> dict:
    """Current streak, longest streak, best day, monthly totals."""
    counts = {d["date"]: d["count"] for d in days}
    total = sum(counts.values())

    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)

    # Walk backwards from today. An empty today doesn't break the streak yet —
    # the day isn't over — but an empty yesterday does.
    current = 0
    cursor = date.today()
    if counts.get(cursor.isoformat(), 0) == 0:
        cursor -= timedelta(days=1)
    while counts.get(cursor.isoformat(), 0) > 0:
        current += 1
        cursor -= timedelta(days=1)

    best = max(days, key=lambda d: d["count"]) if days else {"date": None, "count": 0}

    months: "OrderedDict[str, int]" = OrderedDict()
    for d in days:
        months[d["date"][:7]] = months.get(d["date"][:7], 0) + d["count"]

    active = sum(1 for d in days if d["count"] > 0)
    return {
        "total": total,
        "days_tracked": len(days),
        "active_days": active,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "daily_average": round(total / len(days), 2) if days else 0,
        "months": months,
    }


def main() -> int:
    user = sys.argv[1] if len(sys.argv) > 1 else USERNAME
    print(f"fetch_contributions: {user}")

    html = fetch_html(user)
    days = parse_days(html)
    if not days:
        print("error: parsed 0 day cells — GitHub's markup may have changed.",
              file=sys.stderr)
        return 1

    stats = derive_stats(days)

    # Reconcile against GitHub's own headline. A mismatch means the day cells
    # stopped parsing the way we expect, and the heatmap would quietly lie.
    reported = parse_reported_total(html)
    if reported is not None and reported != stats["total"]:
        print(f"error: parsed {stats['total']} contributions but GitHub reports "
              f"{reported} — the calendar markup has drifted.", file=sys.stderr)
        return 1

    payload = {
        "username": user,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "reported_total": reported,
        "stats": stats,
        "days": days,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    s = payload["stats"]
    print(f"  {s['total']} contributions over {s['days_tracked']} days "
          f"({days[0]['date']} -> {days[-1]['date']})")
    print(f"  streak: {s['current_streak']} current / {s['longest_streak']} longest")
    print(f"  -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
