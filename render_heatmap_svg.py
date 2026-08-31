#!/usr/bin/env python3
"""
Render data/contributions.json as an animated SVG heatmap.

Usage:
    python scripts/render_heatmap_svg.py

Output:
    contrib-heatmap.svg
"""
import json
import html
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

PALETTE = [
    "#161b22",  # level 0
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
    "#69f0a0",  # level 5
]

CELL = 13
GAP = 4
STEP = CELL + GAP
LEFT = 28
TOP = 72
WEEKS = 53
DAYS = 7
WIDTH = LEFT + WEEKS * STEP + 28
HEIGHT = TOP + DAYS * STEP + 90


def load_days():
    obj = json.loads(DATA.read_text(encoding="utf-8"))
    by_date = {d["date"]: d for d in obj["days"]}
    return obj, by_date


def main():
    obj, by_date = load_days()

    # Build exactly 53 columns ending on the latest Sunday-containing week.
    latest = date.fromisoformat(max(by_date))
    end = latest + timedelta(days=(6 - latest.weekday()) % 7)
    start = end - timedelta(days=7 * WEEKS - 1)

    cells = []
    for week in range(WEEKS):
        for dow in range(DAYS):
            day = start + timedelta(days=week * 7 + dow)
            item = by_date.get(day.isoformat(), {"count": 0, "level": 0})
            level = max(0, min(5, int(item.get("level", 0))))
            count = int(item.get("count", 0))
            cells.append((week, dow, day.isoformat(), count, level))

    total = int(obj.get("total", sum(x[3] for x in cells)))

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" rx="16" fill="#0b1220"/>',
        '<rect x="1" y="1" width="100%" height="100%" rx="16" fill="none" stroke="#263244"/>',
        '<style><![CDATA['
        '.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;}'
        '.title{fill:#f8fafc;font-size:18px;font-weight:700;}'
        '.muted{fill:#94a3b8;font-size:12px;}'
        ']]></style>',
        f'<text x="28" y="32" class="mono title">naichal@github ~ $ ./contributions.sh</text>',
        f'<text x="28" y="53" class="mono muted">{html.escape(str(total))} contributions in the last year</text>',
    ]

    # Month-ish markers using the first day of each month in the visible range.
    last_month = None
    for week in range(WEEKS):
        day = start + timedelta(days=week * 7)
        if day.month != last_month:
            parts.append(
                f'<text x="{LEFT + week * STEP}" y="68" class="mono muted">{day.strftime("%b")}</text>'
            )
            last_month = day.month

    for week, dow, day, count, level in cells:
        x = LEFT + week * STEP
        y = TOP + dow * STEP
        delay = (week * 7 + dow) * 0.012
        label = f"{count} contribution{'s' if count != 1 else ''} on {day}"
        parts.append(
            f'<g opacity="0">'
            f'<title>{html.escape(label)}</title>'
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{PALETTE[level]}">'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.18s" begin="{delay:.3f}s" fill="freeze"/>'
            f'</rect></g>'
        )

    legend_y = TOP + DAYS * STEP + 24
    parts.append('<text x="28" y="%d" class="mono muted">Less</text>' % legend_y)
    lx = 62
    for level in range(6):
        parts.append(
            f'<rect x="{lx + level * STEP}" y="{legend_y - 11}" width="{CELL}" height="{CELL}" rx="3" fill="{PALETTE[level]}"/>'
        )
    parts.append(
        f'<text x="{lx + 6 * STEP + 6}" y="{legend_y}" class="mono muted">More</text>'
    )
    parts.append('</svg>')

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
