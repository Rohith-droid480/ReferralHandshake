# ReferralHandshake (Protocol RHP-1) — Master Verification & Test Plan

**System:** Referral Handshake Protocol RHP-1 + Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru)  
**Authority Hierarchy:** `Problem Statement v7` $>$ Research tagged `[V]` $>$ `Solution v8` $>$ `FINAL_LOCKED_Architecture` $>$ `3Gem_Antigravity_Workflow`  
**Environment Lock:** `REAL_DATA=0` (Synthetic data only) | **Database:** PostgreSQL 16 (`synchronous_commit=on`, `READ COMMITTED`)

---

## 1. Verification Philosophy, Scope & Common-Mode Independence (`F17`)

### 1.1 Honest Verification Boundaries (Claims Discipline §19)
Every verification mechanism in RHP-1 states precisely what it proves and what it does not prove:
1. **Bounded Model Checking (`spec/rhp1.qnt` via Quint / Apalache):** Checks the modelled control plane at bounded parameters ($F=3$ facilities, $E=4$ epochs, $\le 25$ steps). It proves that no invariant violation exists within those bounds for the specification model. It is **not** a proof for unbounded network sizes and **not** a proof of the Python/SQL implementation.
2. **Model-Based Conformance Vectors (`spec/vectors/*.json`):** Deterministic state-transition traces covering all 28 real-world scenarios (`v8 §4.8`) and all transition guards (`Architecture §4`). Replayed against the live FastAPI + PostgreSQL 16 stack to verify implementation conformance to `spec/transitions.yaml`.
3. **Stateful Property-Based & Barrier Concurrency Testing (`Hypothesis` + `asyncio.Barrier(200)`):** Exercises real PostgreSQL row locking (`SELECT ... FOR UPDATE`), partial unique index `one_lease`, idempotency advisory locks, and Toxiproxy network faults. Provides empirical evidence under stated test conditions, not a formal proof of absence of all bugs.
4. **Independent Runtime Monitor (`monitor/monitor.py`):** Continuously re-derives every referral's state from the committed `event` log in a `REPEATABLE READ READ ONLY` transaction and performs a differential check against the `referral` row while evaluating invariants `I1`–`I16`.

### 1.2 Common-Mode Independence Rule (`F17`)
To prevent the specification, server, and runtime monitor from sharing a common implementation defect:
- **Person A (Lane A):** Authors the FastAPI backend (`api/`), `spec/transitions.yaml`, and the Quint specification (`spec/rhp1.qnt`).
- **Person B (Lane B):** Authors the independent Python runtime monitor (`monitor/monitor.py`) strictly from the prose predicates in `Architecture §3` inside an isolated workspace that **never imports or reads server code**, connecting exclusively via the read-only PostgreSQL role `rhp_monitor` (which has no `SELECT` grant on `clinical_payload` or `event_secret`).
- **Mutation Gate (`M1`–`M6`):** Neither the test suite nor the monitor counts as valid until every seeded mutation in §6 trips its designated detector.
- **Anti-Reward-Hacking Lock (`CODEOWNERS`):** AI coding agents are strictly prohibited from modifying `spec/transitions.yaml`, `spec/rhp1.qnt`, `spec/vectors/`, `db/schema.sql`, or `monitor/monitor.py` to make a failing test pass.

---

## 2. Static & Pre-Flight Self-Audit CI Suite (`ST-1` to `ST-5`)

These five automated checks (`scripts/run_self_audit.sh`) run on every commit before any integration test executes.

| Test ID | Target | Verification Procedure | Pass Criterion |
|---|---|---|---|
| `ST-1` | Global Lock Order (`F1`, `I14`) | 1. AST scan of `api/` confirming every SQL transaction acquiring multiple table locks executes strictly in order: `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`.<br>2. Verify `poller.py` Phase 1 and `relay.py` execute a single committed `UPDATE ... FOR UPDATE SKIP LOCKED` statement without holding locks across `apply_command()`.<br>3. Attempt direct `INSERT`/`UPDATE` on `referral`, `offer`, `deadline`, `event`, `payload_grant`, and `outbox` without setting `rhp.locked_referral`. | Zero AST lock-order violations; direct writes without `rhp.locked_referral` fail with PostgreSQL exception `I14_LOCK_NOT_HELD`. |
| `ST-2` | Timing Math & Profile Bounds (`F2`, `F3`, `I13`) | Execute `validate(profile, REAL_DATA)` across `PILOT_OB_CRITICAL`, `PILOT_STANDARD`, `DEMO_FAST`, and `DEMO_VOICE`. Verify $T_{max} = F \cdot (A + D + \epsilon) \le B$, notice rungs $= (0, A/4, 3A/4)$, and voice stagger $A/4 + (S-1)\cdot\delta + V \le 3A/4$. | Exact values verified:<br>• `PILOT_OB_CRITICAL`: $3 \cdot (60 + 180 + 3)\text{ s} = 729\text{ s} \le 900\text{ s}$; voice $15000 + 2 \cdot 5000 + 20000 = 45000\text{ ms} \le 45000\text{ ms}$.<br>• `PILOT_STANDARD`: $3 \cdot (120 + 300 + 3)\text{ s} = 1269\text{ s} \le 1500\text{ s}$; voice $30000 + 2 \cdot 10000 + 20000 = 70000\text{ ms} \le 90000\text{ ms}$.<br>• `DEMO_FAST`: $3 \cdot (3 + 4 + 1)\text{ s} = 24\text{ s} \le 25\text{ s}$ (voice off).<br>• `DEMO_VOICE`: $2 \cdot (45 + 20 + 1)\text{ s} = 132\text{ s} \le 150\text{ s}$; voice $11250 + 0 + 20000 = 31250\text{ ms} \le 33750\text{ ms}$. |
| `ST-3` | 24-Table DDL & Constraint Scan (`F4`) | Load `db/schema.sql` into a clean PostgreSQL 16 instance (`psql -v ON_ERROR_STOP=1`). Query `information_schema.tables`, `pg_constraint`, `pg_indexes`, and `pg_trigger`. | All 24 tables created; deferred FK `referral_lease_fk` intact; partial unique index `one_lease` and `one_active_grant` present; all append-only, lock-guard, chain-guard, and `i1_pending_deadline` triggers enabled; role grants match §7. |
| `ST-4` | Idempotency Matrix (`F14`) | Run the 8-case idempotency test suite (`T-F14`) against `apply_command()` Step 1. | All 8 cases return exact status codes and identical replayed bodies; zero duplicate `event` rows. |
| `ST-5` | Claims & Residual Linter (`F15`, §19) | Scan all Markdown, UI copy, and comments (excluding the forbidden-claims column of §19) for banned phrases and scan failure matrices for bare `"none"` residuals. | Zero occurrences of `"mathematically proven system"`, `"bullet-proof"`, `"airtight"`, `"zero loopholes"`, `"immutable log"`, `"ABDM compliant"`, `"BSA certified"`, `"lives saved"`, `"eliminates ping-pong"`; every residual row states a bound and reason. |

---

## 3. Formal Control-Plane Verification (`spec/rhp1.qnt`)

### 3.1 Quint Randomised Simulator & Apalache Bounded Model Checker
Run the following commands in CI (`scripts/verify_spec.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. Randomised simulation (20,000 samples, up to 25 steps)
quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000

# 2. Bounded model checking via Apalache (F=3, MAXE=4)
quint verify spec/rhp1.qnt --invariant safety --max-steps 20

# 3. Track independence run test (transport advances before and after offerFirst)
quint run spec/rhp1.qnt --main rhp1 --max-samples 100

# 4. Non-vacuity reachability checks (each MUST fail with a witness trace)
for target_inv in \
  'not (hs == "ACCEPTED")' \
  'not (hs == "DISPATCH")' \
  'not (hs == "CLOSED")' \
  'not (off.get(1) == "SOFT")'; do
  if quint run spec/rhp1.qnt --invariant "$target_inv" --max-steps 15 --max-samples 5000 >/dev/null 2>&1; then
    echo "VACUITY FAILURE: $target_inv was never violated (state unreachable)!"
    exit 1
  fi
done
echo "All Quint safety and non-vacuity checks passed."
```

### 3.2 Python Explicit-State Explorer (`scripts/explore_transitions.py`)
As the deterministic fallback and direct verifier of the production `spec/transitions.yaml` file:
- Performs breadth-first state-space exploration over `transitions.yaml` for $F=3$ facilities, $E=4$ epochs, modes $\in \{\text{SEQUENTIAL}, \text{PARALLEL2}\}$, and counter rounds $\in \{0, 1, 2\}$.
- Evaluates `I1` (in-flight referrals have $\ge 1$ open offer or transition to `ESCALATED_TO_DISPATCHER`), `I2` ($\le 1$ `ACCEPTED` offer and `lease != 0` iff count $= 1$), `I3` (`TR_UPDATE` enabled in every non-terminal `hs_state`), `I9` (no facility offered twice), and `I12` ($\text{open\_offers} \le 2$).
- Verifies reachability (`T-F6`): from every reachable non-terminal state, at least one deterministic path reaches `CLOSED` or `CANCELLED`.

---

## 4. F1–F20 Architectural Closure Test Specifications

Every architectural fix `F1`–`F20` in `Architecture §1` has a dedicated automated test in `tests/closures/`:

| Test ID | Closure | Exact Test Procedure & Fault Injection | Expected Outcome & Quantitative Assertion |
|---|---|---|---|
| `T-F1` | `lock_order_200way` (F1) | Spawn 150 concurrent worker coroutines issuing `ACK`, `COUNTER`, `ACCEPT`, `DECLINE`, and `TR_UPDATE` across 5 referrals while 50 concurrent poller ticks claim due deadlines and invoke `apply_command(TIMEOUT)`. Record `pg_stat_database.deadlocks` before and after. Also attempt direct SQL `UPDATE offer SET status='ACCEPTED'` without setting `rhp.locked_referral`. | `deadlocks_after - deadlocks_before == 0`; `log_lock_waits` shows zero circular waits; direct SQL without `rhp.locked_referral` raises `I14_LOCK_NOT_HELD`. |
| `T-F2` | `profile_guard` (F2) | 1. Tamper 1 byte in `DEMO_FAST` JSON and boot API.<br>2. Set `REAL_DATA=1` and `PROFILE=DEMO_FAST` (then `DEMO_VOICE`) and boot API.<br>3. Create referral under `PILOT_OB_CRITICAL` ($A=60000\text{ ms}$) and inspect `deadline` rows created at `CREATE`. | 1. Boot fails with `Ed25519SignatureError`.<br>2. Boot fails with `AssertionError: demo profile with REAL_DATA=1`.<br>3. `deadline` rows exist for `NOTICE_VOICE` at $+15000\text{ ms}$ ($A/4$), `NOTICE_PROXY` at $+45000\text{ ms}$ ($3A/4$), and `ACK` at $+60000\text{ ms}$ ($A$). |
| `T-F3` | `tmax_validator` (F3) | Construct synthetic profiles violating: (a) $F \cdot (A + D + \epsilon) > B$ ($3 \cdot (60 + 180 + 3) = 729 > 700$), and (b) voice stagger $A/4 + (S-1)\cdot\delta + V > 3A/4$. Pass to `validate()`. Also test `CREATE` with a 5-facility chain when profile $F=3$. | `validate()` raises `AssertionError` on (a) and (b). `CREATE` truncates `referral.chain` to length $F=3$. |
| `T-F4` | `ddl_load_fk_scan` (F4) | Load `db/schema.sql`. Attempt: (a) `UPDATE` and `DELETE` on `event`, `checkpoint`, `rejected_command` as `rhp_app`; (b) `SELECT` on `clinical_payload` and `event_secret` as `rhp_monitor`; (c) two `ACCEPTED` offers on one referral. | (a) Raises `APPEND_ONLY <table>`; (b) raises `permission denied`; (c) raises unique violation on index `one_lease`. |
| `T-F5` | `arrival_cases` (F5) | Execute all 6 arrival sub-cases:<br>(a) Geofence trigger ($<200\text{ m}$ + dwell) at lease holder;<br>(b) Arrival at facility with `OPEN`/`ACKED`/`SOFT_OPEN` offer followed by immediate `ACCEPT`;<br>(c) Unannounced arrival at facility with no offer;<br>(d) Crew issues `TR_DESTINATION_CHANGE` en route;<br>(e) Crew sends `TR_DESTINATION_CHANGE(accepted=false)` after redirect advisory;<br>(f) Ambulance past highway turn-off receives cached Matrix detour ETA. | (a) Emits `ARRIVAL_SUGGESTED` only (`tr_state` stays `EN_ROUTE` until human `TR_UPDATE(ARRIVED)`);<br>(b) `ACCEPT` succeeds only when all `need_class_requirement` capabilities are confirmed and unexpired (`I15`);<br>(c) Emits `ARRIVAL_AT_NON_OWNER` + pages dispatcher, never blocks care;<br>(d) `tr_facility_id` updated, `hs_state` untouched;<br>(e) Logged with `accepted=false`, lease unchanged, dispatcher paged;<br>(f) Advisory includes detour ETA; no automatic reroute. |
| `T-F6` | `reachability_bfs` (F6) | 1. Run BFS reachability check over all states.<br>2. Test `CLOSE` with `ADMITTED_STABLE` when `tr_state='EN_ROUTE'`.<br>3. Advance a referral to `ACCEPTED` + `HANDED_OVER` under `DEMO_FAST` (`CLOSURE` $= 20\text{ s}$) and leave unclosed for $42\text{ s}$. | 1. Every state can reach `CLOSED` or `CANCELLED`.<br>2. Rejected with `422` (`ADMITTED_*` requires `HANDED_OVER`).<br>3. At $t=20\text{ s}$, `CLOSURE_OVERDUE` emitted and deadline re-armed once; at $t=40\text{ s}$, system auto-closes with `outcome='UNKNOWN_COUNTER_REFERRAL'`, `proxy=true`, `actor=system`. |
| `T-F7` | `pin_lockout_scope` (F7) | 1. Redeem `enrollment_ticket` twice.<br>2. From Session A on Facility 1's duty role, submit 3 `ACCEPT` calls with wrong PIN (`0000`), then 1 call with valid PIN. Simultaneously from Session B (same roster slot, different device/session), submit `ACCEPT` with valid PIN.<br>3. Simulate Exotel outbound call where AMD detects voicemail / no keypress-1 within $8\text{ s}$. | 1. Second redemption rejected (`used_at IS NOT NULL`).<br>2. Session A `pin_failed` increments `1 -> 2 -> 3` across rollbacks via autonomous connection, emits `PIN_LOCKED`, and returns `429 PIN_LOCKED` on 4th attempt. Session B succeeds with `200 OK` (no cross-session DoS).<br>3. Call marked `UNANSWERED`; zero `OFFER_ACKED` events written. |
| `T-F8` | `tamper_vs_restore` (F8) | 1. Take checkpoint $C_1$ at `head_seq=5`, append 2 events (`head_seq=7`), then as PostgreSQL superuser delete `seq IN (6,7)` and reset `referral.head_seq=5` without a `RESTORE` checkpoint.<br>2. Repeat, but sign a `RESTORE` checkpoint referencing $C_1$ with the offline cold Ed25519 key and append a `RESTORE` event at `seq=6` whose `prev_hash` equals $C_1$'s `head_hash`. | 1. Browser verifier and monitor report `TRUNCATED at seq=5` / `TAMPER`.<br>2. Browser verifier and monitor verify the cold signature and `RESTORE` link and report `VALID (RESTORED FROM C1)`. |
| `T-F9` | `detail_check_fuzz` (F9) | Run 5,000 Hypothesis examples generating random JSON objects for `event.detail` (including floats like `3.14`, free-text patient names, lowercase strings, unapproved keys) and test both Pydantic models and direct SQL `INSERT INTO event`. Also test aggregate export with cell counts $n \in \{1, 4, 5, 10\}$. | 100% of non-allowlisted keys, floats, and free-text strings rejected by both Pydantic (`422`) and PostgreSQL `rhp_detail_ok` (`CHECK` violation). Aggregate export buckets timestamps to 4-hour windows and suppresses all cells with $n < 5$. |
| `T-F10` | `sse_revoke` (F10) | Open an authenticated SSE stream for Facility 1 (`OFFERED`, active `payload_grant`). Verify clinical frames arrive. Have Facility 1 `DECLINE` (or get `SUPERSEDED` by Facility 2). Emit a new observation event on the referral. | Within 1 relay cycle of `DECLINE`/`SUPERSEDE`, Facility 1's SSE stream receives `GRANT_REVOKED` control frame, its client DOM wipes clinical state, and subsequent SSE frames for that referral have clinical fields stripped (`I10`). |
| `T-F11` | `clock_step` (F11) | 1. Record `referral.head_ts` at event `seq=1`. Inject a mock/wrapped DB clock returning `clock_timestamp() - interval '10 seconds'` on `seq=2`.<br>2. Write `heartbeat` row with `ntp_offset_ms = 2500`. | 1. `seq=2` is stamped with `server_ts == seq_1.server_ts` via `GREATEST(clock_timestamp(), r.head_ts)` (`I16` holds).<br>2. Monitor raises `CLOCK_OFFSET_ALARM` within $\le 5\text{ s}$. |
| `T-F12` | `offline_stale` (F12) | 1. Confirm resources on Offer 1 (`expires_at = ts + 10s` under `DEMO_FAST`). Wait $11\text{ s}$ (offline client queues `ACCEPT`), then flush `ACCEPT`.<br>2. Queue `ACCEPT` on Offer 1 (`SOFT_OPEN`), let Offer 2 `ACK` first, then flush Offer 1's `ACCEPT`. | 1. Server returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`; PWA displays reconfirmation modal; re-issuing `RESOURCE_CONFIRM` + fresh `ACCEPT` succeeds.<br>2. Server returns `409 LATE_ACCEPT_REJECTED`. |
| `T-F13` | `open_cap` (F13) | 1. In `SEQUENTIAL` mode: Facility 1 times out $\to$ Facility 1 becomes `SOFT_OPEN`, Facility 2 becomes `OPEN` ($\text{open\_offers}=2$). Before Facility 2 ACKs, Facility 2 times out and Facility 3 opens.<br>2. In `PARALLEL2` mode: Facility 1 (`OPEN`) issues `COUNTER` while Facility 2 (`OPEN`) issues `ACCEPT` concurrently. | 1. At the instant Facility 3 opens, Facility 1 (`SOFT_OPEN`) transitions to `TIMED_OUT`, keeping `open_offers == 2` (`I12` never exceeds 2).<br>2. Whichever commits first wins the lease; if Facility 2's `ACCEPT` wins, Facility 1's `COUNTERED` offer is `SUPERSEDED` and `CONFIRM_COUNTER(true)` returns `409 LEASE_HELD`. |
| `T-F14` | `idem_matrix` (F14) | Execute all 8 rows of the Idempotency Edge-Case Table (§5.2 below) against `/v1/offers/{id}/accept`. | All 8 cases match exact HTTP status codes and payloads; `event` table contains at most 1 row per command. |
| `T-F15` | `residual_lint` (F15) | Parse §18 Failure-Mode Matrix in `Architecture` and §9 of `TEST_PLAN.md`. | Every row has a non-empty bounded residual with a technical reason, or is explicitly justified under lock order. |
| `T-F16` | `loop_rehearsal` (F16) | Automated Playwright + API harness executing the 30-second live proof loop under `DEMO_FAST` (§10). | Complete loop finishes in $\le 30.0\text{ s}$ across 3 consecutive runs; all 7 time-window assertions pass. |
| `T-F17` | `mutation_suite` (F17) | Run `scripts/run_mutations.sh` executing `M1`–`M6` + `M7` (Track-Independence mutation). | 7 of 7 mutations are caught by their designated checker within the timeout budget. |
| `T-F18` | `cost_recompute` (F18) | Run `pytest tests/test_cost_model.py` checking the reconciled AWS `ap-south-1` table. | Base $= \$140/\text{mo}$ ($\$840/6\text{mo}$), App subtotal $= \$190/\text{mo}$ ($\$1,140/6\text{mo}$), Total with telephony + 10% contingency $= \$236.50/\text{mo}$ ($\$1,419/6\text{mo} \approx \$1,420$). |
| `T-F19` | `v7_map` (F19) | Replay traces covering all 12 `Problem Statement v7` conceptual states (`CREATED`, `OFFERED`, `ACKNOWLEDGED`, `ACCEPTED`, `COUNTERED`, `DECLINED`, `TIMED_OUT`, `ESCALATED`, `ARRIVAL_REJECTED`, `ESCALATED_TO_DISPATCHER`, `CANCELLED`, `CLOSED`) and verify the tuple `(referral.hs_state, offer.status, referral.tr_state, event.type)`. | 12 of 12 mappings match the `Architecture §4` v7-to-RHP-1 mapping table. |
| `T-F20` | `broken_isolation` (F20) | 1. Start API with `BROKEN_BUILD=1` and `REAL_DATA=1`.<br>2. Start API with `BROKEN_BUILD=1` and `DATABASE_URL` pointing to `rhp_main`.<br>3. Attempt to connect to `rhp_main` using the `rhp_scratch` database role.<br>4. Start API with valid `BROKEN_BUILD=1` on `rhp_scratch_broken` and query `/mode`. | 1 & 2. Process exits immediately with exit code `78`.<br>3. `pg_hba.conf` / role check rejects authentication.<br>4. `/mode` returns `{"broken_build": true, "db": "rhp_scratch_broken"}` and UI renders flashing red banner `BROKEN BUILD — SCRATCH DB`. |

---

## 5. Invariants I1–I16 Test Matrix & Idempotency Edge Matrix

### 5.1 Invariant Test Matrix (`T-I1` to `T-I16`)

| Test ID | Invariant | DB / Server Enforcement Tested | Monitor Rule Tested | Pass Condition |
|---|---|---|---|---|
| `T-I1` | **I1 (No silent referral)** | Deferred constraint trigger `i1_pending_deadline` on `referral` at `COMMIT`. Attempt to update a non-terminal referral while cancelling all its `PENDING` deadlines in the same txn. | Query `deadline WHERE status='PENDING' AND due_at < clock_timestamp() - TAU_MS`. | Transaction aborts with `I1_NO_PENDING_DEADLINE`; overdue deadline injected in scratch DB triggers monitor `("I1", referral_id)` within 1 cycle. |
| `T-I2` | **I2 (Single owner lease)** | Partial unique index `one_lease` on `offer(referral_id) WHERE status='ACCEPTED'` + `SELECT ... FOR UPDATE` on `referral`. | Fold counts `ACCEPTED` offers $>1$ or `e.epoch <= st["epoch"]` on `LEASE_GRANTED`. | 200-way concurrent accept (`T-C1`) grants exactly 1 lease; `lease_epoch` strictly increases on `ACCEPT`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`. |
| `T-I3` | **I3 (Never block care)** | Issue `TR_UPDATE` (`DISPATCHED`, `EN_ROUTE`, `ARRIVED`, `HANDED_OVER`) and `TR_DESTINATION_CHANGE` while `hs_state` is in each of `CREATED`, `OFFERED`, `ACKNOWLEDGED`, `COUNTERED`, `ACCEPTED`, `ESCALATED_TO_DISPATCHER`, and with `mgso4_status='UNKNOWN'`. | Flag any `rejected_command` for `TR_UPDATE` where `hs_state NOT IN ('CLOSED', 'CANCELLED')` and transition is valid on `tr_state`. | 100% of valid transport transitions return `200 OK` regardless of `hs_state` or `mgso4_status`. |
| `T-I4` | **I4 (Exactly-once & gap-free `seq`)** | `idempotency(actor_id, key)` PK, `event.event_id UNIQUE`, `event(referral_id, seq)` PK, and trigger `rhp_event_guard` (`NEW.seq <> r.head_seq + 1`). | Monitor fold checks `e.seq != st["seq"] + 1` and duplicate `event_id`. | Retries with same key or same `event_id` produce 0 duplicate rows; `max(seq) == count(*)` per referral. |
| `T-I5` | **I5 (Hash chain, checkpoints, outcome on close)** | Triggers `event_ao`, `checkpoint_ao`, `rhp_event_guard`, and `referral` CHECK `((hs_state IN ('CLOSED','CANCELLED')) = (outcome IS NOT NULL AND closed_at IS NOT NULL))`. | Monitor recomputes `SHA256(prev_hash || JCS(core))` for every event and verifies Ed25519 checkpoint signatures. | Any tampered byte in `event` or missing `outcome` on `CLOSED`/`CANCELLED` is rejected or flagged immediately. |
| `T-I6` | **I6 (Rostered authority & PIN)** | `apply_command()` Steps 2, 3, and 5 verify active `session`, `device`, `roster` (`valid_from <= ts <= valid_to`), facility match, and Argon2id PIN (or `proxy=true` for dispatcher). | Monitor verifies `actor_roster_id` has an active `roster` row at `server_ts` for the target facility/role or `proxy=true`. | Unrostered user, expired shift, wrong facility, or bad PIN returns `401`/`403`. |
| `T-I7` | **I7 (No invented destination)** | Trigger `offer_chain_guard` checks `NEW.source='CHAIN' AND NOT (NEW.facility_id = ANY(chain))`. | Monitor checks every `OFFER_CREATED` has `facility IN referral.chain` or `source == 'DISPATCHER'`. | Inserting a `CHAIN` offer for a facility outside `referral.chain` raises `I7_NOT_IN_CHAIN`. |
| `T-I8` | **I8 (Stale writers fenced)** | Step 5 checks `cmd.expected_version == r.version` and `cmd.expected_epoch == r.lease_epoch`. On mismatch, rolls back to `SAVEPOINT sp_cmd` and logs to `rejected_command`. | Monitor checks no applied event carries `e.epoch < st["epoch"]`. | Stale command returns `412 Precondition Failed`, writes 1 row to `rejected_command`, and leaves `referral` and `event` untouched. |
| `T-I9` | **I9 (No referral loops)** | `UNIQUE(referral_id, facility_id)` constraint on `offer` + `advance()` filter excluding previously offered facilities. | Monitor fold checks no facility appears in two `OFFER_CREATED` events for the same referral. | Attempting to re-offer a facility that declined, timed out, or rejected on arrival is skipped by `advance()` and rejected by DB constraint. |
| `T-I10` | **I10 (Clinical payload grant enforcement)** | `one_active_grant` partial unique index + per-event SSE filter + `/v1/referrals/{id}/payload` authorization check against `payload_grant WHERE revoked_at IS NULL`. | Monitor verifies no clinical payload access or unstripped SSE frame occurs after `GRANT_REVOKED`. | Revoked facility receives `403` on payload fetch and stripped SSE frames within 1 relay cycle. |
| `T-I11` | **I11 (PHI-free metadata allowlist)** | Pydantic `extra='forbid'` + PostgreSQL `CHECK (rhp_detail_ok(type, detail))`. | Monitor scans `event.detail` against `rhp_allowed(type)` and value regexes. | Any non-allowlisted key, float, or free-text string fails with `422` / `CHECK` violation. |
| `T-I12` | **I12 ($\le 2$ open offers)** | `referral.open_offers CHECK (open_offers BETWEEN 0 AND 2)` maintained under the referral lock. | Monitor fold counts offers in `{'OPEN','ACKED','COUNTERED','SOFT_OPEN'}` and checks `count <= 2`. | `open_offers` never exceeds 2 in `SEQUENTIAL`, `PARALLEL2`, `SOFT_OPEN`, or `COUNTER` states. |
| `T-I13` | **I13 ($T_{max} \le B$)** | Startup validator `validate(profile, REAL_DATA)` and `/healthz` recomputation. | Monitor recomputes $F \cdot (A + D + \epsilon) \le B$ at startup and on every cycle. | Boot aborts if $T_{max} > B$; `/healthz` reports profile hash and $T_{max}$ margin. |
| `T-I14` | **I14 (Referral lock required for state writes)** | `SELECT * FROM referral WHERE id=%s FOR UPDATE` + `set_config('rhp.locked_referral', id, true)` + triggers `lk_referral`, `lk_offer`, `lk_deadline`, `lk_event`, `lk_grant`, `lk_outbox`. | Monitor checks `pg_stat_database.deadlocks` delta $= 0$ and `log_lock_waits`. | Any contract write without holding the referral lock raises `I14_LOCK_NOT_HELD`. |
| `T-I15` | **I15 (Unexpired resource confirmations)** | Step 7 verifies every capability in `need_class_requirement` for `r.need_class` has a row in `offer_resource_confirmation` with `expires_at > ts`. | Monitor checks `OFFER_ACCEPTED` is preceded by unexpired `RESOURCE_CONFIRMED` events for all required capabilities. | Missing or expired confirmation returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`. |
| `T-I16` | **I16 (Monotone per-referral server timestamp)** | `ts = GREATEST(clock_timestamp(), r.head_ts)` under referral lock + `rhp_event_guard` (`NEW.server_ts < r.head_ts`). | Monitor fold checks `e.ts >= st["ts"]` for every event in `seq` order. | Backward clock jump on host cannot produce decreasing `server_ts`; manual insert with smaller `server_ts` raises `CHAIN_BREAK`. |

### 5.2 Idempotency Edge-Case Test Matrix (`T-F14`)

| Case # | Test Scenario | Input `(actor_id, Idempotency-Key, payload, event_id)` | Expected HTTP Status & Code | DB State Assertion |
|---|---|---|---|---|
| 1 | Prior success replay | Same `actor_id`, same `key`, identical JCS payload hash after `200 OK` commit | `200 OK` (exact stored JSON response body) | `event` count $= 1$; `idempotency.status = 'DONE'`. |
| 2 | Prior domain rejection replay | Same `actor_id`, same `key`, identical JCS payload hash after `409 LEASE_HELD` or `412` commit | `409` / `412` / `422` (exact stored error body) | `rejected_command` count $= 1$; `idempotency.status = 'DONE'`. |
| 3 | Key reused with modified payload | Same `actor_id`, same `key`, different `decline_reason` or `expected_version` | `422 KEY_REUSED_DIFFERENT_PAYLOAD` | Original `idempotency` row unchanged; no new `event`. |
| 4 | Concurrent in-flight duplicate | Two coroutines send identical `(actor_id, key, payload)` at a barrier while Step 4 sleeps $200\text{ ms}$ | Winner: `200 OK`; Concurrent duplicate: `409 DUPLICATE_IN_FLIGHT` (advisory lock `pg_try_advisory_xact_lock` returns `false`) | Retry of second coroutine after winner commits returns stored `200 OK`. |
| 5 | Crash / unhandled exception mid-transaction | Inject `RuntimeError` after Step 8 before Step 10 commit, then retry with same `(actor_id, key)` | First call: `500`; Retry: `200 OK` | Unhandled error rolls back entire txn (including `IN_FLIGHT` row); retry executes cleanly once. |
| 6 | Expired idempotency key ($>48\text{ h}$) with same `event_id` | Purge `idempotency` row (`expires_at < now()`), resend command with same `event_id` | `409 DUPLICATE_EVENT_ID` (returns original committed event view) | `event.event_id UNIQUE` constraint catches replay beyond 48h window. |
| 7 | Missing `Idempotency-Key` header | `POST /v1/referrals` or `/v1/offers/{id}/accept` with no `Idempotency-Key` header | `422 MISSING_IDEMPOTENCY_KEY` | Rejected before DB transaction opens. |
| 8 | New `Idempotency-Key` but reused `event_id` | Same `event_id` sent under `key-2` after `key-1` succeeded | `409 DUPLICATE_EVENT_ID` | Savepoint rolls back; zero duplicate `event` rows. |

---

## 6. Mutation Testing Suite (`M1`–`M6` + `M7` Track-Independence)

The script `scripts/run_mutations.sh` applies each patch in turn (or runs against `rhp_scratch_broken`), executes the verification suite, and asserts that the designated detector fails with the exact expected signal. **If any mutation survives (detector stays green), the build fails.**

| Mutation ID | Target Artifact | Exact Mutation Applied | Detector That Must Trip | Required Failure Signal |
|---|---|---|---|---|
| `M1` | `api/pipeline.py` (Step 5) | Comment out `if cmd.expected_epoch != r.lease_epoch: raise Reject(412, "STALE_EPOCH")`. | Conformance vector `V-STALE-EPOCH` + Independent Monitor | Vector fails (gets `200` instead of `412`); Monitor outputs `("I8", referral_id, seq)`. |
| `M2` | `api/pipeline.py` (Step 4) + `rhp_scratch_broken` | Remove `FOR UPDATE` from `SELECT * FROM referral` and drop index `one_lease` (`BROKEN_BUILD=1`). | `T-C1` (`race200`) + Independent Monitor | `race200` asserts `sum(r.status_code == 200) > 1`; Monitor outputs `("I2", referral_id, seq)` within $\le 2\text{ s}$. |
| `M3` | `api/poller.py` | Hold `SELECT ... FROM deadline FOR UPDATE` open in an uncommitted transaction while calling `apply_command(TIMEOUT)` on the same referral as a concurrent `ACCEPT`. | `T-F1` (`lock_order_200way`) | PostgreSQL raises `DeadlockDetected` (`deadlocks_delta > 0`) or `rhp_require_lock` raises `I14_LOCK_NOT_HELD` on Phase 1 status mutation. |
| `M4` | `spec/rhp1.qnt` (`timeout` action) | Change `val canNext = nxt <= 3 and off.get(nxt) == "NONE"` in `timeout(f)` so that a `SOFT` offer is not expired when `nxt` opens, allowing 3 simultaneous open offers. | `quint run spec/rhp1.qnt --invariant safety` | Quint produces a counterexample trace violating `I12` (`nOpen(off) == 3`). |
| `M5` | `api/pipeline.py` (`append_event`) | Force `prev_hash = b"\x00" * 32` when `seq == 2`. | Browser Verifier (`verifier.js`) + Independent Monitor + DB trigger `rhp_event_guard` | DB trigger raises `CHAIN_BREAK seq=2` (and if trigger is bypassed on scratch DB, Monitor outputs `("I5", referral_id, 2)` and JS verifier prints `BROKEN referral=... seq=2 kind=PREV`). |
| `M6` | `api/pipeline.py` (Step 7) | Change confirmation check from `expires_at > ts` to `expires_at IS NOT NULL`. | Conformance vector `V-STALE-CONFIRM` + Independent Monitor | Vector fails (accepts expired confirmation with `200` instead of `409`); Monitor outputs `("I15", referral_id, seq)`. |
| `M7` | `spec/transitions.yaml` & `spec/rhp1.qnt` | Add guard `hs_state != 'ESCALATED_TO_DISPATCHER'` to `TR_UPDATE` in `transitions.yaml` and `hs != "DISPATCH"` to `trStep` in `rhp1.qnt`. | Vector `V-S08` + Independent Monitor (`I3`) + Quint `transportNeverGated` | Monitor flags `("I3", referral_id)` on rejected `TR_UPDATE`; Quint run test fails. |

---

## 7. The 28 Conformance Vectors (`v8 §4.8`) & Stateful Property Tests

Every real-world scenario in `Solution v8 §4.8` maps to a deterministic JSON conformance vector in `spec/vectors/` replayed by `pytest tests/test_conformance_vectors.py`.

| Vector ID | Scenario (`v8 §4.8`) | Initial Setup & Command Sequence | Expected HTTP Statuses | Final `(hs_state, tr_state, lease_epoch)` & Key Events |
|---|---|---|---|---|
| `V-S01` | 1. Receiver has no smartphone | `CREATE(SEQ, [F1,F2])` $\to$ `NOTICE_VOICE` fires at $A/4$ $\to$ Exotel webhook `ACK(VOICE, press=1)` $\to$ `RESOURCE_CONFIRM(VOICE)` $\to$ `ACCEPT(VOICE, PIN)`. | `200, 200, 200, 200` | `('ACCEPTED', 'REQUESTED', 1)`; events: `OFFER_ACKED(channel='VOICE')`, `OFFER_ACCEPTED`, `LEASE_GRANTED`. |
| `V-S02` | 2. Receiver cannot take but suggests redirect | `CREATE(SEQ, [F1,F2])` $\to$ F1 `DECLINE(reason='NO_NICU', suggest=F2)`. | `200, 200` | `('OFFERED', 'REQUESTED', 0)`; F1 `DECLINED` (grant revoked), F2 `OPEN`; suggestion shown as advisory only, chain order respected (`I7`). |
| `V-S03` | 3. Receiver can take partly (`COUNTER`) | `CREATE(SEQ, [F1,F2])` $\to$ F1 `ACK` $\to$ F1 `COUNTER(round=1, mask=NO_NICU)` $\to$ Referrer `CONFIRM_COUNTER(confirmed=true)`. | `200, 200, 200, 200` | `('ACCEPTED', 'REQUESTED', 1)`; `OFFER_COUNTERED`, `COUNTER_RESOLVED(confirmed=true)`, `LEASE_GRANTED`. |
| `V-S04` | 4. Duty nurse busy (intra-facility notice ladder) | `CREATE(SEQ, [F1,F2])` $\to$ Rung 0 SSE/FCM to Nurse/CMO/Consultant $\to$ Rung $A/4$ Voice slot 1, then slot 2 at $A/4+\delta$ $\to$ CMO answers `ACK` + `ACCEPT`. | `200, 200, 200` | `('ACCEPTED', 'REQUESTED', 1)`; `NOTICE_SENT` rungs logged; `OFFER_ACKED` by CMO stops remaining ladder rungs. |
| `V-S05` | 5. Two facilities accept at once (`PARALLEL2`) | `CREATE(PAR2, [F1,F2])` $\to$ F1 and F2 confirm resources $\to$ F1 `ACCEPT(v=1)` and F2 `ACCEPT(v=1)` at barrier. | Winner: `200`; Loser: `409 LEASE_HELD` | `('ACCEPTED', 'REQUESTED', 1)`; Winner offer `ACCEPTED`, Loser offer `SUPERSEDED` (grant revoked), 1 row in `rejected_command`. |
| `V-S06` | 6. Late accept after escalation (`SOFT_OPEN`) | `CREATE(SEQ, [F1,F2])` $\to$ F1 `TIMEOUT(ACK)` (F1=`SOFT_OPEN`, F2=`OPEN`).<br>Subcase 6a: F1 `ACCEPT` before F2 ACKs.<br>Subcase 6b: F2 `ACK` first (F1$\to$`TIMED_OUT`), then F1 `ACCEPT`. | 6a: `200`<br>6b: `409 LATE_ACCEPT_REJECTED` | 6a: `('ACCEPTED', 'REQUESTED', 1)` to F1, F2 `SUPERSEDED`.<br>6b: `('ACKNOWLEDGED', 'REQUESTED', 0)` at F2, F1 `TIMED_OUT`. |
| `V-S07` | 7. Accept, then cannot take on arrival (`ARRIVAL_REJECTED`) | F1 holds lease (`epoch=1`), ambulance `ARRIVED` at F1 $\to$ F1 issues `ARRIVAL_REJECTED(reason='OT_OCCUPIED')`. | `200` | `('OFFERED', 'ARRIVED', 2)`; F1 `ARRIVAL_REJECTED` (grant revoked, lease cleared), F2 `OPEN` (`ladder_cursor=2`). |
| `V-S08` | 8. All approved facilities fail | `CREATE(SEQ, [F1,F2])` $\to$ F1 `DECLINE` $\to$ F2 `TIMEOUT(ACK)` (chain exhausted). | `200, 200, 200` | `('ESCALATED_TO_DISPATCHER', 'REQUESTED', 0)`; `open_offers=0`; `DISPATCH_ACTION` deadline `PENDING`. |
| `V-S09` | 9. Ambulance in dead zone (telemetry set-union) | Ambulance offline queues 3 GPS points (`e1, e2, e3`) and 2 vitals (`v1, v2`), reconnects and flushes batch twice. | `200, 200` | All 5 unique `telemetry.event_id` rows inserted once (set union, zero overwrites, zero duplicates). |
| `V-S10` | 10. Server or internet down (offline outbox reconcile) | Referrer creates card with `paper_code='RHP8K2M9*'`; ambulance proceeds; after reconnect, outbox flushes with original `Idempotency-Key`s. | `200` | Events committed in order with `client_ts_ms` preserved and authoritative `server_ts` assigned. |
| `V-S11` | 11. Wrong person "accepts" | User from Facility 3 (or expired shift / wrong PIN) calls `ACCEPT` on Facility 1's offer. | `403 Forbidden` | Offer remains `OPEN`; failure logged in `rejected_command`; `pin_failed` incremented if PIN mismatch. |
| `V-S12` | 12. Crew cannot use app (dispatcher proxy) | Dispatcher submits `TR_UPDATE(EN_ROUTE, proxy=true, proxy_for=emt_roster_id)`. | `200` | `('OFFERED', 'EN_ROUTE', 0)`; `TR_UPDATED` event has `channel='DISPATCHER_PROXY', proxy=true`. |
| `V-S13` | 13. Slip arrives with paper code | Receiving desk enters `paper_code` (8 Crockford Base32 + 1 mod-37 check char) to look up and link referral; also test 1 mutated character. | Valid: `200`; Mutated: `422 INVALID_PAPER_CODE_CHECKSUM` | Valid code links referral; single-character mutation or adjacent transposition rejected at client & API. |
| `V-S14` | 14. iPhone restricted background flush | iOS PWA flushes queued `TR_UPDATE` + `telemetry` on `visibilitychange -> visible`. | `200` | State updates cleanly on foreground resume; UI shows `"last confirmed Ns ago"` while backgrounded. |
| `V-S15` | 15. AI draft wrong / anchors required | `GET /v1/ai/draft` before committing `need_class` and `mgso4_status` $\to$ commit anchors $\to$ fetch draft with seeded error $\to$ disable `T3_EXTRAS` and create manually. | Pre-anchor: `423 ANCHOR_REQUIRED`; Post-anchor: `200`; Manual with AI off: `200` | Draft withheld until anchors committed; manual path has zero dependency on AI. |
| `V-S16` | 16. Patient delivers or stabilises before departure | Clinician issues `CANCEL(outcome='DELIVERED_EN_ROUTE', reason='STABILISED_AT_ORIGIN')` while `hs_state='OFFERED'`. | `200` | `('CANCELLED', 'TR_CANCELLED', 0)`; open offers `WITHDRAWN`, grants revoked, deadlines `CANCELLED`. |
| `V-S17` | 17. Patient refuses transfer | Clinician issues `CANCEL(outcome='PATIENT_REFUSED', reason='AMA_SIGNED')`. | `200` | `('CANCELLED', 'TR_CANCELLED', 0)`; terminal `outcome='PATIENT_REFUSED'` and `closed_at` populated (`I5`). |
| `V-S18` | 18. Ambulance breaks down | Handshake is `ACCEPTED` at F1; dispatcher issues `TR_UPDATE` / vehicle reassignment on transport track. | `200` | Handshake lease (`lease_facility_id=F1, lease_epoch=1`) remains completely unaffected (`I3`). |
| `V-S19` | 19. Receiver roster stale (delivery failure escalation) | Rung $A/4$ voice call to Slot 1 fails (`NO_ANSWER`) $\to$ after $\delta$, Slot 2 is called $\to$ after $3A/4$, `NOTICE_PROXY` pages dispatcher $\to$ at $A$, `TIMEOUT` advances to F2. | `200` | Escalates deterministically on schedule without stalling. |
| `V-S20` | 20. Counter loop ($\le 2$ rounds max) | F1 `COUNTER` (round 1) $\to$ Referrer rejects or F1 updates $\to$ F1 `COUNTER` (round 2) $\to$ F1 attempts 3rd `COUNTER`. | Round 1 & 2: `200`; Round 3: `409 MAX_COUNTER_ROUNDS_EXCEEDED` | `offer.counter_round` capped at 2 by guard and DB `CHECK (counter_round BETWEEN 0 AND 2)`. |
| `V-S21` | 21. Duplicate referral for same patient | Paper-code lookup shows existing active referral at origin; prompts link rather than silent auto-merge. | `200` | Referrals remain distinct contract entities unless clinician explicitly links/cancels duplicate. |
| `V-S22` | 22. Client clock wrong (2 hours ahead/behind) | Client sends `client_ts_ms = now() - 7200000` (or $+7200000$). | `200` | `event.client_ts_ms` recorded as sent; deadlines and `event.server_ts` use server `GREATEST(clock_timestamp(), r.head_ts)`. |
| `V-S23` | 23. SIM theft / PIN brute force | 3 failed PIN attempts on a session, followed by repeated lockouts across sessions on the same roster slot. | `403, 403, 403, 429 PIN_LOCKED` | Session locked $120\text{ s}$, `PIN_LOCKED` event emitted, dispatcher paged; repeated slot lockouts suspend slot. |
| `V-S24` | 24. Admin / Dispatcher override | Referral in `ESCALATED_TO_DISPATCHER` $\to$ Dispatcher issues `DISPATCHER_ASSIGN(facility=F3, reason='PHONE_CONFIRMED_CMO')`. | `200` | `('ACCEPTED', 'REQUESTED', 1)`; offer created with `source='DISPATCHER'`, `proxy=true`, flagged on monitor. |
| `V-S25` | 25. Receiver accepts but delays bed (APOT gaming) | F1 `ACCEPT`s at $t=10\text{ s}$; ambulance `ARRIVED` at $t=600\text{ s}$; `HANDED_OVER` does not occur before `HANDOVER` deadline $H$. | `200` | `HANDOVER_OVERDUE` event emitted; KPI projection reports `ARRIVED -> HANDED_OVER` (APOT) separately from `ACCEPT` latency. |
| `V-S26` | 26. Tertiary overload (`AT_CAPACITY`) | Tertiary facility F1 has 2 open offers (load guard cap) or declines with `decline_reason='AT_CAPACITY'`. | `200` | F1 declined with `AT_CAPACITY`; chain advances immediately to next approved facility. |
| `V-S27` | 27. Retry storm from flaky network | 50 rapid retries of the same `ACCEPT` command with identical `(actor_id, Idempotency-Key)`. | `200` (or `409 DUPLICATE_IN_FLIGHT` while in flight, then `200`) and `429` above rate limit | Exactly 1 `OFFER_ACCEPTED` event committed (`I4`). |
| `V-S28` | 28. Referral never closed by human | `ACCEPTED` + `HANDED_OVER` reached; both stages of `CLOSURE` deadline expire without human `CLOSE`. | `200` (poller `TIMEOUT` $\times 2$) | Stage 1 emits `CLOSURE_OVERDUE` and re-arms; Stage 2 transitions to `CLOSED` with `outcome='UNKNOWN_COUNTER_REFERRAL', proxy=true, actor=system`. |

### 7.2 Stateful Property-Based Testing (`tests/test_stateful_pbt.py`)
Implemented with `hypothesis.stateful.RuleBasedStateMachine`:
- **Bundles:** `referrals`, `offers`, `sessions`, `idempotency_keys`.
- **Rules:** `create_referral`, `ack_offer`, `confirm_resources`, `accept_offer`, `counter_offer`, `confirm_counter`, `decline_offer`, `fire_due_timers`, `arrival_rejected`, `dispatcher_assign`, `tr_update`, `cancel_referral`, `close_referral`, `replay_previous_command`, `stale_epoch_command`.
- **Invariants (`@invariant` run after every step):**
  1. Invokes `monitor.cycle(dsn)` and asserts `violations == []`.
  2. Asserts `referral.head_seq == count(event WHERE referral_id=r.id)`.
  3. Asserts `referral.open_offers == count(offer WHERE referral_id=r.id AND status IN ('OPEN','ACKED','COUNTERED','SOFT_OPEN')) <= 2`.
- **Execution Profile:** Minimum 200 stateful trajectories $\times$ 40 steps in CI (`--hypothesis-max-examples=200`), plus a 10-minute continuous chaos soak for the T0 gate.

---

## 8. Concurrency Barrier & Toxiproxy Chaos Matrix

### 8.1 200-Way Concurrent Accept Barrier (`tests/test_race200.py` — `T-C1`)
- **Setup:** Create a `PARALLEL2` referral with offers `OFFER[0]` (Facility 1) and `OFFER[1]` (Facility 2), both with confirmed unexpired resources and `version = V`.
- **Execution:** Synchronize $N = 200$ `httpx.AsyncClient` coroutines on an `asyncio.Barrier(200)` (100 targeting `OFFER[0]`, 100 targeting `OFFER[1]`, plus 20 duplicate retries sharing keys).
- **Mandatory Quantitative Assertions:**
  1. `sum(1 for r in responses if r.status_code == 200) == 1` (plus exact replays of the winning key if retried).
  2. `all(r.status_code in (200, 409, 412, 422, 429) for r in responses)` (zero `500 Internal Server Error`).
  3. `SELECT count(*) FROM offer WHERE referral_id = $1 AND status = 'ACCEPTED'` equals `1`.
  4. `SELECT max(seq) - count(*) FROM event WHERE referral_id = $1` equals `0` (gap-free sequence).
  5. `pg_stat_database.deadlocks` delta equals `0`.
  6. `monitor.cycle(dsn)` returns `[]` (zero invariant violations).

### 8.2 Toxiproxy Fault Injection Matrix (`tests/test_toxiproxy.py`)
Two Toxiproxy proxies sit in `docker-compose.yml`: `proxy_pg` (`API <-> PostgreSQL 16`) and `proxy_api` (`Clients <-> FastAPI`).

| Toxic # | Toxic Type & Target Proxy | Parameters | Workload During Fault | Pass Assertion |
|---|---|---|---|---|
| 1 | `latency` (upstream) on `proxy_pg` | `latency=350ms, jitter=100ms` | 20 concurrent `ACCEPT` + `TR_UPDATE` calls with retries | p95 latency increases as expected; zero duplicate events (`I4`); monitor green. |
| 2 | `latency` (downstream) on `proxy_api` | `latency=1500ms` (client times out at $1000\text{ ms}$ and retries) | Client issues `CREATE` and `ACCEPT` with `1.0s` timeout and retries same `Idempotency-Key` | Retry receives `409 DUPLICATE_IN_FLIGHT` or stored `200 OK`; exactly 1 effect committed. |
| 3 | `bandwidth` on `proxy_api` | `rate=2KB/s` + connection drop | Active SSE stream on receiving desk during 10 state transitions | Client reconnects with `Last-Event-ID` header and receives all missed events in `seq` order. |
| 4 | `slow_close` on `proxy_pg` | `delay=2000ms` | 50 rapid commands followed by expired-idempotency purge job | Zero leaked `IN_FLIGHT` rows after transaction completion; connection pool recovers cleanly. |
| 5 | `timeout` on `proxy_pg` | `timeout=500ms` | `apply_command(ACCEPT)` cut mid-flight; client retries same `Idempotency-Key` after proxy restored | Either original txn committed (retry replays `200`) or aborted (retry executes fresh `200`); 1 event in log. |
| 6 | `reset_peer` on `proxy_pg` | `timeout=100ms` (TCP RST during Step 8) | `apply_command(CREATE)` hit by TCP RST before `COMMIT` | Transaction rolls back completely (`IN_FLIGHT` row absent); client retry succeeds with `seq=1`. |
| 7 | `slicer` on `proxy_api` | `average_size=32, size_variation=16, delay=50us` | JSON command POSTs and Merkle inclusion proof fetches | HTTP/JSON frames reassemble without corruption; JCS SHA-256 hashes and Ed25519 signatures verify. |
| 8 | `limit_data` / Proxy Disabled (`enabled=false`) | Cut `proxy_api` for $10\text{ s}$, then re-enable | Outbox relay attempting SSE/FCM/Voice delivery + ambulance offline outbox | Outbox rows stay `PENDING`, reappear after visibility timeout ($\le 30\text{ s}$) or immediate retry, and deliver once (`I4`). |

---

## 9. Complete 47-Item Failure-Mode & Attack Test Traceability (`Architecture §18`)

Every row in the `Architecture §18` Failure-Mode & Attack Matrix is verified by its named test below:

| Matrix ID | Class | Scenario | Test ID | Verification Method | Bounded Residual Verified | Status |
|---|---|---|---|---|---|---|
| `C1` | Concurrency | 200 simultaneous `ACCEPT` | `T-C1` | `asyncio.Barrier(200)` on `PARALLEL2` referral | Relies on PostgreSQL row lock + `one_lease` index correctness | `CLOSED` |
| `C2` | Concurrency | `ACCEPT` vs `TIMEOUT` race | `T-C2` | Barrier synchronizing poller Phase 2 `TIMEOUT` and desk `ACCEPT` | Either lock-order outcome legal; both audited in `event` | `CLOSED` |
| `C3` | Concurrency | Late `ACCEPT` after successor `ACK` | `T-C3` | `V-S06b`: `SOFT_OPEN` offer accepts after next facility `ACK`s | Receiver sees `409 LATE_ACCEPT_REJECTED` on next sync | `CLOSED` |
| `C4` | Concurrency | `COUNTER` + other `ACCEPT` | `T-C4` | `T-F13`: F1 `CONFIRM_COUNTER(true)` races F2 `ACCEPT` | Decided deterministically under single referral lock | `CLOSED` |
| `C5` | Concurrency | Poller vs command deadlock | `T-F1` | 150 commands + 50 poller ticks; check `pg_stat_database.deadlocks` | PostgreSQL internal lock manager assumed correct | `CLOSED` |
| `C6` | Concurrency | Duplicate timer fire | `T-C6` | Two pollers invoke `apply_command(TIMEOUT)` for same `deadline.id` | Second call sees `status='DONE'` under lock and returns `200` no-op | `CLOSED` |
| `C7` | Concurrency | Stale writer (old version/epoch) | `T-I8` | Submit command with `expected_version = r.version - 1` | Returns `412` + logs to `rejected_command` | `CLOSED` |
| `C8` | Concurrency | Third offer attempted | `T-F13` | Force 3rd open offer via mutated transition or parallel race | Blocked by `open_offers CHECK (0..2)` and `SOFT_OPEN` expiry | `CLOSED` |
| `T1` | Timer | Poller crash | `T-T1` | `kill -9` poller container while `claimed_until` is set; start backup poller | Claim lapses in $\le 5\text{ s}$ + $1\text{ s}$ poll interval | `BOUNDED` |
| `T2` | Timer | Clock forward step | `T-F11` | Step mock clock forward $+10\text{ s}$ | Premature escalation only ($\le \Delta$); `SOFT_OPEN` preserves prior offer | `BOUNDED` |
| `T3` | Timer | Clock backward step | `T-F11` | Step mock clock backward $-10\text{ s}$; check `server_ts` and `ntp_offset_ms` | `GREATEST` keeps `server_ts` monotone (`I16`); deadlines late $\le \Delta$ ($\le 2\text{ s}$ before alarm) | `BOUNDED` |
| `T4` | Timer | Deadline storm after outage | `T-T4` | Insert 250 overdue deadlines and run poller ticks | Drains at 50 claims/tick in $\lceil n/50 \rceil = 5$ ticks | `BOUNDED` |
| `T5` | Timer | Failover mid-timer | `T-T5` | Inject `reset_peer` on `proxy_pg` during poller tick | Poller reconnects and re-claims durable `deadline` rows ($60\text{--}120\text{ s}$ Multi-AZ window `[V*]`) | `BOUNDED` |
| `T6` | Timer | Profile tampering | `T-F2` | Flip 1 bit in profile JSON or signature | Startup refuses boot (`I13`) | `CLOSED` |
| `N1` | Network | Offline stale `ACCEPT` | `T-F12` | Flush offline `ACCEPT` after `confirm_ttl` expires | Returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` (`I15`) | `CLOSED` |
| `N2` | Network | Lost response, retry | `T-F14` | Drop HTTP response via Toxiproxy; retry same `Idempotency-Key` | Returns stored `200 OK` within 48h; `event_id UNIQUE` beyond 48h | `CLOSED` |
| `N3` | Network | SSE drop | `T-N3` | Drop SSE TCP connection; reconnect with `Last-Event-ID` | Resumes without gap; stale view $\le 15\text{ s}$ heartbeat interval | `BOUNDED` |
| `N4` | Network | Ambulance dead zone | `T-N4` | Disable network on ambulance client for $60\text{ s}$, queue GPS, reconnect | UI shows `"last confirmed Ns ago"`; set-union merge on reconnect | `BOUNDED` |
| `N5` | Network | Exotel webhook duplicate | `T-N5` | POST identical `(source='EXOTEL', external_id)` webhook 10 times | `inbox` `UNIQUE(source, external_id)` dedupes; 1 command executed | `CLOSED` |
| `N6` | Network | Webhook slower than $2\text{ s}$ budget | `T-N6` | Inject $1.8\text{ s}$ DB delay during Exotel callback | Returns HTTP 200 `"please hold"` XML within $2\text{ s}$ (Exotel limit $5\text{ s}$ `[V]`); next callback reads committed state | `BOUNDED` |
| `N7` | Network | Venue internet down | `T-N7` | Block external WAN; switch to LAN mode (`REAL_DATA=0`) | LAN QR admits up to 20 desks; pure-JS `@noble` crypto verifies without WebCrypto | `BOUNDED` |
| `N8` | Network | Retry storm | `T-N8` | Send 300 req/s from one token | Rate limiter returns `429`; passing requests replay idempotently | `BOUNDED` |
| `I1` | Identity | Wrong person accepts | `T-I6` | Unrostered user or wrong facility calls `ACCEPT` | Rejected with `403`; shared-credential misuse inside valid roster is bounded | `CLOSED` |
| `I2` | Identity | PIN brute force | `T-F7` | Submit rapid wrong PINs on one session | Argon2id ($\approx 100\text{ ms}$), backoff $0\text{s}/5\text{s}/30\text{s}$, $120\text{ s}$ lock on 3rd strike | `BOUNDED` |
| `I3` | Identity | Lockout-DoS by rival | `T-F7` | Lock Session A; test valid PIN on Session B for same role | Session B succeeds (`pin_failed` scoped per `session_id`/`call_sid`) | `CLOSED` |
| `I4` | Identity | SIM swap | `T-I4b` | Trigger 3 lockouts across calls on one roster slot | Emits `PIN_LOCKED`, pages dispatcher, suspends slot | `BOUNDED` |
| `I5` | Identity | Voicemail counted as `ACK` | `T-F7` | Send Exotel webhook with `AnsweredBy='machine'` or no digit `1` | Zero `OFFER_ACKED` events; call marked `UNANSWERED` | `CLOSED` |
| `I6` | Identity | BOLA / mass-assignment | `T-I6b` | Facility A queries Facility B's grant; POST body includes `"hs_state": "ACCEPTED"` | Returns `403` (BOLA) and `422` (Pydantic `extra='forbid'`) | `CLOSED` |
| `P1` | Privacy | PHI in `event.detail` | `T-F9` | Fuzz `event.detail` with patient names, phone numbers, floats | Rejected by Pydantic + `rhp_detail_ok` DB `CHECK` (`I11`) | `BOUNDED` |
| `P2` | Privacy | PHI via SMS | `T-P2` | Inspect all outbound SMS payloads in `outbox` | Matches static DLT template `"RHP alert: new referral. Open {#var#}"` ($\le 30$ chars) | `CLOSED` |
| `P3` | Privacy | PHI via FCM | `T-P3` | Inspect all outbound FCM payloads in `outbox` | Empty data payload `{}` wake ping only; requires authenticated fetch (`I10`) | `CLOSED` |
| `P4` | Privacy | Stream after revoke | `T-F10` | Revoke grant while SSE connected; emit clinical update | `GRANT_REVOKED` frame sent; subsequent frames stripped; DOM wiped | `BOUNDED` |
| `P5` | Privacy | Crypto-shred vs WAL/backup | `T-P5` | Expire referral $\to$ run shredder $\to$ verify `clinical_payload` & `event_secret` deleted, `wrapped_dek=NULL, status='SHREDDED'`, and chain hash still verifies via `secret_hash` | Ciphertext deleted + DEK nulled + KEK epoch destroyable; chain verification intact | `BOUNDED` |
| `A1` | AI | Wrong draft field | `T-A1` | Run 20-slip seeded-error usability gate (30% fatal seeded errors) | Critical-error rubber-stamp rate $\le 5\%$, silent omission $\le 1\%$ | `BOUNDED` |
| `A2` | AI | Draft leaks before anchors | `T-A2` | Request AI draft before submitting `need_class` and `mgso4_status` | Server returns `423 ANCHOR_REQUIRED` | `CLOSED` |
| `A3` | AI | ASR error (Kannada) | `T-A3` | Disable `T3_EXTRAS` flag and run full referral lifecycle | Completes 100% via structured manual entry without AI | `BOUNDED` |
| `K1` | Clinical | `mgso4_status` unknown | `T-K1` | Create referral with `mgso4_status='UNKNOWN'` and dispatch ambulance | `CREATE` and `TR_UPDATE` succeed without delay; receiving desk renders red verification banner | `BOUNDED` |
| `K2` | Clinical | Accept-then-no-bed gaming | `T-K2` | Delay `HANDED_OVER` past `HANDOVER` deadline $H$ or issue `ARRIVAL_REJECTED` | `HANDOVER_OVERDUE` / `ARRIVAL_REJECTED` logged; APOT reported separately from `ACCEPT` | `BOUNDED` |
| `K3` | Clinical | Tertiary funnelling | `T-K3` | Configure facility load cap and `AT_CAPACITY` decline | Returns structured `AT_CAPACITY` and advances down approved catchment chain | `BOUNDED` |
| `K4` | Clinical | Ambulance past turn-off | `T-F5` | Reassign lease while ambulance `EN_ROUTE` past junction | Emits advisory with cached Matrix detour ETA; never auto-reroutes | `BOUNDED` |
| `S1` | Insider | Admin edits `event` row | `T-F8` | As superuser (bypassing trigger on scratch DB), alter `detail` in `event` row `seq=3` | Browser verifier prints `BROKEN referral=... seq=3 kind=HASH`; monitor flags `I5` | `BOUNDED` |
| `S2` | Insider | Split-view history | `T-S2` | Present divergent checkpoint root for same `checkpoint_id` to two witness clients | Witness cross-comparison flags `SPLIT_VIEW_DETECTED` | `BOUNDED` |
| `S3` | Insider | Signer key theft | `T-S3` | Execute key-rotation runbook drill (revoke `signer_key_id`, deploy new key under `rhp-sign` user) | Verifier accepts old checkpoints under old key and new checkpoints under rotated key | `OPEN` |
| `S4` | Insider | Dispatcher override abuse | `T-S4` | Issue `DISPATCHER_ASSIGN` with override reason | Event logged with `proxy=true`, mandatory reason enum, and highlighted on monitor | `BOUNDED` |
| `F1` | Infra | API container kill | `T-F1b` | `docker kill api` mid-load, restart container, retry client calls | In-flight txns abort cleanly; client retries succeed; zero lost/duplicate events | `BOUNDED` |
| `F2` | Infra | Primary DB loss | `T-F2b` | Simulate primary restart / standby promotion | Poller, relay, and API reconnect; durable deadlines fire | `BOUNDED` |
| `F3` | Infra | Outbox relay crash | `T-F3b` | Kill `relay` after claiming `outbox` rows before marking `SENT` | Rows become visible again after `visible_after` ($30\text{ s}$) and deliver | `BOUNDED` |
| `F4` | Infra | OEM kills foreground service | `T-F4b` | Stop Android location updates for $>30\text{ s}$ | Stale `heartbeat` marks GPS `"last confirmed Ns ago"`; manual update button works | `BOUNDED` |
| `L1` | Legal | Voice legality unsettled | `T-L1` | Inspect Exotel target whitelist and prompts | Only $\le 10$ whitelisted sandbox numbers called; zero patient names in audio (`REAL_DATA=0`) | `OPEN` |
| `L2` | Legal | Retention vs erasure | `T-L2` | Test configurable `clinical_payload.expires_at` parameter | Policy parameter adjusts retention TTL without code changes | `OPEN` |
| `L3` | Legal | BSA s.63 over-claim | `T-L3` | Generate BSA s.63 export bundle and run `ST-5` claims linter | Bundle outputs JCS events, SHA-256 hashes, and Part A/B uncertified templates; zero `"BSA certified"` claims | `CLOSED` |
| `L4` | Legal | Breach reporting clock | `T-L4` | Trigger simulated security alert and generate incident report packet | Generates 6h CERT-In and 72h DPBI templates with log timestamps | `BOUNDED` |
| `D1` | Demo | No Ed25519 in iOS WebCrypto | `T-D1` | Run browser verifier in WebKit / iOS Safari over plain HTTP (`crypto.subtle == undefined`) | Pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256` verify checkpoint and chain in $<200\text{ ms}$ | `BOUNDED` |
| `D2` | Demo | Exotel trial limit $\le 10$ | `T-D2` | Run pre-flight whitelist check | Confirms demo feature phone is whitelisted; judges use QR web desks | `BOUNDED` |
| `D3` | Demo | `BROKEN_BUILD` on real DB | `T-F20` | Test all 3 boot-abort guards in `T-F20` | Exits with code `78` on any violation | `CLOSED` |
| `D4` | Demo | Venue network fails | `T-D4` | Disconnect WAN during rehearsal; switch to LAN QR and MP4 clips | LAN QR works on local hotspot; MP4 fallback clips `A`–`D` play cleanly | `BOUNDED` |
| `D5` | Demo | Late code change | `T-D5` | Verify git tag and CI freeze lock at `H22` | Only config changes allowed after `H22` | `BOUNDED` |

---

## 10. End-to-End 30-Second Live Proof Loop Test (`T-F16`)

Executed by `scripts/rehearse_30s_loop.py` under `PROFILE=DEMO_FAST, REAL_DATA=0`:

| Window | Automated Action | Hard Assertion | Fallback Verified |
|---|---|---|---|
| $0\text{--}4\text{ s}$ | Mint rotating QR (`jti`, $20\text{ s}$ TTL); join two judge sessions `D1` (Facility 1) and `D2` (Facility 2). | Both SSE streams emit initial heartbeat; active desk count $\le 20$. | `clip_A.mp4` |
| $4\text{--}7\text{ s}$ | Clinician creates `PARALLEL2` referral (`need_class='OBSTETRIC_EMERGENCY'`, `mgso4_status='UNKNOWN'`); both desks confirm required resources. | `D1` and `D2` receive `OFFER_CREATED` via SSE in $<500\text{ ms}$ and display the red `mgso4_status=UNKNOWN` banner. | `clip_A.mp4` |
| $7\text{--}12\text{ s}$ | `D1` and `D2` fire `POST /v1/offers/{id}/accept` simultaneously at an `asyncio.Barrier(2)`. | Exactly one returns `200 OK` (`lease_epoch=1`), the other returns `409 LEASE_HELD` (`SUPERSEDED`); Monitor status is `GREEN (0 violations)`. | `clip_B.mp4` |
| $12\text{--}18\text{ s}$ | Switch active target to `BROKEN_BUILD=1` (`rhp_scratch_broken`); create referral; `D1` and `D2` press `Accept` together. | Big screen displays flashing red `BROKEN BUILD — SCRATCH DB` banner; both receive `200 OK`; Monitor turns `RED` with `("I2", referral_id)` in $\le 2.0\text{ s}$. | `clip_C.mp4` |
| $18\text{--}21\text{ s}$ | Switch back to `BROKEN_BUILD=0` (`rhp_main`); create fresh referral. | Red banner clears; Monitor returns `GREEN (0 violations)`. | `clip_C.mp4` |
| $21\text{--}27\text{ s}$ | In scratch DB, execute superuser `UPDATE event SET detail='{"channel":"VOICE"}' WHERE referral_id=$1 AND seq=2` (temporarily disabling trigger to simulate insider disk/superuser tamper) and invoke browser verifier. | Pure-JS browser verifier outputs exact string: `BROKEN referral=<id> seq=2 kind=HASH expected=<h1> got=<h2>`. | `clip_D.mp4` |
| $27\text{--}30\text{ s}$ | Query `/metrics` and render Guarantee Arena recap overlay. | Displays live-measured `I1`–`I16` counters and live-measured `p50`/`p95` event latency (zero hardcoded or pre-claimed numbers). | `clip_D.mp4` |

---

## 11. Pre-Event Verification Protocol (`Architecture §21`)

All 12 pre-event checks must be executed and logged in `docs/PRE_EVENT_VERIFICATION_LOG.md` before `H0`:

| # | Verification Item | Timebox | Exact Test Procedure | Pass Threshold | Pre-Decided Fallback if Blocked |
|---|---|---|---|---|---|
| 1 | Hackathon rules on pre-built work & AI coding | $1.0\text{ h}$ | Inspect official Colossus 3.0 rulebook and confirm in writing with organisers. | Written confirmation recorded. | Keep only `Phase P` spec documents pre-event; write all application code (`Phase E`) inside the 24h window. |
| 2 | Exotel concurrency, DTMF `%23`, AMD | $1.5\text{ h}$ | Place 5 concurrent outbound calls to whitelisted team phones + 1 call to voicemail; enter PIN + `#`. | Human press-1 + PIN `#` (`%23`) parsed; voicemail produces 0 `OFFER_ACKED` rows. | Sequential outbound voice calls ($S=1, \delta=0$); QR web desks for multi-party demo. |
| 3 | Exotel webhook latency $\le 5\text{ s}$ under load | $30\text{ min}$ | Replay 20 signed Exotel webhook callbacks concurrently against API. | 100% return HTTP 200 within $\le 2.0\text{ s}$ (`p95 <= 2.0s`). | Handler returns immediate `"please hold"` XML at $1.5\text{ s}$ and reads result on next callback. |
| 4 | LAN HTTP + iPhone QR camera scan | $30\text{ min}$ | Connect laptop and iPhone to phone hotspot; scan QR encoding `http://192.168.x.x:8000/join?jti=...`. | Safari opens desk UI and connects SSE stream. | Use Cloudflare tunnel domain or pre-installed mkcert local root CA. |
| 5 | Pure-JS Ed25519 on iPhone Safari | $30\text{ min}$ | Load `/verify` page on iPhone Safari over plain LAN HTTP and verify a 40-leaf checkpoint + 10-event chain. | Verification completes in $<200\text{ ms}$ with `crypto.subtle` undefined. | Server-side verifier endpoint (explicitly labelled `"server-verified"` in UI). |
| 6 | Quint / Apalache at $F=3, E=4$ | $1.0\text{ h}$ | Run `quint run` (20,000 samples) and `quint verify` on `spec/rhp1.qnt`. | Completes in $<10\text{ min}$ with 0 violations and all 4 vacuity checks failing as required. | Python explicit-state BFS explorer (`scripts/explore_transitions.py`) over `transitions.yaml`. |
| 7 | Mapbox Matrix API limits & key | $30\text{ min}$ | Issue 1 `mapbox/driving` Matrix call (25 coords) and 1 `driving-traffic` call (10 coords). | Returns valid duration matrix; 120s server cache hit verified on second call. | Cached synthetic ETA table for the curated Karnataka facility directory (`ETA stale` badge shown). |
| 8 | Android foreground location soak | $2.0\text{ h}$ | Run Kotlin app (`FOREGROUND_SERVICE_TYPE_LOCATION`) with screen off for $2\text{ h}$. | Continuous GPS telemetry with gap $<60\text{ s}$; battery drain measured. | `T1` PWA ambulance desk with foreground `watchPosition` + manual `"Update Location"` button. |
| 9 | DPDP commencement date conflict | $1.0\text{ h}$ | Check official Gazette notification text (13 Nov 2025 vs 14 Nov 2025 `[CONFLICT]`). | Primary citation documented. | Cite both dates conservatively (`13/14 Nov 2025`, core obligations `13/14 May 2027`). |
| 10 | DPDP `s.7(f)` vs `s.7(d)` citation | $30\text{ min}$ | Verify section lettering in the enacted Digital Personal Data Protection Act, 2023. | Exact clause verified. | Cite `"DPDP Act 2023 s.7 emergency processing provision"`. |
| 11 | Das et al. (2023) denominator | $30\text{ min}$ | Check Table 1/2 of Das et al. (2023) (`25,253` vs `28,020` `[CONFLICT]`). | Denominator reconciled. | Quote verified percentages only (`47%`, `37%`, `60%`) without unverified raw denominators. |
| 12 | Chrony slew-only & clock-step alarm | $30\text{ min}$ | Step test container clock by $+3\text{ s}$ and $-3\text{ s}$. | `heartbeat.ntp_offset_ms` $>2000\text{ ms}$ triggers monitor alarm within $5\text{ s}$; `I16` holds. | Demo clock-step injection endpoint on scratch environment. |