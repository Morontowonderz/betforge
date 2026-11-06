"""Vectorized chronological walk-forward out-of-sample club backtest (pandas/numpy).

Everything the old pure-Python eval did per-match is now an array operation:
- strengths computed ONCE per window via pandas groupby (no per-fixture rescan)
- probabilities from closed-form Poisson math, vectorized over the whole test set:
      P(Over1.5) = 1 - exp(-(lam_h+lam_a)) * (1 + lam_h + lam_a)
      P(BTTS)    = (1 - exp(-lam_h)) * (1 - exp(-lam_a))
  (independent goals; the joint collapses to these closed forms, no tensor here)

ODDS AS FEATURES (owner directive 2026-11-06): the xgabora odds columns
(home_odds/draw_odds/away_odds) are de-vigged (margin removed) into implied
probabilities and blended into the per-team lambda via MARKET_WEIGHT. This is
the value-betting direction: the model now conditions on the market, not just
raw historical strength.

Strict OOS: for test year Y the model trains only on matches with date < Y.

Run:  .venv/bin/python scripts/eval_model.py
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "matches.csv"
TEST_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
MARKET_WEIGHT = 0.5  # blend: historical strength vs market (0..1)


def _p_over1_5(lam_h: np.ndarray, lam_a: np.ndarray) -> np.ndarray:
    s = lam_h + lam_a
    return 1.0 - np.exp(-s) * (1.0 + s)


def _p_btts(lam_h: np.ndarray, lam_a: np.ndarray) -> np.ndarray:
    return (1.0 - np.exp(-lam_h)) * (1.0 - np.exp(-lam_a))


def de_vig(df: pd.DataFrame) -> pd.DataFrame:
    """Remove the bookmaker margin from 1X2 decimal odds -> implied probs.

    Rows missing an odd produce zeros here; their lam blend falls back to pure
    historical strength (weight redirected to 1-W) rather than corrupting.
    """
    h = pd.to_numeric(df["home_odds"], errors="coerce")
    d = pd.to_numeric(df["draw_odds"], errors="coerce")
    a = pd.to_numeric(df["away_odds"], errors="coerce")
    inv = pd.DataFrame({"h": 1 / h, "d": 1 / d, "a": 1 / a})
    total = inv.sum(axis=1).replace(0, np.nan)
    probs = inv.div(total, axis=0)
    return probs.rename(columns={"h": "qh", "d": "qd", "a": "qa"})


def team_strengths(train: pd.DataFrame):
    """Return (attack, defence, league_for, league_against) from training goals."""
    gf = train.groupby("home")["home_goals"].mean()
    ga = train.groupby("home")["away_goals"].mean()  # home concedes away's score
    league_for = float(train["home_goals"].mean())
    league_against = float(train["away_goals"].mean())
    lag_for = max(league_for, 0.1)
    lag_against = max(league_against, 0.1)
    attack = (gf / lag_for).to_dict()
    defence = (ga / lag_against).to_dict()
    return attack, defence, lag_for, lag_against


def brier(preds: np.ndarray, actuals: np.ndarray) -> float:
    return float(np.mean((preds - actuals) ** 2))


def main() -> None:
    t0 = time.time()
    df = pd.read_csv(DATA)
    for c in ("home", "away", "date"):
        df[c] = df[c].astype(str)
    df["home_goals"] = pd.to_numeric(df["home_goals"], errors="coerce")
    df["away_goals"] = pd.to_numeric(df["away_goals"], errors="coerce")
    df = df.dropna(subset=["home_goals", "away_goals", "date"]).reset_index(drop=True)
    print(f"Loaded {len(df)} dated club matches from {DATA.name}")
    print(f"Date range: {df['date'].min()} .. {df['date'].max()}")
    print(f"market_weight (odds blend) = {MARKET_WEIGHT}")

    pool_over_pred, pool_btts_pred = [], []
    pool_over_act, pool_btts_act = [], []

    header = (f"{'window':<22}{'n':>7}{'over_freq':>10}{'over_pred':>10}"
              f"{'brier_ov':>9}{'log_ov':>8}{'btts_freq':>10}{'btts_pred':>10}"
              f"{'brier_bt':>9}{'log_bt':>8}")
    print("\n" + header)
    print("-" * len(header))

    results = []
    for yr in TEST_YEARS:
        cut, nxt = f"{yr}-01-01", f"{yr + 1}-01-01"
        train = df[df["date"] < cut]
        test = df[(df["date"] >= cut) & (df["date"] < nxt)]
        if len(test) == 0:
            continue

        attack, defence, lag_for, lag_against = team_strengths(train)
        base = (lag_for + lag_against) / 2.0

        # Historical-strength lambdas (vectorized over the test set).
        h_att = test["home"].map(attack).fillna(1.0).to_numpy()
        a_att = test["away"].map(attack).fillna(1.0).to_numpy()
        h_def = test["away"].map(defence).fillna(1.0).to_numpy()
        a_def = test["home"].map(defence).fillna(1.0).to_numpy()
        lam_h = base * h_att * h_def
        lam_a = base * a_att * a_def

        # ODDS AS FEATURES: market-implied strength blend.
        probs = de_vig(test[["home_odds", "draw_odds", "away_odds"]])
        qh, qa = probs["qh"].to_numpy(), probs["qa"].to_numpy()
        with np.errstate(invalid="ignore", divide="ignore"):
            mkt_h = np.where((qh + qa) > 0, qh / np.maximum(qh + qa, 1e-12), 0.5)
            mkt_a = 1.0 - mkt_h
        valid = np.isfinite(mkt_h)
        # Market-factor per side: odds-implied home split relative to neutral 0.5.
        mkt_factor_h = np.where(valid, mkt_h / 0.5, 1.0)
        mkt_factor_a = np.where(valid, mkt_a / 0.5, 1.0)
        # Blend: 1.0 factor = pure historical; market tilts when odds disagree.
        fh = (1 - MARKET_WEIGHT) * 1.0 + MARKET_WEIGHT * mkt_factor_h
        fa = (1 - MARKET_WEIGHT) * 1.0 + MARKET_WEIGHT * mkt_factor_a
        lam_h = base * h_att * h_def * fh
        lam_a = base * a_att * a_def * fa

        lam_h = np.maximum(lam_h, 0.02)
        lam_a = np.maximum(lam_a, 0.02)

        p_over = _p_over1_5(lam_h, lam_a)
        p_btts = _p_btts(lam_h, lam_a)
        act_over = (test["home_goals"].to_numpy() + test["away_goals"].to_numpy()) > 1.5
        act_btts = (test["home_goals"].to_numpy() >= 1) & (test["away_goals"].to_numpy() >= 1)

        n = len(test)
        over_freq, over_pred = float(act_over.mean()), float(p_over.mean())
        btts_freq, btts_pred = float(act_btts.mean()), float(p_btts.mean())
        bo, bb = brier(p_over, act_over.astype(float)), brier(p_btts, act_btts.astype(float))
        log_ov = math.log(over_freq / over_pred) if over_freq > 0 and over_pred > 0 else float("nan")
        log_bt = math.log(btts_freq / btts_pred) if btts_freq > 0 and btts_pred > 0 else float("nan")
        results.append({"yr": yr, "n": n, "over_freq": over_freq, "over_pred": over_pred,
                        "brier_ov": bo, "log_ov": log_ov, "btts_freq": btts_freq,
                        "btts_pred": btts_pred, "brier_bt": bb, "log_bt": log_bt})
        print(f"train<{yr},test{yr:<14}"[:22]
              + f"{n:>7}{over_freq:>10.4f}{over_pred:>10.4f}{bo:>9.4f}"
              f"{log_ov:>8.3f}{btts_freq:>10.4f}{btts_pred:>10.4f}{bb:>9.4f}{log_bt:>8.3f}")

        pool_over_pred.append(p_over); pool_btts_pred.append(p_btts)
        pool_over_act.append(act_over.astype(float)); pool_btts_act.append(act_btts.astype(float))

    pop, ppb = np.concatenate(pool_over_pred), np.concatenate(pool_btts_pred)
    aov, abt = np.concatenate(pool_over_act), np.concatenate(pool_btts_act)
    N = len(pop)
    ov_freq, ov_pred = float(aov.mean()), float(pop.mean())
    bt_freq, bt_pred = float(abt.mean()), float(ppb.mean())
    bo, bb = brier(pop, aov), brier(ppb, abt)
    lou = math.log(ov_freq / ov_pred) if ov_freq > 0 and ov_pred > 0 else float("nan")
    lub = math.log(bt_freq / bt_pred) if bt_freq > 0 and bt_pred > 0 else float("nan")

    print("-" * len(header))
    print(f"{'POOLED':<22}{N:>7}{ov_freq:>10.4f}{ov_pred:>10.4f}{bo:>9.4f}"
          f"{abs(lou):>8.3f}{bt_freq:>10.4f}{bt_pred:>10.4f}{bb:>9.4f}{abs(lub):>8.3f}")

    print("\n=== Interpretation ===")
    print("calibration: realized frequency vs mean predicted p (closer = better)")
    print("log(realized/mean): 0 = perfect; + under-predicts; - over-predicts.")
    print(f"Baseline Brier (always-predict-mean): over1.5={ov_freq*(1-ov_freq):.4f} "
          f"btts={bt_freq*(1-bt_freq):.4f}  (model beats baseline iff its Brier is lower)")
    print(f"\nTotal test matches across {len(results)} windows: {N}")
    print(f"Elapsed: {time.time() - t0:.2f}s (was ~15min pure-Python)")
    print("DONE")


if __name__ == "__main__":
    main()
