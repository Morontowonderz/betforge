"""Load the canonical sample season CSV into the SQLite store.

Usage:
    python scripts/seed_historical.py [data/matches.csv] [betforge.db]

Reuses storage.run_ingest (stdlib sqlite3) so no ORM/driver is needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from betforge.storage import run_ingest, count_matches  # noqa: E402


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "data" / "matches.csv"
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd() / "betforge.db"
    n = run_ingest(csv_path, db_path)
    print(f"seeded {n} rows into {db_path}; db now has {count_matches(db_path)} matches")


if __name__ == "__main__":
    main()
