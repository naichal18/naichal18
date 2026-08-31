#!/usr/bin/env python3

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

OUTPUT_FILE = (
    ROOT
    / "data"
    / "contributions.json"
)


def extract_count(text: str) -> int:
    """Extract contribution count from GitHub tooltip text."""

    if not text:
        return 0

    text = " ".join(text.split())

    match = re.search(
        r"(\d[\d,]*)\s+contributions?",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(
            match.group(1).replace(",", "")
        )

    if re.search(
        r"\bno\s+contributions?\b",
        text,
        re.IGNORECASE,
    ):
        return 0

    return 0


def fetch_github_page() -> str:

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,"
            "application/xhtml+xml,"
            "application/xml;q=0.9,"
            "*/*;q=0.8"
        ),
        "Accept-Language": (
            "en-US,en;q=0.9"
        ),
    }

    response = requests.get(
        URL,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


def parse_contributions(page_html: str):

    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    # ---------------------------------------------------------
    # Find contribution cells
    # ---------------------------------------------------------

    cells = soup.select(
        "[data-date][data-level]"
    )

    if not cells:
        raise RuntimeError(
            "Could not find GitHub contribution cells."
        )

    # ---------------------------------------------------------
    # Build tooltip map
    #
    # GitHub's tooltip is NOT necessarily inside the cell.
    #
    # Example concept:
    #
    # <td id="cell-id"
    #     data-date="2026-08-25"
    #     data-level="4">
    #
    # <tool-tip for="cell-id">
    #     19 contributions on August 25th
    # </tool-tip>
    # ---------------------------------------------------------

    tooltip_map = {}

    for tooltip in soup.select(
        "tool-tip"
    ):

        target = tooltip.get("for")

        if not target:
            continue

        tooltip_text = tooltip.get_text(
            " ",
            strip=True,
        )

        tooltip_map[target] = (
            tooltip_text
        )

    days = []

    # ---------------------------------------------------------
    # Parse every contribution cell
    # ---------------------------------------------------------

    for cell in cells:

        contribution_date = (
            cell.get("data-date")
        )

        if not contribution_date:
            continue

        cell_id = cell.get("id")

        try:
            level = int(
                cell.get(
                    "data-level",
                    "0",
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            level = 0

        level = max(
            0,
            min(
                5,
                level,
            ),
        )

        count = 0

        # -----------------------------------------------------
        # PRIMARY:
        # cell ID -> matching tooltip
        # -----------------------------------------------------

        if cell_id:

            tooltip_text = (
                tooltip_map.get(
                    cell_id,
                    "",
                )
            )

            count = extract_count(
                tooltip_text
            )

        # -----------------------------------------------------
        # FALLBACK:
        # Search tooltip using date text.
        # -----------------------------------------------------

        if count == 0:

            date_string = (
                contribution_date
            )

            # Search all tooltip texts.
            for tooltip_text in (
                tooltip_map.values()
            ):

                if not tooltip_text:
                    continue

                extracted = extract_count(
                    tooltip_text
                )

                if extracted > 0:

                    # Don't blindly assign arbitrary
                    # tooltip counts. Only use this
                    # fallback when GitHub's tooltip
                    # contains the contribution date.
                    #
                    # The primary ID mapping above is
                    # preferred.

                    try:
                        parsed_date = date.fromisoformat(
                            date_string
                        )

                        month_name = (
                            parsed_date.strftime(
                                "%B"
                            )
                        )

                        day_number = (
                            str(
                                parsed_date.day
                            )
                        )

                        if (
                            month_name
                            in tooltip_text
                            and day_number
                            in tooltip_text
                        ):
                            count = extracted
                            break

                    except ValueError:
                        pass

        days.append(
            {
                "date": contribution_date,
                "count": count,
                "level": level,
            }
        )

    # ---------------------------------------------------------
    # Remove duplicate dates
    # ---------------------------------------------------------

    unique_days = {}

    for item in days:

        unique_days[
            item["date"]
        ] = item

    days = sorted(
        unique_days.values(),
        key=lambda item: item["date"],
    )

    return days


def main():

    print(
        f"Fetching GitHub contributions "
        f"for {USERNAME}..."
    )

    page_html = fetch_github_page()

    days = parse_contributions(
        page_html
    )

    if not days:

        raise RuntimeError(
            "No contribution days were parsed."
        )

    # Keep approximately 53 weeks.
    days = days[-371:]

    total = sum(
        item["count"]
        for item in days
    )

    active_days = sum(
        1
        for item in days
        if item["count"] > 0
    )

    print("")
    print("=" * 60)
    print("Contribution parsing result")
    print("=" * 60)
    print(
        f"Days parsed   : {len(days)}"
    )
    print(
        f"Active days   : {active_days}"
    )
    print(
        f"Total         : {total}"
    )
    print("=" * 60)

    # ---------------------------------------------------------
    # SAFETY CHECK
    #
    # Never overwrite the JSON with fake zero data.
    # ---------------------------------------------------------

    if total == 0:

        raise RuntimeError(
            "ERROR: GitHub returned contribution levels "
            "but the contribution counts could not be parsed. "
            "Refusing to write incorrect zero-count data."
        )

    payload = {
        "username": USERNAME,
        "updated": date.today().isoformat(),
        "total": total,
        "days": days,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"Saved contribution data to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
