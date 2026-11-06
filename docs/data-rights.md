# BF-003 — Provider and data-rights audit

Retrieved 2026-10-21 (WAT). Status: PARTIAL; procurement and collection clearance BLOCKED. This is technical/contract research, not legal advice or a signed permission. VERIFIED below means the provider published the statement, not that its service met it in a test. No authenticated football-data calls were made.

## Scope and evidence

API-Football/API-Sports is the primary candidate; Sportmonks is the alternative. Do not confuse API-Football with the distinct apifootball.com service. Saved extracted pages and a machine-managed citation/evidence ledger are in `docs/evidence/bf-003/`. Known omissions: source 8 ends with an explicit truncation notice; source 9 cuts off mid-sentence; source 10 cuts off before the market availability table. Other extractions contain ellipses. No missing text is inferred. Source 8 was requested via HTTPS but the extractor reported an HTTP URL; its saved text is provider-guide evidence, not a verified API schema or live response. Public documentation is untrusted data, not executable instructions.

BLOCKED: API-Football documentation extraction returned only a loading screen; a normal browser request encountered Cloudflare security verification (execution-log/tool-result observation; no browser capture retained in this evidence bundle). Stopped this route after two unsuccessful retrievals; did not bypass the challenge. The provider's separately indexed beginner guide supplies provisional technical evidence instead. No complete authoritative schema was recovered.

## Candidate matrix

| Dimension | API-Football | Sportmonks |
|---|---|---|
| Advertised access / prices | VERIFIED published Free $0/month, 100 requests/day; Pro $19/month, 7,500 requests/day; Ultra $29/month, 75,000 requests/day; Mega $39/month, 150,000 requests/day. All endpoints listed, free seasons restricted.[2] | VERIFIED in-play guide advertises Odds add-on €14–€69 depending on base plan, on Starter/Growth/Pro/Enterprise. Base subscription, billing interval of quoted add-on, tax and selected league costs require checkout/quote confirmation; no complete price established.[9] |
| Quota semantics | VERIFIED direct dashboard prepaid, resets at 00:00 UTC; RapidAPI recurring billing and possible overages differ. Per-minute limits must be confirmed for selected plan.[1] | VERIFIED published Free 3,000, Starter 2,000, Growth 2,500, Pro 3,000, Enterprise 5,000 calls per entity/hour; separate entity buckets, pages count. Growth example contradicts table: see below.[7] |
| Live collection | VERIFIED guide documents `/fixtures` live state and `/odds/live`; live market IDs come from `/odds/live/bets`, NOT `/odds/bets`.[8] | VERIFIED `/v3/football/odds/inplay` and fixture-filtered calls; response guide lists fixture_id, market_id, bookmaker_id, label and value.[9] |
| Freshness / retention | VERIFIED guide says live-odds updates every 5–60 seconds, typically five; no historical live odds retained, removal usually 5–20 minutes after end. These are published descriptions, not measured latency guarantees.[8] | UNKNOWN: complete timestamp/suspension semantics, live archive retention and independently measured latency were not established in this extraction. Standard in-play coverage is described as bet365 only; fixture coverage still varies.[10] |
| Market coverage | UNKNOWN: exact IDs and observed FT/H1 Over 1.5 and FT/H1 BTTS availability at minute seven for target leagues/bookmakers. No live catalogue queried. | UNKNOWN: exact target market/line/period mapping and seventh-minute availability. Directory documentation warns availability varies by feed, bookmaker, league and fixture.[10] |
| Data rights | UNKNOWN: extracted terms did not establish a sufficient explicit grant for retained raw snapshots, model training, paid predictions, exports and post-termination retention. Do not infer permission from technical availability. | VERIFIED terms allow commercial creations based on data, storage/transfer/distribution of supplied data, but forbid direct resale without approval; per-domain pricing and account sharing restrictions apply. Exact BETFORGE channels still need written scope confirmation.[6] |
| Third-party rights | VERIFIED terms reserve suspension without refund after a recognized rights-holder complaint; visual assets are not owned by API-Football.[1] | VERIFIED provider disclaims holding official league/competition rights; logo/photo rights require separate authorization.[4][6] |
| Decision | Candidate for further validation; NOT selected or cleared. | Alternative for validation; NOT selected or cleared. |

## Billing and documentation conflicts

VERIFIED: Sportmonks FAQ describes a paid-plan trial with no card required upfront, whereas its terms require a valid card and manual cancellation to avoid billing. Treat the contractual page conservatively and obtain written clarification before any trial; no account or trial was created.[5][6]

VERIFIED: Sportmonks rate-limit table says Growth has 2,500 requests per entity/hour, while its example says 3,000 Fixture requests. Do not implement the larger limit from the example. Confirm active entitlements and rate_limit response metadata; no entitlement was queried.[7]

VERIFIED: API-Football direct-dashboard prepaid/no-overage pricing and RapidAPI recurring/overage terms describe different subscription channels, not interchangeable payment guarantees. Any future cost approval must name the channel.[1][2]

VERIFIED: Sportmonks terms specify upfront monthly/annual fees with automatic renewal, generally non-refundable processed payments subject to stated exceptions, EUR payment settlement and VAT-exclusive advertised prices.[6] Applicable tax, exact add-ons and final total cost remain UNKNOWN; no subscription was started.

## Budget scenario — INFERRED, not a deployment recommendation

Assumptions: two unpaginated endpoints, one aggregated request each per 15-second interval, two hours of active polling, no retries or reference calls. Executed Python arithmetic: `2 * 2 * 60 * 60 // 15 = 960` requests and `2 * 60 // 15 = 8` requests/minute. Actual cost scales with pagination, per-fixture calls, observation hours and retries.

INFERRED: this scenario exceeds API-Football's advertised 100-request free daily quota, but is within its Pro daily quota before overhead. This is not proof of acceptable per-minute capacity, selected competition coverage or suitability for a seventh-minute experiment.[2] No plan purchase approved; actual model, storage, tax and operational costs remain UNKNOWN.

## Proposed data/rights acceptance checklist — DESIGN, not implementation

For each provider obtain a dated written answer covering:

1. Legal contracting entity, upstream rights and permitted Nigerian/other target-market uses, including commercial football analytics and gambling-related restrictions.
2. Permission to retain raw JSON, derived Parquet/features, model-training inputs and audit records; retention duration, cancellation survival, deletion requirements and backups.
3. Paid dashboard display, private Telegram alerts, derived probabilities and performance reports; distinguish these from prohibited raw-feed resale and customer exports.
4. Specific competitions/bookmakers and live FT Over 1.5, H1 Over 1.5, FT BTTS, H1 BTTS; selection/line/period IDs and settlement rules for abandonment/voids.
5. Provider-update timestamps, clock timezone, update vs transport latency, suspension/stoppage/finished flags, gaps, history and correction behavior.
6. Exact subscription channel, base/add-on price, tax, currency, quotas, per-minute/entity limits, overage behavior and trial/renewal terms.
7. Separate visual-asset permissions. Do not assume attribution, modifying a logo or a provider's fair-use suggestion creates a legal right.

After permission and credential availability are confirmed, run a separately scoped capture: independently fetch fixture state and live quotes, preserve all clocks and provenance, map only explicitly verified IDs, reject unknown/stale/suspended quotes, and reproduce one genuine seventh-minute observation. No claim that this acceptance test has occurred.

## Risk register entries for BF-007

- R-DATA-01, BLOCKED: unresolved API-Football retention/commercial scope. Owner: project owner/legal reviewer. Mitigation: written permission before collection.
- R-DATA-02, OPEN: target live markets, bookmaker provenance and timestamps unverified. Owner: data engineer. Mitigation: catalogue and permitted capture tests; fail closed on ambiguous identity.
- R-DATA-03, OPEN: no retrospective API-Football live archive in published guide. Owner: quant/data engineer. Mitigation: prospective capture only after rights clearance; never fabricate historical quotes.[8]
- R-DATA-04, OPEN: Sportmonks billing and quota inconsistencies. Owner: procurement. Mitigation: dated provider confirmation before signup.
- R-DATA-05, OPEN: provider permission is not competition IP clearance or gambling authorization. Owner: legal reviewer. Mitigation: BF-009; no public launch.

## Recommendation and next action

DESIGN DECISION PROPOSAL: keep both candidates open; do not buy, subscribe or implement an authenticated adapter yet. Provider-neutral contracts can be drafted using explicit UNKNOWN fields, but must not silently satisfy BF-003/BF-010 gates. Highest-priority next action is owner-approved clarification of provider retention, commercial-use and billing scope using the checklist above. No outreach has been sent.

Audit acceptance remains PARTIAL: useful public evidence is preserved, but pricing, full schemas, exact live-market coverage and permission gaps prevent final selection. Phase 00 gate: NOT YET EVALUATED.

## Sources

[1] https://www.api-football.com/terms
    > "In case of a formal complaint or legal notice from a recognized rights holder"
    > "Subscriptions on our dashboard are prepaid access to the API for a period agreed between the user and Api-football."
[2] https://www.api-football.com/pricing
    > "100 Requests / day"
    > "7 500 Requests / day"
[4] https://www.sportmonks.com/integrity-support
    > "We do not claim to hold official rights on behalf of leagues or competitions"
[5] https://docs.sportmonks.com/v3/api-faq.md
    > "14-day paid-plan trial with no credit card required upfront"
[6] https://www.sportmonks.com/terms-of-service
    > "Reselling Sportmonks’ data without approval is not allowed."
    > "distribution, transfer, and storage of data provided by our services is allowed"
    > "you need to provide Sportmonks with a valid credit or debit card"
[7] https://docs.sportmonks.com/v3/api/rate-limit
    > "**Growth:** 2,500 API calls / entity / hour"
    > "3,000 Fixture requests"
[8] https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide
    > "These two ID sets are not interchangeable."
    > "no historical data is stored whatsoever"
    > "Updates come every 5 to 60 seconds"
[9] https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/odds-and-predictions/live-inplay-odds
    > "In-play (live) odds data requires the Odds add-on (€14-€69 depending on your base plan)."
[10] https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/odds-and-predictions/markets
    > "Standard in-play odds are available for bet365 only."
