"""Typed canonical contracts for a single football match.

The schema encodes the BF-004 requirements at a minimal level:
FT (not HT) goals, plain 'home'/'away' team IDs, no naive timezone-less
dates, non-negative integer goals and valid decimal odds. Invalid rows
must be rejected, never silently repaired.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Match:
    """A canonical full-time football match (FT result, not HT)."""

    home: str
    away: str
    home_goals: int  # full-time goals, 0..INT_MAX
    away_goals: int
    date: str | None = None  # ISO-8601 date (YYYY-MM-DD) or None
    # decimal odds; float("inf") == no odds provided (market unknown)
    home_odds: float = float("inf")
    draw_odds: float = float("inf")
    away_odds: float = float("inf")

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def over1_5(self) -> bool:
        """Full-time total goals strictly greater than 1.5."""
        return self.total_goals > 1

    @property
    def btts(self) -> bool:
        """Both teams scored (each team >= 1 goal)."""
        return self.home_goals >= 1 and self.away_goals >= 1


def _validate_odds(value: float) -> bool:
    return value == float("inf") or value is None or (value >= 1.0 and value < 1e9)


def parse_match(row) -> Match:
    """Parse a CSV row into a Match, rejecting anything malformed.

    Accepted column order: home, away, home_goals, away_goals[, date].
    Raises ValueError on any invalid field so callers can skip the row.
    """
    if len(row) < 4:
        raise ValueError(f"row needs >=4 columns, got {len(row)}")
    home = str(row[0]).strip()
    away = str(row[1]).strip()
    if not home or not away:
        raise ValueError("empty team name")
    try:
        hg = int(row[2])
        ag = int(row[3])
    except (ValueError, TypeError):
        raise ValueError(f"non-integer goals: {row[2:4]}")
    if hg < 0 or ag < 0:
        raise ValueError("negative goals")
    m = Match(home=home, away=away, home_goals=hg, away_goals=ag)
    if len(row) >= 5 and str(row[4]).strip():
        m = Match(home=home, away=away, home_goals=hg, away_goals=ag, date=str(row[4]).strip())
    return m
