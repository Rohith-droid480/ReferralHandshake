# GEMINI.md — ReferralHandshake (Protocol RHP-1) Workspace & Agent Constitution

**Project:** ReferralHandshake — Verifiable Referral Contract (Protocol RHP-1) + Reference Platform
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru; 24-hour build, 2 students, 5-minute pitch with ≥30 s live demo)
**Data Posture:** Synthetic data only (`REAL_DATA=0` enforced at boot)
**First Clinical Pathway:** Emergency obstetric referral through Karnataka-style tiers (`PHC → CHC → FRU → DH → MC`), with a generic data model extensible to `NEONATAL`, `TRAUMA`, `CARDIAC`, and `STROKE`.

---

## 1. Strict Input Precedence & Tag Discipline (Non-Negotiable)

All AI agents (Google Antigravity, Gemini Pro, Gem 1 CONDUCTOR & MASTER VALIDATION AUDITOR) operating in this repository must resolve any conflict or ambiguity using this exact hierarchy:

1. **`ReferralHandshake_LOCKED_Problem_Statement_v7.md`:** Highest authority on problem framing, evidence register, operational scope, and claims discipline.


2. **Primary Research Findings Tagged `[V]`:** Verified primary-source facts embedded in the specification set.


3. **`ReferralHandshake_v8_LOCKED_Solution.md`:** Authority on D1–D20 defect closures, 28 real-world scenarios, 40-item loophole ledger, and clinical operating model.


4. **`ReferralHandshake_FINAL_LOCKED_Architecture.md`:** Ultimate technical authority on F1–F20 closures, I1–I16 invariants, the 24-table PostgreSQL 16 DDL, the 10-step `apply_command()` pipeline, timing math, Quint specification (`rhp1.qnt`), independent Python runtime monitor, and T0–T3 feature tiers.


5. **`ReferralHandshake_3Gem_Antigravity_Workflow.md` & `AGENTS.md`:** Authority on the 1-Gem Direct Post-Build Validation Loop, lane isolation, packet formats, and verification gates.



### 1.1 Evidence & Weakness Tag Legend

Every architectural artifact, doc, slide, or UI screen must preserve these exact status tags:

* **`[V]`:** Verified from primary sources in the research corpus.


* **`[V*]`:** Verified only from a secondary or vendor source; must be confirmed from primary sources before appearing on a slide.


* **`[CONFLICT]`:** Research sources disagree (e.g., Das et al., 2023 Maharashtra denominator `25,253` vs `28,020`; DPDP Rules commencement `13 Nov 2025` vs Gazette `14 Nov 2025`; DPDP emergency clause `s.7(f)` vs `s.7(d)`); quote percentages or conservative dates only.


* **`[GAP]`:** No reliable evidence found (e.g., national prevalence, ambulance time lost in India, mortality impact of digital handshakes, voice IVR legality, NMC 3-year retention applicability to handover records); parameterise and never make a factual claim.


* **`[verify]`:** Must be verified in the pre-event hardware/sandbox checklist (§21 of the Architecture spec).


* **`CLOSED`:** Weakness eliminated by a concrete technical mechanism + named automated test.


* **`BOUNDED`:** Weakness constrained within a stated technical residual + live runtime monitor alarm.


* **`OPEN`:** Residual risk assigned to a named human owner with required closing evidence.



---

## 2. Coherence Rule & Locked Technology Stack

### 2.1 The Coherence Rule

Every file, endpoint, worker, database object, and UI element in this repository must be **exclusively** one of the following:

1. **(a) Contract State or Event:** A state, transition, deadline, or hash-chained event in the RHP-1 contract.


2. **(b) Producer/Consumer Interface:** A channel adapter (PWA desk, Android app, Exotel voice IVR, DLT SMS link, Crockford paper code, dispatcher proxy console) that produces commands or consumes outbox notifications without holding business logic.


3. **(c) Read-Only Log Projection:** A downstream reader (independent Python runtime monitor, Ed25519 Merkle witness/signer, pure-JS browser verifier, Guarantee Arena big screen, command centre map/KPIs, FHIR R4 exporter, IEEE 1849 XES exporter) that derives views strictly from the committed event log.



Anything outside `(a)`, `(b)`, or `(c)` is **strictly out of scope** and must be rejected.

### 2.2 Locked Technology Stack vs. Banned Technologies

| Architectural Layer | Locked Choice (Mandatory) | Banned Technologies (Strictly Prohibited) |
| --- | --- | --- |
| **Database** | PostgreSQL 16, single writable primary, `synchronous_commit=on`, `READ COMMITTED` isolation + explicit `SELECT ... FOR UPDATE`

 | SQLite for contract state, hot-standby lock taking, distributed consensus DBs

 |
| **Backend API & Workers** | Python 3.12, FastAPI, `psycopg3`, Pydantic v2 with `extra='forbid'`, stateless 2-phase timer poller, transactional outbox relay

 | Kafka, Debezium, Redis, RabbitMQ, Celery, Kubernetes (EKS/GKE)

 |
| **Web Clients (PWA)** | React PWA, Server-Sent Events (SSE) over HTTP/2 with `Last-Event-ID` & 15 s heartbeats, pure-JS `@noble/curves/ed25519` & `@noble/hashes/sha256`

 | WebSockets, `window.crypto.subtle` for Ed25519 (unsupported on iOS Safari / plain LAN HTTP)

 |
| **Canonical Serialization** | RFC 8785 JCS canonical JSON restricted strictly to ASCII keys and `int`, `str`, `bool` values

 | Floating-point numbers (`float` / IEEE 754) inside canonical JSON or `event.detail`

 |
| **Mobile Client** | Native Android (Kotlin, `FOREGROUND_SERVICE_TYPE_LOCATION`, `FusedLocationProviderClient`, Room outbox, empty-payload FCM wake) for `T3`; PWA GPS fallback for `T1`

 | Sending PHI inside FCM push payloads, claiming background GPS guarantees on iOS

 |
| **Reach & Telephony** | Outbound-only Exotel IVR (≤10 whitelisted numbers, AMD + press-1 gate, HTTP 200 within 5 s / 2 s internal budget), static DLT SMS (`≤30`-char variable), 9-char Crockford Base32 + mod-37 paper code

 | WhatsApp for health data, free-text clinical SMS, inbound IVR numbers, bypassing telecom controls

 |
| **Maps & Routing** | Server-side cached Mapbox Directions & Matrix (`mapbox/driving` 25 coords / 60 rpm; `driving-traffic` 10 coords / 30 rpm), Mapbox SDK or self-hosted PMTiles

 | Bulk-downloading OSM tile servers, autonomous ambulance rerouting without human confirmation

 |
| **Formal Proof & Verification** | Quint (`rhp1.qnt` by Person A), independent Python monitor (by Person B), `asyncio.Barrier(200)` race suite, Toxiproxy fault injection

 | Blockchain / smart contracts, CRDTs for authoritative state, AI agents editing specs/monitors to pass CI

 |
| **AI Intake (Optional `T3`)** | Off-critical-path draft behind Cognitive Forcing Function (`423 ANCHOR_REQUIRED` until `need_class` and `mgso4_status` committed)

 | On-device LLMs, AI auto-routing, displaying AI confidence scores or explanations

 |

---

## 3. Multi-Agent Governance: The 1-Gem Direct Post-Build Validation Loop

All 12 modules (`MODULE 1` through `MODULE 12`) are built. The repository operates under the direct **1-Gem Loop (`Gem 1 <-> Antigravity`)** focused on post-build validation, testing, bug fixing, and integration completion.

* **Lane A (Person A — Backend & Formal Spec):** Owns PostgreSQL DDL (`db/01_schema.sql`), `spec/transitions.yaml`, `spec/rhp1.qnt`, FastAPI `apply_command()` pipeline, 2-phase poller, outbox relay, hash chain, Merkle witness/signer, and concurrency/mutation test suites.

* **Lane B (Person B — Clients, Reach & Independent Monitor):** Owns the independent Python runtime monitor (`monitor/`), React PWA desks, SSE consumer, pure-JS browser verifier, `BROKEN_BUILD` scratch orchestration, dispatcher console, Exotel IVR & paper code adapters, and demo fallbacks.

### 3.1 Common-Mode Failure Independence (`F17`)

To prevent the server and runtime monitor from sharing a common-mode bug:

* **Person A** writes the backend server, `spec/transitions.yaml`, and the Quint specification (`spec/rhp1.qnt`).

* **Person B** writes the Python runtime monitor (`monitor/`) in a **separate Antigravity workspace/conversation** derived strictly from the prose invariants in §3 of the Architecture spec and the database schema.

* The monitor **must never** import server packages, share helper functions with `/api`, or read `/api` source files; it connects exclusively via the read-only PostgreSQL role `rhp_monitor`.

### 3.2 Agent Responsibilities & Direct Loop

| Agent Role | Owns | Strictly Prohibited From |
| --- | --- | --- |
| **Google Antigravity (Builder, Fixer & Test Runner)** | Executing surgical tasks from `AG-PROMPT`, diagnosing issues, applying clean fixes inside permitted files, running test/audit commands, pasting raw outputs into the report, committing tags `step-<ID>-loop<n>`, and outputting the single mandatory completion banner. | Deciding architecture, editing `/spec` or `db/01_schema.sql`, claiming tests pass without raw terminal output. |
| **Gem 1 — CONDUCTOR & MASTER VALIDATION AUDITOR** | Sole reviewing agent (Gem 2 & Gem 3 retired). Maintains the `STATE LEDGER`, sequences validation stages (V1..V5), performs root-cause analysis, writes targeted `AG-PROMPT` fix blocks, and enforces gate acceptance criteria. | Writing product code directly, advancing stages without raw verification output. |

### 3.3 Loop Cadence & Mandatory Banner

* **Direct Post-Build Loop (`Gem 1 -> Antigravity -> Gem 1`):** Every cycle goes directly between Gem 1 and Antigravity.
* **Mandatory Antigravity Completion Banner:**
  `🛑 VALIDATION & FIX STEP COMPLETED — PASTE THIS REPORT DIRECTLY BACK INTO GEM 1!`



---

## 4. Protected Paths & Repository Layout (`CODEOWNERS` Enforcement)

```text
/
├── GEMINI.md                          # Workspace & Agent Constitution (READ-ONLY to coding agents)
├── AGENTS.md                          # Antigravity builder rules & report contract (READ-ONLY)
├── CODEOWNERS                         # Enforces human-only edits on /spec, /db/schema.sql, /monitor
├── docker-compose.yml                 # Locked 8-service local/demo topology (pg, api, poller, relay, monitor, witness, toxiproxy, pwa, tunnel)
├── spec/                              # FROZEN L0 ARTIFACTS — AI AGENTS MAY NOT EDIT TO PASS CI
│   ├── ReferralHandshake_LOCKED_Problem_Statement_v7.md
│   ├── ReferralHandshake_v8_LOCKED_Solution.md
│   ├── ReferralHandshake_FINAL_LOCKED_Architecture.md
│   ├── transitions.yaml               # Canonical state transition table (consumed by server & explorer)
│   ├── rhp1.qnt                       # Quint formal control-plane specification (Person A)
│   ├── profiles.signed.json           # 4 cold-key Ed25519-signed timing profiles
│   └── vectors/                       # Model-based conformance vectors (28 scenarios + edge cases)
├── db/
│   ├── schema.sql                     # Locked 24-table PostgreSQL 16 DDL, functions, triggers, roles
│   └── seed_synthetic.sql             # Synthetic Karnataka obstetric directory & roster seed (REAL_DATA=0)
├── api/                               # Lane A: FastAPI application, 10-step apply_command(), poller, relay
├── monitor/                           # Lane B: Independent Python runtime monitor (ZERO imports from /api)
├── witness/                           # Separate OS user (uid 1002, rhp-sign) Ed25519 Merkle checkpoint signer
├── pwa/                               # Lane B: React PWA desks, dispatcher console, pure-JS noble verifier
└── scripts/
    └── make_scratch.sh                # Provisions isolated rhp_scratch_broken DB (drops one_lease for BROKEN_BUILD=1)

```

* **Anti-Reward-Hacking Rule (`D28`, `L0`):** AI agents are strictly forbidden from modifying files in `spec/`, `db/schema.sql`, or `monitor/` to make a failing build or test pass unless explicitly instructed in a user-approved `SPEC-DEVIATION`.



---

## 5. Core Protocol Engineering Laws (Mandatory Implementation Rules)

### 5.1 Global Lock Order & I14 Enforcement (`F1`, `I14`)

1. Every multi-table transaction touching contract state must acquire locks in this strict total order: **`referral → offer (ORDER BY id) → deadline (ORDER BY id) → outbox`**.


2. Every contract-mutating transaction must lock the `referral` row first (`SELECT * FROM referral WHERE id = %s FOR UPDATE`) and immediately stamp the transaction-local session GUC: `SELECT set_config('rhp.locked_referral', %s, true)`.


3. Database triggers `lk_referral`, `lk_offer`, `lk_deadline`, `lk_event`, `lk_grant`, and `lk_outbox` execute `rhp_require_lock()` and raise `I14_LOCK_NOT_HELD` if `current_setting('rhp.locked_referral', true)` does not match the target `referral_id`.


4. Only delivery-bookkeeping updates (`deadline.claimed_until` when `status` and `due_at` are unchanged, and `outbox` updates for `status`/`attempts`/`visible_after`) are exempt from `rhp_require_lock()`.



### 5.2 The 10-Step `apply_command()` Pipeline (`§5`)

Every state-changing command (`CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `COUNTER`, `CONFIRM_COUNTER`, `DECLINE`, `TIMEOUT`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`, `TR_UPDATE`, `CANCEL`, `CLOSE`, `REVOKE_GRANT`) must execute through `apply_command(conn, cmd, sess, idem_key)` in `READ COMMITTED` isolation following these exact 10 steps:

1. **Idempotency (Before Referral Lock):** Compute `h = sha256(jcs(cmd.body_for_hash()))`. Acquire non-blocking transaction advisory lock `pg_try_advisory_xact_lock(hashtextextended(f"{sess.roster_id}:{idem_key}", 0))`; if `false`, return `409 DUPLICATE_IN_FLIGHT`. Query `idempotency` by `(actor_id, key)`: if `request_hash != h`, return `422 KEY_REUSED_DIFFERENT_PAYLOAD`; if `status == 'DONE'`, replay stored `(http_status, response)` (including stored `409`/`412`/`422` rejections). Otherwise upsert `status = 'IN_FLIGHT'` with 48-hour expiry.


2. **Session Validation:** Verify opaque token hash in `session` (and linked `device` / `roster` validity, not revoked or expired); return `401 SESSION_INVALID` on failure.


3. **PIN Verification (Mutating Commands):** Verify PIN against `roster.pin_hash` using Argon2id (~100 ms target). On failure, increment `session.pin_failed` and set `pin_locked_until` (backoff `0 s`, `5 s`, `30 s`, then lock `120 s` on strike 3 and emit `PIN_LOCKED` / page dispatcher) on a **separate autonomous database connection** so main-transaction rollback never erases failed attempts (`F7`). Lockout is scoped strictly to `(session_id or call_sid)` so an attacker cannot lock out a facility's duty role.


4. **Lock Referral, Stamp GUC & Monotone Timestamp (`F11`, `I16`):** Execute `SELECT * FROM referral WHERE id = %s FOR UPDATE`, set `rhp.locked_referral`, compute `ts = GREATEST(clock_timestamp(), r.head_ts)`, and open `SAVEPOINT sp_cmd`.


5. **Authority & Fencing (`I6`, `I8`):** Verify active roster slot, facility match, and active `payload_grant` (`403` on failure); verify `cmd.expected_version == r.version` and `cmd.expected_epoch == r.lease_epoch` (`412` on stale writer).


6. **Transition Guard (`transitions.yaml`):** Lock `offer` rows (`ORDER BY id`) and `deadline` rows (`ORDER BY id`) for `r.id`; lookup transition guard in `transitions.yaml`.


7. **Staleness & Live Reconfirmation (`F12`, `I15`):** For `ACCEPT` or `CONFIRM_COUNTER(true)`, verify the offer is in an acceptable state (`409 LATE_ACCEPT_REJECTED` if already `TIMED_OUT`/`SUPERSEDED`) and verify every required capability in `need_class_requirement` has a row in `offer_resource_confirmation` with `expires_at > ts` (`409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` if expired).


8. **Apply Contract State Changes:** Update `offer` statuses, increment `lease_epoch` on ownership grant/revoke, update `referral.open_offers` (`0..2`), manage `payload_grant` rows, mark satisfied/superseded `deadline` rows `DONE`/`CANCELLED` (`WHERE id = $1 AND status = 'PENDING'`), and insert new `deadline` rows (satisfying deferred trigger `i1_pending_deadline`).


9. **Append Hash-Chained Event & Outbox Rows (`I4`, `I5`):** Increment `seq = r.head_seq + 1`, compute `hash = SHA256(prev_hash || JCS(core))` (genesis `prev_hash = 32 × 0x00`), insert into `event` (and `event_secret` if applicable), insert notification rows into `outbox` (locked last in global order), and update `referral` (`version + 1`, `head_seq`, `head_hash`, `head_ts = ts`).


10. **Finalize & Commit (or Rollback to Savepoint on Domain Reject):** Update `idempotency` to `status = 'DONE'` with HTTP status and response JSON, then `COMMIT`. If steps 5–8 raise a deterministic domain `Reject(code, reason)`, execute `ROLLBACK TO SAVEPOINT sp_cmd` (retaining the `referral` lock acquired before the savepoint), insert an audit row into `rejected_command`, mark `idempotency` as `DONE` with the error code/reason, and `COMMIT`. Any unexpected exception aborts the entire transaction so the `idempotency` row vanishes and client retries re-execute cleanly.



### 5.3 Stateless Two-Phase Poller & Outbox Relay (`F1`, `§5`)

* **Poller Phase 1 (Single Committed Claim Statement, No Referral Lock):**
```sql
UPDATE deadline SET claimed_until = clock_timestamp() + interval '5 seconds'
 WHERE id IN (
   SELECT id FROM deadline
    WHERE status = 'PENDING' AND due_at <= clock_timestamp()
      AND (claimed_until IS NULL OR claimed_until < clock_timestamp())
    ORDER BY due_at LIMIT 50 FOR UPDATE SKIP LOCKED
 )
 RETURNING id, referral_id, kind, step, epoch;

```


Phase 1 commits immediately so `deadline` locks are never held while waiting for a `referral` lock.


* **Poller Phase 2 (Per-Deadline Command Execution):** Iterates over claimed rows and invokes `apply_command(..., TimeoutCmd(...), SYSTEM_SESSION, idem_key=f"timeout:{d.id}")`, which acquires the `referral` lock first and re-verifies `status = 'PENDING'` and matching `step`/`epoch`.


* **Outbox Relay:** Claims up to 20 pending rows via `FOR UPDATE SKIP LOCKED` with a 30-second visibility timeout (`visible_after = clock_timestamp() + interval '30 seconds'`, `attempts = attempts + 1`), dispatches to adapters, and marks `status = 'SENT'` (or `status = 'DEAD'` + dispatcher page when `attempts > 8`).



### 5.4 Two Independent Tracks, Offer Cap & Soft-Open Rules (`I2`, `I3`, `I12`, `F5`, `F6`, `F13`)

* **Track Independence (`I3`):** Handshake states (`CREATED`, `OFFERED`, `ACKNOWLEDGED`, `ACCEPTED`, `COUNTERED`, `ESCALATED_TO_DISPATCHER`, `CANCELLED`, `CLOSED`) and Transport states (`REQUESTED`, `DISPATCHED`, `EN_ROUTE`, `ARRIVED`, `HANDED_OVER`, `TR_CANCELLED`) run in parallel. `TR_UPDATE` and `TR_DESTINATION_CHANGE` **never** read `hs_state` and never block care.


* **Pre-Referral MgSO4 Rule (`D1`, `K1`):** `mgso4_status` (`GIVEN | NONE_GIVEN | UNKNOWN`) is answer-required, never knowledge-required. Selecting `UNKNOWN` never blocks `CREATE` or ambulance dispatch; it renders a red verification banner on the receiving desk.


* **Single Lease & Open-Offer Cap (`I2`, `I12`, `F13`):** Partial unique index `one_lease ON offer (referral_id) WHERE status = 'ACCEPTED'` guarantees at most one lease holder. Open offer statuses are `OPEN`, `ACKED`, `COUNTERED`, and `SOFT_OPEN`, bounded by `CHECK (open_offers BETWEEN 0 AND 2)`.


* **Sequential Soft-Open Overlap (`F13`):** In `SEQUENTIAL` mode, when step $k$ times out and step $k+1$ is offered, offer $k$ enters `SOFT_OPEN` (total open offers = 2). If $k$ accepts before $k+1$ ACKs, $k$ wins the lease and $k+1$ becomes `SUPERSEDED`. Once $k+1$ ACKs (or if $k+2$ opens), $k$ transitions to `TIMED_OUT` and any late accept from $k$ receives `409 LATE_ACCEPT_REJECTED`.


* **Counter-Offer Cap (`F13`):** Maximum 2 counter rounds (`counter_round BETWEEN 0 AND 2`). `COUNTER_CONFIRM` deadline is `min(C, remaining D)` so counter-offers never extend a facility's decision window $D$.


* **Six Arrival Cases (`F5`):** Geofence (`200 m` + dwell) emits `ARRIVAL_SUGGESTED` only; human EMT or desk actor must confirm `TR_UPDATE(ARRIVED)`. Unannounced arrival at a non-owner emits `ARRIVAL_AT_NON_OWNER` + urgent alert without blocking care.


* **Mandatory Closure & 9 Outcomes (`F6`):** Terminal states `CLOSED` and `CANCELLED` require one of the 9 outcomes (`ADMITTED_STABLE`, `ADMITTED_CRITICAL`, `DELIVERED_AT_RECEIVER`, `DELIVERED_EN_ROUTE`, `PATIENT_REFUSED`, `TRANSPORT_CANCELLED`, `DETERIORATED_OR_DIED_PRE_HANDOVER`, `REDIRECTED_ON_ARRIVAL`, `UNKNOWN_COUNTER_REFERRAL`). If unclosed after `HANDED_OVER`, the `CLOSURE` deadline fires `CLOSURE_OVERDUE`, re-arms once, and on second expiry auto-closes with `UNKNOWN_COUNTER_REFERRAL` (`proxy=true`, `actor=system`).



### 5.5 Timing Model & Signed Profiles (`F2`, `F3`, `I13`)

* **Unified ACK Window ($A$) & Notice Rungs (`F2`):** Rung `0` = SSE + empty-payload FCM to all rostered slots concurrently; Rung `A/4` = Exotel outbound voice (slot $i$ at $A/4 + i \cdot \delta$, $i = 0 \dots S-1$); Rung `3A/4` = dispatcher proxy page; Rung `A` = `TIMEOUT(ack)`.


* **Worst-Case Escalation Bound (`F3`, `I13`):**

$$T_{max} = F \cdot (A + D + \epsilon) \le B$$



And when voice is enabled:

$$\frac{A}{4} + (S - 1) \cdot \delta + V \le \frac{3A}{4}$$



The startup validator refuses to boot if $T_{max} > B$, if the Ed25519 cold-key signature on the profile fails, or if a demo profile (`DEMO_FAST`, `DEMO_VOICE`) is loaded when `REAL_DATA=1`.



| Profile ID | $A$ (ms) | $D$ (ms) | Rungs ($0, A/4, 3A/4$) | $S, \delta, V$ (ms) | $F$ | $\epsilon$ (ms) | $T_{max}$ | Bound $B$ | `REAL_DATA=1` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `PILOT_OB_CRITICAL` | 60,000 | 180,000 | 0 / 15,000 / 45,000 | 3, 5,000, 20,000 | 3 | 3,000 | 729 s | 900 s | Allowed

 |
| `PILOT_STANDARD` | 120,000 | 300,000 | 0 / 30,000 / 90,000 | 3, 10,000, 20,000 | 3 | 3,000 | 1,269 s | 1,500 s | Allowed

 |
| `DEMO_FAST` | 3,000 | 4,000 | 0 / 750 / 2,250 | 3, 0, voice off | 3 | 1,000 | 24 s | 25 s | **Refuses Boot**

 |
| `DEMO_VOICE` | 45,000 | 20,000 | 0 / 11,250 / 33,750 | 1, 0, 20,000 | 2 | 1,000 | 132 s | 150 s | **Refuses Boot**

 |

---

## 6. Complete 24-Table Database Inventory & Role Separation (`F4`, `§7`)

The PostgreSQL 16 schema consists of exactly **24 locked tables** and **3 least-privilege database roles**:

1. **`facility`:** Curated directory (`id`, `code`, `name`, `tier` in `PHC|CHC|FRU|DH|MC|DISPATCH`, `lat_e5`, `lon_e5`, `active`).


2. **`roster`:** Duty roles (`NURSE`, `CMO`, `CONSULTANT`, `CLINICIAN`, `EMT`, `DISPATCHER`, `ADMIN`, `JUDGE_DESK`), `slot_no`, `phone_e164`, Argon2id `pin_hash`, validity window.


3. **`facility_capability`:** Self-reported capabilities (`OT`, `BLOOD`, `ANAESTHETIST`, `PAEDIATRICIAN`, `NICU`) with `attested_at` and `expires_at` (never presented as live beds).


4. **`need_class_requirement`:** Maps `need_class_t` to required `cap_t` capabilities.


5. **`catchment_chain`:** Administratively approved ordered target facilities per `(origin_facility_id, need_class, position 1..8)`.


6. **`device`:** Registered 32-byte Ed25519 public keys bound to `roster_id`.


7. **`enrollment_ticket`:** Single-use 15-minute enrollment token hashes issued by `ADMIN`.


8. **`session`:** Opaque session token hashes bound to `device_id` or `call_sid`, tracking per-session `pin_failed` and `pin_locked_until` (`F7`).


9. **`referral`:** Authoritative contract head (`version`, `hs_state`, `tr_state`, `mode`, `need_class`, `chain`, `ladder_cursor`, `lease_offer_id` deferred FK, `lease_facility_id`, `lease_epoch`, `open_offers` `0..2`, `mgso4_status`, `profile_id`, `profile_hash`, `paper_code`, `head_seq`, `head_hash`, `head_ts`, `outcome`).


10. **`offer`:** Per-facility offer state (`UNIQUE(referral_id, facility_id)` for `I9`, partial unique index `one_lease` where `status = 'ACCEPTED'` for `I2`, `offer_chain_guard` trigger for `I7`).


11. **`offer_resource_confirmation`:** Live capability confirmations with `expires_at > confirmed_at` (`I15`).


12. **`deadline`:** Durable timers (`ACK`, `DECISION`, `COUNTER_CONFIRM`, `NOTICE_VOICE`, `NOTICE_PROXY`, `HANDOVER`, `DISPATCH_ACTION`, `CLOSURE`) with `claimed_until`.


13. **`event`:** Append-only hash-chained log (`PRIMARY KEY (referral_id, seq)`, `event_id UNIQUE`, `CHECK (rhp_detail_ok(type, detail))`, protected by `event_ao` and `event_guard` triggers).


14. **`key_version`:** Per-referral wrapped AES-256-GCM DEK under monthly `kek_epoch` (`ACTIVE` vs `SHREDDED`).


15. **`event_secret`:** Encrypted PHI/sensitive event fields bound to `event.secret_hash`.


16. **`clinical_payload`:** Envelope-encrypted ISBAR + Dakshata handover payload with `expires_at`.


17. **`payload_grant`:** Per-facility decryption/stream access grants (`one_active_grant` partial unique index; drives `I10` SSE filtering).


18. **`telemetry`:** Set-union append-only `GPS` and `OBS` events (`event_id UNIQUE`).


19. **`idempotency`:** Scoped `(actor_id, key)` request hash and response store (`IN_FLIGHT` / `DONE`, 48 h TTL).


20. **`inbox`:** Webhook deduplication table (`UNIQUE (source, external_id)`) for Exotel/FCM callbacks.


21. **`outbox`:** Transactional notification queue (`SSE`, `FCM`, `VOICE`, `SMS`, `PROXY_PAGE`) with `visible_after` and `attempts`.


22. **`rejected_command`:** Append-only audit log of deterministic `401/403/409/412/422/429` rejections (protected by `rejected_ao` trigger).


23. **`checkpoint`:** Append-only 5-second binary Merkle roots (`REGULAR` or cold-key-signed `RESTORE`, protected by `checkpoint_ao` trigger).


24. **`heartbeat`:** Liveness and `ntp_offset_ms` tracker for `POLLER`, `RELAY`, `MONITOR`, `WITNESS`, and `DEVICE`.



### 6.1 Database Roles

* **`rhp_app`:** Application writer; `REVOKE UPDATE, DELETE ON event, checkpoint, rejected_command`; `GRANT DELETE` only on `event_secret, clinical_payload, idempotency, telemetry` for crypto-shredding and TTL purge.


* **`rhp_monitor`:** Read-only (`SELECT` on `event, referral, offer, deadline, checkpoint, heartbeat, outbox, rejected_command`; `INSERT, UPDATE` on `heartbeat`); zero access to `clinical_payload` or `event_secret`.


* **`rhp_witness`:** Separate OS user (`rhp-sign`, uid `1002`); `SELECT` on `event, referral, checkpoint`; `INSERT` on `checkpoint`; `INSERT, UPDATE` on `heartbeat`.



---

## 7. Invariants (`I1–I16`) & Mutation Suite (`M1–M6`)

### 7.1 Invariant Verification Matrix

| ID | Invariant Predicate | Primary DB / Server Enforcement | Independent Monitor Check (`rhp_monitor`) |
| --- | --- | --- | --- |
| **I1** | Every non-terminal referral has $\ge 1$ `PENDING` deadline; overdue acted on within $\tau$

 | Deferred constraint trigger `i1_pending_deadline` at `COMMIT`

 | `clock_timestamp() - due_at > TAU_MS` on `PENDING` deadline

 |
| **I2** | $\le 1$ active lease per referral; `lease_epoch` strictly increases

 | `one_lease` partial unique index + `referral` row lock

 | Fold counts $>1$ `ACCEPTED` offer or `epoch <= prev_epoch` on `LEASE_GRANTED`

 |
| **I3** | `TR_UPDATE` accepted in every non-terminal `hs_state`

 | Transport transition path never reads `hs_state`

 | Any `rejected_command` on `TR_UPDATE` with reason $\ne$ terminal/invalid TR step

 |
| **I4** | Each `event_id` appears once; per-referral `seq` is gap-free ($1 \dots n$)

 | `idempotency` PK, `event.event_id UNIQUE`, `PK(referral_id, seq)`, `rhp_event_guard`

 | `e.seq != st["seq"] + 1` or duplicate `event_id` in fold

 |
| **I5** | Per-referral SHA-256 chain & Ed25519 checkpoints verify; terminal states have `outcome`

 | Append-only triggers `event_ao`, `checkpoint_ao`; `CHECK ((hs_state IN ('CLOSED','CANCELLED')) = (outcome IS NOT NULL))`

 | Recomputes `SHA256(prev_hash |
| **I6** | Every `ACCEPT`/`COUNTER`/`DECLINE` is from a valid rostered role + device/number + PIN, or `proxy=true`

 | Steps 2–3 & Step 5 of `apply_command()`

 | Event actor lacks valid `roster` row at `server_ts`

 |
| **I7** | System-chosen offers target `referral.chain`; dispatcher offers carry `source='DISPATCHER'`

 | Trigger `offer_chain_guard` (`rhp_chain_guard()`)

 | Offer with `source='CHAIN'` where `facility_id` $\notin$ `referral.chain`

 |
| **I8** | Stale `expected_version` / `expected_epoch` is never applied and is logged

 | Step 5 fencing $\rightarrow$ `412` + `rejected_command` insert

 | Applied event with `epoch < referral.lease_epoch`

 |
| **I9** | A facility is offered at most once per referral (no `A → B → A` loops)

 | `UNIQUE (referral_id, facility_id)` on `offer`

 | Duplicate `facility_id` across `OFFER_CREATED` events for a referral

 |
| **I10** | Clinical SSE frames sent only to subscribers with an active `payload_grant`

 | Per-frame grant check + `GRANT_REVOKED` control frame

 | Audit of frame emission after `payload_grant.revoked_at`

 |
| **I11** | `event.detail` contains only allowlisted keys with `bool`, `int`, enum, or `UUID` values

 | Pydantic `Literal` schemas + DB `CHECK (rhp_detail_ok(type, detail))`

 | Scan of `event.detail` keys/values against allowlist

 |
| **I12** | $\le 2$ open offers (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) per referral

 | `CHECK (open_offers BETWEEN 0 AND 2)` maintained under lock

 | `r.open_offers > 2` or fold count of open offers $> 2$

 |
| **I13** | Configured $T_{max} = F \cdot (A + D + \epsilon) \le B$ for the active profile

 | Startup `validate(profile, REAL_DATA)` guard

 | Recomputed at boot and on `/healthz`

 |
| **I14** | No contract-state write occurs without holding the `referral` row lock

 | Triggers `lk_*` checking GUC `rhp.locked_referral`

 | `pg_stat_database.deadlocks` delta $= 0$ and `log_lock_waits` scan

 |
| **I15** | No lease is granted from a resource confirmation expired at `server_ts`

 | Step 7 `expires_at > ts` check $\rightarrow$ `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`

 | `OFFER_ACCEPTED` where $\min(\text{expires\_at}) \le \text{server\_ts}$

 |
| **I16** | `server_ts` is monotonically non-decreasing per referral

 | `GREATEST(clock_timestamp(), r.head_ts)` + `rhp_event_guard`

 | `e.ts < st["ts"]` in fold

 |

### 7.2 Mandatory Mutation Tests (`M1–M6`, `F17`)

Before Gate `G0` passes, each of these 6 mutations must be injected on an isolated test run and caught by its designated detector:

* **`M1`:** Skip `expected_epoch` fencing in server $\rightarrow$ must trip Monitor `I8` + vector `V-STALE-EPOCH`.


* **`M2`:** Remove `FOR UPDATE` on `referral` and drop `one_lease` index (in `rhp_scratch_broken`) $\rightarrow$ must trip `T-C1 race200` + Monitor `I2`.


* **`M3`:** Poller holds `deadline` row lock across `apply_command()` $\rightarrow$ must trip `T-F1 lock_order_200way` (deadlock delta $> 0$) / `I14`.


* **`M4`:** Remove open-offer cap guard in `rhp1.qnt` so a 3rd offer opens $\rightarrow$ `quint run rhp1.qnt --invariant safety` must produce an `I12` counterexample.


* **`M5`:** Write `prev_hash` as all-zeros on event insert $\rightarrow$ must trip Pure-JS Browser Verifier + Monitor `I5` (`kind=PREV`).


* **`M6`:** Ignore `offer_resource_confirmation.expires_at` on `ACCEPT` $\rightarrow$ must trip vector `V-STALE-CONFIRM` + Monitor `I15`.



---

## 8. Copy-Paste Handoff Packet Formats & Build Catalogue

### 8.1 `STATE LEDGER` (Printed by Gem 1 in Every Reply)

```text
=== STATE LEDGER v<n> ===
Clock: H<hh> of 24 (or Phase P) | Lane A step: <id> | Lane B step: <id>
Gates:  G0(T0)[ ]  G1(T1)[ ]  G2(T2)[ ]  G3(rehearsal)[ ]  FREEZE H22[ ]
Done steps: <ids with last good tag>
Open defects: <D-id sev short title> ...
Accepted risks (user-approved): <R-id ...>
Approved spec deviations: <none | ids>
Last good commit/tag: <lane A> / <lane B>
Cut so far: <none | T3 ...>
Next 3 steps: <ids>

```



### 8.2 `BUILD REPORT` + `AUDIT-REQUEST` (Emitted by Antigravity after Every Step)

```text
STEP / LOOP / commit hash (tagged step-<ID>-loop<n>)
FILES CHANGED (git diff --stat)
CODE: full text of every file marked HIGH risk (or git diff if >300 lines)
COMMANDS RUN + RAW OUTPUT (pasted verbatim, never summarised)
TESTS: name | pass/fail | measured numbers
NOT DONE / SKIPPED
DEVIATIONS FROM SPEC (or "none")
ASSUMPTIONS
OPEN QUESTIONS
SELF-RATED RISK + the 3 things most likely to be wrong

=== VALIDATION & FIX REPORT FOR GEM 1 ===
Step: <id> | Stage: <V1..V5> | Loop: #<n>
Spec Anchors: <§ numbers, I# invariants, T-# tests>
Acceptance Criteria: <list from AG-PROMPT>
<Paste Report above>
Banner: 🛑 VALIDATION & FIX STEP COMPLETED — PASTE THIS REPORT DIRECTLY BACK INTO GEM 1!

```



### 8.3 Step Catalogue (`Phase P` & `Phase E`) and Tier Acceptance Gates (`§24`)

| Step ID | Window / Phase | Lane A (Backend / Proof) | Lane B (Clients / Reach / Monitor) | Risk / Loop | Gate & Measured Pass Criteria (`§24`) |
| --- | --- | --- | --- | --- | --- |
| **P1–P6** | Pre-Event (`Phase P`) | `P1`: `transitions.yaml` + vectors; `P2`:PG16 DDL load + FK scan (`ST-3`); `P3`: `rhp1.qnt` safety + vacuity checks

 | `P4`: Signed profiles + $T_{max}$ validator (`I13`); `P5`: Synthetic seed (`REAL_DATA=0`); `P6`: §21 pre-event verification checklist

 | `P1–P3`: HIGH (`FULL`); `P4–P6`: LOW/MED (`FAST`)

 | `ST-1..ST-5` green; `quint run rhp1.qnt --invariant safety --max-samples 20000` passes; vacuity checks fail as required.

 |
| **E0** | `H00–H02` | Repo, `docker-compose.yml`, DDL load, seed, `transitions.yaml` loader

 | PWA shell, rotating single-use QR (`jti`, 20 s TTL, rotates 15 s, cap 20 desks)

 | MED (`FAST`)

 | All containers boot healthy; `REAL_DATA=0` verified.

 |
| **E1** | `H02–H06` | `apply_command()` steps 1–10: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `DECLINE`

 | Receiving desk UI (priority queue, no countdown clocks, red `mgso4_status=UNKNOWN` banner), SSE with per-event `payload_grant` filter (`I10`)

 | HIGH (`FULL`)

 | Core state transitions and `GRANT_REVOKED` frame stripping verified.

 |
| **E2** | `H06–H09` | 2-phase poller, outbox relay, `TIMEOUT`, unified notice ladder (`0, A/4, 3A/4`)

 | Big screen UI; **Independent Python monitor** (built in isolated workspace, `rhp_monitor` role)

 | HIGH (`FULL`)

 | Monitor folds events and performs differential check against `referral`.

 |
| **E3** | `H09–H12` | RFC 8785 JCS hash chain, separate-OS-user (`rhp-sign`) Ed25519 Merkle witness, 5 s checkpoints

 | Pure-JS browser verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`, inclusion proof + `RESTORE` check)

 | HIGH (`FULL`)

 | Verifier pinpoints tampered `seq` (`kind=PREV|HASH`, `SEQ_GAP`, `TRUNCATED`).

 |
| **E4** | `H12–H14` | `race200` barrier test, mutation tests `M1–M6`, Toxiproxy suite

 | `BROKEN_BUILD=1` isolated `rhp_scratch_broken` DB + flashing red banner + exit-78 boot guards (`F20`)

 | HIGH (`FULL`)

 | **Gate `G0` (`T0` Pass):** `race200` = 1 `200 OK`, 1 `ACCEPTED` offer, gap-free `seq`, deadlock delta `0`; `M1–M6` trip checkers; 0 monitor violations over 10-min Hypothesis + chaos run; `BROKEN_BUILD` turns monitor red $\le 2\text{ s}$ and green on switch-back; `DEMO_FAST` silence-to-dispatcher $\le 25\text{ s}$.

 |
| **E5** | `H14–H17` | `COUNTER`, `CONFIRM_COUNTER`, 6 arrival cases (`F5`), 2-stage `CLOSURE` (`F6`)

 | Dispatcher console (proxy entry + override reason), PWA GPS ambulance fallback, replay scrubber

 | HIGH (`FULL`)

 | **Gate `G1` (`T1` Pass):** 20 paired proxy vs direct API runs yield identical state & event sequence; dispatcher assigns after `ESCALATED_TO_DISPATCHER`; log replay reproduces final state.

 |
| **E6** | `H17–H20` | Full idempotency edge-case matrix (`F14`), stale confirmation & fencing vectors

 | Outbound Exotel IVR (AMD + press-1 gate, 2 s webhook budget, `%23` PIN), 9-char Crockford + mod-37 paper code

 | HIGH (`FULL`)

 | **Gate `G2` (`T2` Pass):** 20/20 voice ACKs recorded only after DB commit; 0/5 voicemail calls ACKed; webhook p95 $\le 2\text{ s}$; 1,000/1,000 single-symbol mutated paper codes rejected.

 |
| **E7** | `H20–H22` | Fix any defects surfaced in `G0–G2`

 | Record MP4 fallback clips (`Clips A–D`), run 30-second live proof loop rehearsal $\times 3$

 | MED (`FULL`)

 | **Gate `G3` (Rehearsal Pass):** 30-second live proof loop completes smoothly; LAN fallback tested.

 |
| **E8** | `H22–H24` | **CODE FREEZE AT H22:** config-only adjustments

 | Final stage rehearsal, warm backup laptop + phone hotspot

 | LOW (`FAST`)

 | **FREEZE:** Zero application code commits after `H22`.

 |

(Note: `T3_EXTRAS` — Kotlin Android app, AI intake accelerator with 20-slip seeded-error gate $\le 5\%$ rubber-stamp / $\le 1\%$ silent omission, and FHIR R4 / IEEE 1849 XES export — may only be attempted if Gates `G0`, `G1`, and `G2` are completely green.)

---

## 9. Explicit DO / DO NOT Guardrails & Claims Register (`§19`)

### 9.1 Technical & Workflow DO / DO NOTs

* **DO** route every contract mutation exclusively through `apply_command()` after locking `referral` first and setting `rhp.locked_referral`.


* **DO** separate optimistic concurrency `version` (`412` on stale precondition) from ownership `lease_epoch` (`409 LEASE_HELD` / `LATE_ACCEPT_REJECTED` on lost race).


* **DO** keep receiving desk queues free of countdown clocks (to prevent Goodhart triage distortion) and report APOT-style `ARRIVED → HANDED_OVER` separately from `ACCEPT`.


* **DO** paste verbatim terminal commands and raw outputs in every `BUILD REPORT`.


* **DO NOT** write `referral`, `offer`, `deadline`, `event`, or `payload_grant` rows from any route or worker outside `apply_command()`.


* **DO NOT** allow `BROKEN_BUILD=1` to connect to the primary database or boot when `REAL_DATA=1`.


* **DO NOT** send patient names or clinical text over SMS, FCM push notifications, or unauthenticated SSE streams, and never speak a patient name on Exotel voice calls.


* **DO NOT** display pre-claimed latency or recovery numbers in the UI or pitch; every operational metric shown on stage must be measured live from the running system.



### 9.2 Authorized vs. Forbidden Claims (`§19` Claims Lint)

| Authorized Wording (Mandatory in UI, Docs & Pitch) | Forbidden Claims (Must Never Appear in Code, UI, Docs or Slides) |
| --- | --- |
| Referral communication and documentation gaps are documented in specific urban Indian studies (Das et al., 2023 Maharashtra; Safdarjung Hospital Delhi 2018–2023)

 | National prevalence claims; "lives saved"; "deaths prevented"; mortality reduction claims

 |
| Automatic inter-facility escalation and hard single-owner guarantees were "not found in public documentation of the systems audited"

 | "First", "only", or "no competitor has this"

 |
| Designed to comply; synthetic data only (`REAL_DATA=0`); "ABDM-sandbox aligned" only if sandbox calls are executed

 | "ABDM compliant"; "production ready"; live integration with 108, hospitals, or ABDM

 |
| Every identified weakness is `CLOSED`, `BOUNDED` with a stated technical residual, or `OPEN` with a named owner

 | "Bullet-proof", "airtight", "zero loopholes", "guaranteed", "immune", "crash-proof", "zero silent drops"

 |
| Control-plane model checked within stated bounds ($F=3, E=4$); implementation checked by conformance vectors, randomised tests, and a live independent monitor

 | "Mathematically proven system"; "mathematically impenetrable"

 |
| Tamper-evident hash-chained log with independent Merkle witnesses and a BSA s.63-ready export bundle

 | "Immutable log"; "BSA certified"; legally conclusive without Part A / Part B certification

 |
| Process improvements, escalation, and capacity signalling are hypotheses to be tested in an ethics-approved pilot

 | "Eliminates ping-pong"; measured ambulance-minutes saved in India as an established fact

 |