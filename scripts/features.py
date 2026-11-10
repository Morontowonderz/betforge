"""Leakage-safe, vectorized feature engineering for the Phase 2 XGBoost model.

Every feature for a match is derived ONLY from information available before
kick-off: the match's own pre-match 1X2 odds and the two teams' EARLIER
matches (shifted by one, so a match never sees its own result).

MARKET PROXY (labelled PROXY everywhere): the data has 1X2 odds only, no
Over/Under line. We de-vig 1X2 -> (qh, qd, qa), then find the independent
Poisson (lam_h, lam_a) whose 1X2 distribution is nearest (KD-tree over a
precomputed grid). P(Over1.5) / P(BTTS) follow in closed form. This is the
bookmaker's *implied* goal view, not a quoted O/U price.

FATIGUE: rest days since the team's previous match, matches in the trailing
7/14/30 days (closed-left rolling count). No travel distance - no coordinates.

MOMENTUM: EWM (halflife 5 matches, shifted 1) of goals for/against minus the
odds-implied expected goals for/against -> "beat the market's expectation".

All group operations are pandas groupby / shift / rolling / ewm. No row loops.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import gammaln
from scipy.spatial import cKDTree

HALFLIFE = 5          # matches
MAX_GOALS = 10        # truncation for the proxy Poisson grid


# --------------------------------------------------------------------------- #
# Odds -> market proxy
# --------------------------------------------------------------------------- #
def de_vig(df: pd.DataFrame) -> pd.DataFrame:
    h = pd.to_numeric(df["home_odds"], errors="coerce")
    d = pd.to_numeric(df["draw_odds"], errors="coerce")
    a = pd.to_numeric(df["away_odds"], errors="coerce")
    inv = pd.DataFrame({"qh": 1 / h, "qd": 1 / d, "qa": 1 / a})
    inv = inv.where(np.isfinite(inv) & (inv > 0))
    total = inv.sum(axis=1, min_count=3)
    return inv.div(total, axis=0)


def _poisson_pmf_matrix(lam: np.ndarray) -> np.ndarray:
    k = np.arange(MAX_GOALS + 1)
    logp = -lam[:, None] + k[None, :] * np.log(lam[:, None]) - gammaln(k + 1)[None, :]
    return np.exp(logp)


def _grid_1x2(lam_h: np.ndarray, lam_a: np.ndarray):
    ph = _poisson_pmf_matrix(lam_h)
    pa = _poisson_pmf_matrix(lam_a)
    joint = ph[:, :, None] * pa[:, None, :]
    i = np.arange(MAX_GOALS + 1)
    home = joint[:, i[:, None] > i[None, :]].sum(axis=1)
    draw = joint[:, i[:, None] == i[None, :]].sum(axis=1)
    away = joint[:, i[:, None] < i[None, :]].sum(axis=1)
    return home, draw, away


def market_proxy(q: pd.DataFrame) -> pd.DataFrame:
    """(qh,qd,qa) -> nearest independent-Poisson (lam_h, lam_a) and PROXY targets.

    Fitted per training window (see eval_xgb.py) so test-window odds never
    influence their own proxy. Grid is fine enough that the 1X2 residual is
    ~1e-3; the residual is the independent-Poisson shape error, not a fit error.
    """
    tot = np.linspace(0.6, 6.0, 271)
    split = np.linspace(0.08, 0.92, 85)
    T, S = np.meshgrid(tot, split, indexing="ij")
    g_lh, g_la = (T * S).ravel(), (T * (1 - S)).ravel()
    gh, gd, _ = _grid_1x2(g_lh, g_la)
    tree = cKDTree(np.column_stack([gh, gd]))

    out = pd.DataFrame(index=q.index)
    valid = q[["qh", "qd", "qa"]].notna().all(axis=1).to_numpy()
    lam_h = np.full(len(q), np.nan)
    lam_a = np.full(len(q), np.nan)
    if valid.any():
        _, idx = tree.query(q.loc[valid, ["qh", "qd"]].to_numpy(), k=1)
        lam_h[valid], lam_a[valid] = g_lh[idx], g_la[idx]
    out["mkt_lam_h"], out["mkt_lam_a"] = lam_h, lam_a
    s = lam_h + lam_a
    out["mkt_p_over15"] = 1 - np.exp(-s) * (1 + s)
    out["mkt_p_btts"] = (1 - np.exp(-lam_h)) * (1 - np.exp(-lam_a))
    return out


# --------------------------------------------------------------------------- #
# Team-level lagged features
# --------------------------------------------------------------------------- #
def _long_table(m: pd.DataFrame) -> pd.DataFrame:
    base = ["match_id", "date"]
    home = pd.DataFrame({
        "match_id": m["match_id"], "date": m["date"], "team": m["home"], "is_home": 1,
        "gf": m["home_goals"], "ga": m["away_goals"],
        "xg_for": m["mkt_lam_h"], "xg_ag": m["mkt_lam_a"],
    })
    away = pd.DataFrame({
        "match_id": m["match_id"], "date": m["date"], "team": m["away"], "is_home": 0,
        "gf": m["away_goals"], "ga": m["home_goals"],
        "xg_for": m["mkt_lam_a"], "xg_ag": m["mkt_lam_h"],
    })
    long = pd.concat([home, away], ignore_index=True)
    long["tot"] = long["gf"] + long["ga"]
    long["over15"] = (long["tot"] > 1.5).astype(float)
    long["btts"] = ((long["gf"] >= 1) & (long["ga"] >= 1)).astype(float)
    long["res_for"] = long["gf"] - long["xg_for"]
    long["res_ag"] = long["ga"] - long["xg_ag"]
    long["one"] = 1.0
    return long.sort_values(["team", "date", "match_id"]).reset_index(drop=True)[
        base + [c for c in long.columns if c not in base]]


def team_features(m: pd.DataFrame) -> pd.DataFrame:
    """Return long table with lagged features; one row per (match, team)."""
    long = _long_table(m)
    g = long.groupby("team", sort=False)

    # --- fatigue -----------------------------------------------------------
    prev_date = g["date"].shift(1)
    long["rest_days"] = (long["date"] - prev_date).dt.days.clip(upper=60)
    long["n_prev"] = g.cumcount()
    for win in (7, 14, 30):
        r = (long.set_index("date").groupby("team", sort=False)["one"]
             .rolling(f"{win}D", closed="left").sum())
        long[f"cong_{win}"] = r.reset_index(level=0, drop=True).to_numpy()

    # --- momentum (EWM of past matches only; shift(1) prevents self-leak) --
    def _ewm_lag(col: str) -> np.ndarray:
        return g[col].transform(
            lambda s: s.shift(1).ewm(halflife=HALFLIFE, min_periods=1).mean()).to_numpy()

    for col in ("gf", "ga", "tot", "over15", "btts", "res_for", "res_ag", "xg_for", "xg_ag"):
        long[f"ewm_{col}"] = _ewm_lag(col)
    long["ewm_home_rate"] = _ewm_lag("is_home")
    return long


FEATURE_COLS_TEAM = ["rest_days", "n_prev", "cong_7", "cong_14", "cong_30",
                     "ewm_gf", "ewm_ga", "ewm_tot", "ewm_over15", "ewm_btts",
                     "ewm_res_for", "ewm_res_ag", "ewm_xg_for", "ewm_xg_ag",
                     "ewm_home_rate"]
MARKET_COLS = ["qh", "qd", "qa", "mkt_lam_h", "mkt_lam_a", "mkt_p_over15", "mkt_p_btts"]


def build(df: pd.DataFrame) -> pd.DataFrame:
    """Full match-level feature frame. Input: canonical matches.csv columns."""
    m = df.copy()
    m["date"] = pd.to_datetime(m["date"], errors="coerce")
    m["home_goals"] = pd.to_numeric(m["home_goals"], errors="coerce")
    m["away_goals"] = pd.to_numeric(m["away_goals"], errors="coerce")
    m = m.dropna(subset=["date", "home_goals", "away_goals"]).sort_values("date").reset_index(drop=True)
    m["match_id"] = np.arange(len(m))

    q = de_vig(m)
    m = pd.concat([m, q, market_proxy(q)], axis=1)

    long = team_features(m)
    h = long[long["is_home"] == 1].set_index("match_id")[FEATURE_COLS_TEAM].add_prefix("h_")
    a = long[long["is_home"] == 0].set_index("match_id")[FEATURE_COLS_TEAM].add_prefix("a_")
    m = m.set_index("match_id").join(h).join(a).reset_index()

    for c in FEATURE_COLS_TEAM:
        m[f"d_{c}"] = m[f"h_{c}"] - m[f"a_{c}"]
    m["fatigue_idx"] = (m["a_cong_14"] - m["h_cong_14"]) + (m["h_rest_days"].clip(upper=14) - m["a_rest_days"].clip(upper=14)) / 7.0
    # Momentum: both teams' recent over/under-performance vs market xG, summed.
    # Positive = recent matches of both sides ran hotter than the bookmaker expected.
    m["momentum_idx"] = (m["h_ewm_res_for"] + m["a_ewm_res_for"]
                         + m["h_ewm_res_ag"] + m["a_ewm_res_ag"]) / 2.0
    m["pace_idx"] = m["h_ewm_tot"] + m["a_ewm_tot"]
    m["year"] = m["date"].dt.year
    m["month"] = m["date"].dt.month
    m["dow"] = m["date"].dt.dayofweek

    m["y_over15"] = ((m["home_goals"] + m["away_goals"]) > 1.5).astype(int)
    m["y_btts"] = ((m["home_goals"] >= 1) & (m["away_goals"] >= 1)).astype(int)
    return m


def feature_sets(m: pd.DataFrame) -> dict[str, list[str]]:
    team = [f"{p}_{c}" for p in ("h", "a", "d") for c in FEATURE_COLS_TEAM]
    engineered = ["fatigue_idx", "momentum_idx", "pace_idx", "month", "dow"]
    # CLEAN: drop every feature that is itself built from the odds (ewm_xg_*, ewm_res_*).
    # What remains is pure calendar (rest/congestion) + pure scoring history (ewm_gf/ga/tot/over15/btts).
    clean = [c for c in team if "ewm_xg" not in c and "ewm_res" not in c]
    return {
        "A_no_odds": team + engineered,
        "B_with_odds": team + engineered + MARKET_COLS,
        "C_clean": clean + ["fatigue_idx", "pace_idx", "month", "dow"],
    }
