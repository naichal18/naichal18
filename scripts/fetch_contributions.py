#!/usr/bin/env python3
"""
Fetch the public GitHub contribution calendar without an API token.

Usage:
    python scripts/fetch_contributions.py

Output:
    data/contributions.json
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = "naichal18"
URL = f"https://github.com/users/{USERNAME}/contributions"
OUT = Path(__file__).resolve().parents[1] / "data" / "contributions.json"


def main():
    response = requests.get(
        URL,
        headers={"User-Agent": "naichal18-profile-art/1.0"},
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    days = []

    for cell in soup.select("td.ContributionCalendar-day"):
        day = cell.get("data-date")
        level = cell.get("data-level")

        # GitHub's contribution cells expose date + contribution level.
        if day and level is not None:
            try:
                level = int(level)
            except ValueError:
                continue
            count_text = cell.get("aria-label", "")
            m = re.search(r"(\d[\d,]*) contribution", count_text)
            count = int(m.group(1).replace(",", "")) if m else 0
            days.append({"date": day, "count": count, "level": level})

    if not days:
        raise RuntimeError(
            "No contribution cells were found. GitHub may have changed its HTML."
        )

    days.sort(key=lambda x: x["date"])

    # Keep the most recent 371 days (~53 weeks).
    days = days[-371:]

    total = sum(d["count"] for d in days)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "username": USERNAME,
                "updated": date.today().isoformat(),
                "total": total,
                "days": days,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {len(days)} contribution days to {OUT}")


if __name__ == "__main__":
    main()
