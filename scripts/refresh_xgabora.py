"""Refresh the BetForge training set from a club-league CSV exported from
xgabora/Club-Football-Match-Data-2000-2025 (MIT repo; source data is
football-data.co.uk — see docs/research/free-data-sources-2026.md §4 for the
commercial-reuse caveat).

Maps the wide xgabora schema into the canonical BetForge CSV:
    home, away, home_goals, away_goals, date, home_odds, draw_odds, away_odds

Only full-time result columns are used (FT, not HT) — matching the BF-004
requirement that FT and HT markets stay separate. Rows with missing FT scores
or an unrecognizable date are skipped (count reported).

Pseudo-rows (e.g. all '#VALUE!') are dropped rather than repaired.

Run:
    .venv/bin/python scripts/refresh_xgabora.py --in /tmp/xgabora.csv \
        --out data/matches.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

_DIVISION_RE = re.compile(r"[A-Za-z]{1,2}[0-9]+")
_ODD_RE = re.compile(r"^[0-9]*\.?[0-9]+$")


def _parse_odd(raw: str) -> float | None:
    if isinstance(raw, str):
        raw = raw.strip()
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        return float(raw) if float(raw) > 0 else None
    if not _ODD_RE.match(raw):
        return None
    f = float(raw)
    return f if f > 0 else None


def _parse_date(raw: str) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.date().isoformat()
        except ValueError:
            continue
    return None


def transform(input_path: Path) -> list[dict]:
    records: list[dict] = []
    skipped = {"missing_score": 0, "bad_date": 0, "no_odds": 0, "pseudo": 0}
    with input_path.open(newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            hg_raw = (row.get("FTHome") or "").strip()
            ag_raw = (row.get("FTAway") or "").strip()
            hg = float(hg_raw) if hg_raw else None
            ag = float(ag_raw) if ag_raw else None
            if hg is None or ag is None:
                skipped["missing_score"] += 1
                continue
            if hg < 0 or ag < 0:
                skipped["pseudo"] += 1
                continue

            home = (row.get("HomeTeam") or "").strip()
            away = (row.get("AwayTeam") or "").strip()
            if not home or not away:
                skipped["missing_score"] += 1
                continue

            d = _parse_date(row.get("MatchDate") or "")
            if not d:
                skipped["bad_date"] += 1
                continue

            home_odd = _parse_odd(row.get("OddHome") or "")
            draw_odd = _parse_odd(row.get("OddDraw") or "")
            away_odd = _parse_odd(row.get("OddAway") or "")
            if home_odd is None or draw_odd is None or away_odd is None:
                skipped["no_odds"] += 1
                # Odds are preserved for future calibration but not required:
                # keep the row and write empty odds rather than discard fixtures.

            records.append(
                {
                    "home": home,
                    "away": away,
                    "home_goals": int(hg),
                    "away_goals": int(ag),
                    "date": d,
                    "home_odds": home_odd if home_odd is not None else "",
                    "draw_odds": draw_odd if draw_odd is not None else "",
                    "away_odds": away_odd if away_odd is not None else "",
                }
            )
    print(f"transformed {len(records)} records")
    print(f"skipped: {json.dumps(skipped)}", file=sys.stderr)
    return records


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="input", required=True)
    ap.add_argument("--out", dest="output", required=True)
    ap.add_argument("--since", type=str, default=None, help="only dates >= YYYY-MM-DD")
    args = ap.parse_args()

    records = transform(Path(args.input))
    if args.since:
        since = date.fromisoformat(args.since)
        before = len(records)
        records = [r for r in records if r["date"] >= since.isoformat()]
        print(f"windowed since {args.since}: {before} -> {len(records)}", file=sys.stderr)

    if not records:
        print("nothing to write", file=sys.stderr)
        raise SystemExit(1)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["home", "away", "home_goals", "away_goals", "date",
                    "home_odds", "draw_odds", "away_odds"])
        for r in records:
            w.writerow([r["home"], r["away"], r["home_goals"], r["away_goals"],
                        r["date"], r["home_odds"], r["draw_odds"], r["away_odds"]])
    print(f"wrote {len(records)} club rows to {out}")


if __name__ == "__main__":
    main()
