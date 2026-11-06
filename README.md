# BetForge — prediction core (Phase 01 scaffold)

Research core for football **Over 1.5 goals** and **Both Teams To Score**
probabilities, built dependency-light on free/public data.

> Owner override (D005, 2026-11-06): the Phase-00 foundation gate was
> deliberately skipped to produce this engineering scaffold. This is a
> research estimator, not a wagering signal and not a live product. No
> edge or live deploy is claimed. See `docs/decisions.md`.

## Status
- Python package, no runtime deps (predictions use only the stdlib).
- Source: free/public CSV of matches (columns: `home, away, home_goals,
  away_goals[, date]`).
- Model: Poisson joint goal distribution with optional Dixon-Coles `rho`
  correction, marginalized to P(Over1.5) and P(BTTS).
- Tests: `pytest`.

## Quickstart
```bash
pip install -e .[test]
betforge ingest   data/matches.csv
betforge predict  data/matches.csv --home Arsenal --away Chelsea --json
```

## Layout
```
src/betforge/
  collection.py    ingest + provenance
  normalization.py canonical Match contract (FT goals, validated)
  models.py        Poisson/Dixon-Coles joint goal distribution
  cli.py           ingest/predict entry point
tests/             unit tests
```

## Limits (honest)
- FT only; HT/H1 markets are out of scope here (BF-004 requires separation).
- Team names are exact strings; no provider ID mapping yet.
- No market quoting, no live fixture ingestion, no wagering path.
