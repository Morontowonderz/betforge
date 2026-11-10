"""Dixon-Coles baseline: Power-Method de-vig + bivariate Poisson scoreline matrix.

Architecture (Phase 2 pivot, Step 1):
  A. Power-Method de-vig of 1X2 odds (solves sum_i q_i^k == 1 for k).
  B. Fit a Dixon-Coles bivariate Poisson (lam_h, lam_a, rho) to the de-vigged
     1X2 probabilities -> 10x10 scoreline matrix.
  C. Marginalize that matrix to P(Over 1.5) / P(BTTS).

This is the baseline the XGBoost residual model will be trained against in
Step 2, once advanced data (xG, PPDA, referee, venue) is available.

Dependency-light: numpy + scipy only in this module. The core strength model
(`models.py`) stays stdlib; this module is the market-conditioned baseline.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.optimize import least_squares
from scipy.special import gammaln

MAX_GOALS = 10          # scoreline truncation (0..10 goals per side)
RHO_BOUNDS = (-0.3, 0.3)
LAM_BOUNDS = (0.3, 6.0)


@dataclass(frozen=True)
class DCParams:
    """Fitted Dixon-Coles parameters for one match."""
    lam_home: float
    lam_away: float
    rho: float
    fit_rmse: float
    method: str = "dixon-coles"


# --------------------------------------------------------------------------- #
# A. Power-Method de-vig
# --------------------------------------------------------------------------- #
def power_devig(odds: Sequence[float], *, tol: float = 1e-10,
                max_iter: int = 200) -> tuple[list[float], float]:
    """Power-method de-vig: find k with sum_i q_i^k == 1, q_i = 1/odds_i.

    Newton iteration on k. Returns (probs, k). Falls back to the
    multiplicative method (k=1) when any implied probability is
    non-finite/<=0 or the solver diverges.

    The power method is preferred over proportional for heavy favourites:
    it assigns more of the margin to the longshot, which matches how
    bookmakers actually build 1X2 prices.
    """
    raw = [float(o) for o in odds]
    if len(raw) != 3 or not all(math.isfinite(o) and o > 1.0 for o in raw):
        # Degenerate market (missing/zero/negative odds): multiplicative on
        # whatever finite implied probabilities exist, else uniform.
        inv = np.asarray([1.0 / o if (math.isfinite(o) and o > 1.0) else np.nan
                          for o in raw], dtype=float)
        if np.all(np.isfinite(inv)) and np.any(inv > 0):
            total = inv.sum()
            return [float(x / total) for x in inv], 1.0
        return [1.0 / len(raw)] * len(raw), 1.0
    inv = np.asarray([1.0 / o for o in raw], dtype=float)
    # NOTE: do NOT normalise. The solver needs the raw over-round (sum > 1)
    # to be visible; normalising makes sum q^k == 1 at k=1 and no-ops.
    q = inv
    k = 1.0
    for _ in range(max_iter):
        qk = q ** k
        f = float(qk.sum()) - 1.0
        if abs(f) < tol:
            break
        df = float((qk * np.log(q)).sum())  # d/dk of sum q^k
        if abs(df) < 1e-14:
            break
        k -= f / df
        if k <= 0 or not math.isfinite(k):
            return [float(x) for x in (q / q.sum())], 1.0  # degenerate -> multiplicative
    probs = q ** k
    probs = probs / probs.sum()
    return [float(p) for p in probs], float(k)


def multiplicative_devig(odds: Sequence[float]) -> list[float]:
    """Proportional de-vig (the baseline the power method improves on)."""
    inv = np.asarray([1.0 / float(o) for o in odds], dtype=float)
    total = inv.sum()
    return [float(x / total) for x in inv]


# --------------------------------------------------------------------------- #
# B. Dixon-Coles bivariate Poisson matrix
# --------------------------------------------------------------------------- #
def dc_matrix(lam_h: float, lam_a: float, rho: float,
              max_goals: int = MAX_GOALS) -> np.ndarray:
    """P(home=i, away=j) with Dixon-Coles rho correction on 0-0/0-1/1-0/1-1.

    tau corrections (Coles 1997):
      (0,0): 1 - lam_h*lam_a*rho ; (0,1): 1 + lam_h*rho ;
      (1,0): 1 + lam_a*rho      ; (1,1): 1 - rho
    Renormalized so the matrix is a valid distribution.
    """
    lam_h = max(float(lam_h), 1e-6)
    lam_a = max(float(lam_a), 1e-6)
    k = np.arange(max_goals + 1)
    log_ph = -lam_h + k * np.log(lam_h) - gammaln(k + 1)
    log_pa = -lam_a + k * np.log(lam_a) - gammaln(k + 1)
    joint = np.exp(log_ph[:, None] + log_pa[None, :])
    joint[0, 0] *= 1.0 - lam_h * lam_a * rho
    joint[0, 1] *= 1.0 + lam_h * rho
    joint[1, 0] *= 1.0 + lam_a * rho
    joint[1, 1] *= 1.0 - rho
    joint = np.clip(joint, 0.0, None)
    total = joint.sum()
    if total <= 0:
        raise ValueError("dc_matrix degenerated to zero mass")
    return joint / total


def _matrix_1x2(J: np.ndarray) -> tuple[float, float, float]:
    i = np.arange(J.shape[0])
    j = np.arange(J.shape[1])
    p_home = float(J[i[:, None] > j[None, :]].sum())
    p_draw = float(J[i[:, None] == j[None, :]].sum())
    p_away = float(J[i[:, None] < j[None, :]].sum())
    return p_home, p_draw, p_away


def fit_dc(probs: Sequence[float], *, starts: int = 8,
           max_goals: int = MAX_GOALS) -> DCParams:
    """Fit (lam_h, lam_a, rho) so the DC 1X2 probs match de-vigged (ph,pd,pa).

    Multi-start least_squares on (log lam_h, log lam_a, rho); rho bounded to
    RHO_BOUNDS, lambdas to LAM_BOUNDS. Returns the best fit and its RMSE.
    """
    ph, pd_, pa = (float(x) for x in probs)
    if not (np.isfinite([ph, pd_, pa]).all() and ph > 0 and pd_ > 0 and pa > 0):
        return DCParams(1.3, 1.1, -0.1, float("inf"), "fallback")

    def resid(x: np.ndarray) -> np.ndarray:
        lh, la, rho = math.exp(x[0]), math.exp(x[1]), float(x[2])
        m_h, m_d, m_a = _matrix_1x2(dc_matrix(lh, la, rho, max_goals))
        return np.array([m_h - ph, m_d - pd_, m_a - pa])

    lo = [math.log(LAM_BOUNDS[0]), math.log(LAM_BOUNDS[0]), RHO_BOUNDS[0]]
    hi = [math.log(LAM_BOUNDS[1]), math.log(LAM_BOUNDS[1]), RHO_BOUNDS[1]]
    best = None
    grid = np.linspace(0.8, 2.2, starts)
    for th in grid:
        for ta in grid:
            x0 = np.array([math.log(th), math.log(ta), -0.1])
            try:
                r = least_squares(resid, x0, bounds=(lo, hi), max_nfev=200)
            except Exception:  # noqa: BLE001, S112 - multi-start solver: skip diverged starts
                continue
            if best is None or r.cost < best.cost:
                best = r
    if best is None:
        return DCParams(1.3, 1.1, -0.1, float("inf"), "fallback")
    lh, la, rho = math.exp(best.x[0]), math.exp(best.x[1]), float(best.x[2])
    return DCParams(lh, la, rho, float(np.sqrt(np.mean(best.fun ** 2))), "dixon-coles")


@lru_cache(maxsize=8192)
def _cached_matrix(lam_h: float, lam_a: float, rho: float,
                   max_goals: int) -> tuple[float, ...]:
    return tuple(dc_matrix(lam_h, lam_a, rho, max_goals).ravel())


def marginalize(J: np.ndarray) -> dict[str, float]:
    """Marginalize a scoreline matrix to the markets BetForge targets.

    Over 2.5 = P(home + away >= 3). The 1-1 scoreline sits on the DC tau
    boundary, so O2.5 is preferred over O1.5 for proxy work (owner mandate
    2026-11-06): the boundary cells are inside the O2.5 region, not on it.
    """
    over15 = 1.0 - J[0, 0] - J[0, 1] - J[1, 0]
    # P(total >= 3) = 1 - P(total <= 2). The total<=2 region is exactly the
    # six cells (0,0),(0,1),(0,2),(1,0),(1,1),(2,0) -- including (1,1), the
    # DC tau-boundary cell that makes O1.5 proxying unsafe.
    over25 = float(1.0 - J[0, 0] - J[0, 1] - J[0, 2]
                   - J[1, 0] - J[1, 1] - J[2, 0])
    btts = float(J[1:, 1:].sum())
    p_home, p_draw, p_away = _matrix_1x2(J)
    return {
        "p_over15": float(over15),
        "p_over25": over25,
        "p_btts": btts,
        "p_home": p_home,
        "p_draw": p_draw,
        "p_away": p_away,
    }


def _over25_of_matrix(lh: float, la: float, rho: float, max_goals: int) -> float:
    J = dc_matrix(lh, la, rho, max_goals)
    return float(1.0 - J[0, 0] - J[0, 1] - J[0, 2]
                 - J[1, 0] - J[1, 1] - J[2, 0])


# --------------------------------------------------------------------------- #
# D. Likelihood fit (scipy L-BFGS-B) -- Stage-1 target for the two-stage model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DCFit:
    """Fitted global Dixon-Coles parameters from a likelihood fit."""
    lam_home: float
    lam_away: float
    rho: float
    neg_log_likelihood: float
    method: str
    n_matches: int

    def over25(self) -> float:
        """P(Over 2.5) from the fitted global matrix."""
        return _over25_of_matrix(self.lam_home, self.lam_away, self.rho, MAX_GOALS)

    def as_dict(self) -> dict:
        return {
            "lambda_home": round(self.lam_home, 4),
            "lambda_away": round(self.lam_away, 4),
            "rho": round(self.rho, 4),
            "p_over25_dc": round(self.over25(), 4),
            "neg_log_likelihood": round(self.neg_log_likelihood, 4),
            "n_matches": self.n_matches,
            "method": self.method,
        }


def dc_logpmf(i: int, j: int, lam_h: float, lam_a: float, rho: float) -> float:
    """Dixon-Coles log P(home=i, away=j) with the tau correction."""
    from scipy.stats import poisson

    logp = poisson.logpmf(i, lam_h) + poisson.logpmf(j, lam_a)
    if i == 0 and j == 0:
        logp += np.log(max(1.0 - lam_h * lam_a * rho, 1e-12))
    elif i == 0 and j == 1:
        logp += np.log(max(1.0 + lam_h * rho, 1e-12))
    elif i == 1 and j == 0:
        logp += np.log(max(1.0 + lam_a * rho, 1e-12))
    elif i == 1 and j == 1:
        logp += np.log(max(1.0 - rho, 1e-12))
    return float(logp)


def fit_dc_model(df, *, max_goals: int = MAX_GOALS) -> DCFit:
    """Fit (lambda_home, lambda_away, rho) by maximum likelihood on actual goals.

    Owner spec 2026-11-06: scipy.optimize.minimize with L-BFGS-B, minimising
    the negative log-likelihood of the observed FTHG/FTAG under the DC pmf.
    Team-specific attack/defence is intentionally omitted (global lambdas) --
    this is the Stage-1 baseline that the XGBoost lambdas will later replace.

    Returns a DCFit with the fitted parameters and fit diagnostics.
    """
    from scipy.optimize import minimize

    hg = np.asarray(df["home_goals"], dtype=int)
    ag = np.asarray(df["away_goals"], dtype=int)
    if len(hg) == 0:
        return DCFit(1.3, 1.1, -0.1, float("inf"), "fallback", 0)

    def neg_ll(x: np.ndarray) -> float:
        lh, la, rho = float(x[0]), float(x[1]), float(x[2])
        if lh <= 0 or la <= 0:
            return 1e9
        total = 0.0
        for i, j in zip(hg, ag):
            total -= dc_logpmf(int(i), int(j), lh, la, rho)
        return total / len(hg)

    res = minimize(
        neg_ll,
        x0=np.array([hg.mean() or 1.3, ag.mean() or 1.1, -0.1]),
        method="L-BFGS-B",
        bounds=[(0.2, 4.0), (0.2, 4.0), (-0.5, 0.5)],
    )
    lh, la, rho = float(res.x[0]), float(res.x[1]), float(res.x[2])
    return DCFit(lh, la, rho, float(res.fun), "mle-lbfgsb", len(hg))


def fit_dc_to_over25(p_over25_market: float, probs_1x2: Sequence[float] | None = None,
                     *, max_goals: int = MAX_GOALS, starts: int = 8) -> DCParams:
    """Fit (lam_h, lam_a, rho) to the market's de-vigged P(Over 2.5).

    Primary target is the real O/U 2.5 closing line (owner mandate). When the
    de-vigged 1X2 probabilities are supplied they are used as a regulariser so
    the fitted lambdas stay consistent with the match outcome market.

    Returns DCParams with fit_rmse measured against the O2.5 target.
    """
    target = float(p_over25_market)
    if not (np.isfinite(target) and 0.0 < target < 1.0):
        return DCParams(1.3, 1.1, -0.1, float("inf"), "fallback")

    def resid(x: np.ndarray) -> np.ndarray:
        lh, la, rho = math.exp(x[0]), math.exp(x[1]), float(x[2])
        pred = _over25_of_matrix(lh, la, rho, max_goals)
        out = [pred - target]
        if probs_1x2 is not None:
            m_h, m_d, m_a = _matrix_1x2(dc_matrix(lh, la, rho, max_goals))
            out += [m_h - probs_1x2[0], m_d - probs_1x2[1], m_a - probs_1x2[2]]
        return np.array(out)

    lo = [math.log(LAM_BOUNDS[0]), math.log(LAM_BOUNDS[0]), RHO_BOUNDS[0]]
    hi = [math.log(LAM_BOUNDS[1]), math.log(LAM_BOUNDS[1]), RHO_BOUNDS[1]]
    best = None
    grid = np.linspace(0.8, 2.2, starts)
    for th in grid:
        for ta in grid:
            x0 = np.array([math.log(th), math.log(ta), -0.1])
            try:
                r = least_squares(resid, x0, bounds=(lo, hi), max_nfev=200)
            except Exception:  # noqa: BLE001, S112 - multi-start solver: skip diverged starts
                continue
            if best is None or r.cost < best.cost:
                best = r
    if best is None:
        return DCParams(1.3, 1.1, -0.1, float("inf"), "fallback")
    lh, la, rho = math.exp(best.x[0]), math.exp(best.x[1]), float(best.x[2])
    rmse = abs(_over25_of_matrix(lh, la, rho, max_goals) - target)
    return DCParams(lh, la, rho, float(rmse), "dixon-coles-o25")


# --------------------------------------------------------------------------- #
# C. One-shot: odds -> DC params -> market probabilities
# --------------------------------------------------------------------------- #
def predict_from_odds(odds: Sequence[float], *,
                      over25_odds: float | None = None) -> tuple[dict[str, float], DCParams]:
    """Full pipeline: 1X2 decimal odds -> DC baseline probabilities.

    When `over25_odds` (a real O/U 2.5 line) is supplied, the DC parameters
    are fitted to that line instead of the 1X2 triple -- the owner-mandated
    path now that real closing lines exist. Otherwise the 1X2 fit is used.

    Returns (market_probs, fitted_params). Falls back gracefully when odds are
    missing/invalid (params marked method='fallback').
    """
    if len(odds) != 3 or not all(math.isfinite(float(o)) and float(o) > 1.0 for o in odds):
        params = DCParams(1.3, 1.1, -0.1, float("inf"), "fallback")
        J = dc_matrix(params.lam_home, params.lam_away, params.rho)
        return marginalize(J), params

    if over25_odds is not None and math.isfinite(float(over25_odds)) and float(over25_odds) > 1.0:
        # A single O/U leg is not a market -- use predict_from_ou() with both legs.
        raise ValueError("predict_from_odds needs both O/U legs; use predict_from_ou()")

    probs, k = power_devig(odds)
    params = fit_dc(probs)
    J = dc_matrix(params.lam_home, params.lam_away, params.rho)
    out = marginalize(J)
    out["devig_k"] = k
    return out, params


def predict_from_ou(over_odds: float, under_odds: float, *,
                    odds_1x2: Sequence[float] | None = None) -> tuple[dict[str, float], DCParams]:
    """Fit the DC baseline from a REAL Over/Under 2.5 pair (owner-mandated path).

    De-vigs the two-way O/U market (multiplicative -- the standard for a
    two-way line), fits (lam_h, lam_a, rho) to that probability, optionally
    regularised by the de-vigged 1X2 triple, then marginalizes the 10x10
    matrix to every market BetForge serves.
    """
    over, under = float(over_odds), float(under_odds)
    if not (math.isfinite(over) and math.isfinite(under) and over > 1.0 and under > 1.0):
        params = DCParams(1.3, 1.1, -0.1, float("inf"), "fallback")
        J = dc_matrix(params.lam_home, params.lam_away, params.rho)
        return marginalize(J), params

    inv_o, inv_u = 1.0 / over, 1.0 / under
    total = inv_o + inv_u
    p_over25 = inv_o / total

    probs_1x2 = None
    if odds_1x2 is not None and len(odds_1x2) == 3 and all(math.isfinite(float(o)) and float(o) > 1.0 for o in odds_1x2):
        probs_1x2, _ = power_devig(odds_1x2)

    params = fit_dc_to_over25(p_over25, probs_1x2)
    J = dc_matrix(params.lam_home, params.lam_away, params.rho)
    out = marginalize(J)
    out["p_over25_market"] = float(p_over25)
    out["devig_k"] = 1.0
    return out, params
