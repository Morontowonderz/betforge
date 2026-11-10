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
from collections.abc import Iterable, Iterator
from pathlib import Path

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

# Real Over/Under 2.5 closing lines (football-data.co.uk), for the honest O2.5 path.
SCHEMA_OU = """
CREATE TABLE IF NOT EXISTS matches_ou (
    id         INTEGER PRIMARY KEY,
    home       TEXT NOT NULL,
    away       TEXT NOT NULL,
    home_goals INTEGER NOT NULL,
    away_goals INTEGER NOT NULL,
    date       TEXT,
    over_odds  REAL,
    under_odds REAL
);
CREATE INDEX IF NOT EXISTS idx_matches_ou_date ON matches_ou(date);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    conn.executescript(SCHEMA_OU)
    return conn


def run_ingest(csv_path: str | Path, db_path: str | Path) -> int:
    """Populate the DB from a canonical CSV. Returns rows inserted."""
    conn = connect(db_path)
    conn.execute("DELETE FROM matches")
    n = 0
    with Path(csv_path).open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader, None)  # tolerate an optional header; skip it
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


def ingest_ou_matches(records: Iterable[Match], db_path: str | Path) -> int:
    """Insert real-line (over_odds/under_odds) Matches into matches_ou. Returns count."""
    conn = connect(db_path)
    conn.execute("DELETE FROM matches_ou")
    n = 0
    for m in records:
        if not m.has_ou_line:
            continue
        conn.execute(
            "INSERT INTO matches_ou(home,away,home_goals,away_goals,date,over_odds,under_odds) VALUES(?,?,?,?,?,?,?)",
            (m.home, m.away, m.home_goals, m.away_goals, m.date, m.over_odds or float("inf"), m.under_odds or float("inf")),
        )
        n += 1
    conn.commit()
    conn.close()
    return n


def iter_matches_ou(db_path: str | Path) -> Iterator[Match]:
    """Yield real-line Matches (with over_odds/under_odds) from matches_ou."""
    conn = connect(db_path)
    cur = conn.execute("SELECT home,away,home_goals,away_goals,date,over_odds,under_odds FROM matches_ou")
    for home, away, hg, ag, date, ov, un in cur:
        yield Match(
            home=home,
            away=away,
            home_goals=int(hg),
            away_goals=int(ag),
            date=date,
            over_odds=float(ov) if ov is not None else float("inf"),
            under_odds=float(un) if un is not None else float("inf"),
        )
    conn.close()


def count_matches_ou(db_path: str | Path) -> int:
    conn = connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM matches_ou").fetchone()[0]
    conn.close()
    return int(n)
