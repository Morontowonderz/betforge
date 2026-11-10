"""Fetch historical football-data.co.uk CSVs (real O/U 2.5 closing odds).

WHY: the xgabora club dataset has 1X2 odds only. football-data.co.uk ships
the actual Over/Under 2.5 lines (multiple bookmakers + average + closing),
plus referee, shots, and cards -- three of the features the Phase 2 pivot
needs. This script downloads those CSVs into data/raw_fd/.

URL STRUCTURE (verified 2026-11-06):
    https://football-data.co.uk/mmz4281/<season>/<division>.csv
  - <season> is the two-digit year the season STARTS (2526 = 2025/26).
  - <division>: E0 = English Premier League, E1/E2/EC = lower divisions,
    D1/D2 = Germany, SP1/SP2 = Spain, I1/I2 = Italy, F1/F2 = France.
  - Older seasons may live under mmz421 (redirects to mmz4281).

Robots/rate: the host sets a 1000/hr rate limit. We fetch sequentially with
a small delay and never hammer it. Files are cached on disk; re-running
skips already-downloaded seasons.

Run:
    .venv/bin/python scripts/fetch_data.py --divisions E0 --seasons 2019-2024
    .venv/bin/python scripts/fetch_data.py --divisions E0,D1,SP1 --seasons 2015-2024
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "https://football-data.co.uk/mmz4281/{season}/{division}.csv"
LEGACY_URL = "https://football-data.co.uk/mmz421/{season}/{division}.csv"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw_fd"
UA = {"User-Agent": "BetForge research fetch (contact: local developer)"}
DELAY_S = 1.0  # polite sequential pacing


def _get(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
            if r.status == 200 and data:
                return data
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        print(f"  error {url}: {e}")
    return None

DIVISIONS = {
    "E0": "England Premier League",
    "E1": "England Championship",
    "E2": "England League One",
    "EC": "England League Two",
    "D1": "Germany Bundesliga",
    "D2": "Germany 2. Bundesliga",
    "SP1": "Spain La Liga",
    "SP2": "Spain Segunda",
    "I1": "Italy Serie A",
    "I2": "Italy Serie B",
    "F1": "France Ligue 1",
    "F2": "France Ligue 2",
}


def season_code(season: str) -> str:
    """'2019-2020' -> '1920' (the two-digit start-year code the site uses)."""
    start, end = season.split("-")
    return start[2:] + end[2:]


def fetch_one(division: str, season: str, out_dir: Path, force: bool = False) -> Path | None:
    """Download one division-season CSV. Returns the path or None on failure."""
    code = season_code(season)
    target = out_dir / f"{division}_{season}.csv"
    if target.exists() and not force and target.stat().st_size > 1000:
        print(f"  cached  {target.name}")
        return target

    for url in (BASE_URL.format(season=code, division=division),
                LEGACY_URL.format(season=code, division=division)):
        data = _get(url)
        if data and data[:1] in (b"\xef", b"D", b"d"):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            print(f"  fetched {target.name} ({len(data):,} bytes) via .../{code}/")
            return target
        print(f"  no data from {url}")
    return None


def parse_seasons(spec: str) -> list[str]:
    """'2019-2024' -> ['2019-2020', ..., '2023-2024'] (inclusive)."""
    lo, hi = (int(x) for x in spec.split("-"))
    return [f"{y}-{y + 1}" for y in range(lo, hi + 1)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch football-data.co.uk CSVs")
    ap.add_argument("--divisions", default="E0",
                    help="comma-separated division codes (E0,D1,SP1,...)")
    ap.add_argument("--seasons", default="2019-2024",
                    help="season range, e.g. 2019-2024 (inclusive)")
    ap.add_argument("--out", default=str(RAW_DIR))
    ap.add_argument("--force", action="store_true", help="re-download cached files")
    args = ap.parse_args()

    out_dir = Path(args.out)
    divisions = [d.strip().upper() for d in args.divisions.split(",") if d.strip()]
    seasons = parse_seasons(args.seasons)

    print(f"football-data.co.uk fetch")
    print(f"  divisions: {', '.join(divisions)}")
    print(f"  seasons  : {seasons[0]} .. {seasons[-1]}")
    print(f"  out      : {out_dir}")
    print()

    ok, fail = 0, 0
    for division in divisions:
        if division not in DIVISIONS:
            print(f"  UNKNOWN division '{division}' -- skipping")
            continue
        print(f"[{division}] {DIVISIONS[division]}")
        for season in seasons:
            path = fetch_one(division, season, out_dir, force=args.force)
            if path:
                ok += 1
            else:
                fail += 1
                print(f"  FAILED {division} {season}")
            time.sleep(DELAY_S)

    print(f"\ndone: {ok} fetched/cached, {fail} failed")
    if ok == 0:
        print("no data downloaded -- check the season codes and division names")
        return 1
    print(f"\nNext: .venv/bin/python scripts/build_advanced_csv.py --src {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
