# Minute-7 Hypothesis

## The claim (defined before testing, not inferred)

**H1:** Matches in which at least one goal is scored **by minute 7** (1–7′) are
**more likely to finish Over 1.5 goals** than matches without an early goal.

- **Null (H0):** The Over-1.5 outcome probability does not differ between the
  early-goal group and the no-early-goal group.

This is a *strength-of-effort* hypothesis: an early goal is evidence that (a)
both sides are creating and (b) the game state (trailing side pushing) raises
the probability of more goals — a pattern that, **if true**, would create an
in-play value opportunity at the ~7′ mark for an "Over 1.5 / Over 2.5 in-play"
tactic.

## Why this exact claim

The minute-7 window is intentionally *short and testable*:
- If goals were uniform across 1–90′, an early goal carries no information.
- If the "early goal ⇒ higher tempo" effect is real on **full-time totals**,
  it is detectable in the FT Over-1.5 outcome — a clean, well-defined binary.
- It is the cheapest, least ambiguous version of the "minute-7 in-play value"
  idea to test before any in-play odds work.

## Data & method

- **Data source (this build):** a mock minute-by-minute generator in
  `src/betforge/minute7.py` — full matches simulated from Poisson goal rates
  (`λ_home`, `λ_away`) with per-goal minutes drawn uniform on 1–90, plus a
  seeded RNG. Flag `simulated: true` is surfaced on every report.
  Real live data replaces the generator via `live_ingest`.
- **Groups:** `early` (≥1 goal in minutes 1–7) vs `no-early`.
- **Test:** two-proportion pooled **z-test** on the Over-1.5 completion rate,
  one-tailed; report p-value, absolute risk difference (effect size) and a 95%
  normal-approximation CI.
- **Decision rule:** `alpha = 0.05`; a p-value above alpha or `|effect| < 0.02`
  or a small group (<30) ⇒ **INCONCLUSIVE**. Otherwise SUPPORTED / NOT SUPPORTED.

## Example output (mock sample, n=200, λ_h=1.4, λ_a=1.2, seed 7)

| Group | n | Over-1.5 finish rate |
|---|---|---|
| Early goal (≤7′) | 33 | 90.9% |
| No early goal | 167 | 67.7% |

- p-value ≈ **0.0034** (z-test, one-tailed)
- effect size ≈ **+0.23** (absolute risk difference)
- 95% CI ≈ **[0.11, 0.35]**
- conclusion: **SUPPORTED (simulated)**

## How to read this — honestly

The generator is seeded and internally consistent, so the test *mechanism* is
provably correct. But **simulated data is not evidence about real football**:
the effect size and p-value here are properties of the generator's λ and goal
minute model, not of real matches. Under that framing the claim is
"plausible / worth testing with real in-play data", never "proven".

### If a real-data follow-up supported it

The contract mitigation is already wired into the product stack:
- The finding is labelled **experimental**.
- An experimental in-play tactic, if enabled, is **stake-capped at 0.5%** of
  paper bankroll (half the default 1% cap) and clearly labelled.
- Everything remains **paper trading only**.

## Files

- `src/betforge/minute7.py` — generator, z-test, `run_hypothesis_test`, report.
- `src/betforge/product_api.py` — `GET /api/research/minute7`.
- `frontend/src/app/research/page.tsx` — research dashboard.
