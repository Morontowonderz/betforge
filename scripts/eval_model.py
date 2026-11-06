"""Chronological walk-forward out-of-sample backtest of the BetForge model.

For each test year Y (2019..2024), the model is trained ONLY on matches with
date < Y (strictly earlier) and used to predict every match whose date falls
in Y. This is a true out-of-sample design: no match's own outcome or history
derived from it is ever used to form its own prediction, because prediction
for a test match only sees matches strictly earlier than the test cut.

Metrics computed per window and pooled:
  - calibration: realized frequency of Over1.5 and BTTS vs mean predicted p
  - Brier score for p_over1_5 and p_btts
  - log(realized / mean predicted) as a rough deviation measure
  - match counts

Run:  .venv/bin/python scripts/eval_model.py
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

from betforge.models import predict
from betforge.normalization import Match, parse_match

DATA = Path(__file__).resolve().parent.parent / "data" / "matches.csv"
TEST_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]


def load_matches() -> list[tuple[str, Match]]:
    """Return list of (iso_date, Match) sorted chronologically by date."""
    rows: list[tuple[str, Match]] = []
    with open(DATA, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for raw in reader:
            if not raw or not raw[0].strip():
                continue
            try:
                m = parse_match(raw)
            except ValueError:
                continue
            if not m.date:
                continue
            rows.append((m.date, m))
    rows.sort(key=lambda t: t[0])
    return rows


def brier_score(preds: list[float], actuals: list[bool]) -> float:
    n = len(preds) or 1
    return sum((p - (1.0 if y else 0.0)) ** 2 for p, y in zip(preds, actuals)) / n


def run_window(train: list[Match], test: list[tuple[str, Match]]) -> dict:
    over_pred = []
    btts_pred = []
    over_act = []
    btts_act = []
    for _, m in test:
        pr = predict(
            m.home,
            m.away,
            train,
            recent=None,
            rho=0.0,
            league_average=None,
        )
        over_pred.append(pr.p_over1_5)
        btts_pred.append(pr.p_btts)
        over_act.append(m.over1_5)
        btts_act.append(m.btts)

    n = len(test)
    over_freq = sum(over_act) / n if n else float("nan")
    btts_freq = sum(btts_act) / n if n else float("nan")
    over_mean = sum(over_pred) / n if n else float("nan")
    btts_mean = sum(btts_pred) / n if n else float("nan")

    def log_ratio(realized: float, mean_pred: float) -> float:
        if realized <= 0 or mean_pred <= 0:
            return float("nan")
        return math.log(realized / mean_pred)

    return {
        "n": n,
        "over_freq": over_freq,
        "over_mean": over_mean,
        "brier_over": brier_score(over_pred, over_act),
        "log_over": log_ratio(over_freq, over_mean),
        "btts_freq": btts_freq,
        "btts_mean": btts_mean,
        "brier_btts": brier_score(btts_pred, btts_act),
        "log_btts": log_ratio(btts_freq, btts_mean),
    }


def main() -> None:
    matches = load_matches()
    print(f"Loaded {len(matches)} dated matches from {DATA.name}")
    print(f"Date range: {matches[0][0]} .. {matches[-1][0]}")

    # pool accumulators
    pool = {
        "over_pred": [], "btts_pred": [],
        "over_act": [], "btts_act": [],
        "pred_tuples": [], "actual_tuples": [],
    }

    header = (
        f"{'window':<26}{'n':>6}{'over_freq':>10}{'over_pred':>10}"
        f"{'brier_ov':>9}{'log_ov':>8}{'btts_freq':>10}{'btts_pred':>10}"
        f"{'brier_bt':>9}{'log_bt':>8}"
    )
    print("\n" + header)
    print("-" * len(header))

    results = []
    for i, yr in enumerate(TEST_YEARS):
        cut = f"{yr}-01-01"
        # training = strictly earlier than the test year
        train = [m for d, m in matches if d < cut]
        test = [(d, m) for d, m in matches if cut <= d < f"{yr + 1}-01-01"]
        if not test:
            continue
        r = run_window(train, test)
        results.append((yr, len(train), r))
        print(
            f"train<{yr},test{yr:<20}"[:26]
            + f"{r['n']:>6}{r['over_freq']:>10.4f}{r['over_mean']:>10.4f}"
            f"{r['brier_over']:>9.4f}{r['log_over']:>8.3f}"
            f"{r['btts_freq']:>10.4f}{r['btts_mean']:>10.4f}"
            f"{r['brier_btts']:>9.4f}{r['log_btts']:>8.3f}"
        )
        # accumulate pool
        over_pred = [predict(m.home, m.away, train, rho=0.0).p_over1_5
                     for _, m in test]
        btts_pred = [predict(m.home, m.away, train, rho=0.0).p_btts
                     for _, m in test]
        pool["over_pred"] += over_pred
        pool["btts_pred"] += btts_pred
        pool["over_act"] += [m.over1_5 for _, m in test]
        pool["btts_act"] += [m.btts for _, m in test]

    # ---- pooled results ----
    N = len(pool["over_pred"])
    ov_freq = sum(pool["over_act"]) / N
    ov_mean = sum(pool["over_pred"]) / N
    bt_freq = sum(pool["btts_act"]) / N
    bt_mean = sum(pool["btts_pred"]) / N
    brier_ov = brier_score(pool["over_pred"], pool["over_act"])
    brier_bt = brier_score(pool["btts_pred"], pool["btts_act"])

    print("-" * len(header))
    label = "POOLED"
    print(
        f"{label:<26}{N:>6}{ov_freq:>10.4f}{ov_mean:>10.4f}"
        f"{brier_ov:>9.4f}{abs(math.log(ov_freq/ov_mean)) if ov_freq>0 and ov_mean>0 else float('nan'):>8.3f}"
        f"{bt_freq:>10.4f}{bt_mean:>10.4f}"
        f"{brier_bt:>9.4f}{abs(math.log(bt_freq/bt_mean)) if bt_freq>0 and bt_mean>0 else float('nan'):>8.3f}"
    )

    print("\n=== Interpretation ===")
    print("calibration: realized frequency vs mean predicted p (closer = better-calibrated)")
    print("log(realized/mean): log of realized-frequency over mean-predicted. 0 = perfect match;")
    print("  positive = model under-predicts the market; negative = model over-predicts.")
    print("Baseline Brier (always-predict-mean): "
          f"over1.5={ov_freq*(1-ov_freq):.4f} btts={bt_freq*(1-bt_freq):.4f}"
          " (model beats baseline iff its Brier is below this).")

    print(f"\nTotal test matches across {len(results)} windows: {N}")
    print("DONE")


if __name__ == "__main__":
    main()
