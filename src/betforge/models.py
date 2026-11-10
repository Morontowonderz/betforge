"""Prediction models: Poisson/Dixon-Coles-style joint goal distribution.

Derives P(home=i, away=j) for a match from attack/defence strength
estimates and lambda adjustment (rho) following the Dixon-Coles
correction for low scores. From that joint distribution we marginalize
to the two markets BetForge targets:

  - Over 1.5 goals  (P(H+A > 1.5))
  - Both Teams To Score (P(home>=1 and away>=1))

Dependency-light: uses only math/statistics from the stdlib. This is a
research estimator, not a wagering signal; no edge is claimed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean

MAX_GOALS = 10  # truncation ceiling for the joint distribution (prob beyond ~0)


@dataclass(frozen=True)
class TeamStrength:
    attack: float = 1.0
    defence: float = 1.0


@dataclass(frozen=True)
class Prediction:
    home: str
    away: str
    expected_home: float
    expected_away: float
    p_over1_5: float
    p_btts: float
    p_home: float
    p_draw: float
    p_away: float

    def as_dict(self) -> dict:
        return {
            "home": self.home,
            "away": self.away,
            "expected_home": round(self.expected_home, 3),
            "expected_away": round(self.expected_away, 3),
            "p_over1_5": round(self.p_over1_5, 4),
            "p_btts": round(self.p_btts, 4),
            "p_home": round(self.p_home, 4),
            "p_draw": round(self.p_draw, 4),
            "p_away": round(self.p_away, 4),
        }


def poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam**k / math.factorial(k)


def joint_goal_matrix(lam_home: float, lam_away: float, rho: float = 0.0) -> list[list[float]]:
    """P(home=i, away=j) with Dixon-Coles rho correction on 0-0/0-1/1-0/1-1."""
    rows = []
    for i in range(MAX_GOALS + 1):
        row = []
        for j in range(MAX_GOALS + 1):
            p = poisson_pmf(i, lam_home) * poisson_pmf(j, lam_away)
            if i == 0 and j == 0:
                p *= 1.0 - lam_home * lam_away * rho
            elif i == 0 and j == 1:
                p *= 1.0 + lam_home * rho
            elif i == 1 and j == 0:
                p *= 1.0 + lam_away * rho
            elif i == 1 and j == 1:
                p *= 1.0 - rho
            row.append(max(p, 0.0))
        rows.append(row)
    # renormalize to a valid distribution (correction can push a tail slightly)
    total = sum(sum(r) for r in rows)
    if total > 0:
        for i in range(MAX_GOALS + 1):
            for j in range(MAX_GOALS + 1):
                rows[i][j] /= total
    return rows


def _estimate_strengths(matches, recent: int | None = None):
    """Estimate per-team attack/defence factors from observed results.

    attack = team goals scored / league avg goals per team
    defence = team goals conceded / league avg goals per team
    Uses last `recent` matches per team when given (else all).
    Falls back to league average (1.0) for teams with no history.
    """

    per_team_goals_for: dict[str, list[int]] = {}
    per_team_goals_against: dict[str, list[int]] = {}
    for m in matches:
        per_team_goals_for.setdefault(m.home, []).append(m.home_goals)
        per_team_goals_against.setdefault(m.home, []).append(m.away_goals)
        per_team_goals_for.setdefault(m.away, []).append(m.away_goals)
        per_team_goals_against.setdefault(m.away, []).append(m.home_goals)

    all_scored = [g for gs in per_team_goals_for.values() for g in gs]
    all_conceded = [g for gs in per_team_goals_against.values() for g in gs]
    lg_for = mean(all_scored) if all_scored else 1.3
    lg_against = mean(all_conceded) if all_conceded else 1.3
    # Guard zero league average (e.g. an all-0-0 sample) -> fall back to baseline.
    lag_for = max(lg_for, 0.1)
    lag_against = max(lg_against, 0.1)

    strengths: dict[str, TeamStrength] = {}
    for team, scored in per_team_goals_for.items():
        conceded = per_team_goals_against.get(team, scored)
        s = scored if recent is None else scored[-recent:]
        c = conceded if recent is None else conceded[-recent:]
        attack = (mean(s) / lag_for) if s else 1.0
        defence = (mean(c) / lag_against) if c else 1.0
        strengths[team] = TeamStrength(attack=max(attack, 0.05), defence=max(defence, 0.05))
    return strengths, lag_for, lag_against


def precompute_strengths(matches, recent: int | None = None):
    """Compute per-team strengths once (e.g. for a whole eval window), so the
    per-match `predict` call can reuse them instead of re-scanning the training
    set for every fixture. Returns (strengths, base_average) where base_average
    is the per-match league goals estimate passed as `league_average`.
    """
    matches = list(matches)
    strengths, lg_for, lg_against = _estimate_strengths(matches, recent=recent)
    base = (lg_for + lg_against) / 2
    return strengths, base


def predict(
    home: str,
    away: str,
    matches,
    *,
    recent: int | None = None,
    rho: float = 0.0,
    league_average: float | None = None,
    strengths=None,
) -> Prediction:
    """Predict over1.5/BTTS for `home` vs `away` from historical matches.

    matches: iterable of Match. recent: per-team window. league_average:
    overall expected goals per match (defaults to observed). strengths: an
    optional precomputed {team: TeamStrength} map (see precompute_strengths)
    to avoid re-scanning the training set for every call; when given it must
    already be consistent with `matches`/`recent`.
    """
    matches = list(matches)
    if strengths is None:
        strengths, lg_for, lg_against = _estimate_strengths(matches, recent=recent)
        base_default = (lg_for + lg_against) / 2
    else:
        # Precomputed strengths carry no league-average; caller should pass
        # league_average (see precompute_strengths). Fall back to a stable base.
        base_default = 1.3

    hs = strengths.get(home, TeamStrength())
    as_ = strengths.get(away, TeamStrength())

    base = league_average if league_average is not None else base_default
    lam_home = base * hs.attack * as_.defence
    lam_away = base * as_.attack * hs.defence
    lam_home = max(lam_home, 0.02)
    lam_away = max(lam_away, 0.02)

    mat = joint_goal_matrix(lam_home, lam_away, rho)

    p_home = p_draw = p_away = 0.0
    p_over1_5 = 0.0
    p_btts = 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = mat[i][j]
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
            if i + j > 1:  # over 1.5
                p_over1_5 += p
            if i >= 1 and j >= 1:  # BTTS
                p_btts += p

    return Prediction(
        home=home,
        away=away,
        expected_home=lam_home,
        expected_away=lam_away,
        p_over1_5=p_over1_5,
        p_btts=p_btts,
        p_home=p_home,
        p_draw=p_draw,
        p_away=p_away,
    )
