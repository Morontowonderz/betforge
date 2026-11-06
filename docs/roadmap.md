# Task board
Statuses: BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFIED; BLOCKED/FAILED/DEFERRED as needed. VERIFIED means the named deliverable was checked, not the product claim proved. Roles below are assignments, not claims that separate agents have executed.

| ID | Phase | Priority | Objective / deliverable | Dependencies | Allowed scope | Role | Acceptance / verification evidence | Status |
|---|---|---|---|---|---|---|---|---|
| BF-001 | 00 | P0 | Bounded repository/environment audit | none | BETFORGE_REPOSITORY_AUDIT.md, docs/EXECUTION_LOG.md, docs/project-state.md, docs/roadmap.md | Coordinator | Scoped search results, Git/tool evidence, limitations and missing repository disclosed; final documentation validation | VERIFIED |
| BF-002 | 00 | P0 | Research-only product charter | BF-001 | docs/product-charter.md, docs/decisions.md, state/log/board | Product/Coordinator | Scope, primary markets, non-goals, legal gates and unknowns explicit; independent document review | VERIFIED |
| BF-003 | 00 | P0 | Provider and data-rights audit | BF-001 | docs/data-rights.md, docs/evidence/bf-003/, state/log/board/decisions | Researcher | Dated first-party citations for API-FOOTBALL and alternatives; market coverage, quotas, storage/redistribution rights, pricing and unresolved permissions distinguished; no subscription | BLOCKED |
| BF-003A | 00 | P0 | Unsent provider clarification drafts | BF-003 partial evidence | docs/provider-clarification-drafts.md, state/log/board | Coordinator | Both drafts cover rights, market/time semantics and billing; no invented recipients or commitments; review and no-send boundary | VERIFIED |
| BF-004 | 00 | P0 | Canonical schemas and architecture | BF-002, BF-003 | docs/data-contracts.md, docs/architecture.md | Architect | Enumerate FT/H1 Over1.5 and BTTS separately; fixture/market/selection/provider IDs, quote states and all clocks; rejection examples reviewed | BACKLOG |
| BF-005 | 00 | P0 | Preregister research | BF-004 | docs/model-validation.md | Quant | Primary hypothesis, timing, estimand, sample-size rationale, chronological splits, holdout freeze, baselines, multiplicity and stop rules reviewed | BACKLOG |
| BF-006 | 00 | P0 | Engineering verification plan | BF-004 | docs/verification-plan.md | QA | Unit/integration/replay/security and clean-checkout protocol; deterministic clock and leakage tests; actual commands selected after package review | BACKLOG |
| BF-007 | 00 | P0 | Risk register | BF-002 | docs/risk-register.md, state/log/board | Reviewer | Rights, leakage, freshness, licensing, operations, budget and responsible-use risks each have owner, trigger and mitigation | VERIFIED |
| BF-008 | 00 | P1 | Customer-discovery plan | BF-002 | docs/customer-discovery.md, state/log/board | Product researcher | Interview protocol, consent, segment hypotheses and disconfirmation criteria; no outreach executed | VERIFIED |
| BF-009 | 00 | P0 | Legal requirements register | BF-002, BF-003 | docs/compliance.md | Compliance researcher | Nigerian and target-market obligations sourced; legal interpretation reserved for qualified counsel; launch blockers explicit | BACKLOG |
| BF-010 | 00 | P0 | Independent foundation gate | BF-003..BF-009 | docs/release-gates.md, state/log/board | Independent reviewer | Read all deliverables, record unresolved blockers and explicit phase decision; no implicit PASS | BACKLOG |

## Proposed Phase 01 backlog (not authorized to bypass BF-010)

| ID | Priority | Objective / expected deliverable | Dependencies | Allowed scope | Role | Acceptance tests and evidence | Status |
|---|---|---|---|---|---|---|---|
| BF-101 | P0 | Minimal package and dependency decision | BF-010 PASS | pyproject.toml, selected lockfile, src/betforge/__init__.py, docs/development.md, decisions | Engineer | Verify dependency authenticity/license and Python compatibility; isolated install/import from documented clean environment; retain command output | BACKLOG |
| BF-102 | P0 | Config and fail-closed boundaries | BF-101 | src/betforge/config.py, tests/unit/test_config.py, .gitignore, .env.example | Engineer | Reject live wagering mode; missing secrets fail safely; no secrets logged; environment examples contain names/placeholders only | BACKLOG |
| BF-103 | P0 | Typed canonical contract validators | BF-101, BF-004 | src/betforge/normalization/, tests/unit/test_contracts.py | Engineer | FT/H1 confusion, ambiguous IDs, naive timestamps, invalid decimal odds and unknown status rejected; deterministic test output | BACKLOG |
| BF-104 | P0 | Verification tooling and CI definition | BF-101..BF-103, BF-006 | .github/workflows/ci.yml, pyproject.toml, tests/, docs/development.md | QA/Engineer | Actual lint/type/test/build commands pass locally and clean checkout; CI hosted run remains UNKNOWN until approved publication | BACKLOG |
| BF-105 | P1 | Contribution and safety context | BF-101 | AGENTS.md, CONTRIBUTING.md, docs/release-gates.md | Coordinator | Scoped work, secrets, rights and approval gates documented; independent review | BACKLOG |

Next priority: owner review of BF-003A drafts and specific send approval; do not contact providers without it. BF-004/BF-009 remain dependency-gated. No Phase 01 task may start merely because local documentation exists.
