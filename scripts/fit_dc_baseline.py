"""Fit Dixon-Coles lambdas/rho from REAL Over/Under 2.5 closing lines.

Owner mandate 2026-11-06: O1.5 proxy is killed (1-1 sits on the DC tau
boundary). We train on the actual O/U 2.5 closing lines from
football-data.co.uk. This script:

  1. loads data/matches_advanced.csv (from scripts/build_advanced_csv.py)
  2. de-vigs the O/U 2.5 pair (two-way multiplicative)
  3. fits (lam_h, lam_a, rho) per match to that probability, regularised by
     the de-vigged 1X2 triple
  4. builds the 10x10 DC matrix and marginalizes to P(Over 2.5)
  5. writes results/dc_baseline_o25.csv with the baseline and diagnostics

It also reports the calibration of the DC baseline against the realized O2.5
outcome -- the honest check of whether the baseline is any good.

Run:
    .venv/bin/python scripts/fit_dc_baseline.py
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from betforge import baseline as B  # noqa: E402

ADV = Path(__file__).resolve().parent.parent / "data" / "matches_advanced.csv"
OUT = Path(__file__).resolve().parent.parent / "results" / "dc_baseline_o25.csv"


def _f(row: dict, key: str) -> float | None:
    v = (row.get(key) or "").strip()
    if not v:
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    return f if f > 1.0 else None


def main() -> int:
    if not ADV.exists():
        print(f"missing {ADV} -- run scripts/fetch_data.py && scripts/build_advanced_csv.py")
        return 1

    with ADV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    print(f"loaded {len(rows)} matches from {ADV.name}")

    t0 = time.time()
    out_rows, skipped = [], 0
    for r in rows:
        over = _f(r, "over25_close")
        under = _f(r, "under25_close")
        if over is None or under is None:
            skipped += 1
            continue
        o1x2 = [_f(r, "home_odds"), _f(r, "draw_odds"), _f(r, "away_odds")]
        odds_1x2 = [float(x) for x in o1x2 if x is not None] if all(x is not None for x in o1x2) else None

        market, params = B.predict_from_ou(over, under, odds_1x2=odds_1x2)
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        out_rows.append({
            "date": r["date"], "home": r["home"], "away": r["away"],
            "home_goals": hg, "away_goals": ag,
            "over25_close": over, "under25_close": under,
            "p_over25_market": round(market["p_over25_market"], 5),
            "p_over25_dc": round(market["p_over25"], 5),
            "p_btts_dc": round(market["p_btts"], 5),
            "p_home_dc": round(market["p_home"], 5),
            "p_draw_dc": round(market["p_draw"], 5),
            "p_away_dc": round(market["p_away"], 5),
            "lam_home": round(params.lam_home, 4),
            "lam_away": round(params.lam_away, 4),
            "rho": round(params.rho, 4),
            "fit_rmse": round(params.fit_rmse, 6),
            "method": params.method,
            "y_over25": int(hg + ag >= 3),
        })

    print(f"fitted {len(out_rows)} matches ({skipped} skipped, no O/U line) "
          f"in {time.time() - t0:.1f}s")

    if not out_rows:
        print("nothing fitted")
        return 1

    # ---- honest calibration check -----------------------------------------
    p_dc = np.array([r["p_over25_dc"] for r in out_rows])
    p_mk = np.array([r["p_over25_market"] for r in out_rows])
    y = np.array([r["y_over25"] for r in out_rows], dtype=float)
    n = len(y)
    freq = y.mean()
    brier_dc = float(np.mean((p_dc - y) ** 2))
    brier_mk = float(np.mean((p_mk - y) ** 2))
    brier_base = float(freq * (1 - freq))
    log_dc = float(-np.mean(y * np.log(np.clip(p_dc, 1e-7, 1 - 1e-7))
                            + (1 - y) * np.log(np.clip(1 - p_dc, 1e-7, 1 - 1e-7))))
    log_mk = float(-np.mean(y * np.log(np.clip(p_mk, 1e-7, 1 - 1e-7))
                            + (1 - y) * np.log(np.clip(1 - p_mk, 1e-7, 1 - 1e-7))))
    log_base = float(-np.mean(y * np.log(np.clip(freq, 1e-7, 1 - 1e-7))
                              + (1 - y) * np.log(np.clip(1 - freq, 1e-7, 1 - 1e-7))))

    print(f"\n=== Over 2.5 calibration (n={n}) ===")
    print(f"  realized frequency : {freq:.4f}")
    print(f"  {'model':<18}{'brier':>9}{'logloss':>9}{'mean_pred':>11}")
    print(f"  {'DC baseline':<18}{brier_dc:>9.4f}{log_dc:>9.4f}{p_dc.mean():>11.4f}")
    print(f"  {'market (de-vig)':<18}{brier_mk:>9.4f}{log_mk:>9.4f}{p_mk.mean():>11.4f}")
    print(f"  {'base rate':<18}{brier_base:>9.4f}{log_base:>9.4f}{freq:>11.4f}")
    print(f"\n  DC vs market  : {'DC WINS' if brier_dc < brier_mk else 'DC LOSES'} "
          f"(margin {abs(brier_dc - brier_mk):.4f})")
    print(f"  DC vs base    : {'DC WINS' if brier_dc < brier_base else 'DC LOSES'} "
          f"(margin {abs(brier_dc - brier_base):.4f})")
    print(f"  market vs base: {'MARKET WINS' if brier_mk < brier_base else 'MARKET LOSES'} "
          f"(margin {abs(brier_mk - brier_base):.4f})")

    # ---- write ------------------------------------------------------------
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["date", "home", "away", "home_goals", "away_goals",
            "over25_close", "under25_close", "p_over25_market", "p_over25_dc",
            "p_btts_dc", "p_home_dc", "p_draw_dc", "p_away_dc",
            "lam_home", "lam_away", "rho", "fit_rmse", "method", "y_over25"]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"\nwrote {OUT}")

    mean_rho = float(np.mean([r["rho"] for r in out_rows]))
    mean_rmse = float(np.mean([r["fit_rmse"] for r in out_rows]))
    print(f"mean fitted rho = {mean_rho:.4f} (negative expected)")
    print(f"mean O2.5 fit rmse = {mean_rmse:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
