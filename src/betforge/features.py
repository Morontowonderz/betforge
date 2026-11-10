"""Feature engineering for match prediction, STRICTLY no-lookahead.

Every feature for a match M is computed only from matches that finished
BEFORE M's kickoff. This module enforces temporal leakage discipline: it
sorts chronologically and exposes a `features_before(matches, cutoff)`
view so the backtester and value detector can never peek at the outcome or
at any later match.

Dependency-light stdlib implementation (no pandas) so the product layer
runs on any Python; large-history callers may precompute once per eval.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from statistics import mean

from .normalization import Match


@dataclass(frozen=True)
class TeamFeatures:
    """Rolling form features for one team (home/away aggregate)."""

    played: int = 0
    goals_for_avg: float = 0.0
    goals_against_avg: float = 0.0
    btts_rate: float = 0.0
    over15_rate: float = 0.0
    win_rate: float = 0.0
    recent_goals: tuple[int, ...] = ()  # FT goals scored, oldest -> latest

    def as_dict(self) -> dict[str, float | int | tuple[int, ...]]:
        return {
            "played": self.played,
            "goals_for_avg": round(self.goals_for_avg, 3),
            "goals_against_avg": round(self.goals_against_avg, 3),
            "btts_rate": round(self.btts_rate, 3),
            "over15_rate": round(self.over15_rate, 3),
            "win_rate": round(self.win_rate, 3),
            "recent_goals": self.recent_goals,
        }


@dataclass(frozen=True)
class MatchFeatures:
    """Feature vector for a single fixture (no outcome / no future data)."""

    home: str
    away: str
    home_played: int
    away_played: int
    home_gf_avg: float
    away_gf_avg: float
    home_ga_avg: float
    away_ga_avg: float
    home_btts_rate: float
    away_btts_rate: float
    home_over15_rate: float
    away_over15_rate: float

    def as_dict(self) -> dict[str, float | int | str]:
        return {
            "home": self.home,
            "away": self.away,
            "home_played": self.home_played,
            "away_played": self.away_played,
            "home_gf_avg": round(self.home_gf_avg, 3),
            "away_gf_avg": round(self.away_gf_avg, 3),
            "home_ga_avg": round(self.home_ga_avg, 3),
            "away_ga_avg": round(self.away_ga_avg, 3),
            "home_btts_rate": round(self.home_btts_rate, 3),
            "away_btts_rate": round(self.away_btts_rate, 3),
            "home_over15_rate": round(self.home_over15_rate, 3),
            "away_over15_rate": round(self.away_over15_rate, 3),
        }


def _roll(features: list[Match], team: str, window: int | None) -> list[Match]:
    """Fixture history of `team`, oldest first (already chronologically sorted input)."""
    out = [m for m in features if m.home == team or m.away == team]
    if window is not None:
        out = out[-window:]
    return out


def team_features(features: list[Match], team: str, *, window: int = 5) -> TeamFeatures:
    """Rolling features for `team` from its last `window` matches (all venues)."""
    hist = _roll(features, team, window)
    n = len(hist)
    if n == 0:
        return TeamFeatures()
    gf: list[int] = []
    ga: list[int] = []
    btts = 0
    over15 = 0
    wins = 0
    for m in hist:
        goals_for = m.home_goals if m.home == team else m.away_goals
        goals_against = m.away_goals if m.home == team else m.home_goals
        gf.append(goals_for)
        ga.append(goals_against)
        if goals_for >= 1 and goals_against >= 1:
            btts += 1
        if goals_for + goals_against >= 2:
            over15 += 1
        if goals_for > goals_against:
            wins += 1
    return TeamFeatures(
        played=n,
        goals_for_avg=mean(gf),
        goals_against_avg=mean(ga),
        btts_rate=btts / n,
        over15_rate=over15 / n,
        win_rate=wins / n,
        recent_goals=tuple(gf),
    )


def features_before(history: Sequence[Match], home: str, away: str) -> MatchFeatures:
    """Build a fixture feature vector from matches strictly BEFORE it.

    The caller passes `history` = already-settled matches (the backtester
    guarantees this by construction). Nothing about the current fixture's
    result or any future match enters these features.
    """
    prior = list(history)
    hf = team_features(prior, home)
    af = team_features(prior, away)
    return MatchFeatures(
        home=home,
        away=away,
        home_played=hf.played,
        away_played=af.played,
        home_gf_avg=hf.goals_for_avg,
        away_gf_avg=af.goals_for_avg,
        home_ga_avg=hf.goals_against_avg,
        away_ga_avg=af.goals_against_avg,
        home_btts_rate=hf.btts_rate,
        away_btts_rate=af.btts_rate,
        home_over15_rate=hf.over15_rate,
        away_over15_rate=af.over15_rate,
    )


def chrono_sort(matches: Iterable[Match]) -> list[Match]:
    """Stable chronological sort (no date => treated as oldest)."""
    return sorted(matches, key=lambda m: (m.date is None, m.date or ""))
