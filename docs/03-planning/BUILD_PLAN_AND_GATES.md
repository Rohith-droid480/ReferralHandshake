# BUILD_PLAN_AND_GATES.md — Strict 24-Hour Build Plan, Step Catalogue & Acceptance Gates

**Rule:** You must follow this build sequence and tier gating strictly. No layer or tier may start until the previous gate's acceptance suite and runtime monitor are green, or unless explicitly directed by Gem 1's `AG-PROMPT`.

---

## 1. Tier Flags & Scope Cut Order

Every feature sits behind an environment feature flag so the MVP can always run alone on stage. If behind schedule, Gem 1 cuts strictly from the bottom up (**T3 first → T2 second → T1 third → T0 is NEVER cut**).

| Tier | Feature Flag | Scope Included | Cut Priority |
|---|---|---|---|
| **T0 (MVP + Proof Core)** | Always ON | FastAPI Command API, PostgreSQL 16 (24 tables), 2-phase Poller, Outbox Relay, React PWA Desks with rotating QR join, Independent Python Monitor, Separate-OS-User Witness/Signer + Browser Pure-JS Verifier, `BROKEN_BUILD` scratch DB switch | **NEVER CUT** |
| **T1 (Transport & Console)** | `T1_TRANSPORT=1` | PWA Ambulance client (foreground GPS), Dispatcher Console + Proxy entry, Time-Scrubber Replay | Cut 3rd |
| **T2 (Reach Layer)** | `T2_REACH=1` | Exotel Outbound Voice IVR (AMD + Press-1 gate + DTMF PIN), DLT-style static SMS alert stub, Crockford Base32 + mod-37 Paper Code entry | Cut 2nd |
| **T3 (Extras)** | `T3_EXTRAS=1` | Native Kotlin Android foreground location app, AI Intake Accelerator (Cognitive Forcing Function), FHIR R4 (`ServiceRequest`/`Task`) & IEEE 1849 XES export | Cut 1st |

---

## 2. Phase P — Pre-Event Spec Artefacts Catalogue

*(Run before the 24-hour clock only as permitted by event rules; otherwise execute at Hour 0).*

| Step ID | Lane | Task Description | Spec Anchors | Risk | Loop Type |
|---|---|---|---|---|---|
| **P1** | Lane A | Author `transitions.yaml` and conformance test vectors covering all 14 commands and 28 real-world scenarios | Arch §4, §5; v8 §4.8 | HIGH | FULL |
| **P2** | Lane A | Load complete 24-table DDL into PostgreSQL 16; run FK/constraint/trigger scan (`ST-3`); verify append-only & `rhp_require_lock` triggers | Arch §7, §23 (`T-F4`) | HIGH | FULL |
| **P3** | Lane A | Run Quint control-plane spec (`rhp1.qnt`); execute `quint run safety` ($\ge 20,000$ samples) and verify vacuity checks fail as required | Arch §12 | HIGH | FULL |
| **P4** | Lane B | Create the 4 Ed25519-signed timing profiles (`PILOT_OB_CRITICAL`, `PILOT_STANDARD`, `DEMO_FAST`, `DEMO_VOICE`) + $T_{\max} \le B$ startup validator (`I13`) | Arch §6 (`T-F2`, `T-F3`) | MED/HIGH | FULL |
| **P5** | Lane B | Build synthetic seed data generator (`REAL_DATA=0`): Karnataka-style tier facilities (PHC, CHC, FRU, DH, MC, DISPATCH), rosters, capabilities, catchment chains | Arch §2, §7, §10 | LOW | FAST |
| **P6** | Lane B | Execute Pre-Event Verification Checklist (Exotel trial whitelist, pure-JS Ed25519 on iOS Safari, LAN HTTP QR scan, Mapbox Matrix call) | Arch §21 | LOW | FAST |

---

## 3. Phase E — 24-Hour Event Build Plan (24 Half-Module Prompts)

**Team Split:**
- **Lane A (Person A):** Protocol, PostgreSQL, FastAPI Command Pipeline, Poller/Relay, Witness/Crypto, Concurrency & Mutation Tests.
- **Lane B (Person B):** Independent Runtime Monitor (Clean-Room Workspace), React PWA Desks, Big Screen / Guarantee Arena, Reach Layer (Voice/SMS/Paper), Demo Operations.

| Hour | Half-Module | Lane | Sub-Segments Built & Scope | Combined Verification Command | Gate / Milestone |
|---|---|---|---|---|---|
| `H00–H01` | **`M1-A`** | Lane A + B | `1.1`–`1.3`: Workspace, Docker topology, PG16 DDL, seed & signed profiles | `pytest tests/test_boot_guards.py tests/test_ddl_constraints.py tests/test_tmax_profiles.py` | — |
| `H01–H02` | **`M1-B`** | Lane A | `1.4`–`1.6`: RFC 8785 JCS parity, `transitions.yaml` loader, Quint `rhp1.qnt` & Explorer | `pytest tests/test_jcs_parity.py tests/test_transitions_table.py && python tests/explore_transitions.py && quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000` | **Completes Module 1** |
| `H02–H03` | **`M2-A`** | Lane A | `2.1`–`2.3`: Dual connection pools, sessions (cookie/voice), Argon2id lockout | `pytest tests/test_auth_sessions.py tests/test_pin_lockout_scope.py` | — |
| `H03–H04` | **`M2-B`** | Lane A | `2.4`–`2.5`: Role-command authz matrix, Pydantic schemas, 10-step pipeline core | `pytest tests/test_authz_matrix.py tests/test_pipeline_core.py` | **Completes Module 2** |
| `H04–H05` | **`M3-A`** | Lane A | `3.1`–`3.3`: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT` lease arbitration | `pytest tests/test_cmd_create.py tests/test_cmd_ack_confirm.py tests/test_cmd_accept.py` | — |
| `H05–H06` | **`M3-B`** | Lane A | `3.4`–`3.6`: `DECLINE` escalation, `COUNTER` negotiation, terminal commands | `pytest tests/test_cmd_decline_advance.py tests/test_cmd_counter.py tests/test_cmd_lifecycle.py` | **Completes Module 3** |
| `H06–H07` | **`M4-A`** | Lane B / A | `4.1`–`4.2`: Independent monitor `monitor.py` (F17), `race200` barrier, idempotency | `pytest tests/test_monitor_fold.py tests/test_race200.py tests/test_idempotency_matrix.py` | — |
| `H07–H08` | **`M4-B`** | Lane B / A | `4.3`–`4.4`: `BROKEN_BUILD` scratch isolation, mutation tests `M1`–`M6`, 28 vectors | `pytest tests/test_broken_build.py tests/test_mutations.py tests/test_conformance_vectors.py` | **Completes Module 4 (T0 Proof Core)** |
| `H08–H09` | **`M5-A`** | Lane A | `5.1`–`5.3`: Two-phase poller, notice ladder ($0, A/4, 3A/4$), outbox relay | `pytest tests/test_poller_liveness.py tests/test_notice_ladder_and_closure.py` | — |
| `H09–H10` | **`M5-B`** | Lane A + B | `5.4`–`5.5`: Authorized SSE hub with `GRANT_REVOKED` stripping, clock guards | `pytest tests/test_sse_revoke.py tests/test_clock_and_heartbeats.py` | **Completes Module 5** |
| `H10–H11` | **`M6-A`** | Lane A | `6.1`–`6.2`: Witness signer 5s Merkle tree, off-box sync & cold `RESTORE` | `pytest tests/test_witness_merkle.py tests/test_tamper_vs_restore.py` | — |
| `H11–H12` | **`M6-B`** | Lane B | `6.3`: Pure-JS browser verifier (`@noble`) & superuser SQL `tamper.sh` | `npm --prefix pwa test -- verifier && bash scripts/tamper.sh --dry-check` | **Completes Module 6** |
| `H12–H13` | **`M7-A`** | Lane B | `7.1`–`7.3`: React PWA shell, rotating judge QR admission, clinician card | `pytest tests/test_judge_join.py && npm --prefix pwa run build` | — |
| `H13–H14` | **`M7-B`** | Lane B | `7.4`–`7.6`: Receiving duty desk, judge race desk, Guarantee Arena big screen | `npm --prefix pwa test && make gate-t0` | **GATE G0 (T0 PASS)** |
| `H14–H15` | **`M8-A`** | Lane A | `8.1`–`8.2`: Parallel transport track API, 6 arrival cases, Mapbox Matrix ETA | `pytest tests/test_transport_and_arrivals.py` | — |
| `H15–H16` | **`M8-B`** | Lane B | `8.3`–`8.4`: PWA ambulance client (foreground GPS) & Dispatcher Console with replay | `pytest tests/test_dispatcher_proxy_and_replay.py && make gate-t1` | **GATE G1 (T1 PASS)** |
| `H16–H17` | **`M9-A`** | Lane B + A | `9.1`–`9.3`: Outbound Exotel IVR, AMD + Press-1 gate, DTMF PIN verification | `pytest tests/test_exotel_ivr.py` | — |
| `H17–H18` | **`M9-B`** | Lane B | `9.4`–`9.5`: TRAI DLT static SMS adapter & 9-char Crockford mod-37 paper code | `pytest tests/test_dlt_sms_lint.py tests/test_paper_code_mod37.py && make gate-t2` | **GATE G2 (T2 PASS)** |
| `H18–H19` | **`M10-A`** | Lane A | `10.1`–`10.2`: AES-256-GCM envelope encryption, monthly KEK wrapping, crypto-shredder | `pytest tests/test_envelope_crypto.py` | — |
| `H19–H20` | **`M10-B`** | Lane A + B | `10.3`–`10.4`: District command centre live map/APOT KPIs & graph aggregations | `pytest tests/test_analytics_recompute.py` | **Completes Module 10** |
| `H20–H20:30` | **`M11-A`** | Lane A + B | `11.1`–`11.2`: Cognitive-forcing AI intake (`423 ANCHOR_REQUIRED`), FHIR R4 exporter | `pytest tests/test_ai_seeded_errors.py tests/test_fhir_exporter.py` | — |
| `H20:30–H21` | **`M11-B`** | Lane A + B | `11.3`–`11.4`: IEEE 1849 XES / BSA evidence generator & native Kotlin Android EMT app | `pytest tests/test_bsa_xes_exports.py tests/test_fcm_zero_payload.py && make gate-t3` | **Completes Module 11 (T3)** |
| `H21–H21:45` | **`M12-A`** | Lane A | `12.1`–`12.2`: Eight-scenario Toxiproxy fault matrix & automated self-audit CI suite | `pytest tests/test_toxiproxy_chaos.py tests/test_lock_order.py tests/test_tmax_profiles.py tests/test_ddl_constraints.py tests/test_idempotency_matrix.py tests/test_claims_lexicon.py` | — |
| `H21:45–H22` | **`M12-B`** | Lane A + B | `12.3`: Master tier acceptance gate runner `Makefile` (`gate-all`) & rehearsal | `make gate-all && bash scripts/preflight.sh` | **GATE G3 (REHEARSAL)** |
| `H22–H24` | **`FREEZE`** | Team A + B | **HARD CODE FREEZE AT H22:** Configuration-only tweaks, 30s proof loop $\times 3$, demo polish | `bash scripts/preflight.sh` | **STAGE READY** |

## 4. Mandatory Tier Acceptance Gates (Architecture §24)

When Gem 1 issues a **GATE-PROMPT**, you must run and paste the raw output for every criterion in that gate before advancing:

### Gate G0 (Tier T0 Acceptance — Must Pass by H14)
1. **`race200` Barrier Test (`T-C1`):** 200 concurrent `ACCEPT` requests across 2 competing offers -> exactly `1` returns HTTP `200`, `199` return `409/412`, DB has `count(*) = 1` in `offer WHERE status='ACCEPTED'`, `event.seq` has `0` gaps, and PostgreSQL deadlock counter delta = `0`.
2. **Mutation Suite (`M1–M6` / `T-F17`):**
   - `M1` (skip `expected_epoch` fencing) -> trips Monitor `I8` + vector `V-STALE-EPOCH`.
   - `M2` (drop `FOR UPDATE` + `one_lease` on scratch) -> trips `race200` + Monitor `I2`.
   - `M3` (poller holds deadline lock into `apply_command`) -> trips `T-F1` deadlock detector (`I14`).
   - `M4` (Quint cap guard removed) -> `quint run safety` produces `I12` counterexample.
   - `M5` (write `prev_hash` as zeros) -> trips Browser Verifier + Monitor `I5` (`kind=PREV`).
   - `M6` (ACCEPT ignores confirmation `expires_at`) -> trips vector `V-STALE-CONFIRM` + Monitor `I15`.
3. **10-Minute Chaos & Hypothesis Run:** Independent monitor reports `0` invariant violations across randomised stateful commands + Toxiproxy faults.
4. **Tamper Detection (`T-F8`):** Superuser edits 1 row in `event` -> judge-phone JS verifier prints `BROKEN referral=<id> seq=<n> kind=HASH`.
5. **Broken Build Switch (`T-F20`):** Flipping `BROKEN_BUILD=1` on scratch DB grants 2 leases and turns Monitor RED (`I2`) in $\le 2\text{s}$; switching back turns Monitor GREEN.
6. **Silence Escalation Bound:** Under `DEMO_FAST`, an unanswered referral escalates through all 3 facilities to `ESCALATED_TO_DISPATCHER` in $\le 25\text{s}$ ($T_{\max} = 24\text{s}$).

### Gate G1 (Tier T1 Acceptance — Must Pass by H17)
1. **Proxy Equivalence:** Dispatcher proxy entry and direct clinician/EMT API entry produce identical state and event sequences across 20 paired runs (differing only in `proxy=true` and `proxy_for`).
2. **Dispatcher Fallback:** Console successfully assigns a destination after `ESCALATED_TO_DISPATCHER` with `source='DISPATCHER'` and mandatory reason enum.
3. **Log Replay:** Time-scrubber replay deterministically reconstructs every historical step of a referral from the `event` log alone.

### Gate G2 (Tier T2 Acceptance — Must Pass by H20)
1. **Voice Commit Discipline:** 20/20 voice ACKs play the spoken "recorded" confirmation ONLY after `apply_command(ACK)` commits; webhook latency $p_{95} \le 2\text{s}$.
2. **Voicemail Immunity (`T-F7`):** 5 simulated voicemail/machine pickups without pressing `1` result in `0` false ACKs.
3. **Paper Code Checksum:** 1,000 single-symbol mutations and adjacent transpositions of valid 9-character Crockford Base32 + mod-37 codes are rejected `100%` of the time.

---

## 5. The 30-Second Live Proof Loop (Must Always Work Under `DEMO_FAST`)

Every UI and backend change must preserve this exact 30-second stage sequence:
- **0–4s:** Judges scan rotating QR; two desks (`D1`, `D2`) join.
- **4–7s:** `PARALLEL2` referral created; both desks receive the live SSE offer.
- **7–12s:** Both judges press **Accept** simultaneously -> one gets `200 OK` (Lease Epoch 1), the other gets `409 LEASE_HELD`; Monitor stays **GREEN**.
- **12–18s:** Flip `BROKEN_BUILD=1` (red scratch banner); new referral; both press Accept -> two leases granted; Monitor turns **RED (`I2`)** within $\le 2\text{s}$.
- **18–21s:** Flip back to normal build -> Monitor returns to **GREEN**.
- **21–27s:** `psql` tampers with 1 event row -> judge-phone browser verifier flags `BROKEN referral=... seq=... kind=HASH`.
- **27–30s:** Big screen displays live-measured `I1–I16` counters and live-measured $p_{50}/p_{95}$ latency (never pre-claimed numbers).