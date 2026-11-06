"""Data collection from free/public sources.

No API keys, no live feeds. Ingesters accept local CSV fixtures of
matches (the football-data / openfootball style: home, away, home_goals,
away_goals, optional date). Return normalized records.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .normalization import Match, parse_match


@dataclass
class Source:
    """A bound free/public data source with provenance."""

    name: str
    url: str | None
    license_note: str
    # Ingested rows are retained so provenance of every prediction cell is traceable.
    matches: list[Match] = field(default_factory=list)

    def ingest_csv(self, path: str | Path, *, skip_header: bool = True) -> int:
        path = Path(path)
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            if skip_header:
                next(reader, None)
            added = 0
            for row in reader:
                if not row or not row[0]:
                    continue
                try:
                    m = parse_match(row)
                except ValueError:
                    continue
                self.matches.append(m)
                added += 1
        return added

    def ingest_records(self, records: Iterable[Match]) -> int:
        before = len(self.matches)
        self.matches.extend(records)
        return len(self.matches) - before
