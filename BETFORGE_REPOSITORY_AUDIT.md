# BETFORGE repository and environment audit — BF-001

Audit date: 2026-10-20 (host clock, WAT). Status: scoped inventory VERIFIED; recovery of historical implementation UNKNOWN. Phase 00 incomplete.

## Evidence and scope

VERIFIED: Starting directory was `/home/moronto/src/moronto-mornica-antigravity`, branch `agent/antigravity-mornica-launch-contract-20261019`, HEAD `8ee2190d66518636864bf2f2a2d9e5c61130bbf9`. `git status --short` returned no changes. Its recent history concerns an Android music app, not BETFORGE. No files there were changed.

VERIFIED: Targeted content searches across `/home/moronto/src`, `/home/moronto/Projects`, `/home/moronto/Work` for `betforge|football_betting|sportybet|over_1_5|btts|shadowflat|dynamic_kelly|betforge.v2.yaml` in Python, Markdown, YAML, TOML and JSON returned no matches (search_files results). These searches are not proof of absence in ignored files, archives or other locations.

VERIFIED: Earlier bounded filename traversal of src, Projects, Work, agent-orchestrator, deepseek-harness, Documents, Downloads and Desktop found only `/home/moronto/Documents/gods-eye-view/dist/cesium/Assets/Textures/maki/america-football.png`, an unrelated image asset. `/home/moronto/.local/bin/betforge` contains a shell launcher invoking Hermes with `-p betforge`, not a football engine. The corresponding profile directory is runtime configuration, not application source.

VERIFIED: `gh api --paginate --slurp 'user/repos?per_page=100&affiliation=owner,collaborator,organization_member'` exited 0 and returned 50 repositories. Programmatic filtering of name and description for betforge, football, betting, sportybet and shadowflat returned no candidates. Earlier `gh repo list` returned only owned repositories; it was not the full accessible inventory. Remote repository contents, alternate branches, organization archives and deleted repositories were NOT exhaustively searched. Historical implementation therefore remains UNKNOWN, not proven nonexistent.

## Verified repository inventory

- Path: `/home/moronto/src/betforge`, newly initialized local documentation repository, not recovered historical code.
- Conflict checks: path did not exist and was not a symlink; `/home/moronto/src` is not a Git repository; no parent AGENTS.md, .hermes.md, CLAUDE.md or HARNESS.md found in home/src.
- Ownership: local Linux account `moronto`; product organization ShadowSpark Technologies is user-supplied context, not verified legal ownership.
- Remote: none (`git remote -v` empty). No remote created or push attempted.
- Branch: `audit/bf-001`, unborn; no commit exists. No commits authorized or made.
- Tree: root audit plus `docs/` for charter, decisions, roadmap, state and execution evidence. Exact final paths and status: `git status --short --untracked-files=all`.
- Existing executable components: none found for BETFORGE.
- Existing configuration/lockfiles/package scripts: none recovered or introduced.
- Tests/results: no application tests exist; no application functionality tested. Documentation checks are not software tests.
- CI: none.
- Infrastructure/deployments: none verified. No cloud, database, containers or accounts created.
- Dependencies: none declared or installed for BETFORGE.
- Current architecture: documentation only. Six-layer modular monolith is a proposal, not implemented architecture.

## Environment evidence

Commands on 2026-10-20:

- `id -un`: moronto; HOME `/home/moronto`.
- `df -h /home/moronto`: root volume 147G, 128G used, 17G available, 89% used. Large datasets/container builds require capacity review.
- `hermes --version`: Hermes Agent v0.22.2 (2026.9.24), stable, local d923a5eb487a; Python 3.14.7; OpenAI SDK 2.24.0. CLI also printed “Up to date”; no independent upstream verification performed.
- HERMES_HOME: `/home/moronto/.hermes/profiles/betforge`.
- Allowlisted config inspection: stored model default `google/gemini-3.8-flash`, provider `nous`. Current session runtime/user switch reports `gpt-6-astra` via `openai-codex`; persisted default is distinct from the session override. No routing changed.
- Python 3.14.7; Git 2.56.0; Node v24.21.0; Docker CLI 29.9.1; gh 2.102.0.
- `command -v`: psql at `/usr/bin/psql`, uv at `/home/moronto/.local/bin/uv`; pytest, ruff, pygount absent from PATH. Python modules/virtual environments not exhaustively inventoried. No package installation required for audit.
- GitHub authentication reported account Morontowonderz; accessible read-only inventory succeeded. No tokens intentionally read or saved.
- `docker info --format '{{.ServerVersion}}'`: permission denied at unix:///var/run/docker.sock. Docker daemon usability BLOCKED; no sudo/group/socket changes attempted.
- API_FOOTBALL_KEY, APISPORTS_KEY, API_SPORTS_KEY, RAPIDAPI_KEY, DATABASE_URL, PGHOST and TELEGRAM_BOT_TOKEN: not present in tool process environment. This does not establish absence from secret storage. Credential files were not read.
- Available session tools include terminal, file operations, web research, browser, delegation, skills, clarification and deferred task/session tooling. Availability does not verify external-service authentication. Skills loaded: hermes-agent, codebase-inspection, github. No global configuration changes.

## Security and audit limitations

VERIFIED: Earlier continuation history included an overbroad home traversal that timed out after 180s (exit 124), and a .config content search that returned browser-related filenames. These are not valid exhaustive evidence. No further browser/private-data inspection was performed. Future recovery searches must stay bounded to approved project assets. Do not repeat broad home/config scans.

VERIFIED: A presumed Hermes Python path did not exist: `/home/moronto/.hermes/hermes-agent/.hermes/bin/python: No such file or directory`. A minimal standard-library, allowlisted config reader succeeded instead. Earlier `hermes version` was invalid/inconclusive; `hermes --version` succeeded. Git parent-scope check intentionally returned 128 because src is not a repository. Other successful version commands in that batch must not be described as failed because of its final exit code.

UNKNOWN: data licenses, commercial reuse/redistribution rights, live market coverage, quotas, legal permissions, historical data quality, functioning signals, strategy performance, customer demand and sustainable economics. No wagering edge or profitability established. No live provider requests, wagers, customer messages or deployments performed.

## Reuse and missing requirements

INFERRED: Python/Git/uv and existing authenticated GitHub CLI can support future local tooling. Compatibility of statistical dependencies with Python 3.14 must be checked before adoption. No source reuse approved or copied from unrelated projects; no authentic BETFORGE utility discovered. PostgreSQL client availability does not prove a configured database.

Missing: historical source provenance, provider rights evidence, canonical market/time contracts, registered research hypotheses, evaluation thresholds, tests, CI, application package, data storage design, legal review and customer evidence.

## Recommended next changes

1. Complete BF-002 product charter with explicit research-only scope and approval gates.
2. BF-003 provider/rights audit: first-party technical and terms sources; separate technical availability from permitted commercial use.
3. Specify canonical contracts and leakage-safe validation before implementing acquisition/models.
4. Only after Phase 00 review, propose `src/betforge/{collection,normalization,models,decisions,delivery,audit}`, `tests/{unit,integration,replay}`, `docs/`, and later pyproject/lockfile/CI. These are proposed paths, not existing functionality.

Phase-gate decision: NOT YET EVALUATED. Numeric readiness score withheld: roadmap quality is not evidence of product readiness.
