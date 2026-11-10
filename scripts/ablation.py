"""Ablation: does the owner's fatigue/momentum hypothesis have ANY standalone signal?

D_pure = only calendar features (rest days, congestion) + month/dow.
No odds, no xG, no scoring history. If this cannot beat the base rate, the
fatigue/momentum hypothesis is dead on this data and the entire XGBoost edge
is the odds/scoring-history backdoor.

Also reports a "scoring history only" set (E_hist) to separate the two.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_xgb as E  # noqa: E402

CACHE = Path("/home/moronto/.hermes/cache/scratch/bf_features.pkl")
TEST_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

SETS = {
    "D_pure_fatigue": ["fatigue_idx", "h_rest_days", "a_rest_days",
                       "h_cong_7", "a_cong_7", "h_cong_14", "a_cong_14",
                       "month", "dow"],
    "E_hist_scoring": ["pace_idx", "h_ewm_tot", "a_ewm_tot", "h_ewm_gf", "a_ewm_gf",
                       "h_ewm_ga", "a_ewm_ga", "h_ewm_over15", "a_ewm_over15",
                       "h_ewm_btts", "a_ewm_btts"],
    "F_momentum_only": ["momentum_idx", "h_ewm_res_for", "a_ewm_res_for",
                        "h_ewm_res_ag", "a_ewm_res_ag"],
}


def main() -> None:
    t0 = time.time()
    m = pd.read_pickle(CACHE)
    print(f"Loaded {m.shape}")

    for tgt, ycol, key in (("over15", "y_over15", "over15"), ("btts", "y_btts", "btts")):
        print(f"\n===== {tgt} =====")
        pooled = {name: {"p": [], "y": []} for name in SETS}
        pooled["base"] = {"p": [], "y": []}
        for yr in TEST_YEARS:
            cut, nxt = f"{yr}-01-01", f"{yr + 1}-01-01"
            train = m[m["date"] < cut]
            test = m[(m["date"] >= cut) & (m["date"] < nxt)]
            ytr = train[ycol].to_numpy()
            yte = test[ycol].to_numpy()
            base = float(ytr.mean())
            pooled["base"]["p"].append(np.full(len(yte), base))
            pooled["base"]["y"].append(yte)
            for name, cols in SETS.items():
                Xtr = train[cols].to_numpy(dtype=float)
                Xte = test[cols].to_numpy(dtype=float)
                ok_tr = np.isfinite(Xtr).all(axis=1)
                ok_te = np.isfinite(Xte).all(axis=1)
                if ok_te.mean() < 0.5:
                    continue
                model = xgb.XGBClassifier(**E.XGB_PARAMS)
                model.fit(Xtr[ok_tr], ytr[ok_tr], verbose=False)
                p = np.full(len(yte), base)
                p[ok_te] = model.predict_proba(Xte[ok_te])[:, 1]
                pooled[name]["p"].append(p)
                pooled[name]["y"].append(yte)

        print(f"{'set':<18}{'brier':>9}{'logloss':>9}{'n':>9}")
        base_p = np.concatenate(pooled["base"]["p"])
        base_y = np.concatenate(pooled["base"]["y"])
        print(f"{'base_rate':<18}{E.brier(base_p, base_y):>9.4f}{E.logloss(base_p, base_y):>9.4f}{len(base_y):>9}")
        for name in SETS:
            p = np.concatenate(pooled[name]["p"])
            y = np.concatenate(pooled[name]["y"])
            b = E.brier(p, y)
            ll = E.logloss(p, y)
            verdict = "BEATS BASE" if b < E.brier(base_p, base_y) else "no edge"
            print(f"{name:<18}{b:>9.4f}{ll:>9.4f}{len(y):>9}  {verdict}")

    print(f"\n({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
