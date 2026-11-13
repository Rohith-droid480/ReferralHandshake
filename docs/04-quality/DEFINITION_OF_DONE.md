# ReferralHandshake (Protocol RHP-1) — Definition of Done & Tier Acceptance Gates

**System:** Referral Handshake Protocol RHP-1 + Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru)  
**Authority Hierarchy:** `Problem Statement v7` $>$ Research tagged `[V]` $>$ `Solution v8` $>$ `FINAL_LOCKED_Architecture` $>$ `3Gem_Antigravity_Workflow`

---

## 1. Architectural Coherence & Non-Negotiable Locks

No feature, module, PR, or build step in ReferralHandshake may be marked **DONE** if it violates any of the following ten architectural locks:

1. **Coherence Rule (`v7 §5`, `Architecture §0`):** Every component in the repository is strictly one of:
   - **(a)** a state or event in the RHP-1 contract (`referral`, `offer`, `deadline`, `event`),
   - **(b)** an interface producing or consuming those events (`PWA`, `Android`, `Exotel IVR`, `DLT SMS`, `Paper Code`, `Dispatcher Console`), or
   - **(c)** a read-only projection of the committed event log (`Monitor`, `Witness`, `Browser Verifier`, `Command Centre`, `FHIR/XES Exporters`).
   Anything outside (a), (b), or (c) is out of scope and must be deleted.
2. **Locked Stack Only (`Architecture §0`):** Python 3.12, FastAPI, `psycopg3`, PostgreSQL 16 single writable primary (`synchronous_commit=on`, `READ COMMITTED` + explicit `SELECT ... FOR UPDATE`), React PWA (SSE with `Last-Event-ID`, $15\text{ s}$ heartbeats, bundled pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256`), Kotlin Android (`T3`) / PWA GPS (`T1`), Exotel outbound IVR, Mapbox Directions/Matrix, Toxiproxy, Quint (`rhp1.qnt`).
3. **Zero Banned Technologies (`Architecture §0`):** Repository scan (`ST-5`) confirms zero references or dependencies on blockchain, Kafka, Debezium, Redis, Kubernetes, WebSockets, WhatsApp, on-device LLMs, CRDTs for authoritative state, or floating-point numbers inside RFC 8785 JCS canonical JSON payloads.
4. **Global Lock Order (`F1`, `I14`):** All contract mutations execute through `apply_command()` acquiring locks strictly in the order `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`, with session GUC `rhp.locked_referral` enforced by trigger `rhp_require_lock`. Poller Phase 1 and Outbox Relay claims are single committed `UPDATE ... FOR UPDATE SKIP LOCKED` statements.
5. **Two Independent Tracks (`I3`, `D1`, `D2`):** Transport track (`REQUESTED -> DISPATCHED -> EN_ROUTE -> ARRIVED -> HANDED_OVER | TR_CANCELLED`) never reads `hs_state` and never blocks care. `mgso4_status` (`GIVEN | NONE_GIVEN | UNKNOWN`) is answer-required, never knowledge-required, and never blocks dispatch.
6. **Single-Owner Lease & Open-Offer Cap (`I2`, `I12`, `F13`, `D7`):** Optimistic row `version` (`412` on stale precondition) and monotonic `lease_epoch` (`409` on lost race) are separate columns. Partial unique index `one_lease` enforces at most one `ACCEPTED` offer per referral. `open_offers` (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) $\le 2$ always.
7. **Bounded Escalation Math (`F2`, `F3`, `I13`, `I16`):** Unified ACK window $A$ with notice rungs at $0$, $A/4$, and $3A/4$; worst-case escalation time $T_{max} = F \cdot (A + D + \epsilon) \le B$ verified at startup; server timestamps are monotone via `GREATEST(clock_timestamp(), referral.head_ts)`.
8. **Common-Mode Independence (`F17`, `D19`, `D30`):** Person A authors the server, `spec/transitions.yaml`, and `spec/rhp1.qnt`. Person B authors `monitor/monitor.py` in a separate clean-room workspace from `Architecture §3` prose alone, importing zero server modules and connecting via read-only role `rhp_monitor`.
9. **Synthetic Data & Scratch Isolation (`F20`):** `REAL_DATA=0` is enforced across all environments. `BROKEN_BUILD=1` runs exclusively against `rhp_scratch_broken` and hard-aborts (exit `78`) if `REAL_DATA=1` or if pointed at the main database.
10. **Claims & Evidence Discipline (`v7 §12`, `v8 §15`, `Architecture §19`):** Every number shown on screen is measured live from the event log. Zero forbidden claims appear in code, UI, or slides.

---

## 2. Milestone Definition of Done (2-Gem Milestone Validation Governance)

Under the locked 2-Gem Milestone Validation Workflow, no feature or milestone/gate (`P1`–`P6`, `E0`–`E8`, `G0`–`G3`) may transition to **DONE** in the `STATE LEDGER` until all gates below are satisfied:

| # | Gate | Owner | Mandatory Evidence Required | Automatic Failure Condition |
|---|---|---|---|---|
| 1 | **Builder Execution & Raw Output** | Antigravity | Complete `BUILD REPORT` containing: (a) `git diff --stat`, (b) full source text of every `HIGH`-risk file touched (or full diff if $>300$ lines), (c) exact shell commands executed and **raw, unedited terminal output pasted**, (d) measured test metrics, and (e) mandatory Case B routing banner. | Claiming `"tests pass"` without raw terminal output pasted, or touching any file listed in `FILES MUST NOT TOUCH`. |
| 2 | **Milestone Validation (Audit + Red-Team)** | Gem 2 (`MILESTONE VALIDATOR`) | Line-by-line conformance table mapping every `SPEC ANCHOR` to `file:line` with status `MATCH`; invariant sweep confirming enforcement mechanisms for `I1`–`I16`; adversarial attack tests (`A-1..A-k`) verified; `DECISION PACKET` with verdict `ADVANCE` (or `FIX-THEN-ADVANCE` after `MUST-FIX` closed); 0 open `S1` defects; Claims Register clean. | Any unapproved deviation, any `S1` blocker defect, or verdict `REJECT`. |
| 4 | **Self-Audit CI Green** | CI / Runner | `scripts/run_self_audit.sh` (`ST-1` through `ST-5`) passes with exit code `0`. | Any failure in `ST-1`..`ST-5`. |
| 5 | **Scope Cut & Loop Cap Rule** | Gem 1 (`CONDUCTOR`) | Step completed within $\le 2$ fix loops. If a step fails its 3rd loop, Gem 1 executes the mandatory tier cut order (`T3 -> T2 -> T1`; `T0` is never cut) or escalates a `SPEC-QUESTION` to the human team. | Entering a 4th fix loop on the same step without a scope cut or human override. |
| 6 | **Git Commit & Immutable Tag** | Human Courier | Committed on clean branch and tagged `step-<ID>-loop<n>` before merging to `main`. Zero `.env` secrets or API keys in git history. | Untracked changes, missing git tag, or leaked secret. |

---

## 3. Tier Acceptance Gates (`T0`–`T3` — `Architecture §24`)

Each tier sits behind its feature flag (`T0` always on, `T1_TRANSPORT`, `T2_REACH`, `T3_EXTRAS`). No higher tier may be enabled for the demo unless all preceding tier gates are **100% GREEN** with raw measured outputs captured.

### 3.1 Gate G0 — Tier T0 (`always`: Contract Core, PWA Desks, Monitor, Witness, Verifier, `BROKEN_BUILD`)

| # | Criterion | Verification Command / Test | Required Quantitative Measurement | Status |
|---|---|---|---|---|
| `G0.1` | **24-Table Schema & Constraints** | `pytest tests/closures/test_f4_ddl.py` (`ST-3`, `T-F4`) | All 24 tables, `one_lease`, `one_active_grant`, deferred FK `referral_lease_fk`, append-only triggers, `rhp_require_lock`, `i1_pending_deadline`, and `offer_chain_guard` active in PostgreSQL 16. | `[ ]` |
| `G0.2` | **Quint Control-Plane Spec & Non-Vacuity** | `bash scripts/verify_spec.sh` (`§3.1`) | `quint run` passes $\ge 20,000$ samples (0 violations); `quint verify` passes ($F=3, E=4$); all 4 vacuity checks (`ACCEPTED`, `DISPATCH`, `CLOSED`, `SOFT`) fail with witness traces as required. | `[ ]` |
| `G0.3` | **200-Way Concurrent Accept Race** | `pytest tests/test_race200.py` (`T-C1`, `T-F1`) | Exactly `1` of `200` concurrent `ACCEPT` requests returns `200 OK`; DB shows `1` `ACCEPTED` offer; `max(seq) - count(*) == 0` (gap-free); `pg_stat_database.deadlocks` delta `== 0`. | `[ ]` |
| `G0.4` | **Mutation Suite (`M1`–`M6` + `M7`)** | `bash scripts/run_mutations.sh` (`T-F17`) | 7 of 7 seeded mutations trip their designated checker (`I8`, `I2`, `I14`, `I12`, `I5`, `I15`, `I3`) within timeout. | `[ ]` |
| `G0.5` | **10-Minute Randomised Chaos Soak** | `pytest tests/test_stateful_pbt.py --soak-seconds=600` (with Toxiproxy toxics 1–8 cycled) | Independent Python monitor (`monitor.py`, connected as `rhp_monitor`) records **0 invariant violations** across the entire 10-minute run. | `[ ]` |
| `G0.6` | **Tamper Detection & Merkle Proof Verifier** | `pytest tests/closures/test_f8_tamper.py` + headless browser test on `verifier.js` (`T-F8`, `T-D1`) | Editing 1 byte of any `event` row causes pure-JS browser verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`) to name the exact `referral_id`, `seq`, and `kind=PREV|HASH`; head truncation without cold-key `RESTORE` reports `TRUNCATED`. | `[ ]` |
| `G0.7` | **`BROKEN_BUILD` Isolation & Detection Speed** | `pytest tests/closures/test_f20_broken_build.py` (`T-F20`) | Setting `BROKEN_BUILD=1` routes to `rhp_scratch_broken`, displays flashing red banner, grants 2 leases on race, and turns the monitor **RED (`I2`) within $\le 2.0\text{ s}$**; switching back turns monitor **GREEN**; `REAL_DATA=1` + `BROKEN_BUILD=1` exits with code `78`. | `[ ]` |
| `G0.8` | **Silence-to-Dispatcher Bound (`DEMO_FAST`)** | `pytest tests/closures/test_f3_timing.py` (`T-F2`, `T-F3`) | An unanswered referral across 3 facilities under `DEMO_FAST` ($A=3\text{ s}, D=4\text{ s}, \epsilon=1\text{ s}$) reaches `ESCALATED_TO_DISPATCHER` in measured time **$\le 25.0\text{ s}$** ($T_{max} = 24\text{ s} \le B = 25\text{ s}$). | `[ ]` |

### 3.2 Gate G1 — Tier T1 (`T1_TRANSPORT`: PWA Ambulance GPS, Dispatcher Console + Proxy, Replay Scrubber)

| # | Criterion | Verification Command / Test | Required Quantitative Measurement | Status |
|---|---|---|---|---|
| `G1.1` | **Proxy vs Direct Equivalence** | `pytest tests/test_t1_proxy_equivalence.py` | Across `20` paired referral runs, dispatcher proxy entry (`channel='DISPATCHER_PROXY', proxy=true`) and direct clinician/EMT API entry produce **100% identical `(hs_state, tr_state, offer.status, lease_epoch)` and event type sequences**. | `[ ]` |
| `G1.2` | **Dispatcher Escalation & Assignment** | `pytest tests/test_conformance_vectors.py -k "V-S08 or V-S24"` | After chain exhaustion (`ESCALATED_TO_DISPATCHER`), dispatcher console successfully executes `DISPATCHER_ASSIGN` (`source='DISPATCHER'`, `proxy=true`, mandatory reason enum) or `CLOSE`/`CANCEL`. | `[ ]` |
| `G1.3` | **Parallel Track Independence & 6 Arrival Cases** | `pytest tests/closures/test_f5_arrival.py` (`T-I3`, `T-F5`) | `TR_UPDATE` succeeds in every non-terminal `hs_state`; all 6 arrival cases (a)–(f) pass; geofence ($200\text{ m}$ + dwell) emits `ARRIVAL_SUGGESTED` only and never transitions to `ARRIVED` without human confirmation. | `[ ]` |
| `G1.4` | **Deterministic Log Replay Scrubber** | `pytest tests/test_t1_replay.py` | Folding committed `event` rows from `seq=1` to `head_seq` reproduces the exact intermediate and final `(hs_state, tr_state, lease_facility_id, lease_epoch, open_offers)` for 100% of test referrals. | `[ ]` |

### 3.3 Gate G2 — Tier T2 (`T2_REACH`: Exotel Outbound IVR, DLT SMS Stub/Sandbox, Paper Code)

| # | Criterion | Verification Command / Test | Required Quantitative Measurement | Status |
|---|---|---|---|---|
| `G2.1` | **Voice ACK Post-Commit Guarantee** | `pytest tests/test_t2_voice_ivr.py` (`V-S01`, `T-N5`, `T-N6`) | **`20 / 20` voice ACKs** play the spoken `"recorded"` confirmation only after `apply_command(ACK)` transaction commits; `inbox(source, external_id)` dedupes replayed webhooks with 0 duplicate events. | `[ ]` |
| `G2.2` | **Voicemail / AMD Press-1 Gate** | `pytest tests/closures/test_f7_auth.py -k "voicemail"` (`T-F7`) | **`0` ACKs recorded across `5` voicemail / machine / silent call trials** (AMD + mandatory press-`1` gate within $8\text{ s}$). | `[ ]` |
| `G2.3` | **Exotel Webhook Latency Budget** | `pytest tests/test_t2_voice_ivr.py -k "latency"` | Webhook response latency measures **`p95 <= 2.0 s`** under 20 concurrent callbacks (well inside Exotel's $5.0\text{ s}$ hard timeout `[V]`). | `[ ]` |
| `G2.4` | **Paper Code Error Detection (`Crockford + mod 37`)** | `pytest tests/test_t2_paper_code.py` (`V-S13`) | **100% (`1,000 / 1,000`)** of single-symbol mutations and adjacent transpositions of valid 9-character paper codes (8 Crockford Base32 payload chars + 1 mod-37 check char from `0-9A-Z*~$=U`) are rejected. | `[ ]` |
| `G2.5` | **DLT SMS & FCM Zero-PHI Lint** | `pytest tests/test_privacy_channels.py` (`T-P2`, `T-P3`) | 100% of SMS outbox rows use static template with variable $\le 30$ chars and zero clinical text; 100% of FCM rows carry empty payload `{}`. | `[ ]` |

### 3.4 Gate G3 — Tier T3 (`T3_EXTRAS`: Kotlin Android Service, AI Intake Accelerator, FHIR R4 & XES Export)

| # | Criterion | Verification Command / Test | Required Quantitative Measurement | Status |
|---|---|---|---|---|
| `G3.1` | **Android Screen-Off GPS Soak** | `scripts/verify_android_soak.py` (`T-F4b`) | Native Kotlin app (`FOREGROUND_SERVICE_TYPE_LOCATION` + `FusedLocationProviderClient` + Room outbox) maintains GPS telemetry for **$\ge 2.0\text{ hours}$ with screen off** on the demo device and reconciles offline queues via `Idempotency-Key`. | `[ ]` |
| `G3.2` | **AI Cognitive Forcing Function (CFF)** | `pytest tests/test_t3_ai_cff.py` (`T-A2`, `V-S15`) | Draft endpoint returns **`423 ANCHOR_REQUIRED`** until clinician commits `need_class` and `mgso4_status`; zero confidence scores or explanations rendered; system works 100% with `T3_EXTRAS=0`. | `[ ]` |
| `G3.3` | **20-Slip Seeded-Error Usability Gate** | `pytest tests/test_t3_seeded_gate.py` (`T-A1`) | Across 20 synthetic referral slips (30% seeded fatal errors): critical-error rubber-stamp rate **$\le 5.0\%$** and silent-omission rate **$\le 1.0\%$**. | `[ ]` |
| `G3.4` | **FHIR R4 & IEEE 1849 XES Validator** | `pytest tests/test_t3_exports.py` | Exported FHIR R4 bundle (`ServiceRequest`, `Task`, `Encounter`, `Communication`) passes JSON schema + curated value-set validator; XES export passes IEEE 1849 schema check with 4-hour timestamp buckets and $k \ge 5$ suppression. | `[ ]` |

---

## 4. Phase P (Pre-Event) & Phase E (24-Hour At-Event) Milestone Checklist

### 4.1 Phase P — Pre-Event Spec Artefacts (`Architecture §2`, `Workflow §6`)
*Note: Confirm event rules on pre-built work first (`§21 #1`). Phase P artefacts are specification and verification definitions.*

| Step ID | Lane | Deliverable | Completion Gate | Done |
|---|---|---|---|---|
| `P1` | A | `spec/transitions.yaml` + 28 conformance vectors (`V-S01`..`V-S28`) | Python explicit-state explorer verifies reachability (`T-F6`) and all 12 v7 state mappings (`T-F19`). | `[ ]` |
| `P2` | A | `db/schema.sql` (24-table PostgreSQL 16 DDL) | Loads cleanly into PostgreSQL 16; `ST-3` and `T-F4` pass 100%. | `[ ]` |
| `P3` | A | `spec/rhp1.qnt` (Quint control-plane model) | `quint run` (20,000 samples) and `quint verify` pass; all 4 vacuity checks fail as required. | `[ ]` |
| `P4` | B | `spec/profiles.json` (4 cold-key signed profiles) + $T_{max}$ validator | `ST-2`, `T-F2`, and `T-F3` pass for `PILOT_OB_CRITICAL`, `PILOT_STANDARD`, `DEMO_FAST`, `DEMO_VOICE`. | `[ ]` |
| `P5` | B | `db/seed.sql` (synthetic Karnataka facilities, catchment chains, rosters, `REAL_DATA=0`) | Loads cleanly; zero real patient or staff PII (`ST-5`). | `[ ]` |
| `P6` | B | Pre-Event Verification Log (`Architecture §21` items 1–12) | All 12 items tested within timeboxes and fallbacks recorded. | `[ ]` |

### 4.2 Phase E — 24-Hour At-Event Build Schedule (`Architecture §17`, `Workflow §6`)

| Step ID | Window | Lane A (Backend / Proof — Person A) | Lane B (Clients / Reach / Monitor — Person B) | Gate Required | Done |
|---|---|---|---|---|---|
| `E0` | `H00–H02` | Repo setup, `docker-compose.yml`, DDL load, seed, `transitions.yaml` loader | React PWA shell, rotating single-use QR admission (`jti`, cap 20) | `ST-1`..`ST-5` green | `[ ]` |
| `E1` | `H02–H06` | `apply_command()` Steps 1–10: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `DECLINE` | Receiving desk UI (priority list, no countdowns, red `mgso4` banner), SSE + per-event authz (`F10`) | Core vectors pass | `[ ]` |
| `E2` | `H06–H09` | Two-phase `poller.py`, visibility-timeout `relay.py`, `TIMEOUT`, notice ladder rungs | Guarantee Arena big screen; **Independent Python Monitor (`monitor.py`) in isolated workspace** | Monitor differential check green | `[ ]` |
| `E3` | `H09–H12` | RFC 8785 JCS hash chain, separate-OS-user `witness` signer (`rhp-sign`), 5s Merkle checkpoints | Browser verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`), inclusion proof UI | `T-F8`, `T-D1` green | `[ ]` |
| `E4` | `H12–H14` | `race200` barrier test (`T-C1`), mutation suite `M1`–`M7` (`T-F17`) | `BROKEN_BUILD=1` scratch DB script (`make_scratch.sh`), boot guards (`T-F20`), flashing red banner | **GATE G0 (T0 PASS)** | `[ ]` |
| `E5` | `H14–H17` | `COUNTER`, `CONFIRM_COUNTER`, `ARRIVAL_REJECTED`, 6 arrival cases (`F5`), two-stage `CLOSURE` (`F6`) | Dispatcher console (`DISPATCHER_ASSIGN`, proxy entry), PWA ambulance GPS, replay scrubber | **GATE G1 (T1 PASS)** | `[ ]` |
| `E6` | `H17–H20` | Full idempotency matrix (`T-F14`), stale fencing (`T-I8`), offline confirmation expiry (`T-F12`) | Exotel outbound IVR (`press-1` gate, PIN `%23`), DLT SMS stub, Crockford + mod-37 paper code | **GATE G2 (T2 PASS)** | `[ ]` |
| `E7` | `H20–H22` | Defect fixes from Toxiproxy chaos & red-team attacks | Record MP4 fallback clips (`clip A`–`clip D`), run 30s proof loop + 7m pitch rehearsal $\times 3$ | **GATE G3 (REHEARSAL PASS)** | `[ ]` |
| `E8` | `H22–H24` | **HARD CODE FREEZE AT H22** (config-only changes permitted) | Final rehearsal, hot-standby backup laptop + phone hotspot + LAN QR pre-flight | **FREEZE LOCKED** | `[ ]` |

---

## 5. Complete Sign-Off Checklists (`I1`–`I16`, `F1`–`F20`, `D1`–`D20`)

### 5.1 Invariants `I1`–`I16` Sign-Off Table

| ID | Invariant Summary | DB Trigger / Index Active | Pipeline Guard Active | Independent Monitor Rule Active | Test Green |
|---|---|---|---|---|---|
| `I1` | Every non-terminal referral has $\ge 1$ `PENDING` deadline; acted on within $\tau$ | `i1_pending_deadline` | Step 8 creates next deadline | Overdue query $> \tau$ | `T-I1` `[ ]` |
| `I2` | At most 1 active lease; `lease_epoch` strictly increasing | `one_lease` unique index | Step 6 & 8 under referral lock | Fold `ACCEPTED` count $\le 1$ & epoch monotone | `T-I2` `[ ]` |
| `I3` | `TR_UPDATE` accepted in every non-terminal `hs_state`; `mgso4` never blocks | Independent `tr_state` column | `TR_UPDATE` never reads `hs_state` | Flag invalid `TR_UPDATE` rejection | `T-I3` `[ ]` |
| `I4` | Each `event_id` once; per-referral `seq` gap-free | `idempotency` PK, `event_id` UNIQUE, `rhp_event_guard` | Step 1 advisory lock + Step 9 `seq+1` | Fold `e.seq == st["seq"] + 1` | `T-I4` `[ ]` |
| `I5` | Hash chain & checkpoint signatures verify; terminal states have `outcome` | `event_ao`, `checkpoint_ao`, `outcome` CHECK | Step 9 SHA-256 JCS chain | Recompute SHA-256 chain & Ed25519 sigs | `T-I5` `[ ]` |
| `I6` | Mutating responses require rostered role, registered device/number, verified PIN, or `proxy=true` | `roster`, `device`, `session` FKs | Steps 2, 3 (Argon2id), and 5 | Verify `actor_roster_id` validity at `server_ts` | `T-I6` `[ ]` |
| `I7` | System-chosen offer targets $\in \text{referral.chain}$; dispatcher offers carry `source='DISPATCHER'` | `offer_chain_guard` trigger | `advance()` reads `referral.chain` | Check `facility IN chain OR source=='DISPATCHER'` | `T-I7` `[ ]` |
| `I8` | Stale `expected_version` / `expected_epoch` never applied and logged | `rejected_ao` on `rejected_command` | Step 5 savepoint rollback $\to$ `412` | Check `e.epoch >= st["epoch"]` | `T-I8` `[ ]` |
| `I9` | A facility is offered at most once per referral | `UNIQUE(referral_id, facility_id)` on `offer` | `advance()` excludes prior targets | Fold checks unique facilities in `OFFER_CREATED` | `T-I9` `[ ]` |
| `I10` | Clinical frames sent only to subscribers with an active `payload_grant` | `one_active_grant` index | Per-event SSE filter + `GRANT_REVOKED` | Audit clinical access vs `revoked_at` | `T-I10` `[ ]` |
| `I11` | `event.detail` holds only allowlisted keys with enum/int/bool/UUID values | `CHECK (rhp_detail_ok(type, detail))` | Pydantic `extra='forbid'` + `Literal` enums | Scan `event.detail` keys and types | `T-I11` `[ ]` |
| `I12` | At most 2 open offers (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) | `CHECK (open_offers BETWEEN 0 AND 2)` | Step 8 updates `open_offers` under lock | Fold count of open offers $\le 2$ | `T-I12` `[ ]` |
| `I13` | Configured $T_{max} = F \cdot (A + D + \epsilon) \le B$ for active profile | `profile_hash` recorded on `referral` | Startup `validate()` refuses boot if $> B$ | Recompute at boot and `/healthz` | `T-I13` `[ ]` |
| `I14` | No contract-state write without holding the referral row lock | `rhp_require_lock` on 6 tables | Step 4 `SELECT ... FOR UPDATE` + `set_config` | Check `deadlocks` delta $= 0$ | `T-I14` `[ ]` |
| `I15` | No lease granted from a resource confirmation expired at `server_ts` | `CHECK (expires_at > confirmed_at)` | Step 7 checks `expires_at > ts` | Verify unexpired `RESOURCE_CONFIRMED` before `ACCEPT` | `T-I15` `[ ]` |
| `I16` | `server_ts` is non-decreasing per referral | `rhp_event_guard` (`NEW.server_ts < r.head_ts`) | Step 4 `GREATEST(clock_timestamp(), r.head_ts)` | Fold checks `e.ts >= st["ts"]` | `T-I16` `[ ]` |

### 5.2 Architectural Closures `F1`–`F20` & Solution Defects `D1`–`D20` Sign-Off

| Closure | Verified Mechanism | Solution Defect Closed | Passing Test |
|---|---|---|---|
| `F1` | Global lock order `referral > offer > deadline > outbox`; two-phase poller; `rhp_require_lock` | `D8`, Loophole #6 | `T-F1` `[ ]` |
| `F2` | Unified ACK window $A$ with notice rungs at $0, A/4, 3A/4$; 4 cold-key signed profiles | `D3`, Loophole #8, #37 | `T-F2` `[ ]` |
| `F3` | Concurrent slot notification; $T_{max} = F \cdot (A + D + \epsilon) \le B$ startup guard | `D3`, Loophole #8 | `T-F3` `[ ]` |
| `F4` | Complete 24-table PostgreSQL 16 DDL, `one_lease`, deferred FK, append-only triggers | `D8`, Loophole #38 | `T-F4` `[ ]` |
| `F5` | Six explicit arrival cases (a)–(f); geofence emits `ARRIVAL_SUGGESTED` only | `D2`, Loophole #2, #32 | `T-F5` `[ ]` |
| `F6` | Reachability table, 9 outcomes, two-stage `CLOSURE` $\to$ `UNKNOWN_COUNTER_REFERRAL` | Loophole #9, #28 | `T-F6` `[ ]` |
| `F7` | Single-use enrollment ticket, Argon2id in autonomous txn, per-session lockout, AMD + press-1 gate | `D4`, `D12`, Loophole #13, #36 | `T-F7` `[ ]` |
| `F8` | Separate-OS-user (`rhp-sign`) Ed25519 signer, Merkle inclusion proofs, cold-key `RESTORE` | `D10`, Loophole #15, #16 | `T-F8` `[ ]` |
| `F9` | Per-type `event.detail` allowlist (`rhp_detail_ok`), 4h buckets, $k \ge 5$ suppression | `D9`, Loophole #18, #19, #20 | `T-F9` `[ ]` |
| `F10` | Per-event SSE grant authorization, `GRANT_REVOKED` frame, DOM state wipe | `D13`, Loophole #14, #18 | `T-F10` `[ ]` |
| `F11` | `GREATEST(clock_timestamp(), r.head_ts)`, chrony slew-only, $>2\text{ s}$ NTP offset alarm | Loophole #7 | `T-F11` `[ ]` |
| `F12` | `expires_at` on `offer_resource_confirmation`, `409` reconfirm codes, live reconfirm modal | Loophole #4 | `T-F12` `[ ]` |
| `F13` | `open_offers <= 2` CHECK, `SOFT_OPEN` early expiry, `PARALLEL2` & `COUNTER` race rules | `D3`, `D7`, Loophole #3, #10 | `T-F13` `[ ]` |
| `F14` | Step 1 advisory lock idempotency, `(actor_id, key)` + JCS request hash, savepoint `sp_cmd` | Loophole #5 | `T-F14` `[ ]` |
| `F15` | Every failure matrix row carries an explicit technical bound and reason | `D5`, Loophole #27 | `T-F15` `[ ]` |
| `F16` | Feature-flagged tiers `T0`–`T3`, second-by-second 30s live proof loop, MP4 fallbacks | `D17`, `D20`, Loophole #31 | `T-F16` `[ ]` |
| `F17` | Two-person split (`A` = spec/server, `B` = clean-room monitor), mutation suite `M1`–`M7` | `D6`, `D19`, Loophole #28, #29, #30, #39 | `T-F17` `[ ]` |
| `F18` | Single reconciled 6-month AWS `ap-south-1` Multi-AZ cost table ($\approx \$1,420$) | — | `T-F18` `[ ]` |
| `F19` | Explicit 12-state mapping from `Problem Statement v7` to RHP-1 tables and events | — | `T-F19` `[ ]` |
| `F20` | `BROKEN_BUILD=1` isolated to `rhp_scratch_broken` with exit `78` boot aborts and red banner | — | `T-F20` `[ ]` |
| `D1` | `mgso4_status` (`GIVEN \| NONE_GIVEN \| UNKNOWN`) never blocks `CREATE` or dispatch; sets red banner | `D1`, Loophole #1 | `T-K1` `[ ]` |
| `D11` | Rotating QR (`jti`, 20s TTL) + Cloudflare Turnstile challenge + cap 20 desks + LAN fallback | `D11`, Loophole #17 | `T-N7` `[ ]` |
| `D14/D15` | Curated Karnataka registry + timestamped capability attestations shown with age (never `"live beds"`) | `D14`, `D15`, Loophole #33, #34 | `ST-5` `[ ]` |
| `D16/D18` | In-app process projections; priority queue without countdowns; APOT separated from `ACCEPT` | `D16`, `D18`, Loophole #12, #24, #25, #26 | `T-K2` `[ ]` |

---

## 6. Demo & Pitch Readiness Sign-Off (`Gate G3` & `H22 Freeze`)

Before entering the presentation room, both teammates (`T1` and `T2`) must verify and initial every item below:

- [ ] **1. 30-Second Live Proof Loop Rehearsed $\times 3$ (`T-F16`):** Completes inside $30.0\text{ s}$ under `DEMO_FAST` covering: QR join (`0–4s`) $\to$ `PARALLEL2` offer (`4–7s`) $\to$ simultaneous `Accept` race won by exactly 1 desk (`7–12s`) $\to$ `BROKEN_BUILD=1` scratch DB turning monitor `RED (I2)` in $\le 2\text{ s}$ (`12–18s`) $\to$ switch back to `GREEN` (`18–21s`) $\to$ `psql` row tamper caught by pure-JS verifier naming exact `seq` (`21–27s`) $\to$ live-measured `I1`–`I16` counters and `p50`/`p95` latency overlay (`27–30s`).
- [ ] **2. Pre-Recorded MP4 Fallback Clips Armed:** `clip_A.mp4` (QR + Create + Voice), `clip_B.mp4` (200-way / Judge Race), `clip_C.mp4` (`BROKEN_BUILD` Red $\to$ Green), and `clip_D.mp4` (`psql` Tamper + Verifier + Recap) are open in hot-keyed media player tabs for instant switchover.
- [ ] **3. Dual Uplink + LAN Fallback Verified:** Primary laptop connected to dedicated phone hotspot; secondary uplink on venue Wi-Fi; LAN-QR fallback (`REAL_DATA=0`, cap 20, pure-JS `@noble` verifier) tested with iPhone and Android cameras.
- [ ] **4. Feature Phone & Exotel Pre-Flight (`T2`):** Feature phone charged to 100%, ringer volume maximum, number confirmed on Exotel trial whitelist ($\le 10$ numbers), `DEMO_VOICE` profile signature verified.
- [ ] **5. Code Freeze Enforced at `H22`:** Git tag `freeze-h22` pushed; zero code edits after `H22`; both teammates can explain every module (`apply_command()`, lock order, `poller.py`, `monitor.py`, Merkle verifier, Quint spec) to judges.
- [ ] **6. Claims Discipline Slide & Script Audit (`ST-5`):** Slide deck includes the explicit `"What We Do Not Claim"` slide (`v8 §14`, `Architecture §19`); Das et al. (2023) and Safdarjung (2018–2023) citations include setting and study names; all latency and recovery numbers shown on screen are measured live during the run.