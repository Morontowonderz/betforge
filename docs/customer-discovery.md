# BF-008 — Customer-discovery plan

As of 2026-10-21. Status: VERIFIED for plan-document acceptance only after independent review deleg_ca2a2cf3. Execution remains blocked pending the approvals below. All segments, thresholds and methods below are DESIGN proposals. No interviews, outreach, recruitment, data collection, design-partner agreements or paid pilots have occurred. Demand, pricing and willingness to pay are UNKNOWN. Sources for requirements: docs/product-charter.md and docs/risk-register.md; this is not an external market-research report.

## Objective and hypotheses

Test whether trustworthy football data, reproducible analysis and transparent uncertainty solve recurring customer problems independently of any promised betting profit. Do not validate a betting edge through interviews: that requires the registered quantitative evaluation.

| Hypothesis | Candidate segment (unvalidated) | Evidence sought | Disconfirming evidence |
|---|---|---|---|
| H-CUST-01 | Independent football analysts/researchers | Recent repeated work checking data quality, timestamps and market identity; time spent or existing spend | No recurring task, free alternatives already adequate, unwilling to inspect provenance |
| H-CUST-02 | Small sports analytics/media teams | Concrete need for reproducible comparisons and historical explanations with a decision-maker | Only generic interest or demand for unsupported predictions/raw-feed resale |
| H-CUST-03 | Adult research-oriented football followers in legally cleared markets | Understanding and useful application of descriptive analysis and uncertainty without wagering prompts | Value depends solely on guaranteed wins, chasing losses or real-time wagering instructions |

Prioritize the first two segments for safety and clearer workflows. The third remains deferred until legal/privacy/responsible-use review permits recruitment. No inferred segment membership from private browsing, financial data or gambling activity.

## Recruitment and execution gates

Planning is authorized; execution is not. Before invitations or collection, require a named owner, approved jurisdictions/eligible adult criteria, legal/privacy review of purpose and lawful basis, approved participant notice, secure non-Git storage, retention/deletion procedure, approved recruitment channel and specific outreach approval. Age and jurisdiction rules are UNKNOWN pending BF-009; do not assume a universal age threshold or request ID documents as a default.

Use only owner-approved opt-in contacts or permitted research communities after approval. No scraped customer lists, unsolicited promotional messages, recruitment from unrelated projects, bookmaker-account access or minors. Exclude people seeking recovery of gambling losses; never request betting histories or diagnostic health information. Screening must minimize sensitive information. Invitations must identify research purpose, voluntary participation and that no betting advice is offered. No incentives, gifts or purchases without separate cost approval.

## Sampling and stopping rule

DESIGN: aim for 15 distinct completed interviews, initially split across the first two segments, with recruitment source, refusals and incomplete interviews counted. Use a frozen interview-guide version per batch; record any change before later interviews. Do not count colleagues' encouragement or duplicate interviews as additional customers. Log selection bias and the limits of a small convenience sample; do not claim statistical representativeness.

Stop recruitment immediately for a privacy incident, eligibility uncertainty, coercion, gambling distress, or unapproved scope. Stop an interview on withdrawal or distress without probing causes; offer only an approved neutral support-resource route if appropriate. Do not turn the session into financial, medical or gambling advice.

## Consent and data minimization

Before starting, provide approved plain-language purpose, intended internal use, voluntary participation, ability to skip/stop, contact for access/deletion requests, retention period and withdrawal handling. Consent to an interview is not marketing consent. Recording is OFF by default and needs separate explicit consent plus approved storage and retention; no AI transcription/upload without separate review and authorization.

Proposed retention: delete identifiable scheduling/contact records and raw notes within 30 days after the interview unless an approved shorter period applies or separately renewed consent and legal basis justify retention. This duration is a proposal, not an established legal rule. Set an exact deletion date when collecting. Review de-identified synthesis after 90 days; retain only genuinely necessary, approved summaries. Until these rules and a deletion mechanism are approved, collect nothing.

Use random participant IDs. Keep identity linkage/contact details in separate access-restricted storage, not this repository. Do not collect bank details, account passwords, stakes, losses, precise income or unnecessary health data. Do not save interview records in Git, Hermes memory, shared logs or public documents. No real participant records are created by this plan. Public quotations, marketing use and future contact each require separate permission. Report whether withdrawal can remove linked notes and what cannot be reversed after genuine aggregation; never promise impossible deletion.

## Interview protocol — proposed 30-minute guide

1. Opening and consent: explain research, no sales pitch, no betting recommendations and permission to stop; confirm approved eligibility without unnecessary identifiers.
2. Recent workflow: “Tell me about the last time you analyzed a football match. What were you trying to decide or explain?” Ask for a concrete episode, not whether they like the idea.
3. Existing tools: “What did you use? Where did you have to double-check information? What happened when information disagreed?” Do not prompt for credentials or copyrighted/private materials.
4. Cost of the problem: “How often does this happen? How much time does it take? What have you already tried?” Record self-reports as self-reports, not measurements. Ask about tool expenditure only optionally, in broad ranges.
5. Alternatives and non-use: “When is your current approach good enough? What would make another tool unnecessary?” Actively record reasons not to buy.
6. Concept test only after unaided discovery: describe a proposed analysis record containing fixture, distinct market period/line, source timestamp, quality flags and uncertainty. Use fictional text explicitly marked DEMO, no real odds/tips, live assets or claims of an existing system.
7. Comprehension: “What would you conclude from an unavailable or stale quote? What does this probability not tell you?” Failure to understand limitations is a usability/safety finding, not participant failure.
8. Value and trade-offs: “Which part, if any, improves that earlier workflow? What would you remove? What would you use instead?” Separate descriptive-data usefulness from wagering expectations.
9. Buying process: “Who would decide on a tool like this? What evidence and budget process would they need?” No made-up price anchors. Optional budget range is a hypothesis, not willingness-to-pay proof.
10. Close: summarize limitations, ask what was missed, confirm allowed note usage and separately whether future research contact is welcome. Make no launch, returns, uptime or data-rights promises.

## Evidence template — fields only, no participant data

Store any future filled record outside Git in approved storage. Required fields: participant_id; guide_version; approved segment; eligibility_check_result (no identity documents); consent_version/time; recording_permission; recruitment_source_category; interview_date; withdrawal/deletion_due_date; recent_workflow; frequency_self_report; current_alternative; problem_evidence; counterevidence; optional_budget_range; decision_authority_role; comprehension_observation; concept_response; interviewer_interpretation; evidence_confidence; future_contact_permission; follow_up_commitment; review_status.

Distinguish verbatim quotations (with permission), participant self-report, interviewer interpretation and independently observed behavior. Do not fill unknown fields with plausible values. Preserve refusals, neutral responses and contradictions in aggregate without identifying details.

## Qualification and analysis rules

A qualified prospect must satisfy ALL: approved eligible segment/jurisdiction, concrete recurring problem, explicit evidence current alternatives leave a gap, plausible decision process, useful analytics need without guaranteed-return dependence, and separate opt-in for further research. Interest or a budget guess alone is not qualification.

A serious design partner additionally agrees to a specific feedback workflow and review milestone in writing, with named authorized contact handled privately, no promise of profitable predictions and no obligation to wager or pay. Expressions of interest are not agreements. A paid pilot requires separate legal/data-rights clearance, specific owner/payment approval and actual verified payment/customer delivery evidence; no payment processor or transaction is authorized here.

DESIGN analysis: after the initial 15 interviews, an independent product reviewer codes positive, negative and neutral evidence by segment, checks every qualification against the same rubric, counts distinct participants and records bias/unknowns. Targets remain five qualified prospects, three serious design partners and two legally cleared paid pilots from the charter. None is achieved. Do not merge these stages or infer two paid pilots from stated intent.

Continue discovery only with a bounded owner-approved next batch if the evidence identifies a concrete uncertainty worth resolving. Rework the proposition if fewer than five qualify or if useful demand is confined to unsupported profit claims. Stop the current commercial proposition if no recurring useful problem is demonstrated; consider descriptive analytics only where separately supported. Reaching numeric targets never overrides legal, security, data-rights or model-validation gates. Interview evidence does not validate seventh-minute prediction performance.

## Ownership and deliverables

Proposed roles: product researcher runs approved sessions; privacy/legal reviewer clears eligibility, notices, retention and lawful basis; independent product reviewer checks coding and qualification; project owner approves outreach, budgets and any future pilot. Named owners must be assigned before execution.

Future deliverables, not created or populated here: approved consent/notice, versioned guide, de-identified analysis with counterevidence, verified funnel counts, limitations report and go/rework/stop recommendation. Raw records stay outside Git. No cadence, automation or recurring job is scheduled.

## Acceptance checklist

BF-008 document acceptance requires segment hypotheses, non-leading interview protocol, consent/minimization/retention safeguards, execution approvals, qualification rules, disconfirmation/stopping criteria, bias disclosure and separation of plan/actual evidence. Independent review may verify the plan only, never claim customer validation or approve Phase 00.
