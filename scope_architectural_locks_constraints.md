# ReferralHandshake (Protocol RHP-1) — Scope, Architectural Locks & Constraints

**System:** Referral Handshake Protocol (RHP-1) & Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0  
**Authority:** Derived strictly from `ReferralHandshake_LOCKED_Problem_Statement_v7.md`, `ReferralHandshake_v8_LOCKED_Solution.md`, `ReferralHandshake_FINAL_LOCKED_Architecture.md`, and `ReferralHandshake_3Gem_Antigravity_Workflow.md`.

---

## 1. Scope Boundaries, Tier Cut Order & Honest Limits

### 1.1 The Coherence Rule (In-Scope vs. Out-of-Scope)
Every module, table, endpoint, and UI screen in ReferralHandshake must be:
1. **(a)** A state or event in the RHP-1 contract,
2. **(b)** An interface that produces or consumes those contract events, or
3. **(c)** A read-only projection of the committed event log.

**Strictly Out of Scope:**
- Longitudinal electronic health record (EHR/EMR) storage or fetching patient histories via ABDM M3 consent (an unconscious emergency patient cannot grant consent, and emergency consent overrides in ABDM are unverified `[GAP]`).
- Automated clinical triage, diagnosis, or autonomous AI routing of ambulances.
- Creating physical hospital capacity (beds, OTs, ventilators, blood units, or staff).
- Addressing the "First Delay" (patient/family decision to seek care at home).
- Unverified "live bed marketplace" claims (all capability attestations are staff self-reports displayed with explicit age timestamps and expiry).

### 1.2 Feature-Flagged Build Tiers (`T0`–`T3`) & Mandatory Cut Order (`F16`)
To guarantee a working, verifiable system within a 24-hour, 2-person build window, all work is partitioned into four tiers behind environment feature flags. If any step fails $3$ fix loops or falls behind the hour schedule, scope is cut strictly from the bottom (`T3` first, then `T2`, then `T1`; **`T0` is never cut**):

| Tier | Feature Flag | Exact Scope Included | Cut Priority |
|---|---|---|---|
| **`T0`** | Always On | FastAPI `apply_command()` (10 steps), PostgreSQL 16 (24 tables, `synchronous_commit=on`), 2-phase Poller, Outbox Relay, React PWA Desks with rotating QR + Turnstile admission, Independent Python Runtime Monitor (`rhp_monitor`), Ed25519 Witness/Signer (`rhp_witness`) + Pure-JS Browser Verifier, `BROKEN_BUILD` scratch DB (`rhp_scratch_broken`) | **Never Cut (MVP Core)** |
| **`T1`** | `T1_TRANSPORT=1` | PWA Ambulance client (foreground GPS `watchPosition` + manual update), Dispatcher Console + proxy entry (`proxy=true`), Time-scrubber Event Replay UI | Cut 3rd |
| **`T2`** | `T2_REACH=1` | Outbound Exotel Voice IVR (AMD + Press-1 gate + native Kannada/Hindi/English audio + `%23` PIN), DLT-compliant static SMS stub/sandbox, 9-character Crockford Base32 (`mod 37`) paper code entry & printable slip | Cut 2nd |
| **`T3`** | `T3_EXTRAS=1` | Native Android Kotlin app (`FOREGROUND_SERVICE_TYPE_LOCATION` + Room outbox + empty-payload FCM), AI Intake Accelerator with Cognitive Forcing Function (`423 ANCHOR_REQUIRED`), NRCeS-aligned FHIR R4 export + IEEE 1849 XES export + `networkx` centrality graph | Cut 1st |

### 1.3 Pre-Event vs. At-Event Work Boundary & H22 Code Freeze
- **Phase P — Pre-Event Permitted Artifacts (Documents & Specifications Only `[verify]`):** Locked specification markdown files, `transitions.yaml`, Quint formal specification (`rhp1.qnt`), 24-table PostgreSQL DDL (`db/schema.sql`), conformance test vectors, signed profile JSON (`profiles.json`), Exotel number whitelist, bundled pure-JS `@noble` crypto packages, synthetic seed data (`REAL_DATA=0`), and fallback MP4 recording scripts.
- **Phase E — At-Event Build (`H0`–`H22`):** All application code (`api/`, `monitor/`, `witness/`, `pwa/`, `android/`) built against the frozen specifications.
- **Hour 22 Hard Code Freeze (`H22`–`H24`):** At Hour 22, all application code is frozen and git-tagged. Only `.env` configuration adjustments, rehearsal runs, and fallback MP4 recordings are permitted in the final 2 hours.

---

## 2. Locked Technology Stack & Banned Technology Ledger

### 2.1 Locked Technology Stack (`FINAL §0`)

| Architectural Layer | Locked Technology & Configuration | Rationale |
|---|---|---|
| **Database** | **PostgreSQL 16**, single writable primary, `synchronous_commit=on`, `READ COMMITTED` isolation + explicit `SELECT ... FOR UPDATE` and `FOR UPDATE SKIP LOCKED` | Row-level per-referral locking (`I14`), durable timer queues, atomic same-transaction event + outbox writes, zero cross-referral serialization bottleneck. |
| **Backend API & Workers** | **Python 3.12**, **FastAPI**, **psycopg3** (synchronous/async connection pool), **Pydantic v2** (`extra='forbid'`), **Argon2id** (`argon2-cffi`) | Strict schema validation, explicit transaction control (`SAVEPOINT sp_cmd`), deterministic lock ordering. |
| **Web Clients** | **React PWA**, **Server-Sent Events (SSE)** over HTTP/2 with `Last-Event-ID` resume and $15\text{ s}$ heartbeats, bundled pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256` | Zero-install QR join for judges; SSE traverses hospital proxies cleanly; pure-JS noble crypto works on iOS Safari and LAN HTTP where `crypto.subtle` Ed25519 is unavailable `[V]`. |
| **Mobile Client** | **Native Android (Kotlin)** (`T3`) with `FOREGROUND_SERVICE_TYPE_LOCATION`, `FusedLocationProviderClient`, Room outbox, WorkManager, empty-payload FCM wake; **PWA GPS fallback** (`T1`) | Deterministic background location on Android; safe PWA fallback for the 24-hour demo. |
| **Voice & SMS Reach** | **Exotel Outbound IVR** ($\le 10$ whitelisted numbers in trial; HTTP 200 webhook within $5\text{ s}$ `[V]`, internal budget $2\text{ s}$); **DLT Static SMS** ($\le 30\text{ char}$ variable) | Reaches basic feature phones without apps or internet; prevents silent SMS drops and voicemail false-ACKs. |
| **Maps & Routing** | **Mapbox Directions & Matrix API** (`mapbox/driving`: $25$ coords, $60\text{ req/min}$; `driving-traffic`: $10$ coords, $30\text{ req/min}$ `[V]`), server-side cached ($120\text{ s}$ TTL) | Respects OSM tile-server bulk-download policy; bounds API quota consumption to top candidates of active referrals. |
| **Formal & Runtime Proof** | **Quint** (`rhp1.qnt`, Person A), **Independent Python Runtime Monitor** (`psycopg3` `REPEATABLE READ READ ONLY`, Person B), **Hypothesis**, **Toxiproxy** | True common-mode independence (`F17`) without requiring a fragile stage JVM stream engine. |

### 2.2 Strictly Banned Technologies (Zero-Tolerance Constraint)

| Banned Technology | Architectural Reason for Prohibition |
|---|---|
| **Blockchain / Smart Contracts** | Adds latency, gas/consensus overhead, and operational complexity over a SHA-256 hash chain + Ed25519 signed Merkle checkpoints with independent witnesses (`v8 §1.3`, `§14`). |
| **Kafka / Debezium / RabbitMQ** | Over-engineered for a district deployment; PostgreSQL same-transaction `outbox` table with a `FOR UPDATE SKIP LOCKED` polling relay provides at-least-once delivery with zero external broker dependencies (`v8 §3`). |
| **Redis / Shared In-Memory Cache** | Violates crypto-shredding guarantees (decrypted PHI in cache tiers) and introduces split-brain state outside PostgreSQL transactional locks (`FINAL §0`, `§10`). |
| **SQLite for Contract State** | SQLite WAL `synchronous=NORMAL` can lose commits on power loss, serializes unrelated referrals on a single writer lock, and lacks `FOR UPDATE SKIP LOCKED` (`v8 D8`, `Appendix A`). |
| **Kubernetes (EKS/GKE)** | Over-engineered and cost-prohibitive for a 2-person team and single-district pilot; `docker-compose` (demo) and managed Multi-AZ Postgres + 2 small VMs (pilot) are locked (`v8 §3`, `§12`). |
| **WebSockets** | Replaced by unidirectional HTTP/2 `SSE` (`Last-Event-ID`) for server push + standard idempotent HTTP `POST` for commands (`v8 §3`). |
| **WhatsApp** | Strictly excluded for clinical/health handover data due to third-party metadata/PHI exposure (`v7 §12`, `v8 §1.3`). |
| **On-Device LLMs** | Prohibited due to memory/battery constraints on budget Android phones and uncalibrated hallucination risk (`FINAL §0`). |
| **CRDTs for Authoritative State** | Contract state (`referral`, `offer`) requires serialized single-owner mutual exclusion (`I2`). Append-only set-union by `event_id` handles offline telemetry without a CRDT library (`v7 §6`). |
| **Floating-Point Numbers in JCS JSON** | Prohibited in RFC 8785 JCS canonical JSON (`event.detail` and hash inputs) to prevent cross-language IEEE 754 serialization divergence; use integers (e.g., `lat_e5`, `lon_e5`, `client_ts_ms`, `server_ts_us`), strings, and booleans only (`FINAL §0`, `§7`). |

---

## 3. Hard Database, Concurrency & Timing Locks

### 3.1 Global Lock Order & I14 Enforcement (`F1`, `I14`)
1. **Total Lock Hierarchy:** Every transaction that locks more than one table must acquire row locks strictly in this order:
   $$\text{referral} \longrightarrow \text{offer } (\text{ORDER BY id}) \longrightarrow \text{deadline } (\text{ORDER BY id}) \longrightarrow \text{outbox}$$
2. **Session GUC Trigger (`rhp_require_lock`):** Before mutating `referral`, `offer`, `deadline` (when `status` or `due_at` changes), `event`, `payload_grant`, or inserting into `outbox`, the transaction must lock the `referral` row (`SELECT * FROM referral WHERE id = %s FOR UPDATE`) and set `SELECT set_config('rhp.locked_referral', r.id::text, true)`. Any write without this matching GUC raises `I14_LOCK_NOT_HELD`.
3. **Delivery Bookkeeping Exemption:** Updating `deadline.claimed_until` in Poller Phase 1 (where `status` and `due_at` are unchanged) and updating `outbox.status / attempts / visible_after` in the Outbox Relay are explicitly exempted in `rhp_require_lock()` because they carry no contract state and execute as single-statement `FOR UPDATE SKIP LOCKED` claims that never wait while holding another lock.

### 3.2 Complete 24-Table Schema Inventory & Role Separation (`F4`, `§7`)
All 24 tables in `db/schema.sql` are locked:
1. `facility`
2. `roster`
3. `facility_capability`
4. `need_class_requirement`
5. `catchment_chain`
6. `device`
7. `enrollment_ticket`
8. `session`
9. `referral`
10. `offer` (with partial unique index `one_lease`)
11. `offer_resource_confirmation`
12. `deadline` (with partial indexes `deadline_due` and `deadline_ref`)
13. `event` (append-only trigger `event_ao`, chain guard `event_guard`, detail check `rhp_detail_ok`)
14. `key_version`
15. `event_secret`
16. `clinical_payload`
17. `payload_grant` (with partial unique index `one_active_grant`)
18. `telemetry`
19. `idempotency`
20. `inbox`
21. `outbox` (with partial index `outbox_ready`)
22. `rejected_command` (append-only trigger `rejected_ao`)
23. `checkpoint` (append-only trigger `checkpoint_ao`)
24. `heartbeat`

**Database Role Separation:**
- **`rhp_app`**: `SELECT, INSERT, UPDATE` on public tables; `REVOKE UPDATE, DELETE ON event, checkpoint, rejected_command`; `GRANT DELETE ON event_secret, clinical_payload, idempotency, telemetry` (for crypto-shredding and TTL purge only).
- **`rhp_monitor`** (Person B's process, OS UID `1001`): `SELECT` only on `event, referral, offer, deadline, checkpoint, heartbeat, outbox, rejected_command`; `INSERT, UPDATE ON heartbeat`. **Zero access to `clinical_payload`, `event_secret`, or `key_version`.**
- **`rhp_witness`** (Signer process, OS UID `1002`, key mode `0400`): `SELECT` on `event, referral, checkpoint`; `INSERT` on `checkpoint`; `INSERT, UPDATE` on `heartbeat`.

### 3.3 Safe `BROKEN_BUILD` Scratch Isolation (`F20`)
When `BROKEN_BUILD=1` is toggled in the Guarantee Arena:
- The application connects exclusively to the isolated scratch database `rhp_scratch_broken` (created via `scripts/make_scratch.sh` without the `one_lease` index and with the Python lease check bypassed).
- The process immediately aborts with **exit code `78`** if `REAL_DATA=1`, if the target database name is not `rhp_scratch_broken`, or if the scratch DB role can authenticate to the main database.
- `/mode` returns `{"broken_build": true}`, displaying a flashing red banner `BROKEN BUILD — SCRATCH DB` across the big screen and all desks.

---

## 4. Security, Privacy & Indian Regulatory Posture (`§10`)

### 4.1 Cryptographic & Privacy Constraints
- **Envelope Encryption & Crypto-Shredding:** Every referral has a unique 256-bit `AES-256-GCM` Data Encryption Key (`DEK`), wrapped via `AES-KW` by a monthly Key Encryption Key (`kek_epoch`) in `key_version`. `clinical_payload` AAD $= \text{referral\_id} \parallel \text{key\_id} \parallel \text{schema\_ver}$; `event_secret` AAD $= \text{referral\_id} \parallel \text{seq} \parallel \text{key\_id}$. `event.secret_hash` binds the ciphertext into the SHA-256 chain so deleting `clinical_payload`, `event_secret`, and `key_version.wrapped_dek` (`status='SHREDDED'`) erases all clinical content without invalidating the hash chain (`I5`).
- **K-Anonymity & Bucketing (`F9`):** Public/aggregate XES and analytics exports bucket timestamps into $4\text{-hour}$ windows and suppress any cell with $< 5$ referrals ($k \ge 5$).

### 4.2 Indian Legal & Regulatory Compliance Posture
ReferralHandshake uses synthetic data (`REAL_DATA=0`) and is **"designed to comply"** with the following frameworks (never claim "certified" or "compliant"):

| Regulatory Framework | Architectural Design Posture & Constraints | Status |
|---|---|---|
| **DPDP Act 2023 & DPDP Rules 2025** | Rules notified `13 Nov 2025` vs Gazette `14 Nov 2025` `[CONFLICT]`; core obligations apply from `13/14 May 2027` `[V]`. Emergency processing without consent (`s.7(f)`, cited as `s.7(d)` in earlier drafts `[CONFLICT]`) is scoped strictly to the handover record with logged basis. Staff telemetry (`s.7(i)`) requires prior written notice, minimization, HR siloing, and erasure after evaluation. Penalty ceilings: up to ₹$250\text{ Cr}$ (`s.8(5)` safeguards) and ₹$200\text{ Cr}$ (`s.8(6)` breach notification; $72\text{ h}$ detailed report to DPBI) `[V*]`. Interplay between `s.8(7)` erasure and 3-year clinical retention is parameterized `[GAP]`. | `OPEN` (Requires legal review before real data) |
| **Bharatiya Sakshya Adhiniyam (BSA) 2023 s.63** | Exports a `BSA s.63-ready` bundle containing the JCS canonical event log, per-file SHA-256 hashes, bundle SHA-256 hash, and pre-filled Part A (custodian) and Part B (expert) certificate templates. Never claim "BSA certified". | `BOUNDED` |
| **CERT-In Directions (April 2022)** | $6\text{-hour}$ incident reporting runbook; $180\text{-day}$ rolling logs stored in India; host chrony NTP synchronized to `time.nic.in` / `time.nplindia.org` `[V]`. | `BOUNDED` |
| **TRAI TCCCPR 2018 & DLT** | SMS uses static pre-registered templates with variables $\le 30\text{ chars}$, whitelisted static domains, and zero clinical text `[V]`. Outbound voice uses sandbox/whitelisted numbers; team never circumvents telecom controls. | `CLOSED` (by design) |
| **ABDM / HDMP & NRCeS FHIR R4** | No M3 longitudinal record fetch; clinician-authored summary at point of care; FHIR R4 export (`ServiceRequest`, `Task`, `Encounter`, `Communication`). Claim "ABDM-sandbox aligned" only if live sandbox calls are executed. | `BOUNDED` |
| **ICMR National Ethical Guidelines (2017 / 2023)** | Any district shadow-mode pilot requires ethics committee review (full committee review if pregnant women's identifiable data are used or if the system influences clinical decisions); human-in-the-loop override is mandatory for AI. | `OPEN` |

---

## 5. Complete 40-Item Loophole Ledger & Ranked Residual-Risk Register

### 5.1 The 40-Item Loophole Ledger (`v8 §16`)

| # | Identified Loophole | Deterministic Closure / Bounded Residual in RHP-1 |
|---|---|---|
| 1 | Blocking care through mandatory drug dose/time fields | `mgso4_status` is answer-required (`GIVEN \| NONE_GIVEN \| UNKNOWN`), never knowledge-required; `UNKNOWN` sets red receiver banner and never blocks dispatch (`D1`, `I3`) |
| 2 | Ambulance held waiting for handshake completion | Independent transport track (`tr_state`); `TR_UPDATE` never reads `hs_state` (`I3`) |
| 3 | Double lease granted to two hospitals simultaneously | Per-referral row lock + `one_lease` partial unique index + `lease_epoch` + `rhp_monitor` (`I2`) |
| 4 | Zombie write from a delayed/reconnecting device | Stale `expected_version` / `expected_epoch` fenced with `412` and logged in `rejected_command` (`I8`) |
| 5 | Lost HTTP response followed by client retry | Step 1 `idempotency(actor_id, key)` + `event.event_id UNIQUE` replays stored response (`I4`, `F14`) |
| 6 | In-memory timer lost on server crash | Timers are durable rows in `deadline`; 2-phase poller with $5\text{ s}$ `claimed_until` lease is crash-safe (`I1`, `F1`) |
| 7 | Client clock skew manipulating deadlines | Deadlines use server time `GREATEST(clock_timestamp(), referral.head_ts)` under referral lock (`I16`, `F11`) |
| 8 | Silent receiving hospital ignoring the app | Unified ACK window $A$ with Rung $0$ (`SSE`/`FCM`), Rung $A/4$ (`Exotel` voice), Rung $3A/4$ (dispatcher proxy), and Rung $A$ (`TIMEOUT` escalation) (`I1`, `F2`) |
| 9 | Entire catchment chain exhausted without acceptance | Deterministic transition to `ESCALATED_TO_DISPATCHER` + `DISPATCH_ACTION` deadline; never invents a destination (`I7`, `F6`) |
| 10 | Tertiary medical college funnelling / overload | Default `SEQUENTIAL` mode + `AT_CAPACITY` structured decline + `open_offers <= 2` cap (`I12`, `F13`) |
| 11 | `A -> B -> A` referral ping-pong loops | `UNIQUE (referral_id, facility_id)` on `offer` ensures each facility is targeted at most once per referral (`I9`) |
| 12 | Hospital accepts to game KPIs when no bed is available | APOT (`ARRIVED -> HANDED_OVER`) measured separately from acceptance; `ARRIVAL_REJECTED` revokes lease and logs broken commitment (`K2`) |
| 13 | Shared ward tablet spoofing by unauthorized user | Roster check + registered `device` + server-verified Argon2id PIN on every mutating command (`I6`, `F7`) |
| 14 | BOLA, mass-assignment of `state`, or role abuse | Per-route facility authz, server-owned state transitions, Pydantic `extra='forbid'`, role matrix tests (`I6`) |
| 15 | Database log tampering by sysadmin/superuser | Per-referral SHA-256 JCS chain + $5\text{ s}$ Ed25519 Merkle checkpoints + independent witnesses (`I5`, `F8`) |
| 16 | Split-view history shown to different observers | Signed checkpoints broadcast simultaneously to big screen, judge phones, and off-box witness log (`S2`, `F8`) |
| 17 | Bot flood minting QR join tokens on stage | Rotating single-use QR ($20\text{ s}$ TTL) + Cloudflare Turnstile challenge + hard cap of $20$ `JUDGE_DESK` sessions + LAN fallback (`§9`) |
| 18 | PHI leaked through third-party push notification service | Empty-payload FCM wake ping followed by authenticated TLS fetch (`P3`, `I10`) |
| 19 | PHI leaked or silently dropped in SMS | Static DLT template with $\le 30\text{ char}$ code and whitelisted domain; zero clinical text (`P2`) |
| 20 | Fake crypto-shredding (deleting a salt instead of a key) | Envelope encryption (`AES-256-GCM`) with per-referral DEK deletion + monthly `kek_epoch` destruction (`D9`, `P5`) |
| 21 | DPDP erasure vs. clinical record retention conflict | Retention duration parameterized in `clinical_payload.expires_at`; pseudonymous metadata log lacks PHI (`L2`, `F9`) |
| 22 | AI hallucination reaching the clinical handover record | Draft withheld (`423 ANCHOR_REQUIRED`) until `need_class` + `mgso4_status` anchored; critical fields re-entered; AI optional (`A1`, `A2`) |
| 23 | Automation bias triggered by AI confidence scores/explanations | Neither confidence scores nor explanations are rendered in the UI (`§16`) |
| 24 | Goodhart gaming triggered by countdown timers on desks | Receiving desks show an ordered priority queue without countdown timers; district analytics show aggregated capacity signals (`§15`) |
| 25 | Unlawful staff performance surveillance | DPDP `s.7(i)` prior written notice, minimal collection, strict siloing from HR records, scheduled erasure (`§10`) |
| 26 | Double-entry burden on referring clinicians | Printable ReferralHandshake card *is* the physical referral slip with a 9-char Crockford Base32 code (`§8`) |
| 27 | Over-claiming clinical or mathematical perfection in pitch | Strict Claims Register (`§6` below) enforced by automated forbidden-word linter (`ST-5`) |
| 28 | Spec/code drift or AI coding agent reward-hacking tests | `CODEOWNERS` protection on `spec/`, `db/schema.sql`, and `monitor/`; 3-Gem audit/adversary ring (`§7` below) |
| 29 | False atomicity in abstract models hiding DB race conditions | 200-way `asyncio.Barrier` concurrency test (`race200`) + Toxiproxy + live `rhp_monitor` against real PostgreSQL 16 (`T-C1`) |
| 30 | Server and runtime monitor sharing a common-mode bug | Person A writes server/`transitions.yaml`/`rhp1.qnt`; Person B writes `monitor` from §3 prose alone; verified by `M1`–`M6` (`F17`) |
| 31 | Venue Wi-Fi / internet failure during live pitch | Dual uplink + local hotspot LAN QR mode + pre-recorded MP4 clips (`clip A`–`clip D`) + H22 code freeze (`D4`, `D5`) |
| 32 | Urban canyon / ionospheric GPS error mis-triggering arrival | $200\text{ m}$ geofence emits `ARRIVAL_SUGGESTED` only; human confirmation required for `ARRIVED` (`F5`) |
| 33 | Missing OSM hospital capability tags & tile policy limits | Curated Karnataka facility registry + timestamped staff attestations + commercial Mapbox SDK (`§14`) |
| 34 | Stale capability attestations treated as "live beds" | UI displays attestation age and hides expired rows (`expires_at <= now()`); never called "live beds" (`§14`) |
| 35 | Stale duty roster phone numbers | Unanswered call advances across staggered slots $\delta \to$ Rung $3A/4$ dispatcher proxy $\to$ next facility (`F2`) |
| 36 | PIN brute-force or rival hospital lockout DoS | Argon2id in autonomous transaction scoped per `session_id`/`call_sid`; $3$ strikes page dispatcher (`F7`) |
| 37 | Unsafe or unvalidated timer configuration edits | Signed timing profiles verified by Ed25519 cold key + $T_{max} = F \cdot (A + D + \epsilon) \le B$ startup check (`F2`, `F3`, `I13`) |
| 38 | Single database failure in production pilot | Managed Multi-AZ PostgreSQL 16 with synchronous standby + nightly logical backup + cold-key `RESTORE` protocol (`F8`) |
| 39 | LLM-generated concurrency defects in application code | Spec-first pipeline, `rhp_require_lock` DB trigger (`I14`), `race200`, and `M1`–`M6` mutation gates (`§12`) |
| 40 | Unsettled telecom legality of automated clinical voice calls | Outbound Exotel sandbox to $\le 10$ whitelisted team numbers with de-identified audio now; legal opinion required before pilot (`L1`) |

### 5.2 Ranked Residual-Risk Register (`FINAL §20`)

| Rank | Residual Risk Item | Status | Owner | Mitigation in Place | Closing Evidence Required |
|---|---|---|---|---|---|
| 1 | Voice call regulatory legality unsettled (`L1`) | `OPEN` | Legal Advisor | Exotel sandbox, synthetic de-identified prompts, whitelisted team phones | Written legal opinion prior to any real-world clinical pilot |
| 2 | Retention vs. erasure interplay under NMC / DPDP (`L2`) | `OPEN` | Legal Advisor | Parameterized `clinical_payload.expires_at` and `kek_epoch` lifecycle | Counsel's written opinion on DPDP `s.8(7)` for handover records |
| 3 | Hot Ed25519 signer key theft (`S3`) | `OPEN` | Person A (`T1`) | Separate OS user `rhp-sign` (`0400`), cold-key `RESTORE` check | Cloud HSM / KMS integration in pilot + key-rotation drill log |
| 4 | Real-world clinician adoption incentives | `OPEN` | Person B (`T2`) | Valid decline vocabulary, no countdown clocks, APOT separation, card=slip | $\ge 3$ structured interviews with clinician, 108 crew, and district officer |
| 5 | Software creates zero physical hospital capacity | `BOUNDED` | District Admin | Surfaces refusal before ambulance departs; logs missing-resource bottlenecks | District pilot capacity-bottleneck report |
| 6 | Host clock step bounds (`T2` / `T3`) | `BOUNDED` | Person A (`T1`) | Chrony slew-only, `GREATEST(clock_timestamp(), head_ts)`, $> 2\text{ s}$ NTP alarm | Clock-step fault-injection test report (`T-F11`) |
| 7 | Clinician rubber-stamping of AI drafts (`A1`) | `BOUNDED` | Person B (`T2`) | Cognitive Forcing Function (`423`), critical field re-entry, AI off by default | 20-slip seeded-error usability gate ($\le 5\%$ rubber-stamp, $\le 1\%$ omission) |
| 8 | Android OEM battery-saver process kills (`F4`) | `BOUNDED` | Person B (`T2`) | `heartbeat` staleness indicator, onboarding checklist, PWA manual update button | 2-hour screen-off GPS soak test on target Android device |
| 9 | Low-volume cell re-identification (`P1` / `F9`) | `BOUNDED` | Person A (`T1`) | Closed API `Literal` enums, `rhp_detail_ok` DB check, $4\text{ h}$ buckets, $k \ge 5$ suppression | 10,000-case JSONB fuzz test (`T-F9`) + export k-anonymity audit |
| 10 | AI-generated concurrency defects | `BOUNDED` | Both (`T1` & `T2`) | Global lock order (`I14`), `rhp_require_lock` trigger, `race200`, `M1`–`M6` | Passing `G0` gate report with raw `race200` and `M1`–`M6` outputs |

---

## 6. Claims Discipline & Forbidden Wording Register (`§19`)

The automated CI linter (`ST-5`) scans all documentation, UI strings, and pitch materials (excluding this register table) and fails the build if any phrase in the **Forbidden Claim** column appears:

| Authorized Wording (Permitted) | Forbidden Claim (Strictly Prohibited) |
|---|---|
| *"Referral communication and documentation gaps are documented in specific urban Indian studies (Das et al., 2023; Safdarjung Hospital audit, 2018–2023)."* | National prevalence claims; *"lives saved"*; *"deaths prevented"*; *"mortality reduced"* |
| *"Automatic inter-facility escalation and hard single-owner guarantees were not found in public documentation of the systems audited."* | *"First in India/world"*; *"only system"*; *"no competitor has this"* |
| *"Designed to comply with DPDP Act 2023; ABDM-sandbox aligned (if sandbox calls are executed); synthetic data only (`REAL_DATA=0`)."* | *"ABDM compliant"*; *"DPDP certified"*; *"production ready"*; *"live integration with 108/ABDM"* |
| *"Every identified weakness is CLOSED with a named test, BOUNDED with a stated residual and alarm, or OPEN with an assigned owner."* | *"Bullet-proof"*; *"airtight"*; *"zero loopholes"*; *"mathematically guaranteed"*; *"immune"*; *"crash-proof"*; *"zero silent drops"* |
| *"Control-plane specification model-checked within stated bounds (3 facilities, 4 epochs); implementation checked by conformance vectors, 200-way concurrency tests, and a live independent runtime monitor."* | *"Mathematically proven system"*; *"mathematically impenetrable"* |
| *"Tamper-evident hash-chained event log with independent witnesses and BSA s.63-ready export bundle."* | *"Immutable log"*; *"BSA certified"*; *"legally conclusive"* |
| *"Process improvement and reduced unannounced arrivals are hypotheses to be evaluated in an ethics-approved district pilot."* | *"Eliminates ping-pong"*; *"proven to reduce transfers"* |

---

## 7. 24-Hour Build Schedule, Reconciled Cost Model & Multi-Agent Governance

### 7.1 Hour-by-Hour 24-Hour Build Schedule (`FINAL §17`)
- **Lane A (Person A — `T1`):** Owns `spec/transitions.yaml`, `spec/rhp1.qnt`, `db/schema.sql`, FastAPI `apply_command()`, Poller, Relay, Witness/Signer, and Concurrency/Mutation tests.
- **Lane B (Person B — `T2`):** Owns the **Independent Python Runtime Monitor (`monitor/`)** (built in a separate workspace that never views `api/` server code), React PWA desks, Big Screen Guarantee Arena, Pure-JS Browser Verifier, Dispatcher Console, Exotel IVR, and Paper Code.

| Hours | Lane A (`Person A` — Backend & Proof) | Lane B (`Person B` — Monitor, Clients & Reach) | Tier / Gate |
|---|---|---|---|
| `H0–H2` | Load 24-table DDL (`db/schema.sql`), synthetic seed data, `transitions.yaml` loader, profile validator | React PWA shell, rotating QR + Turnstile admission (`JUDGE_DESK` cap $20$) | `T0` |
| `H2–H6` | `apply_command()` steps 1–10: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `DECLINE` | Receiving Desk UI, SSE stream with per-event `payload_grant` filter | `T0` |
| `H6–H9` | 2-phase Poller, Outbox Relay, `TIMEOUT`, unified notice ladder rungs ($0, A/4, 3A/4$) | Big Screen Guarantee Arena UI; **Independent Python Monitor (`monitor/`)** from §3 prose | `T0` |
| `H9–H12` | SHA-256 JCS hash chain, separate-OS-user Ed25519 witness/signer (`rhp-sign`), Merkle checkpoints | Pure-JS browser verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`) | `T0` |
| `H12–H14` | `race200` barrier test (`T-C1`), Mutation tests `M1`–`M6`, Quint verification | `BROKEN_BUILD=1` scratch DB (`rhp_scratch_broken`) + flashing red banner | **Gate G0 (`T0` Pass)** |
| `H14–H17` | `COUNTER`, `CONFIRM_COUNTER`, arrival cases `(a)`–`(f)`, `CLOSE` & 9 outcomes | Dispatcher Console (`proxy=true`, `DISPATCHER_ASSIGN`), PWA GPS fallback, Replay Scrubber | **Gate G1 (`T1` Pass)** |
| `H17–H20` | 8-case Idempotency matrix (`T-F14`), fencing tests, Toxiproxy chaos suite | Outbound Exotel IVR (AMD + Press-1 gate + `%23` PIN), Crockford Base32 (`mod 37`) paper code | **Gate G2 (`T2` Pass)** |
| `H20–H22` | Fix any defects surfaced by Gate G0–G2 and Gem 2 Milestone Validation attacks | Record MP4 fallback clips (`clip A`–`clip D`), execute 30-second proof loop rehearsal $\times 3$ | **Gate G3 (Rehearsal)** |
| `H22–H24` | **HARD CODE FREEZE AT H22** — config-only adjustments | Final stage rehearsal, hotspot LAN QR check, backup laptop standby | **FREEZE** |

### 7.2 Reconciled 6-Month District Pilot Cloud Cost (`F18`, AWS `ap-south-1` Multi-AZ)

| Infrastructure Line Item | Monthly Cost (USD) | 6-Month Cost (USD) | Reconciliation Notes |
|---|---|---|---|
| Managed PostgreSQL 16 Multi-AZ (`db.t4g.medium`) | $\$95.00$ | $\$570.00$ | Synchronous standby for durable commit |
| Provisioned Storage ($2 \times 100\text{ GB}$ `gp3`) | $\$23.00$ | $\$138.00$ | Primary + standby storage |
| Application Load Balancer (ALB) | $\$22.00$ | $\$132.00$ | Base subtotal $=\$140/\text{mo}$ ($\$840/6\text{ mo}$; reconciles Report 3's $\$810$ within $\$30$ LCU rounding) |
| Compute ($2 \times$ small Linux App VMs) | $\$26.00$ | $\$156.00$ | FastAPI + Poller + Relay + Witness + Monitor |
| Automated Backups & S3 Object Lock Witness Storage | $\$8.00$ | $\$48.00$ | Off-box checkpoint witness log + WAL archive |
| Logs & CloudWatch Monitoring | $\$10.00$ | $\$60.00$ | `log_lock_waits`, NTP offset, and `180-day` CERT-In retention |
| Outbound Data Transfer | $\$6.00$ | $\$36.00$ | Subtotal with app tier $=\$190/\text{mo}$ ($\$1,140/6\text{ mo}$) |
| Exotel Voice IVR & DLT SMS Allowance | $\$25.00$ | $\$150.00$ | District pilot outbound notice rungs |
| $10\%$ Operational Contingency (on $\$215.00$) | $\$21.50$ | $\$129.00$ | — |
| **Locked Total Pilot Budget** | **$\$236.50 / \text{month}$** | **$\$1,419.00$ ($\approx \$1,420$)** | Reconciles all earlier estimates into one locked figure (`$1,140–$1,500` band) |

### 7.3 2-Gem Milestone Validation Multi-Agent Governance (`ReferralHandshake_3Gem_Antigravity_Workflow.md`)
1. **Strict Role Separation:**
   - **Gem 1 (`CONDUCTOR`):** Owns the `STATE LEDGER`, step sequence, tier cut decisions, and emits `AG-PROMPT`s. Never writes product code.
   - **Google Antigravity (`BUILDER`):** The only agent permitted to write product code. Must touch only files listed in `FILES YOU MAY TOUCH`, tag every step `step-<ID>-loop<n>`, and paste raw terminal/test output in the `BUILD REPORT`.
   - **Gem 2 (`MILESTONE VALIDATOR`):** Combined Spec Auditor & Red-Team Adversary. Invoked ONLY at complete feature or milestone/gate completion (or S1 fix). Verifies raw test output, line-by-line spec conformance, `I1`–`I16` enforcement, turns every red-team attack into a runnable test specification `A-1..A-k`, and emits the `DECISION PACKET` directly for Gem 1. (Gem 3 is retired).
2. **Protected Files (`CODEOWNERS`):** `spec/transitions.yaml`, `spec/rhp1.qnt`, `db/schema.sql`, `spec/profiles.json`, and `monitor/` are human-owned and hash-pinned in CI. Coding agents are strictly forbidden from modifying specifications, database triggers, or monitor assertions to make a failing build pass.