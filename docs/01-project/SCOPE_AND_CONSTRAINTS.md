# ReferralHandshake (Protocol RHP-1) — Scope, Architectural Locks & Operational Constraints

**System:** Referral Handshake Protocol (RHP-1) & Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru)  
**Build Window:** 24 Hours | **Team Size:** 2 Engineers (Person A / Lane A & Person B / Lane B)  
**Pitch Format:** 5-Minute Pitch with $\ge 30\text{ s}$ Live Guarantee Arena Demo `[V]`  
**Data Posture:** Synthetic Data Only (`REAL_DATA=0` enforced at boot)

---

## 1. Input Precedence & Evidence Tag Legend

### 1.1 Strict Input Precedence Hierarchy (Non-Negotiable)
Any ambiguity across project artifacts, specifications, prompts, or implementation code is resolved strictly in this descending order of authority:
1. **`ReferralHandshake_LOCKED_Problem_Statement_v7.md`** — Highest authority on problem framing, empirical evidence citations, status tags, and claims discipline.
2. **Primary Research Findings Tagged `[V]`** — Verified facts across Waves 1–4 (R01–R15) embedded in the locked documents.
3. **`ReferralHandshake_v8_LOCKED_Solution.md`** — Authority on D1–D20 defect closures, the 28-scenario conformance catalogue, the 40-item loophole ledger, and the real-world clinical operating model.
4. **`ReferralHandshake_FINAL_LOCKED_Architecture.md`** — Ultimate technical authority on F1–F20 architectural closures, I1–I16 formal invariants, the 24-table PostgreSQL 16 DDL, the 10-step `apply_command()` pipeline, timing math, the Quint specification (`rhp1.qnt`), the independent Python runtime monitor, and T0–T3 build tiers.
5. **`ReferralHandshake_3Gem_Antigravity_Workflow.md` & `AGENTS.md`** — Authority on multi-agent governance, Lane A / Lane B workspace isolation, `CODEOWNERS` locks, and verification gates.

### 1.2 Evidence & Risk Status Tag Legend
All architectural claims, pitch slides, documentation, and UI labels must preserve these exact epistemic and risk tags:
- **`[V]`** — Verified from primary research or official technical documentation.
- **`[V*]`** — Verified only from a secondary, vendor, blog, or law-firm source; must be confirmed from primary sources before appearing on a slide.
- **`[CONFLICT]`** — Primary or secondary research files disagree; both sides must be stated conservatively without asserting a single figure where contested.
- **`[GAP]`** — No reliable empirical evidence or settled legal interpretation found; parameterized in software, no factual claim permitted.
- **`[verify]`** — Requires execution of the pre-event verification test (§21 of the Locked Architecture) before live reliance.
- **`CLOSED`** — Weakness eliminated by a deterministic technical mechanism verified by a named automated test (`T-*`).
- **`BOUNDED`** — Weakness constrained to an explicit, mathematically or operationally stated residual bound monitored by a runtime alarm.
- **`OPEN`** — Residual risk that software alone cannot close; assigned to a named human owner with required closing evidence.

---

## 2. Problem Scope, Clinical Pathway & Empirical Boundaries

### 2.1 The Locked Problem Statement
> **How can an emergency referral stop being a message and become a verifiable contract: one that is offered, answered, negotiated, owned by exactly one destination, escalated automatically when nobody responds, never delays care, works from a feature phone to a command centre, survives failures, and closes with an outcome back to the referrer, with its guarantees provable rather than promised?**

### 2.2 Three Delays Framing Boundary
- **In Scope:** The contested operational boundary between **Delay 2** (reaching an adequate facility) and **Delay 3** (receiving adequate care upon arrival) `[V]`—specifically inter-facility handover communication, ownership arbitration, capability verification, and escalation `[V*]`.
- **Out of Scope:** **Delay 1** (deciding to seek care at the household/community level) is explicitly excluded from system scope.

### 2.3 Empirical Evidence Register & Mandatory Citation Rules
All problem framing is restricted to the following verified studies and their exact operational constraints:

| Finding | Study / Setting | Tag | Mandatory Citation & Scope Constraint |
|---|---|---|---|
| Referring facility phoned receiving facility in **47%** of referrals (11,988); **53%** had no phone contact | Urban Maharashtra, 2016–2019, 199,888 deliveries (Das et al., 2023) | `[V]` / Denominator `[CONFLICT]` | Denominator is reported as 25,253 in some tables and 28,020 in others `[CONFLICT]`; 47%, 37%, and 60% only reproduce with 25,253. **Quote percentages only**; state "urban Maharashtra obstetric study". |
| **37%** of referral slips fully documented (9,279) | Same study (Das et al., 2023) | `[V]` | Quote percentage only; attribute to documentation completeness, never clinical mortality. |
| **60%** of referred women tracked at higher facility; **40%** untraceable due to incomplete documentation and demographic errors | Same study (Das et al., 2023) | `[V]` | Frame strictly as traceability/loop-closure loss, never "lost lives". |
| **19%** of referrals driven purely by missing resources: no emergency OT (**47%**), no NICU (**45%**), no anaesthetist (**24%**), no paediatrician (**22%**) | Same study (Das et al., 2023) | `[V]` | State clearly that OT/NICU/anaesthetist/paediatrician percentages are shares *within* the 19% resource-driven subgroup. |
| **90.6%** of critically ill obstetric patients arrived with no prior communication; **70%** had no escort; slips incomplete in **50%** | Safdarjung Hospital, Delhi, 3,220 inter-facility referrals, 2018–2023 | `[V]` | Must qualify as "one tertiary obstetric ICU centre in Delhi", never a national average. |
| **47.3%** had visited $\ge 2$ hospitals before arrival ("ping-pong") | Same audit (Safdarjung, 2018–2023) | `[V]` | Cite as evidence of multi-stop transfer delay in that cohort; never claim RHP-1 "eliminates ping-pong". |
| Asynchronous digital referral handled **52%** of one hospital's gynaecology referrals by advice alone, but suffered delays when receivers did not respond due to **no mandated response deadline** | Vula Mobile evaluation (South Africa) | `[V]` | Cite as direct process evidence for enforced deadlines and automatic escalation ladders. |
| Calls for GIS facility mapping, bed/critical-care readiness, and command centres linked toward ERSS 112 | National Ambulance Services (NAS) Guidelines 2026 (29 June 2026) | `[V]` | Policy states the desired outcome, not a handover protocol. Verify exact clauses in official text before quoting. |
| National Indian referral failure prevalence, ambulance-minutes lost in India, and mortality effect of digital handshakes | Literature audit across Waves 1–4 | `[GAP]` | **Zero claims permitted.** All claims must be strictly operational (handover reliability, documentation completeness, traceability). |

### 2.4 Clinical Pathway Scope
- **Primary Pathway (Built & Demoed First):** Emergency obstetric referral (`OBSTETRIC_EMERGENCY`) across Karnataka-style public health tiers:
  $$\text{PHC} \rightarrow \text{CHC} \rightarrow \text{FRU} \rightarrow \text{DH (District Hospital)} \rightarrow \text{MC (Medical College)} \rightarrow \text{DISPATCH}$$
- **Generic Data Model Support:** The PostgreSQL domain `need_class_t` (`OBSTETRIC_EMERGENCY`, `NEONATAL`, `TRAUMA`, `CARDIAC`, `STROKE`) and `cap_t` (`OT`, `BLOOD`, `ANAESTHETIST`, `PAEDIATRICIAN`, `NICU`) generalize the state machine without schema changes. Non-obstetric pathways are data-model ready but out of scope for the 24-hour live clinical scenario script.

---

## 3. The Coherence Rule & System Boundary Classification

### 3.1 The Coherence Rule (Non-Negotiable Scope Filter)
Every table, API endpoint, background worker, UI screen, and script in ReferralHandshake **must** be classified as exactly one of:
- **(a) Contract State or Event:** Authoritative state machine transitions, ownership leases, durable deadlines, or hash-chained events.
- **(b) Contract Interface (Producer / Consumer):** An adapter or client that submits idempotent commands into `apply_command()` or delivers outbox notifications from committed events, holding **zero** business logic.
- **(c) Read-Only Projection of the Committed Log:** An independent verifier, monitor, analytics view, or exporter that reads committed state/events without mutating contract state.

**Anything that does not fit (a), (b), or (c) is strictly out of scope and must be rejected.**

### 3.2 Complete Component Classification Matrix

| Component / Module | Category | Exact Role in RHP-1 Contract | Scope Boundary & Constraints |
|---|---|---|---|
| `referral`, `offer`, `offer_resource_confirmation`, `deadline` | **(a) Contract State** | Holds authoritative handshake state (`hs_state`), transport state (`tr_state`), single-owner lease (`lease_epoch`), resource confirmations, and durable timers | Mutated **exclusively** inside `apply_command()` under `SELECT ... FOR UPDATE` on `referral` (`I14`). |
| `event`, `event_secret`, `clinical_payload`, `key_version`, `payload_grant`, `rejected_command` | **(a) Contract Evidence & Privacy State** | Append-only per-referral SHA-256 hash chain, AES-256-GCM envelope-encrypted clinical payload, facility access grants, and fenced/rejected command audit | `event` and `rejected_command` have `BEFORE UPDATE OR DELETE` trigger `rhp_no_mutate()`. `rph_app` has no `UPDATE`/`DELETE` privilege on them. |
| `facility`, `roster`, `facility_capability`, `need_class_requirement`, `catchment_chain`, `device`, `enrollment_ticket`, `session` | **(a) Contract Authority State** | Defines valid facilities, rostered duty roles, timestamped capability attestations, administratively approved escalation chains, device keys, and PIN-verified sessions | Enforces `I6` (authority), `I7` (no invented destination), and `F7` (per-session PIN lockout scope). |
| `idempotency`, `inbox`, `outbox`, `telemetry`, `heartbeat` | **(b) Interface Plumbing** | Guarantees exactly-once command application (`I4`), deduplicates external webhooks, schedules at-least-once channel delivery, and records append-only GPS/vitals/liveness | `telemetry` is append-only set-union (`event_id UNIQUE`); never overwrites authoritative contract state. |
| FastAPI Command API (`apply_command`) | **(a)/(b) Core Arbiter** | Executes the 10-step serialised command pipeline | Single entry point for all state transitions. |
| Stateless Timer Poller (`rhp.poller`) | **(b) Event Producer** | Phase 1 claims due `deadline` rows (`SKIP LOCKED`); Phase 2 invokes `apply_command(TIMEOUT)` | Never mutates `referral` or `offer` directly (`F1`). |
| Outbox Relay (`rhp.relay`) | **(b) Event Consumer** | Claims `outbox` rows (`SKIP LOCKED`) with 30 s visibility timeout and dispatches to SSE, FCM, Exotel, and SMS adapters | At-least-once delivery; consumers deduplicate by `outbox.id`. |
| React PWA Desks (Clinician, Receiving Desk, Dispatcher, Judge QR, Ambulance Fallback) | **(b) Interface** | Submits commands with `Idempotency-Key` and consumes SSE streams (`Last-Event-ID`) | Holds zero authoritative state; offline actions queued as "pending, not confirmed". |
| Native Android App (Kotlin, Tier T3) | **(b) Interface** | Runs `FOREGROUND_SERVICE_TYPE_LOCATION`, Room offline outbox, and empty-payload FCM wake + fetch | Geofence (200 m + dwell) emits `ARRIVAL_SUGGESTED` only; never transitions `ARRIVED` without human confirmation (`D2`, `F5`). |
| Exotel Outbound IVR & DLT SMS Adapters | **(b) Interface** | Places outbound voice calls with AMD + Press-1 gate + DTMF PIN; sends static DLT SMS alerts | Outbound only; no patient name spoken; zero PHI in SMS (`P2`). |
| Paper Slip & 9-Char Crockford Code (`mod 37`) | **(b) Interface** | Printable referral card with checksummed code linking paper arrivals to digital records | Eliminates double-entry (`D18`); carries zero clinical data in the code. |
| AI Intake Accelerator (Tier T3) | **(b) Interface Helper** | Drafts unverified intake fields behind a Cognitive Forcing Function (`423 ANCHOR_REQUIRED`) | Off critical path; hidden until `need_class` and `mgso4_status` are committed; zero confidence scores shown (`D1`, `A1–A3`). |
| Independent Python Runtime Monitor (`monitor`) | **(c) Read-Only Projection** | Connects via read-only role `rhp_monitor` (`REPEATABLE READ READ ONLY`), folds `event` log, checks `I1–I16` and state differential | Written by Person B from §3 prose alone; imports **zero** server code (`F17`). |
| Witness / Checkpoint Signer (`witness`) & Pure-JS Browser Verifier | **(c) Read-Only Projection** | Separate OS user (`rhp-sign`, role `rhp_witness`) signs 5 s binary Merkle trees (`checkpoint`); browser verifies Ed25519 + SHA-256 inclusion proofs | Detects database tampering, row deletion, or split-view history (`F8`, `D10`). |
| Command Centre, Network Graph, XES & FHIR R4 Exporters | **(c) Read-Only Projection** | Computes APOT-separated KPIs, descriptive `networkx` centrality, IEEE 1849 XES (4 h buckets, $k \ge 5$), and FHIR `ServiceRequest`/`Task`/`Encounter`/`Communication` | Strictly read-only; no live ProM on stage (`D16`); no counterfactual claims in demo. |

### 3.3 Explicit Out-of-Scope Exclusions
The following features are permanently excluded from ReferralHandshake:
1. **Electronic Health Record (EHR) / Longitudinal Medical Record Storage:** RHP-1 stores a short-lived *handover record* and an anonymised *event-metadata log*, never a hospital EHR.
2. **ABDM Longitudinal Health Record Fetching:** Fetching past records requires patient consent (ABDM M3) which an unconscious emergency patient cannot grant (`[GAP]`). Summaries are strictly clinician-authored at the point of care.
3. **Automated AI Triage or Autonomous Routing:** The system never invents a destination (`I7`), never auto-reroutes a moving ambulance (`D2`), and never uses AI to choose facilities.
4. **Live Bed-Inventory Management:** Facility capabilities are self-reported staff attestations shown with age (`attested_at`, `expires_at`), never presented as "live beds" (`D15`).
5. **Hospital Billing, Pharmacy, Lab Order Management, or Teleconsultation Video:** Out of scope.

---

## 4. Hard Technology Stack & Architectural Locks

### 4.1 Locked Technology Stack

| Layer | Locked Technology | Mandatory Configuration & Constraints |
|---|---|---|
| **Database** | PostgreSQL 16 (Single Writable Primary) | `synchronous_commit=on`, `log_lock_waits=on`, isolation level `READ COMMITTED` with explicit per-referral `SELECT ... FOR UPDATE` (`F1`, `D8`). Read-only projections use `REPEATABLE READ READ ONLY`. Row locks never run on standbys/replicas. |
| **Backend API & Workers** | Python 3.12 + FastAPI + `psycopg` (v3) | Pydantic v2 models with `extra='forbid'` on all request schemas (`I6`, `I11`). Synchronous/async connection pool executing the 10-step `apply_command()` pipeline. |
| **Web Client** | React PWA (TypeScript/JavaScript) | Server-Sent Events (SSE) with `Last-Event-ID` resume and 15 s heartbeats. HttpOnly, Secure, `SameSite=Strict` session cookies. |
| **Client Cryptography** | `@noble/curves/ed25519` & `@noble/hashes/sha256` | Bundled pure-JS libraries required because iOS Safari lacks Ed25519 in WebCrypto and `crypto.subtle` is disabled on insecure LAN HTTP origins `[V]` (`D1`). |
| **Canonical Serialization** | RFC 8785 JSON Canonicalization Scheme (JCS) | Restricted strictly to ASCII keys and **integers, strings, and booleans only**. Floating-point numbers are prohibited (coordinates use `lat_e5`/`lon_e5` micro-integers; timestamps use integer milliseconds/microseconds). |
| **Password / PIN Hashing** | Argon2id | Tuned to $\approx 100\text{ ms}$ per verification on demo hardware; failure counters committed on an autonomous DB connection (`F7`). |
| **Payload Encryption** | AES-256-GCM + AES-KW | Per-referral 256-bit DEK (`clinical_payload`, `event_secret`) wrapped by a monthly KEK (`key_version.kek_epoch`). |
| **Mobile Client (T3 / T1)** | Native Android (Kotlin) / React PWA Fallback | Android uses `FOREGROUND_SERVICE_TYPE_LOCATION`, `FusedLocationProviderClient`, Room offline outbox, WorkManager, and zero-payload FCM wake pings (`D13`). Demo uses T1 PWA GPS fallback if T3 is cut. |
| **Telephony / SMS** | Exotel Outbound IVR + DLT SMS | Outbound voice calls to $\le 10$ whitelisted sandbox numbers `[V]`; webhook must return HTTP 200 within $\le 2\text{ s}$ internal budget (Exotel hard timeout 5 s `[V]`). Static DLT SMS template with `{#var#}` $\le 30$ chars `[V]`. |
| **Routing & Maps** | Mapbox Directions & Matrix API | Server-side cached calls for active referral's top candidates only. `mapbox/driving` Matrix (25 coords, 60 req/min) or `driving-traffic` (10 coords, 30 req/min) `[V]`. Commercial Mapbox tiles or self-hosted PMTiles (never bulk-scrape OSM tile servers). |
| **Edge & Admission** | Cloudflare WAF + Turnstile + Tunnel | Rotating single-use QR (`jti` valid 20 s, rotates every 15 s) gated by Turnstile challenge and 20-desk admission cap (`D11`). Local hotspot LAN-QR fallback fails closed. |
| **Formal Spec & Testing** | Quint (`rhp1.qnt`) + Apalache + Hypothesis + Toxiproxy | Quint bounded model checking ($F=3, \text{MAXE}=4$, 20,000 samples); 200-way `asyncio.Barrier` concurrency test; 8-toxic Toxiproxy fault matrix; M1–M6 mutation suite. |

### 4.2 Banned Technologies & Prohibited Patterns
Introducing any of the following into code, configuration, or documentation is an automatic **S1 Audit Failure**:

| Banned Technology / Pattern | Reason for Prohibition (Traceability) | Locked Alternative in RHP-1 |
|---|---|---|
| **Blockchain / Smart Contracts / Distributed Ledgers** | Adds latency, cost, and complexity with zero benefit over a single district arbiter (`v8 §1.3`, `App. A`). | Per-referral SHA-256 hash chain + 5 s Ed25519 signed Merkle checkpoints held by outside witnesses (`§11`). |
| **Kafka / Debezium / RabbitMQ** | Over-engineered operational burden for a 2-person team and single-district pilot (`v8 §3`). | Same-transaction PostgreSQL `outbox` table + stateless polling relay (`SKIP LOCKED`, 30 s visibility timeout). |
| **Redis / Memcached (Shared Cache Tier)** | Introduces cache-invalidation races and leaves decrypted PHI in shared memory (`§0`, `§10`). | Process-memory-only payload decryption with `Cache-Control: no-store`; PostgreSQL primary for all state/locks. |
| **Kubernetes (EKS/GKE)** | Over-engineered for a 24-hour build and single-district pilot (`v8 §3`, `§12`). | `docker-compose` for demo; managed Multi-AZ PostgreSQL + 2 small app VMs + ALB for pilot (`§17`). |
| **WebSockets** | Complicates proxy traversal, stateless horizontal scaling, and reconnection semantics (`v8 §3`). | HTTP/2 Server-Sent Events (SSE) with `Last-Event-ID` + standard HTTP POST commands. |
| **WhatsApp / Consumer Messengers** | Prohibited for transmitting clinical health data (`v7 §12`, `v8 §1.3`). | PWA web desks, Exotel voice IVR, static DLT SMS alerts, and paper checksum codes. |
| **On-Device LLMs / Authoritative AI** | High error rates (VLM 85–95%, Indic ASR WER $>20\%$) and hardware limits (`v8 §8`, `§16`). | Structured ISBAR entry primary; optional cloud intake draft behind Cognitive Forcing Function (`T3_EXTRAS`). |
| **CRDTs for Authoritative Contract State** | Cannot enforce single-owner leases (`I2`) or fencing tokens across competing hospitals (`v7 §6`, `v8 §3`). | Serialised PostgreSQL row lock (`SELECT ... FOR UPDATE`) for state; set-union (`event_id UNIQUE`) for append-only telemetry. |
| **SQLite for Contract State** | WAL `synchronous=NORMAL` risks losing commits on power loss; single-file lock serialises unrelated referrals (`D8`). | PostgreSQL 16 with `synchronous_commit=on` and per-referral row locking. |
| **Event-Sourcing-Only Storage** | Recomputing state on every read complicates query performance and row locking (`v8 §3`, `§5.2`). | Mutable `referral`/`offer` state tables updated in the **same transaction** as the append-only `event` log, verified continuously by the differential monitor. |
| **Floating-Point Numbers in Canonical JSON** | IEEE 754 formatting discrepancies across languages break RFC 8785 JCS SHA-256 hashes (`§0`, `§11`). | Strict integer micro-units (`lat_e5`, `lon_e5`, `client_ts_ms`, `server_ts_us`). |
| **Live ProM on Stage** | Fragile JVM desktop tooling during a 5-minute pitch (`D16`). | In-app process/network graph computed directly from the PostgreSQL log + validated IEEE 1849 XES export. |

---

## 5. Formal Protocol Constraints & Invariants (I1–I16)

### 5.1 Complete Invariant Specification Table
Every code path in `api/` must preserve, and `monitor/` must independently verify, all 16 invariants:

| ID | Type | Formal Predicate | Primary Enforcement Mechanism | Independent Monitor Rule (`rhp_monitor`) | Verification Test |
|---|---|---|---|---|---|
| **I1** | Liveness | Every non-terminal referral (`hs_state NOT IN ('CLOSED','CANCELLED')`) has $\ge 1$ `PENDING` deadline and a responsible role; overdue deadlines are acted on within tolerance $\tau$ (`2 * poll_interval + 2000 ms`). | `DEFERRABLE INITIALLY DEFERRED` constraint trigger `i1_pending_deadline` on `referral` at `COMMIT`; two-phase stateless poller. | Flag `("I1", referral_id)` if `status='PENDING' AND due_at < clock_timestamp() - TAU_MS`. | `T-I1` |
| **I2** | Safety | At most **one** active ownership lease per referral (`count(ACCEPTED) <= 1`); `lease_epoch` is strictly increasing on every ownership grant/revocation. | Partial unique index `one_lease ON offer(referral_id) WHERE status='ACCEPTED'` + `SELECT * FROM referral FOR UPDATE`. | In event fold, flag `("I2", seq)` if `LEASE_GRANTED` occurs while `lease != None` or `e.epoch <= st["epoch"]`; check `DIFF_EPOCH`. | `T-I2`, `T-C1 race200` |
| **I3** | Safety | Transport track updates (`TR_UPDATE`, `TR_DESTINATION_CHANGE`) are accepted in **every** non-terminal `hs_state`; care is never blocked by handshake state or unknown drug history. | `TR_UPDATE` handler never reads `hs_state` (except to check terminal `CLOSED`/`CANCELLED`); `mgso4_status='UNKNOWN'` allowed. | Flag `("I3", id)` if any `rejected_command` for `TR_UPDATE` has a reason other than terminal referral or invalid `tr_state` step. | `T-I3`, `T-K1` |
| **I4** | Safety | Every client `event_id` is applied at most once; per-referral `seq` starts at 1 and is strictly gap-free (`seq = head_seq + 1`). | Step 1 `idempotency` PK `(actor_id, key)` + `pg_try_advisory_xact_lock`, `event.event_id UNIQUE`, `PRIMARY KEY(referral_id, seq)`, trigger `rhp_event_guard()`. | In event fold, flag `("I4", seq)` if `e.seq != st["seq"] + 1` or duplicate `event_id` observed. | `T-I4`, `T-F14` |
| **I5** | Safety | Per-referral SHA-256 hash chain (`hash = SHA256(prev_hash || JCS(core))`) and Ed25519 checkpoint signatures verify; `CLOSED`/`CANCELLED` referrals always have a non-null `outcome` and `closed_at`. | Triggers `event_ao`, `checkpoint_ao`, `rhp_event_guard()`; `referral` CHECK `((hs_state IN ('CLOSED','CANCELLED')) = (outcome IS NOT NULL AND closed_at IS NOT NULL))`. | Recompute `SHA256(prev_hash || JCS(core))` for every event; flag `("I5", seq)` on mismatch; verify `DIFF_HEAD` against `referral`. | `T-I5`, `T-F8` |
| **I6** | Safety | Every `ACCEPT`, `COUNTER`, `DECLINE`, or `RESOURCE_CONFIRM` originates from an active rostered role on a registered device/number with a verified PIN, or carries `proxy=true` with a reason code. | Pipeline Steps 2, 3, and 5 (`load_session`, `argon2_verify`, `authorize`). | Verify `actor_roster_id` has a valid `roster` row covering `server_ts` and matching facility/role, or `proxy=true`. | `T-I6`, `T-F7` |
| **I7** | Safety | The system never invents a destination: every offer with `source='CHAIN'` targets a facility in `referral.chain`; out-of-chain offers must have `source='DISPATCHER'`. | Trigger `offer_chain_guard()` (`BEFORE INSERT ON offer`) checks `NEW.facility_id = ANY(referral.chain)` when `source='CHAIN'`. | Flag `("I7", seq)` if `OFFER_CREATED` has `source='CHAIN'` and `facility` $\notin$ `referral.chain`. | `T-I7` |
| **I8** | Safety | Commands carrying a stale `expected_version` or `expected_epoch` are never applied to contract state and are recorded in `rejected_command` with HTTP `412`. | Pipeline Step 5 `fence(r, cmd)` raises `Reject(412, "STALE_VERSION_OR_EPOCH")`, rolls back to `SAVEPOINT sp_cmd`, logs to `rejected_command`. | Flag `("I8", seq)` if any committed event has `e.epoch < st["epoch"]`. | `T-I8`, `M1` |
| **I9** | Safety | No referral loops: a facility appears at most once as an offer target per referral. | Table constraint `UNIQUE (referral_id, facility_id)` on `offer`; `advance()` skips already-offered facilities. | Flag `("I9", seq)` if the same `facility` receives more than one `OFFER_CREATED` in a referral's fold. | `T-I9` |
| **I10** | Safety | Clinical payload frames are delivered only to subscribers holding an active (`revoked_at IS NULL`) `payload_grant` for that referral and facility. | Per-event SSE/fetch authorization check + 15 s heartbeat re-check + `GRANT_REVOKED` control frame pushed on revocation. | Audit stream emitter logs against `payload_grant.revoked_at`. | `T-I10`, `T-F10` |
| **I11** | Safety | `event.detail` contains only allowlisted keys for its `event.type` (`rhp_allowed(type)`) and values restricted to booleans, $\le 12$-digit integers, UUIDs, or uppercase enum tokens (`^[A-Z0-9_]{1,40}$`). | Pydantic `Literal` schemas (`extra='forbid'`) + PostgreSQL `CHECK (rhp_detail_ok(type, detail))` on `event`. | Scan `event.detail` keys and value formats during fold. | `T-I11`, `T-F9` |
| **I12** | Safety | At most **2** offers per referral may be in the open set (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) at any instant. | `referral.open_offers CHECK (open_offers BETWEEN 0 AND 2)` maintained under the referral lock; early expiry of `k-1` `SOFT_OPEN` when `k+1` opens. | Flag `("I12", referral_id)` if `r.open_offers > 2` or folded count of open offers $> 2$. | `T-I12`, `T-F13`, `M4` |
| **I13** | Safety | For the active signed timing profile, worst-case escalation time satisfies $T_{max} = F \cdot (A + D + \epsilon) \le B$, and demo profiles refuse boot when `REAL_DATA=1`. | Startup `validate(profile, REAL_DATA)` check + cold-key Ed25519 signature verification before FastAPI accepts traffic. | Recompute $T_{max} \le B$ and profile signature at monitor startup and `/healthz`. | `T-I13`, `T-F2`, `T-F3` |
| **I14** | Safety | No contract-state write (`referral`, `offer`, `deadline` status/due, `event`, `payload_grant`, `outbox` insert) occurs without holding the `referral` row lock in the canonical lock order. | `SELECT * FROM referral WHERE id=$1 FOR UPDATE` + `set_config('rhp.locked_referral', r.id, true)` enforced by trigger `rhp_require_lock()`. | Monitor `pg_stat_database.deadlocks` delta (must equal 0) and `log_lock_waits`. | `T-I14`, `T-F1`, `M3` |
| **I15** | Safety | No lease is granted (`ACCEPT` or `CONFIRM_COUNTER(true)`) if any required capability confirmation in `offer_resource_confirmation` has `expires_at <= server_ts`. | Pipeline Step 7 `check_confirmations()` verifies all `need_class_requirement` capabilities are confirmed and `expires_at > ts`; else returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`. | Cross-check `OFFER_ACCEPTED` `server_ts` against `offer_resource_confirmation.expires_at`. | `T-I15`, `T-F12`, `M6` |
| **I16** | Safety | Per-referral event timestamps (`server_ts`) are monotonically non-decreasing (`NEW.server_ts >= r.head_ts`). | `ts = GREATEST(clock_timestamp(), r.head_ts)` under the referral lock + trigger `rhp_event_guard()`. | In event fold, flag `("I16", seq)` if `e.ts < st["ts"]`. | `T-I16`, `T-F11` |

---

## 6. Concurrency, Locking, Timing & State-Machine Constraints

### 6.1 Global Lock Order & Two-Phase Poller Discipline (`F1`, `I14`)
To prevent deadlocks across concurrent HTTP commands and background workers, every transaction touching contract state must acquire locks in this strict forward order:
$$\text{advisory try-lock (non-blocking)} \rightarrow \texttt{referral} \rightarrow \texttt{offer } (\text{ORDER BY id}) \rightarrow \texttt{deadline } (\text{ORDER BY id}) \rightarrow \texttt{outbox}$$

1. **No Lock Held Across Worker Phases:** The timer poller (`rhp.poller`) **never** holds a `deadline` row lock while calling `apply_command()`.
   - **Phase 1 (Claim):** Executes a single self-contained `UPDATE deadline SET claimed_until = clock_timestamp() + interval '5 seconds' WHERE id IN (... LIMIT 50 FOR UPDATE SKIP LOCKED) RETURNING ...` and **commits immediately**.
   - **Phase 2 (Execute):** Iterates over the claimed rows and invokes `apply_command(TimeoutCmd(...), idem_key=f"timeout:{d.id}")`, which acquires the `referral` lock first, then `offer`, then re-verifies `deadline.status = 'PENDING'` under the lock.
2. **Database Trigger Enforcement (`rhp_require_lock`):** `BEFORE INSERT OR UPDATE` triggers (`lk_referral`, `lk_offer`, `lk_deadline`, `lk_event`, `lk_grant`, `lk_outbox`) verify `current_setting('rhp.locked_referral', true) = referral_id::text`. Only delivery bookkeeping updates (`deadline.claimed_until` when `status` and `due_at` are unchanged, and `outbox` `UPDATE` for `status`/`attempts`/`visible_after`) are exempt because they mutate no contract state.

### 6.2 Fencing vs. Contention HTTP Status Discipline (`D7`, `F12`, `F14`)
- **`412 Precondition Failed` (`STALE_VERSION_OR_EPOCH`):** Returned when `cmd.expected_version != referral.version` or `cmd.expected_epoch != referral.lease_epoch`. Recorded in `rejected_command` via `ROLLBACK TO SAVEPOINT sp_cmd`.
- **`409 Conflict`:** Returned when preconditions match or are evaluated at the offer level, but the business race or state guard rejects the command:
  - `LEASE_HELD` — Another facility already holds the lease (`status = 'ACCEPTED'`).
  - `LATE_ACCEPT_REJECTED` — A `SOFT_OPEN` offer attempted to accept after successor facility $k+1$ already ACKed (or after `PARALLEL2` timeout).
  - `STALE_CONFIRMATION_RECONFIRM_REQUIRED` — Required `offer_resource_confirmation` expired (`expires_at <= server_ts`).
  - `DUPLICATE_IN_FLIGHT` — Concurrent request with the same `(actor_id, Idempotency-Key)` is currently executing.
  - `DUPLICATE_EVENT_ID` — Reused `event_id` with a new `Idempotency-Key`.
  - `INVALID_TRANSITION` / `INVALID_TR` — State transition not permitted from current state.
- **`422 Unprocessable Entity`:** Returned on schema violation (`extra='forbid'`), `KEY_REUSED_DIFFERENT_PAYLOAD`, `MISSING_IDEMPOTENCY_KEY`, or `OUTCOME_REQUIRED`.
- **`423 Locked` (`ANCHOR_REQUIRED`):** Returned by the T3 AI Intake endpoint if queried before the clinician commits `need_class` and `mgso4_status`.

### 6.3 Timing Math & Signed Profile Constraints (`F2`, `F3`, `I13`)
1. **Unified ACK Window ($A$) & Notice Ladder Rungs:**
   - Every offer opens at $t = 0$ with an `ACK` deadline at $t = A$, a `NOTICE_VOICE` deadline at $t = A/4$, and a `NOTICE_PROXY` deadline at $t = 3A/4$.
   - All $S$ rostered slots at the receiving facility are notified concurrently via SSE/FCM at $t = 0$; voice calls stagger across slots at $t = A/4 + i \cdot \delta$ ($i \in \{0, \dots, S-1\}$) with call duration budget $V$, constrained by:
     $$\frac{A}{4} + (S - 1)\delta + V \le \frac{3A}{4}$$
2. **Worst-Case Time-to-Dispatcher Bound ($T_{max}$):**
   - Because COUNTER rounds ($\le 2$, each bounded by $\min(C, \text{remaining } D)$) sit strictly inside the facility decision window $D$, a single facility can consume at most $A + D$ before escalating, plus $\epsilon$ (poller tick + `apply_command` budget) per hop. Across $F$ max facilities:
     $$T_{max} = F \cdot (A + D + \epsilon) \le B$$
3. **Locked Signed Profiles (Milliseconds):**

| Parameter | `PILOT_OB_CRITICAL` | `PILOT_STANDARD` | `DEMO_FAST` | `DEMO_VOICE` |
|---|---|---|---|---|
| ACK Window $A$ | `60000` (60 s) | `120000` (120 s) | `3000` (3 s) | `45000` (45 s) |
| Decision Window $D$ | `180000` (180 s) | `300000` (300 s) | `4000` (4 s) | `20000` (20 s) |
| Notice Rungs $(0, A/4, 3A/4)$ | `0 / 15000 / 45000` | `0 / 30000 / 90000` | `0 / 750 / 2250` | `0 / 11250 / 33750` |
| Slots $S$, Stagger $\delta$, Voice $V$ | `3, 5000, 20000` | `3, 10000, 20000` | `3, 0, 0 (voice off)` | `1, 0, 20000` |
| Max Facilities $F$, Hop Budget $\epsilon$ | `3, 3000` | `3, 3000` | `3, 1000` | `2, 1000` |
| Counter Confirm $C$ / Confirm TTL | `90000 / 120000` | `150000 / 180000` | `2000 / 10000` | `10000 / 60000` |
| Handover $H$ / Dispatch / Closure | `7200000 / 300000 / 86400000` | `7200000 / 300000 / 86400000` | `30000 / 5000 / 20000` | `60000 / 10000 / 60000` |
| Computed $T_{max}$ vs. Bound $B$ | $729\text{ s} \le 900\text{ s}$ | $1269\text{ s} \le 1500\text{ s}$ | $24\text{ s} \le 25\text{ s}$ | $132\text{ s} \le 150\text{ s}$ |
| Boot Permitted with `REAL_DATA=1` | **YES** | **YES** | **NO (Hard Abort)** | **NO (Hard Abort)** |

---

## 7. Complete Traceability of Architectural & Solution Closures

### 7.1 Architectural Defect Closures (F1–F20)

| ID | v4/v5 Defect | Locked Mechanism in RHP-1 | Spec § | Verification Test |
|---|---|---|---|---|
| **F1** | Poller held deadline locks across commands; v5 self-contradicted | Total lock order `referral > offer > deadline > outbox`; poller Phase 1 is a single committed claim statement, Phase 2 calls `apply_command`; DB trigger `rhp_require_lock` enforces `I14` | §5, §7 | `T-F1 lock_order_200way` |
| **F2** | Notice ladder raced offer ACK | Rungs at $0, A/4, 3A/4$ inside ACK window $A$; 4 signed profiles; demo profiles refuse boot if `REAL_DATA=1` | §6 | `T-F2 profile_guard` |
| **F3** | $T_{max}$ double-counted slots and was unbounded in config | Slots notified concurrently; $T_{max} = F \cdot (A + D + \epsilon)$; startup refusal if $> B$ (`I13`) | §6 | `T-F3 tmax_validator` |
| **F4** | DDL incomplete | Complete 24-table PostgreSQL 16 DDL, `one_lease`, FKs, CHECKs, append-only triggers | §7 | `T-F4 ddl_load_fk_scan` |
| **F5** | Arrival ambiguity | Six explicit arrival cases `(a)–(f)`; geofence emits `ARRIVAL_SUGGESTED` only; human confirms `ARRIVED` | §4 | `T-F5 arrival_cases` |
| **F6** | Closure holes | Reachability & Exit table; 9-outcome taxonomy; two-stage `CLOSURE` deadline ending in explicit `UNKNOWN_COUNTER_REFERRAL` (`proxy=true, actor=system`) | §4 | `T-F6 reachability_bfs` |
| **F7** | Lockout-DoS, voicemail ACK | Single-use ticket $\rightarrow$ device key $\rightarrow$ opaque session; Argon2id in autonomous txn; lockout per `session_id`/`call_sid`; AMD + Press-1 gate | §8, §9 | `T-F7 pin_lockout_scope` |
| **F8** | Witness/restore gaps | Separate-OS-user Ed25519 signer (`rhp-sign`); binary Merkle inclusion proofs; cold-key signed `RESTORE` checkpoint & events | §7, §11 | `T-F8 tamper_vs_restore` |
| **F9** | Free-text `event.detail` | Per-type key allowlist (`rhp_allowed`), Pydantic + PG CHECK (`rhp_detail_ok`), 4 h export buckets, $k \ge 5$ suppression | §7, §10 | `T-F9 detail_check_fuzz` |
| **F10** | Streams outlive grants | Per-event authorization check; 15 s heartbeat check; `GRANT_REVOKED` control frame + DOM wipe | §9 | `T-F10 sse_revoke` |
| **F11** | Clock hazards | `GREATEST(clock_timestamp(), head_ts)` under referral lock (`I16`); chrony slew-only; $> 2\text{ s}$ `ntp_offset_ms` alarm | §6 | `T-F11 clock_step` |
| **F12** | Stale offline ACCEPT | `expires_at` on `offer_resource_confirmation`; `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`; live reconfirm (`I15`) | §5 | `T-F12 offline_stale` |
| **F13** | Open-offer count undefined | $\le 2$ open offers (`open_offers` CHECK `0..2`); `SOFT_OPEN` early-close rule; `PARALLEL2` and `COUNTER` race rules | §4 | `T-F13 open_cap` |
| **F14** | Replay semantics undefined | Idempotency is Step 1 before referral lock; scoped `(actor_id, key)` + `request_hash`; 8-case edge matrix | §5 | `T-F14 idem_matrix` |
| **F15** | Bare "none" residuals | Every row in §18 failure matrix states an explicit technical bound and reason | §18 | `T-F15 residual_lint` |
| **F16** | Demo scope vague | Tiers T0–T3 behind feature flags; second-by-second 30 s live proof loop with MP4 fallbacks | §2, §17 | `T-F16 loop_rehearsal` |
| **F17** | Spec/monitor common-mode bug | Person A writes backend/YAML/Quint; Person B writes Python monitor from §3 prose alone; M1–M6 mutation suite | §12 | `T-F17 mutation_suite` |
| **F18** | Three conflicting cloud cost figures | Reconciled 6-month AWS `ap-south-1` Multi-AZ cost table ($\approx \$1,419$, locked planning figure $\$1,420$) | §17 | `T-F18 cost_recompute` |
| **F19** | v7 state mapping implicit | Explicit 12-row v7 $\rightarrow$ RHP-1 (`hs_state`, `offer.status`, `tr_state`, `event.type`) mapping table | §4 | `T-F19 v7_map` |
| **F20** | Broken build near real data | `BROKEN_BUILD=1` uses isolated `rhp_scratch_broken` DB (without `one_lease`), flashing red banner, hard abort (exit 78) if `REAL_DATA=1` | §12 | `T-F20 broken_isolation` |

### 7.2 Solution Defect Closures (D1–D20 from v8 §0.2)

| ID | Defect in Earlier Drafts | Locked Fix in v8 & Final Architecture |
|---|---|---|
| **D1** | Hard-rejecting `CREATED` without MgSO4/Oxytocin dose blocked care | `mgso4_status` (`GIVEN \| NONE_GIVEN \| UNKNOWN`) is *answer-required*, never *knowledge-required*; `UNKNOWN` sets a red banner at the receiving desk and never blocks dispatch. |
| **D2** | No transport track; `ARRIVED` tied to geofence alone | Independent `tr_state` track (`I3`); 200 m geofence emits `ARRIVAL_SUGGESTED` only; human EMT/desk confirms `ARRIVED`. |
| **D3** | No counter/decline vocabulary, no intra-facility ladder, no loop prevention | Structured `ACCEPT` / `COUNTER` ($\le 2$ rounds) / `DECLINE` (with missing resource code), notice ladder + catchment chain, `UNIQUE(referral_id, facility_id)` (`I9`). |
| **D4** | Smartphone/web only; contradicted equity claim | Outbound Exotel voice IVR with DTMF + PIN, static DLT SMS alert, 9-char Crockford paper code, and dispatcher proxy entry. |
| **D5** | Overclaims ("mathematically impenetrable", "eliminates ping-pong", "MTTR 3 s") | Enforced Claims Register (§19); every latency/recovery metric shown on stage is measured live during the run. |
| **D6** | Dropped formal spec and model checking | Quint control-plane spec (`rhp1.qnt`) checked via Apalache/simulator + conformance vectors + Hypothesis stateful tests. |
| **D7** | Conflated `version_id` and lease token; returned `412` to race losers | Separate `referral.version` (`412` on stale precondition) and `referral.lease_epoch` (`409` on lost race); explicit `SOFT_OPEN` late-accept rule. |
| **D8** | SQLite WAL `synchronous=NORMAL` single-file database | PostgreSQL 16 primary with `synchronous_commit=on` and per-referral row locks. |
| **D9** | Fake "salt deletion" crypto-shredding; unverified 3-year retention claim | AES-256-GCM per-referral DEK (`key_version.wrapped_dek = NULL`) + monthly KEK epoch destruction; retention parameterized (`[GAP]`). |
| **D10** | Hash chain without outside witnesses vulnerable to split-view tampering | 5 s Ed25519 signed binary Merkle checkpoints broadcast to big screen, judge phones, and off-box witness log. |
| **D11** | Mintable QR JWTs allowed bot rate-limit bypass | Rotating single-use QR (`jti` valid 20 s) + Cloudflare Turnstile challenge + 20-desk admission cap + fail-closed LAN mode. |
| **D12** | Unspecified PIN verification location and brute-force exposure | Server-side Argon2id verification; failure counter in autonomous transaction; lockout scoped to `(session_id \| call_sid)`. |
| **D13** | Unsupported SSE mobile battery claim | SSE restricted to web desks; Android uses zero-payload FCM wake ping + authenticated HTTPS fetch. |
| **D14** | Misquoted OSM capability stats and patient bypass stats | Corrected citations (OSM bed tag 0.08%, emergency 1.03%); server-side cached Mapbox Matrix ETAs for top candidates only. |
| **D15** | Assumed live CEmONC capability data existed | Curated facility registry + staff attestations displayed with age and expiry (`expires_at`); never called "live beds". |
| **D16** | Fragile live ProM desktop demo and invalid counterfactual claims | In-app process/network view from live PostgreSQL log + IEEE 1849 XES export; zero counterfactual claims in demo. |
| **D17** | No demo fallback, code freeze, or offline path | Code freeze at H22, local hotspot + LAN-QR fallback, pre-recorded MP4 clips (`clip A–D`) for every scene. |
| **D18** | Ignored Goodhart gaming, DPDP s.7(i) staff notice, ICMR ethics, double-entry | Priority queue without countdown clocks; APOT arrival-to-handover separated from acceptance; printable referral card *is* the slip. |
| **D19** | Heavy JVM TeSSLa dependency for ordered streams | Independent Python runtime monitor written by Person B (`rhp_monitor`) over gap-free per-referral `seq`. |
| **D20** | No cut lines for a 2-person, 24-hour team | Strict T0–T3 feature-flagged tiers with deterministic cut order (`T3 -> T2 -> T1`, `T0` never cut). |

---

## 8. Build Tiers (T0–T3), Cut-Line Hierarchy & Multi-Agent Governance

### 8.1 Tier Definitions, Feature Flags & Cut Order (`F16`, `§2`, `§24`)
If schedule pressure occurs or a step fails 3 consecutive fix loops in the 2-Gem milestone workflow, scope is cut strictly from the bottom (`T3` first, then `T2`, then `T1`; **`T0` is never cut**):

| Tier | Feature Flag | Included Components | Cut Priority | Mandatory Acceptance Gate Criteria (§24) |
|---|---|---|---|---|
| **T0 (Core + Proof)** | *Always On* | FastAPI (`apply_command` 10 steps), PG 16 (`schema.sql` 24 tables), 2-phase poller, outbox relay, PWA desks with rotating QR, Python monitor (Person B), witness signer + pure-JS browser verifier, `BROKEN_BUILD` scratch DB | **Never Cut** | `race200` passes (1 of 200 gets `200`, 1 `ACCEPTED` offer in DB, `seq` gap-free, deadlock delta = 0); M1–M6 each trip their checker; monitor shows 0 violations over 10-min Hypothesis + chaos run; `quint run safety` passes ($\ge 20,000$ samples) & vacuity checks fail; verifier names edited `seq` on tampered row; `BROKEN_BUILD=1` turns monitor red $\le 2\text{ s}$ and green on switch-back; `DEMO_FAST` silence-to-dispatcher measured $\le 25\text{ s}$. |
| **T1 (Transport + Console)** | `T1_TRANSPORT=1` | PWA ambulance GPS (`watchPosition` + manual update), dispatcher console + proxy entry, override with reason, time-scrubber replay | **Cut 3rd** | Proxy entry and direct API entry produce identical state and event sequence in 20 paired runs; dispatcher console assigns after `ESCALATED_TO_DISPATCHER`; replay scrubber reproduces final state from the event log. |
| **T2 (Reach Channels)** | `T2_REACH=1` | Exotel outbound voice IVR (AMD + Press-1 gate + DTMF PIN), DLT-style static SMS stub/sandbox, 9-char Crockford Base32 (`mod 37`) paper code | **Cut 2nd** | 20/20 voice ACKs recorded only after DB commit; voicemail/silence yields 0 ACKs across 5 trials; Exotel webhook p95 $\le 2\text{ s}$; paper-code single-symbol errors and adjacent transpositions rejected 100% across 1,000 mutated codes. |
| **T3 (Extras)** | `T3_EXTRAS=1` | Native Kotlin Android app (`FOREGROUND_SERVICE_TYPE_LOCATION` + Room outbox), AI intake accelerator (`423 ANCHOR_REQUIRED`), FHIR R4 & IEEE 1849 XES exporters | **Cut 1st** | Android maintains GPS logging $\ge 2\text{ h}$ with screen off on demo device; AI draft withheld until `need_class` + `mgso4_status` anchors committed; 20-slip seeded-error gate achieves rubber-stamp $\le 5\%$ and silent omission $\le 1\%$; FHIR R4 bundle passes validator. |

### 8.2 Pre-Event vs. At-Event Work Boundary (`§2`, `§21`)
- **Permitted Pre-Event Artifacts (Specification & Setup Only, subject to organiser rules check `[verify]`):**
  1. Locked specification documents (`v7`, `v8`, `FINAL_LOCKED_Architecture`, `SCOPE_AND_CONSTRAINTS.md.md`, `AGENTS.md`).
  2. Frozen state transition table (`spec/transitions.yaml`), Quint specification (`spec/rhp1.qnt`), conformance vectors, and signed timing profile file (`spec/profiles.json`).
  3. PostgreSQL 16 schema file (`db/schema.sql`) and synthetic seed data (`db/seed.sql` with `REAL_DATA=0`).
  4. Exotel trial number whitelisting ($\le 10$ numbers), pre-recorded native speaker audio prompts (Kannada, Hindi, English), bundled `@noble/*` JS dependencies, and MP4 fallback recording plan.
- **At-Event Work (Built Inside the 24-Hour Window):**
  - All production application code (`api/`, `monitor/`, `witness/`, `pwa/`, `android/`), executed against the frozen specification and conformance vectors.
- **Hard Code Freeze at Hour 22 (`H22`):**
  - At `H22` (2 hours before the 24-hour mark), all application code is frozen. Only configuration toggles, MP4 fallback recording, and live pitch rehearsals (`G3`) are permitted between `H22` and `H24`.

### 8.3 Common-Mode Independence (`F17`) & Multi-Agent Governance Constraints
1. **Strict Author Separation (`F17`):**
   - **Person A (Lane A):** Owns `spec/transitions.yaml`, `spec/rhp1.qnt`, `db/schema.sql`, `api/`, and `witness/`.
   - **Person B (Lane B):** Owns `monitor/` (written exclusively from the prose invariants in §3 and the database schema, **never** reading or importing code from `api/`), `pwa/`, and reach adapters.
2. **Read-Only Spec & `CODEOWNERS` Protection (`v8 §7.1`, `AGENTS.md`):**
   - Files in `/spec`, `db/schema.sql`, and `monitor/` are hash-pinned in CI and protected by `CODEOWNERS`.
   - The AI coding builder (Google Antigravity) is **strictly forbidden** from modifying `/spec`, loosening database constraints, weakening `rhp_detail_ok`, or editing `monitor/` to make a failing test pass (anti-reward-hacking lock).
3. **2-Gem Milestone Validation Ring Enforcement:**
   - Every complete Feature or Milestone/Gate (`P1`–`P6`, `E0`–`E8`, `G0`–`G3`) and any `S1` fix must be validated through the **Milestone Validation** loop (`Gem 1 Conductor -> Antigravity -> Gem 2 Milestone Validator -> Gem 1`).
   - Any build report lacking raw terminal output and full code/diff of HIGH-risk files is automatically marked **REJECT** by Gem 2.

---

## 9. Security, Privacy, Telecom & Regulatory Constraints

### 9.1 Cryptographic & Privacy Engineering Locks
1. **Envelope Encryption & Crypto-Shredding (`D9`, `§10`):**
   - Clinical payloads (`clinical_payload`) and sensitive event fields (`event_secret`) are encrypted using AES-256-GCM with a unique per-referral 256-bit DEK (`AAD = referral_id || key_id || schema_ver` or `referral_id || seq || key_id`).
   - Each DEK is wrapped (`key_version.wrapped_dek`) with AES-KW under a monthly `kek_epoch` key.
   - `event.secret_hash` stores `SHA-256(ciphertext)` inside the hash chain so that deleting `clinical_payload` and `event_secret` rows and setting `key_version.wrapped_dek = NULL, status = 'SHREDDED'` destroys all clinical content **without breaking the SHA-256 event hash chain**.
   - When all referrals in a monthly `kek_epoch` expire, destroying the `kek_epoch` key renders historical WAL archives and database backups permanently unrecoverable.
2. **Metadata PHI Firewall (`F9`, `I11`):**
   - `event.detail` is validated by both Pydantic `Literal` schemas (`extra='forbid'`) and the PostgreSQL `rhp_detail_ok(type, detail)` CHECK constraint. Free text, patient names, phone numbers, and floating-point values are rejected at the database boundary.
   - Aggregate exports (XES, network graphs) bucket timestamps to **4-hour windows** and suppress any cell with **$k < 5$ referrals**.

### 9.2 Indian Legal & Regulatory Compliance Posture (`§10`)
ReferralHandshake operates on **synthetic data only (`REAL_DATA=0`)** during the hackathon and is **designed to comply** with the following statutory constraints prior to any clinical pilot:

| Statute / Guideline | Specific Provision / Constraint | System Posture & Technical Control | Status Tag |
|---|---|---|---|
| **DPDP Act 2023 & DPDP Rules 2025** | Commencement notified 13 Nov 2025 vs. Gazette 14 Nov 2025 `[CONFLICT]`; core obligations apply 13/14 May 2027 `[V]`. Section 7(f) (some drafts cite s.7(d) `[CONFLICT]`) medical emergency processing; Section 7(i) employment/staff telemetry; Section 8(5) security safeguards (ceiling ₹250 Cr); Section 8(6) breach notification (ceiling ₹200 Cr, 72 h DPBI report); Section 8(7) erasure vs. retention. | Handover record only; envelope encryption + per-grant stream revocation (`I10`); staff telemetry requires prior written notice, minimisation, siloing from HR records, and post-evaluation erasure (`D18`); retention period parameterized pending legal opinion on s.8(7) vs. NMC rules `[GAP]`. | `OPEN` (Legal review required before real data) |
| **Bharatiya Sakshya Adhiniyam (BSA) 2023, s.63** | Admissibility of electronic records requires Part A (custodian) and Part B (expert) certificates stating the cryptographic hash. | Exporter generates a deterministic JCS event bundle, per-file SHA-256, root bundle SHA-256, and pre-filled Part A / Part B certificate templates. **Never claimed as "BSA certified".** | `BOUNDED` |
| **CERT-In Directions (28 Apr 2022)** | Mandatory 6-hour incident reporting; 180-day rolling logs retained within India; NTP synchronisation traceable to NIC / NPL `[V]`. | Chrony configured in slew-only mode against NIC/NPL stratum sources with $> 2\text{ s}$ `heartbeat.ntp_offset_ms` alarm (`F11`); 180-day append-only audit log design; 6-hour breach runbook. | `BOUNDED` |
| **TRAI TCCCPR 2018 & DLT Rules** | Transactional SMS templates require Principal Entity registration, pre-tagged variables $\le 30$ chars, and whitelisted static domains; unsolicited voice calls restricted `[V]`. | SMS carries zero clinical text (`RHP alert: new referral. Open {#var#}`); voice IVR calls only pre-registered duty roster numbers (`<= 10` whitelisted trial numbers in demo) with de-identified prompts. No circumvention of telecom controls. | `CLOSED` (SMS) / `OPEN` (Voice legality `[GAP]`) |
| **ABDM / HDMP & NRCeS FHIR R4** | Longitudinal record fetch (M3) requires explicit patient consent (`[GAP]` for unconscious patients); production ABDM requires STQC/CERT-In WASA "Safe to Host" audit `[V*]`. | Zero longitudinal record fetching; clinician-authored point-of-care summary; curated NRCeS-aligned FHIR R4 export (`ServiceRequest`, `Task`, `Encounter`, `Communication`). Claim "ABDM-sandbox aligned" **only** if sandbox calls are executed; never claim "ABDM compliant". | `BOUNDED` |
| **NMC Telemedicine Guidelines 2020** | 3-year record retention mandate for teleconsultations `[V*]`. | Applicability to inter-facility handover records is unsettled `[GAP]`; `clinical_payload.expires_at` is a configurable policy parameter. | `OPEN` |
| **ICMR National Ethical Guidelines (2017 & 2023 AI)** | Tracking clinical staff behaviour is not exempt from ethics review; identifiable data of pregnant women or decision-influencing software requires Full Committee Review; AI requires human-in-the-loop override. | Shadow-mode district pilot gated on IEC approval; card replaces paper slip (zero double-entry); AI intake is optional, off-critical-path, and requires human anchor commitment (`423 ANCHOR_REQUIRED`). | `OPEN` |

---

## 10. Honest Limits, Loophole Ledger & Residual Risk Constraints

### 10.1 Explicit Honest Limits (Must Be Stated Plainly to Judges)
1. **Creates Zero Physical Capacity:** ReferralHandshake does not create ICU beds, operating theatres, blood units, or obstetricians. When every facility in a district is full, its value is surfacing refusal **before** the ambulance leaves or reaches the door, routing to the human dispatcher (`ESCALATED_TO_DISPATCHER`), and recording structured bottleneck evidence (`AT_CAPACITY`, missing capability codes).
2. **Cannot Force Clinical Honesty or Data Accuracy:** If a clinician enters inaccurate vitals or a receiving desk attests a capability that is unavailable, the protocol records the signed attestation and any subsequent `ARRIVAL_REJECTED` event, separating acceptance from physical handover (`ARRIVED -> HANDED_OVER` APOT metric), but cannot physically verify a ward bed.
3. **Does Not Eliminate Network Outages:** When cellular networks fail completely, existing clinical and phone procedures remain primary. The offline outbox queues events ("pending, not confirmed") and the printed 9-character Crockford paper code bridges the handover at the receiving door.
4. **Bounded Model Checking Scope:** Quint (`rhp1.qnt`) verifies the modelled control-plane specification at bounded parameters ($F=3, \text{MAXE}=4$), **not** the Python/SQL implementation for arbitrary sizes. The implementation is verified by conformance vectors, the 200-way barrier race test, Toxiproxy fault injection, M1–M6 mutation tests, and the live independent Python monitor.

### 10.2 Complete 40-Item Loophole Closure Ledger (`v8 §16` Mapped to Final Architecture)

| # | Loophole / Vulnerability | Closure Mechanism / Bounded Residual | Inv / Fix | Status |
|---|---|---|---|---|
| 1 | Mandatory drug fields block care | `mgso4_status` (`GIVEN \| NONE_GIVEN \| UNKNOWN`) is answer-required, never blocks dispatch; `UNKNOWN` triggers red receiver banner | `D1`, `I3`, `K1` | `BOUNDED` |
| 2 | Ambulance held until handshake finishes | Parallel, un-gated transport track (`tr_state` never reads `hs_state`) | `D2`, `I3` | `CLOSED` |
| 3 | Double lease granted on concurrent accept | `SELECT ... FOR UPDATE` on `referral` + `one_lease` partial unique index + `lease_epoch` | `I2`, `C1` | `CLOSED` |
| 4 | Zombie write from delayed offline device | Stale `expected_version` / `expected_epoch` fenced with `412` and logged in `rejected_command` | `I8`, `C7` | `CLOSED` |
| 5 | Lost HTTP response followed by client retry | Step 1 `idempotency` table `(actor_id, key)` + advisory try-lock + `event_id UNIQUE` replays stored response | `F14`, `I4`, `N2` | `CLOSED` |
| 6 | In-memory timer lost on server crash | Deadlines stored as durable PostgreSQL rows; stateless 2-phase poller re-claims after 5 s lease expiry | `F1`, `I1`, `T1` | `BOUNDED` |
| 7 | Client clock skew alters deadlines | Deadlines use server time only; `GREATEST(clock_timestamp(), head_ts)` enforces monotonicity; client skew logged | `F11`, `I16`, `T2/T3` | `BOUNDED` |
| 8 | Silent receiving facility stalls referral | Unified ACK window $A$ (rungs at $0, A/4, 3A/4$) + decision window $D$ escalates automatically | `F2`, `F3`, `I1` | `CLOSED` |
| 9 | Catchment chain exhausted | Transitions deterministically to `ESCALATED_TO_DISPATCHER` with `DISPATCH_ACTION` deadline; never invents a target | `F6`, `I7` | `CLOSED` |
| 10 | Parallel offers overload tertiary hospital | `SEQUENTIAL` is default; `PARALLEL2` capped at `open_offers <= 2`; `AT_CAPACITY` structured decline | `F13`, `I12`, `K3` | `BOUNDED` |
| 11 | Referral ping-pong loops ($A \rightarrow B \rightarrow A$) | `UNIQUE (referral_id, facility_id)` on `offer` prevents re-offering any previously targeted facility | `I9` | `CLOSED` |
| 12 | Receiver accepts to hit KPI, then delays bed | APOT `ARRIVED -> HANDED_OVER` metric tracked separately from `ACCEPTED`; `ARRIVAL_REJECTED` revokes lease | `D18`, `K2` | `BOUNDED` |
| 13 | Shared ward tablet spoofing | Roster check + registered device key + server-verified Argon2id PIN on every mutating action | `F7`, `I6`, `I1` | `CLOSED` |
| 14 | BOLA, mass-assignment, or role escalation | Object-level facility checks, Pydantic `extra='forbid'`, server-owned state columns, role matrix suite | `I6`, `I11` | `CLOSED` |
| 15 | Database admin edits or deletes `event` rows | `rhp_no_mutate()` triggers + SHA-256 chain + 5 s Ed25519 Merkle checkpoints on outside witnesses | `F8`, `I5`, `S1` | `BOUNDED` |
| 16 | Operator presents split-view history | Independent witnesses (big screen, judge phones, off-box log) compare signed checkpoint roots | `D10`, `I5`, `S2` | `BOUNDED` |
| 17 | Bot farm mints judge QR sessions | Rotating single-use QR (`jti` 20 s) + Cloudflare Turnstile + 20-desk admission cap + fail-closed LAN mode | `D11`, `N7` | `BOUNDED` |
| 18 | PHI leaked through third-party FCM push | FCM sends zero-payload wake ping only; Android app fetches ciphertext over authenticated HTTPS | `D13`, `I10`, `P3` | `CLOSED` |
| 19 | PHI leaked through DLT SMS | Static SMS alert template with short code (`<= 30` chars); zero clinical text | `P2` | `CLOSED` |
| 20 | Broken salt-deletion crypto-shredding | Per-referral AES-256-GCM DEK (`wrapped_dek = NULL`) + monthly KEK epoch destruction | `D9`, `P5` | `BOUNDED` |
| 21 | DPDP erasure vs. clinical retention conflict | `clinical_payload.expires_at` parameterized; metadata log is PHI-free (`rhp_detail_ok`); legal review scheduled | `F9`, `L2` | `OPEN` |
| 22 | AI hallucination enters clinical record | Cognitive Forcing Function (`423 ANCHOR_REQUIRED`), critical field re-entry, speed bump, `T3_EXTRAS` off by default | `A1`, `A2` | `BOUNDED` |
| 23 | AI confidence scores induce automation bias | Confidence scores and explanations are stripped from API and UI | `v8 §8`, `A1` | `CLOSED` |
| 24 | Countdown clocks distort clinical triage | Receiving desk displays priority queue without countdown timers; district analytics show aggregate capacity | `D18`, `§15` | `CLOSED` |
| 25 | Unlawful staff performance surveillance | DPDP s.7(i) prior written notice, data minimisation, strict siloing from HR records, post-pilot erasure | `D18`, `§10` | `OPEN` |
| 26 | Clinician double-entry burden (app + paper) | Printable ReferralHandshake card *is* the official referral slip with 9-char Crockford code | `D18`, `§8` | `CLOSED` |
| 27 | Unverified claims on pitch slides | Strict Claims Register (§19) + automated forbidden-phrase CI linter (`ST-5`) | `D5`, `L3` | `CLOSED` |
| 28 | AI coding agent edits spec/tests to pass CI | `/spec`, `db/schema.sql`, and `monitor/` locked via `CODEOWNERS` and CI SHA-256 hash pin | `v8 §7.1` | `CLOSED` |
| 29 | Formal model hides database lock races | 200-way `asyncio.Barrier` concurrency test + Toxiproxy + live differential monitor against real PostgreSQL | `T-C1`, `F1` | `CLOSED` |
| 30 | Server and runtime monitor share a bug | Person A writes server/YAML/Quint; Person B writes Python monitor from §3 prose alone; M1–M6 mutations | `F17`, `§12` | `CLOSED` |
| 31 | Venue Wi-Fi fails during live judge demo | Dual uplink (phone hotspot primary), LAN-QR fail-closed mode, pure-JS noble crypto, MP4 clips `A–D` | `D1`, `D4`, `N7` | `BOUNDED` |
| 32 | Urban canyon GPS drift triggers false arrival | 200 m + dwell geofence emits `ARRIVAL_SUGGESTED` only; human EMT or desk confirms `ARRIVED` | `D2`, `F5` | `CLOSED` |
| 33 | Missing OSM hospital tags / tile scraping ban | Curated district facility seed + commercial Mapbox SDK or self-hosted PMTiles | `D14`, `§9` | `CLOSED` |
| 34 | Stale capability attestation misleads routing | Attestations carry `attested_at` and `expires_at`; UI shows age and hides expired capabilities; live reconfirm (`I15`) | `D15`, `F12`, `I15` | `CLOSED` |
| 35 | Outdated duty roster phone number | Unanswered voice call falls through to next slot at $A/4 + i\cdot\delta$, then dispatcher proxy at $3A/4$ | `F2`, `§6` | `BOUNDED` |
| 36 | Rival brute-forces PIN to lock out hospital | Lockout counter scoped to `(session_id \| call_sid)`; rival session locks itself, leaving duty role active; 3rd strike pages dispatcher | `F7`, `I2`, `I3` | `CLOSED` |
| 37 | Hardcoded demo timers used with real patients | Signed profiles (`Ed25519`); `DEMO_FAST` and `DEMO_VOICE` refuse boot if `REAL_DATA=1` | `F2`, `I13` | `CLOSED` |
| 38 | Single database failure in district pilot | Managed Multi-AZ PostgreSQL with synchronous standby (60–120 s failover `[V*]`) + idempotent client retries | `T5`, `F2` | `BOUNDED` |
| 39 | Voicemail greeting auto-acknowledges voice call | Exotel AMD + mandatory "Press 1 to hear referral" keypad gate before `apply_command(ACK)` executes | `F7`, `I5` | `CLOSED` |
| 40 | revoked facility continues reading SSE stream | Per-event `payload_grant` check + 15 s heartbeat check + `GRANT_REVOKED` frame wipes client DOM | `F10`, `I10`, `P4` | `BOUNDED` |

---

## 11. Mandatory Claims Discipline & Forbidden Vocabulary (`§19`, `ST-5`)

Every pitch deck slide, README, UI banner, and judge Q&A response must adhere strictly to the following table. The CI self-audit test (`ST-5`) scans all repository files (excluding this table and `ReferralHandshake_FINAL_LOCKED_Architecture.md §19`) and fails the build if any forbidden phrase appears:

| Topic | Authorized, Evidence-Backed Wording | Forbidden Claim (Immediate Audit Failure) |
|---|---|---|
| **Epidemiological Framing** | "Referral communication and documentation gaps are documented in specific urban Indian studies (Das et al. 2023 in urban Maharashtra; Safdarjung Hospital 2018–2023 in Delhi) `[V]`." | "National prevalence", "lives saved", "deaths prevented", "reduces maternal mortality". |
| **Competitive Landscape** | "Hard single-owner leases and automatic inter-facility escalation ladders were not found in public documentation of the systems audited `[V*]`." | "First in the world", "only system", "no competitor has this". |
| **Formal Verification & Proof** | "Control-plane model checked within stated bounds ($F=3, \text{MAXE}=4$); implementation checked by conformance vectors, 200-way concurrency tests, mutation tests M1–M6, and a live independent runtime monitor." | "Mathematically proven system", "mathematically guaranteed", "mathematically impenetrable", "100% bug-free". |
| **System Reliability & Security** | "Every identified failure mode is `CLOSED` with a named test, `BOUNDED` with a stated residual and monitor alarm, or `OPEN` with an assigned owner." | "Bullet-proof", "airtight", "zero loopholes", "zero silent drops", "crash-proof", "immune to failure", "unhackable". |
| **Audit Log & Legal Admissibility** | "Tamper-evident SHA-256 hash chain with 5-second Ed25519 signed Merkle checkpoints held by independent witnesses; BSA s.63-ready export bundle." | "Immutable log", "blockchain-grade immutability", "legally conclusive", "BSA certified". |
| **Regulatory & Standards Alignment** | "Designed to comply with DPDP Act 2023; synthetic data only (`REAL_DATA=0`); NRCeS-aligned FHIR R4 export; 'ABDM-sandbox aligned' only if sandbox calls are executed." | "ABDM compliant", "DPDP certified", "production ready", "live integration with 108/ERSS". |
| **Operational Impact** | "Process improvement (reducing unanswered referrals and unannounced arrivals) is a hypothesis to be evaluated in an ethics-approved district pilot." | "Eliminates ping-pong", "guaranteed 3-second MTTR" (unless measured live in that exact run). |

---

## 12. Pre-Submission Self-Audit Gates (`ST-1` to `ST-5`)

No release or demo branch may be marked ready until these five automated self-audit checks pass in CI:
1. **`ST-1` (Lock Order & Deadlock Check):** Verify all SQL/Python write paths acquire locks strictly in `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox` order, `rhp_require_lock()` is active on all 6 contract tables, and `T-F1` (`lock_order_200way`) completes with `pg_stat_database.deadlocks` delta $= 0$.
2. **`ST-2` ($T_{max}$ & Voice Stagger Arithmetic):** Run `validate(profile, REAL_DATA)` across all 4 signed profiles (`PILOT_OB_CRITICAL`, `PILOT_STANDARD`, `DEMO_FAST`, `DEMO_VOICE`); verify $F \cdot (A + D + \epsilon) \le B$, $A/4 + (S-1)\delta + V \le 3A/4$, and hard boot refusal when `demo=True` and `REAL_DATA=1`.
3. **`ST-3` (24-Table DDL & Constraint Scan):** Load `db/schema.sql` into a clean PostgreSQL 16 instance; verify all 24 tables, deferred FK `referral_lease_fk`, partial unique index `one_lease`, deferred constraint trigger `i1_pending_deadline`, and role privilege revocations (`REVOKE UPDATE, DELETE ON event, checkpoint, rejected_command FROM rhp_app`) are present in `pg_catalog`.
4. **`ST-4` (Idempotency 8-Case Matrix):** Execute `T-F14` covering prior 200 replay, prior 409/412/422 replay, payload hash mismatch (`422`), concurrent in-flight duplicate (`409`), mid-transaction crash recovery, $> 48\text{ h}$ expired key with duplicate `event_id` (`409`), missing header (`422`), and reused `event_id` under a new key (`409`).
5. **`ST-5` (Forbidden Claims Linter):** Scan all Markdown, Python, TypeScript, and HTML templates for forbidden phrases from §11; exit non-zero on any match outside the explicit "Forbidden Claim" column.