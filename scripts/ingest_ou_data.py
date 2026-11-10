"""Ingest real Over/Under 2.5 closing lines (football-data.co.uk CSVs) into the store.

Usage:
    python scripts/ingest_ou_data.py [data/raw_fd] [betforge_ou.db]

Parses every football-data.co.uk CSV under the dir (closing O/U line preferred,
opening fallback), writes real-line matches to the `matches_ou` table, and
prints ingest stats — the honest-edge path for the O2.5 backtest.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from betforge.ingestion import load_ou_corpus  # noqa: E402
from betforge.storage import ingest_ou_matches, count_matches_ou  # noqa: E402


def main() -> None:
    csv_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "data" / "raw_fd"
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd() / "betforge_ou.db"
    if not csv_dir.exists():
        sys.exit(f"no CSV dir at {csv_dir} — run fetch or point at the raw_fd directory")
    matches, totals = load_ou_corpus(csv_dir)
    n = ingest_ou_matches(matches, db_path)
    print(f"files={totals['files']} rows={totals['rows']} dropped_ou={totals['dropped_ou']}")
    print(f"ingested {n} real-line matches into {db_path} (table matches_ou={count_matches_ou(db_path)})")


if __name__ == "__main__":
    main()
