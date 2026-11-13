---
trigger: always_on
scope: "**/*"
authority: ReferralHandshake_FINAL_LOCKED_Architecture.md
precedence: "Problem_Statement_v7 > Research_[V] > Solution_v8 > Architecture_FINAL > Workflow_3Gem"
system: "ReferralHandshake (Protocol RHP-1)"
team: "MAHA YODHAS (Colossus 3.0 HealthTech Track)"
---

# `.agents/rules/architecture-integrity.md` — Architectural Integrity & Coherence Guardrails

You are operating as a builder or auditor agent on **ReferralHandshake (Protocol RHP-1)**. Every architectural decision, module boundary, state transition, and dependency in this repository is governed by this rule file. If a prompt or task conflicts with these rules, **STOP immediately** and report a `SPEC-QUESTION` or `DEVIATION`. Never improvise architecture.

---

## 1. Strict Input Precedence Hierarchy (Non-Negotiable)

Resolve any ambiguity across project documents using this exact order of authority:
1. **`ReferralHandshake_LOCKED_Problem_Statement_v7.md`** — Highest authority on problem framing, operational scope, evidence status tags (`[V]`, `[V*]`, `[CONFLICT]`, `[GAP]`), and claims discipline.
2. **Primary Research Findings tagged `[V]`** — Verified facts embedded in the locked documents.
3. **`ReferralHandshake_v8_LOCKED_Solution.md`** — Authority on defects `D1`–`D20`, the 28 real-world conformance scenarios, the 40-item loophole ledger, and the clinical operating model.
4. **`ReferralHandshake_FINAL_LOCKED_Architecture.md`** — Ultimate technical authority on closures `F1`–`F20`, invariants `I1`–`I16`, the 24-table PostgreSQL 16 DDL, the 10-step `apply_command()` pipeline, timing bounds, the Quint formal specification (`rhp1.qnt`), the independent Python runtime monitor, and tiers `T0`–`T3`.
5. **`ReferralHandshake_3Gem_Antigravity_Workflow.md`** — Authority on `.agents/`, `AGENTS.md`, lane isolation (`Lane A` vs `Lane B`), and the `Conductor -> Antigravity -> Auditor -> Adversary` verification ring.

---

## 2. The Coherence Rule (Strict Scope Gate)

Every file, module, endpoint, background worker, or UI view in ReferralHandshake **MUST** be reducible to at least one of three architectural roles:
- **(a) Contract State or Event:** A state or event in the RHP-1 Handshake or Transport state machine.
- **(b) Contract Producer/Consumer Interface:** An adapter or client channel that produces commands into `apply_command()` or consumes committed events from the outbox.
- **(c) Read-Only Log Projection:** A process or view that derives state, metrics, verification proofs, or exports strictly by reading the committed event log.

**Anything that is not (a), (b), or (c) is out of scope and MUST NOT be built.**

| Architectural Layer | Component / Module | Role in the Contract | Allowed Database Access |
|---|---|---|---|
| **Core Contract Engine** | `api/` (`apply_command`, `transitions.yaml` loader) | **(a)** Evaluates guards, mutates contract state, appends hash-chained events | `rhp_app` (RW via `apply_command()` only) |
| **Durable Timer & Delivery Workers** | `api/poller.py`, `api/relay.py` | **(a)/(b)** Claims due deadlines (`TIMEOUT`) and relays `outbox` frames | `rhp_app` (2-phase poller + `SKIP LOCKED` relay) |
| **Field & Desk Interfaces** | React PWA desks, Android Kotlin app, Exotel IVR webhook, DLT SMS link, Paper code entry, Dispatcher proxy console | **(b)** Submits idempotent commands; renders SSE/FCM/voice notifications | None direct (HTTP REST + SSE only) |
| **Optional AI Intake Accelerator** | `api/intake.py`, PWA draft verification UI (`T3_EXTRAS`) | **(b)** Pre-create draft assistant with Cognitive Forcing Function (`423 ANCHOR_REQUIRED`); off critical path | None on contract tables prior to `CREATE` |
| **Independent Runtime Monitor** | `monitor/` (Person B, zero shared code with `api/`) | **(c)** Folds `event` table in `REPEATABLE READ READ ONLY` snapshot; checks `I1`–`I16` | `rhp_monitor` (`SELECT` only on non-PHI tables; `INSERT/UPDATE` on `heartbeat`) |
| **Cryptographic Witness / Signer** | `witness/` (OS user `rhp-sign`, `0400` key) | **(c)** Builds binary Merkle tree over referral heads every $5\text{ s}$; signs C2SP checkpoint notes | `rhp_witness` (`SELECT` on `event, referral, checkpoint`; `INSERT` on `checkpoint`; `heartbeat`) |
| **Pure-JS Browser Verifier** | `pwa/src/verifier/` (`@noble/curves/ed25519`, `@noble/hashes/sha256`) | **(c)** Verifies Ed25519 checkpoint signatures, SHA-256 event hash chains, and Merkle inclusion paths | None (consumes `/checkpoints/latest` and proof JSON) |
| **Command Centre & Exporters** | Live map, APOT KPIs, `networkx` graph, IEEE 1849 XES, NRCeS FHIR R4 (`ServiceRequest`, `Task`, `Encounter`, `Communication`) | **(c)** Read-only projections derived from committed events | Read-only queries / replica-compatible projections |

---

## 3. Locked Technology Stack vs. Banned Technologies

### 3.1 Locked Technology Choices
| Layer | Locked Choice | Mandatory Configuration / Constraint |
|---|---|---|
| **Database** | PostgreSQL 16 (single writable primary) | `synchronous_commit=on`, `log_lock_waits=on`, `READ COMMITTED` + explicit `SELECT ... FOR UPDATE` |
| **Backend API** | Python 3.12, FastAPI, `psycopg3` (v3) | Pydantic v2 with `model_config = ConfigDict(extra='forbid')` on all request models |
| **Password / PIN Hashing** | Argon2id (`argon2-cffi`) | Tuned to $\approx 100\text{ ms}$ per verification on demo hardware; failure count updated on autonomous connection |
| **Web Client** | React PWA (TypeScript/JS) | Server-Sent Events (SSE) with `Last-Event-ID` resume and $15\text{ s}$ heartbeats |
| **Client Cryptography** | `@noble/curves/ed25519`, `@noble/hashes/sha256` | Bundled pure-JS (required because iOS Safari WebCrypto lacks Ed25519 and LAN HTTP lacks `crypto.subtle`) |
| **Canonical Serialization** | RFC 8785 JSON Canonicalization Scheme (JCS) | ASCII keys, values restricted to **integers, strings, and booleans only** (floating-point numbers are strictly prohibited) |
| **Mobile Ambulance Client** | Kotlin Android (`T3_EXTRAS`) / PWA GPS fallback (`T1_TRANSPORT`) | `FOREGROUND_SERVICE_TYPE_LOCATION`, `FusedLocationProviderClient`, Room outbox + WorkManager, empty-payload FCM wake |
| **Telephony / Reach** | Exotel Outbound IVR + DLT SMS stub/sandbox + Crockford Base32 paper code | Outbound calls only ($\le 10$ whitelisted numbers in trial); webhook HTTP 200 within $2\text{ s}$ budget ($5\text{ s}$ hard limit) |
| **Maps & Routing** | Mapbox Directions + `mapbox/driving` Matrix API | Server-side cached ($120\text{ s}$ TTL) for active referral's top candidates only ($25$ coords, $60\text{ req/min}$) |
| **Formal Spec & Chaos** | Quint (`spec/rhp1.qnt`), Toxiproxy, `asyncio.Barrier(200)` | Bounded model checking ($F=3, E=4$), 8-toxic chaos matrix, 6 mutation tests (`M1`–`M6`) |

### 3.2 Explicitly Banned Technologies (Immediate Audit `REJECT`)
- **NO Blockchain / Smart Contracts / Web3** (hash chain + signed Merkle checkpoints with external witnesses provide tamper-evidence without consensus overhead).
- **NO Kafka, Debezium, RabbitMQ, or external message brokers** (use the same-transaction PostgreSQL `outbox` table + `SKIP LOCKED` relay).
- **NO Redis or external shared cache tiers** (deadlines, sessions, idempotency keys, and rate/lockout counters live in PostgreSQL; decrypted clinical payloads live only in transient process memory with `Cache-Control: no-store`).
- **NO Kubernetes / EKS** (deploy via `docker-compose.yml` for demo and single-region Multi-AZ VMs for pilot).
- **NO WebSockets** (use HTTP SSE with `Last-Event-ID` for server-to-desk push and standard HTTP POST with `Idempotency-Key` for commands).
- **NO WhatsApp** (strictly excluded for health data and emergency handovers).
- **NO On-Device LLMs or Unanchored AI Auto-Routing** (AI is optional under `T3_EXTRAS`, off the critical path, and never chooses a facility or auto-submits a card).
- **NO CRDT Libraries for Authoritative State** (authoritative contract state is serialized via per-referral row locks on the PostgreSQL primary; additive observations in `telemetry` merge by `event_id` set-union).
- **NO SQLite for the Contract Core** (SQLite lacks per-referral row locking and `SKIP LOCKED` semantics; `D8`).
- **NO Floating-Point Numbers (`float`, `double`, `numeric` decimals) in JCS-hashed Event Payloads or Telemetry** (store coordinates as integer micro/centi-degrees `lat_e5`, `lon_e5`, timestamps as integer milliseconds `client_ts_ms` or microseconds `server_ts_us`).

---

## 4. File-Ownership Boundaries, CODEOWNERS & Common-Mode Independence (`F17`)

### 4.1 Read-Only Frozen Specification Artifacts
Agents **MUST NOT** modify any file in `/spec` or `/db/schema.sql` to make a failing test pass (anti-reward-hacking lock):
- `spec/ReferralHandshake_LOCKED_Problem_Statement_v7.md` (READ-ONLY)
- `spec/ReferralHandshake_v8_LOCKED_Solution.md` (READ-ONLY)
- `spec/ReferralHandshake_FINAL_LOCKED_Architecture.md` (READ-ONLY)
- `spec/transitions.yaml` (Frozen after Step P1; protected by CODEOWNERS and SHA-256 pin in CI)
- `spec/rhp1.qnt` (Frozen after Step P3; Person A only)
- `spec/profiles.json` (Cold-key Ed25519 signed timing profiles; read-only at runtime)
- `spec/vectors.json` (Frozen conformance test vectors)
- `db/schema.sql` (Frozen 24-table PostgreSQL 16 DDL after Step P2)

### 4.2 Two-Lane Author Separation (`F17`)
To prevent common-mode bugs between the server and the runtime monitor:
1. **Lane A (Person A — Backend & Formal Spec):** Owns `api/`, `db/schema.sql`, `spec/transitions.yaml`, `spec/rhp1.qnt`, `witness/`, and server concurrency tests.
2. **Lane B (Person B — Independent Monitor, Clients & Reach):** Owns `monitor/`, `pwa/`, `android/`, and reach adapters.
3. **Strict Isolation Rule for `monitor/`:** The code inside `monitor/` **MUST** be written from the prose specification of Invariants `I1`–`I16` (§3 of the Architecture) alone. `monitor/` **MUST NOT** import any module from `api/`, **MUST NOT** load `spec/transitions.yaml`, and **MUST** connect to PostgreSQL exclusively using the read-only `rhp_monitor` role.

---

## 5. Two-Track Independence & State Model Rules (`I3`, `F5`, `F6`, `F13`, `F19`, `D1`)

### 5.1 Parallel Handshake and Transport Tracks (`I3`)
- **Handshake Track (`referral.hs_state`):**
  `CREATED`, `OFFERED`, `ACKNOWLEDGED`, `ACCEPTED`, `COUNTERED`, `ESCALATED_TO_DISPATCHER`, `CANCELLED`, `CLOSED`.
- **Transport Track (`referral.tr_state`):**
  `REQUESTED`, `DISPATCHED`, `EN_ROUTE`, `ARRIVED`, `HANDED_OVER`, `TR_CANCELLED`.
- **Offer Status (`offer.status`):**
  `OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`, `ACCEPTED`, `DECLINED`, `TIMED_OUT`, `SUPERSEDED`, `ARRIVAL_REJECTED`, `WITHDRAWN`.
  - The **open offer set** (`I12`) is strictly `{'OPEN', 'ACKED', 'COUNTERED', 'SOFT_OPEN'}`. `referral.open_offers` must satisfy $0 \le \text{open\_offers} \le 2$ at all times.
- **Track Independence Rule (`I3`):** The transport handler (`TR_UPDATE`, `TR_DESTINATION_CHANGE`) **NEVER** reads or branches on `referral.hs_state` (except to verify the referral is not in a terminal `CLOSED` or `CANCELLED` state). Transport can advance to `DISPATCHED`, `EN_ROUTE`, or `ARRIVED` while the handshake is still `OFFERED`, `COUNTERED`, or `ESCALATED_TO_DISPATCHER`.
- **Pre-Referral $\text{MgSO}_4$ Rule (`D1`, `K1`):** `referral.mgso4_status` (`'GIVEN' | 'NONE_GIVEN' | 'UNKNOWN'`) is **answer-required, never knowledge-required**. Selecting `'UNKNOWN'` is always valid, never blocks `CREATE` or ambulance dispatch, and triggers a high-visibility red verification banner on the receiving desk UI.

### 5.2 Complete v7 $\rightarrow$ RHP-1 State Mapping (`F19`)
Transient v7 conceptual states (`DECLINED`, `TIMED_OUT`, `ESCALATED`) are represented as committed **events** and **offer statuses**, while `referral.hs_state` reflects the current lead offer after `advance()` executes within the same transaction:

| v7 Conceptual State | `referral.hs_state` | `offer.status` | `referral.tr_state` | Emitted `event.type` |
|---|---|---|---|---|
| `CREATED` | `CREATED` (inside `CREATE` txn) | — | `REQUESTED` | `REFERRAL_CREATED` |
| `OFFERED` | `OFFERED` | `OPEN` | any | `OFFER_CREATED` |
| `ACKNOWLEDGED` | `ACKNOWLEDGED` | `ACKED` | any | `OFFER_ACKED` |
| `ACCEPTED` | `ACCEPTED` | `ACCEPTED` | any | `OFFER_ACCEPTED`, `LEASE_GRANTED` |
| `COUNTERED` | `COUNTERED` | `COUNTERED` | any | `OFFER_COUNTERED` |
| `DECLINED` | `OFFERED` or `ESCALATED_TO_DISPATCHER` (post-`advance()`) | `DECLINED` | any | `OFFER_DECLINED` |
| `TIMED_OUT` | `OFFERED` or `ESCALATED_TO_DISPATCHER` (post-`advance()`) | `TIMED_OUT` or `SOFT_OPEN` | any | `DEADLINE_TIMEOUT` |
| `ESCALATED` | `OFFERED` (`ladder_cursor + 1`) | next `OPEN` | any | `OFFER_CREATED` (`reason: ESCALATION`) |
| `ARRIVAL_REJECTED` | `OFFERED` or `ESCALATED_TO_DISPATCHER` | `ARRIVAL_REJECTED` | `ARRIVED` | `ARRIVAL_REJECTED`, `LEASE_REVOKED` |
| `ESCALATED_TO_DISPATCHER` | `ESCALATED_TO_DISPATCHER` | — | any | `ESCALATED_TO_DISPATCHER` |
| `CANCELLED` | `CANCELLED` | `WITHDRAWN` | any / `TR_CANCELLED` | `CANCELLED` |
| `CLOSED` | `CLOSED` | — | `HANDED_OVER` or outcome-specific | `CLOSED` |

### 5.3 Reachability & Deterministic Exit Guarantee (`F6`)
Every non-terminal `hs_state` must be reachable from `CREATED` and have a deterministic exit path to `CLOSED` or `CANCELLED`:
- `CREATED` exits immediately inside the `CREATE` transaction to `OFFERED` (when `cardinality(chain) >= 1`) or `ESCALATED_TO_DISPATCHER` (when `cardinality(chain) == 0`).
- `OFFERED`, `ACKNOWLEDGED`, and `COUNTERED` are bounded by `ACK`, `DECISION`, and `COUNTER_CONFIRM` deadlines; silence or rejection advances through at most $F$ facilities to `ESCALATED_TO_DISPATCHER`.
- `ACCEPTED` arms a `HANDOVER` deadline; upon `HANDED_OVER`, a two-stage `CLOSURE` deadline fires `CLOSURE_OVERDUE` once and, on its second expiry, automatically executes `CLOSE` with `outcome='UNKNOWN_COUNTER_REFERRAL'`, `proxy=true`, `actor=system`.

---

## 6. Timing Model, Signed Profiles & Clock Discipline (`F2`, `F3`, `F11`, `I13`, `I16`)

### 6.1 Unified Offer-ACK Window & Notice Ladder (`F2`)
Every offer opens with a single unified ACK window of duration $A$ and three notice rungs scheduled as `deadline` rows inside $A$:
- **Rung $0$ ($t = 0$):** Push SSE + empty-payload FCM wake to all rostered slots concurrently.
- **Rung $A/4$ ($t = A/4$):** Outbound Exotel voice call to slot $i \in \{0, \dots, S-1\}$ at $A/4 + i \cdot \delta$.
- **Rung $3A/4$ ($t = 3A/4$):** Dispatcher proxy page for human phone-assist.
- **ACK Expiry ($t = A$):** `TIMEOUT(ACK)` fires. If the offer is still `OPEN` (silent) in `SEQUENTIAL` mode, it transitions to `SOFT_OPEN` and the next facility in `chain` opens (`OPEN`). If the offer was already `ACKED`, the next facility receives an `ADVISORY_PREWARM` event (not an offer, carries no deadline, does not increment `open_offers`).

### 6.2 Worst-Case Escalation Bound $T_{\max}$ (`F3`, `I13`)
With $F$ max facilities in the chain, ACK window $A$, hard decision window $D$ (counter-offer confirmation $C$ is capped at $\min(C, \text{remaining } D)$ so counters never extend $D$), and per-hop poll+apply budget $\epsilon$:
$$T_{\max} = F \cdot (A + D + \epsilon) \le B$$

| Profile ID | $A\text{ (ms)}$ | $D\text{ (ms)}$ | Rungs $(0, A/4, 3A/4)\text{ (ms)}$ | $S, \delta\text{ (ms)}, V\text{ (ms)}$ | $F$ | $\epsilon\text{ (ms)}$ | $C\text{ (ms)}$ | `confirm_ttl` $\text{(ms)}$ | $T_{\max}\text{ (s)}$ | Bound $B\text{ (s)}$ | Allowed with `REAL_DATA=1` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `PILOT_OB_CRITICAL` | `60000` | `180000` | `0 / 15000 / 45000` | `3, 5000, 20000` | `3` | `3000` | `90000` | `120000` | $729\text{ s}$ | $900\text{ s}$ | `true` |
| `PILOT_STANDARD` | `120000` | `300000` | `0 / 30000 / 90000` | `3, 10000, 20000` | `3` | `3000` | `150000` | `180000` | $1269\text{ s}$ | $1500\text{ s}$ | `true` |
| `DEMO_FAST` | `3000` | `4000` | `0 / 750 / 2250` | `3, 0, 0 (voice off)` | `3` | `1000` | `2000` | `10000` | $24\text{ s}$ | $25\text{ s}$ | **`false` (refuses boot)** |
| `DEMO_VOICE` | `45000` | `20000` | `0 / 11250 / 33750` | `1, 0, 20000` | `2` | `1000` | `10000` | `60000` | $132\text{ s}$ | $150\text{ s}$ | **`false` (refuses boot)** |

### 6.3 Mandatory Startup Profile Validator (`T-F2`, `T-F3`)
Every API and poller process **MUST** execute this validation check before binding a socket or claiming deadlines:
```python
def validate_profile(p: Profile, real_data: bool, cold_pub: bytes) -> None:
    assert p.F * (p.A + p.D + p.eps) <= p.B, f"I13 violation: T_max exceeds B for {p.id}"
    if p.voice_enabled:
        assert p.A // 4 + (p.S - 1) * p.delta + p.V <= (3 * p.A) // 4, "Voice stagger exceeds 3A/4 rung"
    assert p.rungs == (0, p.A // 4, (3 * p.A) // 4), "Invalid notice ladder rungs"
    assert not (p.demo and real_data), "F2 violation: Demo profile cannot boot with REAL_DATA=1"
    assert ed25519_verify(cold_pub, p.canonical_bytes(), p.signature), "Invalid cold-key profile signature"
```

### 6.4 Monotone Server Timestamp (`F11`, `I16`)
- Server time for every mutation is computed **inside the referral row lock** as:
  `SELECT GREATEST(clock_timestamp(), r.head_ts)`
- Client timestamps (`client_ts_ms`) are recorded for audit only and **NEVER** used to evaluate deadline expiry or confirmation TTLs.

---

## 7. Build Tiers (`T0`–`T3`) & Explicit DO / DO NOT Guardrails

### 7.1 Tier Cut Order (`F16`)
- **`T0` (Always On — NEVER CUT):** FastAPI core, PostgreSQL 16 DDL, 2-phase poller, outbox relay, PWA desks with rotating QR, Python independent monitor, witness/signer + pure-JS browser verifier, `BROKEN_BUILD` scratch DB isolation.
- **`T1` (`T1_TRANSPORT` — Cut 3rd):** PWA ambulance GPS fallback, dispatcher console + proxy entry, replay time-scrubber.
- **`T2` (`T2_REACH` — Cut 2nd):** Exotel outbound IVR (press-1 gate + PIN), DLT SMS alert stub, Crockford Base32 + mod-37 paper code.
- **`T3` (`T3_EXTRAS` — Cut 1st):** Native Kotlin Android app, AI intake accelerator with Cognitive Forcing Function, FHIR R4 & IEEE 1849 XES exporters.

### 7.2 DO / DO NOT Checklist for Coding Agents
- **DO** route every contract mutation (`referral`, `offer`, `deadline`, `event`, `payload_grant`, `outbox` insert) through `apply_command()`.
- **DO** enforce `REAL_DATA=0` in all demo and test environments.
- **DO NOT** write contract state from background workers, webhooks, or admin scripts outside `apply_command()`.
- **DO NOT** touch files outside the `FILES YOU MAY TOUCH` list in your active `AG-PROMPT`.
- **DO NOT** suppress, weaken, or edit any invariant check (`I1`–`I16`), DB trigger, or conformance vector.