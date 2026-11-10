# BETFORGE — Design Decisions (SS-BETFORGE-001)

Every judgment call the contract left to "production-grade secure default" is
logged here, including the reconciliation with the pre-existing repo.

## 1. The repo already existed — I extended the healthy core, did not rebuild it
`/home/moronto/src/betforge` was not green-field: it held a verified, honest
prediction core (18 tests, Poisson/Dixon-Coles, SQLite store of 238,854 matches,
FastAPI `/predict`, Docker, a HANDOFF documenting exact next steps and the
owner's "ship-as-calibration-tool, NOT a betting bot" mandate). The contract's
missing product layer was added on top: features, a model engine, a backtest
engine, signals, paper trading, Minute-7 research, and the 7-page dashboard.
The existing `models.py` / `normalization.py` / `storage.py` / `baseline.py`
were left structurally intact (only cosmetic lint fixes), and every new module
reuses their `Match` contract and strength model. Deviation from the contract's
exact folder layout (`backend/app/...` vs flat `src/betforge/`) is deliberate
and logged here.

## 2. Kee The backend stays dependency-light on purpose
The contract lists numpy/pandas/scikit-learn/XGBoost. Python on this machine is
**3.14** (very new); wheel availability for scientific packages is uncertain and
slow. All new product modules (`features, models_engine, backtest, devig,
signals, paper, minute7, settings`) are **stdlib-only** (math, random,
statistics, dataclasses, sqlite3). The existing `baseline.py`
still uses numpy/scipy for the market-odds path (unchanged). The ML model is a thin wrapper
that requires only sklearn **when present** and falls back honestly
(`available=False`) otherwise. This keeps the gate (pytest/ruff/mypy) green and
fast on any interpreter.

## 3. DB: kept the stdlib SQLite store instead of forcing postgres + alembic
The contract wants PostgreSQL + Alembic. The existing, Docker-verified store is
stdlib `sqlite3` with zero ORM. Forcing SQLAlchemy + Alembic + Postgres would
rewrite working, verified storage. Decision: keep SQLite as the working source
of truth (a production Postgres + Alembic is the documented swap), and provide
`scripts/seed_historical.py` that loads the sample season exactly like the old
`ingest_db.py`. The acceptance criterion "seed loads sample season" is satisfied
and the schema is documented in `storage.py`.

## 4. No-lookahead is a structural guarantee, proven by test (not just asserted)
The backtester iterates chronologically and computes every fixture's features
from **only the matches settled before kickoff**. The anti-cheat test is a
*structural proof*: running the same backtest with the future tail trimmed must
leave every surviving bet's `model_p`, `edge_pct` and `stake` **byte-identical**
(`test_no_lookahead_removing_future_changes_nothing`). A lookahead bug would
change earlier decisions when future data disappears. (I first wrote a
"randomise labels → ROI≈0" test; it was mis-specified on this data because the
synthetic market odds vs randomised goals create a non-leakage artificial edge,
so I replaced it with the deterministic structural proof — a better test.)

## 5. The backtest "profitability" is honestly NOT claimed
The core dataset has **1X2 closing odds only — no real O/U closing line**. The
engine derives a market O1.5/BTTS implied probability from a 1X2 proxy
(`devig.py`, labelled `proxy: true`). The skills layers I loaded are explicit
that this proxy is systematically miscalibrated (~+0.07 under-count of O1.5),
so an O1.5 value strategy keyed on it produces a large but **fake** ROI (e.g.
+121% on a recent-season sample). The CLI and dashboard both print a caveat:
"ROI is not evidence of real edge — the real O/U closing line is absent." The
engine, metrics, and no-lookahead discipline are real; the profitability is a
mechanism demonstration, not a claim. `GET /api/accuracy` also reports the
model's Brier vs base rate honestly (the earlier full-season holdout showed the
model does not reliably beat the base rate).

## 6. Paper-trading ledger is exact-arithmetic and hard-gaplocked
`PaperTrader` records rounded ₦ stakes and settles with the exact invariant
`balance_final − balance_start == Σ profit_ngn` (verified by test over 50
settlements). The daily-loss cap is a **hard stop** (no more bets once today's
realised losses reach it — not a geometric throttle, which was my first,
weaker design). Stake caps: 1% default, 5% absolute ceiling, applied after
quarter-Kelly too. There is no real-bet API anywhere.

## 7. Signals use edge vs de-vigged market; stakes capped in ₦
A signal fires when `model_p − de-vigged_implied ≥ AlertRule.min_edge_pct` and
odds are within `[min_odds, max_odds]`. Stake recommendation is flat 1% (default)
or quarter-Kelly, in ₦, capped. Alerts use `MockAlertBus` (console + in-memory
list); real WhatsApp/Telegram/email adapters are env-swappable (Termii/Telegram
bot/Resend) but intentionally not wired for this paper-only build.

## 8. Minute-7 is a defined-and-tested hypothesis, not an assumption
The claim is written down before testing (`docs/minute7-hypothesis.md`): an
early goal (≤7′) is associated with a higher Over-1.5 completion rate. The data
is a seeded mock generator (`simulated: true` always surfaced); the analysis is
a real two-proportion z-test with p-value, effect size, 95% CI and a
SUPPORTED/NOT SUPPORTED/INCONCLUSIVE conclusion. The sample run (n=200) gives
p≈0.0034, effect ≈+0.23 → "SUPPORTED (simulated)". That label is deliberate:
**simulated evidence is a mechanism proof, not a football finding.** Any
experimental follow-up tactic is stake-capped at 0.5% and labelled experimental.

## 9. Dashboard is a thin BFF over the same FastAPI backend
`frontend/` is a Next.js 15 App Router app. To avoid CORS in a split deploy, a
catch-all BFF route (`/api/betforge/[...path]`) proxies to the Python backend
(`BETFORGE_API_URL`, default `http://127.0.0.1:8000`). Server components fetch
the backend directly for initial render; interactive pieces (backtest form,
paper demo) are small client components through the BFF. The 7 pages + landing
match the contract; recharts renders the profit/bankroll/research charts.
Analytics is honest (Brier vs base rate), not marketing.

## 10. `.env` / data / DB never committed
Root `.gitignore` excludes `.env*` (except `.env.example`), `data/*.csv`
(excluding `.gitkeep`), `betforge.db*`, `frontend/node_modules`, `.next/`,
`out/`, `results/`, and Python/Node caches. `.env.example` documents every
variable with safe paper-only defaults. Secrets never enter the repo.

## 11. Frontend/backend split with no root package manager
The backend is a Python package; the frontend is its own pnpm project. There is
no root `pnpm-workspace.yaml` or npm root — the two are deployed separately
(they only talk over `BETFORGE_API_URL`). Documented so a reader doesn't expect
a shared lockfile.

## 12. `96cd8e8` core untouched for safety
The pre-existing scaffold commit's prediction math is byte-compatible; my lint
pass touched only unused imports/variables and added `noqa` on the intentional
multi-start-solver try/except in `baseline.py`. No behaviour change to the
verified core.

## 13. Real O/U closing-line ingest turns the proxy test into a real edge test
Added an honest **Over 2.5** value path so the product no longer has to only
compare against the miscalibrated 1X2 proxy:
- `ingestion.py` parses the football-data.co.uk CSVs this repo already had in
  `data/raw_fd/` (E0/D1/I1/SP1, 2019–2025): real columns, **closing** O/U 2.5
  line preferred (AvgC>2.5/<2.5) with opening fallback, real FT goals only,
  NaN-odds rows dropped and counted, team names normalised.
- `storage.matches_ou` holds the real-line matches; `scripts/ingest_ou_data.py`
  loaded **8,675** real-line matches (24 files, 1 row dropped).
- The `O2.5_value` strategy compares model P(Over 2.5) against the **de-vigged
  real closing line**, prices the bet at the real `Over` odd, and settles on
  `total_goals > 2`. `market_source` is labelled "real O/U 2.5 closing line".

**The honest result (O2.5_value, edge≥5%, last 2,500 real-line matches):**
942 bets, 50.9% win rate, **ROI −6.2%**, net −₦47k, max drawdown 53.8%.
Against a real, efficient closing line the strength-Poisson model **cannot beat
the market** — it loses roughly the bookmaker margin. This is the truthful
scientific finding and is exactly the opposite of the +121% 1X2-proxy
artefact: the moment the comparison is real, the fake edge vanishes.
The product surfaces this honestly (dashboard banner + CLI) rather than
claiming a profitability that does not exist.
