#!/usr/bin/env python3

import html
import json
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = (
    ROOT
    / "data"
    / "contributions.json"
)

OUTPUT_FILE = (
    ROOT
    / "contrib-heatmap.svg"
)


PALETTE = [
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
    "#69f0a0",
]


CELL_SIZE = 13
CELL_GAP = 4
CELL_STEP = CELL_SIZE + CELL_GAP

LEFT_MARGIN = 32
TOP_MARGIN = 72

WEEKS = 53
DAYS_PER_WEEK = 7

WIDTH = (
    LEFT_MARGIN
    + WEEKS * CELL_STEP
    + 32
)

HEIGHT = (
    TOP_MARGIN
    + DAYS_PER_WEEK * CELL_STEP
    + 100
)


def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {DATA_FILE}"
        )

    data = json.loads(
        DATA_FILE.read_text(
            encoding="utf-8"
        )
    )

    if not data.get("days"):
        raise RuntimeError(
            "contributions.json contains no days."
        )

    return data


def get_level(item):
    """
    Use GitHub's data-level.

    If count exists but level is zero,
    derive a fallback level.
    """

    count = int(
        item.get(
            "count",
            0,
        )
    )

    level = int(
        item.get(
            "level",
            0,
        )
    )

    if count > 0 and level == 0:
        if count <= 2:
            level = 1
        elif count <= 5:
            level = 2
        elif count <= 9:
            level = 3
        else:
            level = 4

    return max(
        0,
        min(
            5,
            level,
        ),
    )


def build_calendar(data):
    days = data["days"]

    by_date = {
        item["date"]: item
        for item in days
    }

    latest_date = max(
        date.fromisoformat(
            item["date"]
        )
        for item in days
    )

    # GitHub contribution calendar starts
    # weeks on Sunday.
    days_until_saturday = (
        6 - latest_date.weekday()
    ) % 7

    calendar_end = (
        latest_date
        + timedelta(
            days=days_until_saturday
        )
    )

    calendar_start = (
        calendar_end
        - timedelta(
            days=(WEEKS * 7) - 1
        )
    )

    cells = []

    for week in range(WEEKS):
        for weekday in range(
            DAYS_PER_WEEK
        ):
            current_date = (
                calendar_start
                + timedelta(
                    days=(
                        week * 7
                        + weekday
                    )
                )
            )

            date_string = (
                current_date.isoformat()
            )

            item = by_date.get(
                date_string,
                {
                    "date": date_string,
                    "count": 0,
                    "level": 0,
                },
            )

            cells.append(
                {
                    "week": week,
                    "weekday": weekday,
                    "date": date_string,
                    "count": int(
                        item.get(
                            "count",
                            0,
                        )
                    ),
                    "level": get_level(
                        item
                    ),
                }
            )

    return cells


def svg_text(
    x,
    y,
    text,
    css_class,
):
    return (
        f'<text x="{x}" y="{y}" '
        f'class="{css_class}">'
        f'{html.escape(str(text))}'
        f'</text>'
    )


def render(data):
    username = data.get(
        "username",
        "github",
    )

    total = int(
        data.get(
            "total",
            0,
        )
    )

    cells = build_calendar(
        data
    )

    svg = []

    svg.append(
        '<?xml version="1.0" encoding="UTF-8"?>'
    )

    svg.append(
        f'<svg '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'width="{WIDTH}" '
        f'height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">'
    )

    # ---------------------------------------------------------
    # BACKGROUND
    # ---------------------------------------------------------

    svg.append(
        f'<rect '
        f'x="0" '
        f'y="0" '
        f'width="{WIDTH}" '
        f'height="{HEIGHT}" '
        f'rx="16" '
        f'fill="#0b1220"/>'
    )

    svg.append(
        f'<rect '
        f'x="1" '
        f'y="1" '
        f'width="{WIDTH - 2}" '
        f'height="{HEIGHT - 2}" '
        f'rx="16" '
        f'fill="none" '
        f'stroke="#263244"/>'
    )

    # ---------------------------------------------------------
    # CSS
    # ---------------------------------------------------------

    svg.append(
        """
<style><![CDATA[
.mono {
    font-family:
        ui-monospace,
        SFMono-Regular,
        Menlo,
        Monaco,
        Consolas,
        "Liberation Mono",
        monospace;
}

.title {
    fill: #f8fafc;
    font-size: 18px;
    font-weight: 700;
}

.subtitle {
    fill: #94a3b8;
    font-size: 12px;
}

.month {
    fill: #94a3b8;
    font-size: 11px;
}

.legend {
    fill: #94a3b8;
    font-size: 11px;
}
]]></style>
"""
    )

    # ---------------------------------------------------------
    # HEADER
    # ---------------------------------------------------------

    svg.append(
        svg_text(
            32,
            31,
            f"{username}@github ~ $ ./contributions.sh",
            "mono title",
        )
    )

    svg.append(
        svg_text(
            32,
            51,
            f"{total:,} contributions in the last year",
            "mono subtitle",
        )
    )

    # ---------------------------------------------------------
    # MONTH LABELS
    # ---------------------------------------------------------

    previous_month = None

    for week in range(WEEKS):
        current = (
            cells[
                week * DAYS_PER_WEEK
            ]
        )

        current_date = date.fromisoformat(
            current["date"]
        )

        month = current_date.month

        if month != previous_month:
            x = (
                LEFT_MARGIN
                + week * CELL_STEP
            )

            svg.append(
                svg_text(
                    x,
                    68,
                    current_date.strftime(
                        "%b"
                    ),
                    "mono month",
                )
            )

            previous_month = month

    # ---------------------------------------------------------
    # HEATMAP
    # ---------------------------------------------------------

    for cell in cells:
        week = cell["week"]
        weekday = cell["weekday"]

        x = (
            LEFT_MARGIN
            + week * CELL_STEP
        )

        y = (
            TOP_MARGIN
            + weekday * CELL_STEP
        )

        level = cell["level"]
        count = cell["count"]
        cell_date = cell["date"]

        color = PALETTE[
            level
        ]

        if count == 0:
            label = (
                f"No contributions on "
                f"{cell_date}"
            )
        else:
            suffix = (
                ""
                if count == 1
                else "s"
            )

            label = (
                f"{count} contribution"
                f"{suffix} on "
                f"{cell_date}"
            )

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT put opacity="0" on a parent <g>.
        #
        # The rect itself is animated.
        # -----------------------------------------------------

        delay = (
            week * 7
            + weekday
        ) * 0.012

        svg.append(
            f'<rect '
            f'x="{x}" '
            f'y="{y}" '
            f'width="{CELL_SIZE}" '
            f'height="{CELL_SIZE}" '
            f'rx="3" '
            f'fill="{color}" '
            f'opacity="0">'
            f'<title>'
            f'{html.escape(label)}'
            f'</title>'
            f'<animate '
            f'attributeName="opacity" '
            f'from="0" '
            f'to="1" '
            f'dur="0.18s" '
            f'begin="{delay:.3f}s" '
            f'fill="freeze"/>'
            f'</rect>'
        )

    # ---------------------------------------------------------
    # LEGEND
    # ---------------------------------------------------------

    legend_y = (
        TOP_MARGIN
        + DAYS_PER_WEEK * CELL_STEP
        + 25
    )

    svg.append(
        svg_text(
            32,
            legend_y,
            "Less",
            "mono legend",
        )
    )

    legend_x = 67

    for level, color in enumerate(
        PALETTE
    ):
        x = (
            legend_x
            + level * CELL_STEP
        )

        svg.append(
            f'<rect '
            f'x="{x}" '
            f'y="{legend_y - 11}" '
            f'width="{CELL_SIZE}" '
            f'height="{CELL_SIZE}" '
            f'rx="3" '
            f'fill="{color}"/>'
        )

    svg.append(
        svg_text(
            legend_x
            + len(PALETTE)
            * CELL_STEP
            + 6,
            legend_y,
            "More",
            "mono legend",
        )
    )

    svg.append(
        "</svg>"
    )

    return "\n".join(svg)


def main():
    data = load_data()

    total = int(
        data.get(
            "total",
            0,
        )
    )

    if total <= 0:
        raise RuntimeError(
            "Refusing to render a zero-total "
            "heatmap. Fix contribution data first."
        )

    svg = render(
        data
    )

    OUTPUT_FILE.write_text(
        svg,
        encoding="utf-8",
    )

    print(
        f"Heatmap generated successfully: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
