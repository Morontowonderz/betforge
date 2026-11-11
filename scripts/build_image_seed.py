"""Build the in-image SQLite seed for BETFORGE (used by the Dockerfile).

From the football-data.co.uk corpus (data/raw_fd) it populates BOTH tables of
the one betforge.db:
  * matches     <- canonical FT-only rows (home,away,hg,ag,date) for /predict,
                   /api/accuracy and the strength model;
  * matches_ou  <- real O/U 2.5 closing lines for the honest O2.5 backtest.

Usage:
    python scripts/build_image_seed.py data/raw_fd /app/betforge.db
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from betforge.ingestion import load_ou_corpus  # noqa: E402
from betforge.storage import run_ingest, ingest_ou_matches, count_matches, count_matches_ou  # noqa: E402


def main() -> None:
    csv_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd() / "data" / "raw_fd"
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("betforge.db")

    ou_matches, stats = load_ou_corpus(csv_dir)
    # canonical FT-only temp CSV for the strength-model `matches` table
    tmp = db_path.parent / "_canonical_for_seed.csv"
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        fh.write("home,away,home_goals,away_goals,date\n")
        for m in ou_matches:
            fh.write(f"{m.home},{m.away},{m.home_goals},{m.away_goals},{m.date or ''}\n")

    n_matches = run_ingest(tmp, db_path)
    tmp.unlink(missing_ok=True)
    n_ou = ingest_ou_matches(ou_matches, db_path)

    print(f"files={stats['files']} rows={stats['rows']} dropped_ou={stats['dropped_ou']}")
    print(f"matches table   = {count_matches(db_path)} (FT results, for /predict + accuracy)")
    print(f"matches_ou table= {count_matches_ou(db_path)} (real O/U 2.5 closing lines)")
    if n_matches == 0 or n_ou == 0:
        sys.exit("seed produced no rows; aborting image build")


if __name__ == "__main__":
    main()
