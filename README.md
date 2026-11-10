# ss//betforge — Football Value Analytics (Paper-Trading Only)

BETFORGE is a football **prediction + backtesting engine** for Over 1.5 goals and
Both Teams To Score, with value-signal detection, a **paper-trading simulator**,
and a **Minute-7 research** module. It is **analysis & paper trading only —
there is no real-money betting automation and no API to place a real bet.**

> ⚠ Paper Trading Mode — Not Financial Advice. Stake limits are configurable
> (default 1% of paper bankroll, hard max 5%); a daily-loss cap is enforced.
> Gambling can be harmful — risk nothing real.

Repo layout: `backend/` (Python/FastAPI) + `frontend/` (Next.js) + `data/` + `scripts/`.

```text
betforge/
├── src/betforge/            # Python package
│   ├── models.py            # Poisson / Dixon-Coles core (prediction, stdlib)
│   ├── normalization.py     # canonical Match contract (FT goals, validated)
│   ├── storage.py           # SQLite store (238k matches), stdlib sqlite3
│   ├── api.py               # FastAPI app (/health /predict …)
│   ├── product_api.py       # /api/matches signals backtest paper research settings accuracy
│   ├── features.py          # no-lookahead rolling team features
│   ├── models_engine.py     # poisson + dixon-coles + ML + weighted ensemble
│   ├── backtest.py          # event-driven, strict no-lookahead engine + metrics
│   ├── signals.py           # value detection (edge vs de-vigged market) + mock alerts
│   ├── paper.py             # ₦ paper bankroll, ledger, hard caps, daily-loss stop
│   ├── minute7.py           # Minute-7 hypothesis + z-test research
│   ├── devig.py             # stdlib de-vig + 1X2->O1.5/BTTS market proxy
│   └── settings.py          # responsible-use policy (caps, stakes, edge)
├── tests/                   # pytest (82 passing)
├── frontend/                # Next.js 15 dashboard (cyberpunk, recharts)
├── docs/minute7-hypothesis.md
├── scripts/{seed_historical.py, run_backtest.sh, simulate_signals.sh}
└── data/                    # sample CSVs (gitignored; large/licensed)
```

## Quickstart

```bash
# backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -e ".[test,web]" ruff mypy
cp ../.env.example .env            # leave blank = paper-only mock
uvicorn betforge.api:app --port 8000

# seed the SQLite training store (already present as betforge.db via scripts/ingest_db.py)
python scripts/seed_historical.py data/matches.csv betforge.db

# CLI backtest + demo signals (real metrics, honest caveats printed)
bash scripts/run_backtest.sh O1.5 5 2500
bash scripts/simulate_signals.sh

# frontend (second terminal)
cd frontend && pnpm install
BETFORGE_API_URL=http://127.0.0.1:8000 pnpm dev   # :3000
```

## Gates (acceptance)

```bash
cd backend
.venv/bin/ruff check src/betforge            # clean
.venv/bin/pytest -q                           # 82 passed
.venv/bin/mypy --strict src/betforge/models_engine.py src/betforge/backtest.py src/betforge/signals.py   # clean
cd ../frontend && pnpm build                  # clean (7 pages + landing + BFF)
```

## Backend API (FastAPI)

| Endpoint | Purpose |
|---|---|
| `GET /health` | liveness + data loaded |
| `GET /predict` | strength/Dixon-Coles O1.5 + BTTS prediction |
| `GET /api/matches` | sample matches + odds + model probs + edge |
| `GET /api/signals` | active value signals (edge ≥ threshold, capped ₦ stake) |
| `POST /api/backtest` | run backtest (strategy, edge, stake plan, sample) → metrics + curve |
| `GET /api/paper` | paper bankroll + ledger + curve |
| `POST /api/paper/place` / `POST /api/paper/settle` | paper bet lifecycle (guarded) |
| `GET /api/research/minute7` | Minute-7 hypothesis report + goal distribution |
| `GET /api/accuracy` | honest Brier vs base-rate calibration |
| `GET /api/settings` | responsible-use policy + knobs |

## Responsible-use (implemented, not cosmetic)

- **No real-bet path.** There is no API, CLI or UI surface that places, takes or
  settles a real bet. "Paper" is enforced end-to-end.
- **Stake caps.** Default 1% of paper bankroll per bet; absolute ceiling 5%
  (`stake_cap_frac` / `hard_max_stake_frac`), applied after quarter-Kelly too.
- **Daily loss cap.** Once realised paper losses today reach the cap, the trader
  hard-stops until the next day.
- **Notice everywhere.** Every page carries the "Paper Trading Mode — Not
  Financial Advice" banner; the footer carries the responsible-gambling notice.

## Honesty (the load-bearing part)

This product was deliberately built as a **calibration tool, not a betting bot**
(verified in the repo's HANDOFF). Two honest facts you should not paper over:

1. **The backtest market comparison uses a 1X2-derived O1.5/BTTS PROXY** — the
   core dataset has 1X2 closing odds but no real O/U closing line. That proxy is
   systematically miscalibrated (it under-predicts O1.5 by roughly +0.07 in
   season after season), so **any edge/ROI measured against it is NOT evidence
   of real value.** The engine, strategies, metrics and no-lookahead discipline
   are real and correct; the *profitability* numbers are not a claim. The CLI
   and dashboard both print this caveat.
   **This is now fixed for the Over 2.5 strategy**: we ingest the real
   football-data.co.uk **closing O/U 2.5 line** (`scripts/ingest_ou_data.py`,
   8,675 matches) and the `O2.5` backtest compares against that real line.
   The honest result: **ROI ≈ −6.2%** (942 bets, 50.9% win rate) — the model
   cannot beat an efficient real closing line and loses roughly the margin.
   That negative number is the truth; the +121% on the 1X2 proxy was the
   artefact of the proxy's bias.
2. **The model does not reliably beat the base rate** on the historical eval
   (the earlier full-season holdout showed Brier ≈ base-rate). `GET
   /api/accuracy` shows the current pooled Brier vs base rate and labels it
   honestly; an edge is asserted only where it actually holds.

## Data & sources

- Training: `betforge.db` — 238,854 club matches (2000–2026), 1X2 odds, from
  free/public CSV sources. License: assembly MIT (xgabora); upstream
  football-data.co.uk has no formal open license — review before commercial use.
- Intentional mock fallbacks (documented, env-swappable): no odds feed → mock
  generator; no live feed → mock minute-by-minute; no alert credentials → mock
  adapters log to console + in-memory. See `.env.example`.
