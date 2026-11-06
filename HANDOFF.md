# BETFORGE HANDOFF
**Generated:** 2026-11-06 · **By:** Hermes running the BetForge inner loop (owner override D005)
**Purpose:** context transfer point. Architectural decisions + next steps only — no code.

---

## 1. Verified current state

- **Repo:** `/home/moronto/src/betforge`, branch `audit/bf-001`, 6 commits, no remote.
- **Tests:** 17/17 pass (model, API, degenerate-input, eval smoke). Command: `.venv/bin/pytest -q`.
- **Wheel:** builds clean; ships only package modules. Core + FastAPI import with **no** numpy/pandas (those live in the optional `[fast]` extra).
- **Data:** `data/matches.csv` = **238,854 club matches** 2000–2026 from xgabora (MIT repo; source football-data.co.uk — license unverified for commercial reuse). Columns: `home,away,home_goals,away_goals,date,home_odds,draw_odds,away_odds`. International set backed up at `data/matches-INTL-backup.csv`.
- **Vectorized backtest:** `scripts/eval_model.py` → **0.68s** for 70,523 out-of-sample tests across 2019–2024 (was ~15 min pure-Python). Odds columns ARE used as features (de-vig + market blend, weight 0.5). Output: `docs/eval/backtest-club-output.txt`.

### The load-bearing honest number
- **Calibration:** near-perfect for Over1.5 (pooled log-ratio **+0.009**).
- **Skill:** Brier Over1.5 **0.1924** vs base-rate baseline **0.1907** → the model does **NOT** beat "always predict the mean". Odds features tightened calibration but did NOT create a profitable value signal yet.
- Verdict: well-calibrated, **no demonstrated edge**. Best current statement in `docs/eval/model-eval.md` (international version) — needs a club-data + odds re-write of that doc.

---

## 2. Exact next 3 tasks (in order)

1. **Shift to market-implied / value betting.** Stop optimizing Brier; adopt **log-loss + ROI/CLV**. Rule: only flag a value bet when model P > de-vigged market implied P by a threshold. Model currently has no edge — this is the phase that fixes it.
2. **Upgrade the model.** Replace single independent-Poisson with **bivariate Poisson** (Dixon-Coles) or **xgb on Dixon-Coles residuals**, using the odds as inputs. Keep the vectorized backtest as the harness.
3. **Persist data + serve.** Move ingested CSV → **SQLite** (SQLAlchemy) so the FastAPI app doesn't load a 45 MB CSV per startup; then a real deploy (needs a target unlocked).

---

## 3. Blockers / decisions still open

- **Deploy target: none.** Docker daemon permission-denied (policy forbids sudo fixes). Railway CLI is a broken/partial install. `gh auth` unverified (status call hung). A real deploy needs one unlocked path.
- **Data license:** football-data.co.uk has no formal open license; the MIT on the xgabora repo covers assembly only — decide before monetizing.
- **No API keys in env** — fine for local, required for live feeds.
- **No wagering path wired** — correctly so.

---

## Key conventions carried forward
- No fabricated results / no self-graded gates: a gate is a REAL command's exit code, quoted. `UNVERIFIED` when it couldn't run.
- Verify sub-agent artifacts on disk; never trust a self-report (a child once reported a 0-byte file as run → caught, re-ran).
- Courtesies: mean team only. Nigeria/Pidgin English. Concise progress/errors.
- Skills already installed on this host that apply: `python-package-bootstrap`, `ml-engineering`, `automatic-dispatch`.
