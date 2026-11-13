# Project Context — ReferralHandshake (Protocol RHP-1)

**System:** Referral Handshake Protocol (RHP-1) & Reference Platform  
**Team:** MAHA YODHAS (2-Person Architecture & Engineering Team)  
**Event:** Colossus 3.0 — HealthTech Track (13–14 Nov 2026, Bengaluru; 24-hour build, 5-minute pitch with $\ge 30\text{ s}$ live demo `[V]`)  
**Data Posture:** Synthetic data only (`REAL_DATA=0`)  
**First Clinical Pathway:** Emergency obstetric referral across Karnataka-style tiers ($\text{PHC} \rightarrow \text{CHC} \rightarrow \text{FRU} \rightarrow \text{DH} \rightarrow \text{MC}$); data model generic across `OBSTETRIC_EMERGENCY`, `NEONATAL`, `TRAUMA`, `CARDIAC`, and `STROKE`.

---

## 0. Input Precedence Hierarchy & Tag Legend

### 0.1 Strict Input Precedence (Non-Negotiable)
Any ambiguity across project artifacts is resolved strictly in this order:
1. **`ReferralHandshake_LOCKED_Problem_Statement_v7.md`** — Highest authority on problem framing, empirical evidence tags, and claims discipline.
2. **Primary Research Findings Tagged `[V]`** — Verified facts embedded inside the locked documents.
3. **`ReferralHandshake_v8_LOCKED_Solution.md`** — Authority on D1–D20 defect closures, 28 conformance scenarios, 40-item loophole ledger, ideation scoring, and clinical operating model.
4. **`ReferralHandshake_FINAL_LOCKED_Architecture.md`** — Ultimate technical authority on F1–F20 architectural closures, invariants I1–I16, the 24-table PostgreSQL 16 DDL, the 10-step `apply_command()` pipeline, timing math, Quint specification, independent Python runtime monitor, and T0–T3 scope tiers.
5. **`ReferralHandshake_3Gem_Antigravity_Workflow.md`** — Authority on multi-agent build governance (`CONDUCTOR`, `AUDITOR`, `ADVERSARY`, Google Antigravity builder, `AGENTS.md`, and Lane A / Lane B separation).

### 0.2 Evidence & Weakness Status Tags
- **`[V]`** — Verified in primary research sources.
- **`[V*]`** — Verified only from a secondary, blog, law-firm, or vendor source; must be confirmed from primary text before appearing on a slide.
- **`[CONFLICT]`** — Research files or statutory drafts disagree; conservative bound or percentage-only citation rule applies.
- **`[GAP]`** — Nothing reliable found in the literature/law; parameterised in software and never claimed as fact.
- **`[verify]`** — Requires pre-event empirical verification via the §21 checklist.
- **`CLOSED`** — Architectural weakness eliminated by an explicit mechanism plus a named automated test.
- **`BOUNDED`** — Residual risk constrained to a stated technical bound with a live runtime monitor alarm.
- **`OPEN`** — Legal, operational, or hardware dependency assigned to a named owner with required closing evidence before real-world use.

---

## 1. Empirical Problem Context: The Referral Black Box

When an emergency patient requires care that the originating facility cannot provide, a referring clinician, an ambulance crew, and a receiving triage team must coordinate as one unit. Empirical audits in Indian urban and tertiary settings demonstrate that inter-facility handover is routinely an unconfirmed message rather than a bilateral commitment.

### 1.1 Empirical Evidence Register

| Finding | Setting & Sample | Status | Mandatory Citation Rule |
|---|---|---|---|
| Referring facility phoned the receiving facility in $47\%$ of referrals ($11,988$); $53\%$ had no phone contact prior to transfer | Urban Maharashtra, 2016–2019, $199,888$ deliveries (Das et al., 2023) | `[V]` | Quote percentages; denominator is $25,253$ in some reports and $28,020$ in others `[CONFLICT]` ($47\%$, $37\%$, $60\%$ reproduce only with $25,253$) |
| Only $37\%$ of referral slips were fully documented ($9,279$) | Same study (Das et al., 2023) | `[V]` | Quote percentage and study setting ("Urban Maharashtra, 2016–2019") |
| $60\%$ of referred women could be tracked at the higher facility; authors attribute the $40\%$ loss to incomplete documentation and demographic errors | Same study (Das et al., 2023) | `[V]` | Frame process improvement as a hypothesis to test in a pilot, never an established fact |
| $19\%$ of referrals were driven purely by missing resources; within that resource-driven group: no emergency OT ($47\%$), no NICU ($45\%$), no anaesthetist ($24\%$), no paediatrician ($22\%$) | Same study (Das et al., 2023) | `[V]` | Cite OT/NICU/anaesthetist/paediatrician shares strictly as proportions *within* the $19\%$ resource-driven group |
| $90.6\%$ of critically ill obstetric patients arrived with no prior communication; $70\%$ had no escort; referral slips were incomplete in $50\%$ | Safdarjung Hospital, Delhi, $3,220$ inter-facility referrals, 2018–2023 | `[V]` | Always qualify as "one tertiary obstetric ICU centre in Delhi" |
| $47.3\%$ of referred patients had visited $\ge 2$ hospitals before reaching the tertiary centre ("ping-pong"); authors link this to delay | Same audit (Safdarjung Hospital, 2018–2023) | `[V]` | Never claim the protocol "eliminates ping-pong"; state that it surfaces refusal earlier |
| Asynchronous digital referral handled $52\%$ of one hospital's gynaecology referrals by advice alone, but evaluation found delays when receivers did not respond because there was no mandated response time | Vula Mobile (South Africa) evaluation | `[V]` | Direct empirical justification for enforced `ACK` and `DECISION` deadlines |
| In Karnataka's 108 ambulance service, $44\%$ of dispatched calls were non-emergencies and $50\%$ of trauma responses missed the golden hour | CAG Audit of Karnataka 108 service | `[V*]` | Secondary citation; use only as operational background for 108 crew load |

### 1.2 Honest Empirical Limits
- **Scope of Studies:** Both primary Indian studies (Das et al., 2023; Safdarjung 2018–2023) are obstetric and urban, and the Delhi audit represents a single tertiary referral centre.
- **Unmeasured Quantities (`[GAP]`):** No national Indian prevalence of silent referrals, no measured ambulance-minutes lost to referral failure in India, and no clinical mortality effect of digital referral handshakes were found in the research.
- **Operational Positioning:** All project claims are strictly **operational and process-oriented** (handover reliability, documentation completeness, traceability, and time-to-acknowledgement), never clinical outcome or mortality claims.

### 1.3 Theoretical Framing: The Three Delays Model
The Three Delays model defines:
1. **First Delay:** Deciding to seek care.
2. **Second Delay:** Identifying and reaching an adequate medical facility `[V]`.
3. **Third Delay:** Receiving adequate and appropriate treatment at the facility `[V]`.

Academic literature classifies inter-facility referral-communication failure inconsistently across the second delay, the third delay, or a proposed "fourth delay" for administrative and digital barriers `[V*]`. **Locked Position:** Referral handover failure sits at the contested boundary between the **Second Delay** and the **Third Delay**. ReferralHandshake does not address the First Delay.

### 1.4 Existing Systems & The Protocol Gap
- **Policy Context:** The National Ambulance Services (NAS) Guidelines 2026 (29 June 2026) call for GIS mapping of medical facilities, visibility into bed availability and critical-care readiness, and command centres integrated toward ERSS 112 `[V]`. However, NAS 2026 states the desired operational outcome rather than specifying a deterministic inter-facility handover protocol.
- **Audited Systems:** Public documentation was audited across ABDM FHIR resources, eSanjeevani, NIC e-Hospital, Community Health Toolkit (CHT), DHIS2, OpenSRP, Pulsara, ReferralMD, and Epic Transfer Center `[V*]`.
- **Identified Gap:** Automatic two-level inter-facility timer escalation combined with a hard single-owner lease guarantee was **not found in public documentation of the systems audited** `[V*]`. Because closed proprietary systems and internal Karnataka state referral tools could not be inspected `[GAP]`, this gap is framed as a hypothesis to test with clinicians and 108 staff, using competitor-safe wording (*"not found in public documentation of the systems audited"*, never *"first"* or *"only"*).

---

## 2. Real-World Operating Model & Clinical Context

### 2.1 Duty-Role Addressing (Not Named Individuals)
In busy public hospitals (CHCs, FRUs, District Hospitals, Medical Colleges), individual clinicians change shifts and cannot be reliably targeted by personal accounts.
- **Duty Role Roster:** Facilities register **duty roles** (`NURSE`, `CMO`, `CONSULTANT`, `CLINICIAN`, `EMT`, `DISPATCHER`, `ADMIN`, `JUDGE_DESK`) with slot numbers (`slot_no`), registered phone numbers (`phone_e164`), device public keys, and salted Argon2id PIN hashes.
- **Concurrent Slot Notification (F2, F3):** When an offer opens at a facility, all active rostered slots at that facility are notified concurrently at $t = 0$ via SSE/FCM, followed by staggered outbound Exotel voice calls at $t = A/4 + i \cdot \delta$ ($i \in \{0, \dots, S-1\}$) and a dispatcher proxy page at $t = 3A/4$ inside the unified acknowledgement window $A$.

### 2.2 Receiver Incentive Model & Anti-Goodhart Protections
Why would a busy casualty medical officer or duty nurse respond to a digital offer? (Framed as **hypotheses to test in expert interviews and a shadow-mode pilot**, not established facts):
1. **Every Structured Answer is Legitimate:** `ACCEPT`, `COUNTER`, and `DECLINE` (with a structured missing-resource reason such as no OT, no blood, no anaesthetist, or `AT_CAPACITY`) are all valid, timestamped clinical actions. **Silence is the only unrecorded outcome, and only silence triggers automated escalation.**
2. **Advance Notice & Redirects:** Responding gives the casualty team advance warning (plus pre-referral $\text{MgSO}_4$ status and ETA) instead of an unannounced arrival at the door, and allows a facility to suggest an alternative destination on decline.
3. **No Countdown Clocks on Receiving Desks (`[V]`):** Empirical studies of the Manchester Triage System (MTS) showed that displaying countdown target clocks to clinicians distorted clinical priority decisions. Receiving desks in ReferralHandshake display an ordered priority queue with no countdown timers.
4. **Separate Arrival-to-Handover (APOT) Metric:** To prevent "accept to hit the KPI, then stall the patient at the door without a bed," the system measures `ARRIVED -> HANDED_OVER` separately from `OFFERED -> ACCEPTED` and flags `ARRIVAL_REJECTED` events.
5. **District-Level Capacity Framing:** Dashboards aggregate declines and timeouts at the facility and district level as **resource-capacity signals** for health administrators (e.g., showing where an FRU lacks an anaesthetist on night shifts), never as individual staff blame.
6. **Honest Capacity Limit:** ReferralHandshake **does not create hospital beds, OTs, or specialists**. When every facility in a catchment chain is full, the protocol surfaces that refusal earlier—before the ambulance drives blindly from door to door—and routes the case to a human dispatcher (`ESCALATED_TO_DISPATCHER`).

### 2.3 Clinical Payload & Pre-Referral Intervention Safety (Fixing Defect D1)
- **ISBAR + Dakshata Structure:** The clinical card captures structured ISBAR fields alongside Dakshata obstetric pre-referral fields (specifically $\text{MgSO}_4$ loading dose—typically $14\text{ g}$ Pritchard regimen—and oxytocin administration).
- **Never Block Care on Missing Clinical History (D1 Closure):** Earlier drafts proposed rejecting `CREATE` if $\text{MgSO}_4$ dose/time were omitted. That violated Promise 3 (*Never block care*) because a referring worker may not know what was administered prior to arrival. In RHP-1, `mgso4_status` is **answer-required, never knowledge-required** (`GIVEN | NONE_GIVEN | UNKNOWN`). Selecting `UNKNOWN` permits immediate referral creation and ambulance dispatch while rendering a high-visibility red banner (`"Pre-referral MgSO4 dose UNKNOWN — verify before dosing"`) on the receiving desk to prevent double-dosing toxicity.
- **No Double-Entry Burden:** The referral card generated by ReferralHandshake prints directly as the physical inter-facility referral slip carrying a 9-character Crockford Base32 paper code (`8 payload chars + 1 mod-37 check char`) and QR code. Clinicians enter data once.

---

## 3. Architectural Context, Coherence Rule & Defect Closures

### 3.1 The Coherence Rule
To prevent scope creep during a 24-hour build, every component in ReferralHandshake must be strictly one of:
- **(a) A state or event in the contract** (authoritative state machine in PostgreSQL 16),
- **(b) An interface that produces or consumes those events** (PWA desks, Kotlin Android app, Exotel voice IVR, DLT SMS, Paper code, Dispatcher proxy), or
- **(c) A read-only projection of the committed event log** (Independent Python runtime monitor, Witness/signer, Pure-JS browser verifier, Command centre map/KPIs, FHIR R4 / IEEE 1849 XES exporters).

Anything that does not fit (a), (b), or (c) is out of scope.

### 3.2 Locked Technology Stack vs. Banned Technologies

| Architectural Layer | Locked Choice | Rationale & Constraints |
|---|---|---|
| **Contract Database** | PostgreSQL 16 (single writable primary, `synchronous_commit=on`, `READ COMMITTED`) | Per-referral `SELECT ... FOR UPDATE` row locking, `FOR UPDATE SKIP LOCKED` durable timers/outbox, partial unique index `one_lease`, deferrable constraint triggers. Row locks never run on hot standbys. |
| **Command API & Workers** | Python 3.12, FastAPI, `psycopg3`, Pydantic (`extra='forbid'`) | Deterministic 10-step `apply_command()` pipeline, stateless 2-phase timer poller, stateless outbox relay. |
| **Web Desks & Console** | React PWA + Server-Sent Events (SSE) over HTTP/2 (`Last-Event-ID`, $15\text{ s}$ heartbeats) | Zero-install QR join for judges; pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256` for client-side verification even on iOS Safari / LAN HTTP where WebCrypto is unavailable `[V]`. |
| **Ambulance Client** | Native Android (Kotlin, `FOREGROUND_SERVICE_TYPE_LOCATION`, `FusedLocationProviderClient`, Room outbox, empty-payload FCM wake) in T3; PWA GPS fallback in T1 | Deterministic background location on Android; $200\text{ m}$ geofence + dwell emits `ARRIVAL_SUGGESTED` only (human confirms `ARRIVED`). |
| **Telephony Reach** | Outbound-only Exotel IVR ($\le 10$ whitelisted trial numbers; HTTP 200 within $5\text{ s}$ `[V]`, internal budget $2\text{ s}$) + DLT SMS ($\le 30\text{ char}$ variables `[V]`) | Reaches feature phones with AMD + mandatory `Press 1` human gate, pre-recorded Kannada/Hindi/English prompts, and DTMF PIN entry. |
| **Maps & Routing** | Mapbox Directions & `mapbox/driving` Matrix ($25$ coords, $60\text{ req/min}$; `driving-traffic` $10$ coords, $30\text{ req/min}$ `[V]`) | Server-side cached ETAs ($120\text{ s}$ TTL) for active referral top candidates only; avoids OSM tile bulk-download policy violations. |
| **Formal Spec & Runtime Proof** | Quint (`rhp1.qnt`, Person A) + Independent Python Monitor (Person B) + Toxiproxy + `asyncio.Barrier(200)` | Bounded model checking of control plane ($F=3, E=4$), common-mode independence across teammates, live differential checking. |
| **Explicitly Banned** | **Blockchain, Kafka, Debezium, Redis, Kubernetes, WebSockets, WhatsApp, On-device LLMs, CRDTs for authoritative state, JSON floats** | Eliminated due to latency, operational complexity, health-data privacy exclusions (WhatsApp), concurrency hazards, or JCS canonicalization ambiguity. |

### 3.3 Summary of D1–D20 Closures (Solution v8) & F1–F20 Closures (Final Architecture)

| Closure ID | Defect in Earlier Drafts | Locked Architectural Resolution |
|---|---|---|
| **D1 / K1** | Hard-rejecting `CREATE` without $\text{MgSO}_4$ dose/time blocked care | `mgso4_status` (`GIVEN \| NONE_GIVEN \| UNKNOWN`) is answer-required; `UNKNOWN` triggers a red desk banner and never blocks dispatch |
| **D2 / F5** | No transport track; geofence auto-triggered `ARRIVED` | Parallel `tr_state` track (`I3`); $200\text{ m}$ geofence emits `ARRIVAL_SUGGESTED` only; human confirms `ARRIVED`; 6 arrival cases `(a)–(f)` |
| **D7 / F13** | Conflated row `version` and `lease_epoch`; undefined open-offer cap | `version` ($412$ on stale) separated from `lease_epoch` ($409$ on lost race); `open_offers` CHECK $0..2$ (`I12`); `SOFT_OPEN` late-accept rule |
| **D8 / F4** | SQLite single-writer / incomplete schema | PostgreSQL 16 primary (`synchronous_commit=on`) with complete 24-table DDL, `one_lease` partial unique index, and append-only triggers |
| **F1 / I14** | Poller held `deadline` lock while locking `referral` (deadlock hazard) | Global lock order `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`; 2-phase poller; DB trigger `rhp_require_lock` |
| **F2 / F3 / I13** | Notice ladder raced `ACK` timer; $T_{max}$ double-counted slots | Notice rungs at $0, A/4, 3A/4$ inside $A$; slots notified concurrently; $T_{max} = F \cdot (A + D + \epsilon) \le B$ enforced at boot |
| **F6** | Referrals could stall unclosed after `HANDED_OVER` | Reachability & Exit table; 9-outcome taxonomy; two-stage `CLOSURE` deadline auto-closes as `UNKNOWN_COUNTER_REFERRAL` (`proxy=true`) |
| **F7** | Rival could lock out a facility's duty role by spamming wrong PINs; voicemail counted as `ACK` | Argon2id failure counter in autonomous txn; lockout scoped per `(session_id \| call_sid)`; outbound IVR AMD + mandatory `Press 1` gate |
| **F8** | Backup restore indistinguishable from log truncation tamper | Separate-OS-user Ed25519 witness signer (`rhp-sign`); binary Merkle tree checkpoints every $5\text{ s}$; cold-key signed `RESTORE` checkpoint |
| **F9 / I11** | Free-text `event.detail` risked leaking PHI into the audit log | Per-type key allowlist (`rhp_allowed`) + regex value check (`rhp_detail_ok`); $4\text{ h}$ time buckets and $k \ge 5$ cell suppression on exports |
| **F10 / I10** | SSE streams continued streaming clinical data after offer decline/supersede | Per-event `payload_grant` filter at emit time + `15 s` heartbeat re-check + `GRANT_REVOKED` control frame + DOM state wipe |
| **F11 / I16** | Host clock step backward could break event timestamp monotonicity | `ts = GREATEST(clock_timestamp(), referral.head_ts)` under referral lock; chrony slew-only; $> 2\text{ s}$ NTP offset alarm |
| **F12 / I15** | Offline queued `ACCEPT` replayed hours later with stale capability checks | `offer_resource_confirmation.expires_at` checked at `server_ts`; returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` |
| **F14** | Ambiguous retry behavior on domain rejections or in-flight duplicates | Step 1 idempotency (`pg_try_advisory_xact_lock`, `(actor_id, key)` PK, `SAVEPOINT sp_cmd` stores $409/412/422$ rejections) |
| **F17** | Common-mode bug between server transition table and runtime monitor | Person A writes backend + `transitions.yaml` + Quint spec; Person B writes Python monitor from §3 prose alone; 6 mutation tests (`M1–M6`) |
| **F18** | Conflicting pilot cloud cost figures across reports ($\$810$ vs $\$900\text{--}1,000$ vs $\$1,000\text{--}1,500$) | Reconciled into a single itemised AWS `ap-south-1` Multi-AZ table ($\approx \$1,419$ over 6 months) |
| **F19** | Implicit mapping between v7 states and implementation tables | Explicit 12-state mapping table across `referral.hs_state`, `offer.status`, `referral.tr_state`, and `event.type` |
| **F20** | `BROKEN_BUILD=1` risked corrupting primary DB or running on real data | Isolated `rhp_scratch_broken` DB without `one_lease`; hard `exit(78)` abort if `REAL_DATA=1` or main DB reachable; flashing red banner |

---

## 4. Indian Regulatory, Privacy & Security Context

### 4.1 Indian Statutory & Standards Posture (`REAL_DATA=0` in Prototype)
ReferralHandshake holds a **short-lived handover record**, not a longitudinal electronic health record. All regulatory controls are framed as *"designed to comply"* for future pilot evaluation under legal review.

| Statute / Guideline | Technical & Operational Posture | Status |
|---|---|---|
| **DPDP Act 2023 & DPDP Rules 2025** | Rules commencement cited as 13 Nov 2025 vs Gazette 14 Nov 2025 `[CONFLICT]`; core obligations apply from 13/14 May 2027 `[V]`. Emergency processing without consent relies narrowly on s.7(f) (some drafts cite s.7(d) `[CONFLICT]`) with logged emergency basis. Staff telemetry under s.7(i) requires prior written notice, data minimisation, strict siloing from HR performance records, and erasure after evaluation. Safeguard breach ceiling up to ₹250 Cr (s.8(5)); breach notification ceiling up to ₹200 Cr with $72\text{ h}$ detailed report to DPBI (s.8(6)). Interplay between s.8(7) erasure and NMC 3-year retention for handover records is unsettled `[GAP]` and parameterised. | `OPEN` (Legal review before real data) |
| **Bharatiya Sakshya Adhiniyam (BSA) 2023 s.63** | System generates an export bundle containing the RFC 8785 JCS canonical event log, per-file SHA-256 digests, bundle SHA-256 root, and pre-filled Part A (custodian) and Part B (expert) certificate templates citing the hash. **Never claimed as "BSA certified".** | `BOUNDED` |
| **CERT-In Directions 2022** | $6\text{ h}$ incident reporting runbook; $180\text{ d}$ rolling audit logs retained in India; host clocks synchronised via chrony slew-only to NIC/NPL NTP stratum sources `[V]`. | `BOUNDED` |
| **TRAI TCCCPR / DLT Rules** | SMS carries static template text only (`"RHP alert: new referral. Open {#var#}"`), variable $\le 30\text{ chars}$, pre-tagged whitelisted static domain, zero clinical text `[V]`. Outbound voice uses provider sandbox / $\le 10$ whitelisted numbers; legality of automated clinical voice calls is unsettled `[GAP]`. WhatsApp is strictly excluded for health data. | `CLOSED` (SMS) / `OPEN` (Voice legality) |
| **ABDM / HDMP & NRCeS FHIR R4** | No longitudinal record fetch (an unconscious emergency patient cannot grant M3 consent, and emergency consent overrides are unverified `[GAP]`). Summary is clinician-authored at point of care. Export is FHIR R4-shaped (`ServiceRequest`, `Task`, `Encounter`, `Communication`) using a curated code subset. Claim *"ABDM-sandbox aligned"* only if sandbox calls are executed; **never claim "ABDM compliant"**. | `BOUNDED` |
| **ICMR 2017 & ICMR 2023 AI Guidelines** | Any shadow-mode district pilot tracking staff behaviour requires Ethics Committee review (full committee review if identifiable data of pregnant women are involved or if the system influences clinical decisions). Mandatory human-in-the-loop override for any AI feature. | `OPEN` (Pilot ethics approval) |

---

## 5. Claims Discipline, Loophole Ledger & Residual Risks

### 5.1 Mandatory Claims Register (§19)

| Authorized Wording (Permitted in Docs, UI & Pitch) | Forbidden Claim (Strictly Prohibited) |
|---|---|
| Referral communication and documentation gaps are documented in specific urban Indian studies (Das et al., 2023; Safdarjung 2018–2023) | National prevalence; "lives saved"; "deaths prevented" |
| Hard single-owner guarantees and automatic inter-facility timer escalation were not found in public documentation of the systems audited | "First", "only", "no competitor has this" |
| Designed to comply; ABDM-sandbox aligned (only if sandbox calls are made); synthetic data only (`REAL_DATA=0`) | "ABDM compliant"; "production ready" |
| Every identified weakness is `CLOSED`, `BOUNDED` with a stated residual, or `OPEN` with an owner | "Bullet-proof", "airtight", "zero loopholes", "guaranteed", "immune", "crash-proof" |
| Control-plane model checked within stated bounds ($3$ facilities, $4$ epochs); code checked by conformance vectors, concurrency tests, and a live independent monitor | "Mathematically proven system"; "mathematically impenetrable" |
| Tamper-evident log with independent witnesses; BSA s.63-ready export bundle | "Immutable log"; "BSA certified" |
| Escalation and capacity signalling are process hypotheses for an ethics-approved pilot | "Eliminates ping-pong"; measured ambulance time saved |

### 5.2 Complete 40-Item Loophole Ledger (v8 §16 → Final Architecture Traceability)

| # | Identified Loophole | Architectural Closure / Bounded Residual |
|---|---|---|
| 1 | Blocking care through mandatory clinical fields | `mgso4_status` is answer-required (`GIVEN \| NONE_GIVEN \| UNKNOWN`); never blocks dispatch (`D1`, `I3`) |
| 2 | Ambulance held until handshake completes | Independent `tr_state` transport track accepted in all non-terminal `hs_state` (`I3`) |
| 3 | Double lease granted under concurrent clicks | Per-referral `SELECT ... FOR UPDATE` + `one_lease` partial unique index + `lease_epoch` (`I2`) |
| 4 | Zombie write from delayed / reconnecting device | `expected_version` / `expected_epoch` checked in Step 5; rejected with `412` and logged in `rejected_command` (`I8`) |
| 5 | Lost HTTP response followed by client retry | Step 1 idempotency table (`(actor_id, key)` PK) + `event.event_id UNIQUE` (`F14`, `I4`) |
| 6 | In-memory timer lost on API process crash | Deadlines stored as durable PostgreSQL rows; stateless 2-phase poller claims via `SKIP LOCKED` (`F1`, `I1`) |
| 7 | Client clock skew alters escalation deadlines | Server time `GREATEST(clock_timestamp(), referral.head_ts)` is sole deadline authority; `client_ts_ms` recorded only (`F11`, `I16`) |
| 8 | Silent receiving facility stalls referral | Unified ACK window $A$ with rungs at $0, A/4, 3A/4$ + decision window $D$ + automatic ladder progression (`F2`, `I1`) |
| 9 | Pre-approved escalation chain exhausted | Transitions deterministically to `ESCALATED_TO_DISPATCHER` with `DISPATCH_ACTION` deadline; never invents a target (`I7`) |
| 10 | Tertiary hospital funnelling / overload | `SEQUENTIAL` mode is default; `AT_CAPACITY` structured decline; catchment chain order (`K3`) |
| 11 | Referral loops ($A \rightarrow B \rightarrow A$) | `UNIQUE (referral_id, facility_id)` constraint on `offer` table (`I9`) |
| 12 | Accept-then-no-bed KPI gaming | APOT `ARRIVED -> HANDED_OVER` measured separately from `ACCEPTED`; `ARRIVAL_REJECTED` revokes lease (`K2`) |
| 13 | Shared-tablet spoofing at hospital desk | Rostered slot + registered device pubkey + server-verified Argon2id PIN on every mutating action (`F7`, `I6`) |
| 14 | BOLA / mass-assignment / function-level abuse | Object-level facility checks, Pydantic `extra='forbid'`, server-owned state transitions (`I6`) |
| 15 | Database log tampering by sysadmin | Per-referral SHA-256 JCS hash chain + $5\text{ s}$ Ed25519 Merkle checkpoints (`F8`, `I5`) |
| 16 | Split-view history attack by operator | Signed checkpoints broadcast to independent witnesses (big screen, judge phones, off-box log) (`S2`) |
| 17 | Bot minting QR judge tokens | Rotating single-use QR (`jti`, $20\text{ s}$ TTL) + Cloudflare Turnstile challenge + 20-desk cap + LAN fail-closed mode (`§9`) |
| 18 | PHI leaked over third-party FCM push | Empty-payload FCM wake ping followed by authenticated HTTPS fetch (`P3`, `I10`) |
| 19 | PHI leaked in DLT SMS | Static template alert + short link only; zero clinical text (`P2`) |
| 20 | Broken salt-deletion "crypto-shredding" | Envelope encryption: per-referral AES-256-GCM DEK wrapped by monthly KEK; DEK zeroed + KEK epoch destroyed (`§10`) |
| 21 | DPDP erasure vs medical record retention conflict | Handover payload shredded on expiry; metadata log PHI-free; retention parameterised for legal review (`L2`) |
| 22 | AI hallucination reaches clinical record | Cognitive Forcing Function (`423 ANCHOR_REQUIRED` until anchors committed); critical fields re-entered; AI optional (`A1`, `A2`) |
| 23 | Automation bias from AI confidence scores | Confidence scores and LLM explanations are never displayed (`§16`) |
| 24 | Goodhart gaming via countdown clocks | Receiving desks show priority queue without countdown timers; district metrics framed as capacity signals (`§15`) |
| 25 | Unlawful staff performance surveillance | DPDP s.7(i) prior written notice, data minimisation, strict siloing from HR records, scheduled erasure (`§10`) |
| 26 | Double-entry burden on referring clinician | Printed ReferralHandshake card *is* the physical referral slip with Crockford Base32 paper code (`§8`) |
| 27 | Overclaiming in hackathon pitch | Enforced Claims Register (§19) + automated forbidden-word lint scan (`ST-5`) |
| 28 | Spec/code drift or AI "fixing" tests to pass | `CODEOWNERS` lock on `spec/`, `db/schema.sql`, and `monitor/`; hash-pinned in CI |
| 29 | False atomicity in model checking | Real 200-way `asyncio.Barrier` concurrency test (`T-C1`) + Toxiproxy chaos against PostgreSQL 16 |
| 30 | Monitor and server share a common-mode bug | Person A writes server/Quint; Person B writes monitor from §3 prose alone; verified by 6 mutation tests `M1–M6` (`F17`) |
| 31 | Venue Wi-Fi failure during live demo | Local-first Docker stack on laptop hotspot + LAN QR mode + pre-recorded MP4 fallback clips A–D (`F16`, `D4`) |
| 32 | Budget-phone GPS error mis-triggers arrival | $200\text{ m}$ geofence + dwell emits `ARRIVAL_SUGGESTED` only; EMT or receiving desk must confirm `ARRIVED` (`F5`) |
| 33 | OSM capability tag sparsity / tile policy | Curated Karnataka facility directory + commercial Mapbox SDK / self-hosted PMTiles (`§9`) |
| 34 | Stale capability attestations | Attestations displayed with age and hard `expires_at`; never presented as "live beds" (`§14`) |
| 35 | Outdated duty roster phone number | Concurrent multi-slot notification + voice stagger + $3A/4$ dispatcher proxy page (`F2`) |
| 36 | PIN brute-force / rival lockout DoS | Argon2id in autonomous transaction; lockout scoped to `(session_id \| call_sid)`, never locking out the whole facility (`F7`) |
| 37 | Unsafe hardcoded escalation timers | Signed write-once profiles with boot-time $T_{max} = F \cdot (A + D + \epsilon) \le B$ validator; demo profiles refuse `REAL_DATA=1` (`F2`, `F3`) |
| 38 | Single DB host failure in district pilot | AWS Multi-AZ synchronous standby + nightly logical backup + WAL archive + cold-key signed `RESTORE` protocol (`F8`) |
| 39 | Vibe-coded concurrency defects | Spec-first workflow (3-Gem + Antigravity ring) + `rhp_require_lock` trigger (`I14`) + `race200` gate |
| 40 | Unsettled legal status of automated voice | Outbound-only to $\le 10$ whitelisted trial numbers with synthetic de-identified prompts; `OPEN` for legal review (`L1`) |

### 5.3 Ranked Residual-Risk Register (Architecture §20)

| Rank | Risk Item | Status | Owner | Technical / Operational Mitigation | Required Closing Evidence |
|---|---|---|---|---|---|
| 1 | Voice call legality unsettled (`L1`) | `OPEN` | Legal Advisor | Sandbox, synthetic de-identified text, team's own whitelisted numbers | Written legal opinion prior to any real-world deployment |
| 2 | Retention vs erasure interplay (`L2`, NMC/DPDP) | `OPEN` | Legal Advisor | Parameterised `clinical_payload.expires_at` and KEK epoch destruction | Counsel's written reading of DPDP s.8(7) for handover records |
| 3 | Witness signer key theft (`S3`) | `OPEN` | Person A (`T1`) | Separate OS user `rhp-sign` (`0400` key), cold-key rotation drill | Cloud HSM / KMS integration in pilot + signed rotation drill log |
| 4 | Clinician & receiver adoption incentives | `OPEN` | Person B (`T2`) | Capacity-signal framing, zero countdown clocks, APOT separation | $\ge 3$ structured interviews (clinician, 108 crew, district coordinator) |
| 5 | No physical hospital capacity created | `BOUNDED` | District Admin | Earlier refusal discovery + `ESCALATED_TO_DISPATCHER` + bottleneck logs | Pilot district bottleneck aggregation report |
| 6 | Host clock step bounds (`T2`/`T3`) | `BOUNDED` | Person A (`T1`) | `GREATEST(clock_timestamp(), head_ts)`, chrony slew-only, $> 2\text{ s}$ alarm | NTP fault-injection test report (`T-F11`) |
| 7 | AI draft rubber-stamping (`A1`) | `BOUNDED` | Person B (`T2`) | Cognitive Forcing Function (`423 ANCHOR_REQUIRED`), AI off by default | 20-slip seeded-error usability gate ($\le 5\%$ rubber-stamp, $\le 1\%$ omission) |
| 8 | Android OEM battery-saver kills (`F4`) | `BOUNDED` | Person B (`T2`) | Foreground service + heartbeat staleness alert + PWA manual GPS fallback | 2-hour screen-off device soak test |
| 9 | Low-volume facility re-identification (`P1`/`P6`) | `BOUNDED` | Person A (`T1`) | Closed enum allowlist `rhp_detail_ok` + $4\text{ h}$ buckets + $k \ge 5$ suppression | Fuzz test `T-F9` + export anonymisation audit |
| 10 | AI-generated concurrency defects | `BOUNDED` | Both (`T1` & `T2`) | Spec-first 3-Gem ring, `M1–M6` mutation suite, independent Python monitor | Green `T-C1 race200` and `M1–M6` in CI |