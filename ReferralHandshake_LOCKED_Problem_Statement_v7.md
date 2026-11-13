# ReferralHandshake — LOCKED Problem Statement and Project Definition (v7)

**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0
**Basis:** submitted idea + six research reports + two independent critical reviews, each point checked against the research (Appendix B).

> **Status tags:** **[V]** verified in the research · **[V\*]** verified only from a secondary or vendor source · **[CONFLICT]** research files disagree · **[GAP]** nothing reliable found, so no claim may be made. Everything tagged [V\*], [CONFLICT] or [GAP] must be confirmed from primary sources before it appears on a slide.

---

## 1. The Problem: the Referral Black Box

When a patient needs care the current facility cannot give, a referring clinician, an ambulance crew and a receiving team must act as one. The research shows the handover is usually an unconfirmed message, not a commitment.

| Finding | Setting | Status |
|---|---|---|
| Referring facility phoned the receiving facility in 47% of referrals (11,988); 53% had no phone contact | Urban Maharashtra, 2016–2019, 199,888 deliveries (Das et al., 2023) | [V] |
| 37% of referral slips fully documented (9,279) | Same study | [V] |
| 60% of referred women could be tracked at the higher facility; the authors attribute the 40% loss to incomplete documentation and demographic errors | Same study | [V] |
| 19% of referrals driven purely by missing resources; within those, no emergency OT (47%), no NICU (45%), no anaesthetist (24%), no paediatrician (22%) | Same study | [V] |
| 90.6% of critically ill obstetric patients arrived with no prior communication; 70% had no escort; slips incomplete in 50% | Safdarjung Hospital, Delhi, 3,220 inter-facility referrals, 2018–2023 | [V] |
| 47.3% had visited two or more hospitals first ("ping-pong"); authors link this to delay | Same audit | [V] |

**Honest limits.** Both studies are obstetric and urban; the Delhi audit is one tertiary centre. The Maharashtra denominator is 25,253 in some reports and 28,020 in others **[CONFLICT]**; the 47%, 37% and 60% figures only reproduce with 25,253, so quote percentages and check the paper's tables. No national prevalence, no measured ambulance time lost to referral failure in India, and no mortality effect of digital handshakes were found **[GAP]**. Claims are operational (handover reliability, documentation, traceability), never clinical outcomes.

## 2. Framing

The Three Delays model defines the second delay as reaching an adequate facility and the third as receiving adequate care there [V]. The literature classifies referral-communication failure inconsistently (second delay, third delay, or a proposed "fourth delay" for administrative and digital barriers, a term used inconsistently) [V\*]. **Position:** referral handover failure sits at the contested boundary between delays two and three. The project does not address the first delay.

## 3. What Exists, and the Gap

- **Policy:** the National Ambulance Services Guidelines 2026 (29 June 2026) call for GIS mapping of facilities, bed availability and critical-care readiness, and command centres linked toward ERSS 112 [V]. They state the outcome, not a handover protocol.
- **Systems audited:** ABDM FHIR resources, eSanjeevani, NIC e-Hospital, Community Health Toolkit, DHIS2, OpenSRP, Pulsara, ReferralMD, Epic Transfer Center [V\*]. Automatic inter-facility escalation and a hard single-owner guarantee were **not found in public documentation** [V\*]. Closed systems and Karnataka state referral systems could not be inspected **[GAP]**; treat the gap as a hypothesis to test with clinicians and 108 staff.
- **Vula Mobile (South Africa):** asynchronous digital referral changed behaviour (52% of one hospital's gynaecology referrals handled by advice alone), but its evaluation found delays when receivers did not respond, with no mandated response time [V]. This is direct evidence for enforced deadlines.

## 4. The Locked Problem Statement

> **How can an emergency referral stop being a message and become a verifiable contract: one that is offered, answered, negotiated, owned by exactly one destination, escalated automatically when nobody responds, never delays care, works from a feature phone to a command centre, survives failures, and closes with an outcome back to the referrer, with its guarantees provable rather than promised?**

**Pitch:** *Today a referral is shouted across a street. ReferralHandshake makes it a signed-for handover, and proves the signature holds, live.*

**First pathway (as in the submitted idea: one pathway first):** emergency obstetric referral through Karnataka-style tiers (PHC → CHC → first referral unit / district hospital → medical college), because that is where the evidence is. The data model is generic so trauma, neonatal, cardiac and stroke referrals can follow.

## 5. USP, MVP and the Coherence Rule

### USP (the one idea everything hangs on)
**The Verifiable Referral Contract.** Three parts, each answering a documented failure:
1. **Contract semantics:** offer, acknowledge, accept / counter / decline-with-reason, single-owner lease, resource commitments, escalation, closing outcome. (Answers: silent referrals, ping-pong, lost patients.)
2. **Reach without dependency:** works from a smartphone, a feature phone (voice), a paper code, or offline. (Answers: no app at the receiver, dead zones, adoption.)
3. **Provability:** a written specification, bounded model checking of its invariants, a public conformance test suite, and a **live runtime monitor** that independently re-derives every referral's state from the event log and shows the guarantees holding while judges attack the system. (Answers: "why should anyone trust it?")

Competitor-safe wording: *"Not found in public documentation of the systems audited"*, never "first" or "only".

### MVP (the smallest thing that proves the whole idea, end to end)
One obstetric referral, four roles (referring clinician, receiving duty role, ambulance crew, dispatcher), running through:
**structured referral card → offer to a facility's duty role → acknowledge → accept / counter / decline-with-reason → single-owner lease → timer escalation (inside the facility, then to the next facility, then to the dispatcher) → parallel transport track → arrival → closing outcome**, with an append-only hash-chained log, an offline outbox, a chaos switch, and the live guarantee monitor.
*Done means:* the conformance suite passes, the monitor shows zero invariant violations under judge-style attacks, and the demo runs with every other layer switched off.

### Coherence rule (why this is not a pile of features)
Every feature must be exactly one of: **(a)** a state or event in the contract, **(b)** an interface that produces or consumes those events, or **(c)** a reader of the event log. Anything else is out of scope.

| Layer | Role in the contract |
|---|---|
| Referral card, intake accelerator | Writes the *terms* of the contract (structured payload) |
| Resource commitments, counter-offers | The counterparty's *commitment* |
| Timers, ladders, dispatcher fallback | *Enforcement* of the obligation to respond |
| Voice, link, paper code, offline outbox | *Delivery* to every kind of party |
| Hash chain, signed acknowledgements, replay | *Evidence* |
| Spec, conformance suite, runtime monitor, chaos | *Proof* that the contract holds |
| Command centre, network graph, digital twin | *Learning* from the same log |

## 6. The Handshake Contract (core solution)

**Two tracks, so care is never blocked**
- **Handshake track** (who owns the patient): `CREATED → OFFERED → ACKNOWLEDGED → {ACCEPTED | COUNTERED | DECLINED}`; `COUNTERED → ACCEPTED` only when the referrer confirms.
- **Transport track** (where the patient is): `REQUESTED → DISPATCHED → EN_ROUTE(facility) → ARRIVED(facility) → HANDED_OVER`. It runs in parallel and is never gated by the handshake track, so an ambulance can leave toward the clinician's chosen primary while the handshake proceeds. If ownership moves, everyone sees a redirect alert.
- **Failure paths:** `TIMED_OUT → ESCALATED` (next step in the ladder), `ARRIVAL_REJECTED → ESCALATED`, `ESCALATED_TO_DISPATCHER` when the pre-approved chain is exhausted (a human must assign or close; the system never invents a destination), `CANCELLED`.
- **Closure:** `CLOSED` requires an outcome note from the receiver or an explicit "unknown" (a digital counter-referral).

**Response vocabulary (a real handshake, not a button):**
- **ACCEPT:** all required resources confirmed one by one; ownership granted as a lease with a fencing token.
- **COUNTER:** "can take, but without NICU" or "anaesthetist in 20 minutes"; the referrer confirms or escalates.
- **DECLINE:** structured reason (which resource is missing) and an optional redirect suggestion.
Silence is the only unrecorded outcome, and silence triggers escalation.

**Two-level escalation:** inside the receiving facility first (duty nurse → casualty medical officer → on-call consultant or administrator, each with its own timer), then to the next facility in the chain the clinician approved at creation, then to the dispatcher. Timer values are configuration owned by clinical leadership; demo values are short; the project claims no clinical threshold.

**Five promises and the invariants that formalise them**
1. *No silent referral:* every non-terminal referral has a pending deadline and a responsible actor.
2. *One patient, one owner:* at most one active ownership lease per referral.
3. *Never block care:* transport events are accepted in any non-terminal handshake state.
4. *Nothing is lost or duplicated:* each client event appears exactly once in the log after any number of retries or reconnects.
5. *Nothing is untraceable:* the log is hash-chained and `CLOSED` requires an outcome or "unknown".

**Data design.** Observations (vitals, notes, GPS) are append-only events with unique IDs, so merging after offline periods is a set union, with no in-place edits (corrections are new events). This resolves the "overwrite" risk without a CRDT library. Authoritative state changes go through one serialised server decision (PostgreSQL row locks or serializable isolation are documented as sufficient across replicas [V]; SQLite's single-writer behaviour is unverified **[GAP]**). An offline accept is only a request shown as "pending, not confirmed".

## 7. Layers (built in this order; each behind a feature flag)

| Layer | What it is | Gate to pass before the next layer |
|---|---|---|
| L0 Spec and harness | State machine specification, invariants, bounded model checking of the control plane, conformance test suite, trace validation of the implementation against the spec | Suite runs green in CI |
| L1 Contract core | Server, event log, ownership lease, durable timers, two-level escalation | Suite plus concurrency tests |
| L2 Field clients | Referral card, receiving desk, ambulance client (Android-first with foreground location service), dispatcher console; offline outbox; proxy entry by dispatcher or EMT | Offline and duplicate tests |
| L3 Guarantee Arena | Live runtime monitor, chaos switch, tamper verifier, replay, deliberately broken build for the monitor to catch | Monitor detects injected faults |
| L4 Reach | Judge-friendly web desks via QR code; SMS alert with pre-registered link; automated voice with keypad and PIN for pre-registered duty numbers; paper code entry | Channel acknowledgement tests |
| L5 Command centre | Live map, handover KPIs, referral network graph, ambulance-minutes metrics | Metrics match log recomputation |
| L6 Intake accelerator | Photo or dictation draft with active verification, off the critical path | Seeded-error safety gates |
| L7 Interoperability | FHIR-shaped export with a small curated code subset; sandbox attempt only if feasible | Validator passes |
| L8 Proof engine | District digital twin and counterfactual replay | Assumptions shown, outputs labelled "simulated" |
| L9 Field validation | Expert interviews, then ethics-approved shadow-mode baseline if permitted | Permissions in place |

## 8. Real-World Operating Model

- **Who holds the receiving device:** a **duty role** (casualty medical officer or duty nurse) that the facility registers on a roster, not a named person. Offers go to the role; the intra-facility ladder covers staff shortages.
- **Why a busy receiver responds (hypotheses to test with clinicians):** all three answers are valid, timestamped responses, and a documented decline for a missing resource is not a failure; silence is the only losing move. Advance notice reduces unannounced arrivals at casualty; a redirect suggestion lets them help without taking the patient; reliability views are aggregated at district level and framed as capacity signals, not individual blame.
- **Honest limit:** the system does not create capacity. If every facility is full it surfaces the refusal earlier (before the ambulance reaches the door) and gives administrators data on bottlenecks.
- **No receiver at all:** voice to a pre-registered duty number; failing that, the dispatcher does a phone-assisted response recorded as proxy; at the door, the EMT's device records arrival and handover.
- **Identity and authority:** only rostered, role-authorised users on registered devices or numbers can accept, with a PIN; device-signed acknowledgements.

## 9. Live Data and Liveness

| Live feed | Source | Drives | Caveat |
|---|---|---|---|
| Ambulance position | A teammate's Android phone, HTTPS geolocation | Live map, ETAs | Background tracking needs the native location service **[GAP]** |
| Road ETAs | Routing API with traffic (one provider: 25 coordinates per request, 300 requests per minute, 100,000 free requests per month [V]) | Ranking, arrival times | Compute only for active referrals' top candidates, cached |
| Facility locations | OSM/Overpass (under 10,000 queries per day [V]), cached once | Map, candidates | Karnataka coverage unverified **[GAP]**; curated directory |
| Handshake telemetry | The system itself | Responsiveness, reliability, KPIs | Real once used; synthetic in the demo |
| Real calls and alerts | Telephony provider to real phones | Reach demo | See section 12 |
| Facility attestations | Staff updates with timestamps | Readiness shown with age | Self-reported; never presented as live beds |

## 10. Real-World Scenarios the System Must Handle

| Scenario | Behaviour |
|---|---|
| Receiver has no smartphone | Voice call with PIN and keypad reply; dispatcher proxy if needed |
| Receiver cannot take the patient but knows who can | Decline with redirect suggestion |
| Receiver can take the patient only partly | COUNTER; referrer confirms or escalates |
| Duty nurse is busy | Intra-facility ladder escalates to the casualty medical officer, then onward |
| Two facilities accept at once | One lease granted; the other sees why |
| Receiver accepts, then cannot take the patient on arrival | `ARRIVAL_REJECTED` records the broken commitment and escalates |
| All approved facilities fail | `ESCALATED_TO_DISPATCHER`; a human assigns or closes |
| Ambulance in a dead zone | Observations queue; state shown as last confirmed; set-union merge on reconnect |
| Server or internet down | Clinical and phone procedures continue; the paper slip carries the code; the outbox reconciles after recovery |
| Wrong person "accepts" | Roster, role and PIN checks reject and log it |
| Crew cannot use the app | Dispatcher or EMT enters status, marked as proxy |
| Slip arrives without a digital record | Desk enters the paper code and links it |
| iPhone with restricted background behaviour | Foreground flush; limitation stated; no background guarantee claimed |
| AI draft is wrong | Structured entry is primary; critical fields need active verification; system works with AI off |

## 11. The Wow Centrepiece: the Guarantee Arena

The headline is not a feature, it is a demonstration of *trust under attack*. A big screen shows the **Guarantee Monitor**: an independent process that re-derives every referral's state from the event log and checks the five invariants continuously (green counters, violation count).
1. **The race:** judges scan a QR code, become competing hospital desks in their own browsers, and press Accept together. Exactly one lease is granted; the monitor stays green.
2. **The silence:** one judge ignores an offer; watch the intra-facility ladder, then inter-facility escalation, fire on schedule.
3. **The failure:** a judge kills a server instance mid-referral, or cuts the ambulance phone's network; nothing is lost or duplicated; recovery time is displayed.
4. **The forgery:** change one log row; the verifier points to the exact broken link.
5. **The proof it can catch bugs:** switch to a deliberately broken build that grants two leases; the monitor turns red within seconds. Switch back; green.
6. **The patient's journey:** real phone GPS moves the ambulance on the live map; counter-offer, confirm, arrival, outcome note returns to the referring clinic. Replay the whole referral on a time scrubber.
7. **The degraded world:** turn off AI, the app and the network in turn, and show the referral still completing through voice, paper code and the dispatcher.
8. **The district view:** the digital twin runs "phone and paper" against "Handshake" on identical synthetic referrals, with assumptions visible and outputs labelled as simulation.

## 12. Safety, Legal and Security Design

**Data-minimisation architecture.** ReferralHandshake holds a *handover record*, not the medical record. (1) The clinical payload is shared with the referring and receiving facilities and held in the service for a configurable limited period. (2) A pseudonymous event-metadata log (no clinical content) is kept longer for audit and tamper-evidence. (3) Retention periods and the interaction between DPDP Act s.7(f) emergency processing and record-keeping duties (3-year retention, 180-day CERT-In logs, as reported in secondary sources [V\*]) are policy parameters that need legal review before real use **[GAP]**. The prototype uses synthetic data only. DPDP Rules were notified on 14 November 2025 with core obligations from 14 May 2027 [V\*].

**ABDM and FHIR.** The service does not fetch longitudinal health records (which, per the regulatory research, would need patient consent that an unconscious patient cannot give, with emergency overrides unverified **[GAP]**). The referral summary is clinician-authored at the point of care. Export is FHIR-shaped using a small curated set of preset codes, so no terminology server is needed; validate codes against the official value sets. Claim "ABDM-sandbox aligned" only if sandbox calls are made. Never claim "ABDM compliant".

**Telecom.** Clinical text does not go by SMS (DLT templates, reportedly ~30-character variables, silent drops [V\*]). SMS carries a static alert and a link on a pre-registered, whitelisted domain pattern **[to verify with provider]**. Voice reads a short de-identified summary to pre-registered duty numbers, with a PIN; its legality is unsettled **[GAP]**. A student team cannot register as a telecom principal entity, so the prototype uses a provider sandbox or trial with pre-verified numbers, synthetic data, and the team's own feature phone. Judges participate through QR-code web desks, which need no telecom setup. The project does not attempt to circumvent telecom controls. WhatsApp is excluded for health data.

**Security (to be fully threat-modelled in the research phase).** Role-based access, roster checks, PINs and device-bound signing keys; rate limiting; spoofed-acceptance and replay tests; encrypted transport and storage; minimal data in notifications; audit of every administrative action. Tamper-evident is not immutable and is not legally conclusive without formal certification under the electronic-evidence rules [V\*].

**Claims you may and may not make**

| May claim | Must not claim |
|---|---|
| Referral communication and documentation gaps are documented in specific urban Indian studies | National prevalence, deaths prevented, lives saved |
| A specified, model-checked, conformance-tested protocol with single-owner leases and timed escalation | That no competitor has it |
| The guarantees held under our stated test conditions | Production readiness |
| FHIR-aligned export; "sandbox aligned" if true | "ABDM compliant", live integration with 108, hospitals or ABDM |
| Simulated ambulance-minute savings under stated assumptions | Measured time saved or "ping-pong eliminated" |
| Process improvement is a hypothesis to be tested in a pilot | That the protocol reduces lost patients or transfers as an established fact |

Safety fallback: existing clinical and emergency communication procedures remain primary; the system never delays care.

## 13. Success Criteria (measured, not promised)

- Zero invariant violations in the monitor across the full attack script and randomised long-run tests; bounded model checking of the specification passes for the stated configurations (this checks the specification, not the code; the code is checked by trace validation and the conformance suite).
- Exactly one lease across N concurrent-accept trials; zero duplicates or losses across retry, replay and reconnect tests.
- Escalation within stated tolerance of deadlines at both levels; event latency p50/p95; recovery time after instance failure.
- Time to acknowledgement per channel; referral card completion time; completeness with and without the accelerator.
- Accelerator safety on seeded synthetic errors: critical-error rubber-stamp rate and silent-omission rate against our own proposed gates (5% and 1%); an internal usability test, not a clinical study.
- If a pilot is approved: acknowledgement time, unanswered rate, completeness versus paper, ambulance wait at origin, secondary transfer rate.

## 14. How It Gets Built (spec-first, so fast tooling stays safe)

AI-assisted ("vibe") coding speeds up scaffolding and integration, but concurrency, timers and recovery are exactly where generated code looks right and is wrong. So: write the specification and conformance suite first (L0), let the coding agent build against them, and make no layer count as done until the suite and the runtime monitor are green. Every layer sits behind a feature flag so the demo can run with any subset, and keep a recorded backup of the demo. Understand every module well enough to explain it to judges. Confirm the event's rules on pre-built work and AI-assisted coding.

## 15. Social Impact and Path to Real Use

**Who benefits:** patients in obstetric (first), neonatal, trauma, cardiac and stroke referrals; PHC and CHC clinicians; 108 crews; receiving triage teams; district officers who cannot see where referrals stall. **Design for equity:** works on a feature phone, in Kannada and Hindi voice, on weak networks, and for facilities with no IT. **Why it matters:** it turns blind transfers into accountable handovers, makes refusal visible before the ambulance reaches the door, and gives administrators evidence to fix bottlenecks. The research supports process claims only. **Path:** synthetic demo → expert conversations → optional ABDM sandbox → ethics-approved shadow-mode pilot in one district → integration only through authorised channels.

## 16. Residual Risks (honest)

| Risk | Response |
|---|---|
| No capacity is created | Stated plainly; value is earlier discovery and data |
| Adoption depends on receivers' incentives | Hypotheses in section 8; test in expert conversations and pilot |
| Voice and data-retention law unsettled | Legal review before any real use; synthetic data now |
| Scope is very large | Layers, gates and flags; the MVP must always run alone |
| Platform limits (iOS background, tile policies) | Android-first ambulance client; foreground flush; tile choice verified in research |
| Real-world clinical thresholds unknown | Configuration owned by clinical leadership; no claim made |
| Vibe-coded defects | Spec-first development, conformance suite, runtime monitor |

---

## Appendix A — Evidence Register

| Figure | Status | Use rule |
|---|---|---|
| 47%, 37%, 60% (Das 2023) | [V]; denominator [CONFLICT] | Quote percentages; confirm denominator |
| Delhi 90.6%, 70%, 50%, 47.3% | [V] | "One tertiary obstetric ICU centre" |
| 19% and OT/NICU/anaesthetist shares | [V] | Shares within the resource-driven group |
| Vula 52%; response-delay finding | [V] | Process outcomes only |
| NAS 2026 content | [V] via PIB and secondary summaries | Read the official document before quoting clauses |
| Competitor gaps | [V\*] | "Not found in public documentation" |
| DLT limits; URL whitelisting; registration needs | [V\*] | Confirm with provider and TRAI texts |
| DPDP timeline and s.7(f) | [V]/[V\*] | Confirm in Act and Rules text |
| CERT-In, BSA s.63, record retention | Blog and law-firm sources | Verify primary text |
| AI accuracy and error figures | [V] preprint and benchmark; Kannada and 26.3% scribe figures are single-source | Cite with dataset and conditions |
| Ambulance time lost in India | [GAP] | Simulation or pilot only |
| Ethiopia "47% refused referral" | Different phenomenon | Do not use |

## Appendix B — Review Findings and Verdicts

| Review point | Verdict | Where handled |
|---|---|---|
| ABDM M3 consent blocks fetching an unconscious patient's history | Valid for fetching; we do not fetch | §12: clinician-authored summary, no fetch |
| Voice demo blocked as unsolicited communication | Valid risk. The suggested "bypass" is rejected; the project does not circumvent telecom controls | §12: sandbox, verified numbers, QR web desks |
| DPDP 7(f) versus record retention | Valid tension; legal interpretation unverified | §12: handover record vs medical record, legal review |
| SNOMED/LOINC burden | Valid | §12: small curated code subset |
| Escalation chain exhaustion | Valid, good catch | `ESCALATED_TO_DISPATCHER` |
| DLT URL whitelisting | Plausible; verify with provider | §12 |
| Receiving desk lacks a device | Valid | Voice, dispatcher proxy, EMT device |
| "Reduces lost patients" overclaims | Valid | Reworded as hypothesis |
| "Start immediately" on telecom registration | Valid; a student team cannot register as a principal entity | Removed |
| Adoption incentives; who holds the device | Valid, important | §8: duty role, ladder, response vocabulary |
| "Observations merge freely but defaults overwrite" | Valid inconsistency | §6: append-only events, set-union merge |
| Cut AI, FHIR, twin, pilot to save time | Right for a 24-hour build, not for a long pre-build; the real risk is incoherence and untested code | Kept, but layered, gated and flagged |
| Judge answers citing Meta PHI terms and Clinical Establishments Act s.12(2); "protocol eliminates ping-pong" | Weakly sourced or overclaimed | Not used |

## Appendix C — Verify Before Final Submission

1. Das et al. denominator and definitions. 2. NAS 2026 clauses from the official document. 3. Telecom sandbox terms, voice-content legality, URL whitelisting. 4. Routing and map terms, Karnataka hospital coverage, SQLite concurrency documentation. 5. Primary text for CERT-In, BSA s.63 and record retention. 6. Background location approach on Android. 7. ABDM sandbox route and FHIR value sets. 8. Hackathon rules on pre-built and AI-assisted work. 9. At least three conversations with a clinician, a 108 crew member or a district coordinator.
