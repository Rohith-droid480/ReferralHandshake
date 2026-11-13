# ReferralHandshake (Protocol RHP-1) — Product Requirements Document (PRD)

**System:** Referral Handshake Protocol (RHP-1) & Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru)  
**Build Constraint:** 24-hour build, 2 engineers, 5-minute pitch with a live demo of $\ge 30\text{ s}$ `[V]`  
**Data Posture:** Synthetic data only (`REAL_DATA=0`)  
**First Clinical Pathway:** Emergency Obstetric Referral across Karnataka-style tiers (`PHC -> CHC -> FRU / DH -> MC`); generic data model supporting `OBSTETRIC_EMERGENCY`, `NEONATAL`, `TRAUMA`, `CARDIAC`, and `STROKE`.

---

## 1. Document Authority, Input Precedence & Evidence Tag Legend

### 1.1 Strict Input Precedence Hierarchy (Non-Negotiable)
Any ambiguity across project artifacts is resolved strictly in this descending order of authority:
1. `ReferralHandshake_LOCKED_Problem_Statement_v7.md` (Highest authority on problem framing, empirical evidence tags, and claims discipline).
2. Research findings tagged `[V]` inside the locked source documents.
3. `ReferralHandshake_v8_LOCKED_Solution.md` (Authority on `D1`–`D20` defect fixes, 28 real-world scenarios, 40-item loophole ledger, and operating model).
4. `ReferralHandshake_FINAL_LOCKED_Architecture.md` (Ultimate authority on `F1`–`F20` closures, `I1`–`I16` invariants, 24-table PostgreSQL 16 DDL, 10-step `apply_command()` pipeline, timing math, Quint specification, independent Python monitor, and `T0`–`T3` tiers).
5. `ReferralHandshake_3Gem_Antigravity_Workflow.md` (Authority on multi-agent governance, `AGENTS.md`, Lane A / Lane B isolation, and build verification loops).

### 1.2 Epistemic & Verification Status Tags
- **`[V]`**: Verified from primary research or official technical documentation.
- **`[V*]`**: Verified only from a secondary, blog, law-firm, or vendor source; must be confirmed from primary text before appearing on a slide.
- **`[CONFLICT]`**: Primary/secondary research sources disagree; quote conservatively as specified.
- **`[GAP]`**: No reliable empirical fact or settled legal interpretation found; parameterized in software, and no factual claim may be made.
- **`[verify]`**: Requires pre-event hardware/sandbox execution per the Pre-Event Verification Checklist.
- **`CLOSED`**: Weakness eliminated by a deterministic mechanism verified by a named automated test.
- **`BOUNDED`**: Weakness constrained within a stated quantitative/operational residual monitored by an explicit alarm.
- **`OPEN`**: Residual risk requiring external legal, administrative, or hardware action, assigned to a named owner.

---

## 2. The Problem: The Referral Black Box

When a patient requires emergency care that the originating facility cannot provide, a referring clinician, an ambulance crew, and a receiving hospital team must coordinate as one. Empirical studies in urban India demonstrate that inter-facility referral is routinely an unconfirmed message rather than an owned commitment.

### 2.1 Empirical Evidence Base

| Finding | Setting & Source | Status & Usage Rule |
|---|---|---|
| Referring facility phoned the receiving facility in $47\%$ of referrals ($11,988$); $53\%$ had no prior phone contact | Urban Maharashtra, 2016–2019, $199,888$ deliveries (Das et al., 2023) | `[V]`; denominator is $25,253$ in some reports and $28,020$ in others `[CONFLICT]`. The $47\%$, $37\%$, and $60\%$ figures reproduce only with $25,253$; quote percentages only and verify paper tables. |
| $37\%$ of referral slips were fully documented ($9,279$) | Same study (Das et al., 2023) | `[V]` |
| $60\%$ of referred women could be tracked at the higher facility; authors attribute the $40\%$ loss to incomplete documentation and demographic errors | Same study (Das et al., 2023) | `[V]` |
| $19\%$ of referrals were driven purely by missing resources; within that resource-driven group: no emergency OT ($47\%$), no NICU ($45\%$), no anaesthetist ($24\%$), no paediatrician ($22\%$) | Same study (Das et al., 2023) | `[V]`; quote shares strictly as percentages *within* the $19\%$ resource-driven group. |
| $90.6\%$ of critically ill obstetric patients arrived with no prior communication; $70\%$ had no escort; referral slips were incomplete in $50\%$ | Safdarjung Hospital, Delhi, $3,220$ inter-facility referrals, 2018–2023 | `[V]`; always qualify as "one tertiary obstetric ICU centre". |
| $47.3\%$ had visited two or more hospitals before arriving ("ping-pong"); authors link this to delay | Same audit (Safdarjung Hospital, 2018–2023) | `[V]`; qualify as "one tertiary obstetric ICU centre". |
| Asynchronous digital referral handled $52\%$ of one hospital's gynaecology referrals by advice alone, but evaluation found delays when receivers did not respond because there was no mandated response time | Vula Mobile (South Africa) evaluation | `[V]`; direct empirical evidence for enforced response deadlines. Process claims only. |
| Call for GIS mapping of facilities, bed availability, critical-care readiness, and command centres linked toward ERSS 112 | National Ambulance Services (NAS) Guidelines 2026 (29 June 2026) | `[V]` via PIB/secondary summaries; read official text before quoting clauses. States desired outcome, not a handover protocol. |
| Automatic inter-facility escalation and a hard single-owner guarantee were not found in public documentation of audited systems | Audit of ABDM FHIR resources, eSanjeevani, NIC e-Hospital, CHT, DHIS2, OpenSRP, Pulsara, ReferralMD, Epic Transfer Center | `[V*]`; closed systems and Karnataka state referral systems could not be inspected `[GAP]`. Use exact phrase: *"Not found in public documentation of the systems audited"*. |
| National prevalence of referral failure, ambulance-minutes lost in India, and mortality effect of digital handshakes | Literature review across Waves 1–4 | `[GAP]`; zero claims permitted on national prevalence, measured time saved, or lives saved. |

### 2.2 Theoretical Framing & Locked Problem Statement
- **Three Delays Framing:** The Three Delays model defines the second delay as reaching an adequate facility and the third delay as receiving adequate care upon arrival `[V]`. Literature classifies referral-communication failure inconsistently across the second delay, third delay, or a proposed "fourth delay" `[V*]`. **Position:** Referral handover failure sits at the contested boundary between delays two and three. The project does not address the first delay.
- **Locked Problem Statement:**
  > *"How can an emergency referral stop being a message and become a verifiable contract: one that is offered, answered, negotiated, owned by exactly one destination, escalated automatically when nobody responds, never delays care, works from a feature phone to a command centre, survives failures, and closes with an outcome back to the referrer, with its guarantees provable rather than promised?"*
- **Locked Pitch Line:**
  > *"Today a referral is shouted across a street. ReferralHandshake makes it a signed-for handover, and proves the signature holds, live."*

---

## 3. Product Vision, Three-Part USP, MVP & Coherence Rule

### 3.1 Big Goal
**"No emergency referral without a receipt."** Establish the open **Referral Handshake Protocol (RHP-1)** and its reference platform, starting with emergency obstetric referrals through Karnataka-style tiers (`PHC -> CHC -> FRU -> DH -> MC`) and extending to neonatal, trauma, cardiac, and stroke pathways.

### 3.2 Three-Part Unique Selling Proposition (USP)
All three pillars must operate together:
1. **Contract Semantics:** Structured offer, explicit acknowledgement (`ACK`), structured response vocabulary (`ACCEPT`, `COUNTER`, `DECLINE` with reason), single-owner lease with monotonic fencing epoch (`lease_epoch`), itemized resource commitments (`OT`, `BLOOD`, `ANAESTHETIST`, `PAEDIATRICIAN`, `NICU`), two-level timed escalation (intra-facility notice rungs $\to$ inter-facility catchment chain $\to$ human dispatcher), and mandatory closing outcome.
2. **Reach Without Dependency:** Operates across React PWA web desks, native Android ambulance/clinician apps, outbound automated voice IVR calls (`Exotel`) to basic feature phones with keypad DTMF + PIN, DLT-compliant static SMS alerts, Crockford Base32 paper slip codes, dispatcher proxy entry, and offline outboxes.
3. **Provability:** A frozen control-plane specification (`Quint` `rhp1.qnt` + `transitions.yaml`), bounded model checking, conformance test vectors, 200-way concurrent barrier tests, a separate-author **Independent Python Runtime Monitor** (`rhp_monitor`) that continuously re-derives every referral's state from the hash-chained event log, Ed25519-signed Merkle checkpoints published to independent witnesses, and a live **Guarantee Arena** with a scratch-DB `BROKEN_BUILD` switch.

### 3.3 Minimum Viable Product (MVP — Tier `T0`)
One obstetric referral across four roles (`CLINICIAN`, receiving duty role `NURSE`/`CMO`/`CONSULTANT`, `EMT`, `DISPATCHER`) executing:
`structured referral card -> offer to a facility's duty role -> acknowledge -> accept / counter / decline-with-reason -> single-owner lease -> timer escalation (inside facility via notice ladder, then next facility in chain, then dispatcher) -> parallel transport track -> arrival -> closing outcome`, backed by an append-only hash-chained PostgreSQL 16 event log, durable database deadlines, an offline outbox, Toxiproxy fault injection, `BROKEN_BUILD` scratch DB isolation, and the live Independent Runtime Monitor.

### 3.4 The Coherence Rule (Strict Feature Gate)
Every component in ReferralHandshake must be exactly one of:
- **(a)** A state or event in the RHP-1 contract,
- **(b)** An interface that produces or consumes those contract events, or
- **(c)** A read-only projection/reader of the committed event log.

Anything else is strictly out of scope.

| System Layer | Classification | Role in the RHP-1 Contract |
|---|---|---|
| Referral card, optional AI intake accelerator | **(b) Interface** | Writes the structured clinical and operational *terms* of the contract |
| Resource confirmations, counter-offers | **(a) State / Event** | Records the receiving counterparty's explicit *commitment* |
| Durable deadlines, notice ladder, catchment chain, dispatcher fallback | **(a) State / Event** | Enforces the *obligation to respond* within bounded time $T_{max} \le B$ |
| PWA desks, Android app, Exotel Voice IVR, SMS link, Paper code, Offline outbox | **(b) Interface** | *Delivers* and *captures* contract events across every connectivity tier |
| SHA-256 event hash chain, Ed25519 Merkle checkpoints, device-signed ACKs | **(a) State / (c) Reader** | Produces tamper-evident *evidence* and external witness proofs |
| Quint spec, conformance vectors, independent Python monitor, browser verifier | **(c) Reader** | *Proves* that contract invariants (`I1`–`I16`) hold continuously |
| Command centre map, APOT KPIs, `networkx` graph, FHIR R4 / XES exporters | **(c) Reader** | *Learns* and *exports* from the committed event log without mutating state |

---

## 4. Real-World Operating Model, Personas & Behavioral Engineering

### 4.1 Rostered Duty Roles & Actors
Offers are never sent to a personal individual account; they target a facility's **rostered duty role** (`roster` table):
- **`CLINICIAN`**: Referring medical officer or nurse at the originating `PHC`/`CHC`/`FRU`. Authors the referral card, confirms or rejects counter-offers, or cancels prior to handover.
- **`NURSE` / `CMO` / `CONSULTANT`**: Receiving facility duty slots (`slot_no` $1 \dots S$). Notified concurrently at Rung $0$ (`SSE` + empty-payload `FCM`) and staggered at Rung $A/4$ (`VOICE`). Any authorized slot with a valid session and server-verified PIN can `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `COUNTER`, or `DECLINE`.
- **`EMT`**: Ambulance crew member operating the Android app (`T3`) or PWA GPS fallback (`T1`). Advances the independent transport track (`DISPATCHED -> EN_ROUTE -> ARRIVED -> HANDED_OVER`) and queues offline telemetry (`GPS`, `OBS`).
- **`DISPATCHER`**: 108/command-centre operator. Handles `NOTICE_PROXY` pages at Rung $3A/4$, resolves `ESCALATED_TO_DISPATCHER` referrals via `DISPATCHER_ASSIGN` (`source='DISPATCHER'`, `proxy=true`), and records phone-assisted proxy actions.
- **`ADMIN`**: District or facility administrator managing rosters, enrollment tickets, catchment chains, and cold-key restores.
- **`JUDGE_DESK`**: Read-only or synthetic-race participant admitted via rotating QR code + Cloudflare Turnstile (capped at $20$ concurrent desks).

### 4.2 Incentive Alignment & Anti-Goodhart Protections
1. **Valid Response Vocabulary:** `ACCEPT`, `COUNTER`, and `DECLINE` (with structured missing-resource reason such as `NO_NICU`, `NO_OT`, `AT_CAPACITY`) are all valid, timestamped professional responses. Documenting a missing resource is not penalized; **silence is the only losing move**, and silence triggers automatic escalation.
2. **No Countdown Clocks on Receiving Desks:** Empirical emergency-department studies (MTS triage study `[V]`) show displayed countdown clocks distort clinical decision-making. Receiving desks render an ordered priority queue without countdown timers.
3. **Separation of Acceptance from Handover (APOT):** To detect "accept to hit the KPI, then delay the bed on the ramp" gaming, the system tracks `ARRIVED -> HANDED_OVER` (Ambulance Patient Offload Time) separately from `OFFER_CREATED -> OFFER_ACCEPTED` and flags `ARRIVAL_REJECTED` events.
4. **Capacity Signals, Not Blame:** District command-centre analytics aggregate responsiveness and missing-resource declines at the facility/district level as infrastructure capacity signals, siloed from individual HR records.
5. **Single Entry (Card = Slip):** The digital referral card prints directly with a 9-character Crockford Base32 paper code and QR code, serving as the physical referral slip so clinicians never double-enter data.

---

## 5. Core Functional Requirements: The Handshake Contract (RHP-1)

### 5.1 FR-1: Two Independent Parallel Tracks & Non-Blocking Care (`I3`, Fix `D1`/`D2`)
- **Handshake Track (`referral.hs_state`):** Governs institutional ownership of the patient (`CREATED`, `OFFERED`, `ACKNOWLEDGED`, `ACCEPTED`, `COUNTERED`, `ESCALATED_TO_DISPATCHER`, `CANCELLED`, `CLOSED`).
- **Transport Track (`referral.tr_state`):** Governs physical ambulance movement (`REQUESTED`, `DISPATCHED`, `EN_ROUTE`, `ARRIVED`, `HANDED_OVER`, `TR_CANCELLED`).
- **Strict Independence (`I3`):** The `TR_UPDATE` and `TR_DESTINATION_CHANGE` execution paths never read `hs_state` (except to verify the referral is not terminal `CLOSED`/`CANCELLED`). An ambulance can depart immediately toward the primary destination while the handshake is still negotiating. If ownership shifts to another facility, the crew and dispatcher receive a redirect advisory with cached Mapbox detour ETAs; the system **never** autonomously reroutes a moving ambulance.
- **Pre-Referral $\text{MgSO}_4$ Rule (Fix `D1`):** `referral.mgso4_status` is an enum (`GIVEN`, `NONE_GIVEN`, `UNKNOWN`). It is **answer-required, never knowledge-required**. Selecting `UNKNOWN` is valid, never blocks `CREATE` or ambulance dispatch, and automatically triggers a high-visibility red warning banner on the receiving desk: *"Pre-referral $\text{MgSO}_4$ dose unknown — verify before dosing"*.

### 5.2 FR-2: State Machines & Complete 14-Command Transition Specification
All state mutations execute exclusively through the 10-step `apply_command()` pipeline under `SELECT * FROM referral WHERE id = %s FOR UPDATE`.

- **Referral `hs_state` values (8):** `CREATED`, `OFFERED`, `ACKNOWLEDGED`, `ACCEPTED`, `COUNTERED`, `ESCALATED_TO_DISPATCHER`, `CANCELLED`, `CLOSED`. (Note: `referral.hs_state` reflects the lead open offer—highest step among open offers, where `ACCEPTED` wins).
- **Offer `status` values (10):** `OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`, `ACCEPTED`, `DECLINED`, `TIMED_OUT`, `SUPERSEDED`, `ARRIVAL_REJECTED`, `WITHDRAWN`.
- **Open Offer Subset (`I12`):** `{'OPEN', 'ACKED', 'COUNTERED', 'SOFT_OPEN'}`. The database enforces `open_offers BETWEEN 0 AND 2`.
- **Transport `tr_state` values (6):** `REQUESTED`, `DISPATCHED`, `EN_ROUTE`, `ARRIVED`, `HANDED_OVER`, `TR_CANCELLED`.

| Command | Authorized Actor | Pre-State Guard | Atomic State & Side-Effect Transitions | Error Codes |
|---|---|---|---|---|
| `CREATE` | Rostered `CLINICIAN` (or `DISPATCHER` proxy) | Referral does not exist | Insert `referral` (`version=1`, `lease_epoch=0`, `tr_state='REQUESTED'`), snapshot `chain` (truncated to profile max $F$), create `key_version` + `clinical_payload` + `payload_grant` for origin. If `chain` non-empty: insert `offer` (`OPEN`) for `chain[0]` (`SEQUENTIAL`) or `chain[0..1]` (`PARALLEL2`), grant payload to offered facility(ies), insert `ACK`, `NOTICE_VOICE`, `NOTICE_PROXY` deadlines, set `hs_state='OFFERED'`. If `chain` empty: set `hs_state='ESCALATED_TO_DISPATCHER'` and insert `DISPATCH_ACTION` deadline. Emit `REFERRAL_CREATED` (+ `OFFER_CREATED`). | `422 SCHEMA`, `403 FORBIDDEN` |
| `ACK` | Receiving duty role (`PWA` / `VOICE`) | Target `offer.status == 'OPEN'` | Set `offer.status='ACKED'`, `acked_at=ts`, `acked_by=roster_id`; mark `ACK`, `NOTICE_VOICE`, `NOTICE_PROXY` deadlines `DONE`; insert `DECISION` deadline (`due_at = ts + D`); if prior offer $k-1$ is `SOFT_OPEN`, set $k-1$ to `TIMED_OUT` and revoke its `payload_grant`; update `hs_state='ACKNOWLEDGED'`. Emit `OFFER_ACKED`. | `409 INVALID_TRANSITION` |
| `RESOURCE_CONFIRM` | PIN-verified receiving role (live online only) | Target `offer.status` in `{'OPEN', 'ACKED', 'SOFT_OPEN'}` | Upsert `offer_resource_confirmation(offer_id, capability, confirmed_by, confirmed_at=ts, expires_at=ts+confirm_ttl)`. Emit `RESOURCE_CONFIRMED`. | `409 INVALID_TRANSITION`, `422 SCHEMA` |
| `ACCEPT` | PIN-verified receiving role | Target `offer.status` in `{'OPEN', 'ACKED', 'SOFT_OPEN'}`; `referral.lease_offer_id IS NULL`; every capability in `need_class_requirement` confirmed with `expires_at > ts` (`I15`) | Set `offer.status='ACCEPTED'`, `decided_at=ts`; increment `referral.lease_epoch = lease_epoch + 1`; set `lease_offer_id=offer.id`, `lease_facility_id=offer.facility_id`, `hs_state='ACCEPTED'`; transition all other open offers (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) to `SUPERSEDED` and revoke their `payload_grant`s; cancel pending offer deadlines and insert `HANDOVER` deadline (`due_at = ts + H`). Emit `OFFER_ACCEPTED`, `LEASE_GRANTED`. | `409 LEASE_HELD`, `409 LATE_ACCEPT_REJECTED`, `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`, `412 PRECONDITION_FAILED` |
| `COUNTER` | PIN-verified receiving role | Target `offer.status` in `{'OPEN', 'ACKED'}` and `offer.counter_round < 2` | Set `offer.status='COUNTERED'`, `counter_round = counter_round + 1`, `counter_mask = cmd.mask`; cancel `DECISION` deadline and insert `COUNTER_CONFIRM` deadline with `due_at = ts + min(C, remaining_D)`; update lead `hs_state='COUNTERED'`. Emit `OFFER_COUNTERED`. | `409 INVALID_TRANSITION`, `422 COUNTER_LIMIT` |
| `CONFIRM_COUNTER` | Referring `CLINICIAN` (or `DISPATCHER` proxy) | Target `offer.status == 'COUNTERED'` | If `cmd.confirmed == true`: re-verify `I15` resource confirmations and `lease_offer_id IS NULL`, then execute `ACCEPT` path (`lease_epoch + 1`, supersede other open offers, `hs_state='ACCEPTED'`). If `cmd.confirmed == false`: set `offer.status='DECLINED'`, revoke `payload_grant`, call `advance()`. Emit `COUNTER_RESOLVED`. | `409 LEASE_HELD`, `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` |
| `DECLINE` | PIN-verified receiving role | Target `offer.status` in `{'OPEN', 'ACKED', 'SOFT_OPEN', 'COUNTERED'}` | Set `offer.status='DECLINED'`, `decline_reason=cmd.reason`, `decided_at=ts`; cancel offer deadlines; revoke facility's `payload_grant`; call `advance()`. Emit `OFFER_DECLINED`. | `409 INVALID_TRANSITION` |
| `TIMEOUT` | System (`poller`) | `deadline.status == 'PENDING'` and matches `offer.step` / `referral.lease_epoch` | Mark `deadline.status='DONE'`. **Case 1 (`NOTICE_VOICE` / `NOTICE_PROXY`):** enqueue outbox rows for voice rung or dispatcher proxy page; emit `NOTICE_SENT`. **Case 2 (`ACK` expiry):** if offer still `OPEN` (silent), in `SEQUENTIAL` set `offer.status='SOFT_OPEN'` (if a next target exists and cap allows; any older `SOFT_OPEN` offer $k-1$ becomes `TIMED_OUT` and loses its grant) and open next target in `chain`; in `PARALLEL2` or if no next target, set `TIMED_OUT`, revoke grant, and call `advance()`; if offer is already `ACKED` (undecided), emit `ADVISORY_PREWARM` to next facility in `chain` (not an offer). **Case 3 (`DECISION` / `COUNTER_CONFIRM` expiry):** in `SEQUENTIAL` with available next target, set `offer.status='SOFT_OPEN'` (closing any older `SOFT_OPEN`) and open next target; otherwise set `TIMED_OUT`, revoke grant, and call `advance()`. **Case 4 (`HANDOVER` / `DISPATCH_ACTION` / `CLOSURE` expiry):** emit overdue event (`HANDOVER_OVERDUE` / `CLOSURE_OVERDUE`), re-page dispatcher, and re-arm deadline; on second `CLOSURE` expiry, auto-execute `CLOSE(outcome='UNKNOWN_COUNTER_REFERRAL', proxy=true, actor=system)`. | `200 OK` (no-op if deadline not `PENDING`) |
| `ARRIVAL_REJECTED` | Receiving desk or `EMT` | `referral.hs_state == 'ACCEPTED'` | Set `offer.status='ARRIVAL_REJECTED'`; increment `referral.lease_epoch = lease_epoch + 1`; clear `lease_offer_id` and `lease_facility_id`; revoke facility's `payload_grant`; cancel `HANDOVER` deadline; call `advance()`. Emit `ARRIVAL_REJECTED`, `LEASE_REVOKED`. | `409 INVALID_TRANSITION` |
| `DISPATCHER_ASSIGN` | `DISPATCHER` | `hs_state == 'ESCALATED_TO_DISPATCHER'` (or live referral with mandatory `override` reason enum) | Supersede/withdraw any existing open/accepted offer; insert or update `offer` (`source='DISPATCHER'`, `status='ACCEPTED'`, `proxy=true`); increment `lease_epoch = lease_epoch + 1`; set `lease_offer_id`, `lease_facility_id`, `hs_state='ACCEPTED'`; grant `payload_grant`; insert `HANDOVER` deadline. Emit `DISPATCHER_ASSIGNED`, `LEASE_GRANTED`. | `409 LEASE_HELD` |
| `TR_UPDATE` | `EMT`, `DISPATCHER`, or `SYSTEM` (for `ARRIVAL_SUGGESTED` only) | Referral not in `{'CLOSED', 'CANCELLED'}` | Never reads `hs_state` (`I3`). Geofence trigger emits `ARRIVAL_SUGGESTED` without changing `tr_state`. Human-confirmed transition updates `tr_state` (`REQUESTED -> DISPATCHED -> EN_ROUTE -> ARRIVED -> HANDED_OVER` or `TR_CANCELLED`). When `tr_state` reaches `HANDED_OVER`, cancel `HANDOVER` deadline and insert `CLOSURE` deadline (`due_at = ts + CLOSURE`). Emit `TR_UPDATED`. | `409 INVALID_TR` |
| `CANCEL` | `CLINICIAN` or `DISPATCHER` | Referral not in `{'CLOSED', 'CANCELLED'}` | Set `hs_state='CANCELLED'`, `tr_state='TR_CANCELLED'` (if not handed over), `outcome=cmd.outcome`, `closed_at=ts`; set all open/accepted offers to `WITHDRAWN`; clear lease; revoke all active `payload_grant`s; mark all `PENDING` deadlines `CANCELLED`. Emit `CANCELLED`. | `409 INVALID_TRANSITION` |
| `CLOSE` | Receiving role, `DISPATCHER`, or `SYSTEM` (after $2\times$ `CLOSURE` expiry) | `hs_state` in `{'ACCEPTED', 'ESCALATED_TO_DISPATCHER'}` and valid `outcome` enum | Verify `ADMITTED_STABLE`, `ADMITTED_CRITICAL`, and `DELIVERED_AT_RECEIVER` require `tr_state == 'HANDED_OVER'`. Set `hs_state='CLOSED'`, `outcome=cmd.outcome`, `closed_at=ts`; mark all `PENDING` deadlines `DONE`/`CANCELLED`; revoke remaining `payload_grant`s; schedule `clinical_payload` crypto-shredding. Emit `CLOSED`. | `422 OUTCOME_REQUIRED`, `409 HANDOVER_REQUIRED` |
| `REVOKE_GRANT` | `ADMIN`, `DISPATCHER`, or `SYSTEM` | Active `payload_grant` (`revoked_at IS NULL`) | Set `payload_grant.revoked_at=ts`, `revoke_reason=cmd.reason`; enqueue immediate `SSE` control frame `GRANT_REVOKED`. Emit `GRANT_REVOKED`. | `409 GRANT_NOT_ACTIVE` |

### 5.3 FR-3: v7-to-RHP-1 State Mapping (`F19`) & Closure Taxonomy (`F6`)

| Locked v7 Conceptual State | `referral.hs_state` | `offer.status` | `referral.tr_state` | Committed `event.type` |
|---|---|---|---|---|
| `CREATED` | `CREATED` (transient inside `CREATE` txn) | — | `REQUESTED` | `REFERRAL_CREATED` |
| `OFFERED` | `OFFERED` | `OPEN` | any | `OFFER_CREATED` |
| `ACKNOWLEDGED` | `ACKNOWLEDGED` | `ACKED` | any | `OFFER_ACKED` |
| `ACCEPTED` | `ACCEPTED` | `ACCEPTED` | any | `OFFER_ACCEPTED`, `LEASE_GRANTED` |
| `COUNTERED` | `COUNTERED` | `COUNTERED` | any | `OFFER_COUNTERED` |
| `DECLINED` | `OFFERED` or `ESCALATED_TO_DISPATCHER` (post-`advance()`) | `DECLINED` | any | `OFFER_DECLINED` |
| `TIMED_OUT` | `OFFERED` or `ESCALATED_TO_DISPATCHER` (post-`advance()`) | `TIMED_OUT` or `SOFT_OPEN` | any | `DEADLINE_TIMEOUT` |
| `ESCALATED` | `OFFERED` (`ladder_cursor + 1`) | next `OPEN` | any | `OFFER_CREATED` (`reason='ESCALATION'`) |
| `ARRIVAL_REJECTED` | `OFFERED` or `ESCALATED_TO_DISPATCHER` | `ARRIVAL_REJECTED` | `ARRIVED` | `ARRIVAL_REJECTED`, `LEASE_REVOKED` |
| `ESCALATED_TO_DISPATCHER` | `ESCALATED_TO_DISPATCHER` | — | any | `ESCALATED_TO_DISPATCHER` |
| `CANCELLED` | `CANCELLED` | `WITHDRAWN` | any / `TR_CANCELLED` | `CANCELLED` |
| `CLOSED` | `CLOSED` | — | `HANDED_OVER` or outcome-specific | `CLOSED` |

- **Locked 9-Value Outcome Taxonomy (`referral.outcome`):**
  1. `ADMITTED_STABLE` (requires `tr_state == 'HANDED_OVER'`)
  2. `ADMITTED_CRITICAL` (requires `tr_state == 'HANDED_OVER'`)
  3. `DELIVERED_AT_RECEIVER` (requires `tr_state == 'HANDED_OVER'`)
  4. `DELIVERED_EN_ROUTE`
  5. `PATIENT_REFUSED`
  6. `TRANSPORT_CANCELLED`
  7. `DETERIORATED_OR_DIED_PRE_HANDOVER`
  8. `REDIRECTED_ON_ARRIVAL`
  9. `UNKNOWN_COUNTER_REFERRAL` (used by explicit receiver selection or by system auto-close after $2\times$ `CLOSURE` deadline expiry; never fabricates a clinical outcome).

### 5.4 FR-4: Arrival Semantics (`F5` Cases a–f)
Geofencing ($200\text{ m}$ radius + dwell time + speed check) **never** transitions `tr_state` to `ARRIVED` on its own; it emits `ARRIVAL_SUGGESTED` only. A human (`EMT`, receiving desk, or `DISPATCHER` proxy) must confirm `ARRIVED`.
- **Case (a) Arrival at current lease holder:** Geofence emits `ARRIVAL_SUGGESTED`; `EMT` or receiving desk confirms `TR_UPDATE(ARRIVED)`.
- **Case (b) Arrival at a facility with an `OPEN`, `ACKED`, or `SOFT_OPEN` offer:** Receiving desk may `ACCEPT` immediately after completing live `RESOURCE_CONFIRM` checks (`I15`).
- **Case (c) Unannounced arrival at a facility with no offer:** Emits `ARRIVAL_AT_NON_OWNER` urgent alert and pages the dispatcher; **never blocks emergency clinical care**; dispatcher may formalize ownership via `DISPATCHER_ASSIGN`.
- **Case (d) En-route destination change:** Crew or dispatcher issues `TR_DESTINATION_CHANGE` with a structured reason enum; the system never reroutes autonomously.
- **Case (e) Crew refuses a redirect advisory:** `TR_DESTINATION_CHANGE(accepted=false)` is logged with reason; `lease_facility_id` remains unchanged; dispatcher is paged immediately.
- **Case (f) Ambulance already past the highway turn-off when ownership changes:** Advisory displays the cached Mapbox Matrix detour ETA; crew decides whether to divert or continue to the prior destination (which triggers Case (c) on arrival).

### 5.5 FR-5: Unified Offer-ACK Window, Signed Timing Profiles & $T_{max}$ Math (`F2`, `F3`, `I13`)
- **Unified Notice Ladder inside Window $A$ (`F2`):**
  - $t = 0$: Offer opens (`OPEN`); `SSE` + empty-payload `FCM` wake sent concurrently to all $S$ rostered slots at the target facility.
  - $t = A/4$: `NOTICE_VOICE` deadline fires; outbound Exotel IVR calls slot $i \in \{0 \dots S-1\}$ at $A/4 + i \cdot \delta$.
  - $t = 3A/4$: `NOTICE_PROXY` deadline fires; dispatcher console receives a proxy phone-assist page.
  - $t = A$: `ACK` deadline fires (`TIMEOUT`). Any `ACK` prior to $A$ cancels remaining notice rungs and starts the hard `DECISION` window $D$.
- **Worst-Case Escalation Bound (`F3`, `I13`):**
  Because all $S$ intra-facility slots are notified within window $A$ and all counter-offer rounds (`counter_round <= 2`) are bounded inside the remaining decision window $D$ (`min(C, remaining_D)`), a single facility can consume at most $A + D$ plus one hop budget $\epsilon$ (poller interval + transaction execution budget). Across at most $F$ facilities in `referral.chain`:
  $$T_{max} = F \cdot (A + D + \epsilon) \le B$$
  And when voice is enabled, the voice stagger must fit inside the ladder before $3A/4$:
  $$\frac{A}{4} + (S - 1)\delta + V \le \frac{3A}{4}$$

| Parameter | `PILOT_OB_CRITICAL` | `PILOT_STANDARD` | `DEMO_FAST` | `DEMO_VOICE` |
|---|---|---|---|---|
| $A$ (ACK window, $\text{ms}$) | $60,000$ | $120,000$ | $3,000$ | $45,000$ |
| $D$ (Decision window, $\text{ms}$) | $180,000$ | $300,000$ | $4,000$ | $20,000$ |
| Notice rungs ($0, A/4, 3A/4$ in $\text{ms}$) | $0 / 15,000 / 45,000$ | $0 / 30,000 / 90,000$ | $0 / 750 / 2,250$ | $0 / 11,250 / 33,750$ |
| Slots $S$, Stagger $\delta$ ($\text{ms}$), Call budget $V$ ($\text{ms}$) | $3, 5,000, 20,000$ | $3, 10,000, 20,000$ | $3, 0, \text{voice off}$ | $1, 0, 20,000$ |
| Max facilities $F$ | $3$ | $3$ | $3$ | $2$ |
| Hop budget $\epsilon$ ($\text{ms}$) | $3,000$ | $3,000$ | $1,000$ | $1,000$ |
| Counter confirm $C$ ($\text{ms}$) | $90,000$ | $150,000$ | $2,000$ | $10,000$ |
| Resource `confirm_ttl` ($\text{ms}$) | $120,000$ | $180,000$ | $10,000$ | $60,000$ |
| `HANDOVER` $H$ / `DISPATCH_ACTION` / `CLOSURE` ($\text{ms}$) | $7,200,000 / 300,000 / 86,400,000$ | $7,200,000 / 300,000 / 86,400,000$ | $30,000 / 5,000 / 20,000$ | $60,000 / 10,000 / 60,000$ |
| Computed $T_{max} = F \cdot (A + D + \epsilon)$ | $729,000\text{ ms}$ ($729\text{ s}$) | $1,269,000\text{ ms}$ ($1,269\text{ s}$) | $24,000\text{ ms}$ ($24\text{ s}$) | $132,000\text{ ms}$ ($132\text{ s}$) |
| Hard Bound $B$ | $900,000\text{ ms}$ ($900\text{ s}$) | $1,500,000\text{ ms}$ ($1,500\text{ s}$) | $25,000\text{ ms}$ ($25\text{ s}$) | $150,000\text{ ms}$ ($150\text{ s}$) |
| Permitted when `REAL_DATA=1` | Yes | Yes | **No (refuses boot)** | **No (refuses boot)** |

---

## 6. Reach, Client, Clinical & Interoperability Requirements

### 6.1 Outbound Exotel Voice IVR (`T2_REACH`, `F7`)
- **Outbound Only:** Calls pre-registered duty numbers (`roster.phone_e164`). Trial limit: $\le 10$ whitelisted numbers `[V]`.
- **Voicemail / AMD Gate (`F7`):** Upon connection, checks Answering Machine Detection (AMD) and enforces an $8\text{ s}$ keypress gate: *"Press 1 to hear an emergency referral"*. Voicemail, silence, or machine verdict produces zero `ACK` and logs `UNANSWERED`.
- **De-Identified Native Audio:** Pressing `1` commits `apply_command(ACK, channel='VOICE')` and plays pre-recorded native audio phrases (Kannada, Hindi, English) stating originating facility, `need_class` code, and ETA. **No patient name or PHI is ever spoken.**
- **DTMF Action + PIN:** Keypad menu (`1` Accept, `2` Counter conditions, `3` Decline, `9` Repeat) followed by 4-digit PIN terminated by `#` (encoded as `%23`).
- **Webhook Latency Budget:** Exotel requires HTTP 200 within $5\text{ s}$ `[V]`; RHP-1 enforces a $2\text{ s}$ internal budget ($1.5\text{ s}$ for `apply_command`), deduplicating retries via `inbox(source, external_id)` (`ON CONFLICT DO NOTHING`) and playing *"recorded"* only after PostgreSQL transaction commit.

### 6.2 Paper Code (`T2_REACH`)
- Every printed referral card carries an 8-symbol Crockford Base32 payload ($40\text{ bits}$, integer $N$) plus 1 check symbol equal to $N \bmod 37$ mapped onto the 37-symbol Crockford check alphabet (`0-9A-Z*~$=U`).
- Because $37$ is prime and $32^i \not\equiv 0 \pmod{37}$, $100\%$ of single-character substitutions ($\Delta \cdot 32^i \not\equiv 0 \pmod{37}$) and $100\%$ of adjacent transpositions of distinct symbols ($(a - b) \cdot 32^i \cdot 31 \not\equiv 0 \pmod{37}$) are rejected client-side and server-side before hitting the database. Rate-limited to $10\text{ attempts/min}$ per session.

### 6.3 Optional AI Intake Accelerator (`T3_EXTRAS`, `§16`)
- Behind feature flag `T3_EXTRAS`; system operates $100\%$ with AI disabled.
- **Cognitive Forcing Function (CFF):** When a clinician uploads a photo or dictation of a referral slip, the backend withholds the AI draft (`HTTP 423 ANCHOR_REQUIRED`) until the clinician manually commits two anchor fields: `need_class` and `mgso4_status`.
- **No Confidence Scores or Explanations:** Neither percentage confidence scores nor prose explanations are displayed (empirical research shows explanations increased commission errors from $10\%$ to $21\%$ `[V]`). Critical fields require manual re-entry, and a fast-approve speed bump applies exclusively to AI drafts, never to manual entry or dispatch.

---

## 7. Complete 28-Scenario Behavioral Catalogue (`v8 §4.8`)

Every scenario below is a mandatory behavioral requirement and maps directly to a conformance vector:

| # | Real-World Scenario | Required RHP-1 System Behavior | Primary Invariants / Fixes |
|---|---|---|---|
| 1 | Receiver has no smartphone | Outbound Exotel voice call at Rung $A/4$ with Press-1 gate + PIN; dispatcher proxy page at Rung $3A/4$ if unanswered | `I1`, `I6`, `F2`, `F7` |
| 2 | Receiver cannot take patient but knows who can | `DECLINE` with structured missing-resource reason and optional redirect suggestion (displayed as advisory only; never auto-followed) | `I7`, `I9` |
| 3 | Receiver can take patient only partly | `COUNTER` with bitmask of conditions (`counter_round <= 2`); referrer executes `CONFIRM_COUNTER(true/false)` within $\min(C, \text{remaining } D)$ | `I12`, `F13` |
| 4 | Duty nurse is busy | Rung $0$ notifies all $S$ rostered slots (`NURSE`, `CMO`, `CONSULTANT`) concurrently; Rung $A/4$ staggers voice calls across slots $0 \dots S-1$ by $\delta$ | `I1`, `F2`, `F3` |
| 5 | Two facilities accept simultaneously (`PARALLEL2`) | Referral row lock + `one_lease` partial unique index grants lease to first committer (`200 OK`, `lease_epoch + 1`); second gets `409 LEASE_HELD` and its offer becomes `SUPERSEDED` | `I2`, `I14` |
| 6 | Late accept after timeout escalation (`SEQUENTIAL`) | Timed-out offer $k$ stays `SOFT_OPEN` while $k+1$ is `OPEN`; if $k$ accepts before $k+1$ `ACK`s, $k$ wins and $k+1$ is `SUPERSEDED`; once $k+1$ `ACK`s, $k$ becomes `TIMED_OUT` and gets `409 LATE_ACCEPT_REJECTED` | `I2`, `I12`, `F13` |
| 7 | Receiver accepts, then cannot take patient on arrival | `ARRIVAL_REJECTED` increments `lease_epoch`, clears lease, revokes `payload_grant`, logs broken commitment, and calls `advance()` | `I2`, `I10` |
| 8 | All approved facilities in catchment chain fail | `advance()` transitions referral to `ESCALATED_TO_DISPATCHER` and arms `DISPATCH_ACTION` deadline; system never invents a destination | `I1`, `I7` |
| 9 | Ambulance in network dead zone | Android Room / PWA queues `GPS` and `OBS` telemetry with UUIDv7 `event_id`; UI shows *"last confirmed $N\text{ s}$ ago"*; reconnect merges via idempotent set-union | `I3`, `I4` |
| 10 | Server or internet down at origin/destination | Clinical and phone procedures continue unchanged; printed card carries 9-char Crockford Base32 paper code; outbox reconciles on reconnect | `I3`, `I4` |
| 11 | Wrong person attempts to `ACCEPT` | Step 2–3 verifies active `session`, `roster` slot validity, facility match, and Argon2id PIN; rejects with `403` and logs in `rejected_command` | `I6`, `F7` |
| 12 | Ambulance crew cannot use the app | `DISPATCHER` or receiving desk submits `TR_UPDATE` with `proxy=true`, `proxy_for=<roster_id>`, and mandatory reason enum | `I3`, `I6` |
| 13 | Paper slip arrives before/without digital lookup | Receiving desk enters 9-char Crockford Base32 code (`mod 37` verified) to locate referral or flag unannounced arrival | `F5` |
| 14 | iPhone / iOS Safari with restricted backgrounding & no WebCrypto Ed25519 | Foreground flush only (no background claim); pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256` execute verification over LAN HTTP or HTTPS | `I5`, `D1` |
| 15 | AI intake draft contains hallucinated/wrong values | Draft withheld (`423 ANCHOR_REQUIRED`) until `need_class` + `mgso4_status` anchored; critical fields require re-entry; works with AI off | `A1`, `A2` |
| 16 | Patient delivers or stabilizes before departure | `CLINICIAN` issues `CANCEL(outcome='DELIVERED_EN_ROUTE' | 'TRANSPORT_CANCELLED')`; all open/accepted offers become `WITHDRAWN` and grants revoke | `I5`, `I10`, `F6` |
| 17 | Patient or family refuses transfer | `CANCEL(outcome='PATIENT_REFUSED')` committed and audited; all active offers withdrawn | `I5`, `F6` |
| 18 | Ambulance breaks down en route | `DISPATCHER` reassigns vehicle and logs `TR_UPDATE`; handshake lease (`hs_state`) is completely unaffected | `I3` |
| 19 | Receiver roster phone number is stale/unreachable | Exotel call fails/unanswered $\to$ next staggered slot $i+1$ at $\delta$ $\to$ Rung $3A/4$ dispatcher proxy $\to$ next facility at $A$ | `I1`, `F2` |
| 20 | Infinite counter-offer negotiation loop | `offer.counter_round` hard-capped at $2$ (`CHECK (counter_round BETWEEN 0 AND 2)`) inside original decision window $D$ | `I13`, `F13` |
| 21 | Duplicate referral created for the same patient | Paper code / active facility referral list surfaces existing card for manual linking; system never silently auto-merges clinical records | `I4` |
| 22 | Client device clock is skewed by hours | Deadlines and ordering use `GREATEST(clock_timestamp(), referral.head_ts)` under referral lock; `client_ts_ms` recorded for audit only | `I16`, `F11` |
| 23 | SIM swap or repeated PIN guessing | Per-session/per-`call_sid` Argon2id failure counter in autonomous transaction; $0\text{ s}, 5\text{ s}, 30\text{ s}$ backoff then $120\text{ s}$ lock (`429 PIN_LOCKED`); repeated lockouts suspend slot | `I6`, `F7` |
| 24 | Dispatcher overrides chain or forces assignment | `DISPATCHER_ASSIGN` requires explicit reason enum, sets `source='DISPATCHER'` and `proxy=true`, increments `lease_epoch`, and flags monitor | `I6`, `I7` |
| 25 | Hospital accepts to game KPIs but holds patient on ramp | APOT (`ARRIVED -> HANDED_OVER`) tracked separately from acceptance; `HANDOVER` deadline fires `HANDOVER_OVERDUE` pages | `I1`, `K2` |
| 26 | Tertiary hospital is overloaded with referrals | Facility returns structured `DECLINE(reason='AT_CAPACITY')`; sequential default (`SEQUENTIAL`) and catchment chain order prevent blanket broadcasting | `I7`, `I12` |
| 27 | Flaky cellular network causes rapid retry storm | Step 1 `pg_try_advisory_xact_lock` + `idempotency(actor_id, key)` returns stored `200`/`409`/`412`/`422` response with zero duplicate events | `I4`, `F14` |
| 28 | Referral is handed over but receiver forgets to close | `CLOSURE` deadline fires `CLOSURE_OVERDUE` at $1\times$ and auto-closes at $2\times$ with `outcome='UNKNOWN_COUNTER_REFERRAL'`, `proxy=true`, `actor='SYSTEM'` | `I1`, `I5`, `F6` |