"""Phase 2: XGBoost Over1.5 / BTTS walk-forward eval vs market proxy and base rate.

Gate (ship/no-ship, owner-set): model Brier MUST beat the de-vigged market
PROXY Brier on pooled OOS matches. Base rate is reported alongside as the
vanity line. Per-window and pooled numbers are both printed.

Leakage discipline:
  - Features are lagged (shift(1)) at build time; a match never sees its own
    result or any later match.
  - The market proxy is FITTED ON THE TRAINING WINDOW ONLY per test year, then
    applied to the test window. Test odds never influence their own proxy.
  - Train = date < Y, test = Y <= date < Y+1. No shuffling.

Run:  .venv/bin/python scripts/eval_xgb.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import features as F  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data" / "matches.csv"
CACHE = Path("/home/moronto/.hermes/cache/scratch/bf_features.pkl")
TEST_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
XGB_PARAMS = dict(
    n_estimators=400, max_depth=5, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, min_child_weight=50,
    reg_lambda=2.0, objective="binary:logistic", eval_metric="logloss",
    n_jobs=8, tree_method="hist", random_state=42,
)


def _finite(p: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ok = np.isfinite(p) & np.isfinite(y)
    return p[ok], y[ok]


def logloss(p: np.ndarray, y: np.ndarray) -> float:
    p, y = _finite(p, y)
    if len(p) == 0:
        return float("nan")
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier(p: np.ndarray, y: np.ndarray) -> float:
    p, y = _finite(p, y)
    if len(p) == 0:
        return float("nan")
    return float(np.mean((p - y) ** 2))


def fit_proxy(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Fit the independent-Poisson proxy mapping on train odds; apply to both."""
    qtr = train[["qh", "qd", "qa"]].dropna()
    qte = test[["qh", "qd", "qa"]]
    if len(qtr) < 1000:
        return None
    # Build the grid once per window from train odds.
    tot = np.linspace(0.6, 6.0, 271)
    split = np.linspace(0.08, 0.92, 85)
    T, S = np.meshgrid(tot, split, indexing="ij")
    g_lh, g_la = (T * S).ravel(), (T * (1 - S)).ravel()
    gh, gd, _ = F._grid_1x2(g_lh, g_la)
    from scipy.spatial import cKDTree
    tree = cKDTree(np.column_stack([gh, gd]))

    def apply(qdf: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=qdf.index)
        q = qdf[["qh", "qd", "qa"]]
        valid = q.notna().all(axis=1).to_numpy()
        lh = np.full(len(qdf), np.nan)
        la = np.full(len(qdf), np.nan)
        if valid.any():
            _, idx = tree.query(q.loc[valid, ["qh", "qd"]].to_numpy(), k=1)
            lh[valid], la[valid] = g_lh[idx], g_la[idx]
        out["mkt_lam_h"], out["mkt_lam_a"] = lh, la
        s = lh + la
        out["mkt_p_over15"] = 1 - np.exp(-s) * (1 + s)
        out["mkt_p_btts"] = (1 - np.exp(-lh)) * (1 - np.exp(-la))
        return out

    return apply(train), apply(test)


def main() -> None:
    t0 = time.time()
    if CACHE.exists():
        m = pd.read_pickle(CACHE)
        print(f"Loaded cached features {m.shape} ({time.time() - t0:.1f}s)")
    else:
        m = F.build(pd.read_csv(DATA))
        m.to_pickle(CACHE)
        print(f"Built features {m.shape} ({time.time() - t0:.1f}s)")

    sets = F.feature_sets(m)
    rows = []
    pooled = {k: {"p": [], "y": [], "proxy": [], "base": []} for k in ("over15", "btts")}
    imp_rows = []

    for yr in TEST_YEARS:
        cut, nxt = f"{yr}-01-01", f"{yr + 1}-01-01"
        train = m[m["date"] < cut]
        test = m[(m["date"] >= cut) & (m["date"] < nxt)]
        if len(test) < 500:
            continue

        pr = fit_proxy(train, test)
        if pr is None:
            continue
        ptr, pte = pr
        # Drop the globally-built proxy columns so the per-window proxy can join cleanly.
        train = train.drop(columns=["mkt_lam_h", "mkt_lam_a", "mkt_p_over15", "mkt_p_btts"], errors="ignore")
        test = test.drop(columns=["mkt_lam_h", "mkt_lam_a", "mkt_p_over15", "mkt_p_btts"], errors="ignore")
        train = train.join(ptr)
        test = test.join(pte)

        y_tr_o = train["y_over15"].to_numpy()
        y_te_o = test["y_over15"].to_numpy()
        y_tr_b = train["y_btts"].to_numpy()
        y_te_b = test["y_btts"].to_numpy()
        base_o = float(y_tr_o.mean())
        base_b = float(y_tr_b.mean())

        rec = {"year": yr, "n": len(test), "base_o": base_o, "base_b": base_b}
        for tgt, ytr, yte, base, key in (
            ("over15", y_tr_o, y_te_o, base_o, "over15"),
            ("btts", y_tr_b, y_te_b, base_b, "btts"),
        ):
            rec[f"proxy_brier_{key}"] = brier(test[f"mkt_p_{key}"].to_numpy(), yte)
            rec[f"base_brier_{key}"] = brier(np.full(len(yte), base), yte)
            rec[f"proxy_log_{key}"] = logloss(test[f"mkt_p_{key}"].to_numpy(), yte)
            rec[f"base_log_{key}"] = logloss(np.full(len(yte), base), yte)

            for label, cols in sets.items():
                Xtr = train[cols].to_numpy(dtype=float)
                Xte = test[cols].to_numpy(dtype=float)
                ok_tr = np.isfinite(Xtr).all(axis=1)
                ok_te = np.isfinite(Xte).all(axis=1)
                if ok_te.mean() < 0.5:
                    continue
                model = xgb.XGBClassifier(**XGB_PARAMS)
                model.fit(Xtr[ok_tr], ytr[ok_tr], verbose=False)
                p = np.full(len(yte), base)
                p[ok_te] = model.predict_proba(Xte[ok_te])[:, 1]
                rec[f"{label}_brier_{key}"] = brier(p, yte)
                rec[f"{label}_log_{key}"] = logloss(p, yte)
                if tgt == "over15":
                    imp = model.feature_importances_
                    for c, v in zip(cols, imp):
                        imp_rows.append({"year": yr, "set": label, "feat": c, "gain": float(v)})
                pooled[key]["p"].append(p)
                pooled[key]["y"].append(yte)
                pooled[key]["proxy"].append(test[f"mkt_p_{key}"].to_numpy())
                pooled[key]["base"].append(np.full(len(yte), base))
        rows.append(rec)
        print(f"  {yr}: n={len(test)} done ({time.time() - t0:.1f}s)")

    df = pd.DataFrame(rows)
    print("\n=== per-window Brier (over15) ===")
    cols = ["year", "n", "base_o", "proxy_brier_over15", "base_brier_over15",
            "A_no_odds_brier_over15", "B_with_odds_brier_over15"]
    print(df[[c for c in cols if c in df]].round(4).to_string(index=False))
    print("\n=== per-window Brier (btts) ===")
    cols = ["year", "n", "base_b", "proxy_brier_btts", "base_brier_btts",
            "A_no_odds_brier_btts", "B_with_odds_brier_btts"]
    print(df[[c for c in cols if c in df]].round(4).to_string(index=False))

    print("\n=== POOLED ===")
    summary = {}
    for key in ("over15", "btts"):
        p = np.concatenate(pooled[key]["p"])
        y = np.concatenate(pooled[key]["y"])
        pr = np.concatenate(pooled[key]["proxy"])
        ba = np.concatenate(pooled[key]["base"])
        summary[key] = {
            "n": int(len(y)),
            "base_rate": float(y.mean()),
            "brier_model": brier(p, y),
            "brier_proxy_market": brier(pr, y),
            "brier_base_rate": brier(ba, y),
            "logloss_model": logloss(p, y),
            "logloss_proxy_market": logloss(pr, y),
            "logloss_base_rate": logloss(ba, y),
        }
        s = summary[key]
        print(f"{key}: n={s['n']} base_rate={s['base_rate']:.4f}")
        print(f"  Brier  model={s['brier_model']:.4f}  proxy_market={s['brier_proxy_market']:.4f}  base_rate={s['brier_base_rate']:.4f}")
        print(f"  LogLoss model={s['logloss_model']:.4f}  proxy_market={s['logloss_proxy_market']:.4f}  base_rate={s['logloss_base_rate']:.4f}")
        print(f"  beats proxy: {'YES' if s['brier_model'] < s['brier_proxy_market'] else 'NO'}")
        print(f"  beats base : {'YES' if s['brier_model'] < s['brier_base_rate'] else 'NO'}")

    imp = pd.DataFrame(imp_rows)
    if len(imp):
        top = (imp.groupby(["set", "feat"])["gain"].mean().reset_index()
               .sort_values(["set", "gain"], ascending=[True, False]))
        print("\n=== feature importance (mean gain across windows) ===")
        for label in sets:
            sub = top[top["set"] == label].head(12)
            print(f"-- {label} --")
            print(sub.round(4).to_string(index=False))

    out = Path(__file__).resolve().parent.parent / "results"
    out.mkdir(exist_ok=True)
    (out / "xgb_walkforward.json").write_text(json.dumps(
        {"summary": summary, "per_window": rows}, indent=2))
    if len(imp):
        top.to_csv(out / "xgb_importance.csv", index=False)
    print(f"\nWrote results/xgb_walkforward.json  ({time.time() - t0:.1f}s total)")


if __name__ == "__main__":
    main()
