---
trigger: always_on
scope: "**/*"
authority: ReferralHandshake_FINAL_LOCKED_Architecture.md
sections: "§1, §12, §18, §23, §24"
workflow: ReferralHandshake_3Gem_Antigravity_Workflow.md
---

# `.agents/rules/testing-requirements.md` — Verification Gates, Mutation Suite & Chaos Matrix

No step in **ReferralHandshake (Protocol RHP-1)** counts as complete until its tests run and raw evidence is pasted into the `BUILD REPORT`.

---

## 1. Evidence-Based Verification Rule (3-Gem + Antigravity Protocol)

1. **Raw Output Mandate:** Claiming "tests pass" without pasting the exact command executed and its raw terminal output is an **automatic `FAIL` / `REJECT`** by Gem 2 (Auditor).
2. **Anti-Tamper Rule:** Coding agents **MUST NEVER** edit `/spec/*`, `spec/transitions.yaml`, `spec/rhp1.qnt`, `spec/vectors.json`, `db/schema.sql`, or `monitor/` to make a failing test pass.
3. **Git Tagging:** Every completed loop ends with a commit tagged `step-<ID>-loop<n>`.
4. **Required `BUILD REPORT` Order:**
   - `STEP / LOOP / commit hash`
   - `FILES CHANGED (git diff --stat)`
   - `CODE` (full text of every `HIGH` risk file, or `git diff` if $> 300$ lines)
   - `COMMANDS RUN + RAW OUTPUT` (verbatim terminal output)
   - `TESTS` (`name | pass/fail | measured numbers`)
   - `NOT DONE / SKIPPED`, `DEVIATIONS FROM SPEC`, `ASSUMPTIONS`, `OPEN QUESTIONS`, `SELF-RATED RISK`
   - `=== AUDIT-REQUEST FOR GEM 2 ===` block.

---

## 2. Formal Control-Plane Verification (`spec/rhp1.qnt`, §12)

Person A runs bounded model checking on the Quint specification ($F=3$ facilities, $\text{MAXE}=4$ epochs):
1. **Safety Invariant Check (`I2`, `I12`, `I1m`, `IDisp`, `I13`):**
   ```bash
   quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000
   quint verify spec/rhp1.qnt --invariant safety
   ```
2. **Mandatory Vacuity Checks (MUST FAIL to prove state reachability):**
   - `quint run spec/rhp1.qnt --invariant 'not (hs == "ACCEPTED")'` $\rightarrow$ **MUST FAIL** (proves `ACCEPTED` is reachable)
   - `quint run spec/rhp1.qnt --invariant 'not (hs == "DISPATCH")'` $\rightarrow$ **MUST FAIL** (proves `ESCALATED_TO_DISPATCHER` is reachable)
   - `quint run spec/rhp1.qnt --invariant 'not (hs == "CLOSED")'` $\rightarrow$ **MUST FAIL** (proves `CLOSED` is reachable)
   - `quint run spec/rhp1.qnt --invariant 'not (FACS.exists(f => off.get(f) == "SOFT"))'` $\rightarrow$ **MUST FAIL** (proves `SOFT_OPEN` is reachable)
3. **Transport Independence Run:**
   - `quint run spec/rhp1.qnt --main rhp1 --step transportNeverGated` $\rightarrow$ **MUST PASS**.

---

## 3. F1–F20 Closure Tests & Self-Audit Suite (`ST-1`–`ST-5`)

| Test ID | Closure / Invariant | Exact Test Mechanism & Pass Assertion |
|---|---|---|
| `T-F1` (`ST-1`) | `F1`, `I14` Global Lock Order | `lock_order_200way`: Run 200 concurrent commands + active 2-phase poller + relay; assert `pg_stat_database.deadlocks` delta $== 0$ and `rhp_require_lock` blocks any unlocked write with `I14_LOCK_NOT_HELD` |
| `T-F2` | `F2` Notice Ladder & Profile Guard | `profile_guard`: Attempt boot with `DEMO_FAST` and `REAL_DATA=1` $\rightarrow$ assert process refuses boot; tamper 1 byte of profile signature $\rightarrow$ assert boot refusal |
| `T-F3` (`ST-2`) | `F3`, `I13` $T_{\max}$ Validator | `tmax_validator`: Recompute $F \cdot (A + D + \epsilon) \le B$ and voice stagger $A/4 + (S-1)\delta + V \le 3A/4$ across all 4 profiles; assert startup validator rejects any profile with $T_{\max} > B$ |
| `T-F4` (`ST-3`) | `F4` 24-Table DDL & FK Scan | `ddl_load_fk_scan`: Load `db/schema.sql` into fresh PostgreSQL 16; query `information_schema.tables` (count $== 24$), verify `one_lease`, `one_active_grant`, and all triggers exist |
| `T-F5` | `F5` Six Arrival Cases | `arrival_cases`: Execute arrival cases (a)–(f); verify geofence emits `ARRIVAL_SUGGESTED` only and never sets `tr_state='ARRIVED'` without human confirmation |
| `T-F6` | `F6` Reachability & Closure | `reachability_bfs`: Verify every state in `transitions.yaml` reaches `CLOSED` or `CANCELLED`; verify 2x `CLOSURE` expiry closes with `UNKNOWN_COUNTER_REFERRAL` and `proxy=true` |
| `T-F7` | `F7` Lockout Scope & Press-1 Gate | `pin_lockout_scope`: Fail PIN 3x on session A $\rightarrow$ session A gets `429 PIN_LOCKED`, session B for same facility/role still succeeds with valid PIN; voicemail/AMD call without pressing `1` produces $0$ ACKs |
| `T-F8` | `F8` Tamper vs Cold-Key Restore | `tamper_vs_restore`: Truncate `event` row without `RESTORE` checkpoint $\rightarrow$ verifier outputs `TRUNCATED`; insert cold-key signed `RESTORE` checkpoint + `RESTORE` event $\rightarrow$ verifier accepts |
| `T-F9` | `F9`, `I11` `event.detail` Fuzz | `detail_check_fuzz`: Fuzz `event.detail` with 500 non-allowlisted keys, floats, free-text names, and >40-char strings $\rightarrow$ $100\%$ rejected by Pydantic and `rhp_detail_ok` DB `CHECK` |
| `T-F10` | `F10`, `I10` Stream Grant Revocation | `sse_revoke`: Open SSE stream for offered facility, then `DECLINE` or `SUPERSEDE` $\rightarrow$ assert `GRANT_REVOKED` control frame arrives on next relay cycle and clinical fields are stripped |
| `T-F11` | `F11`, `I16` Clock Step Resilience | `clock_step`: Inject backward clock offset $\rightarrow$ assert `GREATEST(clock_timestamp(), head_ts)` keeps `server_ts` non-decreasing (`I16`); offset $> 2000\text{ ms}$ triggers `heartbeat.ntp_offset_ms` alarm |
| `T-F12` | `F12`, `I15` Stale Offline Accept | `offline_stale`: Delay offline `ACCEPT` until after `offer_resource_confirmation.expires_at` $\rightarrow$ assert `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`; delay until after successor `ACK` $\rightarrow$ assert `409 LATE_ACCEPT_REJECTED` |
| `T-F13` | `F13`, `I12` Open-Offer Cap $\le 2$ | `open_cap`: Walk sequential soft-open overlap ($k-1$ `SOFT_OPEN` $\rightarrow$ `TIMED_OUT` when $k+1$ opens) and `PARALLEL2` + `COUNTER`; assert `open_offers` never exceeds $2$ |
| `T-F14` (`ST-4`) | `F14`, `I4` Idempotency Matrix | `idem_matrix`: Execute all 8 idempotency edge cases (§5 table); verify exact HTTP status codes and zero duplicate `event` rows |
| `T-F15` (`ST-5`) | `F15`, §19 Claims & Residual Lint | `residual_lint`: Scan docs/UI/comments for forbidden phrases and bare `"none"` residuals; assert $0$ violations |
| `T-F16` | `F16` 30-Second Proof Loop | `loop_rehearsal`: Automated timing harness runs the `DEMO_FAST` proof loop inside $30\text{ s}$ |
| `T-F17` | `F17` Six Mutation Tests | `mutation_suite`: Run `M1`–`M6` (Section 4 below); assert $6/6$ trip their designated independent checker |
| `T-F18` | `F18` Cost Table Arithmetic | `cost_recompute`: Verify 6-month AWS ap-south-1 cost table sums ($140 \times 6 = 840$, $190 \times 6 = 1140$, $236.5 \times 6 = 1419$) |
| `T-F19` | `F19` v7 State Mapping | `v7_map`: Verify all 12 v7 conceptual states map bijectively to `(hs_state, offer.status, tr_state, event.type)` |
| `T-F20` | `F20` Broken Build Isolation | `broken_isolation`: Attempt `BROKEN_BUILD=1` with `REAL_DATA=1` or primary DSN $\rightarrow$ assert immediate exit `78` |

---

## 4. Six Mandatory Mutation Tests (`M1`–`M6`, `F17`)

To prove that the formal checker, conformance suite, and Person B's independent runtime monitor actually catch bugs, CI **MUST** run each mutation against a temporary mutated branch/flag and assert that the named detector fails/trips:

| Mutation ID | Fault Injected | Mutated Artifact | Detector That MUST Trip | Expected Violation Signal |
|---|---|---|---|---|
| **`M1`** | Disable `expected_epoch` fencing in Step 5 of `apply_command()` | Server (`api/`) | Independent Monitor + Vector `V-STALE-EPOCH` | `I8` (applied event with `epoch < referral.lease_epoch`) |
| **`M2`** | Remove `FOR UPDATE` on `referral` and drop `one_lease` index (`BROKEN_BUILD=1` on scratch DB) | Server + Scratch DB | `T-C1 race200` + Independent Monitor | `I2` (two `ACCEPTED` offers / two `LEASE_GRANTED` events; monitor turns red $\le 2\text{ s}$) |
| **`M3`** | Make poller hold `deadline` lock across `apply_command()` | Poller (`api/poller.py`) | `T-F1 lock_order_200way` | `I14` (deadlock counter delta $> 0$ / lock-order failure) |
| **`M4`** | Remove `nOpen(m1) > 0` / open-offer cap guard so a 3rd offer opens | Quint (`spec/rhp1.qnt`) | `quint run spec/rhp1.qnt --invariant safety` | `I12` counterexample trace (`nOpen(off) == 3`) |
| **`M5`** | Write `prev_hash` as `32 * 0x00` on `seq > 1` | Server (`api/`) | Pure-JS Browser Verifier + Independent Monitor | `I5` (`BROKEN referral=<id> seq=<n> kind=PREV`) |
| **`M6`** | Skip `expires_at > ts` check on `offer_resource_confirmation` during `ACCEPT` | Server (`api/`) | Vector `V-STALE-CONFIRM` + Independent Monitor | `I15` (lease granted from expired resource confirmation) |
| **`M-TR`** | Gate `TR_UPDATE` / `trStep` on `hs_state != 'DISPATCH'` | `transitions.yaml` & `rhp1.qnt` | Monitor `I3` & Quint `transportNeverGated` | `I3` violation (transport blocked by handshake state) |

---

## 5. 200-Way Concurrency Barrier & Toxiproxy Chaos Matrix (§12)

### 5.1 200-Way Concurrent Accept Barrier (`T-C1 race200`)
Using `asyncio.Barrier(200)` against a `PARALLEL2` referral (`OFFER[0]` and `OFFER[1]` both `OPEN`):
- Fire $200$ simultaneous `POST /v1/offers/{offer_id}/accept` requests with distinct `Idempotency-Key: race-{RUN}-{i}`.
- **Required Assertions:**
  1. `sum(r.status_code == 200 for r in rs) == 1` (exactly **one** winner).
  2. `all(r.status_code in (200, 409, 412, 422, 429) for r in rs)` (zero `500` errors).
  3. `SELECT count(*) FROM offer WHERE referral_id = $1 AND status = 'ACCEPTED'` $== 1$.
  4. `SELECT max(seq) - count(*) FROM event WHERE referral_id = $1` $== 0$ (gap-free `seq`).
  5. `deadlocks_delta() == 0` and Independent Monitor reports `0` invariant violations.

### 5.2 Eight-Toxic Chaos Matrix (`Toxiproxy` between API $\leftrightarrow$ DB and Phone $\leftrightarrow$ API)
| # | Toxic Injected | Required System Behavior & Assertion |
|---|---|---|
| 1 | `latency` (upstream) | p95 latency increases; zero duplicate events (`I4` holds) |
| 2 | `latency` (downstream) | Client retries replay stored response from `idempotency`; exactly one state effect |
| 3 | `bandwidth` | SSE stream resumes cleanly via `Last-Event-ID` without missing frames |
| 4 | `slow_close` | No leaked `IN_FLIGHT` idempotency locks; clean expiry after $48\text{ h}$ TTL |
| 5 | `timeout` | Client retry with same `Idempotency-Key` receives stored or fresh result; single event in log |
| 6 | `reset_peer` | Uncommitted transaction aborts cleanly; `idempotency` row rolls back; client retry succeeds |
| 7 | `slicer` | Chunked JSON request/SSE frames reassemble; JCS SHA-256 chain hash verified |
| 8 | `limit_data` / proxy `enabled=false` | Outbox relay redelivers after visibility timeout ($\le 30\text{ s}$); monitor remains green |

---

## 6. Tier Acceptance Gates (`G0`–`G3`, §24)

- **Gate `G0` (`T0` Pass — Hour 14):** `race200` passes ($1/200$ `200 OK`, 1 `ACCEPTED` offer, gap-free `seq`, deadlock delta $0$); `M1`–`M6` trip their checkers; Independent Monitor shows $0$ violations over a 10-minute randomized Hypothesis + chaos run; `quint run safety` passes ($\ge 20,000$ samples) and vacuity checks fail as required; browser verifier pinpoints an edited `seq` on a tampered row; `BROKEN_BUILD=1` turns monitor red in $\le 2\text{ s}$ and green after switch-back; `DEMO_FAST` silence-to-dispatcher measured at $\le 25\text{ s}$.
- **Gate `G1` (`T1` Pass — Hour 17):** Dispatcher proxy entry and direct clinician/desk API entry produce identical state and event sequences across $20$ paired runs; dispatcher console assigns after `ESCALATED_TO_DISPATCHER`; time-scrubber replay reproduces final state from the event log.
- **Gate `G2` (`T2` Pass — Hour 20):** $20/20$ Exotel voice ACKs recorded only after DB commit; voicemail call yields $0$ ACKs across $5$ trials; webhook p95 $\le 2\text{ s}$; paper-code validator rejects $100\%$ of single-symbol errors across $1,000$ mutated Crockford Base32+mod37 codes.
- **Gate `G3` (`T3` / Rehearsal — Hour 22 Code Freeze):** 3x full rehearsal of the 30-second live proof loop + MP4 fallback clips recorded. If `T3_EXTRAS` is enabled: Android keeps GPS $\ge 2\text{ h}$ screen-off; AI draft returns `423` before anchors; 20-slip seeded-error usability gate achieves rubber-stamp $\le 5\%$ and silent omission $\le 1\%$; FHIR R4 bundle passes validator.