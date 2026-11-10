"""Ingest real Over/Under 2.5 closing lines from football-data.co.uk CSVs.

Follows the football-data.co.uk contract (see the data-engineering skill):
  * fetch/read the CSV (url `mmz4281/{season}/{division}.csv` when downloading);
  * prefer the CLOSING O/U line columns (AvgC>2.5 / AvgC<2.5, else B365C>2.5/<),
    fall back to the opening line (Avg>2.5 / Avg<2.5, B365>2.5/<);
  * use only full-time goals (FTHG/FTAG), never HT;
  * drop rows missing a valid O/U pair and report the drop count;
  * normalise team names to canonical spellings before returning.

Returns `Match` objects carrying `over_odds` / `under_odds` so the real-line
O2.5 backtest can compare the model against a genuine market — no 1X2 proxy.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from .normalization import Match

# canonicalise common football-data.co.uk team spellings
TEAM_ALIASES = {
    "man utd": "Manchester United",
    "man united": "Manchester United",
    "man city": "Manchester City",
    "manchester city": "Manchester City",
    "newcastle": "Newcastle United",
    "wolves": "Wolverhampton Wanderers",
    "west brom": "West Bromwich Albion",
    "wba": "West Bromwich Albion",
    "sheffield utd": "Sheffield United",
    "sheff utd": "Sheffield United",
    "bologna": "Bologna",
    "inter": "Inter Milan",
    "napoli": "Napoli",
    "fc bayern": "Bayern Munich",
    "leverkusen": "Bayer Leverkusen",
    "m'gladbach": "Borussia Monchengladbach",
    "mainz 05": "Mainz 05",
    "real sociedad": "Real Sociedad",
    "atl. madrid": "Atletico Madrid",
    "deportivo alaves": "Alaves",
}


def canonical_team(name: str) -> str:
    key = name.strip().lower()
    return TEAM_ALIASES.get(key, name.strip())


CLOSING_OVER = ("AvgC>2.5", "B365C>2.5", "PC>2.5")
CLOSING_UNDER = ("AvgC<2.5", "B365C<2.5", "PC<2.5")
OPENING_OVER = ("Avg>2.5", "B365>2.5", "P>2.5")
OPENING_UNDER = ("Avg<2.5", "B365<2.5", "P<2.5")


def _float_opt(v: object) -> float:
    if v is None:
        return float("inf")
    try:
        f = float(str(v))
    except (TypeError, ValueError):
        return float("inf")
    return f if math.isfinite(f) and f > 1.0 else float("inf")


def parse_football_data_file(path: str | Path) -> tuple[list[Match], dict[str, int]]:
    """Parse one football-data.co.uk CSV into real-line Matches.

    Returns (matches, stats) with stats["dropped_ou"] counting rows skipped
    for a missing/invalid O/U line. Closing line preferred over opening.
    """
    stats = {"rows": 0, "dropped_ou": 0, "with_ou": 0}
    out: list[Match] = []
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            stats["rows"] += 1
            try:
                hg, ag = int(row["FTHG"]), int(row["FTAG"])
            except (ValueError, TypeError, KeyError):
                continue
            date = (row.get("Date") or "").strip() or None

            # closing line first, then opening
            over_col = next((c for c in CLOSING_OVER if row.get(c)), None)
            under_col = next((c for c in CLOSING_UNDER if row.get(c)), None)
            if not over_col or not under_col:
                over_col = next((c for c in OPENING_OVER if row.get(c)), None)
                under_col = next((c for c in OPENING_UNDER if row.get(c)), None)
            over = _float_opt(row.get(over_col) if over_col else None)
            under = _float_opt(row.get(under_col) if under_col else None)
            if not (math.isfinite(over) and math.isfinite(under)):
                stats["dropped_ou"] += 1
                continue
            stats["with_ou"] += 1
            out.append(
                Match(
                    home=canonical_team(row["HomeTeam"]),
                    away=canonical_team(row["AwayTeam"]),
                    home_goals=hg,
                    away_goals=ag,
                    date=date,
                    over_odds=over,
                    under_odds=under,
                )
            )
    return out, stats


def load_ou_corpus(csv_dir: str | Path) -> tuple[list[Match], dict[str, int]]:
    """Parse every football-data.co.uk CSV under `csv_dir` into real-line Matches.

    Returns (matches, totals) where totals aggregates per-file row/dropped/with_ou
    counts. Sorted chronologically.
    """
    matches: list[Match] = []
    totals = {"files": 0, "rows": 0, "dropped_ou": 0, "with_ou": 0}
    for path in sorted(Path(csv_dir).glob("*.csv")):
        rows, stats = parse_football_data_file(path)
        totals["files"] += 1
        totals["rows"] += stats["rows"]
        totals["dropped_ou"] += stats["dropped_ou"]
        totals["with_ou"] += stats["with_ou"]
        matches.extend(rows)
    matches.sort(key=lambda m: (m.date is None, m.date or ""))
    return matches, totals