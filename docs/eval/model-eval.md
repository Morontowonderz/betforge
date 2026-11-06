# BetForge Model — Honest Out-of-Sample Evaluation

**Date:** 2026-11-06
**Script:** `scripts/eval_model.py` (full stdout: `backtest-output.txt`)
**Data:** `data/matches.csv`, 11,513 dated international matches, 2015-01-04 .. 2026-10-06.

## What was measured

A chronological walk-forward backtest with **strict** out-of-sample separation.
For each test year Y in {2019…2024}, the model (Poisson/Dixon-Coles joint-goal
estimator) is trained **only** on matches with `date < Y` (all strictly earlier
matches, per-team attack/defence estimated from that training set) and predicts
every match whose date falls in Y. No test match's own outcome or any history
derived from it enters its own prediction. `rho=0.0`, `recent=None` (full
training history per team).

## Numbers

Per window (Over1.5 and BTTS):

| window | n | O1.5 freq | O1.5 pred | Brier O1.5 | log(freq/pred) | BTTS freq | BTTS pred | Brier BTTS | log(freq/pred) |
|---|---|---|---|---|---|---|---|---|---|
| test 2019 | 1156 | 0.732 | 0.706 | 0.2005 | +0.036 | 0.415 | 0.445 | 0.2544 | −0.069 |
| test 2020 | 356 | 0.677 | 0.646 | 0.2221 | +0.046 | 0.461 | 0.413 | 0.2450 | +0.110 |
| test 2021 | 1115 | 0.718 | 0.688 | 0.1996 | +0.043 | 0.401 | 0.429 | 0.2486 | −0.067 |
| test 2022 | 970 | 0.698 | 0.685 | 0.2164 | +0.019 | 0.417 | 0.448 | 0.2501 | −0.073 |
| test 2023 | 1064 | 0.756 | 0.724 | 0.1849 | +0.043 | 0.443 | 0.467 | 0.2511 | −0.054 |
| test 2024 | 1231 | 0.711 | 0.702 | 0.2053 | +0.013 | 0.448 | 0.463 | 0.2496 | −0.034 |
| **pooled** | **5892** | **0.720** | **0.698** | **0.2025** | **+0.032** | **0.427** | **0.448** | **0.2505** | **−0.048** |

Deviations `log(realized/mean)` are ±0.02–0.11, i.e. within roughly a few
percentage points of perfectly calibrated at the *aggregate* level: the model
under-predicts Over1.5 by ~2-4 points of probability and over-predicts BTTS by
~2-4 points on average.

**Baseline comparison (Brier).** Always predicating the pooled mean:

- Over1.5 baseline Brier = **0.2015**; model Brier = **0.2025** — the model
  does **not** beat "always predict the base rate".
- BTTS baseline Brier = **0.2447**; model Brier = **0.2505** — the model is
  **worse** than the trivial baseline for BTTS.

## What this does NOT show

- **No predictive skill.** Calibration is only reasonable *in aggregate over
  5,892 matches*. The model shows no measurable edge over predicting the
  unconditional base rate — for BTTS it is actually slightly worse on Brier.
  Pooling a Poisson fit over thousands of heterogeneous international matches
  trivially recovers near the population frequency; the model adds essentially
  no match-specific value over the mean.
- **No per-window skill guarantee.** Samples are 356–1,231 matches per window;
  a ±0.03 log-ratio is well inside sampling noise of that size.

## Strongest limitations

1. **International data ≠ club leagues.** The training set is international
   fixtures (martj42), whereas the model's stated use case is domestic club
   betting. International team-strength variance and scoring rates differ from
   club leagues, so even the (weak) calibration found here is unlikely to
   transfer.
2. **Thin team history.** Many international sides have <10 relevant earlier
   matches in a training cut; attack/defence estimates are noisy and collapse
   toward the league average (1.0) for sparse teams.
3. **No market odds.** There is no comparison against bookmaker-implied
   probabilities, the real benchmark for a betting signal. A calibrated
   probability only matters if it disagrees productively with the market; that
   question is untested here.
4. **Aggregate-only calibration.** Reliability-by-bin breakdowns and
   edge-detection by threshold are not performed; only a scalar mean vs
   frequency comparison.

## Conclusion

**Not a calibrated betting signal.** This is a **research estimator** with
reasonable aggregate calibration but no demonstrated predictive edge over the
base rate (and a slightly *worse* Brier than base rate for BTTS). It should not
be used to place bets, back a line, or size a stake. At best it is a
studiable foundation: future work would need club-league data, per-bin
reliability, comparison against closing market odds, and robustness to thin
team histories before any edge claim could even be considered.
