# ReferralHandshake (Protocol RHP-1) — Live Build & Verification State (`CURRENT_STATE.md`)

**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru, 24h Build)
**Input Precedence (Locked):** `Problem_Statement_v7.md` > `[V]` Research > `v8_LOCKED_Solution.md` > `FINAL_LOCKED_Architecture.md` > `3Gem_Antigravity_Workflow.md`
**Data Mode:** `REAL_DATA=0` (Synthetic data only; demo profiles refuse boot if `REAL_DATA=1`)

> **AGENT DIRECTIVE:** This file is the authoritative context anchor for **Gem 1 (CONDUCTOR)**, **Gem 2 (MILESTONE VALIDATOR)**, and **Google Antigravity**. Before starting or auditing any task, read the **Active State Ledger (§1)** and verify that no **Common-Mode Independence (§2)** or **Hard Architectural Locks (§3)** are violated. Update this file at the end of every accepted loop.

---

## 1. Active State Ledger (Copy-Paste into Every Packet)

```text
=== STATE LEDGER v0 ===
Clock: Phase P (Pre-Event) / H00 of 24 | Active Profile: DEMO_FAST | REAL_DATA=0
Lane A (Person A - Backend/Proof) Step: P1 | Branch: lane-a/main | Last Good Tag: init-spec-lock
Lane B (Person B - Clients/Reach/Monitor) Step: P4 | Branch: lane-b/main | Last Good Tag: init-spec-lock
Gates:  G0(T0)[ ]  G1(T1)[ ]  G2(T2)[ ]  G3(Rehearsal)[ ]  FREEZE H22[ ]
Done Steps: [none]
Open Defects: [none]
Accepted Risks (User-Approved):
  - R-L1 [OPEN] Voice legality unsettled -> Sandbox + synthetic de-identified prompts + <=10 whitelisted numbers
  - R-L2 [OPEN] DPDP s.8(7) erasure vs NMC 3-yr retention -> Parameterised retention; handover record only
  - R-S3 [OPEN] Signer key theft -> Separate OS user (rhp-sign, 0400 key) + cold-key RESTORE drill
Approved Spec Deviations: none
Cut So Far: none (Cut order if behind schedule: T3 -> T2 -> T1; T0 is NEVER cut)
Next 3 Steps (Lane A): P1 -> P2 -> P3 (then E0 -> E1 -> E2)
Next 3 Steps (Lane B): P4 -> P5 -> P6 (then E0 -> E1 -> E2)
```

---

## 2. Lane Ownership & Common-Mode Independence Boundary (F17)

To prevent the specification, server, and runtime monitor from sharing a common-mode bug (F17), file ownership is strictly partitioned between **Person A (Lane A)** and **Person B (Lane B)**:

| Artifact / Directory | Owner | DB Role | Common-Mode & CODEOWNERS Rule |
|---|---|---|---|
| `spec/transitions.yaml`, `spec/rhp1.qnt`, `spec/vectors/` | **Lane A** (Person A) | N/A | Frozen after Phase P (`CODEOWNERS` hash-pinned in CI). AI agents may NEVER edit spec/vectors to make a failing build pass. |
| `db/schema.sql` (24-table PG16 DDL), `scripts/make_scratch.sh` | **Lane A** (Person A) | `postgres` (DDL) | Locked to `FINAL_LOCKED_Architecture.md` §7. Any schema change requires human-signed `SPEC-DEVIATION`. |
| `api/` (`apply_command`, `poller.py`, `relay.py`) | **Lane A** (Person A) | `rhp_app` | All contract writes go exclusively through the 10-step `apply_command()` pipeline under session GUC `rhp.locked_referral`. |
| `witness/` (Ed25519 checkpoint signer, Merkle tree) | **Lane A** (Person A) | `rhp_witness` | Runs under separate OS user `rhp-sign` (UID 1002, key mode `0400`). |
| `monitor/` (Independent Python runtime monitor) | **Lane B** (Person B) | `rhp_monitor` | **CRITICAL (F17):** Built in a separate Antigravity workspace that is **NEVER** shown `api/` server code. Written strictly from §3 prose, importing zero server modules, reading `event`, `referral`, `offer`, `deadline`, `checkpoint`, `heartbeat`, `outbox`, `rejected_command` in `REPEATABLE READ READ ONLY`. |
| `pwa/` (React PWA desks, QR join, SSE, pure-JS verifier, GPS fallback) | **Lane B** (Person B) | via HTTP API | Uses `@noble/curves/ed25519` and `@noble/hashes/sha256` (no WebCrypto dependency on LAN HTTP). |
| `reach/` (Exotel outbound IVR, DLT SMS stub, Crockford mod-37 paper code) | **Lane B** (Person B) | via HTTP API | Outbound voice requires AMD + press-1 gate before committing `ACK`; webhook budget $\le 2\text{ s}$. |
| `android/` (Kotlin foreground location service, Room outbox) | **Lane B** (Person B) | via HTTP API | Tier `T3_EXTRAS` (built only after G0–G2 pass). |

---

## 3. Hard Architectural Locks Checklist (Gem 2 Milestone Validation Gate)

Gem 2 MUST verify every item in this table on every `HIGH` risk loop:

- [x] **Coherence Rule:** Every component is (a) a contract state/event, (b) an interface producing/consuming events, or (c) a read-only projection of the event log.
- [x] **Zero Banned Tech:** No blockchain, Kafka, Debezium, Redis, Kubernetes, WebSockets, WhatsApp, on-device LLM, CRDT for authoritative state, or floats in RFC 8785 JCS JSON.
- [x] **Total Lock Order (F1 / I14):** Strictly `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`. Enforced by DB trigger `rhp_require_lock` checking `current_setting('rhp.locked_referral', true)`.
- [x] **Two-Phase Stateless Poller (F1):** Phase 1 claims due rows via a single committed `UPDATE deadline SET claimed_until = clock_timestamp() + interval '5 seconds' ... FOR UPDATE SKIP LOCKED` statement without holding a referral lock. Phase 2 invokes `apply_command(TIMEOUT)`.
- [x] **Step-1 Idempotency & Savepoint Rejections (F14):** `pg_try_advisory_xact_lock(hashtextextended(actor_id || ':' || key, 0))` runs in Step 1 before locking `referral`. Domain rejections (`409`/`412`/`422`) roll back to `SAVEPOINT sp_cmd`, insert into `rejected_command`, and mark `idempotency` as `DONE` so retries replay the exact rejection.
- [x] **Two Independent Tracks (I3 & D1):** Transport (`REQUESTED -> DISPATCHED -> EN_ROUTE -> ARRIVED -> HANDED_OVER | TR_CANCELLED`) never reads `hs_state`. `mgso4_status` (`GIVEN | NONE_GIVEN | UNKNOWN`) is answer-required, never blocks dispatch.
- [x] **Fencing vs Racing (D7, I2, I8, I12, F13):** Stale `expected_version`/`expected_epoch` returns `412` (logged in `rejected_command`). Lost race returns `409` (`LEASE_HELD`, `LATE_ACCEPT_REJECTED`, `STALE_CONFIRMATION_RECONFIRM_REQUIRED`). `one_lease` partial unique index + `open_offers BETWEEN 0 AND 2`.
- [x] **Timing Bound (F2, F3, I13):** Rungs at $0$, $A/4$, $3A/4$. $T_{max} = F \cdot (A + D + \epsilon) \le B$ verified at startup. Server timestamps use `GREATEST(clock_timestamp(), referral.head_ts)` (I16).
- [x] **Safe `BROKEN_BUILD` (F20):** Routes exclusively to `rhp_scratch_broken` (missing `one_lease` and code lease check); hard-aborts (exit 78) if `REAL_DATA=1` or if pointed at primary DB.

---

## 4. Step-by-Step Build Catalogue & Live Tracker

### 4.1 Phase P — Pre-Event Spec Artifacts (Documents & Verification Only `[verify against event rules]`)

| Step ID | Lane | Description | Spec Anchors | Risk | Loop Type | Status | Commit / Tag | Evidence / Notes |
|---|---|---|---|---|---|---|---|---|
| **P1** | A | Author `spec/transitions.yaml` & conformance vectors (28 scenarios + edge cases) | §4, §5, v8 §4.8 | HIGH | FULL | `[ ] PENDING` | — | Must cover all 14 commands & v7 12-state mapping |
| **P2** | A | Load 24-table PG16 DDL (`db/schema.sql`), run FK/constraint scan (`ST-3`) | §7, F1, F4, F9 | HIGH | FULL | `[ ] PENDING` | — | Verify deferred `referral_lease_fk` & `rhp_detail_ok` |
| **P3** | A | Quint spec (`spec/rhp1.qnt`); run `quint run safety` (20k samples) + vacuity checks | §12, I1, I2, I12, I13 | HIGH | FULL | `[ ] PENDING` | — | Vacuity checks on `ACCEPTED`, `DISPATCH`, `CLOSED`, `SOFT` must fail |
| **P4** | B | Signed profile file (`spec/profiles.json`) + $T_{max}$ startup validator (`T-F2`, `T-F3`) | §6, F2, F3, I13 | MED | FAST | `[ ] PENDING` | — | Verify `PILOT_OB_CRITICAL` ($729\text{ s} \le 900\text{ s}$) & `DEMO_FAST` ($24\text{ s} \le 25\text{ s}$) |
| **P5** | B | Synthetic seed data (`db/seed.sql`, `REAL_DATA=0`): Karnataka tiers, rosters, chains | §2, §7, §9, §10 | LOW | FAST | `[ ] PENDING` | — | PHC -> CHC -> FRU -> DH -> MC + DISPATCH |
| **P6** | B | Execute §21 Pre-Event Verification Checklist (12 time-boxed hardware/API checks) | §21 | LOW | FAST | `[ ] PENDING` | — | Record Exotel, iPhone LAN QR, noble Ed25519 results |

### 4.2 Phase E — 24-Hour Hackathon Build (`Colossus 3.0`)

| Step ID | Hours | Lane | Task Scope | Spec Anchors | Risk | Loop | Status | Commit / Tag | Gate |
|---|---|---|---|---|---|---|---|---|---|
| **E0-A** | H00–H02 | A | Repo scaffold, `docker-compose.yml`, DDL load, seed load, `transitions.yaml` loader | §7, §17 | MED | FAST | `[ ] PENDING` | — | — |
| **E0-B** | H00–H02 | B | React PWA shell, rotating single-use QR admission (`jti`, 20s TTL, cap 20), Turnstile/LAN mode | §9, §13, §17 | MED | FAST | `[ ] PENDING` | — | — |
| **E1-A** | H02–H06 | A | `apply_command()` 10-step pipeline: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `DECLINE`, `REVOKE_GRANT` | §4, §5, I1–I16, F1, F7, F12, F14 | HIGH | FULL | `[ ] PENDING` | — | — |
| **E1-B** | H02–H06 | B | Receiving desk UI (priority queue, no countdowns, red `mgso4_status=UNKNOWN` banner), SSE with `Last-Event-ID` & per-event `payload_grant` filter | §8, §9, §13, F10, I10 | HIGH | FULL | `[ ] PENDING` | — | — |
| **E2-A** | H06–H09 | A | Two-phase stateless `poller.py`, visibility-timeout `relay.py`, `TIMEOUT` command, unified notice ladder ($0, A/4, 3A/4$) | §5, §6, §8, F1, F2, F3 | HIGH | FULL | `[ ] PENDING` | — | — |
| **E2-B** | H06–H09 | B | Guarantee Arena big screen UI + **Independent Python Monitor** (`monitor/monitor.py` in isolated workspace) | §3, §12, F17 | HIGH | FULL | `[ ] PENDING` | — | — |
| **E3-A** | H09–H12 | A | RFC 8785 JCS hash chain, envelope encryption (DEK/KEK), `witness` signer (`rhp-sign` UID 1002, 5s Merkle checkpoints, inclusion proofs, cold-key `RESTORE`) | §10, §11, F8, F9, I5, I11 | HIGH | FULL | `[ ] PENDING` | — | — |
| **E3-B** | H09–H12 | B | Browser pure-JS verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`), Merkle path fold, tamper vs restore detection | §11, §13, F8, I5 | HIGH | FULL | `[ ] PENDING` | — | — |
| **E4-A** | H12–H14 | A | 200-way barrier race (`race200`), Toxiproxy 8-toxic suite, mutation tests `M1–M6` | §12, §18, §24, F1, F17 | HIGH | FULL | `[ ] PENDING` | — | **G0 (T0 Pass)** |
| **E4-B** | H12–H14 | B | `BROKEN_BUILD=1` scratch DB (`rhp_scratch_broken`), exit-78 safety guards, flashing red banner, 30s proof loop wiring | §12, §17, §24, F16, F20 | HIGH | FULL | `[ ] PENDING` | — | **G0 (T0 Pass)** |
| **E5-A** | H14–H17 | A | `COUNTER`, `CONFIRM_COUNTER`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`, `TR_UPDATE`, `TR_DESTINATION_CHANGE`, 6 arrival cases, two-stage `CLOSURE` | §4, F5, F6, F13, I3 | HIGH | FULL | `[ ] PENDING` | — | **G1 (T1 Pass)** |
| **E5-B** | H14–H17 | B | Dispatcher console (proxy entry with reason enum, override), PWA ambulance GPS (`watchPosition` + 200m geofence hint), replay time-scrubber | §4, §8, §13, §14, F5 | HIGH | FULL | `[ ] PENDING` | — | **G1 (T1 Pass)** |
| **E6-A** | H17–H20 | A | Full idempotency matrix (`T-F14`), stale confirmation reconfirm flow (`T-F12`), autonomous PIN failure counter & per-session lockout (`T-F7`) | §5, §8, §9, F7, F12, F14 | HIGH | FULL | `[ ] PENDING` | — | **G2 (T2 Pass)** |
| **E6-B** | H17–H20 | B | Exotel outbound IVR webhook (`inbox` dedupe, AMD + press-1 gate, 2s budget, PIN + `%23`), DLT SMS stub, Crockford Base32 + mod-37 paper code slip | §8, F7, I4, I6 | HIGH | FULL | `[ ] PENDING` | — | **G2 (T2 Pass)** |
| **E7-AB** | H20–H22 | A+B | Defect closure from tests; record MP4 fallback clips (Clips A, B, C, D); full 30s loop + 5-min pitch rehearsal $\times 3$ | §17, §24, F16 | MED | FULL | `[ ] PENDING` | — | **G3 (Rehearsal)** |
| **E8-AB** | H22–H24 | A+B | **CODE FREEZE AT H22.** Config-only tuning, backup laptop sync, hotspot + LAN QR preflight | §17, §21 | LOW | FAST | `[ ] PENDING` | — | **FREEZE** |
| **T3-OPT**| Post-G2 | A+B | *(Optional if G0–G2 green)* Kotlin foreground GPS service, AI intake with Cognitive Forcing Function (`423 ANCHOR_REQUIRED`), FHIR R4 / XES export | §13, §15, §16, §24 | MED | FAST | `[ ] CUT/OPT` | — | **T3 (Extras)** |

---

## 5. Tier Acceptance Gates (§24 Definition of Done)

No tier may be marked `[x] PASSED` in the State Ledger until Antigravity pastes the raw command output proving every metric below and Gem 2 + Gem 3 sign off in a `FULL` loop:

### Gate G0 — Tier T0 (Core Contract, Proof & Guarantee Arena) — **NEVER CUT**
- [ ] **`T-C1 race200`:** 200 concurrent `ACCEPT` requests across 2 competing offers -> exactly `1` HTTP `200`, `199` HTTP `409`/`412`, `1` `ACCEPTED` row in `offer`, `max(seq) - count(*) == 0` (gap-free), PostgreSQL deadlock counter delta `== 0`.
- [ ] **Mutation Suite (`T-F17` / `M1–M6`):**
  - [ ] `M1` (skip `expected_epoch` fencing) -> trips monitor `I8` + vector `V-STALE-EPOCH`.
  - [ ] `M2` (drop `FOR UPDATE` & `one_lease` on scratch) -> trips `race200` + monitor `I2`.
  - [ ] `M3` (poller holds `deadline` lock across `apply_command`) -> trips `T-F1` (`deadlocks_delta > 0` / `I14`).
  - [ ] `M4` (remove `open_offers` cap guard in Quint) -> `quint run safety` produces `I12` counterexample.
  - [ ] `M5` (write `prev_hash` as zeros) -> trips browser verifier & monitor `I5 (kind=PREV)`.
  - [ ] `M6` (`ACCEPT` ignores confirmation `expires_at`) -> trips vector `V-STALE-CONFIRM` + monitor `I15`.
- [ ] **Quint Verification:** `quint run rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000` passes; vacuity checks on `ACCEPTED`, `DISPATCH`, `CLOSED`, `SOFT` fail as required.
- [ ] **Continuous Monitor & Chaos:** 0 invariant violations over a 10-minute Hypothesis stateful + Toxiproxy fault-injection run.
- [ ] **Tamper Verifier (`T-F8`):** Editing 1 row in `psql` causes pure-JS verifier to print `BROKEN referral=<id> seq=<n> kind=HASH`.
- [ ] **Broken-Build Switch (`T-F20`):** `BROKEN_BUILD=1` on `rhp_scratch_broken` turns monitor red (`I2`) within $\le 2\text{ s}$ and green after switch-back; aborts with exit code `78` if `REAL_DATA=1`.
- [ ] **Liveness Bound (`DEMO_FAST`):** Silence-to-dispatcher measured at $\le 25\text{ s}$ ($T_{max} = 24\text{ s}$).

### Gate G1 — Tier T1 (`T1_TRANSPORT`: Parallel Transport, Dispatcher Proxy, Replay)
- [ ] **Proxy Equivalence:** Dispatcher proxy entry and direct API entry produce identical state and event sequences across 20 paired runs.
- [ ] **Track Independence (`T-I3`):** `TR_UPDATE` succeeds in every non-terminal `hs_state`; geofence emits `ARRIVAL_SUGGESTED` only; human confirms `ARRIVED`.
- [ ] **Chain Exhaustion & Closure (`T-F6`):** `ESCALATED_TO_DISPATCHER` reached deterministically; `DISPATCHER_ASSIGN` grants lease with `source='DISPATCHER'`; two-stage `CLOSURE` deadline resolves to `UNKNOWN_COUNTER_REFERRAL` if unclosed.
- [ ] **Replay Scrubber:** Time-scrubber reconstructs exact referral state at every `seq` from the event log.

### Gate G2 — Tier T2 (`T2_REACH`: Exotel IVR, DLT SMS, Paper Code)
- [ ] **Voice ACK Integrity (`T-F7`):** 20/20 voice `ACK`s committed only after press-1 gate + DB commit; voicemail/silence yields `0` `ACK`s across 5 trials; webhook p95 latency $\le 2\text{ s}$.
- [ ] **Paper Code Checksum:** 8-char Crockford Base32 + mod-37 check character rejects 100% of single-symbol errors and adjacent transpositions across 1,000 mutated codes.
- [ ] **Idempotency & Lockout (`T-F14`, `T-F7`):** All 8 idempotency edge cases pass; 3 failed PIN attempts lock only that `session_id`/`call_sid` (autonomous commit) without locking out the facility's duty role.

### Gate G3 — Tier T3 (`T3_EXTRAS` — Optional) & Final Rehearsal
- [ ] **30-Second Proof Loop (`T-F16`):** Rehearsed $3\times$ end-to-end inside 30 seconds; MP4 fallback clips A, B, C, D recorded and verified.
- [ ] *(If T3 built)* Android GPS soak $\ge 2\text{ h}$ screen-off; AI draft returns `423 ANCHOR_REQUIRED` until `need_class` and `mgso4_status` committed; 20-slip seeded-error gate ($\le 5\%$ rubber-stamp, $\le 1\%$ silent omission); FHIR R4 bundle validates.

---

## 6. Invariant (I1–I16) & Fix (F1–F20) Verification Matrix

| ID | Mechanism in Code / DB | Test ID | Status | Verified In Step |
|---|---|---|---|---|
| **I1** | Deferred constraint trigger `i1_pending_deadline` + poller `< τ` | `T-I1` | `[ ]` | — |
| **I2** | Partial unique index `one_lease` + `SELECT ... FOR UPDATE` on `referral` | `T-I2` / `T-C1` | `[ ]` | — |
| **I3** | `TR_UPDATE` handler never reads `hs_state`; `mgso4_status` allows `UNKNOWN` | `T-I3` / `T-K1` | `[ ]` | — |
| **I4** | `idempotency` PK + `event.event_id UNIQUE` + `PRIMARY KEY(referral_id, seq)` + `rhp_event_guard` | `T-I4` / `T-F14` | `[ ]` | — |
| **I5** | `event_ao`/`checkpoint_ao` triggers + SHA-256 JCS chain + Ed25519 checkpoints + `outcome` CHECK | `T-I5` / `T-F8` | `[ ]` | — |
| **I6** | Pipeline steps 2–3 (session/roster validity + Argon2id PIN) or `proxy=true` | `T-I6` / `T-F7` | `[ ]` | — |
| **I7** | Trigger `offer_chain_guard` (`source='CHAIN'` must be in `referral.chain`) | `T-I7` | `[ ]` | — |
| **I8** | Pipeline step 5 (`expected_version`/`expected_epoch` check -> `412` + `rejected_command`) | `T-I8` | `[ ]` | — |
| **I9** | `UNIQUE(referral_id, facility_id)` on `offer` | `T-I9` | `[ ]` | — |
| **I10** | Per-event SSE `payload_grant` check + `GRANT_REVOKED` frame | `T-I10` / `T-F10` | `[ ]` | — |
| **I11** | Pydantic `extra='forbid'` + DB `CHECK (rhp_detail_ok(type, detail))` | `T-I11` / `T-F9` | `[ ]` | — |
| **I12** | `CHECK (open_offers BETWEEN 0 AND 2)` on `referral` | `T-I12` / `T-F13` | `[ ]` | — |
| **I13** | Startup `validate(profile)` checking $F \cdot (A + D + \epsilon) \le B$ | `T-I13` / `T-F3` | `[ ]` | — |
| **I14** | Trigger `rhp_require_lock` checking GUC `rhp.locked_referral` | `T-I14` / `T-F1` | `[ ]` | — |
| **I15** | Pipeline step 7 checking `offer_resource_confirmation.expires_at > server_ts` | `T-I15` / `T-F12` | `[ ]` | — |
| **I16** | `GREATEST(clock_timestamp(), referral.head_ts)` + `rhp_event_guard` | `T-I16` / `T-F11` | `[ ]` | — |