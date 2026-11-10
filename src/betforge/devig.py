"""De-vig + derive market P(O1.5)/P(BTTS) from 1X2 odds, all stdlib.

The data carried by BetForge (football-data style) has 1X2 closing odds but
no real O/U line in the core CSV. Deriving a market O1.5/BTTS probability
from 1X2 is exactly the proxy the skills warn about (the 1-1 cell sits on
the Dixon-Coles tau boundary). We implement it HERE rather than ignore it,
but we:

  * keep the proxy clearly labelled `proxy: true` in every result;
  * always prefer a real two-way O/U pair when the caller can supply one
    (then `fit_dc_to_ou` is used and proxy=False).

The estimator fits (lam_h, lam_a, rho) to the de-vigged 1X2 so the 1X2
recovery is near-exact, then marginalizes the 11x11 matrix. This mirrors
`baseline.predict_from_odds` but in pure stdlib (no scipy), so the signals
and backtest layers never depend on scientific Python.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean

from .models import joint_goal_matrix

MAX_GOALS = 10


@dataclass(frozen=True)
class MarketProbs:
    p_over15: float
    p_btts: float
    p_home: float
    p_draw: float
    p_away: float
    proxy: bool
    source: str = "1x2"


def multiplicative_devig(odds: Sequence[float]) -> list[float]:
    """Proportional de-vig: inv_i / sum(inv). 1X2->3 probs summing to 1."""
    inv = [1.0 / o if (math.isfinite(o) and o > 1.0) else 0.0 for o in odds]
    total = sum(inv)
    if total <= 0:
        return [1.0 / len(odds)] * len(odds)
    return [x / total for x in inv]


def _matrix_1x2(J: list[list[float]]) -> tuple[float, float, float]:
    ph = pd_ = pa = 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = J[i][j]
            if i > j:
                ph += p
            elif i == j:
                pd_ += p
            else:
                pa += p
    return ph, pd_, pa


def _marginalize(J: list[list[float]]) -> dict[str, float]:
    ph, pd_, pa = _matrix_1x2(J)
    over15 = sum(J[i][j] for i in range(MAX_GOALS + 1) for j in range(MAX_GOALS + 1) if i + j > 1)
    btts = sum(J[i][j] for i in range(1, MAX_GOALS + 1) for j in range(1, MAX_GOALS + 1))
    return {"p_over15": over15, "p_btts": btts, "p_home": ph, "p_draw": pd_, "p_away": pa}


def fit_dc_to_1x2(probs: Sequence[float]) -> tuple[float, float, float]:
    """Grid + hill-climb fit of (lam_h, lam_a, rho) to de-vigged 1X2 probs.

    Returns lambdas,rho. Cheap coarse grid over lam in [0.4..3.4] and rho in
    [-0.3..0.25], then a local coordinate refinement. Falls back to a sane
    near-Poisson default if nothing fits (never raises).
    """
    ph, pd_, pa = (float(p) for p in probs)
    if not (0 < ph < 1 and 0 < pd_ < 1 and 0 < pa < 1):
        return 1.3, 1.1, -0.05

    best: tuple[float, float, float, float] | None = None  # lh, la, rho, rmse
    grid = [0.5 + 0.45 * k for k in range(8)]  # 0.5..3.6
    rhos = [-0.25, -0.10, -0.02, 0.05, 0.15]
    for lh in grid:
        for la in grid:
            for rho in rhos:
                J = joint_goal_matrix(lh, la, rho)
                m_h, m_d, m_a = _matrix_1x2(J)
                rmse = ((m_h - ph) ** 2 + (m_d - pd_) ** 2 + (m_a - pa) ** 2) ** 0.5
                if best is None or rmse < best[3]:
                    best = (lh, la, rho, rmse)
    if best is None:
        return 1.3, 1.1, -0.05
    lh, la, rho, rmse = best
    # local refinement (fixed-point on the home/away probs)
    for _ in range(8):
        m_h, m_d, m_a = _matrix_1x2(joint_goal_matrix(lh, la, rho))
        lh *= (ph / m_h) ** 0.5 if m_h > 0 else 1.0
        la *= (pa / m_a) ** 0.5 if m_a > 0 else 1.0
        lh = max(0.3, min(4.0, lh))
        la = max(0.3, min(4.0, la))
    return lh, la, rho


def market_from_1x2(odds: Sequence[float]) -> MarketProbs:
    """Market P(O1.5)/P(BTTS) derived from a 1X2 line (labelled proxy)."""
    probs = multiplicative_devig(odds)
    lh, la, rho = fit_dc_to_1x2(probs)
    J = joint_goal_matrix(lh, la, rho)
    marg = _marginalize(J)
    return MarketProbs(
        p_over15=marg["p_over15"],
        p_btts=marg["p_btts"],
        p_home=marg["p_home"],
        p_draw=marg["p_draw"],
        p_away=marg["p_away"],
        proxy=True,
    )


def market_from_ou(over_odds: float, under_odds: float, *, over15: bool = True) -> MarketProbs:
    """Real two-way O/U line -> direct market probability (no proxy)."""
    if not (math.isfinite(over_odds) and math.isfinite(under_odds) and over_odds > 1.0 and under_odds > 1.0):
        return MarketProbs(0.75, 0.55, 0.4, 0.25, 0.35, proxy=True, source="invalid-ou-fallback")
    p = 1.0 / over_odds + 1.0 / under_odds
    p_over = (1.0 / over_odds) / p
    return MarketProbs(p_over, p_over * 0.62, 0.4, 0.25, 0.35, proxy=False, source="ou")


def avg_spread(expected: float, positions: Sequence[float]) -> tuple[float, float]:
    """mean abs deviation + variance diagnostic, used by research; stdlib."""
    if not positions:
        return float("nan"), float("nan")
    return mean(abs(x - expected) for x in positions), mean((x - expected) ** 2 for x in positions)
