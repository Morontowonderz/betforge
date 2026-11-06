"""Populate the BetForge SQLite database from the canonical CSV.

Usage:
    .venv/bin/python scripts/ingest_db.py [--csv data/matches.csv] [--db betforge.db]

Prints rows inserted; exits non-zero if nothing was ingested.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from betforge.storage import count_matches, run_ingest

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default=str(ROOT / "data" / "matches.csv"))
    ap.add_argument("--db", default=str(ROOT / "betforge.db"))
    args = ap.parse_args()

    csv_path = Path(args.csv).resolve()
    db_path = Path(args.db).resolve()
    if not csv_path.exists():
        print(f"BLOCKED: CSV not found: {csv_path}", flush=True)
        return 1

    n = run_ingest(csv_path, db_path)
    total = count_matches(db_path)
    print(f"ingested {n} rows from {csv_path.name} -> {db_path}")
    print(f"verified: {total} rows in DB")
    return 0 if n > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
