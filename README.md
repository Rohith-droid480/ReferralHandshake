# ReferralHandshake — RHP-1 Protocol & Reference Platform

**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru)  
**Data Posture:** Synthetic data only (`REAL_DATA=0`) | **First Pathway:** Emergency Obstetric Referral (Karnataka-style tiers: $\text{PHC} \rightarrow \text{CHC/FRU} \rightarrow \text{DH} \rightarrow \text{MC}$)

> **Specification Precedence (Read-Only):**  
> `ReferralHandshake_LOCKED_Problem_Statement_v7.md` $>$ Research tagged `[V]` $>$ `ReferralHandshake_v8_LOCKED_Solution.md` $>$ `ReferralHandshake_FINAL_LOCKED_Architecture.md` $>$ `ReferralHandshake_3Gem_Antigravity_Workflow.md`.  
> **Evidence Status Tags:** `[V]` verified primary source · `[V*]` secondary/vendor source · `[CONFLICT]` sources disagree · `[GAP]` no reliable primary data found (parameterised) · `[verify]` pre-event verification item.

---

## 1. The Problem: The Referral Black Box

When an emergency patient needs care that the current facility cannot provide, a referring clinician, an ambulance crew, and a receiving team must coordinate reliably. Published Indian urban obstetric audits show that the handover is frequently an unconfirmed message rather than an accountable commitment:

| Finding | Setting | Status |
|---|---|---|
| Referring facility phoned the receiving facility in $47\%$ of referrals ($11,988$); $53\%$ had no prior phone contact | Urban Maharashtra, 2016–2019, $199,888$ deliveries (Das et al., 2023) | `[V]` |
| $37\%$ of referral slips were fully documented ($9,279$) | Same study | `[V]` |
| $60\%$ of referred women could be tracked at the higher facility; authors attribute the $40\%$ loss to incomplete documentation and demographic errors | Same study | `[V]` |
| $19\%$ of referrals were driven purely by missing resources; within those: no emergency OT ($47\%$), no NICU ($45\%$), no anaesthetist ($24\%$), no paediatrician ($22\%$) | Same study | `[V]` |
| $90.6\%$ of critically ill obstetric patients arrived with no prior communication; $70\%$ had no escort; referral slips were incomplete in $50\%$ | Safdarjung Hospital, Delhi, $3,220$ inter-facility referrals, 2018–2023 | `[V]` |
| $47.3\%$ had visited two or more hospitals before arrival ("ping-pong"); authors link this to delay | Same audit | `[V]` |

**Honest Limits:** Both studies are obstetric and urban; the Delhi audit covers one tertiary centre. The Maharashtra denominator is $25,253$ in some reports and $28,020$ in others `[CONFLICT]` (the $47\%$, $37\%$, and $60\%$ figures reproduce with $25,253$, so only percentages are quoted). No national prevalence, no measured ambulance time lost to referral failure in India, and no mortality effect of digital handshakes were found `[GAP]`. All claims in this repository are strictly **operational** (handover reliability, documentation completeness, traceability), never clinical outcomes.

---

## 2. Locked Problem Statement & Three-Part USP

> **How can an emergency referral stop being a message and become a verifiable contract: one that is offered, answered, negotiated, owned by exactly one destination, escalated automatically when nobody responds, never delays care, works from a feature phone to a command centre, survives failures, and closes with an outcome back to the referrer, with its guarantees provable rather than promised?**

### The Verifiable Referral Contract (RHP-1)
1. **Contract Semantics:** Offer, acknowledge (`ACK`), `ACCEPT` (with one-by-one resource confirmations), `COUNTER` ($\le 2$ rounds inside the decision deadline), or `DECLINE` (with structured reason codes); single-owner lease with monotonic `lease_epoch` fencing; two-level timed escalation (intra-facility notice ladder $\rightarrow$ next catchment facility $\rightarrow$ dispatcher fallback); parallel transport track that is **never gated** by handshake state; mandatory closure outcome.
2. **Reach Without Dependency:** React PWA desks, native Android foreground location service (with PWA ambulance fallback), outbound Exotel voice IVR with AMD + keypress-1 gate and DTMF PIN for feature phones, DLT-compliant static SMS alerts, Crockford Base32 + $\bmod 37$ paper codes (the referral card prints as the physical slip to prevent double-entry), offline outbox, and dispatcher proxy entry.
3. **Provability (The Guarantee Arena):** A frozen control-plane specification in Quint (`rhp1.qnt`), conformance test vectors, a 200-way concurrent accept barrier test (`race200`), a 6-part mutation test suite (`M1–M6`), an **independent runtime monitor** (written by Person B from prose without importing server code), an append-only RFC 8785 JCS hash-chained event log with C2SP-style Ed25519 Merkle checkpoints every $5\text{ s}$, a pure-JS browser verifier, and a scratch-isolated `BROKEN_BUILD=1` switch that proves the monitor catches double-lease bugs within $\le 2\text{ s}$.

### The Coherence Rule
Every component in ReferralHandshake is strictly one of:
* **(a)** A state or event in the contract,
* **(b)** An interface that produces or consumes those events, or
* **(c)** A read-only projection of the committed event log.

---

## 3. System Architecture & Locked Technology Stack

```
 PRODUCERS / CONSUMERS (interfaces)              CORE (contract)                        READERS (projections of log)
 ┌──────────────────────────────┐   ┌──────────────────────────────────────┐   ┌─────────────────────────────────┐
 │ PWA desks (QR join, SSE)     │   │ FastAPI  apply_command()  10 steps   │   │ Python Monitor (own transitions)│
 │ Android EMT app (Kotlin)     │──▶│ lock order referral>offer>deadline>  │──▶│ Witness/signer (separate OS user)│
 │ Exotel IVR (outbound voice)  │   │   outbox ; idempotency ; fencing     │   │ Browser verifier (pure JS)      │
 │ DLT SMS (static alert+link)  │   │ PostgreSQL 16 primary, sync commit   │   │ Command centre, XES, FHIR export│
 │ Paper code (Crockford+mod37) │   │ Poller (2-phase) · Outbox relay      │   │ Big screen / Guarantee Arena    │
 │ Dispatcher console (proxy)   │   └──────────────────────────────────────┘   └─────────────────────────────────┘
 └──────────────────────────────┘
```

| Layer | Locked Choice | Rationale |
|---|---|---|
| **Database** | PostgreSQL 16 (single writable primary, `synchronous_commit=on`, `log_lock_waits=on`, `READ COMMITTED`) | Per-referral `SELECT … FOR UPDATE`, partial unique index `one_lease`, `SKIP LOCKED` workers, deferred constraint triggers |
| **API & Workers** | Python 3.12, FastAPI, `psycopg3`, Pydantic v2 (`extra='forbid'`), `argon2-cffi`, `cryptography` | 10-step `apply_command()` pipeline, autonomous PIN failure counter, AES-256-GCM envelope encryption |
| **Web Clients** | React 18 PWA (TypeScript, Vite, Tailwind), SSE (`Last-Event-ID`, $15\text{ s}$ heartbeats) | Pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256` for iOS Safari & LAN HTTP compatibility |
| **Mobile** | Kotlin Android (`FOREGROUND_SERVICE_TYPE_LOCATION`, Room outbox, empty-payload FCM) + PWA fallback | Deterministic background location; zero PHI in push payloads |
| **Voice / SMS** | Exotel outbound IVR ($\le 10$ whitelisted trial numbers, HTTP 200 within $5\text{ s}$ `[V]`), DLT static SMS | Feature-phone reach with AMD + press-1 gate and per-`call_sid` PIN lockout |
| **Proof & Chaos** | Quint (`rhp1.qnt`), independent Python monitor, `pytest` + `hypothesis`, Shopify Toxiproxy | Bounded model checking ($F=3, E=4$), differential state fold, network/DB fault injection |
| **Banned** | **NO** blockchain, Kafka, Redis, Kubernetes, WhatsApp, on-device LLM, or CRDT for authoritative state | Explicitly prohibited by architecture specification §0 |

---

## 4. Formal Invariants (`I1–I16`) & Global Lock Discipline

### Global Lock Order (`F1`, `I14`)
All multi-table paths acquire locks strictly in the total order:
$$\text{referral} \rightarrow \text{offer (ORDER BY id)} \rightarrow \text{deadline (ORDER BY id)} \rightarrow \text{outbox}$$
* The **Poller** runs in two phases: Phase 1 claims due rows in a single committed `UPDATE … FOR UPDATE SKIP LOCKED` statement without holding a referral lock; Phase 2 invokes `apply_command(TIMEOUT)`, which locks `referral` first.
* Database trigger `rhp_require_lock()` verifies that session GUC `rhp.locked_referral` matches the target referral before any contract-state write.

### Invariant Summary
| ID | Type | Invariant Predicate | Primary Enforcement |
|---|---|---|---|
| **I1** | Liveness | Every non-terminal referral has $\ge 1$ `PENDING` deadline and a responsible role; acted on within $\tau$ | Deferred constraint trigger `i1_pending_deadline` at `COMMIT` + 2-phase poller |
| **I2** | Safety | At most $1$ active lease per referral; `lease_epoch` strictly increases | Partial unique index `one_lease` (`WHERE status = 'ACCEPTED'`) + referral row lock |
| **I3** | Safety | `TR_UPDATE` is accepted in every non-terminal `hs_state` (never block care) | Transport path never gates on `hs_state` |
| **I4** | Safety | Each client `event_id` appears once; per-referral `seq` is gap-free ($1 \dots n$) | `idempotency` PK + advisory try-lock, `event.event_id UNIQUE`, `rhp_event_guard` trigger |
| **I5** | Safety | Hash chain and checkpoint signatures verify; `CLOSED`/`CANCELLED` require an outcome | Append-only triggers (`rhp_no_mutate`), `rhp_event_guard`, `CHECK` constraint |
| **I6** | Safety | Every `ACCEPT`/`COUNTER`/`DECLINE` is from a rostered role, registered device/number, verified PIN, or flagged proxy | Pipeline steps 2, 3, and 5 + autonomous `pin_failed` counter |
| **I7** | Safety | System-chosen offer targets belong to `referral.chain`; dispatcher offers carry `source='DISPATCHER'` | Trigger `offer_chain_guard` |
| **I8** | Safety | Stale `expected_version` or `expected_epoch` is never applied and is logged | Step 5 fencing check $\rightarrow$ HTTP `412` + `rejected_command` via savepoint rollback |
| **I9** | Safety | A facility appears at most once as an offer target per referral (no referral loops) | `UNIQUE (referral_id, facility_id)` on `offer` |
| **I10** | Safety | Clinical payload frames are emitted only to subscribers with an active `payload_grant` | Per-event SSE filter + `GRANT_REVOKED` control frame on revoke |
| **I11** | Safety | `event.detail` contains only allowlisted keys with enum, UUID, boolean, or $\le 12$-digit integer values | Pydantic `Literal` schemas + PostgreSQL `rhp_detail_ok(type, detail)` `CHECK` |
| **I12** | Safety | At most $2$ open offers (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) per referral | `referral.open_offers CHECK (BETWEEN 0 AND 2)` maintained under referral lock |
| **I13** | Safety | Configured worst-case escalation time satisfies $T_{\max} \le B$ for the active profile | Startup validator + Ed25519 cold-key signature verification |
| **I14** | Safety | No contract-state write occurs without holding the referral row lock | Trigger `rhp_require_lock` checking `current_setting('rhp.locked_referral', true)` |
| **I15** | Safety | No lease is granted from a resource confirmation expired at `server_ts` | Step 7 check (`expires_at > server_ts`) $\rightarrow$ HTTP `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` |
| **I16** | Safety | Per-referral `server_ts` is monotonically non-decreasing | `GREATEST(clock_timestamp(), referral.head_ts)` under lock + `rhp_event_guard` |

---

## 5. Timing Profiles & $T_{\max}$ Bound (`F2`, `F3`, `I13`)

Inside the ACK window $A$, the unified notice ladder fires at rungs $(0, A/4, 3A/4)$:
* $t = 0$: SSE + empty-payload FCM wake ping to all rostered slots concurrently.
* $t = A/4 + i \cdot \delta$: Outbound Exotel voice IVR call to slot $i \in \{0 \dots S-1\}$.
* $t = 3A/4$: Dispatcher phone-assisted proxy page.

Worst-case time from `CREATE` to `ESCALATED_TO_DISPATCHER` across $F$ facilities with decision window $D$ and per-hop budget $\epsilon$:
$$T_{\max} = F \cdot (A + D + \epsilon) \le B$$

| Profile | $A$ ($\text{ms}$) | $D$ ($\text{ms}$) | $F$ | $\epsilon$ ($\text{ms}$) | $T_{\max}$ | Bound $B$ | Allowed with `REAL_DATA=1`? |
|---|---|---|---|---|---|---|---|
| `PILOT_OB_CRITICAL` | $60,000$ | $180,000$ | $3$ | $3,000$ | $729\text{ s}$ | $900\text{ s}$ | Yes |
| `PILOT_STANDARD` | $120,000$ | $300,000$ | $3$ | $3,000$ | $1,269\text{ s}$ | $1,500\text{ s}$ | Yes |
| `DEMO_FAST` | $3,000$ | $4,000$ | $3$ | $1,000$ | $24\text{ s}$ | $25\text{ s}$ | **No** (refuses boot) |
| `DEMO_VOICE` | $45,000$ | $20,000$ | $2$ | $1,000$ | $132\text{ s}$ | $150\text{ s}$ | **No** (refuses boot) |

---

## 6. Repository Structure & Feature Tiers

```
.
├── AGENTS.md                        # Mandatory builder rules for Google Antigravity
├── README.md                        # Project overview, architecture & claims register
├── docker-compose.yml               # Full local-first stack (pg, api, poller, relay, monitor, witness, toxiproxy, pwa, tunnel)
├── .env.example                     # Template environment variables (REAL_DATA=0 locked)
├── spec/                            # READ-ONLY locked specifications & formal artifacts
│   ├── ReferralHandshake_LOCKED_Problem_Statement_v7.md
│   ├── ReferralHandshake_v8_LOCKED_Solution.md
│   ├── ReferralHandshake_FINAL_LOCKED_Architecture.md
│   ├── ReferralHandshake_3Gem_Antigravity_Workflow.md
│   ├── transitions.yaml             # Frozen transition table consumed by server & explorer
│   ├── profiles.signed.json         # Ed25519 cold-key signed timing profiles
│   ├── rhp1.qnt                     # Quint control-plane model (Person A)
│   └── ddl/
│       ├── 01_schema.sql            # 24-table PostgreSQL 16 DDL + triggers + roles
│       └── 02_scratch_broken.sql    # Isolated rhp_scratch_broken DB without one_lease (F20)
├── api/                             # Lane A: FastAPI server, apply_command(), poller, relay
│   ├── pyproject.toml
│   ├── rhp/
│   └── tests/                       # race200, mutation suite M1-M6, idempotency, Toxiproxy
├── monitor/                         # Lane B: Independent Python runtime monitor (UID 1001)
│   └── monitor.py                   # Written from §3 prose; imports zero server code
├── witness/                         # Lane A/B: Separate OS user (UID 1002) Ed25519 Merkle signer
│   └── signer.py
└── pwa/                             # Lane B: React 18 PWA desks, Guarantee Arena & pure-JS verifier
    ├── package.json
    └── src/
```

### Feature Tiers & Cut Order (§2)
* **T0 (Never Cut):** FastAPI `apply_command()`, PostgreSQL 16, 2-phase poller, outbox relay, PWA desks with rotating QR admission, independent runtime monitor, witness + pure-JS browser verifier, `BROKEN_BUILD` scratch DB.
* **T1 (`T1_TRANSPORT`, Cut 3rd):** PWA ambulance GPS tracker, dispatcher console + proxy entry, replay scrubber.
* **T2 (`T2_REACH`, Cut 2nd):** Exotel outbound voice IVR (AMD + press-1 gate), DLT-style SMS stub, Crockford Base32 + $\bmod 37$ paper code.
* **T3 (`T3_EXTRAS`, Cut 1st):** Native Kotlin Android app, AI intake accelerator with Cognitive Forcing Functions (`423 ANCHOR_REQUIRED`), FHIR R4 / IEEE 1849 XES export.

---

## 7. Quickstart & Verification Suite

### 1. Environment Setup
```bash
cp .env.example .env
# Verify REAL_DATA=0 and PROFILE=DEMO_FAST in .env
```

### 2. Launch the Stack
```bash
docker compose up --build -d
```
* **PWA & Guarantee Arena Big Screen:** `http://localhost:5173`
* **Command API & Health/Metrics:** `http://localhost:8000/healthz`
* **Toxiproxy Control Port:** `http://localhost:8474`

### 3. Run the Proof & Conformance Gates (§12, §24)
```bash
# 1. Bounded model checking & vacuity checks (Quint)
quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000

# 2. 200-way concurrent ACCEPT barrier test (race200) + lock-order deadlock check (T-F1)
docker compose exec api pytest tests/test_race200.py -v

# 3. Six-part mutation suite (M1-M6) & idempotency matrix (T-F14)
docker compose exec api pytest tests/test_mutations.py tests/test_idempotency.py -v

# 4. Pure-JS browser verifier & Crockford Base32 + mod 37 paper code tests
docker compose exec pwa npm test
```

### 4. The 30-Second Live Proof Loop (`DEMO_FAST`)
1. **$0\text{–}4\text{ s}$:** Judges scan the rotating QR code (`jti` valid $20\text{ s}$, rotates every $15\text{ s}$) to join as competing hospital desks `D1` and `D2`.
2. **$4\text{–}7\text{ s}$:** Create a `PARALLEL2` obstetric referral; both desks receive the offer via SSE.
3. **$7\text{–}12\text{ s}$:** Both judges press **Accept** simultaneously $\rightarrow$ exactly one receives HTTP `200` (`lease_epoch = 1`), the other receives HTTP `409 LEASE_HELD`; monitor stays green.
4. **$12\text{–}18\text{ s}$:** Flip `BROKEN_BUILD=1` (routes strictly to isolated `rhp_scratch_broken` DB with flashing red banner); both press Accept $\rightarrow$ two leases granted; independent monitor turns red with `I2` violation within $\le 2\text{ s}$.
5. **$18\text{–}21\text{ s}$:** Flip back to `BROKEN_BUILD=0`; monitor returns green.
6. **$21\text{–}27\text{ s}$:** Tamper with one event row in `psql` $\rightarrow$ the pure-JS browser verifier on judges' phones pinpoints `BROKEN referral=… seq=… kind=HASH`.
7. **$27\text{–}30\text{ s}$:** Display live-measured `I1–I16` counters and $p_{50}/p_{95}$ event latency.

---

## 8. Claims Register & Residual Risks (§19, §20)

| Authorized Wording (May Claim) | Forbidden Claim (Must Never Claim) |
|---|---|
| Referral communication and documentation gaps are documented in specific urban Indian studies (Das et al., 2023; Safdarjung 2018–23) | National prevalence; deaths prevented; lives saved |
| Hard single-owner guarantees were not found in public documentation of the systems audited | "First", "only", or "no competitor has this" |
| Designed to comply; synthetic data only (`REAL_DATA=0`); ABDM-sandbox aligned only if sandbox calls are made | "ABDM compliant"; "production ready" |
| Every identified weakness is `CLOSED`, `BOUNDED` with a stated residual, or `OPEN` with an owner | "Bullet-proof", "airtight", "zero loopholes", "guaranteed", "immune", "crash-proof" |
| Control-plane model checked within stated bounds ($3$ facilities, $4$ epochs); code checked by vectors, tests, and a live independent monitor | "Mathematically proven system" |
| Tamper-evident log with independent witnesses; BSA s.63-ready export bundle | "Immutable log"; "BSA certified" |
| Escalation and capacity signalling are operational hypotheses for an ethics-approved pilot | "Eliminates ping-pong"; creates hospital bed capacity |