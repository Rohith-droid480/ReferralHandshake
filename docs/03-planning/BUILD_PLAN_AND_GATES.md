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

## 3. Phase E — 24-Hour Event Build Plan (Hour-by-Hour)

**Team Split:**
- **Lane A (Person A):** Protocol, PostgreSQL, FastAPI Command Pipeline, Poller/Relay, Witness/Crypto, Concurrency & Mutation Tests.
- **Lane B (Person B):** Independent Runtime Monitor (Clean-Room Workspace), React PWA Desks, Big Screen / Guarantee Arena, Reach Layer (Voice/SMS/Paper), Demo Operations.

| Step ID | Hours | Lane A (Backend & Proof) | Lane B (Monitor, Clients & Reach) | Risk | Gate Target |
|---|---|---|---|---|---|
| **E0** | H00–H02 | Repo setup, `docker-compose.yml`, PG16 DDL load, synthetic seed, `transitions.yaml` loader, `/healthz` with $T_{\max}$ check | React PWA shell, rotating QR admission (`jti`, 20s TTL, cap 20 desks), LAN fallback mode | MED | — |
| **E1** | H02–H06 | `apply_command()` 10-step pipeline: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `DECLINE`, idempotency, Argon2id autonomous PIN counter, row-lock GUC | Receiving Desk UI (priority queue, no countdown clocks, red `mgso4_status=UNKNOWN` banner), SSE hub with per-event `payload_grant` filter & `GRANT_REVOKED` frame | HIGH | — |
| **E2** | H06–H09 | Stateless 2-phase Poller (`CLAIM` + `apply_command(TIMEOUT)`), Outbox Relay (`SKIP LOCKED` + visibility timeout), unified notice ladder (`0, A/4, 3A/4`) | Guarantee Arena Big Screen UI; **Independent Python Runtime Monitor** (`monitor/cycle.py` in isolated workspace checking `I1–I16`) | HIGH | — |
| **E3** | H09–H12 | RFC 8785 JCS SHA-256 event hash chain, envelope encryption (`DEK`/`KEK`), separate-OS-user (`rhp-sign`) Merkle checkpoint signer (every 5s), inclusion proofs | Browser Pure-JS Verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`) on judge phones naming exact broken `seq` | HIGH | — |
| **E4** | H12–H14 | 200-way `asyncio.Barrier` concurrency test (`race200`), Mutation Tests `M1–M6`, Toxiproxy fault matrix | `BROKEN_BUILD=1` scratch DB (`rhp_scratch_broken`) switch + flashing red Arena banner + hard boot guards | HIGH | **GATE G0 (T0 Pass)** |
| **E5** | H14–H17 | `COUNTER` / `CONFIRM_COUNTER` (max 2 rounds), 6 arrival cases (`ARRIVAL_SUGGESTED`, `ARRIVAL_REJECTED`, `ARRIVAL_AT_NON_OWNER`), two-stage `CLOSURE` | Dispatcher Console (proxy entry, `DISPATCHER_ASSIGN` with reason enum), PWA Ambulance GPS tracker, Time-Scrubber Replay | HIGH | **GATE G1 (T1 Pass)** |
| **E6** | H17–H20 | Full idempotency edge-case matrix (`T-F14`), stale offline confirmation rejection (`I15` `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`), fencing tests | Exotel Outbound IVR webhook (AMD + Press-1 gate, $\le 2\text{s}$ budget, `inbox` dedupe), Crockford Base32 + mod-37 Paper Code entry & printable slip | HIGH | **GATE G2 (T2 Pass)** |
| **E7** | H20–H22 | Bug fixes from Gate G0–G2 test runs; self-audit checks `ST-1` to `ST-5` | Record MP4 fallback clips (Clips A, B, C, D); run 3 full rehearsals of the 30-second live proof loop | MED | **GATE G3 (Rehearsal)** |
| **E8** | H22–H24 | **HARD CODE FREEZE AT H22.** Configuration-only tweaks; verify DB backups & clean state reset script | Final stage rehearsal, dual-uplink check (hotspot + Wi-Fi), backup laptop warm standby | LOW | **FREEZE** |

---

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