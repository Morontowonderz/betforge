# Decision log

## D005 — Owner override of the Phase-00 gate (2026-11-06)
OWNER CONSENT RECORDED. On 2026-11-06 the product owner explicitly overrode the BF-010 foundation gate: "skip the gate, integrate a template and build/deploy now (you accept the legal/provider risk)." Direction chosen: Python prediction model (Over1.5/BTTS), free/public data sources only (no API key) for the first build. This does not convert unresolved BF-003 data-rights, BF-009 legal, or volume/quota items into approved facts. The owner accepted the residual risk in writing. Built code remains non-live unless and until separately authorized with real credentials and licensed data.

## D001 — Isolated local documentation repository
VERIFIED: No authentic implementation discovered within the BF-001 search scope. New path /home/moronto/src/betforge passed absence and parent-repository checks. Initialized audit/bf-001 without a remote or commit. Do not identify this as historical recovered code. Evidence: BETFORGE_REPOSITORY_AUDIT.md.

## D002 — Documentation before engineering
DESIGN DECISION: Remain in Phase 00. No dependencies, runtime, CI or model code until contracts and foundation review are complete. Use a proposed six-layer modular monolith; no microservices or dashboard work now.

## D004 — No provider selection or signup yet
DESIGN DECISION (2026-10-21): retain API-Football and Sportmonks as candidates, not approved suppliers. Resolve retention/commercial scope, target live markets, timestamp semantics and billing conflicts before acquisition. Evidence: docs/data-rights.md. Failed documentation retrieval does not authorize challenge bypass.

## D003 — Safe tool and configuration boundaries
DESIGN DECISION: Keep current session override separate from stored Hermes model default. Never mutate global/profile routing, Docker permissions or unrelated repositories to unblock this audit. Inspect credential availability only, never values.
