#!/usr/bin/env python3
"""
Fetch the public GitHub contribution calendar without an API token.

The GitHub calendar exposes each day with data-date/data-level attributes.
The contribution count is rendered in the cell's accessible text/tool-tip,
so this parser deliberately checks both aria-label and visible cell text.
"""

import json
import os
import re
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GITHUB_USERNAME", "naichal18").strip()
URL = f"https://github.com/users/{USERNAME}/contributions"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "contributions.json"


def parse_count(text: str) -> int:
    """Extract '12 contributions' or '1 contribution' from arbitrary cell text."""
    if not text:
        return 0

    # Normalize whitespace first.
    text = " ".join(text.split())

    match = re.search(r"(\d[\d,]*)\s+contributions?", text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", ""))

    # GitHub explicitly uses "No contributions" for zero days.
    if re.search(r"\bno\s+contributions?\b", text, re.IGNORECASE):
        return 0

    return 0


def parse_cells(page_html: str):
    soup = BeautifulSoup(page_html, "html.parser")
    days = {}

    # Prefer cells that actually carry GitHub's date/level metadata.
    cells = soup.select("[data-date][data-level]")

    for cell in cells:
        day = cell.get("data-date")
        if not day:
            continue

        try:
            level = int(cell.get("data-level", "0"))
        except (TypeError, ValueError):
            level = 0

        # Depending on GitHub's current markup, the count may be:
        # - aria-label on the cell
        # - text in a tool-tip child
        # - regular text inside the cell
        candidates = [
            cell.get("aria-label", ""),
            cell.get_text(" ", strip=True),
        ]

        for tip in cell.select("tool-tip, [role='tooltip']"):
            candidates.append(tip.get_text(" ", strip=True))
            candidates.append(tip.get("aria-label", ""))

        combined = " ".join(x for x in candidates if x)
        count = parse_count(combined)

        days[day] = {
            "date": day,
            "count": count,
            "level": max(0, min(5, level)),
        }

    return sorted(days.values(), key=lambda item: item["date"])


def main():
    response = requests.get(
        URL,
        headers={
            "User-Agent": "naichal18-profile-art/2.0",
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=30,
    )
    response.raise_for_status()

    days = parse_cells(response.text)

    if not days:
        soup = BeautifulSoup(response.text, "html.parser")
        data_dates = len(soup.select("[data-date]"))
        data_levels = len(soup.select("[data-level]"))
        raise RuntimeError(
            "GitHub returned the page, but no contribution cells were parsed. "
            f"Diagnostics: status={response.status_code}, "
            f"data-date={data_dates}, data-level={data_levels}, url={URL}"
        )

    # Keep the most recent 371 days (~53 weeks).
    days = days[-371:]

    total = sum(item["count"] for item in days)

    payload = {
        "username": USERNAME,
        "updated": date.today().isoformat(),
        "total": total,
        "days": days,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    nonzero = sum(1 for item in days if item["count"] > 0)
    print(
        f"Fetched {len(days)} days for {USERNAME}: "
        f"{total} total contributions across {nonzero} active days."
    )
    print(f"Wrote: {OUT}")


if __name__ == "__main__":
    main()
