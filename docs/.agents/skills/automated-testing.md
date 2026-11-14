---
name: automated-testing
description: Execute ReferralHandshake (RHP-1) formal verification (Quint rhp1.qnt), independent Python runtime monitor (Person B), 6 mutation tests (M1-M6), 200-way async barrier concurrency stress tests, Toxiproxy fault injection matrix, and Tier Gates G0-G3.
owner_lane: Lane A (Quint Spec, Conformance & Barrier Tests) & Lane B (Independent Runtime Monitor)
tier_scope: T0, T1, T2, T3
spec_anchors:
  - ReferralHandshake_FINAL_LOCKED_Architecture.md (§1, §3, §4, §12, §18, §23, §24)
  - ReferralHandshake_v8_LOCKED_Solution.md (§4.7, §4.8, §7, §13)
  - ReferralHandshake_3Gem_Antigravity_Workflow.md (§1, §3, §6)
invariants_enforced:
  - I1
  - I2
  - I3
  - I4
  - I5
  - I6
  - I7
  - I8
  - I9
  - I10
  - I11
  - I12
  - I13
  - I14
  - I15
  - I16
codeowners_restricted:
  - spec/rhp1.qnt
  - spec/transitions.yaml
  - monitor/
---

# RHP-1 Automated Testing, Chaos & Formal Proof Skill (`automated-testing`)

## 1. Mission & Common-Mode Independence (F17)
In **ReferralHandshake (Protocol RHP-1)**, testing is not an afterthought—it is the third pillar of the USP (**The Guarantee Arena**).
1. **Evidence-Only Rule:** Never claim a test passes without pasting the exact command executed and its raw stdout/stderr output into the `BUILD REPORT`.
2. **Common-Mode Independence (F17):**
   * **Lane A (Person A)** authors the backend (`api/`), `spec/transitions.yaml`, and the Quint specification (`spec/rhp1.qnt`).
   * **Lane B (Person B)** authors the independent Python runtime monitor (`monitor/monitor.py`) **exclusively from the prose of Architecture §3 and §12**, in a separate workspace that never imports or reads code from `api/`.
   * The monitor connects to PostgreSQL using the read-only `rhp_monitor` role under `REPEATABLE READ READ ONLY` isolation with a server-side cursor (`snap`) and performs a differential check between its own event-log fold and the `referral` table.
3. **Reward-Hacking Prohibition:** AI agents are strictly forbidden from modifying `spec/rhp1.qnt`, `spec/transitions.yaml`, `db/schema.sql`, conformance vectors, or `monitor/monitor.py` to make a failing test pass.

---

## 2. Formal Verification with Quint (`spec/rhp1.qnt` — §12)

Run bounded model checking and simulation on `spec/rhp1.qnt` ($F=3$ facilities, $\text{MAXE}=4$ epochs):

```bash
# 1. Randomised simulation (20,000 samples, depth 25)
quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000

# 2. Bounded symbolic model checking via Apalache
quint verify spec/rhp1.qnt --invariant safety --max-steps 20

# 3. Mandatory Vacuity Checks (MUST FAIL with a counterexample trace proving reachability)
quint run spec/rhp1.qnt --invariant 'not (hs == "ACCEPTED")'
quint run spec/rhp1.qnt --invariant 'not (hs == "DISPATCH")'
quint run spec/rhp1.qnt --invariant 'not (hs == "CLOSED")'
quint run spec/rhp1.qnt --invariant 'not (FACS.exists(f => off.get(f) == "SOFT"))'
```
* **Fallback if Apalache exceeds 10 minutes:** Run the deterministic Python explicit-state BFS explorer over `spec/transitions.yaml` (`scripts/explore_states.py`) and verify reachability of all states in the §4 Reachability & Exit table (`T-F6 reachability_bfs`).

---

## 3. Mandatory Mutation Suite (`T-F17 mutation_suite` — §12)

To prove that the conformance suite, database constraints, and independent runtime monitor actually catch bugs, every gate run must execute all **6 core mutations (`M1`–`M6`) plus the Track-Independence mutation (`M7`)** in isolated test runs and verify that the target detector trips:

| ID | Mutation Applied | Target Artifact | Detector That MUST Trip | Expected Violation Signal |
|---|---|---|---|---|
| **M1** | Bypass `expected_epoch` fencing check in Step 5 of `apply_command()` | `api/` (temp branch/flag) | Monitor + Conformance Vector `V-STALE-EPOCH` | `I8` (applied event with stale epoch) |
| **M2** | Remove `FOR UPDATE` on `referral` and run against `rhp_scratch_broken` (no `one_lease` index) | `api/` + Scratch DB (`BROKEN_BUILD=1`) | `T-C1 race200` + Independent Monitor | `I2` (`DOUBLE_LEASE_VIOLATION`, $\ge 2$ `ACCEPTED` offers within $\le 2\text{ s}$) |
| **M3** | Make poller hold `SELECT ... FOR UPDATE` on `deadline` across `apply_command()` while concurrent `ACCEPT` locks `referral -> deadline` | `api/poller.py` | `T-F1 lock_order_200way` | `I14` (`pg_stat_database.deadlocks` delta $> 0$ or `I14_LOCK_NOT_HELD`) |
| **M4** | Remove `nOpen(m1) > 0` / cap guard in `decline`/`timeout` so a 3rd offer opens concurrently | `spec/rhp1.qnt` (temp copy) | `quint run --invariant safety` | `I12` counterexample trace (`nOpen(off) == 3`) |
| **M5** | Write `prev_hash = b"\x00" * 32` on `seq >= 2` in `append_event()` | `api/` (temp flag) | Browser Verifier + DB Trigger + Monitor | `I5` (`CHAIN_BREAK` / `BROKEN referral=... seq=... kind=PREV`) |
| **M6** | Skip `expires_at <= server_ts` check on `offer_resource_confirmation` during `ACCEPT` | `api/` (temp flag) | Vector `V-STALE-CONFIRM` + Monitor | `I15` (lease granted from expired resource confirmation) |
| **M7** | Add guard `hs_state == 'ACCEPTED'` to `TR_UPDATE` in `transitions.yaml` (and `hs != "DISPATCH"` in Quint `trStep`) | `transitions.yaml` / `rhp1.qnt` | Monitor `I3` + Quint `transportNeverGated` | `I3` (transport blocked by handshake state) |

---

## 4. Concurrency, Chaos & Self-Audit Test Catalogue

### 4.1 200-Way Barrier Race (`T-C1 race200` & `T-F1 lock_order_200way`)
Synchronize $N = 200$ async HTTP clients on an `asyncio.Barrier(200)` firing `POST /v1/offers/{offer_id}/accept` across both open offers of a `PARALLEL2` referral while the deadline poller ticks at 50ms intervals.
* **Pass Criteria:**
  1. `sum(r.status_code == 200 for r in responses) == 1`
  2. `all(r.status_code in (200, 409, 412, 422, 429) for r in responses)` (zero `500` errors)
  3. `SELECT count(*) FROM offer WHERE referral_id = $1 AND status = 'ACCEPTED'` equals `1`
  4. `SELECT max(seq) - count(*) FROM event WHERE referral_id = $1` equals `0` (gap-free sequence, I4)
  5. `pg_stat_database.deadlocks` delta equals `0` (F1 / I14)
  6. Independent monitor `cycle(dsn)` returns `[]` (zero violations).

### 4.2 Toxiproxy 8-Toxic Fault Injection Matrix (§12)
Place Toxiproxy between `api <-> pg` and `client <-> api`. Execute a full referral lifecycle (`CREATE -> ACK -> RESOURCE_CONFIRM -> ACCEPT -> TR_UPDATE -> CLOSE`) under each of the 8 toxics:
1. `latency` (upstream 500ms $\pm$ 200ms jitter) $\rightarrow$ p95 latency grows, zero duplicate events.
2. `latency` (downstream 800ms) $\rightarrow$ client retries replay stored response, exactly one effect.
3. `bandwidth` (limit to 10 KB/s) $\rightarrow$ SSE resumes cleanly via `Last-Event-ID`.
4. `slow_close` (delay socket close by 2s) $\rightarrow$ no leaked `IN_FLIGHT` idempotency rows.
5. `timeout` (drop all data after 1s) $\rightarrow$ client retry receives stored or fresh result with identical `event_id`.
6. `reset_peer` (TCP RST mid-transaction) $\rightarrow$ uncommitted transaction aborts cleanly, idempotency row absent, retry succeeds.
7. `slicer` (slice packets into 16-byte chunks) $\rightarrow$ JSON frames reassemble, SHA-256 chain intact.
8. `limit_data` / proxy `enabled=false` (hard partition for 10s) $\rightarrow$ outbox relay redelivers within visibility timeout, monitor stays green.

### 4.3 Self-Audit CI Scripts (`ST-1` to `ST-5` — §23)
* **`ST-1` (Lock Order Static + Runtime Check):** Verify all SQL queries acquiring locks follow `referral -> offer -> deadline -> outbox` and `rhp_require_lock` is attached to all 6 contract tables.
* **`ST-2` ($T_{\max}$ & Voice Stagger Arithmetic):** Verify all 4 profiles in `spec/profiles.json`:
  * `PILOT_OB_CRITICAL`: $3 \cdot (60 + 180 + 3) = 729\text{ s} \le 900\text{ s}$; voice stagger $15000 + 2 \cdot 5000 + 20000 = 45000 \le 45000\text{ ms}$.
  * `PILOT_STANDARD`: $3 \cdot (120 + 300 + 3) = 1269\text{ s} \le 1500\text{ s}$; voice stagger $30000 + 2 \cdot 10000 + 20000 = 70000 \le 90000\text{ ms}$.
  * `DEMO_FAST`: $3 \cdot (3 + 4 + 1) = 24\text{ s} \le 25\text{ s}$.
  * `DEMO_VOICE`: $2 \cdot (45 + 20 + 1) = 132\text{ s} \le 150\text{ s}$; voice stagger $11250 + 0 + 20000 = 31250 \le 33750\text{ ms}$.
* **`ST-3` (DDL 24-Table & FK Constraint Scan):** Load `db/schema.sql` into PostgreSQL 16 and inspect `pg_constraint`.
* **`ST-4` (Idempotency 8-Case Matrix):** Run `T-F14 idem_matrix`.
* **`ST-5` (Forbidden Claims & Bare "None" Residual Linter):** Scan all repository `.md`, `.py`, `.ts`, `.tsx` files (excluding §19's forbidden-claims column) for forbidden strings (`"mathematically proven system"`, `"bullet-proof"`, `"airtight"`, `"zero loopholes"`, `"immutable log"`, `"ABDM compliant"`, `"BSA certified"`, `"lives saved"`, `"eliminates ping-pong"`) and scan failure tables for bare `"none"` residuals (`T-F15`).

---

## 5. Tier Acceptance Gates (`G0`–`G3` / §24 Definition of Done)

No tier counts as complete until its Gate Prompt outputs raw measured numbers passing every criterion below:

| Gate | Tier | Mandatory Measured Pass Criteria |
|---|---|---|
| **G0** | **T0** | 1. `race200` passes (1 of 200 returns `200`, 1 `ACCEPTED` offer in DB, `seq` gap-free, deadlock delta `0`).<br>2. Mutations `M1`–`M6` each trip their named checker.<br>3. Independent Python monitor reports `0` violations over a 10-minute Hypothesis stateful + Toxiproxy chaos run.<br>4. `quint run safety` passes ($\ge 20,000$ samples) and all 4 vacuity checks fail with counterexamples.<br>5. Browser pure-JS verifier names the exact `seq` and `kind=HASH\|PREV` on a superuser-tampered `event` row.<br>6. `BROKEN_BUILD=1` on `rhp_scratch_broken` turns the monitor red (`I2`) within $\le 2\text{ s}$ and green after switch-back.<br>7. `DEMO_FAST` silence-to-dispatcher escalation completes in $\le 25\text{ s}$ (`T_max = 24 s`). |
| **G1** | **T1** | 1. Dispatcher proxy entry and direct clinician/EMT API entry produce identical state and event sequences across 20 paired runs.<br>2. Dispatcher console successfully assigns a facility after `ESCALATED_TO_DISPATCHER`.<br>3. Replay scrubber reconstructs the exact state at every historical `seq` from the event log. |
| **G2** | **T2** | 1. 20/20 Exotel voice ACKs are committed only *after* the press-1 gate (`apply_command` commits before spoken confirmation).<br>2. Voicemail/AMD machine calls yield `0` ACKs across 5 trials.<br>3. Voice webhook p95 latency $\le 2.0\text{ s}$.<br>4. Paper-code Crockford Base32 + mod-37 validator rejects 100% of single-symbol errors and adjacent transpositions across 1,000 mutated codes. |
| **G3** | **T3** | 1. Android foreground location service logs continuous GPS for $\ge 2\text{ h}$ with screen off.<br>2. AI draft endpoint returns `423 ANCHOR_REQUIRED` until `need_class` and `mgso4_status` are committed.<br>3. 20-slip seeded-error usability gate achieves critical-error rubber-stamp $\le 5\%$ and silent omission $\le 1\%$.<br>4. FHIR R4 export bundle (`ServiceRequest`, `Task`, `Encounter`, `Communication`) passes schema validation. |

---

## 6. Explicit DO / DO NOT Guardrails

### DO
* **DO** write an executable regression test for every Red-Team attack (`A-n`) produced by Gem 2 (Milestone Validator) before marking any fix loop complete.
* **DO** run `monitor/monitor.py` under user ID `1001` connected strictly as `rhp_monitor`.
* **DO** test all 28 real-world scenarios from Solution v8 §4.8 as deterministic conformance vectors.

### DO NOT
* **DO NOT** mock the PostgreSQL database in concurrency, locking, trigger, or idempotency tests; always run against a real PostgreSQL 16 instance.
* **DO NOT** summarize test output as `"All tests passed"`—paste the verbatim terminal output and measured timings.
* **DO NOT** weaken any assertion in `monitor/monitor.py` or `spec/rhp1.qnt` to silence a failure.