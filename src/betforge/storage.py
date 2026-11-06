"""SQLite persistence for the ingestion/API layer.

Thin sqlite3 wrapper (stdlib — no ORM dependency) so the FastAPI app loads its
training matches from `betforge.db` instead of re-reading the CSV on every
startup. The prediction model is untouched: rows are read back into the same
`Match` objects the model already consumes.

Schema:
    matches(id INTEGER PRIMARY KEY, home TEXT, away TEXT, home_goals INT,
            away_goals INT, date TEXT, home_odds REAL, draw_odds REAL,
            away_odds REAL)

`run_ingest` fills the DB from a canonical CSV. `iter_matches` yields `Match`
objects for the model. Column order in the CSV is canonical
(home, away, hg, ag, date[, home_odds, draw_odds, away_odds]).
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Iterable, Iterator

from .normalization import Match

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    id         INTEGER PRIMARY KEY,
    home       TEXT NOT NULL,
    away       TEXT NOT NULL,
    home_goals INTEGER NOT NULL,
    away_goals INTEGER NOT NULL,
    date       TEXT,
    home_odds  REAL,
    draw_odds  REAL,
    away_odds  REAL
);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def run_ingest(csv_path: str | Path, db_path: str | Path) -> int:
    """Populate the DB from a canonical CSV. Returns rows inserted."""
    conn = connect(db_path)
    conn.execute("DELETE FROM matches")
    n = 0
    with Path(csv_path).open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        # tolerate an optional header; skip it
        for row in reader:
            if not row or not row[0].strip():
                continue
            # canonical: home, away, hg, ag, date[, odds...]
            home, away = row[0], row[1]
            try:
                hg, ag = int(row[2]), int(row[3])
            except (ValueError, IndexError):
                continue
            date = row[4] if len(row) > 4 else None
            home_odds = _float(row[5]) if len(row) > 5 else None
            draw_odds = _float(row[6]) if len(row) > 6 else None
            away_odds = _float(row[7]) if len(row) > 7 else None
            conn.execute(
                "INSERT INTO matches(home,away,home_goals,away_goals,date,home_odds,draw_odds,away_odds)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (home, away, hg, ag, date, home_odds, draw_odds, away_odds),
            )
            n += 1
    conn.commit()
    conn.close()
    return n


def _float(v) -> float | None:
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def iter_matches(db_path: str | Path) -> Iterator[Match]:
    """Yield `Match` objects from the DB (no ordering guarantees)."""
    conn = connect(db_path)
    cur = conn.execute(
        "SELECT home,away,home_goals,away_goals,date,home_odds,draw_odds,away_odds"
        " FROM matches"
    )
    for home, away, hg, ag, date, ho, do, ao in cur:
        yield Match(
            home=home,
            away=away,
            home_goals=int(hg),
            away_goals=int(ag),
            date=date,
            home_odds=float(ho) if ho is not None else float("inf"),
            draw_odds=float(do) if do is not None else float("inf"),
            away_odds=float(ao) if ao is not None else float("inf"),
        )
    conn.close()


def count_matches(db_path: str | Path) -> int:
    conn = connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    conn.close()
    return int(n)
