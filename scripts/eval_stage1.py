"""Honest walk-forward evaluation of the two-stage λ model (XGB stage-1).

Usage:
    python scripts/eval_stage1.py [betforge_ou.db] [sample]

Splits the chronologically-last `sample` real-line matches 70/30 by date, trains
the Stage1Lambdas model on rolling features computed STRICTLY from matches
before each row (no lookahead), then reports, on the held-out 30%:

  * model Brier for Over 2.5
  * base-rate Brier (always predict the training base rate)
  * closing-line Brier (predict the de-vigged real O/U 2.5 line)

The honest question the HANDOFF cares about: do per-match lambdas beat the
base rate AND the efficient closing line? They usually beat neither.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from betforge import storage  # noqa: E402
from betforge.features import chrono_sort, features_before  # noqa: E402
from betforge.models_engine import Stage1Lambdas  # noqa: E402
from betforge.devig import ou_implied_p25  # noqa: E402


def _brier(probs: list[float], ys: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(probs, ys)) / max(1, len(ys))


def main() -> None:
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("betforge_ou.db")
    sample_n = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    matches = chrono_sort(storage.iter_matches_ou(db))
    matches = matches[-sample_n:]
    if len(matches) < 300:
        sys.exit("need more real-line matches")

    cut = int(len(matches) * 0.7)
    train, test = matches[:cut], matches[cut:]

    # ---- build training features (strictly-before each row) + targets ----
    rows: list[dict[str, float | int | str]] = []
    lam_h: list[float] = []
    lam_a: list[float] = []
    hist: list = []
    for m in train:
        rows.append(features_before(hist, m.home, m.away).as_dict())
        lam_h.append(float(m.home_goals))
        lam_a.append(float(m.away_goals))
        hist.append(m)

    model = Stage1Lambdas(min_samples=200)
    fitted = model.fit(rows, lam_h, lam_a)
    print(f"stage-1 fitted: {fitted} ({model._note})")

    # ---- walk-forward on the held-out test set (history = all prior, not this match) ----
    base_over25 = sum(1 for m in train if m.over2_5) / max(1, len(train))
    p_m: list[float] = []
    p_base: list[float] = []
    p_mkt: list[float] = []
    ys: list[int] = []
    for m in test:
        fr = features_before(hist, m.home, m.away)
        if fitted:
            p_m.append(model.predict(fr.as_dict()).p_over25)
        else:
            # strength-Poisson fallback estimate (still honest)
            from betforge.models import predict

            p_m.append(float(predict(m.home, m.away, hist).p_over2_5))
        p_base.append(base_over25)
        p_mkt.append(ou_implied_p25(m.over_odds, m.under_odds))
        ys.append(1 if m.over2_5 else 0)
        hist.append(m)

    print(f"train={len(train)} test={len(test)} base_over25={base_over25:.3f}")
    print(f"=> Model Brier (O2.5):        {_brier(p_m, ys):.4f}")
    print(f"=> Base-rate Brier (O2.5):    {_brier(p_base, ys):.4f}")
    print(f"=> Closing-line Brier (O2.5): {_brier(p_mkt, ys):.4f}")
    print("(Lower is better. The closing line is the efficient benchmark; the model rarely beats it.)")


if __name__ == "__main__":
    main()
