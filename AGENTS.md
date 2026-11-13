---
project: ReferralHandshake
protocol: RHP-1
team: MAHA YODHAS
event: Colossus 3.0 (HealthTech Track)
architecture_version: FINAL_LOCKED
real_data_allowed: false
code_freeze_hour: 22
---

# AGENTS.md — ReferralHandshake (Protocol RHP-1) Builder & Multi-Agent Governance Rules

You are operating inside the **ReferralHandshake (Protocol RHP-1)** repository by **Team MAHA YODHAS** (Colossus 3.0, 24-hour build, 2 engineers). Every coding agent (Google Antigravity) and reviewing agent (Gem 1 Conductor, Gem 2 Auditor, Gem 3 Adversary) MUST enforce the rules in this file without exception.

---

## 1. Strict Input Precedence (Non-Negotiable)

Resolve any ambiguity across project documents using this exact authority hierarchy:

1. **`spec/ReferralHandshake_LOCKED_Problem_Statement_v7.md`** — Highest authority on problem framing, the Five Promises, evidence status tags (`[V]`, `[V*]`, `[CONFLICT]`, `[GAP]`, `[verify]`), and claims discipline.
2. **Research findings tagged `[V]`** inside the specification documents.
3. **`spec/ReferralHandshake_v8_LOCKED_Solution.md`** — Authority on defects `D1`–`D20`, the 28 real-world conformance scenarios, the 40-item loophole ledger, and the clinical operating model.
4. **`spec/ReferralHandshake_FINAL_LOCKED_Architecture.md`** — Ultimate technical authority on closures `F1`–`F20`, invariants `I1`–`I16`, the 24-table PostgreSQL 16 DDL, the 10-step `apply_command()` pipeline, timing math, the Quint specification (`rhp1.qnt`), the independent Python runtime monitor, and tiers `T0`–`T3`.
5. **`ReferralHandshake_3Gem_Antigravity_Workflow.md` & `AGENTS.md`** — Authority on multi-agent handoff packets, Lane A / Lane B workspace isolation, `CODEOWNERS` locks, and step acceptance gates.

> **STOP RULE:** If a requirement is not specified in these documents, output `"NOT IN SPEC"` and halt for human clarification. Never invent domain rules, states, or schema columns.

---

## 2. The 9 Core Builder Directives

1. **Read-Only Specification Artifacts:** Files in `/spec` (`transitions.yaml`, `rhp1.qnt`, `profiles.json`, `vectors/`) and `/db/schema.sql` are **READ-ONLY** during application build steps unless the current `AG-PROMPT` explicitly lists them under `FILES YOU MAY TOUCH`. Never edit a spec, test vector, or monitor rule to make a failing build pass (reward-hacking is an automatic `S1` blocker).
2. **The Coherence Rule:** Every component in this repository must be:
   - **(a)** a state or event in the RHP-1 contract,
   - **(b)** an interface/channel adapter producing or consuming those events, or
   - **(c)** a read-only projection of the committed event log.
   Anything outside (a), (b), or (c) is strictly out of scope.
3. **Locked Tech Stack & Banned Technologies:** Use only the locked stack (§3). Never introduce any banned technology or library.
4. **Strict Prompt & Scope Discipline:** Execute **only** what the active `AG-PROMPT` instructs. Modify **only** the files listed in `FILES YOU MAY TOUCH`. Never touch files listed in `FILES YOU MUST NOT TOUCH`. If you encounter an ambiguity, an unresolvable test failure, or need to edit a forbidden file: **STOP immediately** and report in the `BUILD REPORT`. Do not improvise or "make it work."
5. **Synthetic Data & Secret Hygiene (`REAL_DATA=0`):** The prototype processes synthetic data only (`REAL_DATA=0`). Demo timing profiles (`DEMO_FAST`, `DEMO_VOICE`) and `BROKEN_BUILD=1` must refuse to boot (hard abort with `sys.exit(78)`) if `REAL_DATA=1`. Never place API keys, Ed25519 private keys, database passwords, or Exotel credentials in source files or build reports; load them exclusively via environment variables (`.env`).
6. **Git Tagging & Rollback Discipline:** Every completed loop ends with a clean git commit tagged `step-<ID>-loop<n>` (e.g., `step-E1-loop1`). If a step is rejected or marked `REDO`, roll back immediately to the last commit tag marked good in the `STATE LEDGER`.
7. **Evidence-Based Reporting:** Never claim a test, migration, or linter passes without pasting the exact shell command and its raw `stdout`/`stderr` output in the `BUILD REPORT`. A claim of `"tests pass"` without raw output is treated as an automatic `FAIL` by Gem 2.
8. **Single Contract Write Path (`apply_command()`):** All mutations to contract state (`referral`, `offer`, `deadline`, `event`, `payload_grant`, and `outbox` insertions) must go through the 10-step `apply_command()` pipeline following the global lock order:
   `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`.
   No endpoint, background worker, or webhook may mutate contract tables directly.
9. **Common-Mode Independence (`F17`):**
   - **Lane A (Person A)** owns the backend (`api/`), `spec/transitions.yaml`, and the Quint model (`spec/rhp1.qnt`).
   - **Lane B (Person B)** builds the independent Python runtime monitor (`monitor/`) in a separate Antigravity workspace that is **never shown the `api/` server code**. The monitor is written from §3 invariant prose in `ReferralHandshake_FINAL_LOCKED_Architecture.md`, connects exclusively via the read-only PostgreSQL role `rhp_monitor`, and implements its own independent event fold.

---

## 3. Locked Stack vs. Banned Technologies

| Layer | Locked Choice (Enforced) | Banned Technologies (Strictly Forbidden) |
|---|---|---|
| **Database** | PostgreSQL 16, single writable primary, `synchronous_commit=on`, `READ COMMITTED` + explicit `SELECT ... FOR UPDATE`, `pgcrypto` | SQLite for contract state, hot-standby row locking, distributed SQL, NoSQL, CRDTs for authoritative state |
| **Backend API** | Python 3.12, FastAPI, `psycopg` (v3, synchronous or async pool with explicit transactions), Pydantic v2 (`ConfigDict(extra='forbid')`), Argon2id (`argon2-cffi`) | Django, Flask, SQLAlchemy ORM implicit lazy-loading, mass-assignment models, Redis, Celery, Kafka, Debezium |
| **Workers** | Stateless Python 2-phase deadline poller (`python -m rhp.poller`) and outbox visibility-timeout relay (`python -m rhp.relay`) using `FOR UPDATE SKIP LOCKED` | In-memory `asyncio.sleep` timers for deadlines, APScheduler, RabbitMQ, Redis queues |
| **Web Clients** | React PWA (Vite + TypeScript), Server-Sent Events (SSE) with `Last-Event-ID` and 15 s heartbeats, pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256` | WebSockets, Socket.IO, browser `window.crypto.subtle` for Ed25519 (unsupported on iOS Safari / LAN HTTP), countdown clocks on receiving desks |
| **Mobile** | Native Android (Kotlin, `FOREGROUND_SERVICE_TYPE_LOCATION`, `FusedLocationProviderClient`, Room outbox, WorkManager, empty-payload FCM wake) in `T3`; PWA GPS fallback in `T1` | Background location claims on iOS, PHI inside FCM push payloads |
| **Reach** | Exotel outbound IVR (AMD + press-1 gate, $\le 2\text{ s}$ webhook budget, `inbox` deduplication), DLT static SMS alert ($\le 30\text{ char}$ variable), 9-char Crockford Base32 + mod 37 paper code | Inbound-only IVR, clinical text or patient names in SMS or voice prompts, WhatsApp |
| **Maps & ETA** | Server-side cached Mapbox Directions & Matrix (`mapbox/driving` 25 coords, 60 req/min; `driving-traffic` 10 coords, 30 req/min), commercial SDK or self-hosted PMTiles | Bulk downloading from OSM tile servers, autonomous ambulance rerouting, geofence auto-arrival without human confirmation |
| **Formal Proof & Chaos** | Quint (`spec/rhp1.qnt`), independent Python monitor (`monitor/`), Hypothesis stateful testing, `asyncio.Barrier(200)` race suite, Shopify Toxiproxy | Unbounded proof claims, single-author spec+monitor, running `BROKEN_BUILD=1` against the primary database |
| **Serialization & Crypto** | RFC 8785 JCS canonical JSON (ASCII keys, integers, strings, booleans only), SHA-256 hash chain, Ed25519 C2SP checkpoints, AES-256-GCM DEK + AES-KW KEK | Floating-point numbers in canonical JSON (`event.detail` or hash inputs), blockchain, smart contracts, on-device LLMs |
| **Deployment** | Docker Compose (`pg`, `api`, `poller`, `relay`, `monitor`, `witness`, `toxiproxy`, `pwa`, `tunnel`), Cloudflare Tunnel + Turnstile, local hotspot LAN fallback | Kubernetes (EKS/GKE) for hackathon or single-district pilot |

---

## 4. Repository Structure, Lane Ownership & `CODEOWNERS` Boundaries

```text
/
├── AGENTS.md                        # [LOCKED] Builder & multi-agent governance rules
├── GEMINI.md                        # [LOCKED] Workspace context & architectural index
├── CODEOWNERS                       # [LOCKED] Enforces human sign-off on spec/DB/monitor
├── docker-compose.yml               # [Lane A] 9-service orchestration
├── spec/                            # [READ-ONLY / CODEOWNERS: Human + Lane A]
│   ├── ReferralHandshake_LOCKED_Problem_Statement_v7.md
│   ├── ReferralHandshake_v8_LOCKED_Solution.md
│   ├── ReferralHandshake_FINAL_LOCKED_Architecture.md
│   ├── transitions.yaml             # Frozen production transition table
│   ├── rhp1.qnt                     # Quint formal control-plane specification
│   ├── profiles.json                # Cold-key signed timing profiles (4 profiles)
│   └── vectors/                     # Conformance & mutation test vectors (V-*)
├── db/                              # [READ-ONLY after P2 / CODEOWNERS: Human + Lane A]
│   ├── schema.sql                   # Complete 24-table PostgreSQL 16 DDL + triggers + roles
│   └── seed.sql                     # Synthetic Karnataka obstetric network seed (REAL_DATA=0)
├── api/                             # [Lane A ONLY — Person A]
│   ├── rhp/
│   │   ├── main.py                  # FastAPI routes, lifespan validators, SSE hub
│   │   ├── pipeline.py              # 10-step apply_command() implementation
│   │   ├── transitions.py           # Loader & evaluator for spec/transitions.yaml
│   │   ├── poller.py                # 2-phase stateless deadline poller
│   │   ├── relay.py                 # Outbox relay with 30s visibility timeout
│   │   ├── auth.py                  # Enrollment tickets, device keys, Argon2id PIN, sessions
│   │   ├── crypto.py                # AES-256-GCM envelope encryption, JCS, SHA-256 chain
│   │   ├── reach.py                 # Exotel IVR webhooks, DLT SMS stub, Crockford mod 37
│   │   └── models.py                # Strict Pydantic schemas (extra='forbid')
│   └── tests/                       # Conformance, race200, idempotency, mutation M1-M6, Toxiproxy
├── witness/                         # [Lane A — OS user 1002 (rhp-sign), role rhp_witness]
│   └── signer.py                    # 5s REPEATABLE READ snapshot, Merkle root, Ed25519 note
├── monitor/                         # [Lane B ONLY — Person B, OS user 1001, role rhp_monitor]
│   └── monitor.py                   # Independent event-log fold & I1-I16 differential checker
├── pwa/                             # [Lane B ONLY — Person B]
│   └── src/
│       ├── desks/                   # Clinician card, Receiving desk, Dispatcher console, Judge QR
│       ├── arena/                   # Big screen Guarantee Arena, Broken-Build switch, Scrubber
│       └── verifier/                # Pure-JS @noble/curves/ed25519 + @noble/hashes/sha256 verifier
├── android/                         # [Lane B — Tier T3 ONLY]
│   └── app/                         # Kotlin foreground location service + Room outbox
└── scripts/                         # [Shared Utilities]
    ├── make_scratch.sh              # Builds rhp_scratch_broken (drops one_lease index)
    └── verify_gates.sh              # Runs ST-1..ST-5, T-I1..T-I16, T-F1..T-F20
```

### Cross-Lane Isolation Rules
1. **Monitor Isolation (`F17`):** When operating on `monitor/`, the agent must **never** read, import, or copy code from `api/`. It may only inspect `db/schema.sql` and §3/§12 of `ReferralHandshake_FINAL_LOCKED_Architecture.md`.
2. **Spec Freeze (`D28`):** Once `P1`–`P4` pass, `spec/transitions.yaml`, `spec/rhp1.qnt`, `spec/profiles.json`, and `db/schema.sql` are hash-pinned. Any modification requires an explicit `SPEC-DEVIATION` approved by the human user in the `STATE LEDGER`.

---

## 5. Hard Architectural Guardrails (DO / DO NOT Matrix)

### 5.1 Database, Locking & Transaction Pipeline (`F1`, `F4`, `F14`, `I14`)
- **DO** enforce the global lock order in every multi-table transaction:
  `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`.
- **DO** execute all 10 steps of `apply_command(conn, cmd, sess, idem_key)` in exact order:
  1. **Idempotency (`Step 1`):** Acquire transaction-scoped non-blocking advisory lock `pg_try_advisory_xact_lock(hashtextextended(f"{sess.roster_id}:{idem_key}", 0))` (return `409 DUPLICATE_IN_FLIGHT` if false). Check `(actor_id, key)` in `idempotency` before locking `referral`. Reject reused key with different `request_hash` (`422 KEY_REUSED_DIFFERENT_PAYLOAD`); replay stored `http_status` and `response` if `status = 'DONE'` (including prior `409`/`412`/`422`). Insert `IN_FLIGHT` row with 48 h expiry.
  2. **Session Validation (`Step 2`):** Verify opaque session token (`session.token_hash`), device or `call_sid`, and active roster window (`valid_from <= now() < valid_to`).
  3. **PIN Verification (`Step 3`):** Verify Argon2id PIN for mutating commands (`ACCEPT`, `COUNTER`, `DECLINE`, `RESOURCE_CONFIRM`). On failure, increment `session.pin_failed` and set backoff (`0 s`, `5 s`, `30 s`, then `120 s` lock on 3rd strike + `PIN_LOCKED` event + dispatcher page) on a **separate autonomous database connection** so rolling back the command transaction never erases the failure count (`F7`).
  4. **Lock Referral & Monotone Timestamp (`Step 4`):** Execute `SELECT * FROM referral WHERE id = %s FOR UPDATE`, immediately set the session GUC `SELECT set_config('rhp.locked_referral', %s, true)` (enforced by trigger `rhp_require_lock`), compute monotone server timestamp `ts = GREATEST(clock_timestamp(), r.head_ts)` (`F11`, `I16`), and issue `SAVEPOINT sp_cmd`.
  5. **Authority & Fencing (`Step 5`):** Verify role slot, facility match, active `payload_grant`, and optimistic preconditions (`expected_version` and `expected_epoch`). On stale version/epoch, raise `Reject(412, "STALE_PRECONDITION")` (`D7`, `I8`).
  6. **Transition Guard (`Step 6`):** Lock `offer` rows (`ORDER BY id FOR UPDATE`) and `deadline` rows (`ORDER BY id FOR UPDATE`), then evaluate `spec/transitions.yaml`.
  7. **Staleness Check (`Step 7`):** For `ACCEPT` / `CONFIRM_COUNTER(true)`, verify that every required capability in `need_class_requirement` has an `offer_resource_confirmation` row with `expires_at > ts` (`F12`, `I15`). If expired, raise `Reject(409, "STALE_CONFIRMATION_RECONFIRM_REQUIRED")`. If a `SOFT_OPEN` offer was already superseded by a successor's `ACK`, raise `Reject(409, "LATE_ACCEPT_REJECTED")`.
  8. **Apply State Effects (`Step 8`):** Update `offer`, increment `referral.lease_epoch` on ownership change, update `referral.open_offers` (`0..2`), manage `payload_grant` rows, mark satisfied `deadline` rows `DONE` (`WHERE id = $1 AND status = 'PENDING'`), and insert new pending `deadline` rows (satisfying deferred constraint trigger `i1_pending_deadline` at commit).
  9. **Append Hash-Chained Event & Outbox (`Step 9`):** Compute `seq = r.head_seq + 1`, serialize `core` using RFC 8785 JCS (integers, strings, booleans only), compute `hash = SHA256(prev_hash || JCS(core))`, insert into `event` (validated by `rhp_event_guard` and `rhp_detail_ok`), insert `outbox` rows **last** in the lock hierarchy, and update `referral` (`head_seq`, `head_hash`, `head_ts`, `version = version + 1`).
  10. **Finalize or Rollback to Savepoint (`Step 10`):** On success, update `idempotency` (`status = 'DONE'`, `http_status = 200`, `response`) and `COMMIT`. On deterministic domain `Reject(code, reason)`, execute `ROLLBACK TO SAVEPOINT sp_cmd` (preserving the referral lock and `idempotency` row), insert into `rejected_command`, update `idempotency` (`status = 'DONE'`, `http_status = code`, `response`), and `COMMIT`. On any unhandled infrastructure exception, abort the entire transaction so the `IN_FLIGHT` row rolls back cleanly.
- **DO NOT** hold a `deadline` lock across `apply_command()`. The poller MUST run in two phases:
  - **Phase 1:** A single auto-committed statement claiming up to 50 due rows (`UPDATE deadline SET claimed_until = clock_timestamp() + interval '5 seconds' WHERE id IN (SELECT id FROM deadline WHERE status = 'PENDING' AND due_at <= clock_timestamp() AND (claimed_until IS NULL OR claimed_until < clock_timestamp()) ORDER BY due_at LIMIT 50 FOR UPDATE SKIP LOCKED) RETURNING ...`).
  - **Phase 2:** For each claimed row, invoke `apply_command(conn, TimeoutCmd(...), SYSTEM_SESSION, idem_key=f"timeout:{d.id}")`.

### 5.2 State Model, Two Independent Tracks & Clinical Safety (`D1`, `D2`, `F5`, `F6`, `F13`, `I1`–`I3`, `I12`)
- **DO** keep the Handshake track (`hs_state`) and Transport track (`tr_state`) completely independent (`I3`). `TR_UPDATE` and `TR_DESTINATION_CHANGE` must NEVER read or block on `hs_state`.
- **DO** treat `mgso4_status` (`GIVEN | NONE_GIVEN | UNKNOWN`) as **answer-required, never knowledge-required** (`D1`). `UNKNOWN` is valid, never blocks `CREATE` or ambulance dispatch, and triggers a high-visibility red banner (`"Pre-referral MgSO4 dose unknown — verify before dosing"`) on the receiving desk.
- **DO** enforce `open_offers <= 2` (`I12`, `F13`), where open statuses are `OPEN`, `ACKED`, `COUNTERED`, and `SOFT_OPEN`:
  - In `SEQUENTIAL` mode, when offer $k$ times out and offer $k+1$ opens, offer $k$ transitions to `SOFT_OPEN` (unless $k-1$ is still `SOFT_OPEN`, in which case $k-1$ transitions to `TIMED_OUT` immediately so total open offers never exceed 2).
  - If $k$ (`SOFT_OPEN`) sends `ACCEPT` before $k+1$ sends `ACK`, $k$ wins the lease and $k+1$ becomes `SUPERSEDED`. Once $k+1$ sends `ACK`, $k$ immediately transitions to `TIMED_OUT` and any late accept from $k$ gets `409 LATE_ACCEPT_REJECTED`.
  - In `PARALLEL2` mode, timed-out offers go directly to `TIMED_OUT` (no `SOFT_OPEN`).
- **DO** require human confirmation (`EMT` or receiving desk) for `TR_UPDATE(ARRIVED)`. A 200 m geofence + dwell time only emits `ARRIVAL_SUGGESTED` (`D2`, `F5`).
- **DO** enforce the 9-value outcome taxonomy on `CLOSE` (`ADMITTED_STABLE`, `ADMITTED_CRITICAL`, `DELIVERED_AT_RECEIVER`, `DELIVERED_EN_ROUTE`, `PATIENT_REFUSED`, `TRANSPORT_CANCELLED`, `DETERIORATED_OR_DIED_PRE_HANDOVER`, `REDIRECTED_ON_ARRIVAL`, `UNKNOWN_COUNTER_REFERRAL`). `ADMITTED_*` and `DELIVERED_AT_RECEIVER` require `tr_state = 'HANDED_OVER'`. After `2x CLOSURE` deadline expiries without human closure, the system closes with `UNKNOWN_COUNTER_REFERRAL` (`proxy=true`, `actor=system`)—never a fabricated clinical outcome (`F6`).

### 5.3 Timing Math, Notice Ladder & Clock Discipline (`F2`, `F3`, `F11`, `I13`, `I16`)
- **DO** place all intra-facility notice rungs inside the unified ACK window $A$ as `deadline` rows:
  - Rung $0$: SSE + empty-payload FCM push to all rostered slots concurrently.
  - Rung $A/4$: Exotel outbound voice call (`NOTICE_VOICE`), slot $i$ staggered at $A/4 + i \cdot \delta$ ($i = 0 \dots S-1$).
  - Rung $3A/4$: Dispatcher proxy page (`NOTICE_PROXY`).
  - Deadline $A$: `ACK` timeout (`DEADLINE_TIMEOUT`).
- **DO** enforce the startup and `/healthz` timing validator (`I13`):
  $$T_{\max} = F \cdot (A + D + \epsilon) \le B$$
  and when voice is enabled:
  $$\frac{A}{4} + (S - 1) \cdot \delta + V \le \frac{3A}{4}$$
  Verify the cold-key Ed25519 signature over the active profile at startup and refuse to boot if invalid or if a demo profile is loaded when `REAL_DATA=1`.

### 5.4 Cryptography, Integrity, Privacy & Stream Authorization (`F8`–`F10`, `I5`, `I10`, `I11`)
- **DO** prohibit floating-point numbers in `event.detail` and all RFC 8785 JCS canonical JSON structures. Represent coordinates as `lat_e5`/`lon_e5` integers and timestamps as integer milliseconds (`client_ts_ms`) or microseconds (`server_ts_us`).
- **DO** restrict `event.detail` keys to the per-event-type allowlist enforced by `rhp_allowed(type)` and `rhp_detail_ok(type, detail)` (`F9`, `I11`). Free-text clinical notes or patient identifiers in `event.detail` are strictly forbidden.
- **DO** encrypt `clinical_payload` and `event_secret` using per-referral AES-256-GCM DEKs wrapped by monthly AES-KW KEK epochs (`key_version`). Bind ciphertext into the hash chain via `event.secret_hash` so deleting ciphertexts and setting `wrapped_dek = NULL, status = 'SHREDDED'` never breaks hash-chain verification (`D9`).
- **DO** check `(facility_id, role_slot, active payload_grant)` on every SSE frame emission and every 15 s heartbeat (`F10`, `I10`). When a grant is revoked (`DECLINE`, `CANCEL`, `SUPERSEDED`, `TIMED_OUT`, `ARRIVAL_REJECTED`), emit a `GRANT_REVOKED` control frame on the next relay cycle, strip clinical fields from that subscriber's stream, and wipe clinical DOM state in the client.
- **DO** run the checkpoint signer (`witness/`) under a dedicated OS user (`1002` / `rhp-sign`, key mode `0400`) connecting as `rhp_witness` in `REPEATABLE READ READ ONLY` mode every 5 s. Build the binary Merkle tree over referrals sorted by `id` (`Leaf = SHA256(0x00 || referral_id(16B) || head_seq(8B BE) || head_hash(32B))`, `Node = SHA256(0x01 || left || right)`, odd node promoted unchanged). Any head regression without a cold-key-signed `checkpoint(kind='RESTORE')` and per-referral `RESTORE` event must be flagged as `TAMPER` (`F8`).

### 5.5 Reach Channels, Anti-Goodhart UI & Safe `BROKEN_BUILD` (`F7`, `F20`, `D13`, `D18`)
- **DO** enforce AMD + a mandatory `"Press 1 to hear a referral"` gate on Exotel outbound IVR before committing an `ACK` (`F7`). Voicemail, silence, or machine verdicts must never trigger `ACK`. Deduplicate webhook retries via `inbox(source, external_id)` and complete webhook processing within the $\le 2\text{ s}$ target budget (Exotel hard timeout is $5\text{ s}$ `[V]`).
- **DO** validate paper codes using 8 Crockford Base32 payload characters ($40\text{ bits}$, integer $N$) + 1 check character ($N \bmod 37$ mapped to `0-9A-Z*~$=U`), rate-limited to 10 attempts/min per session.
- **DO** display an ordered priority queue **without countdown clocks** on receiving hospital desks (`D18`, anti-Goodhart protection) and report arrival-to-handover latency separately from acceptance latency.
- **DO** isolate `BROKEN_BUILD=1` (`F20`): route connections exclusively to `rhp_scratch_broken` (created without the `one_lease` unique index), skip the application-level lease guard, display a flashing red banner (`BROKEN BUILD — SCRATCH DB`), and hard-abort (`sys.exit(78)`) if `REAL_DATA=1` or if the DSN points to the primary database.

---

## 6. Invariants `I1`–`I16` Enforcement & Verification Matrix

Every step touching backend or monitor code is audited against these 16 invariants:

| ID | Type | Formal Predicate | Primary Enforcement | Independent Monitor Rule (`monitor/monitor.py`) | Test ID |
|---|---|---|---|---|---|
| **I1** | Liveness | Every non-terminal referral has $\ge 1$ `PENDING` deadline and a responsible role; overdue deadlines acted on within $\tau$ | Deferred constraint trigger `i1_pending_deadline` at `COMMIT` | Query `deadline` where `status='PENDING' AND due_at < clock_timestamp() - TAU_MS` ($\tau = 2 \times \text{poll} + 2000\text{ ms}$) | `T-I1` |
| **I2** | Safety | $\le 1$ active ownership lease per referral; `lease_epoch` strictly increases on every grant | Partial unique index `one_lease` on `offer(referral_id) WHERE status='ACCEPTED'` + referral row lock | Fold events: flag `I2` if `LEASE_GRANTED` occurs while lease is held or `e.epoch <= st["epoch"]` | `T-I2` |
| **I3** | Safety | `TR_UPDATE` and `TR_DESTINATION_CHANGE` accepted in every non-terminal `hs_state` | Transport handler never reads `hs_state` | Flag `I3` if any `rejected_command` for `TR_*` has reason other than terminal referral or invalid `tr_state` step | `T-I3` |
| **I4** | Safety | Each client `event_id` appears once; per-referral `seq` starts at 1 and has zero gaps | `idempotency` PK, `event.event_id UNIQUE`, `PRIMARY KEY(referral_id, seq)`, trigger `rhp_event_guard` | Fold events: flag `I4` if `e.seq != st["seq"] + 1` or duplicate `event_id` | `T-I4` |
| **I5** | Safety | Per-referral SHA-256 hash chain and Ed25519 checkpoint signatures verify; `CLOSED`/`CANCELLED` has non-null `outcome` | Append-only triggers `event_ao`, `checkpoint_ao`; `referral` outcome `CHECK` | Recompute `SHA256(prev_hash || JCS(core))` for every event and compare with `referral.head_hash` | `T-I5` |
| **I6** | Safety | Every `ACCEPT`/`COUNTER`/`DECLINE` is by an active rostered role on a registered device/number with verified PIN, or `proxy=true` | Pipeline steps 2, 3, and 5 | Verify `actor_roster_id` has valid `roster` window at `server_ts` and valid session/PIN or `proxy=true` | `T-I6` |
| **I7** | Safety | System-chosen offer targets $\in \text{referral.chain}$; dispatcher offers carry `source='DISPATCHER'` | Trigger `offer_chain_guard` on `offer` | Flag `I7` if `OFFER_CREATED` has `source='CHAIN'` and `facility` $\notin \text{referral.chain}$ | `T-I7` |
| **I8** | Safety | Commands with stale `expected_version` or `expected_epoch` are never applied and are logged | Pipeline step 5 (`412` + `SAVEPOINT` rollback + `rejected_command` insert) | Flag `I8` if any applied event has `e.epoch < st["epoch"]` | `T-I8` |
| **I9** | Safety | A facility is offered at most once per referral (no $A \to B \to A$ referral loops) | `UNIQUE(referral_id, facility_id)` on `offer` | Track offered facilities per referral in fold; flag `I9` on duplicate | `T-I9` |
| **I10** | Safety | Clinical payload frames are emitted only to subscribers with an active (`revoked_at IS NULL`) `payload_grant` | Per-frame SSE filter + `GRANT_REVOKED` control frame on revoke | Audit stream/outbox logs against `payload_grant.revoked_at` | `T-I10` |
| **I11** | Safety | `event.detail` contains only allowlisted keys with boolean, integer ($\le 12$ digits), enum (`^[A-Z0-9_]{1,40}$`), or UUID values | Pydantic closed `Literal` models + SQL `CHECK (rhp_detail_ok(type, detail))` | Scan `event.detail` keys/values in fold against allowlist | `T-I11` |
| **I12** | Safety | At most 2 open offers (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) per referral at any instant | `referral.open_offers CHECK (open_offers BETWEEN 0 AND 2)` maintained under lock | Count active open offers in fold and check `referral.open_offers <= 2` | `T-I12` |
| **I13** | Safety | Configured $T_{\max} = F \cdot (A + D + \epsilon) \le B$ and voice stagger $\le 3A/4$ for active profile | Startup and `/healthz` profile validator + Ed25519 cold-key signature check | Recompute $T_{\max}$ against active profile on monitor loop | `T-I13` |
| **I14** | Safety | No contract-state write occurs without holding the `referral` row lock | Trigger `rhp_require_lock` checking `current_setting('rhp.locked_referral', true)` | Check `pg_stat_database.deadlocks` delta $= 0$ and `log_lock_waits` | `T-I14` |
| **I15** | Safety | No ownership lease is granted using a resource confirmation where `expires_at <= server_ts` | Pipeline step 7 check (`409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`) | Join `OFFER_ACCEPTED` `server_ts` with `offer_resource_confirmation.expires_at` | `T-I15` |
| **I16** | Safety | `event.server_ts` is monotonically non-decreasing per referral | `GREATEST(clock_timestamp(), r.head_ts)` in step 4 + `rhp_event_guard` trigger | Flag `I16` if `e.ts < st["ts"]` in fold | `T-I16` |

---

## 7. Traceability Map for Closures `F1`–`F20`

Every agent implementing or auditing a step must verify the corresponding `F1`–`F20` mechanism and test:

| Fix | Defect Closed | Required Implementation Mechanism | Verification Test |
|---|---|---|---|
| **F1** | Poller held deadline locks across commands | Global lock order `referral > offer > deadline > outbox`; 2-phase poller; trigger `rhp_require_lock` | `T-F1 lock_order_200way` |
| **F2** | Notice ladder raced offer ACK | Notice rungs at $0$, $A/4$, $3A/4$ inside ACK window $A$; 4 cold-key signed profiles; demo profiles abort if `REAL_DATA=1` | `T-F2 profile_guard` |
| **F3** | $T_{\max}$ double-counted slots / unbounded | Concurrent slot notification; $T_{\max} = F \cdot (A + D + \epsilon) \le B$ enforced at startup | `T-F3 tmax_validator` |
| **F4** | Incomplete DDL | Complete 24-table PostgreSQL 16 DDL in `db/schema.sql` with `one_lease`, deferred FK, and triggers | `T-F4 ddl_load_fk_scan` |
| **F5** | Arrival ambiguity | 6 explicit arrival cases (`a`–`f`); 200 m geofence emits `ARRIVAL_SUGGESTED` only; human confirms `ARRIVED` | `T-F5 arrival_cases` |
| **F6** | Closure holes | Reachability & Exit table; 9-outcome taxonomy; two-stage `CLOSURE` deadline then system `UNKNOWN_COUNTER_REFERRAL` | `T-F6 reachability_bfs` |
| **F7** | Lockout-DoS & voicemail ACK | Single-use enrollment ticket $\to$ device key $\to$ opaque session; Argon2id failure counter in autonomous txn; per-session/call lockout; AMD + press-1 gate | `T-F7 pin_lockout_scope` |
| **F8** | Witness & restore gaps | Separate OS user `rhp-sign` (`1002`) Ed25519 signer; binary Merkle inclusion proofs; cold-key signed `RESTORE` checkpoint + event | `T-F8 tamper_vs_restore` |
| **F9** | Free-text PHI in `event.detail` | Per-type key allowlist (`rhp_allowed`) + Pydantic `Literal` + SQL `rhp_detail_ok`; 4 h export buckets with $k \ge 5$ suppression | `T-F9 detail_check_fuzz` |
| **F10** | SSE streams outlive grants | Per-frame `(facility, role, active payload_grant)` check + 15 s heartbeat re-check + `GRANT_REVOKED` control frame + client DOM wipe | `T-F10 sse_revoke` |
| **F11** | Clock step hazards | `GREATEST(clock_timestamp(), head_ts)` under referral lock; chrony slew-only; `heartbeat.ntp_offset_ms > 2000` alarm | `T-F11 clock_step` |
| **F12** | Stale offline `ACCEPT` | `expires_at` on `offer_resource_confirmation`; `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` + live reconfirm UI flow | `T-F12 offline_stale` |
| **F13** | Open-offer count undefined | `open_offers CHECK (0..2)`; `SOFT_OPEN` early close when $k+1$ opens; `PARALLEL2` & `COUNTER` race rules | `T-F13 open_cap` |
| **F14** | Replay semantics undefined | Step 1 idempotency with `pg_try_advisory_xact_lock`, `(actor_id, key)` PK, `request_hash`, and `SAVEPOINT` rejection persistence | `T-F14 idem_matrix` |
| **F15** | Unbounded "none" residuals | All 45 rows in §18 failure matrix carry explicit technical bounds and monitor alarms | `T-F15 residual_lint` |
| **F16** | Vague demo scope | Feature-flagged tiers `T0`–`T3`; scripted second-by-second 30 s live proof loop (`DEMO_FAST`) with MP4 fallbacks | `T-F16 loop_rehearsal` |
| **F17** | Spec/monitor common-mode failure | Lane A writes server/YAML/Quint; Lane B writes `monitor.py` from §3 prose alone; verified by 6 mutation tests `M1`–`M6` | `T-F17 mutation_suite` |
| **F18** | Conflicting pilot cloud cost figures | Reconciled 6-month AWS `ap-south-1` Multi-AZ budget table ($\approx \$1,420$ total; $\$840$ base, $\$1,140$ with app tier) | `T-F18 cost_recompute` |
| **F19** | Implicit v7 state mapping | Explicit 12-state mapping table between Problem Statement v7 and RHP-1 `hs_state` / `offer.status` / `event.type` | `T-F19 v7_map` |
| **F20** | Broken build near real data | `BROKEN_BUILD=1` isolated to `rhp_scratch_broken` DB without `one_lease`; red banner; exits `78` if `REAL_DATA=1` or main DB | `T-F20 broken_isolation` |

---

## 8. The 3-Gem + Antigravity Multi-Agent Workflow

### 8.1 Agent Roles
- **Gem 1 — CONDUCTOR:** Owns the build sequence, tier gates (`G0`–`G3`), scope cuts (`T3 -> T2 -> T1`; never `T0`), the `STATE LEDGER`, and emits `AG-PROMPT` blocks. Never writes product code.
- **Google Antigravity — BUILDER (You):** Executes `AG-PROMPT` instructions inside the repository, writes product and test code, runs verification commands, commits/tags (`step-<ID>-loop<n>`), and outputs the `BUILD REPORT` + `AUDIT-REQUEST FOR GEM 2`. Never makes architectural decisions.
- **Gem 2 — AUDITOR:** Audits raw test outputs, line-by-line spec conformance, invariant enforcement (`I1`–`I16`), lock order, and file scope. Emits `PASS`, `PASS-WITH-NOTES`, `FAIL`, or `REJECT` inside a `RED-TEAM REQUEST` block for Gem 3. Never writes fixes.
- **Gem 3 — ADVERSARY:** Designs runnable attack tests (races, Toxiproxy partitions, crashes, clock steps, auth bypasses, claims lint), challenges Gem 2's audit, and emits a `DECISION PACKET` (`ADVANCE`, `FIX-THEN-ADVANCE`, `REDO`, `SPEC-QUESTION`) to Gem 1.

### 8.2 Loop Types & Risk Classification
- **HIGH Risk (`FULL` Loop: `G1 -> AG -> G2 -> G3 -> G1`):** Any step touching `apply_command()`, row locks/triggers, `db/schema.sql`, idempotency, hash chain/witness/crypto, poller/relay, PIN/session/auth, SSE per-event authorization, `BROKEN_BUILD`/`REAL_DATA` guards, or Exotel voice ACK.
- **LOW/MED Risk (`FAST` Loop: `G1 -> AG -> G2 -> G1`):** Styling, synthetic seed data, copy text, static config, README, or `S2`/`S3` defect fixes.
- **Broken Build (`SHORT-CIRCUIT`: `G2 -> G1` directly):** Triggered when Gem 2 issues `REJECT` (code does not run, raw test output missing, or forbidden files modified).

### 8.3 Step Catalogue & Acceptance Gates (`Phase P` & `Phase E`)

| Step | Lane | Hours / Phase | Scope | Risk / Loop | Gate Criteria (§24 Measured Acceptance) |
|---|---|---|---|---|---|
| **P1** | A | Pre-Event | `spec/transitions.yaml` + conformance vectors from §4 transition table | HIGH / FULL | Vectors cover all 14 commands & 28 scenarios |
| **P2** | A | Pre-Event | Load `db/schema.sql` (24 tables) into PG16; run FK/constraint scan (`ST-3`) | HIGH / FULL | All 24 tables, triggers, indexes, and roles load cleanly |
| **P3** | A | Pre-Event | `spec/rhp1.qnt` formal model; `quint run` ($\ge 20,000$ samples) & vacuity checks | HIGH / FULL | `safety` holds; vacuity checks for `ACCEPTED`, `DISPATCH`, `CLOSED`, `SOFT` fail as required |
| **P4** | B | Pre-Event | Signed `spec/profiles.json` + $T_{\max}$ startup validator (`I13`, `ST-2`) | MED / FAST | All 4 profiles pass $T_{\max} \le B$ & Ed25519 signature check |
| **P5** | B | Pre-Event | Synthetic seed data (`db/seed.sql`, `REAL_DATA=0`) | LOW / FAST | Loads Karnataka-style PHC/CHC/FRU/DH/MC tiers & catchment chains |
| **P6** | B | Pre-Event | Execute §21 pre-event verification checklist | LOW / FAST | Checklist results logged |
| **E0** | A & B | H0–H2 | `docker-compose.yml`, DDL load, seed, YAML loader (A); PWA shell, rotating QR (B) | MED / FAST | Stack boots cleanly; `/healthz` returns 200 |
| **E1** | A & B | H2–H6 | `apply_command()` steps 1–10: `CREATE`/`ACK`/`ACCEPT`/`DECLINE` (A); Desk UI + SSE grant filter (B) | HIGH / FULL | Conformance vectors pass; `T-F10 sse_revoke` passes |
| **E2** | A & B | H6–H9 | 2-phase poller, outbox relay, `TIMEOUT`, notice ladder (A); Big screen + independent `monitor.py` (B) | HIGH / FULL | `T-I1`–`T-I16` monitor checks active; zero server imports in `monitor/` |
| **E3** | A & B | H9–H12 | Hash chain, `witness/signer.py`, Merkle proofs (A); Browser noble verifier (B) | HIGH / FULL | `T-F8 tamper_vs_restore` & browser verification pass on tampered row |
| **E4** | A & B | H12–H14 | `race200` barrier test, mutations `M1`–`M6` (A); `BROKEN_BUILD` scratch DB + red banner (B) | HIGH / FULL | **Gate G0 (`T0` Pass):** `race200` $\to$ 1 of 200 gets `200`, 1 `ACCEPTED` in DB, 0 seq gaps, 0 deadlocks; `M1`–`M6` trip checkers; 10-min Hypothesis+chaos run $= 0$ violations; `BROKEN_BUILD` turns monitor red $\le 2\text{ s}$; `DEMO_FAST` silence-to-dispatcher $\le 25\text{ s}$ |
| **E5** | A & B | H14–H17 | `COUNTER`, `CONFIRM_COUNTER`, arrival cases `a`–`f`, closure (A); Dispatcher console + PWA GPS + scrubber (B) | HIGH / FULL | **Gate G1 (`T1` Pass):** 20/20 paired proxy vs direct API runs yield identical state/events; replay scrubber reproduces final state |
| **E6** | A & B | H17–H20 | Idempotency edge matrix, fencing tests (A); Exotel IVR (AMD + press-1 gate) + Crockford mod 37 paper code (B) | HIGH / FULL | **Gate G2 (`T2` Pass):** 20/20 voice ACKs recorded only post-commit; 0/5 voicemail ACKs; webhook p95 $\le 2\text{ s}$; 1,000/1,000 single-symbol paper-code errors rejected |
| **E7** | A & B | H20–H22 | Defect closures from tests (A); Record MP4 fallbacks (`clip A`–`D`), 30 s proof loop rehearsal $\times 3$ (B) | MED / FULL | **Gate G3 (Rehearsal Pass):** 3 consecutive 30 s live proof loops complete inside budget |
| **E8** | A & B | H22–H24 | **CODE FREEZE at H22:** Config-only adjustments, backup laptop sync, final stage check | LOW / FAST | **FREEZE Gate:** Zero code commits after H22 |

> **Tier `T3` Rule:** `T3_EXTRAS` (Kotlin Android app, AI intake accelerator with `423 ANCHOR_REQUIRED` Cognitive Forcing Function, FHIR R4 / IEEE 1849 XES exporters) may ONLY be started if Gates `G0`, `G1`, and `G2` are 100% green.

---

## 9. Mandatory Antigravity Output Format (`BUILD REPORT` + `AUDIT-REQUEST`)

Every task executed by Antigravity MUST conclude with the following two blocks in exact order. Omitting raw command outputs or truncating high-risk code files is an automatic `FAIL`.

```text
=== BUILD REPORT | STEP <id> | LANE <A|B> | LOOP #<n> | COMMIT <hash/tag> ===
1. FILES CHANGED (git diff --stat):
<paste exact output of git diff --stat>

2. CODE OF HIGH-RISK FILES:
<paste full text of every modified file touching apply_command, DDL, locks, auth, crypto, poller, relay, monitor, or witness; or full git diff if >300 lines>

3. COMMANDS RUN + RAW OUTPUT:
<paste exact shell commands executed and raw stdout/stderr — NEVER summarize>

4. MEASURED TEST RESULTS:
| Test ID | Name | Status (PASS/FAIL) | Measured Value / Latency / Assertion |
|---|---|---|---|

5. NOT DONE / SKIPPED:
<list any deferred items or "none">

6. DEVIATIONS FROM SPEC:
<list any deviation or "none" — silent deviation is an automatic S1 failure>

7. ASSUMPTIONS & OPEN QUESTIONS:
<list assumptions made and questions for human/Conductor, or "none">

8. SELF-RATED RISK & TOP 3 FAILURE CANDIDATES:
- Risk: <LOW | MED | HIGH>
- Candidate 1: <what is most likely wrong in this code>
- Candidate 2: <second most likely flaw>
- Candidate 3: <third most likely flaw>

=== AUDIT-REQUEST FOR GEM 2 ===
STEP: <id> | LANE: <A|B> | LOOP: <FULL|FAST> #<n>
SPEC ANCHORS: <§ sections, I# invariants, F# closures, T-# tests>
ACCEPTANCE CRITERIA: <copied from AG-PROMPT>
LEDGER: <one-line STATE LEDGER>
QUESTION FOR GEM 2: Audit the BUILD REPORT and attached code above against every spec anchor and invariant. Verify that raw command output proves every acceptance criterion.
```

---

## 10. Claims & Evidence Discipline (§19 Compliance Lint)

All documentation, UI copy, pitch overlays, comments, and reports generated by any agent must obey the Claims Register (§19 of `ReferralHandshake_FINAL_LOCKED_Architecture.md`).

| Authorized Wording (MUST USE) | Forbidden Claims (NEVER USE — Automatic CI Lint Failure `ST-5`) |
|---|---|
| Referral communication and documentation gaps are documented in specific urban Indian studies (Das et al. 2023 `[V]`, denominator `[CONFLICT]` 25,253 vs 28,020 — quote percentages only; Safdarjung 2018–2023 `[V]`) | "National prevalence", "lives saved", "deaths prevented", "reduces maternal mortality" |
| Automatic inter-facility escalation and hard single-owner guarantees were not found in public documentation of the systems audited `[V*]` | "First in the world", "only system", "no competitor has this" |
| Control-plane model checked within stated bounds (3 facilities, 4 epochs); implementation checked by conformance vectors, 200-way concurrency tests, and a live independent runtime monitor | "Mathematically proven system", "mathematically guaranteed", "100% bug-free" |
| Every identified weakness is `CLOSED` (with a named test), `BOUNDED` (with a stated technical residual and monitor alarm), or `OPEN` (with an assigned owner) | "Bullet-proof", "airtight", "zero loopholes", "immune to failure", "crash-proof", "zero silent drops" |
| Tamper-evident hash-chained log with independent Ed25519 witnesses; BSA 2023 s.63-ready export bundle with Part A/B templates | "Immutable log", "blockchain-grade", "BSA certified", "legally conclusive" |
| Designed to comply with DPDP Act 2023; synthetic data only (`REAL_DATA=0`); FHIR-shaped export ("ABDM-sandbox aligned" only if sandbox calls are made) | "ABDM compliant", "HIPAA/DPDP certified", "production ready", "live 108 integration" |
| Process improvement and earlier refusal visibility are hypotheses for an ethics-approved district pilot; system does not create hospital capacity | "Eliminates ping-pong", "creates bed capacity", "solves hospital overcrowding" |