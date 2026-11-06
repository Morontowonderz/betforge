# BF-003A — Unsent provider-clarification requests

2026-10-21. Status: VERIFIED for draft completeness and safety only after independent review deleg_4e037217. Sending is not approved. UNSENT. No recipients selected, messages transmitted, accounts opened, terms accepted or purchases authorized. Parent BF-003 remains BLOCKED. These drafts ask questions; they are not assertions of legal entitlement or live-market availability. Background evidence: docs/data-rights.md, including retained sources and unresolved contradictions.

## Owner approval before sending

Confirm the legal contracting name and authorized sender (ShadowSpark Technologies is project context, not independently verified registration), sender account, specific verified provider contact/channel, exact text, target jurisdictions, initial leagues/bookmakers, intended domains and spend ceiling. No domain, contact address, quota entitlement or credentials are invented here. Nigeria is an intended jurisdiction for clarification, not a claim of regulatory clearance. Other markets remain unspecified.

Approval to send must identify provider, recipient/channel and final text; it does not authorize a trial, purchase, agreement, live-data capture or later follow-up campaign. Verify the contact through the provider's official site at send time. Use an authorized owner account. Never include API tokens, repository contents, local paths, financial details or participant information. Do not attach internal research evidence bundles by default.

## Draft A — API-Football / API-Sports

Subject: Written data-use and live-odds clarification for proposed BETFORGE research

Hello,

We are evaluating API-Football for BETFORGE, a proposed football analytics project. The initial scope is local research and paper trading, with no real wagers. Possible later uses include a paid analytics dashboard and permissioned private notifications, subject to separate legal clearance. No supplier has been selected and no launch or purchase is being committed to.

Please provide written answers, applicable terms/clauses and any required license or plan for the following:

1. May we retain original fixture and live-odds JSON, produce analytical datasets/features, train and evaluate our own models, and retain provenance/audit backups? Specify retention limits, deletion duties and what may remain after cancellation, including model artifacts and non-reconstructible derived statistics.
2. May we sell access to our own analysis/probabilities and performance reports, display selected attributed scores/quotes in a dashboard, and send them to opted-in private notification recipients? Please distinguish each use from prohibited feed resale and customer exports. What restrictions, attribution or additional licenses apply in Nigeria and other jurisdictions that we would separately identify?
3. What upstream competition/bookmaker rights do you provide, and which permissions remain ours to obtain? We do not intend to display logos, photos or video unless independently authorized. Please identify the contracting entity and any restrictions on gambling-related analytics even without wagering execution.
4. For live full-time Over 1.5 Goals, first-half Over 1.5 Goals, full-time BTTS and first-half BTTS, please provide the appropriate live market catalogue, selection/line/period semantics and per-league/bookmaker coverage information. Is bookmaker identity available for each live quote? Are live IDs separate from pre-match IDs, and how are catalogue changes versioned? We will identify our initial league/bookmaker shortlist before any final quote or validation.
5. Which fields report provider-update time, timezone, match elapsed time, score, suspension/stoppage and finished state? How should fixture state be cross-checked independently of live odds? Please distinguish refresh cadence from quote age/transport delay and supply a credential-free sample response and schema if permitted.
6. Can a score and these live markets be observed around match minute seven? We understand availability cannot be assumed for every fixture. What historical live-odds retention, correction, abandonment/void and settlement information is available? Please confirm whether prospective capture is required and licensed.
7. Please quote the appropriate direct-dashboard plan and separately explain any RapidAPI differences: daily and per-minute limits, pagination/request charging, hard limits versus overages, reset times, currency/tax, billing duration, renewal, cancellation and refund rules. Our illustrative workload is two aggregate unpaginated calls every 15 seconds for two hours; retries, pagination and reference calls are additional. No payment or trial activation is requested.

Please state any unsupported uses or unavailable fields explicitly, and identify which answers are contractual permissions versus non-guaranteed technical descriptions. A commercial response will be reviewed before any agreement or acquisition.

Thank you.

## Draft B — Sportmonks

Subject: Clarification of data rights, standard live odds and trial/billing terms for BETFORGE

Hello,

We are evaluating Sportmonks as a possible provider for BETFORGE, a proposed football analytics project initially limited to local research and paper trading. No real wagers, public predictions or paid launch are being undertaken. Possible later dashboard and private-notification uses depend on legal and licensing review; this inquiry is not a purchase or trial request.

Please confirm in writing:

1. Whether permitted storage and commercial derivative-product use covers raw JSON, historical analytical datasets, our own model training, derived predictions, audit backups and retention after subscription expiry. What deletion, attribution, export or post-termination restrictions apply? Please distinguish dashboard display/private notifications from raw-data resale requiring separate approval.
2. Which contracting entity, upstream rights and geographic restrictions apply to the proposed research and later paid analytics use in Nigeria, with other jurisdictions to be identified separately? Which league, bookmaker, regulatory or visual-asset rights must we arrange ourselves? We are not seeking a gambling license from the data provider.
3. Which feed and add-on provide live full-time Over 1.5 Goals, first-half Over 1.5 Goals, full-time BTTS and first-half BTTS? Please provide current market/selection/period IDs, applicable league coverage and live bookmakers. Does standard in-play remain limited to bet365, and is Premium pre-match only? Please distinguish advertised catalogue coverage from actual per-fixture availability. Our league/bookmaker shortlist is not yet finalized.
4. Please supply a permitted credential-free schema/example covering provider-update timestamps/timezone, fixture score/elapsed time, quote value, suspension/stoppage, stale/deleted quotes and corrected data. Explain independently retrieving fixture state, update cadence versus delivery latency, live archive retention and abandonment/void/settlement semantics. We need reproducible observations around minute seven, not a claim of guaranteed availability.
5. We observed differing public descriptions of paid-plan trial card requirements: the FAQ described no card upfront, while the terms required a card and cancellation to avoid billing. Which terms currently apply? Please confirm trial conversion, automatic renewal, cancellation, refunds, EUR settlement and applicable taxes. Do not activate a trial or process payment in response to this inquiry.
6. The rate-limit page's Growth table and example appeared to differ (2,500 versus 3,000 calls per entity/hour). Please confirm the enforceable quota, entity buckets, reset rules, pagination charges, burst behavior and hard-cap/overage controls for any proposed plan.
7. Please give a complete non-binding quote for the required base plan and live-odds add-on, with billing period, league selection, domain/channel limits, currency and taxes stated separately. Clarify whether private Telegram-style delivery or multiple domains changes licensing/pricing. No domain or additional business account is being represented as already approved.

Please link the governing terms and explicitly mark answers that require a separate agreement or cannot be guaranteed. We will assess the response before proceeding with any subscription, collection or commercial use.

Thank you.

## Response acceptance matrix — proposed internal workflow

| Area | Evidence required | If absent or ambiguous | Reviewer |
|---|---|---|---|
| Identity / scope | Verified official sender, contracting entity, dated response and exact proposed use | Keep UNKNOWN; do not treat an unsigned marketing reply as a signed agreement | Owner/legal |
| Storage / models | Written retention/training/derived-output permission with cancellation and backup duties | Collection and reuse remain BLOCKED | Legal + data owner |
| Display / redistribution | Channel/domain/geographic permissions; restrictions and attribution | No commercial or public delivery | Legal |
| Live markets | Catalogue/schema and permitted genuine per-fixture capture after approval | No mapped observation or signal accepted | Data engineer + QA |
| Freshness / settlement | Timestamp/status semantics, corrections and settlement rules; subsequent tests | Fail closed; no replay or performance validity claim | Data/quant reviewers |
| Price / quota | Complete channel-specific quote and enforceable limits/renewal rules | No trial, paid resource or budget commitment | Owner/procurement |

A response alone does not prove observed latency, coverage, model validity or legal clearance. Reconcile it with governing terms; request scoped follow-up approval for ambiguity rather than silently choosing the favorable reading. Store correspondence privately if it includes personal/confidential material, and only add a redacted permission summary to project docs when allowed. Do not copy credentials into the evidence ledger. BF-003 can advance only after its evidence requirements are reviewed; BF-010 remains a separate gate.

## Draft acceptance criteria

Both requests must distinguish research from future commercial uses, cover the BF-003 rights/market/time/billing gaps, avoid invented recipient/identity/permissions, and explicitly decline activation or commitment. A reviewed draft is not approved sending or an answered provider audit. Next action after document review: owner supplies missing scope and explicitly approves a specific provider message/channel, or elects to keep outreach deferred.
