"""Build the canonical advanced CSV from football-data.co.uk raw files.

Input : data/raw_fd/<DIV>_<season>.csv  (from scripts/fetch_data.py)
Output: data/matches_advanced.csv with real O/U 2.5 closing lines, referee,
        shots, cards, and the 1X2 odds used to fit the DC baseline.

Column mapping (verified against the 2019-2024 E0 files):
  Date, HomeTeam, AwayTeam, FTHG, FTAG          -> identity + result
  B365H/D/A, B365>2.5, B365<2.5                  -> opening lines
  B365C>2.5, B365C<2.5, PC>2.5, PC<2.5, AvgC>2.5 -> CLOSING lines (preferred)
  PSH/PSD/PSA                                    -> Pinnacle closing 1X2
  Referee, HS/AS, HST/AST, HC/AC, HY/AY, HR/AR    -> referee + shots + cards

Missing columns in older seasons fall back to the opening line (never silently
dropped). Team names are normalised to the canonical matches.csv spelling.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw_fd"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "matches_advanced.csv"

# Canonical team-name aliases (football-data.co.uk -> matches.csv spelling).
# Add entries here when a merge produces unmatched teams.
TEAM_ALIASES = {
    "Man United": "Manchester United",
    "Man City": "Manchester City",
    "Tottenham": "Tottenham Hotspur",
    "West Brom": "West Bromwich Albion",
    "West Ham": "West Ham United",
    "Wolves": "Wolverhampton Wanderers",
    "Nott'm Forest": "Nottingham Forest",
    "Leicester": "Leicester City",
    "Leeds": "Leeds United",
    "Brighton": "Brighton and Hove Albion",
    "Brentford": "Brentford",
    "Ipswich": "Ipswich Town",
    "Sheffield United": "Sheffield United",
    "Sheffield Weds": "Sheffield Wednesday",
    "Birmingham": "Birmingham City",
    "Charlton": "Charlton Athletic",
    "Wigan": "Wigan Athletic",
    "Huddersfield": "Huddersfield Town",
    "QPR": "Queens Park Rangers",
    "Notts County": "Notts County",
    "Rotherham": "Rotherham United",
    "Coventry": "Coventry City",
    "Blackburn": "Blackburn Rovers",
    "Preston": "Preston North End",
    "Middlesbrough": "Middlesbrough",
    "Stoke": "Stoke City",
    "Derby": "Derby County",
    "Norwich": "Norwich City",
    "Watford": "Watford",
    "Sunderland": "Sunderland",
    "Aston Villa": "Aston Villa",
    "Everton": "Everton",
    "Liverpool": "Liverpool",
    "Chelsea": "Chelsea",
    "Arsenal": "Arsenal",
    "Newcastle": "Newcastle United",
    "Southampton": "Southampton",
    "Crystal Palace": "Crystal Palace",
    "Fulham": "Fulham",
    "Bournemouth": "AFC Bournemouth",
    "Burnley": "Burnley",
    "Luton": "Luton Town",
}


def _parse_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_odd(raw: str) -> float | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        f = float(raw)
    except ValueError:
        return None
    return f if f > 1.0 else None


def _parse_int(raw: str) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _first(row: dict, *names: str) -> str | None:
    for n in names:
        v = row.get(n)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def _normalise_team(name: str) -> str:
    return TEAM_ALIASES.get(name, name)


def transform_row(row: dict) -> dict | None:
    date = _parse_date(row.get("Date", ""))
    home = _normalise_team((row.get("HomeTeam") or "").strip())
    away = _normalise_team((row.get("AwayTeam") or "").strip())
    hg = _parse_int(row.get("FTHG", ""))
    ag = _parse_int(row.get("FTAG", ""))
    if not date or not home or not away or hg is None or ag is None:
        return None
    if hg < 0 or ag < 0:
        return None

    out = {
        "date": date, "home": home, "away": away,
        "home_goals": hg, "away_goals": ag,
        "division": (row.get("Div") or "").strip(),
    }
    # 1X2 opening + closing
    for src, dst in (("B365H", "home_odds"), ("B365D", "draw_odds"), ("B365A", "away_odds")):
        out[dst] = _parse_odd(row.get(src, "")) or ""
    for src, dst in (("PSH", "home_odds_close"), ("PSD", "draw_odds_close"), ("PSA", "away_odds_close")):
        out[dst] = _parse_odd(row.get(src, "")) or ""
    # O/U 2.5 -- CLOSING preferred, opening as fallback
    out["over25_open"] = _parse_odd(row.get("B365>2.5", "")) or ""
    out["under25_open"] = _parse_odd(row.get("B365<2.5", "")) or ""
    out["over25_close"] = _parse_odd(_first(row, "B365C>2.5", "PC>2.5", "B365>2.5") or "") or ""
    out["under25_close"] = _parse_odd(_first(row, "B365C<2.5", "PC<2.5", "B365<2.5") or "") or ""
    out["over25_avg_close"] = _parse_odd(row.get("AvgC>2.5", "")) or ""
    out["under25_avg_close"] = _parse_odd(row.get("AvgC<2.5", "")) or ""
    # referee + shots + cards
    out["referee"] = (row.get("Referee") or "").strip()
    for src, dst in (("HS", "home_shots"), ("AS", "away_shots"),
                     ("HST", "home_sot"), ("AST", "away_sot"),
                     ("HC", "home_corners"), ("AC", "away_corners"),
                     ("HY", "home_yellows"), ("AY", "away_yellows"),
                     ("HR", "home_reds"), ("AR", "away_reds")):
        out[dst] = _parse_int(row.get(src, ""))
    return out


def write_unified(rows: list[dict], out: Path) -> None:
    """Write the unified O/U-focused CSV (owner spec 2026-11-06).

    Columns: Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR,
             B365>2.5, B365<2.5, Avg>2.5, Avg<2.5
    Rows with a NaN O/U line are DROPPED (spec: "drop rows where odds are NaN").
    """
    cols = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
            "B365>2.5", "B365<2.5", "Avg>2.5", "Avg<2.5"]
    kept, dropped = 0, 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            over = r.get("over25_close") or r.get("over25_open")
            under = r.get("under25_close") or r.get("under25_open")
            avg_o = r.get("over25_avg_close")
            avg_u = r.get("under25_avg_close")
            if not over or not under:
                dropped += 1
                continue
            w.writerow({
                "Date": r["date"], "HomeTeam": r["home"], "AwayTeam": r["away"],
                "FTHG": r["home_goals"], "FTAG": r["away_goals"],
                "FTR": "H" if r["home_goals"] > r["away_goals"] else (
                    "D" if r["home_goals"] == r["away_goals"] else "A"),
                "B365>2.5": over, "B365<2.5": under,
                "Avg>2.5": avg_o or "", "Avg<2.5": avg_u or "",
            })
            kept += 1
    print(f"\nunified CSV: {kept} rows -> {out} ({dropped} dropped, no O/U line)")


COLUMNS = ["date", "home", "away", "home_goals", "away_goals", "division",
           "home_odds", "draw_odds", "away_odds",
           "home_odds_close", "draw_odds_close", "away_odds_close",
           "over25_open", "under25_open", "over25_close", "under25_close",
           "over25_avg_close", "under25_avg_close",
           "referee", "home_shots", "away_shots", "home_sot", "away_sot",
           "home_corners", "away_corners", "home_yellows", "away_yellows",
           "home_reds", "away_reds"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build canonical advanced CSV")
    ap.add_argument("--src", default=str(RAW_DIR))
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    files = sorted(src.glob("*.csv"))
    if not files:
        print(f"no CSVs in {src} -- run scripts/fetch_data.py first")
        return 1

    rows, skipped = [], 0
    for f in files:
        with f.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            n0 = len(rows)
            for raw in reader:
                r = transform_row(raw)
                if r is None:
                    skipped += 1
                    continue
                rows.append(r)
            print(f"  {f.name}: {len(rows) - n0} rows")

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})

    n_ou = sum(1 for r in rows if r["over25_close"])
    n_ref = sum(1 for r in rows if r["referee"])
    print(f"\nwrote {len(rows)} rows -> {out}")
    print(f"  skipped: {skipped}")
    print(f"  with closing O/U 2.5: {n_ou} ({100 * n_ou / max(len(rows), 1):.1f}%)")
    print(f"  with referee:         {n_ref} ({100 * n_ref / max(len(rows), 1):.1f}%)")

    # Unified O/U-focused CSV (owner spec): exact columns, NaN-odds rows dropped.
    # Spec: "create a unified matches.csv in the /data folder."
    write_unified(rows, out.parent / "matches.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
