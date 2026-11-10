"""Stage 1 of the two-stage model: XGBoost predicts per-match lambda_home/lambda_away.

Owner mandate 2026-11-06:
  Stage 1: XGBoost predicts lambda_home and lambda_away (expected goals)
  Stage 2: the Dixon-Coles matrix converts those lambdas to p_over25_dc

Features come from data/matches_advanced.csv -- real match statistics that the
9-column dataset lacked: shots, shots on target, corners, cards, referee, and
the O/U 2.5 closing line.

Leakage discipline: every feature is lagged (shift(1)) or computed from a
rolling window that EXCLUDES the current match (closed='left'). Train =
date < cut, test = cut <= date < cut+1. No shuffling.

The target is the observed goals (FTHG/FTAG). The lambdas are then fed to the
DC matrix with a single global rho fitted by MLE on the training window.

Run:
    .venv/bin/python scripts/stage1_xgb_lambdas.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from betforge import baseline as B  # noqa: E402

ADV = Path(__file__).resolve().parent.parent / "data" / "matches_advanced.csv"
OUT = Path(__file__).resolve().parent.parent / "results" / "stage1_backtest.csv"
TEST_YEARS = [2022, 2023, 2024]

XGB = dict(
    n_estimators=600, max_depth=4, learning_rate=0.03,
    subsample=0.8, colsample_bytree=0.8, min_child_weight=30,
    reg_lambda=2.0, objective="reg:squarederror",
    n_jobs=8, tree_method="hist", random_state=42,
)

FEATURES = [
    "h_r6_gf", "a_r6_gf", "h_r6_ga", "a_r6_ga",
    "h_r6_shots", "a_r6_shots", "h_r6_sot", "a_r6_sot",
    "h_r6_corners", "a_r6_corners", "h_r6_cards", "a_r6_cards",
    "h_r6_shot_share", "a_r6_shot_share",
    "d_gf", "d_ga", "d_shots", "d_sot", "d_corners", "d_cards",
    "month", "dow",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lagged/rolling team-strength features. All values are pre-match."""
    m = df.copy()
    m["date"] = pd.to_datetime(m["date"])
    m = m.sort_values("date").reset_index(drop=True)
    m["match_idx"] = np.arange(len(m))

    # Long table: one row per (match, team) so rolling stats are per-team.
    long = pd.concat([
        pd.DataFrame({"match_idx": m["match_idx"], "date": m["date"], "team": m["home"],
                      "is_home": 1, "gf": m["home_goals"], "ga": m["away_goals"],
                      "shots": m["home_shots"], "sot": m["home_sot"],
                      "corners": m["home_corners"],
                      "cards": m["home_yellows"] + m["home_reds"].fillna(0)}),
        pd.DataFrame({"match_idx": m["match_idx"], "date": m["date"], "team": m["away"],
                      "is_home": 0, "gf": m["away_goals"], "ga": m["home_goals"],
                      "shots": m["away_shots"], "sot": m["away_sot"],
                      "corners": m["away_corners"],
                      "cards": m["away_yellows"] + m["away_reds"].fillna(0)}),
    ], ignore_index=True).sort_values(["team", "date", "match_idx"]).reset_index(drop=True)

    g = long.groupby("team", sort=False)
    # Rolling means over the previous 6 matches (closed='left' excludes current).
    for col in ("gf", "ga", "shots", "sot", "corners", "cards"):
        long[f"r6_{col}"] = g[col].transform(
            lambda s: s.shift(1).rolling(6, min_periods=1, closed="left").mean())
    long["shot_share"] = long["shots"] / (
        long["shots"] + g["shots"].shift(1)).replace(0, np.nan)
    long["r6_shot_share"] = g["shot_share"].transform(
        lambda s: s.shift(1).rolling(6, min_periods=1, closed="left").mean())

    h = long[long["is_home"] == 1].set_index("match_idx").add_prefix("h_")
    a = long[long["is_home"] == 0].set_index("match_idx").add_prefix("a_")
    m = m.set_index("match_idx").join(h).join(a).reset_index(drop=True)

    m["month"] = m["date"].dt.month
    m["dow"] = m["date"].dt.day_of_week
    # Differentials (the model cares about the gap, not the levels).
    for c in ("gf", "ga", "shots", "sot", "corners", "cards"):
        m[f"d_{c}"] = m[f"h_r6_{c}"] - m[f"a_r6_{c}"]
    return m


def brier(p, y):
    ok = np.isfinite(p) & np.isfinite(y)
    return float(np.mean((p[ok] - y[ok]) ** 2))


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 1 XGBoost lambdas -> DC O2.5")
    ap.add_argument("--adv", default=str(ADV))
    args = ap.parse_args()

    if not Path(args.adv).exists():
        print(f"missing {args.adv} -- run scripts/build_advanced_csv.py first")
        return 1

    t0 = time.time()
    m = build_features(pd.read_csv(args.adv))
    print(f"features built: {m.shape} ({time.time() - t0:.1f}s)")

    rows = []
    for yr in TEST_YEARS:
        cut, nxt = f"{yr}-01-01", f"{yr + 1}-01-01"
        train = m[m["date"] < cut]
        test = m[(m["date"] >= cut) & (m["date"] < nxt)]
        if len(test) < 50:
            continue

        # Global rho on the training window (MLE on actual goals).
        rho_fit = B.fit_dc_model(pd.DataFrame({
            "home_goals": train["home_goals"], "away_goals": train["away_goals"]}))
        rho = rho_fit.rho

        Xtr = train[FEATURES].to_numpy(dtype=float)
        Xte = test[FEATURES].to_numpy(dtype=float)
        ok_tr = np.isfinite(Xtr).all(axis=1)
        ok_te = np.isfinite(Xte).all(axis=1)
        if ok_te.mean() < 0.3:
            continue

        mh = xgb.XGBRegressor(**XGB).fit(Xtr[ok_tr], train["home_goals"].to_numpy()[ok_tr], verbose=False)
        ma = xgb.XGBRegressor(**XGB).fit(Xtr[ok_tr], train["away_goals"].to_numpy()[ok_tr], verbose=False)

        lh = np.full(len(test), np.nan)
        la = np.full(len(test), np.nan)
        lh[ok_te] = np.clip(mh.predict(Xte[ok_te]), 0.2, 5.0)
        la[ok_te] = np.clip(ma.predict(Xte[ok_te]), 0.2, 5.0)

        # Stage 2: DC matrix -> p_over25
        p_dc = np.full(len(test), np.nan)
        for i in range(len(test)):
            if np.isfinite(lh[i]) and np.isfinite(la[i]):
                p_dc[i] = B._over25_of_matrix(lh[i], la[i], rho, B.MAX_GOALS)

        # Market (de-vigged Avg>2.5/Avg<2.5) and base rate.
        p_mkt = np.full(len(test), np.nan)
        for i, (o, u) in enumerate(zip(test["over25_avg_close"], test["under25_avg_close"])):
            if pd.notna(o) and pd.notna(u) and o > 1 and u > 1:
                p_mkt[i] = (1.0 / o) / (1.0 / o + 1.0 / u)

        y = ((test["home_goals"] + test["away_goals"]) >= 3).astype(float).to_numpy()
        base = float(y.mean()) if len(y) else np.nan

        ok = np.isfinite(p_dc) & np.isfinite(p_mkt)
        rows.append({
            "year": yr, "n": len(test), "n_ok": int(ok.sum()),
            "rho": rho,
            "brier_dc": brier(p_dc[ok], y[ok]),
            "brier_mkt": brier(p_mkt[ok], y[ok]),
            "brier_base": float(y[ok].mean() * (1 - y[ok].mean())),
            "mean_lh": float(np.nanmean(lh)), "mean_la": float(np.nanmean(la)),
            "mean_pdc": float(np.nanmean(p_dc)), "mean_pmkt": float(np.nanmean(p_mkt)),
            "realized": float(y[ok].mean()),
        })
        print(f"  {yr}: n={len(test)} ok={ok.sum()} dc={rows[-1]['brier_dc']:.4f} "
              f"mkt={rows[-1]['brier_mkt']:.4f} base={rows[-1]['brier_base']:.4f} "
              f"rho={rho:.4f} ({time.time() - t0:.0f}s)")

    if not rows:
        print("no windows evaluated")
        return 1

    df = pd.DataFrame(rows)
    print("\n=== Stage 1 + Stage 2 backtest (pooled, per window) ===")
    print(df[["year", "n", "n_ok", "rho", "brier_dc", "brier_mkt", "brier_base",
              "mean_lh", "mean_la", "realized"]].round(4).to_string(index=False))

    # Pooled, weighted by n_ok
    w = df["n_ok"].to_numpy(dtype=float)
    for col in ("brier_dc", "brier_mkt", "brier_base"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    pooled_dc = float(np.nansum(df["brier_dc"] * w) / np.nansum(w))
    pooled_mkt = float(np.nansum(df["brier_mkt"] * w) / np.nansum(w))
    pooled_base = float(np.nansum(df["brier_base"] * w) / np.nansum(w))
    print(f"\nPOOLED (weighted by n_ok={int(w.sum())}):")
    print(f"  Stage1+2 DC : {pooled_dc:.4f}")
    print(f"  market      : {pooled_mkt:.4f}")
    print(f"  base rate   : {pooled_base:.4f}")
    print(f"  DC vs market: {'DC WINS' if pooled_dc < pooled_mkt else 'DC LOSES'} "
          f"(margin {abs(pooled_dc - pooled_mkt):.4f})")
    print(f"  DC vs base  : {'DC WINS' if pooled_dc < pooled_base else 'DC LOSES'} "
          f"(margin {abs(pooled_dc - pooled_base):.4f})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
