# BETFORGE HANDOFF
**Generated:** 2026-11-06 (updated) · **By:** Hermes running the BetForge inner loop (owner override D005)
**Purpose:** context transfer point. Architectural decisions + next steps only — no code.

---

## 1. Verified current state

- **Repo:** `/home/moronto/src/betforge`, branch `audit/bf-001`, **9 commits**, no remote.
- **Tests:** **18/18 pass** (model, API, degenerate-input, eval smoke, storage). Command: `.venv/bin/pytest -q`.
- **Model:** Poisson/Dixon-Coles Over1.5 + BTTS core, stdlib-only. `models.py`/`normalization.py` are UNCHANGED since the scaffold — verified byte-for-byte. numpy/pandas live only in the optional `[fast]` extra; core + API import without them.
- **Data:** `data/matches.csv` = **238,854 club matches** 2000–2026 from xgabora (MIT repo; source football-data.co.uk — license unverified for commercial reuse). Columns: `home,away,home_goals,away_goals,date,home_odds,draw_odds,away_odds`. International set backed up at `data/matches-INTL-backup.csv`.
- **SQLite (Phase B, DONE):** `betforge.db` (21 MB, WAL) holds all 238,854 rows. Source of truth for the API. Built via `scripts/ingest_db.py`; gitignored build artifact. Storage layer: `src/betforge/storage.py` (stdlib sqlite3, no ORM).
- **API:** `src/betforge/api.py` reads matches from `betforge.db`, not the CSV. DB path resolves via `BETFORGE_DB` env (default `./betforge.db`). `/health` and `/predict` both serve with `provenance`.
- **Docker (Phase C, DONE):** image `betforge:0.1.0` (~271 MB). Build ingests the DB at build time. Set `ENV BETFORGE_DB=/app/betforge.db`. Run:
  ```
  sudo docker run -d --name betforge -p 8125:8000 betforge:0.1.0
  ```
- **Verified live (exact curl):**
  ```
  curl -s -w "\nHTTP %{http_code}\n" http://127.0.0.1:8125/health
  {"status":"ok","matches_loaded":238854,"source":"betforge.db (sqlite)","adb":"/app/betforge.db"}
  HTTP 200
  ```
  `/predict?home=England&away=Brazil` → `p_over1_5 0.7407`, `p_btts 0.5375`.

### The load-bearing honest number (unchanged)
- **Calibration:** near-perfect for Over1.5 (pooled log-ratio **+0.009**, 0.68s vectorized eval, 70,523 OOS matches).
- **Skill:** Brier Over1.5 **0.1924** vs base-rate baseline **0.1907** → the model does **NOT** beat "always predict the mean". Deployed API is a **calibration tool, NOT a betting bot**. No edge claimed — per the owner's contract, ship-as-calibration-tool.

---

## 2. Exact next 3 tasks (in order)

1. **Edge (value betting) — NOT yet attempted (owner HALT on XGBoost).** Shift to log-loss + ROI/CLV; flag a value bet only when model P > de-vigged market P by a threshold. Upgrade to bivariate Poisson (Dixon-Coles) or xgb-on-residuals; keep the vectorized backtest as harness. Gate: honest Brier must beat 0.1900 baseline or say "Edge Failed".
2. **Remote deploy — BLOCKED on auth.** Two paths, both need the human: `gh repo create` (GitHub push) or fix the Railway CLI (`npm install -g @railway/cli --foreground-scripts`). Image is self-contained and ready to push. Do not fake a remote deploy.
3. **CLV/odds refresh cadence.** Wire a repeatable odds-ingest so the trained model can be recalibrated against fresh market lines (the current DB is a one-time snapshot).

---

## 3. Blockers / decisions still open

- **Docker access:** daemon socket is `root:docker`, running user is NOT in the group → `sudo docker` is the working path (build/run as root). A permanent fix needs `sudo usermod -aG docker <user>` (not done).
- **Remote deploy:** no git remote; `gh auth` unverified (status call hung earlier); Railway CLI binary broken/partial. One of these must be unlocked by the human.
- **Data license:** football-data.co.uk has no formal open license; xgabora's MIT covers assembly only — decide before monetizing.
- **No API keys in env** — fine for local, required for live feeds.
- **No wagering path wired** — correctly so.

---

## Key conventions carried forward
- No fabricated results / no self-graded gates: a gate is a REAL command's exit code, quoted. `UNVERIFIED` when it couldn't run.
- Verify sub-agent artifacts on disk; never trust a self-report (a child once reported a 0-byte file as run → caught, re-ran).
- Courtesies: mean team only. Nigeria/Pidgin English. Concise progress/errors.
- Skills installed that apply: `python-package-bootstrap`, `ml-engineering`, `automatic-dispatch`, `football-probability-modeling`, `sports-odds-devigging`, `vectorized-walkforward-backtest`, `leakage-safe-model-eval`, `honest-model-evaluation`, `subagent-artifact-verification`, `uv-package-from-docs-repo`.
