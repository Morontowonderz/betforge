"""Fit the DC baseline by maximum likelihood and benchmark against the market.

Owner spec 2026-11-06:
  1. fit_dc_model(df) -- scipy L-BFGS-B, minimise negative log-likelihood of
     actual FTHG/FTAG under the DC pmf (global lambdas + rho).
  2. Extract p_over25_dc from the 10x10 matrix.
  3. Compare Brier(p_over25_dc) to the de-vigged market P(Over 2.5) from
     Avg>2.5 / Avg<2.5. Print results.

Test on the EPL 2023-2024 season (owner request).

Run:
    .venv/bin/python scripts/benchmark_dc_market.py --season 2023-2024
    .venv/bin/python scripts/benchmark_dc_market.py --csv data/matches_fd.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from betforge import baseline as B  # noqa: E402


def _f(row: dict, key: str) -> float | None:
    v = (row.get(key) or "").strip()
    if not v:
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    return f if f > 1.0 else None


def load_unified(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def de_vig_ou(over: float, under: float) -> float:
    """Two-way multiplicative de-vig -> implied P(Over 2.5)."""
    inv_o, inv_u = 1.0 / over, 1.0 / under
    return inv_o / (inv_o + inv_u)


def brier(p: np.ndarray, y: np.ndarray) -> float:
    ok = np.isfinite(p) & np.isfinite(y)
    return float(np.mean((p[ok] - y[ok]) ** 2))


def logloss(p: np.ndarray, y: np.ndarray) -> float:
    ok = np.isfinite(p) & np.isfinite(y)
    p = np.clip(p[ok], 1e-7, 1 - 1e-7)
    y = y[ok]
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def main() -> int:
    ap = argparse.ArgumentParser(description="DC MLE fit vs market benchmark")
    ap.add_argument("--csv", default="data/matches.csv")
    ap.add_argument("--season", default=None, help="filter to a season, e.g. 2023-2024")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"missing {csv_path} -- run scripts/fetch_data.py && scripts/build_advanced_csv.py")
        return 1

    rows = load_unified(csv_path)
    if args.season:
        year = args.season.split("-")[0]
        rows = [r for r in rows if r.get("Date", "").startswith(year + "-")]
    print(f"loaded {len(rows)} rows from {csv_path.name}"
          + (f" (season {args.season})" if args.season else ""))
    if not rows:
        print("no rows")
        return 1

    # fit_dc_model expects a DataFrame with home_goals/away_goals.
    import pandas as pd
    df = pd.DataFrame([{
        "date": r["Date"], "home": r["HomeTeam"], "away": r["AwayTeam"],
        "home_goals": int(r["FTHG"]), "away_goals": int(r["FTAG"]),
    } for r in rows])

    # ---- Stage 1: MLE fit on actual goals ---------------------------------
    fit = B.fit_dc_model(df)
    print("\n=== Stage 1: DC maximum-likelihood fit (L-BFGS-B) ===")
    for k, v in fit.as_dict().items():
        print(f"  {k:<22} {v}")

    # ---- Stage 2: matrix -> p_over25_dc -----------------------------------
    p_dc = np.full(len(rows), np.nan)
    for i, r in enumerate(rows):
        over = _f(r, "B365>2.5")
        under = _f(r, "B365<2.5")
        # Per-match p_over25 from the GLOBAL fitted lambdas (owner spec: global
        # average lambda + rho, no team-specific parameters yet).
        p_dc[i] = fit.over25()

    # Market: de-vigged Avg>2.5 / Avg<2.5 (fallback to B365 if Avg missing).
    p_mkt = np.full(len(rows), np.nan)
    for i, r in enumerate(rows):
        over = _f(r, "Avg>2.5") or _f(r, "B365>2.5")
        under = _f(r, "Avg<2.5") or _f(r, "B365<2.5")
        if over and under:
            p_mkt[i] = de_vig_ou(over, under)

    y = np.array([1.0 if (int(r["FTHG"]) + int(r["FTAG"]) >= 3) else 0.0 for r in rows])
    ok = np.isfinite(p_dc) & np.isfinite(p_mkt)
    y, p_dc, p_mkt = y[ok], p_dc[ok], p_mkt[ok]
    n = len(y)
    freq = float(y.mean())

    b_dc = brier(p_dc, y)
    b_mkt = brier(p_mkt, y)
    b_base = float(freq * (1 - freq))
    ll_dc = logloss(p_dc, y)
    ll_mkt = logloss(p_mkt, y)
    ll_base = float(-np.mean(y * np.log(max(freq, 1e-7)) + (1 - y) * np.log(max(1 - freq, 1e-7))))

    print(f"\n=== Stage 2: Over 2.5 benchmark (n={n}) ===")
    print(f"  realized frequency     : {freq:.4f}")
    print(f"  {'model':<20}{'brier':>9}{'logloss':>9}{'mean_pred':>11}")
    print(f"  {'DC baseline (MLE)':<20}{b_dc:>9.4f}{ll_dc:>9.4f}{p_dc.mean():>11.4f}")
    print(f"  {'market (de-vig)':<20}{b_mkt:>9.4f}{ll_mkt:>9.4f}{p_mkt.mean():>11.4f}")
    print(f"  {'base rate':<20}{b_base:>9.4f}{ll_base:>9.4f}{freq:>11.4f}")
    print(f"\n  DC vs market  : {'DC WINS' if b_dc < b_mkt else 'DC LOSES'} "
          f"(margin {abs(b_dc - b_mkt):.4f})")
    print(f"  DC vs base    : {'DC WINS' if b_dc < b_base else 'DC LOSES'} "
          f"(margin {abs(b_dc - b_base):.4f})")
    print(f"  market vs base: {'MARKET WINS' if b_mkt < b_base else 'MARKET LOSES'} "
          f"(margin {abs(b_mkt - b_base):.4f})")

    # Calibration buckets: is the DC baseline even calibrated?
    print("\n=== calibration (DC baseline, 5 buckets) ===")
    order = np.argsort(p_dc)
    buckets = np.array_split(order, 5)
    for b in buckets:
        if len(b) == 0:
            continue
        print(f"  pred {p_dc[b].mean():.3f}  actual {y[b].mean():.3f}  n={len(b)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
