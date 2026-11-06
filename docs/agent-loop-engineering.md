# BetForge agent-loop engineering (design)

**Date:** 2026-11-06 · **Scope:** how autonomous agents maintain and ship BetForge
**Context:** owner override D005 (build now); free/public data only; owner wants to
batch their attention — the system must run unattended and only surface decisions.

---

## 1. Why a loop (and what we are NOT doing)

BetForge's real work is *recurring* and *verifiable*: refresh data, retrain,
re-evaluate calibration, gate deploys. A plain "write code per prompt" workflow
leaks the owner's attention into every step. We want the mechanical, evidence-based
parts to run themselves and only escalate when a decision needs a human (a named
operator, a license call, a real listing, a payment).

We are NOT building an unbounded agent that mutates prod or spends money. Every
loop exits to a **human gate** (kanban `blocked`) when it meets a decision the
policy reserves for the owner. That reservation list is explicit (§4).

## 2. Roles / module responsibilities

| Role | Owns | Gates on | Evidence it must produce |
|---|---|---|---|
| **Collector** | refresh data from approved free sources (`collection.py`) | source license check | row counts, provenance, hash |
| **Normalizer** | canonical `Match` contract; reject malformed rows | contract validation | reject counts, sample diff |
| **Modeler** | Poisson/Dixon-Coles estimation (`models.py`) | training window policy | params, matrix sanity |
| **Evaluator** | out-of-sample backtest + calibration (Brier, log-ratio) | eval passes degradation threshold | numbers from a real run |
| **Deployer** | build wheel + optional service image | CI green + eval pass + human approve | artifact hash, health probe |
| **Auditor** | every loop writes evidence to `docs/eval/`, `docs/state` | none (read-only) | dated, signed-off evidence |

## 3. The loop (closed with evidence)

```
              ┌──────────────────────────────────────────────┐
              ▼                                              │
   [COLLECTOR] refresh free data ──► [NORMALIZER] validate   │
                                                    │        │ avoid data/overwrite
                                                    ▼        │        without
                                            [MODELER] retrain─┤  both eval pass
                                                    │        │  and license check
                                                    ▼        │
                                            [EVALUATOR] backtest  calibration OK?
                                                    │        │
                          no (degrade) ────────────┤ yes     │
                              │                     ▼        │
                              │            [DEPLOYER] build+stage ──► CI
                              │                     │
                              ▼                     ▼
                        audit + escalate       human gate: authorize publish?
                                                    │ yes
                                                    ▼
                                              [AUDITOR] record → (external deploy)
```

Invariants enforced by the loop:
- A **ready card must be finishable without inventing the blocked artifact**
  (e.g. "deploy first reviewed home" requires a named operator — that card must be
  `blocked`, never re-opened as implementation).
- Training and evaluation data are **never mixed**: prediction for window W only
  sees matches strictly earlier than W (see `scripts/eval_model.py`).
- No model change is trusted on its own self-report. The **Evaluator's numbers from
  a script run** are the only thing that moves a card from ready → review.

## 4. Human-gate reservation list (do NOT auto-decide)

1. **Named human/data**: a real listing needs a named operator who controls the
   room/property and authorized the photos. Never auto-contact.
2. **Sending/publishing** that was not authorized (merge to prod, a live message,
   a payment). The exact action must be written on the card.
3. **Governance overrides**: elected gate direction chooses providers, monetization,
   or monetizable licensing (e.g. football-data.co.uk terms) — owned by the owner.
4. **Live money / live feeds**: no subscribed API, no wagering path is ever
   autopiloted.

## 5. Agent selection & parallelization strategy

Autonomous-agent skills available on this host: `codex`, `claude-code`, `opencode`,
`hermes-agent`, `computer-use`. Selection by task type:
- **Package / model / CLI / tests** (pure code, fully specifiable) → a single
  `hermes-agent`/codex child with an explicit file-scope contract. Give it the
  exact files it may write and the acceptance tests; verify its artifacts directly
  (a child's self-report is not evidence — read the files it wrote, run its tests).
- **Independent research** (data sources, licensing, market) → spawn parallel
  read-only children, each must return shifted URLs/licenses/facts, then I check.
- **Breadth-first repo work** where failures are cheap → `claude-code`/`codex` in
  an isolated worktree (never the owner's checkout of main).
- **Anything touching external state or a browser** → `computer-use` only for
  already-authorized, already-logged-in sessions; otherwise blocked.

Spawn discipline (this session demonstrated the pitfalls):
- Give each child **all context it needs** — children know nothing of this
  conversation. Repeat shared facts in every task that needs them.
- **Verify, don't trust**: a child wrote an empty `backtest-output.txt` and claimed
  it had run; the real run is still re-running here. Always re-open/run artifacts
  a child produced before reporting them as done.
- Children can't close tracked work or ask questions; they return findings — the
  coordinator applies transitions.

## 6. State & evidence layout (machine-checkable)

```
docs/eval/            backtest-output.txt, model-eval.md     (tightly dated)
docs/research/        free-data-sources-2026.md              (dated, cited)
docs/state/           last-refresh.json                      {source,hash,rows}
data/                 matches.csv (git-ignored by size; source pinned elsewhere)
scripts/              eval_model.py, refresh_data.py         (one command each)
```

## 7. Loop operational rules

- **One change per loop**, otherwise cards collide and a reviewer can't tell which
  change moved a number.
- **Slow/degenerate inputs get tests first**: all-0-0 league, empty team list,
  missing date, non-integer goals (already in `tests/test_models.py`).
- **Degradation rule**: if pooled Brier or  log(realized/mean) worsens past a
  threshold vs the prior loop, the loop stops and escalates instead of deploying.
- **Admit the blocker plainly.** A webserver that can't reach docker, a railway
  shim that isn't a working binary, an empty eval file — all reported as blockers,
  never papered over.

## 8. What the human does (kept minimal, batched)

At most a few genuine decisions per cycle; everything else is evidence. Target:
the owner touches BetForge only to (a) approve a real listing/operator, (b) pick a
provider or monetization policy, (c) answer one gated rollout, or (d) open an
authenticated session for a deploy that needs creds.
