# ReferralHandshake v8 — LOCKED SOLUTION SPECIFICATION

**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 | **Locked:** 10 Nov 2026
**Supersedes:** `referralhandshake_ultimate_spec.md` (Gemini). **Inherits and tightens:** Locked Problem Statement v7.
**Evidence basis:** v7 + Waves 1–4 (R01–R15). Status tags as in v7: **[V]** verified · **[V\*]** secondary/vendor only · **[CONFLICT]** sources disagree · **[GAP]** nothing reliable found. Anything tagged [V\*]/[CONFLICT]/[GAP] must be confirmed from primary sources before it reaches a slide.

---

## 0. Verdict

**Is Gemini's spec the best solution? No.** Its engineering core is good and mostly traceable to the research (serialised writer, fencing, idempotency, outbox, think-first AI friction, Android foreground service, out-of-band monitor). But it solves a narrower problem than the locked statement, contains defects that break the project's own safety promises, and makes claims the research forbids. v8 keeps what is right in it and fixes the rest.

### 0.1 Coverage of the locked problem statement

| Locked clause (v7 §4) | Gemini spec | v8 |
|---|---|---|
| Offered, answered | Partial (accept only) | Full: ack / accept / counter / decline-with-reason |
| Negotiated | No counter-offers | Counter with structured conditions, 2 rounds max |
| Owned by exactly one destination | Yes (single writer + version) | Yes (row lock, lease epoch, late-accept rule) |
| Escalated automatically when nobody responds | One timeout → dispatcher | Two-level ladder (in-facility → next facility → dispatcher) |
| Never delays care | **Violated** (hard-rejects create; no transport track) | Two independent tracks; nothing blocks transport |
| Feature phone → command centre | **Smartphone/web only** | Voice, SMS alert, paper code, proxy, web, Android, command centre |
| Survives failures | Single SQLite file | Postgres + durable timers + offline outbox + replay |
| Closes with outcome | Mentioned | Required: outcome or explicit "unknown" |
| Provable, not promised | Randomised tests + monitor, no spec, "mathematically" overclaimed | Frozen spec, bounded model checking, conformance vectors, independent monitor, honest limits |
| Real-world operating model (duty role, incentives) | Absent | §11 |
| Claims discipline, validation plan | Absent | §14, §12 |

### 0.2 Defects found in the Gemini spec (each closed in v8)

| # | Defect | Severity | Fix in v8 |
|---|---|---|---|
| D1 | "State machine rejects any `CREATED` lacking MgSO4/Oxytocin time and dose" **blocks care** (breaks promise 3). R08 says document it; v7 says never block. | Safety | Field is *answer-required*, not *knowledge-required*: `none given` / `unknown` are valid; missing/unknown flags the card to the receiver, never stops dispatch (§8) |
| D2 | No transport track; `ARRIVED` tied to a geofence alone | Safety/logic | Parallel transport track; geofence only *suggests* arrival, a human confirms (§4.3) |
| D3 | No counter/decline vocabulary, no intra-facility ladder, no referral-loop prevention | Core gap | §4 |
| D4 | No reach beyond smartphones; contradicts the equity claim | Core gap | §6 |
| D5 | Overclaims: "mathematically guarantees", "mathematically impenetrable", "eliminates ping-pong", "zero silent drops", "MTTR 3 s", "mathematical proof of where the district network fractured", "BSA s.63-ready" | Credibility/legal | §14 claims register; every number is measured live or not shown |
| D6 | Dropped the spec and model checking entirely; property-based testing is randomised, not proof (R11) | Proof | Frozen spec + bounded model checking + conformance vectors + PBT (§7) |
| D7 | `version_id` used as lease token; race losers get `412` (should be `409` with reason; `412` is for stale preconditions); lease issue point and late-accept behaviour undefined | Logic | Separate row `version` and `lease_epoch`; explicit late-accept window (§4.4) |
| D8 | SQLite WAL default `synchronous=NORMAL` can lose last commits on power loss; one host, one file; "survives failure" only means process restart | Durability | Postgres primary with synchronous commit; SQLite not used for the contract (§5) |
| D9 | "Crypto-shredding by deleting a per-referral salt" is not crypto-shredding; NMC 3-year retention applicability to referral handover is unverified | Legal/crypto | Envelope encryption, per-referral data key deleted on expiry; retention is a policy parameter needing legal review [GAP] (§10) |
| D10 | "Checkpoint anchoring prevents sysadmin tampering": hash chains only *detect*, and only if outside witnesses hold checkpoints (split-view attack, Wave 2) | Security | Signed checkpoints published to independent witnesses; verifier points at the broken link (§7.4) |
| D11 | JWT issued at QR scan is mintable by bots, so per-token rate limits are meaningless | Security | Challenge before token, admission cap, LAN fallback (§10.2) |
| D12 | "4-digit PIN steps UP → UV" with no statement of where it is verified; brute-forceable | Security | Server-verified PIN, lockout, roster + device/number binding (§10.1) |
| D13 | SSE-saves-battery claim unsupported (SSE also needs keepalives); mobile wake mishandled | Technical | Zero-payload push wake + authenticated fetch on Android; SSE only for web desks (§6.2) |
| D14 | Misquotes: ">98% of clinical capability tags" missing (R07: 98% have a *name*; bed tag 0.08%, emergency 1.03%); "90% bypass" is patient bypass behaviour, not evidence about timeout escalation; "Mapbox absorbs updates into one trip" only under Navigation SDK guidance | Accuracy | Corrected; ETAs computed server-side for top candidates only (§9) |
| D15 | "Routes by verified CEmONC" assumes live capability data that does not exist | Logic | Curated registry + timestamped attestations shown with age; never "live beds" (§9) |
| D16 | Live ProM on stage is fragile; "counterfactual map" from 7 judges' clicks is invalid (R10: shadow processes, STO/CER assumptions) | Demo/credibility | In-app process map from the real log (pm4py/own); no counterfactual claim in the demo |
| D17 | No demo fallback, no code freeze, no offline path (R13) | Demo risk | §13 |
| D18 | No governance: Goodhart risk on dashboards, staff-telemetry notice (DPDP 7(i)), ICMR ethics route, double-entry burden (R14), validation interviews | Real-world | §11–§12 |
| D19 | TeSSLa adds a JVM toolchain; its out-of-order handling is unnecessary once the server assigns a per-referral sequence; independence from server logic not specified | Feasibility | Independent Python monitor with its own transition implementation; TeSSLa optional stretch (§7.3) |
| D20 | No cut lines for a two-person team | Feasibility | §13 |

### 0.3 What v8 keeps from Gemini

Serialised arbitration of acceptance; fencing; `Idempotency-Key` plus payload fingerprint; same-transaction outbox; think-first friction for AI drafts only; native Android foreground location service; 200 m geofence as a *hint*; Mapbox for ETAs; Cloudflare in front; XES export; the hybrid fault-injection demo; the STRIDE highlights.

---

## 1. Ideation: how the best solution was chosen

**Method (7 steps):** root-cause decomposition → design-space map → broad concept generation → weighted scoring → fusion of complementary winners → red-team (pre-mortem) → scenario stress test.

### 1.1 Root causes (what must be solved)

| # | Failure mode | Evidence |
|---|---|---|
| F1 | **Silence**: referral is a message, not a commitment | 53% of referrals had no phone contact (Maharashtra); 90.6% of critically ill obstetric arrivals had no prior communication (Safdarjung) [V] |
| F2 | **Ownerless or doubly-owned patient**, ping-pong | 47.3% visited ≥2 hospitals first (Delhi) [V]; concurrent-accept hazard (R01, R04) |
| F3 | **Capability mismatch** | 19% of referrals resource-driven (no OT 47%, no NICU 45%, no anaesthetist 24%) [V]; only 22% of nominal FRUs fully operational (R08) |
| F4 | **Information loss** | Slips incomplete in 50% (Delhi); 40% untraceable at the higher facility (Maharashtra) [V]; first-dose time/amount of MgSO4 is required on the slip (Dakshata) |
| F5 | **Reach gaps** | 70% no escort (Delhi); dead zones; receivers without apps |
| F6 | **No evidence or loop closure** | No outcome returns to the referrer |
| F7 | **Adoption and incentive failure** | Blame-avoidance, Goodhart gaming (R09), double-entry burden (R14) |
| F8 | **Systemic blindness** | District officers cannot see where referrals stall |

### 1.2 Design space (axes explored)

Coordination model (message relay / dispatcher tool / broker with contract / marketplace / peer mesh) × trust mechanism (none / hash chain / blockchain / formal spec + runtime monitor) × reach (smartphone / web / voice / SMS / paper / proxy) × intelligence (none / rules / AI triage / optimiser) × scope (one pathway / all emergencies / open standard) × data stance (full record / handover record only).

### 1.3 Thirteen concepts, scored

Weights: Impact 20, Real-world operability 15, Safety and legal defensibility 15, Technical soundness/provability 15, Hackathon wow 15, Build feasibility for 2 people 10, Scope/upside 10. Scores are team judgements (0–10); the ranking is robust to moving any single weight by ±5 points.

| Concept | Imp | Oper | Safe | Tech | Wow | Feas | Scope | **Total** |
|---|---|---|---|---|---|---|---|---|
| C1 Gemini spec as written | 6 | 4 | 4 | 6 | 7 | 7 | 5 | 5.6 |
| C2 Locked v7, all layers at once | 8 | 9 | 8 | 8 | 9 | 4 | 8 | 7.9 |
| **C3 v8 (fusion, gated and cut-lined)** | 9 | 9 | 9 | 9 | 10 | 7 | 10 | **9.1** |
| C4 Blockchain referral ledger | 4 | 3 | 4 | 4 | 6 | 5 | 4 | 4.3 |
| C5 AI triage + auto-routing optimiser | 6 | 5 | 2 | 4 | 8 | 5 | 7 | 5.3 |
| C6 Voice/IVR-only referral bridge | 7 | 9 | 7 | 5 | 6 | 8 | 5 | 6.8 |
| C7 Dispatcher command-centre dashboard | 6 | 6 | 7 | 5 | 6 | 7 | 6 | 6.1 |
| C8 FHIR/ABDM e-referral only | 5 | 4 | 6 | 6 | 3 | 5 | 7 | 5.1 |
| C9 District digital-twin as headline | 5 | 3 | 3 | 4 | 8 | 3 | 6 | 4.6 |
| C10 WhatsApp referral bot | 6 | 7 | 1 | 4 | 5 | 9 | 4 | 5.1 |
| C11 Open protocol + conformance suite only | 7 | 4 | 8 | 8 | 5 | 6 | 9 | 6.7 |
| C12 Offline mesh/LoRa network | 5 | 5 | 5 | 5 | 7 | 2 | 4 | 4.9 |
| C13 Live bed-availability marketplace | 7 | 4 | 5 | 5 | 6 | 6 | 7 | 5.7 |

**Why the rejects lose:** blockchain adds latency and cost over a hash chain with no benefit here; AI routing is unsafe given VLM/ASR error rates and automation bias (R08); WhatsApp is excluded for health data; a digital twin is not honestly validatable in the build window (R10); live-bed marketplaces rest on self-reported data and do not create capacity (R10, v7 §8); voice-only, dashboard-only, FHIR-only and standard-only each solve one slice.

### 1.4 Fusion (why C3 wins)

The strongest concepts are complementary, not competing: **C11** (an open protocol with a conformance suite) is the *big goal*; **C6** (voice) is the *reach*; **C7** (command centre) is a *reader of the same log*; **C8** (FHIR) is the *export*. v8 is one protocol with a reference platform, a proof layer, a reach layer and read-only learning views. The coherence rule from v7 stays: every feature is (a) a state/event in the contract, (b) an interface producing or consuming events, or (c) a reader of the log. Anything else is out of scope.

### 1.5 Red-team and scenario stress test
The pre-mortem produced the loophole ledger (§15). Twenty-eight real-world scenarios are specified in §4.8 and each maps to a conformance vector.

---

## 2. The Locked Solution in One Page

**Name:** ReferralHandshake — the *Verifiable Referral Contract*, delivered as the open **Referral Handshake Protocol (RHP-1)** plus a reference platform.

**Problem (locked):** An emergency referral is a message that nobody owns. We make it a signed-for handover: offered, answered, negotiated, owned by exactly one destination, escalated automatically on silence, never blocking care, reaching every kind of receiver, surviving failures, and closed with an outcome — with guarantees *shown holding under attack*, not promised.

**Big goal:** "No emergency referral without a receipt." Start with obstetric referral through Karnataka-style tiers (PHC → CHC/FRU → district hospital → medical college). Grow RHP-1 into the common reliability layer other systems can adopt: 108/ERSS dispatch, state referral systems, hospital information systems, via FHIR-shaped export. Extend the same contract to neonatal, trauma, cardiac and stroke. Success is measured by process metrics (acknowledgement time, unanswered rate, unannounced-arrival rate, arrival-to-handover time, completeness, secondary transfers), never claimed lives saved.

**Three-part USP (all three or none):**
1. **Contract semantics:** offer, acknowledge, accept/counter/decline-with-reason, single-owner lease with fencing epoch, resource commitments, two-level escalation, mandatory outcome.
2. **Reach without dependency:** smartphone, web desk, automated voice call to a feature phone with keypad + PIN, SMS alert, paper code, dispatcher proxy, offline outbox.
3. **Provability:** frozen specification, bounded model checking, conformance vectors, randomised concurrency tests, an independent runtime monitor, tamper-evident log with outside witnesses, and a live **Guarantee Arena** where judges attack it.

**Honest limits, stated up front:** the system does not create capacity; it surfaces refusal earlier and makes ownership unambiguous. No national prevalence, no measured ambulance-minutes lost in India, and no mortality effect exist in the research [GAP]. Claims are operational only. Existing clinical and emergency communication procedures remain primary; the system never delays care.

---

## 3. Architecture Overview

```
 CHANNELS (produce/consume events)            CORE                               READERS (log only)
 ┌─────────────────────────────┐   ┌───────────────────────────────┐   ┌──────────────────────────────┐
 │ Android (EMT/clinician)     │   │ Command API (FastAPI)         │   │ Independent Runtime Monitor   │
 │ Web desks (PWA, QR join)    │──▶│  • idempotent commands        │──▶│  (own transition impl.)       │
 │ Voice IVR (feature phone)   │   │  • per-referral row lock      │   │ Tamper verifier + witnesses   │
 │ SMS alert + link            │   │  • transition table (frozen)  │   │ Command centre (map, KPIs,    │
 │ Paper code entry            │   │ PostgreSQL primary            │   │  network graph, replay)       │
 │ Dispatcher console (proxy)  │   │  • state + hash-chained events│   │ FHIR/XES exporters            │
 └─────────────────────────────┘   │  • durable deadlines, outbox  │   └──────────────────────────────┘
                                   │ Timer poller · Outbox relay   │
                                   └───────────────────────────────┘
```

**Stack (decided):**

| Layer | Choice | Why |
|---|---|---|
| API | Python 3.12, FastAPI, psycopg3 | Team skill, AI-assistable |
| Database | **PostgreSQL 16, single primary** (docker-compose for demo; managed Multi-AZ for pilot) | Per-referral `SELECT … FOR UPDATE`, `SKIP LOCKED` timers, durable commit; row locks only work on the primary (R04) |
| Web desks | React PWA, SSE for push | Judges join by QR; no install |
| Ambulance/clinician app | Native Android (Kotlin), Room outbox, foreground location service | Deterministic background behaviour (R05, R07) |
| Reach | Telephony provider webhooks (Exotel/Twilio trial, whitelisted numbers) | Voice + DTMF; see §6 |
| Maps/ETA | Mapbox Directions/Matrix (server-side, cached) + map tiles via Mapbox or self-hosted PMTiles | Avoid OSM tile-server policy (R07); PMTiles option [verify] |
| Edge | Cloudflare (WAF, Turnstile, tunnel) + local-LAN fallback | §10.2, §13 |
| Proof | TLA+/TLC spec, Python explicit-state checker, Hypothesis, independent monitor | §7 |

**Deliberate non-choices:** no blockchain, no Kafka/Debezium (the same-transaction outbox with a polling relay is enough; Debezium + `pg_logical_emit_message` is the scale path, R15), no CRDT for state (CRDT only for additive telemetry), no event-sourcing-only store (R04: CRUD + outbox; the log is an audit/verification stream, §5.2), no Kubernetes for the pilot (R13's EKS plan is over-engineered for one district), no WebSockets, no WhatsApp, no on-device LLM.

---

## 4. The Handshake Contract (RHP-1)

### 4.1 Two tracks so care is never blocked

**Handshake track** (who owns the patient):
`CREATED → OFFERED(f, step) → ACKNOWLEDGED → { ACCEPTED | COUNTERED | DECLINED }`
`COUNTERED → ACCEPTED` only when the referrer confirms. Failure paths: `TIMED_OUT → next step`, `ARRIVAL_REJECTED → next target`, `ESCALATED_TO_DISPATCHER` (human assigns or cancels; the system never invents a destination), `CANCELLED(reason)`. Terminal: `CLOSED(outcome | unknown)`.

**Transport track** (where the patient is):
`REQUESTED → DISPATCHED → EN_ROUTE(f) → ARRIVED(f) → HANDED_OVER`
Runs in parallel and is **never gated** by the handshake track. An ambulance may leave for the clinician's primary destination while the handshake proceeds. If ownership moves, crew and dispatcher get a *redirect advisory*; the crew or dispatcher decides. The system never reroutes a moving ambulance on its own.

### 4.2 Acknowledge versus respond
- **ACK** = a human on a rostered, registered channel has seen the offer (authenticated card open, or voice keypress). Delivery of an SMS or push is not an ACK.
- **Response** = ACCEPT / COUNTER / DECLINE. Each is a valid, timestamped answer. A documented decline for a missing resource is not a failure. **Silence is the only unrecorded outcome, and silence triggers escalation.**
- Two deadlines per step: `ack_deadline` (short) and `decision_deadline` (longer).

### 4.3 Response vocabulary
- **ACCEPT:** every required resource confirmed one by one (OT, anaesthetist, blood, NICU/paediatrician as the card requires). Grants the lease; `lease_epoch++`.
- **COUNTER:** structured conditions ("without NICU", "anaesthetist in 20 min", "blood on request"). Referrer confirms or rejects; max 2 rounds, then escalate. On voice: DTMF menu of the same conditions.
- **DECLINE:** structured reason (which resource is missing) and optional redirect suggestion; the suggestion is only *shown* to the dispatcher/referrer, never auto-followed.
- **ARRIVAL_REJECTED:** receiver accepted, then cannot take the patient on arrival. Records the broken commitment, revokes the lease, escalates.
- **Arrival confirmation:** geofence (suggest radius 200 m, plus dwell and speed) raises "ARRIVED?"; the EMT or receiving desk confirms. Proxy entries are marked as proxy.

### 4.4 Ownership and the lease
- Row `version` (optimistic check on every command) and `lease_epoch` (monotonic, increments on every ownership change) are **separate**.
- Every state-changing command carries `expected_version`. A stale writer gets `412` and nothing is applied; a lost race gets `409` with a reason code (`LEASE_HELD`, `LATE_ACCEPT_REJECTED`).
- **Default mode: sequential offers.** Parallel offers (max 2 facilities) are a dispatcher-set mode for critical cases and for the demo race. Parallel crowding is a documented tertiary-overload risk (R01), so it is not the default.
- **Late-accept window:** when step *k* times out and step *k+1* is offered, step *k*'s offer stays **soft-open** until *k+1* ACKs. If *k* accepts first, *k+1* is cancelled with a notice and no harm; if *k+1* has already ACKed, *k*'s late accept is refused with `LATE_ACCEPT_REJECTED` and shown. Outcome is decided by lock order, so it is deterministic.
- After ACCEPT, the lease does not silently expire. It ends only by explicit event: `ARRIVAL_REJECTED`, owner revoke ("cannot take now", recorded as a broken commitment), dispatcher override (with reason, logged), `HANDED_OVER`, or `CANCELLED`.

### 4.5 Escalation ladder
1. **Inside the receiving facility:** duty nurse → casualty medical officer → on-call consultant/administrator, each with its own timers.
2. **Next facility** in the *administratively approved catchment chain* (district-level map; clinician may reorder or skip; the system never invents a destination). Facilities that declined, timed out or rejected on arrival are excluded for this referral (no A→B→A loops).
3. **Dispatcher** (`ESCALATED_TO_DISPATCHER`) when the chain is exhausted. A human assigns by phone (recorded as proxy) or cancels with a reason.
4. **Load guard:** a facility may be configured with a cap on concurrently open offers; when full it returns a structured `AT_CAPACITY` decline. Escalation does not funnel every case to the top tier (R01 bypass finding).
5. **Timers are configuration, owned by clinical leadership**, inside hard-coded guard limits (ack 30 s–5 min; decision 1–15 min; counter rounds ≤2). Demo values are short (ack 10 s, decision 20 s). Suggested pilot starting hypotheses: ack ≈ 2 min, decision ≈ 5 min per step, based on in-hospital escalation norms of 3–5 min (R09). The project claims no clinical threshold.

### 4.6 Closure
`CLOSED` requires an outcome note from the receiver or an explicit "unknown" (a digital counter-referral). Unclosed referrals surface to the dispatcher/district view; they are never silently dropped.

### 4.7 Invariants (what the monitor and the checker enforce)

| ID | Invariant |
|---|---|
| I1 | **No silent referral:** every non-terminal handshake state has a pending deadline and a responsible actor; an overdue deadline is acted on within tolerance τ |
| I2 | **One patient, one owner:** at most one active lease; `lease_epoch` strictly increasing |
| I3 | **Never block care:** transport events are accepted in every non-terminal state |
| I4 | **Exactly once:** each client `event_id` appears once; per-referral `seq` has no gaps; retries are replays |
| I5 | **Integrity:** per-referral hash chain verifies; checkpoint signatures verify; `CLOSED` has outcome or `unknown` |
| I6 | **Authority:** every ACCEPT/COUNTER/DECLINE comes from a rostered role on a registered device/number with a verified PIN, or is flagged proxy |
| I7 | **No invented destination:** every escalation target is in the approved chain or is the dispatcher |
| I8 | **Stale writers fenced:** a command with a stale version/epoch is never applied and is logged |
| I9 | **No loops:** a facility appears at most once as an active target per referral |

### 4.8 Scenarios the contract must handle (each is a conformance vector)

| # | Scenario | Behaviour |
|---|---|---|
| 1 | Receiver has no smartphone | Voice call with PIN; dispatcher proxy if unanswered |
| 2 | Receiver cannot take but knows who can | DECLINE with redirect suggestion |
| 3 | Receiver can take partly | COUNTER; referrer confirms or escalates |
| 4 | Duty nurse busy | In-facility ladder to casualty MO, then onward |
| 5 | Two facilities accept at once (parallel mode) | One lease; the other sees why |
| 6 | Late accept after escalation | Late-accept window rule (§4.4) |
| 7 | Accept, then cannot take on arrival | `ARRIVAL_REJECTED`, broken commitment recorded, escalate |
| 8 | All approved facilities fail | `ESCALATED_TO_DISPATCHER` |
| 9 | Ambulance in dead zone | Observations queue; "last confirmed" shown; set-union merge on reconnect |
| 10 | Server or internet down | Phone and paper procedures continue; paper code; outbox reconciles after recovery |
| 11 | Wrong person "accepts" | Roster/role/PIN reject and log |
| 12 | Crew cannot use the app | Dispatcher or EMT enters status as proxy |
| 13 | Slip arrives with no digital record | Desk enters paper code and links or creates a paper-first record |
| 14 | iPhone with restricted background | Foreground flush; limitation stated; no background claim |
| 15 | AI draft wrong | Structured entry primary; critical fields verified; system works with AI off |
| 16 | Patient delivers or stabilises before departure | `CANCELLED(reason)`; offers withdrawn |
| 17 | Patient refuses transfer | `CANCELLED(reason)`, logged |
| 18 | Ambulance breaks down | Dispatcher reassigns transport; handshake unaffected |
| 19 | Receiver roster stale (phone changed) | Offer fails delivery → next roster channel → escalate |
| 20 | Counter loop | Max 2 rounds, then escalate |
| 21 | Duplicate referral for same patient | Paper-code/identifier match prompts link; no auto-merge |
| 22 | Client clock wrong | Server time authoritative; client time recorded, skew flagged |
| 23 | SIM theft / PIN guess | Lockout, alert, role suspension |
| 24 | Admin override by dispatcher | Requires reason, logged, flagged in monitor |
| 25 | Receiver accepts but no bed (gaming) | Separate `ARRIVED→HANDED_OVER` metric; arrival-without-handover flagged |
| 26 | Tertiary overload | `AT_CAPACITY` decline; load guard; chain skips |
| 27 | Retry storm from flaky network | Idempotent replay; rate limit |
| 28 | Referral never closed | Surfaces to dispatcher/district view |

---

## 5. Data, Consistency, Timers

### 5.1 Core tables (sketch)
```
referral(id, version, hs_state, tr_state, lease_facility, lease_epoch, ladder_cursor, need_class, mode, created_at, closed_at, outcome)
event(referral_id, seq, event_id UNIQUE, type, actor{role,facility,channel,proxy_for}, epoch,
      payload_hash, client_ts, server_ts, prev_hash, hash)          -- append-only, per-referral chain
clinical_payload(referral_id, ciphertext, dek_id, schema_ver)       -- envelope-encrypted ISBAR+Dakshata
deadline(id, referral_id, kind, step, epoch, due_at, status)
outbox(id, referral_id, event_seq, channel, status)
roster(facility, role, phone, device_ids, pin_hash, valid_from, valid_to)
facility(id, tier, geo, capabilities[], attested_at, attested_by)
catchment_chain(origin_facility, need_class, ordered_targets[])     -- district-admin approved
checkpoint(id, taken_at, root_hash, signature)
```
The application role has no `UPDATE`/`DELETE` on `event`; triggers reject both. Superusers can still bypass, which is exactly why the hash chain and outside witnesses exist.

### 5.2 One transaction per command
`BEGIN; SELECT referral FOR UPDATE; check version/epoch/authority; apply the frozen transition table; INSERT event(s) with next hash; UPDATE referral; INSERT deadline(s) and outbox rows; COMMIT.`
- Locking is **per referral**, so unrelated referrals do not serialise (an improvement on a global single-writer file).
- State lives in `referral`; the event log is written in the same transaction. The monitor independently re-derives state from the log and compares it with `referral` (a differential check; R04's "no event-sourcing" advice is respected because the log is not the only store).
- `synchronous_commit=on` for the contract database. Pilot: Multi-AZ with a synchronous standby. Read-heavy views use replicas; **locks never run on replicas** (R04).
- **Idempotency:** client-generated UUIDv7 `event_id` with a unique constraint, plus the HTTP `Idempotency-Key` header (IETF draft) and a payload fingerprint. A reused key with a different payload is rejected; a concurrent duplicate gets a conflict response.
- **Observations** (vitals, notes, GPS) are append-only events with unique IDs; offline merge is set union, corrections are new events. This resolves the v7 "overwrite" inconsistency without a CRDT library. **An offline accept is only a request**, displayed "pending, not confirmed".

### 5.3 Durable timers
Timers are rows, not memory. A stateless poller claims due rows with `FOR UPDATE SKIP LOCKED` and applies a `TIMEOUT` command that carries the expected step/version, so a racing accept and a timeout resolve by lock order. Poll interval 1 s in the demo. The server clock is authoritative; client clocks are never used for deadlines. Pilot: NTP traceable to NIC/NPL (CERT-In, [V\*]).

### 5.4 Outbox
The relay reads `outbox` rows (`SKIP LOCKED`), delivers to SSE hub, push, voice, SMS adapters, and marks delivery. At-least-once delivery plus idempotent consumers gives exactly-once *effects* (R04).

---

## 6. Reach Layer

All channels are adapters that **produce or consume events**; none holds business logic.

### 6.1 Channel matrix

| Party | Primary | Fallbacks |
|---|---|---|
| Referring clinician | Web desk / Android card | Dispatcher proxy created from a phone call |
| Receiving duty role | Web desk | **Voice call with keypad + PIN**, SMS alert + link, paper code, dispatcher phone-assisted proxy |
| Ambulance crew | Android app (foreground location service) | EMT/dispatcher proxy entries |
| Dispatcher | Console | Phone |
| District officer | Command centre | Weekly export |

### 6.2 Mechanics
- **Voice IVR:** pre-registered duty numbers; **short, de-identified** prompt ("Emergency obstetric referral from \<facility\>, reason code, ETA. Press 1 accept, 2 conditions, 3 decline, 9 repeat, then your PIN"). Fixed safety phrases are **pre-recorded by native speakers** (Kannada, Hindi, English) rather than synthesised; synthesis only for facility names. No patient name is ever spoken.
- **SMS:** static alert + link to a pre-registered, whitelisted domain pattern. **No clinical text over SMS** (DLT variable limits, silent drops [V\*]). Prototype uses provider sandbox with verified numbers; a student team cannot register as a telecom principal entity and the project does not circumvent telecom controls. WhatsApp is excluded for health data.
- **Paper code:** each printed slip carries a short checksummed code (Crockford base32) and a QR. It contains no clinical data. A desk with no digital record types the code to link or create a paper-first record. **The Handshake card *is* the slip** (printable), so clinicians enter once and nobody dual-enters (R14).
- **Android:** foreground service of type `location` with `ACCESS_FINE_LOCATION` (+ `ACCESS_BACKGROUND_LOCATION` where the app starts from background); Room outbox with WorkManager; FCM **zero-payload** wake ping then authenticated fetch (no PHI through third-party push); expect a charging cable (continuous GPS drains 15–25%/h [V\*]). OEM battery-savers (MIUI etc.) can kill services [GAP]: onboarding checklist + heartbeat shown as "last confirmed".
- **Web desks:** SSE over HTTP/2 with `Last-Event-ID` resume. SSE is chosen for server-push simplicity and proxy compatibility, not for radio-power claims.
- **iOS:** foreground flush only; no background guarantee claimed.
- **Language/equity:** Kannada and Hindi voice; works on a feature phone, weak network, and facilities with no IT.

---

## 7. Proof Layer

**Principle:** the proof is a *demonstration of trust under attack*. Each mechanism states exactly what it proves and what it does not.

### 7.1 Frozen specification (L0)
- A small TLA+ spec of the **control plane** (handshake track, ladder, lease, late-accept, transport independence) checked with TLC at small bounds (e.g., 3 facilities, 2 ladder steps, 2 counter rounds, 2 epochs). Apalache is an optional second checker.
- The transition table is **data** (`transitions.yaml`) used by both the server and a Python explicit-state explorer, so the explorer checks the *production transition function*. Fallback if TLA+ stalls: the Python explorer alone.
- **Spec freeze:** spec, conformance vectors and monitor's transition code are owned by humans (CODEOWNERS), hash-pinned in CI. **AI agents may not edit them to make a build pass** (R11 reward-hacking finding). Changes need a human-signed, versioned decision.
- **What it proves:** no invariant violation for the stated configurations, for the modelled control plane (bounded model checking; it is **not** a proof for all sizes, and **not** a proof of the code).

### 7.2 Conformance and randomised tests
- **Model-based conformance:** enumerate behaviours from the checker up to depth *d*, export as vectors, replay against the API; outcomes must match.
- **Hypothesis stateful tests** (`RuleBasedStateMachine`, `@precondition`, `@invariant`) against the real endpoints, with shrinking to a minimal failing sequence.
- **Concurrency stress:** N concurrent accepts (N ≥ 200) on one referral with retries and reconnects → exactly one lease, zero duplicate events.
- **Fault injection:** Toxiproxy (latency, `reset_peer`, `slicer`, bandwidth) between API and DB, and between phone and API; container kill/restart; clock-skew injection.
- **What it proves:** absence of failures in generated and enumerated behaviours. It does not prove absence of all bugs; randomised testing is evidence, not proof.

### 7.3 Independent runtime monitor
A separate process with a **read-only DB role** and its **own implementation** of the transition function (written by the other teammate). It folds each referral's events by `seq`, compares the derived state with `referral`, and evaluates I1–I9 continuously. Because the server assigns per-referral `seq`, out-of-order arrival is a non-issue, so a JVM stream language is unnecessary; TeSSLa/RTLola remain an optional stretch. Outputs: invariant counters, violation count, p50/p95 event latency, deadline-lateness, per-referral replay.

### 7.4 Tamper evidence with witnesses
- Per-referral chain: `hash = SHA-256(prev_hash ‖ JCS-canonical event)` (RFC 8785 canonical JSON).
- Every 5 s a **signed checkpoint** (Ed25519) over the sorted set of `(referral_id, head_seq, head_hash)` at a snapshot.
- Checkpoints are broadcast to **independent witnesses**: the big screen, judges' phones (QR page), an off-box log. A single operator cannot show different histories to different witnesses without detection (split-view defence, Wave 2).
- **Verifier** recomputes chains up to each checkpointed head and names the exact broken link; truncation is caught because the checkpointed `head_seq` is missing.
- **Limits stated:** tamper-*evident*, not immutable. Legal admissibility under BSA s.63 needs the Part A/Part B certificates (custodian + expert) with the hash value; we generate the hash-bearing export but **do not claim certification** [V\*].

### 7.5 Broken-build switch
`BROKEN_BUILD=1` (demo environment only, visibly labelled) removes the lease check. Two judges both win; the monitor turns red with `DOUBLE_LEASE_VIOLATION` within seconds. Switch back; green. This proves the monitor can catch bugs, not only that it stays green.

---

## 8. Clinical Payload and AI

- **Payload:** ISBAR (Identify, Situation, Background, Assessment, Recommendation) with the Dakshata pre-referral intervention fields. Structured entry is primary; free text is secondary. A small curated code subset (not full SNOMED/LOINC) keeps it light; export is FHIR-shaped using `ServiceRequest` + `Task`, validated against official value sets. Claim "ABDM-sandbox aligned" only if sandbox calls are made; never "ABDM compliant".
- **Pre-referral drug fields (fixes D1):** `time_given`, `dose`, and a mandatory choice `given | none given | unknown`. The card can be sent with `unknown`; the receiver sees a red "pre-referral dose unknown, verify before dosing" banner. Never blocks dispatch. Rationale: the aim is preventing double-dosing (R08), not delaying the ambulance.
- **AI intake accelerator (flagged, off the critical path):** photo/dictation → *unverified draft*. Draft is hidden until the clinician commits at least one anchor value (**think-first**). No confidence scores and no explanations are shown (explanations raised commission errors 10% → 21% in one study; LLM confidence is poorly calibrated, R08). Critical fields require re-entry. A fast-approve speed bump applies only to AI drafts and never to manual entry or sending. System works fully with AI off.
- **Privacy for AI:** prototype uses **synthetic data only**. Any later cloud VLM use requires masking *and* a zero-retention agreement; on-device masking of name/ABHA is not sufficient on its own (slips contain other identifiers). VLM handwriting accuracy 85–95% and Indic ASR WER above 20 on naturalistic dialects (R08) mean AI cannot be authoritative.
- **Safety gates for the accelerator (internal usability test, not a clinical study):** 20 synthetic slips, 30% seeded fatal errors, A/B standard vs forcing-function UI; targets: critical-error rubber-stamp ≤5%, silent-omission ≤1%.

---

## 9. Facility Capability, Routing, Maps

- **Registry:** curated Karnataka directory for the pilot district(s), seeded from official lists [verify coverage; OSM has bed tags on 0.08% and emergency tags on 1.03% of Indian facilities, R07]. Each facility carries CEmONC-style capability tags (OT, blood storage, anaesthetist on roster, paediatrician/NICU) from IPHS 2022 and EmONC signal functions.
- **Attestations:** staff update capabilities with timestamps; the UI shows **age** and expires stale ones. Self-reported; **never presented as live beds**.
- **Matching:** the card's `need_class` filters the administratively approved chain; the chain is pre-filled so the clinician confirms in one tap, and the system never invents a destination.
- **ETAs:** Mapbox Directions/Matrix server-side for the active referral's top candidates, cached; Mapbox free tier covers the prototype (Directions 100,000 requests/month; Matrix limits 60/min, 30/min for driving-traffic [V]). Rural-road traffic quality in Karnataka is unverified [GAP]. Navigation SDK is optional and only changes billing if active guidance is used.
- **Location:** budget-phone GPS in vehicles is 7–13 m typical, up to ~50 m median in bad cases; ionospheric scintillation adds 4–13 m [V\*/V]. Nothing in the contract depends on metre-level accuracy; geofence is a hint (§4.3).
- **Tiles:** do not bulk-download from OSM's tile servers (policy); use a commercial SDK or self-hosted PMTiles [verify].

---

## 10. Security, Privacy, Legal

### 10.1 Identity and authority
Roster-based roles, registered devices/numbers, **server-verified PIN** (salted hash, lockout after repeated failures, alert on lockout), short-lived tokens, per-user device-bound signing key where supported. On a shared ward tablet, accepting always requires PIN entry (the NIST "user present vs user verified" gap). Every administrative action is audited. Object-level authorisation on every request (BOLA), schema-strict inputs with server-side state ownership (no mass-assignment of `state`), function-level role checks, rate limits, encrypted transport and storage, minimal data in notifications.

### 10.2 Edge and QR defence
Cloudflare WAF in front; **Turnstile challenge before any join token is minted**; per-IP mint rate with generous NAT allowance; **admission cap** on simultaneous judge desks; per-token rate limit after minting; read-only judge roles; synthetic data only. **LAN fallback:** local server on a hotspot with a QR to the LAN address if venue internet fails.

### 10.3 Data minimisation and DPDP
- The service holds a **handover record**, not the medical record. Clinical payload is **envelope-encrypted with a per-referral data key**; shared with referring and receiving facilities for a configurable period; deleting the key crypto-shreds it. A **pseudonymous, clinical-content-free event-metadata log** is retained longer for audit.
- DPDP Rules notified 13 Nov 2025; core obligations computed to apply from 13 May 2027 [V\*]. Section 7(f) covers emergency processing without consent (use narrowly, log the emergency basis, regularise after stabilisation); Section 7(i) covers employment processing including staff usage telemetry, but **prior written notice to staff is still required**, collection must be minimal, and telemetry must be siloed from HR performance records and erased after the evaluation purpose ends.
- Retention interplay (DPDP 8(7) erasure vs record-keeping duties; 3-year NMC teleconsultation retention; 180-day CERT-In logs) is a **policy parameter needing legal review** [GAP]. Whether the 3-year retention applies to a referral handover record is unverified.
- Penalty exposure (ceilings, not tariffs): up to ₹250 crore for failure to take reasonable security safeguards; ₹200 crore for failure to notify a breach [V\*].
- Hosting for any real data: MeitY-empanelled provider in India; CERT-In 6-hour incident reporting and 180-day in-India logs; ABDM production needs a WASA "Safe to Host" audit by an STQC/CERT-In-empanelled agency, per platform [V\*]. Not required for a synthetic-data prototype.
- **Voice** reading a short de-identified summary to pre-registered numbers: legality unsettled [GAP]; prototype uses provider sandbox and own verified numbers.
- **ABDM:** no longitudinal record fetch (consent cannot come from an unconscious patient; emergency override unverified [GAP]). The summary is clinician-authored at the point of care.

### 10.4 Developer-side safety (AI-assisted build)
Agents run sandboxed; MCP servers are treated as untrusted inputs; no secrets in agent-readable files; CODEOWNERS on spec/vectors/monitor; branch protection with required CI. LLMs write plausible but wrong concurrency code (CONCUR benchmark, R12), so no layer counts as done until conformance and monitor are green and a *different* teammate can explain the module.

---

## 11. Real-World Operating Model

- **Who holds the receiving device:** a **duty role** (casualty medical officer or duty nurse) registered on a facility roster, not a named person. Offers go to the role; the ladder covers shortages.
- **Why a busy receiver responds (hypotheses to test, not facts):** every answer is valid and timestamped; a decline for a missing resource is not penalised; advance notice reduces unannounced arrivals; a redirect suggestion lets them help without taking the patient.
- **Goodhart protection (R09):** receiving staff see a priority list, not countdown clocks (displayed targets distorted triage in the MTS study). District views show reliability as **capacity signals**, aggregated, never individual blame. Handover is measured separately from acceptance, so "accept to hit the KPI, delay the bed" is visible. Timer limits sit inside hard guard bounds; facilities cannot extend them indefinitely.
- **Alarm fatigue (R09):** targeted notifications, no ward-wide broadcast, multimodal, escalate on silence.
- **Honest limit:** if every facility is full, the system surfaces the refusal earlier (before the ambulance reaches the door) and gives administrators bottleneck data. It does not create beds.
- **No receiver at all:** voice to a pre-registered number → dispatcher phone-assisted proxy → EMT device records arrival and handover.

---

## 12. Impact, Validation and Path to Real Use

**Beneficiaries:** patients in obstetric (first), then neonatal, trauma, cardiac and stroke referrals; PHC/CHC clinicians; 108 crews; receiving triage teams; district officers who cannot see where referrals stall. In Karnataka's 108 service, a CAG audit found 44% of dispatched calls non-emergencies and 50% of trauma responses missing the golden hour (R09, [V\*]); a referral layer that removes blind drops helps the same crews.

**Stages (each gated):**
1. **Synthetic demo** (hackathon).
2. **Expert conversations (start now, in parallel with build):** ≥3 interviews across a clinician, a 108 crew member/dispatcher, a district coordinator. Use the R01 manual-conflict guide (capacity overload, timeout thresholds, concurrent arrival) and the R09 CMO guide. Record responses; adjust timers, vocabulary and defaults.
3. **Optional ABDM sandbox** (Stages 1–3 only → "sandbox aligned").
4. **Ethics-approved shadow-mode pilot in one district.** ICMR 2017 routing: a pilot that tracks staff behaviour is not exempt; expedited review is the realistic route for minimal risk; **full committee review** applies if pregnant women's identifiable data are involved, if deception is used, or if the system begins influencing decisions (R14). Human-in-the-loop and override mechanisms are mandatory for any AI feature (ICMR 2023). **No double entry:** the Handshake card replaces the slip; phone procedures continue unchanged. Pilot sample sizes: for a medium effect on log-normal time metrics ≈15 per arm; for binary process metrics ≈60–100 observations (R14).
5. **Integration only through authorised channels** (108/ERSS, state systems, HIS), via FHIR-shaped export and a conformance suite others can run.
6. **RHP-1 as an open specification** with the reference server and conformance suite published for other states and pathways.

**Pilot metrics (pre-registered, process only):** time to acknowledgement; unanswered rate; unannounced-arrival rate; referral completeness (with/without accelerator); arrival-to-handover time (APOT-style; UK 15 min and Ireland 95% <20 min are reference points, not Indian baselines [V]); secondary-transfer rate; ambulance wait at origin. **Hypotheses, not claims:** the contract reduces silent referrals and unannounced arrivals; whether it reduces ping-pong or deaths is an open question for the pilot.

**Indicative six-month pilot cloud cost** (from R13's AWS ap-south-1 figures; verify with the AWS calculator): Multi-AZ managed Postgres db.t4g.medium ≈ $95/month + 100 GB gp3 ×2 ≈ $23/month + ALB ≈ $22/month + one small app VM; roughly **$1,000–$1,500 for six months** with contingency, without Kubernetes.

---

## 13. Build Plan, Cut Lines, Demo Operations

### 13.1 Layers (each behind a feature flag; each has a gate)

| Layer | Content | Gate |
|---|---|---|
| L0 | Frozen spec, `transitions.yaml`, checker, conformance vectors | Suite green in CI; spec hash pinned |
| L1 | Contract core: Postgres, commands, events, hash chain, durable timers, ladder, lease | L0 + 200-way concurrency test |
| L2 | Web desks, dispatcher console, Android app, offline outbox, proxy | Offline and duplicate tests |
| L3 | **Guarantee Arena:** monitor, chaos switch, verifier, broken-build | Monitor detects injected faults |
| L4 | **Reach:** voice IVR, SMS alert (stub or sandbox), paper code | Channel-ack tests |
| L5 | Command centre: live map, KPIs, network graph, replay scrubber | Metrics match log recomputation |
| L6 | AI intake with forcing functions | Seeded-error gates |
| L7 | FHIR-shaped export, XES export | Validator passes |
| L8 | Counterfactual replay under stated assumptions (stretch) | Labelled "simulated"; assumptions visible |
| L9 | Field validation | Runs from day 1 in parallel |

**Cut lines:** **Must** = L0–L3 + voice from L4 · **Should** = Android app, paper code, L5 · **Could** = L6, L7 · **Stretch** = L8, TeSSLa. If time is short, cut from the bottom; the MVP (one obstetric referral, four roles, handshake → lease → escalation → transport → closure, with log, outbox, chaos switch and monitor) must always run alone.

**Scaling to time available (event date to be confirmed):** ~2 weeks → L0–L3 with web voice stub and recorded fallback; ~4 weeks → add voice live, Android, paper code, L5; 8+ weeks → add L6, L7, interviews and pilot paperwork.

**Roles:** T1 owns protocol, backend, proof; T2 owns clients, reach, demo operations. Each reviews the other's modules and must be able to explain every module to judges. The monitor is written by the teammate who did not write the server.

### 13.2 Demo operations (R13)
- Four-hour code freeze before presenting; hardcoded demo path for any AI call; cached responses.
- **Hybrid demo:** every scene has a pre-recorded fallback clip; practise the switch.
- **Local-first stack** on a laptop with an independent hotspot; Cloudflare tunnel for judges' QR; LAN-QR fallback.
- Pre-flight: telephony credits and whitelisted numbers verified, feature phone charged, chaos switch armed, broken-build branch tested, witnesses page up.

---

## 14. Guarantee Arena: Pitch and 7-Minute Script

**Roles:** T1 pitches; T2 drives devices. Judges form their opinion in ~30 s and need the "aha" inside 60 s (R13), so the first minute is an enacted problem, not slides.

| Time | Scene | What happens | Fallback |
|---|---|---|---|
| 0:00–1:00 | **The phone rings** | T1: one-line composite persona (a PHC medical officer; label it composite). T2 creates a referral on Android in ~20 s (one-tap chain). A judge holds a **feature phone** that rings: voice prompt, press 1, PIN. Screen shows ACK → lease → ambulance dot moving. One slide: 53% no phone contact; 90.6% arrived unannounced (with study names) | Recorded call clip |
| 1:00–2:15 | **The race** | Judges scan QR, become competing hospitals (parallel mode), press Accept together. Exactly one lease; others see why; monitor green | LAN QR |
| 2:15–3:15 | **The silence** | One offer ignored; in-facility ladder, then next facility, then dispatcher fire on schedule | Replay |
| 3:15–4:15 | **The failure** | Toxiproxy partition, then kill the API container; restart; nothing lost or duplicated; **measured** recovery time displayed (never a pre-claimed number) | Clip |
| 4:15–5:00 | **The forgery** | Edit one row in psql; verifier names the exact broken link; checkpoints already on judges' phones | Clip |
| 5:00–5:45 | **The broken build** | Flip `BROKEN_BUILD`; two winners; monitor red within seconds; flip back; green | Clip |
| 5:45–6:30 | **Offline + AI off** | Ambulance phone offline: "pending, not confirmed"; reconnect: authoritative state wins and a visible alert explains. AI/app/network off in turn: referral still completes via voice and paper code. Think-first draft shown briefly | Cut first if short |
| 6:30–7:00 | **Close** | Outcome returns to the referring clinic; in-app process map from the real log; vision: "no emergency referral without a receipt"; ask for pilot partners; one slide of what we do not claim | — |

**Hard questions, prepared answers (short):**
- *Why not blockchain?* A hash chain with outside witnesses gives tamper evidence at far lower cost; consensus is not needed with a single trusted arbiter per district.
- *What if the receiver never answers?* The ladder escalates and a human takes over; the ambulance is never held.
- *Does it create capacity?* No. It surfaces refusal earlier and gives administrators evidence.
- *Is it clinically validated?* No. Process claims only; pilot under ethics review is the next step.
- *Is TLA+ proof of your code?* It checks the design at bounded size; the code is checked by conformance vectors, randomised tests and a live independent monitor.
- *Voice legality?* Unsettled; prototype uses sandbox numbers and synthetic de-identified prompts; legal review precedes real use.
- *iPhone?* Foreground only; Android for ambulances.
- *Who holds the receiving device?* A rostered duty role, not a person.

---

## 15. Claims Register

| May claim | Must not claim |
|---|---|
| Referral communication and documentation gaps documented in specific urban Indian studies (Maharashtra 2016–19; Safdarjung 2018–23) | National prevalence; deaths prevented; lives saved |
| A specified, bounded-model-checked, conformance-tested protocol with single-owner leases and timed escalation | That no competitor has it ("not found in public documentation of the systems audited") |
| Guarantees held under our stated test conditions, with measured numbers shown live | Production readiness; "mathematically guaranteed" for the whole system; "zero silent drops" |
| FHIR-shaped export; "sandbox aligned" only if sandbox calls are made | "ABDM compliant"; live integration with 108, hospitals or ABDM |
| Simulated ambulance-minute savings under stated assumptions (if L8 is built) | Measured time saved; "ping-pong eliminated" |
| Tamper-evident log with outside witnesses | Immutable; legally conclusive; "BSA-certified" |
| Process improvement is a hypothesis for a pilot | That the protocol reduces lost patients or transfers as established fact |

---

## 16. Loophole Ledger (known loopholes and their closure)

| # | Loophole | Closure / bounded residual |
|---|---|---|
| 1 | Blocking care through mandatory fields | Answer-required with `none/unknown`; never blocks (D1) |
| 2 | Ambulance held until handshake completes | Independent transport track (I3) |
| 3 | Double lease | Row lock + version + epoch; late-accept rule; monitor I2 |
| 4 | Zombie write from delayed device | Stale version/epoch rejected, logged (I8) |
| 5 | Lost response then retry | Idempotency key + event_id unique (I4) |
| 6 | Timer lost on crash | Timers are rows; poller restart-safe |
| 7 | Clock skew changes deadlines | Server-authoritative time; client skew recorded |
| 8 | Silent receiver | Ack/decision deadlines; ladder; dispatcher |
| 9 | Chain exhausted | `ESCALATED_TO_DISPATCHER`; no invented destination (I7) |
| 10 | Tertiary funnelling | Sequential default; load guard; `AT_CAPACITY` |
| 11 | Referral loops | Facility excluded after decline/reject (I9) |
| 12 | Accept-then-no-bed gaming | Separate handover metric; `ARRIVAL_REJECTED`; arrival-without-handover flag |
| 13 | Shared-device spoofing | Roster + server-verified PIN + lockout |
| 14 | BOLA / mass-assignment / function-level abuse | Object-level checks, server-owned state, role checks, schema-strict |
| 15 | Log tampering by admin | Hash chain + signed checkpoints + witnesses (detect, not prevent) |
| 16 | Split-view by operator | Checkpoints held by independent witnesses |
| 17 | Bot minting QR tokens | Challenge before mint, admission cap, per-token limits, LAN fallback |
| 18 | PHI over third-party push | Zero-payload ping + authenticated fetch |
| 19 | PHI in SMS | Static alert only |
| 20 | Wrong crypto-shredding | Per-record DEK deletion |
| 21 | Erasure vs retention conflict | Retention parameterised; legal review [GAP] |
| 22 | AI hallucination reaches the record | Draft quarantine, think-first, re-entry of critical fields, AI optional |
| 23 | Automation bias via explanations/scores | None shown |
| 24 | Dashboard gaming (Goodhart) | No countdowns for receivers; aggregated capacity framing; handover metric |
| 25 | Staff telemetry unlawful | Prior notice (7(i)), minimisation, siloing, erasure |
| 26 | Double-entry burden | Card = slip; no parallel documentation |
| 27 | Overclaiming in pitch | Claims register; live-measured numbers only |
| 28 | Spec/code drift or AI "fixing" the spec | Frozen spec, CODEOWNERS, hash-pinned; model-based conformance |
| 29 | False atomicity (model hides races) | Row-lock concurrency tests + Hypothesis + monitor on the real system |
| 30 | Monitor and server share a bug | Independent implementation by the other teammate; differential check |
| 31 | Demo network failure | Local-first, hotspot, LAN-QR, recorded fallbacks, code freeze |
| 32 | GPS error mis-triggers arrival | Geofence is a hint; human confirms |
| 33 | OSM data gaps / tile policy | Curated registry; commercial SDK or self-hosted PMTiles |
| 34 | Stale capability data | Timestamps shown with age; expiry; never "live beds" |
| 35 | Roster out of date | Delivery failure → next roster channel → escalate |
| 36 | PIN theft / SIM swap | Lockout, alert, role suspension |
| 37 | Hardcoded timers unsafe | Config inside guard limits; owned by clinical leadership |
| 38 | Single DB failure in pilot | Multi-AZ synchronous standby; backups; restore drill |
| 39 | LLM concurrency bugs | Spec first, conformance, monitor, explain-it rule |
| 40 | Legal status of voice | Sandbox + own numbers now; legal review before real use [GAP] |

**Residual risks that software cannot remove (stated, not hidden):** no capacity is created; adoption depends on receivers' incentives (test in interviews and pilot); voice and retention law unsettled; clinical timer thresholds unknown; telecom registration for production SMS/voice; OEM battery policies on Android; rural traffic-data quality. No system has zero loopholes; this one has every known loophole closed or explicitly bounded.

---

## 17. Verify Before Final Submission

1. Das et al. denominator (25,253 vs 28,020) and definitions; quote percentages only. 2. National Ambulance Services Guidelines 2026 clauses from the official document. 3. Telecom sandbox terms, voice-content legality, URL whitelisting. 4. Mapbox/Google pricing and limits, Karnataka hospital coverage, tile approach (Mapbox vs PMTiles). 5. Primary text for CERT-In directions, BSA s.63, record retention, DPDP 7(f)/7(i)/8(7). 6. Android background-location approach and OEM behaviour on target devices. 7. ABDM sandbox route and FHIR value sets. 8. Hackathon rules on pre-built work and AI-assisted coding. 9. At least three conversations with a clinician, a 108 crew member or a district coordinator. 10. Measure, then quote, any latency/recovery figure shown live.

## Appendix A — Corrections to earlier documents (found during this audit)

- **v7 §6** says PostgreSQL row locks are sufficient "across replicas". R04: row locks cannot be taken on hot standbys; locks must run on the primary. v8 states this correctly.
- **R10** uses "smart contract" language for the state machine. RHP-1 is a protocol with a database arbiter, not a blockchain contract; avoid the term in the pitch.
- **R10 decision** (live dashboard instead of digital twin) is retained as the headline; v7 L8 is demoted to a labelled stretch.
- **R04 recommended SQLite for the MVP** on operational-overhead grounds. v8 chooses Postgres because per-referral row locking, `SKIP LOCKED` timers, synchronous durable commit and a clean pilot path outweigh the setup cost, and a docker-compose database is no harder for a two-person team.
- **R03's SSE battery argument** is not adopted; SSE is used for web push only.
- **R13's EKS plan** is dropped for the pilot as over-built for one district.
- **R11's recommendation** (property-based tests + monitor, no TLA+) is extended: the frozen spec is kept as a small, human-owned control-plane model because v7's USP requires provability; trace validation is not used (false atomicity and reward-hacking findings).
