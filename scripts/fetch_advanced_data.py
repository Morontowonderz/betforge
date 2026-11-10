"""Advanced-data acquisition scaffold (Phase 2, Step 2).

PURPOSE
    The 9-column club dataset cannot support an edge: the ablation
    (scripts/ablation.py) showed fatigue/momentum features carry zero
    standalone signal, and the only family that beat the base rate was
    scoring history -- a proxy for the bookmaker's goal-rate line.

    To build the XGBoost residual model (Step C of the pivot) we need
    features the current table does not contain:
        - xG / xGA            (shot quality; FBref, Understat, football-data.co.uk)
        - PPDA / possession   (tactical mismatch; Opta/StatsBomb, paid)
        - referee cards/pens  (referee bias; football-data.co.uk extras, Kaggle)
        - venue / geocodes    (travel distance; manual stadium table)

    This module is the PLACEHOLDER for that pipeline. It does NOT fetch
    anything yet. It defines the contract, the target schema, and the
    merge keys, so the ingest is a fill-in once a licensed source is chosen.

DO NOT wire this into the API until real data lands. The XGBoost residual
model is useless until then (see results/PHASE2_NEGATIVE_RESULT.md).

Usage (once a source is selected):
    .venv/bin/python scripts/fetch_advanced_data.py --source fbref --seasons 2019-2024
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Target schema for the advanced table
# --------------------------------------------------------------------------- #
ADVANCED_COLUMNS = [
    # merge keys (must match the existing matches table)
    "date", "home", "away",
    # xG
    "home_xg", "away_xg", "home_xga", "away_xga",
    # shots
    "home_shots", "away_shots", "home_sot", "away_sot",
    # possession / passing (PPDA inputs)
    "home_possession", "away_possession",
    "home_passes", "away_passes",
    "home_def_actions", "away_def_actions",   # tackles + interceptions + fouls
    # referee
    "referee", "home_cards", "away_cards", "home_pens", "away_pens",
    # venue / travel
    "venue", "home_city", "away_city", "home_lat", "home_lon", "away_lat", "away_lon",
    # metadata
    "source", "source_url", "fetched_at",
]

REQUIRED_FOR_RESIDUAL = ["home_xg", "away_xg"]


@dataclass
class FetchResult:
    source: str
    seasons: list[str]
    rows_fetched: int
    rows_merged: int
    output_path: str
    fetched_at: str
    notes: str = ""


def normalise_team(name: str, aliases: dict[str, str] | None = None) -> str:
    """Map source-specific team names to the canonical names in matches.csv.

    TODO: populate `aliases` from a curated mapping table. Without this the
    merge will silently drop rows -- never assume name equality across sources.
    """
    if aliases and name in aliases:
        return aliases[name]
    return name.strip()


def merge_key(date: str, home: str, away: str) -> str:
    """Deterministic merge key: date + sorted team pair."""
    teams = "|".join(sorted([home, away]))
    return hashlib.sha1(f"{date}|{teams}".encode()).hexdigest()[:16]


def build_merge_keys(df) -> "list[str]":
    return [merge_key(d, h, a) for d, h, a in zip(df["date"], df["home"], df["away"])]


def validate_payload(df) -> tuple[bool, list[str]]:
    """Check the fetched payload has the columns the residual model needs."""
    missing = [c for c in ADVANCED_COLUMNS if c not in df.columns]
    problems = []
    if missing:
        problems.append(f"missing columns: {missing}")
    for col in REQUIRED_FOR_RESIDUAL:
        if col in df.columns and df[col].isna().all():
            problems.append(f"{col} is entirely null")
    return (len(problems) == 0, problems)


def write_payload(df, output: Path) -> Path:
    """Write the advanced table to CSV + a sidecar provenance JSON."""
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    sidecar = output.with_suffix(".provenance.json")
    sidecar.write_text(json.dumps({
        "source": "UNCONFIGURED",
        "written_at": datetime.now(timezone.utc).isoformat(),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }, indent=2))
    return output


SOURCES: dict[str, dict] = {
    "fbref": {"url": "https://fbref.com/en/comps/9/Premier-League-Stats",
              "license": "Sports Reference -- check terms before commercial use",
              "provides": ["xG", "xGA", "shots", "possession", "passes"]},
    "understat": {"url": "https://understat.com/league/EPL",
                  "license": "Check terms; xG-focused",
                  "provides": ["xG", "xGA", "shots"]},
    "football-data": {"url": "https://www.football-data.co.uk/",
                      "license": "No formal open license (same as base dataset)",
                      "provides": ["odds", "cards", "referee (some leagues)"]},
    "kaggle-referee": {"url": "https://www.kaggle.com/datasets",
                       "license": "Dataset-dependent",
                       "provides": ["referee", "cards", "penalties"]},
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Advanced-data acquisition scaffold")
    ap.add_argument("--source", choices=sorted(SOURCES), required=True)
    ap.add_argument("--seasons", default="2019-2024")
    ap.add_argument("--output", default="data/advanced_matches.csv")
    args = ap.parse_args()

    print("Advanced-data acquisition scaffold -- NOT YET IMPLEMENTED")
    print(f"  source : {args.source}")
    print(f"  url    : {SOURCES[args.source]['url']}")
    print(f"  license: {SOURCES[args.source]['license']}")
    print(f"  provides: {', '.join(SOURCES[args.source]['provides'])}")
    print()
    print("This is a placeholder. To finish Step 2:")
    print("  1. Choose a licensed source for xG (FBref or Understat).")
    print("  2. Choose a source for PPDA/possession (Opta/StatsBomb is paid).")
    print("  3. Choose a referee/cards source.")
    print("  4. Implement the fetcher against the chosen source's API/HTML.")
    print("  5. Build the team-name alias table (normalise_team).")
    print("  6. Validate with validate_payload(), then write_payload().")
    print()
    print("Until then the XGBoost residual model cannot be built -- the")
    print("ablation showed the available features carry no edge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
