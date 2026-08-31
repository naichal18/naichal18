#!/usr/bin/env python3
"""
Render data/contributions.json as an animated SVG heatmap.
"""

import html
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

PALETTE = [
    "#161b22",  # 0
    "#0e4429",  # 1
    "#006d32",  # 2
    "#26a641",  # 3
    "#39d353",  # 4
    "#69f0a0",  # 5
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
    by_date = {item["date"]: item for item in obj["days"]}
    return obj, by_date


def level_for(item):
    """Use GitHub's level when present; otherwise derive a sensible level."""
    level = int(item.get("level", 0))
    count = int(item.get("count", 0))

    # Current GitHub commonly uses 0..4. Keep compatibility with 0..5.
    if count > 0 and level == 0:
        if count <= 2:
            level = 1
        elif count <= 5:
            level = 2
        elif count <= 9:
            level = 3
        else:
            level = 4

    return max(0, min(5, level))


def main():
    obj, by_date = load_days()

    latest = date.fromisoformat(max(by_date))
    # GitHub calendar weeks run Sunday -> Saturday.
    end = latest + timedelta(days=(5 - latest.weekday()) % 7)
    start = end - timedelta(days=WEEKS * 7 - 1)

    cells = []
    for week in range(WEEKS):
        for dow in range(DAYS):
            day = start + timedelta(days=week * 7 + dow)
            item = by_date.get(
                day.isoformat(),
                {"date": day.isoformat(), "count": 0, "level": 0},
            )
            count = int(item.get("count", 0))
            level = level_for(item)
            cells.append((week, dow, day.isoformat(), count, level))

    total = int(obj.get("total", sum(cell[3] for cell in cells)))

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" rx="16" fill="#0b1220"/>',
        f'<rect x="1" y="1" width="{WIDTH-2}" height="{HEIGHT-2}" rx="16" fill="none" stroke="#263244"/>',
        '<style><![CDATA['
        '.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;}'
        '.title{fill:#f8fafc;font-size:18px;font-weight:700;}'
        '.muted{fill:#94a3b8;font-size:12px;}'
        ']]></style>',
        '<text x="28" y="32" class="mono title">naichal@github ~ $ ./contributions.sh</text>',
        f'<text x="28" y="53" class="mono muted">{html.escape(str(total))} contributions in the last year</text>',
    ]

    # Month labels.
    last_month = None
    for week in range(WEEKS):
        day = start + timedelta(days=week * 7)
        if day.month != last_month:
            parts.append(
                f'<text x="{LEFT + week * STEP}" y="68" class="mono muted">{day.strftime("%b")}</text>'
            )
            last_month = day.month

    # Draw every cell. IMPORTANT: animate the rect itself; do not put it
    # inside a permanently invisible parent <g>.
    for week, dow, day, count, level in cells:
        x = LEFT + week * STEP
        y = TOP + dow * STEP
        delay = (week * 7 + dow) * 0.012
        label = f"{count} contribution{'s' if count != 1 else ''} on {day}"

        parts.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" '
            f'fill="{PALETTE[level]}" opacity="0" '
            f'aria-label="{html.escape(label, quote=True)}">'
            f'<title>{html.escape(label)}</title>'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.18s" '
            f'begin="{delay:.3f}s" fill="freeze"/>'
            f'</rect>'
        )

    legend_y = TOP + DAYS * STEP + 24
    parts.append(f'<text x="28" y="{legend_y}" class="mono muted">Less</text>')

    lx = 62
    for level, color in enumerate(PALETTE):
        parts.append(
            f'<rect x="{lx + level * STEP}" y="{legend_y - 11}" '
            f'width="{CELL}" height="{CELL}" rx="3" fill="{color}"/>'
        )

    parts.append(
        f'<text x="{lx + len(PALETTE) * STEP + 6}" y="{legend_y}" '
        f'class="mono muted">More</text>'
    )

    parts.append("</svg>")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote: {OUT}")


if __name__ == "__main__":
    main()
