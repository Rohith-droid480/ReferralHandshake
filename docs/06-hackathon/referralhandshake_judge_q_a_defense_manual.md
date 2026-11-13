# ReferralHandshake (Protocol RHP-1) — Judge Q&A Preparation & Technical Defense Manual

**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0
**Authority Hierarchy:** `Problem_Statement_v7.md` > `[V]` Research > `v8_LOCKED_Solution.md` > `FINAL_LOCKED_Architecture.md`
**Core Mandate:** Every answer must cite the exact architectural mechanism (`F1–F20`, `I1–I16`, `D1–D20`, SQL DDL, or timing formula), preserve evidence status tags (`[V]`, `[V*]`, `[CONFLICT]`, `[GAP]`, `[verify]`), and strictly obey the Claims Register (`§19`).

---

## 0. Rapid-Fire Response Rules for Team MAHA YODHAS

1. **Lead with the Direct Answer ("Yes", "No", or the exact bound) in the first sentence.** Judges penalize evasive framing.
2. **Name the Concrete Mechanism in the second sentence:** Point to the exact database constraint (`one_lease`, `rhp_require_lock`), pipeline step (`apply_command` Step 1–10), invariant (`I1–I16`), or formula ($T_{max} = F \cdot (A + D + \epsilon) \le B$).
3. **State the Honest Residual or Limit in the third sentence:** Never claim perfection. State whether the risk is `CLOSED` (with named test), `BOUNDED` (with stated technical residual and monitor alarm), or `OPEN` (with owner and closing evidence required before real-world use).

---

## Category 1: Clinical Reality, Patient Safety & Operating Model

### Q1.1: "If every government hospital in the district is full, your software doesn't create a single ICU bed or NICU warmer. How does this help the patient?"
- **Direct Answer:** It does **not** create physical capacity—we state that plainly as our first honest limit (`v7 §8, §16`, `v8 §11`, `FINAL §2`).
- **Operational Value:** What it changes is *when and how* capacity refusal is discovered:
  1. **Discovery Before Departure / En Route, Not at the Hospital Door:** In the Safdarjung Hospital audit (3,220 referrals, 2018–2023) `[V]`, **90.6%** of critically ill obstetric patients arrived with no prior communication and **47.3%** had visited $\ge 2$ hospitals first. Discovering that Facility A lacks an anaesthetist in $\le 4\text{ minutes}$ via a structured `DECLINE(reason = NO_ANAESTHETIST)` or `AT_CAPACITY` load-guard response—before the ambulance drives $40\text{ minutes}$ to a locked door—redirects the handover to Facility B or escalates immediately to the district dispatcher (`ESCALATED_TO_DISPATCHER`).
  2. **Negotiated Partial Capability (`COUNTER`):** In Das et al. (2023) `[V]`, **19%** of referrals were driven purely by missing resources (no emergency OT 47%, no NICU 45%, no anaesthetist 24%, no paediatrician 22%). A receiving CMO can issue a structured `COUNTER` (*"OT available now, anaesthetist in 20 minutes"* or *"Can stabilize mother, no NICU"*), allowing the referring clinician to make an informed clinical choice in $\le 2$ rounds rather than a blind transfer.
  3. **District Bottleneck Evidence:** Every `DECLINE` and `COUNTER` logs structured enum reason codes in `event.detail` (`I11`), giving District Health Officers cryptographic, timestamped evidence of *which specific resource* (blood, OT, anaesthetist) is causing refusals at each tier.

---

### Q1.2: "In an eclampsia emergency, what if the referring PHC nurse doesn't know the exact time or dose of the $\text{MgSO}_4$ loading dose given earlier? Does your state machine reject the referral?"
- **Direct Answer:** **Never.** Blocking a referral over missing historical knowledge would delay care and violate **Invariant `I3` (Never block care)** (`v8 Defect D1`, `FINAL §7, §16`).
- **Exact Mechanism:**
  - In our `referral` table and Dakshata clinical payload, `mgso4_status` (`GIVEN | NONE_GIVEN | UNKNOWN`) is **answer-required, never knowledge-required** (`CHECK (mgso4_status IN ('GIVEN','NONE_GIVEN','UNKNOWN'))`).
  - If the clinician selects `UNKNOWN`, `CREATE` succeeds immediately and transport is never held.
  - On the receiving hospital's desk, `mgso4_status = 'UNKNOWN'` renders a high-contrast red clinical safety banner: **"Pre-referral $\text{MgSO}_4$ dose UNKNOWN — verify clinically before administering additional dose"** (`v8 §8`, `FINAL §13, §16`).
- **Clinical Rationale:** Under the Dakshata guidelines (14 g Pritchard loading regimen), the clinical hazard at the receiving hospital is **accidental double-dosing** leading to magnesium toxicity / respiratory arrest when documentation is missing (incomplete slips occurred in 50% of Safdarjung referrals and 63% of Maharashtra referrals `[V]`). Requiring an explicit `GIVEN | NONE_GIVEN | UNKNOWN` choice prevents silent omission while never holding back the ambulance.

---

### Q1.3: "Does the ambulance have to wait at the referring clinic until the handshake finishes and a hospital clicks Accept?"
- **Direct Answer:** **No.** ReferralHandshake runs **two independent state machines in parallel**: the **Handshake Track** (`hs_state`) and the **Transport Track** (`tr_state`) (`v7 §6`, `v8 §4.1`, `FINAL §3 I3, §4`).
- **Exact Mechanism:**
  - `tr_state` (`REQUESTED -> DISPATCHED -> EN_ROUTE -> ARRIVED -> HANDED_OVER | TR_CANCELLED`) is updated via `TR_UPDATE` and `TR_DESTINATION_CHANGE`.
  - **Invariant `I3`:** The server's `TR_UPDATE` transition handler **never reads `hs_state`** (verified by mutation test on `transitions.yaml` and Quint run `transportNeverGated`, `FINAL §12`).
  - An ambulance can depart immediately toward the clinician's primary catchment target while the handshake ladder runs in parallel.
  - If ownership moves to a different facility down the ladder while the ambulance is `EN_ROUTE`, the ambulance crew and dispatcher receive a **Redirect Advisory** with the detour ETA from cached Mapbox Matrix data (`F5 Case (f)`). The system **never auto-reroutes** a moving ambulance; a human (crew or dispatcher) decides and logs `TR_DESTINATION_CHANGE(accepted = true | false)`.

---

### Q1.4: "Who actually holds the receiving device in a chaotic government hospital casualty ward, and why would a busy CMO bother responding?"
- **Direct Answer:** Offers go to a **rostered duty role** (`NURSE`, `CMO`, `CONSULTANT`), never a hardcoded individual (`v7 §8`, `v8 §11`, `FINAL §7 roster`).
- **Why Receivers Respond (Operational Design & Anti-Goodhart Protections):**
  1. **Concurrent Multi-Slot Notification + Escalation (`F2`, `F3`):** At rung $0$, all active slots for the facility are notified concurrently via PWA SSE and empty-payload FCM; at rung $A/4$, Exotel outbound voice calls stagger across slots (`slot i` at $A/4 + i \cdot \delta$); at rung $3A/4$, the district dispatcher is paged for phone-assisted proxy entry.
  2. **Declining for a Missing Resource is Legitimate, Silence is the Only Losing Move (`v8 §4.2, §11`):** `ACCEPT`, `COUNTER`, and `DECLINE(reason)` are all valid, timestamped professional responses. A documented `DECLINE(NO_NICU)` is recorded as a **facility capacity signal**, not an individual fault.
  3. **Advance Notice Stops Unannounced Doorway Crises:** Receiving staff get structured ISBAR + Dakshata notice and ETA before the patient arrives at casualty.
  4. **Anti-Goodhart UI (`v8 §11`, `FINAL §15`):** Receiving desks display a clinical priority queue with **zero countdown clocks** (since visible countdown targets distorted triage in empirical Manchester Triage System studies `[V]`). Furthermore, **Arrival-to-Handover (APOT)** is tracked separately from **Acceptance**, so gaming the metric by clicking Accept without a bed is immediately exposed (`Loophole #12, #24`, `Matrix K2`).

---

### Q1.5: "What happens if an accepting hospital has an unexpected crisis and rejects the patient when the ambulance arrives at the door, or what if the ambulance arrives unannounced at a hospital that never had an offer?"
- **Direct Answer:** Both scenarios are explicitly handled in our **Six Arrival Cases (`F5`, `FINAL §4`)** without ever blocking clinical care:
  - **Geofence is Only a Hint (`D2`, `F5 Case (a)`):** Because budget phone GPS in vehicles has $7\text{–}13\text{ m}$ typical error and up to $\sim 50\text{ m}$ median error in bad multipath/scintillation conditions `[V/V*]`, a $200\text{ m}$ + dwell geofence only emits `ARRIVAL_SUGGESTED`. A human (EMT or receiving desk) must confirm `TR_UPDATE(ARRIVED)`.
  - **Broken Commitment on Arrival (`ARRIVAL_REJECTED`):** If the lease-holding hospital cannot take the patient upon arrival, the desk or EMT triggers `ARRIVAL_REJECTED`. Under the referral row lock, this sets the offer to `ARRIVAL_REJECTED`, increments `lease_epoch + 1`, clears the lease, revokes `payload_grant` (`I10`), logs the broken commitment in the hash-chained event log, and calls `advance()` to offer the next facility in `referral.chain` (or escalates to `ESCALATED_TO_DISPATCHER` if exhausted).
  - **Unannounced Arrival at Non-Owner (`F5 Case (c)`):** Emits `ARRIVAL_AT_NON_OWNER` urgent alert and pages the dispatcher, who can issue `DISPATCHER_ASSIGN` (`source = 'DISPATCHER'`). Treatment is never blocked.

---

### Q1.6: "What if the receiving hospital treats the patient but completely forgets to close the referral in your app?"
- **Direct Answer:** Closed by **`F6` (Two-Stage `CLOSURE` Deadline & Explicit Unknown Outcome, `FINAL §4`)**.
- **Exact Mechanism:**
  - When `tr_state` reaches `HANDED_OVER`, the server inserts a `CLOSURE` deadline ($24\text{ h}$ in pilot profiles; $20\text{ s}$ in `DEMO_FAST`).
  - **First Expiry:** Poller fires `CLOSURE_OVERDUE`, surfacing the unclosed referral to the receiving desk, dispatcher, and district view, and re-arms the `CLOSURE` deadline once.
  - **Second Expiry:** The system automatically executes `CLOSE` with `outcome = 'UNKNOWN_COUNTER_REFERRAL'`, `proxy = true`, `actor = SYSTEM`.
  - **Why this matters:** Every referral deterministically reaches a terminal state (`Reachability & Exit Table, F6`), and the system **never fabricates a clinical outcome**—it records an explicit, auditable digital counter-referral gap (`UNKNOWN_COUNTER_REFERRAL`) while scheduling clinical payload crypto-shredding.

---

## Category 2: Distributed Systems, Database & Concurrency Architecture

### Q2.1: "Why did you use a single PostgreSQL 16 primary instead of Blockchain, Kafka/Debezium, Redis, CRDTs, or SQLite?"
- **Direct Answer:** Every technology we excluded either violates a safety invariant, adds operational fragility for a 2-person / 1-district deployment, or solves a problem we do not have (`v8 §0.2, §1.3, §3`, `FINAL §0`):
  1. **Why not Blockchain (`v8 C4`):** Within a district emergency network, there is a natural single administrative arbiter; Byzantine consensus across untrusted miners adds seconds of latency and cost without solving clinical coordination. Our SHA-256 RFC 8785 JCS hash chain + 5-second Ed25519 C2SP Merkle checkpoints pushed to external witnesses (`§11`) provides cryptographic tamper-*evidence* and split-view detection in milliseconds.
  2. **Why not SQLite (`v8 Defect D8`, `Appendix A`):** SQLite in WAL mode defaults to `synchronous=NORMAL`, which can lose committed transactions on power loss, and its single-writer lock serializes *all* referrals globally across a single file. PostgreSQL 16 with `synchronous_commit=on` gives durable commit and **per-referral row locking** (`SELECT * FROM referral WHERE id=%s FOR UPDATE`), so unrelated referrals never block each other (`v8 §5.2`).
  3. **Why not Read-Replica Locking (`v8 Appendix A`):** PostgreSQL hot standbys cannot take row locks. All `apply_command()` writes execute strictly against the single writable primary (with Multi-AZ synchronous standby for pilot failover); replicas serve read-only projections only.
  4. **Why not Kafka, Debezium, or Redis (`v8 §3`, `FINAL §0`):** Introducing an external message broker or cache tier creates dual-write consistency bugs and cache-invalidation leaks after crypto-shredding (`§10`). Instead, `outbox` and `deadline` rows are written in the **exact same ACID transaction** as `event` and `referral`, drained via `FOR UPDATE SKIP LOCKED`.
  5. **Why not CRDTs for Contract State (`v7 §6`, `FINAL §0`):** You cannot allow two hospitals to concurrently accept the same patient offline and "merge" ownership later (**Invariant `I2`: One patient, one owner**). Contract state transitions are strictly serialized on the primary. Append-only observations (`telemetry` table: GPS, vitals) use unique `UUIDv7` `event_id`s so offline reconciliation is a trivial mathematical **set union** with zero CRDT library overhead.

---

### Q2.2: "Prove that your command pipeline and timer poller cannot deadlock under high concurrency."
- **Direct Answer:** Closed by **`F1` and Invariant `I14` (Global Lock Hierarchy + Two-Phase Stateless Poller + DB Lock-Enforcement Trigger, `FINAL §5, §7`)**, verified empirically by `T-F1 (lock_order_200way)` with `deadlocks_delta = 0`.
- **The Defect We Fixed from Earlier Designs (`F1`):** If a timer poller starts a transaction, locks a `deadline` row, and then calls `apply_command()` which locks the `referral` row, while a user's `ACCEPT` command locks `referral` first and then updates `deadline`, you get a classic AB-BA deadlock cycle (`deadline -> referral` vs. `referral -> deadline`).
- **Our Three-Part Proof of Deadlock Freedom:**
  1. **Strict Global Total Lock Order:** Every multi-lock transaction acquires row locks strictly in the forward order:
     $$\text{referral} \rightarrow \text{offer (ORDER BY id)} \rightarrow \text{deadline (ORDER BY id)} \rightarrow \text{outbox}$$
     And every command transaction touches **at most one `referral`**.
  2. **Two-Phase Poller (`FINAL §5`):**
     - **Phase 1 (Claim):** The poller executes a **single, immediately committed SQL statement** (`UPDATE deadline SET claimed_until = clock_timestamp() + interval '5 seconds' WHERE id IN (... FOR UPDATE SKIP LOCKED) RETURNING ...`). Because it uses `SKIP LOCKED` and commits immediately before touching `referral`, Phase 1 never waits while holding a lock.
     - **Phase 2 (Apply):** For each claimed deadline, the poller calls `apply_command(TIMEOUT)`, which locks `referral` **first**, then `offer`, then re-reads `deadline` (`WHERE id=$1 AND status='PENDING'`).
  3. **Database Trigger Enforcement (`rhp_require_lock`):** In PostgreSQL 16 (`§7`), Step 4 of `apply_command()` executes `SELECT set_config('rhp.locked_referral', r.id::text, true)` immediately after `SELECT * FROM referral WHERE id=%s FOR UPDATE`. Triggers `lk_referral`, `lk_offer`, `lk_deadline`, `lk_event`, `lk_grant`, and `lk_outbox` check `current_setting('rhp.locked_referral', true)` on every contract-state write and raise `I14_LOCK_NOT_HELD` if any code path ever attempts to mutate contract state without holding the referral lock first.

---

### Q2.3: "Why do you maintain both `version` (returning HTTP 412) and `lease_epoch` (returning HTTP 409) on a referral? Aren't they redundant?"
- **Direct Answer:** No—conflating them was **Defect `D7`** in earlier drafts (`v8 §0.2 D7, §4.4`, `FINAL §4, §5`). They represent two distinct distributed-systems concepts:
  1. **`referral.version` $\rightarrow$ Optimistic State Precondition (`HTTP 412 Precondition Failed`):** Increments on *every* state-changing command. When a client sends `expected_version` or `expected_epoch` that is behind the current state (a stale writer or zombie tab), Step 5 fences it out with `412` and records it in `rejected_command` (**Invariant `I8`**).
  2. **`referral.lease_epoch` $\rightarrow$ Monotonic Ownership Fencing Token (`HTTP 409 Conflict`):** Increments **only** on ownership changes (`ACCEPT`, `CONFIRM_COUNTER(true)`, `DISPATCHER_ASSIGN`, `ARRIVAL_REJECTED`). When two hospitals race on a valid version in `PARALLEL2` mode (or during the `SOFT_OPEN` overlap window), the second hospital's request is not "stale" by precondition—it lost a live ownership race and receives `409 LEASE_HELD` (or `409 LATE_ACCEPT_REJECTED`) so the UI can explain *why* ownership went elsewhere.
  3. **Database Backstop (`Invariant I2`):** Even if application code had a bug, the partial unique index `CREATE UNIQUE INDEX one_lease ON offer (referral_id) WHERE status = 'ACCEPTED'` makes it impossible for PostgreSQL to commit two accepted offers for the same referral.

---

### Q2.4: "Explain your `SOFT_OPEN` late-accept rule and why `open_offers` is capped at 2 (`F13 / I12`)."
- **Direct Answer:** Closed in **`F13` and Invariant `I12` (`FINAL §4`)**.
- **The Problem:** Suppose Hospital 1 (`step k`) is slow to click ACK because the CMO is scrubbing out of theatre. At $t = A$, the timer escalates and offers Hospital 2 (`step k+1`). Two seconds later, Hospital 1 clicks Accept before Hospital 2 has even looked at the screen. If we hard-killed Hospital 1's offer at $t = A$, we just threw away a willing, closer hospital while Hospital 2 hasn't even acknowledged!
- **The `SOFT_OPEN` Mechanism:**
  1. In `SEQUENTIAL` mode, when `step k` times out and `step k+1` is offered (`OPEN`), `step k` transitions to `SOFT_OPEN` rather than `TIMED_OUT`.
  2. **Race Resolution under Lock:**
     - If `step k` submits `ACCEPT` **before** `step k+1` commits `ACK`, `step k` wins the lease! `step k+1` is marked `SUPERSEDED` with a polite cancellation notice.
     - The moment `step k+1` commits `ACK` (proving a human at Hospital 2 is actively evaluating the case), `step k`'s `SOFT_OPEN` offer immediately transitions to `TIMED_OUT`. Any subsequent `ACCEPT` from `step k` is deterministically rejected with `409 LATE_ACCEPT_REJECTED`.
  3. **Strict Cap `open_offers <= 2` (`I12`):** Open statuses are `{OPEN, ACKED, COUNTERED, SOFT_OPEN}`. If `step k+1` also times out and `step k+2` is offered while `step k-1` was somehow still `SOFT_OPEN`, `step k-1` is forced to `TIMED_OUT` at that instant so `open_offers` never exceeds `2` (enforced by `CHECK (open_offers BETWEEN 0 AND 2)` on `referral`).

---

### Q2.5: "How does your 10-step `apply_command()` pipeline guarantee idempotency across network drops, client retries, AND domain rejections (`F14`)?"
- **Direct Answer:** Closed in **`F14` (`FINAL §5`)**.
- **Exact Execution Flow:**
  1. **Step 1 (Before Referral Lock):** We compute `h = sha256(jcs(cmd.body_for_hash()))` and take a non-blocking transaction-level advisory lock `pg_try_advisory_xact_lock(hashtextextended(actor_id || ':' || idem_key, 0))`.
     - If another request with the same `(actor_id, key)` is currently in flight, it immediately returns `409 DUPLICATE_IN_FLIGHT`.
     - If a row exists in `idempotency` with a different `request_hash`, it returns `422 KEY_REUSED_DIFFERENT_PAYLOAD`.
     - If `status == 'DONE'`, it replays the exact stored `http_status` and `response` JSON (`200`, `409`, `412`, or `422`).
  2. **Step 4 (`SAVEPOINT sp_cmd`):** After locking the `referral` row (`FOR UPDATE`), setting `rhp.locked_referral`, and computing monotone timestamp `ts = GREATEST(clock_timestamp(), r.head_ts)`, we open `SAVEPOINT sp_cmd`.
  3. **Deterministic Domain Rejections (`403 / 409 / 412 / 422`):** If a command fails fencing or transition guards, we execute `ROLLBACK TO SAVEPOINT sp_cmd` (which **retains the referral lock** acquired before the savepoint), insert an audit record into `rejected_command`, mark `idempotency` as `DONE` with the error status/body, and `COMMIT`. Replaying the retry returns the exact same rejection without re-running state logic.
  4. **Crash / Unhandled Exception:** Any non-domain exception aborts the entire transaction; the `idempotency` row rolls back completely, and the client's retry executes cleanly from scratch.

---

### Q2.6: "What happens if the server's system clock jumps backward via NTP or steps forward during a referral (`F11 / I16`)?"
- **Direct Answer:** Closed/Bounded in **`F11` and Invariant `I16` (`FINAL §6, §18 T2/T3`)**:
  - **Client Clocks:** Never trusted for deadlines; `client_ts_ms` is recorded as metadata only.
  - **Monotone Server Time (`I16`):** Inside the referral row lock (Step 4), the authoritative timestamp is computed as:
    $$\text{ts} = \max(\text{clock\_timestamp}(), \text{referral.head\_ts})$$
    And the DB trigger `rhp_event_guard` enforces `NEW.server_ts >= r.head_ts`. Thus, even if the OS clock steps backward by $\Delta$, per-referral event timestamps never regress.
  - **Chrony Slew-Only & Alarm:** Pilot hosts configure `chrony` in slew-only mode (no `makestep` after boot) traceable to NIC/NPL (`[V*]`), and `heartbeat.ntp_offset_ms` raises an operator alarm if offset exceeds $2\text{ s}$.
  - **Bounded Residual:** A forward clock step $\Delta$ can fire deadlines up to $\Delta$ early (causing premature escalation only, never a double lease because `one_lease` and row locks are clock-independent, and `SOFT_OPEN` preserves the prior offer). A backward step delays deadlines by at most $\Delta \le 2\text{ s}$ before the NTP alarm fires.

---

## Category 3: Formal Verification, Runtime Monitor & Common-Mode Independence

### Q3.1: "You use Quint (`rhp1.qnt`) for model checking. Are you claiming your system is mathematically proven to be bug-free?"
- **Direct Answer:** **Absolutely not**—claiming a "mathematically proven system" is explicitly forbidden in our Claims Register (`v8 Defect D5, D6`, `FINAL §12, §19`).
- **What Each Layer Actually Proves:**
  1. **Bounded Model Checking (`rhp1.qnt` via Quint / Apalache, `FINAL §12`):** Checks our **control-plane specification** (`I2`, `I12`, `I1m`, `IDisp`, `I13`, plus vacuity checks and `transportNeverGated`) within stated bounds ($F = 3\text{ facilities}$, $\text{MAXE} = 4\text{ epochs}$, $25\text{ steps}$). It proves the *state machine design* has no invariant violation within those bounds; it does **not** prove unbounded sizes and does **not** prove the Python implementation.
  2. **Conformance Vectors & 200-Way Barrier Suite (`race200` + Toxiproxy):** Tests the actual FastAPI + PostgreSQL 16 implementation under concurrent load and network faults (`reset_peer`, `slicer`, `latency`, `timeout`).
  3. **Independent Runtime Monitor (`Person B`, `FINAL §12`):** Continuously checks the live database in production/demo.

---

### Q3.2: "If an AI coding agent helped write your code, couldn't the server and the runtime monitor share the exact same bug (Common-Mode Failure)?"
- **Direct Answer:** Closed by **`F17` (Two-Author Chinese Wall + Six Mutation Tests `M1–M6`, `FINAL §12`)** and our **3-Gem + Antigravity Governance Workflow**:
  1. **Architectural Separation of Authors (`F17`):**
     - **Person A (Lane A):** Owns the FastAPI server, `transitions.yaml`, and the Quint specification (`rhp1.qnt`).
     - **Person B (Lane B):** Writes the independent Python runtime monitor (`monitor/`) **strictly from the prose of `§3 Invariants I1–I16`**, in a separate workspace that never views or imports server code.
     - The monitor connects via the read-only PostgreSQL role `rhp_monitor` using a `REPEATABLE READ READ ONLY` snapshot and server-side cursor, folds the `event` stream from genesis (`seq = 1`), recomputes every SHA-256 JCS hash, and performs a **differential check** comparing its folded state against the `referral` row (`DIFF_HEAD`, `DIFF_EPOCH`, `I1–I16`).
  2. **Verification of the Checker via 6 Mutation Tests (`M1–M6`, `FINAL §12`):** We don't assume the monitor works—we deliberately break 6 guards (`M1` skip epoch fencing $\rightarrow$ trips `I8`; `M2` drop `FOR UPDATE` & `one_lease` $\rightarrow$ trips `I2`; `M3` poller holds deadline lock $\rightarrow$ trips `I14` deadlock delta; `M4` remove Quint open-offer cap guard $\rightarrow$ trips `I12` counterexample; `M5` zero `prev_hash` $\rightarrow$ trips `I5`; `M6` ignore confirmation `expires_at` $\rightarrow$ trips `I15`). All 6 must trip their named detector in CI.
  3. **Spec Freeze (`CODEOWNERS`):** AI builders (`AGENTS.md`) are barred from modifying `spec/`, `db/schema.sql`, or `monitor/` to make a failing test pass (preventing LLM reward-hacking, `v8 §7.1`).

---

### Q3.3: "Why did you build a Python snapshot monitor instead of using a formal stream-runtime language like TeSSLa or RTLola?"
- **Direct Answer:** Resolved in **`v8 Defect D19` and `FINAL §12`**:
  - Stream runtime verification engines like TeSSLa are designed for asynchronous, out-of-order event streams where timestamps and sequence numbers must be reconstructed in memory (requiring a heavy JVM toolchain).
  - In `RHP-1`, Step 4 and Step 9 of `apply_command()` assign a strictly sequential, gap-free per-referral `seq` (`PRIMARY KEY (referral_id, seq)` enforced by `rhp_event_guard`) inside the referral row lock.
  - Because `seq` is already totally ordered per referral in PostgreSQL, out-of-order stream reconstruction is a non-issue. A 45-line zero-dependency Python monitor reading a `REPEATABLE READ READ ONLY` snapshot is simpler, transparent to audit line-by-line on stage, and has zero JVM memory overhead.

---

## Category 4: Timing Math, Reach Layer, Telecom & Offline Mechanics

### Q4.1: "Walk us through your escalation timing bound $T_{max}$. Why doesn't having 3 duty roles inside each facility multiply the total delay by 3?"
- **Direct Answer:** Closed in **`F2`, `F3`, and Invariant `I13` (`FINAL §6`)**.
- **The Math:**
  - Earlier drafts (`v5`) mistakenly multiplied the timeout across intra-facility roles. In our locked architecture (`F2`, `F3`), **all rostered slots at a facility are notified concurrently at rung $0$** (via SSE + FCM), with staggered voice calls at rung $A/4 + i \cdot \delta$ ($i = 0 \dots S-1$) and a dispatcher proxy page at rung $3A/4$—**all occurring strictly inside a single unified ACK window $A$**.
  - Voice stagger is constrained at startup by:
    $$\frac{A}{4} + (S - 1)\delta + V \le \frac{3A}{4}$$
    For `PILOT_OB_CRITICAL` ($A = 60000\text{ ms}, S = 3, \delta = 5000\text{ ms}, V = 20000\text{ ms}$):
    $$15000 + 2(5000) + 20000 = 45000\text{ ms} \le 45000\text{ ms} \quad (\text{passes})$$
  - Worst case at one facility: a receiver ACKs at $A - \epsilon'$ and then stays silent through the full Decision window $D$ (counter-offer confirmation window $C$ sits inside $D$ via $\min(C, \text{remaining } D)$). Adding per-hop poller/apply budget $\epsilon$, each facility consumes at most $A + D + \epsilon$.
  - Across $F$ facilities in the catchment chain, the worst-case time from `CREATE` to `ESCALATED_TO_DISPATCHER` is:
    $$T_{max} = F \cdot (A + D + \epsilon) \le B$$
- **Locked Profile Table (`FINAL §6`):**
  - `PILOT_OB_CRITICAL`: $3 \cdot (60 + 180 + 3)\text{ s} = 729\text{ s} \le B = 900\text{ s}$
  - `PILOT_STANDARD`: $3 \cdot (120 + 300 + 3)\text{ s} = 1269\text{ s} \le B = 1500\text{ s}$
  - `DEMO_FAST`: $3 \cdot (3 + 4 + 1)\text{ s} = 24\text{ s} \le B = 25\text{ s}$
  - `DEMO_VOICE`: $2 \cdot (45 + 20 + 1)\text{ s} = 132\text{ s} \le B = 150\text{ s}$
  - If any profile violates $T_{max} \le B$, or if a demo profile is loaded when `REAL_DATA=1`, the startup validator refuses to boot (`T-F2`, `T-F3`).

---

### Q4.2: "What happens if the Exotel outbound voice call hits a hospital's voicemail or an automated 'number busy' recording? Doesn't your system falsely mark that as `ACKNOWLEDGED`?"
- **Direct Answer:** Closed by **`F7` (AMD + Mandatory Press-1 Human Gate, `FINAL §8, §18 I5`)**.
- **Exact Mechanism:**
  1. Merely answering the phone line **never** triggers an `ACK`.
  2. When the outbound Exotel call connects, we evaluate Answering Machine Detection (AMD) and play an 8-second gate prompt: *"Press 1 to hear an emergency referral."*
  3. Voicemail boxes, carrier announcements, or silence fail the 8-second gate $\rightarrow$ zero `ACK` is recorded, and the call is marked `UNANSWERED`.
  4. Only when a human presses `1` does the webhook invoke `apply_command(ACK, channel='VOICE')` and play the pre-recorded Kannada/Hindi/English de-identified summary.
  5. To `ACCEPT`, `COUNTER`, or `DECLINE`, the caller must still enter their 4-digit duty PIN followed by `#` (`%23`), verified via Argon2id on the server.
  6. **Webhook Latency Budget:** Exotel enforces a $5\text{ s}$ HTTP timeout `[V]`. Our handler deduplicates via `inbox(source, external_id)` (`ON CONFLICT DO NOTHING`) and budgets $\le 1.5\text{ s}$ for `apply_command()`; the spoken *"recorded"* confirmation plays **only after** the PostgreSQL transaction commits (`T2 Gate`: 20/20 voice ACKs recorded only after commit).

---

### Q4.3: "How does the 9-character Paper Code work mathematically, and why did you choose Crockford Base32 + $\bmod 37$?"
- **Direct Answer:** Specified in **`FINAL §8` (`T2 Gate`)**:
  - Each printed referral card carries an 8-symbol Crockford Base32 payload ($40\text{ bits}$, integer value $N$) plus 1 check symbol computed as:
    $$c = N \bmod 37$$
    mapped onto the 37-symbol Crockford check alphabet (`0-9A-Z*~$=U`).
  - **Mathematical Guarantee:** Because $37$ is an odd prime and $\gcd(32, 37) = 1$, every power $32^i$ is invertible $\bmod 37$:
    - Any **single-symbol substitution error** of magnitude $\Delta \in \{1 \dots 31\}$ at position $i$ shifts $N$ by $\Delta \cdot 32^i \not\equiv 0 \pmod{37}$ $\rightarrow$ **100% detected**.
    - Any **adjacent transposition** of distinct symbols $a \neq b$ at positions $i, i+1$ shifts $N$ by $(a - b) \cdot 32^i \cdot (32 - 1) = 31(a - b)32^i \not\equiv 0 \pmod{37}$ $\rightarrow$ **100% detected**.
  - **Zero Double Entry (`v8 §6.2, D18`):** The printed ReferralHandshake card *is* the physical Dakshata referral slip. Clinicians enter data once; if the receiving hospital is offline or lacks the record, typing the 9-character paper code links or initializes the record (rate-limited to $10\text{ attempts/min}$ per session).

---

## Category 5: Security, Cryptography, Privacy & Indian Regulatory Posture

### Q5.1: "A database administrator has `postgres` superuser access. Can't they disable triggers, edit the `event` table, recompute all the SHA-256 hashes, and cover their tracks?"
- **Direct Answer:** That is the classic **split-view / history-rewrite attack**, and it is why we never call a hash chain "immutable" (`v8 Defect D10`, `FINAL §11, §18 S1/S2`). We close detection via **Independent C2SP-Style Signed Merkle Checkpoints (`F8`)**:
  1. **Privilege Separation:** The application connects as `rhp_app` (`REVOKE UPDATE, DELETE ON event, checkpoint, rejected_command`). The checkpoint signer runs as a separate OS user (`rhp-sign`, UID `1002`, key file `0400`) connecting via `rhp_witness`.
  2. **5-Second Merkle Checkpoints:** Every $5\text{ s}$, `rhp-sign` reads a `REPEATABLE READ READ ONLY` snapshot, builds a binary Merkle tree over all referrals sorted by `id` with leaf:
     $$L = \text{SHA256}(\texttt{0x00} \parallel \text{referral\_id}_{16\text{B}} \parallel \text{head\_seq}_{8\text{B BE}} \parallel \text{head\_hash}_{32\text{B}})$$
     and internal node $\text{SHA256}(\texttt{0x01} \parallel \text{left} \parallel \text{right})$, and signs the C2SP note (`rhp1/<deployment>\n<tree_size>\n<root_b64>\n`) with Ed25519.
  3. **External Witnesses:** Checkpoints are pushed every $5\text{ s}$ to independent witnesses: the Guarantee Arena big screen, judges' phones (`/checkpoints/latest`), and an off-box append-only log on a second machine.
  4. **Result:** Even if a superuser rewrites `event` rows *and* recomputes the per-referral SHA-256 chain in PostgreSQL, the new `head_hash` will not match the Merkle root already held on the judges' phones! The pure-JS browser verifier checks the $O(\log N)$ inclusion proof and flags `ROOT_MISMATCH` or `TRUNCATED`.
  5. **Legitimate Backup Restore vs. Tamper (`F8`):** If the database legitimately restores from a backup after a crash, an operator must sign a `checkpoint(kind='RESTORE')` record using an **offline cold Ed25519 key** (pinned in the client verifier) and append a `RESTORE` event linking the restored head hash. Any head regression without a valid cold-key signature is flagged as `TAMPER`.
  6. **Honest Open Risk (`S3`):** If an attacker steals the live `rhp-sign` private key from the host OS, they could sign forged checkpoints from that moment forward until key rotation. In `§20 Rank #3`, we mark `S3` as `OPEN` for pilot closure via cloud HSM/KMS + key rotation drill.

---

### Q5.2: "What if a malicious rival hospital or script dials or clicks wrong PINs 3 times to lock out a competing hospital's duty nurse (`Lockout-DoS`)?"
- **Direct Answer:** Closed by **`F7` (`FINAL §5 Step 3, §9, §18 I2/I3`)**:
  - **Per-Session / Per-Call Scope:** `pin_failed` and `pin_locked_until` live on the `session` table (`CHECK (device_id IS NOT NULL OR call_sid IS NOT NULL)`), **not** globally on the `roster` row!
  - **How Enrollment Works:** A web/Android session requires redeeming a single-use `enrollment_ticket` issued by an admin, binding a device Ed25519 public key (`device` row), and holding an opaque session token. A voice session is scoped to a verified outbound `call_sid` dialled by the server to the rostered `phone_e164`.
  - **Autonomous Transaction for PIN Failures:** In Step 3 of `apply_command()`, Argon2id verification runs before the referral lock; if the PIN is wrong, `autonomous_pin_failed(s.id)` increments `session.pin_failed` on a **separate autonomous database connection** that commits immediately (so rolling back the command cannot reset the strike counter).
  - Backoff is $0\text{ s}, 5\text{ s}, 30\text{ s}$, then a $120\text{ s}$ lock **for that specific `session_id` or `call_sid` only** (emitting `PIN_LOCKED` and paging the dispatcher on strike 3). A rival cannot lock out another hospital's legitimate device session.

---

### Q5.3: "When an offer to Hospital A is declined or superseded because Hospital B accepted, how do you stop Hospital A's open browser tab from continuing to receive patient clinical updates over SSE (`F10 / I10`)?"
- **Direct Answer:** Closed by **`F10` and Invariant `I10` (`FINAL §7, §9, §18 P4`)**:
  1. When an offer transitions to `DECLINED`, `SUPERSEDED`, `WITHDRAWN`, `ARRIVAL_REJECTED`, or final `TIMED_OUT`, `apply_command()` sets `payload_grant.revoked_at = ts` inside the same transaction and emits a `GRANT_REVOKED` event.
  2. For **every SSE frame** and every $15\text{ s}$ heartbeat, the SSE hub re-evaluates `(facility_id, role_slot, active payload_grant)` before emitting bytes.
  3. On `GRANT_REVOKED`, the relay pushes a control frame on the next cycle; the server immediately strips clinical fields for that subscriber, and the React PWA wipes the decrypted clinical DOM state from memory (`Cache-Control: no-store`).
  4. **Honest Bounded Residual (`Matrix P4`):** Data that was already rendered on screen or photographed by a user while their grant was legitimately active cannot be physically recalled from their eyeballs; post-revocation stream leakage is zero (`T-F10 sse_revoke`).

---

### Q5.4: "Explain your Crypto-Shredding architecture (`D9`, `§10`) and how you handle the legal tension between DPDP Act erasure and NMC medical record retention."
- **Direct Answer:** Closed technically via **Envelope Encryption + Monthly KEK Epochs (`v8 Defect D9`, `FINAL §7, §10`)**, and bounded legally as a configurable policy parameter (`Matrix P5, L2`):
  1. **Why Deleting a Salt is Not Crypto-Shredding (`D9`):** Earlier drafts proposed "deleting a salt," which does nothing to decryptable ciphertext. In `FINAL §7 & §10`, `clinical_payload` and `event_secret` are encrypted with a **per-referral 256-bit AES-GCM Data Encryption Key (DEK)** (with AAD = `referral_id || key_id || schema_ver`).
  2. **Two-Tier Shredding (Live DB + WAL/Backups):**
     - Each referral's DEK is wrapped (`wrapped_dek` in `key_version`) using AES-KW under a monthly Key Encryption Key (`kek_epoch`).
     - At `clinical_payload.expires_at`, the shredder deletes the `clinical_payload` and `event_secret` rows and sets `key_version.wrapped_dek = NULL, status = 'SHREDDED'` (`CHECK ((status='SHREDDED') = (wrapped_dek IS NULL))`).
     - Because `event.secret_hash` (SHA-256 of the ciphertext) is what sits inside the `event` hash chain, shredding the ciphertext and DEK **never breaks hash-chain verification**!
     - Because PostgreSQL WAL archives and nightly backups still hold historical pages, once every referral in a `kek_epoch` cohort expires, destroying that single `kek_epoch` master key renders all historical backups of that cohort cryptographically unrecoverable (`Matrix P5`).
  3. **PHI-Free Metadata Log (`F9 / I11`):** `event.detail` is restricted by both Pydantic `Literal` enums and the PostgreSQL `CHECK (rhp_detail_ok(type, detail))` function to per-type allowlisted keys containing only uppercase enum tokens, UUIDs, booleans, and integers. Aggregate exports bucket timestamps to $4\text{ hours}$ and suppress cells with $k < 5$ referrals.
  4. **Indian Legal & Regulatory Posture (`§10`):**
     - **Handover Record vs. Medical Record:** ReferralHandshake holds a transient *inter-facility handover record*, not the hospital's longitudinal medical record.
     - **DPDP Act 2023 & Rules 2025:** Notified 13 Nov 2025 vs. Gazette 14 Nov 2025 (`[CONFLICT]`; we cite 14 Nov 2025 conservatively, with core obligations taking effect 13/14 May 2027 `[V]`). Emergency processing relies narrowly on **Section 7(f)** (some drafts cite s.7(d) `[CONFLICT]`; we cite the emergency processing provision). Staff usage telemetry under **Section 7(i)** requires prior written notice to staff, data minimization, strict siloing from HR performance records, and erasure after evaluation (`v8 §10.3`).
     - **Erasure (DPDP s.8(7)) vs. Retention (NMC 2020 3-year teleconsultation retention / 180-day CERT-In logs):** Whether NMC's 3-year retention applies to an emergency handover record is unsettled (`[GAP]`, `Matrix L2`). Therefore, `clinical_payload.expires_at` is an administrator-configured policy parameter awaiting formal legal opinion before real-data deployment. Our prototype runs strictly with `REAL_DATA=0` (100% synthetic data).

---

### Q5.5: "Are you ABDM compliant and BSA Section 63 certified?"
- **Direct Answer:** **We never claim either (`§19 Claims Register`).**
  - **ABDM / FHIR Posture (`§10, §15`):** Fetching an unconscious emergency patient's longitudinal health record over ABDM requires patient consent that an unconscious patient cannot provide (and emergency consent-override mechanisms in ABDM are unverified `[GAP]`, `v7 §12`). Therefore, we **never fetch** longitudinal records. Our referral summary is clinician-authored at the point of care, and our export is **FHIR R4-shaped** (`ServiceRequest`, `Task`, `Encounter`, `Communication` using a small curated code subset). We claim *"FHIR-shaped export"* (and *"ABDM-sandbox aligned"* only if sandbox calls are executed)—never *"ABDM compliant"*.
  - **Bharatiya Sakshya Adhiniyam (BSA) 2023 Section 63 (`§10, §11`):** Legal admissibility of electronic records requires formal Part A (custodian) and Part B (expert) certificates signed at the time of evidence production. Our platform generates a **BSA s.63-ready export bundle** (RFC 8785 JCS event file, per-file SHA-256, bundle SHA-256, and pre-populated Part A / Part B certificate templates citing the cryptographic hash), but we never claim our software output is pre-certified.

---

## Category 6: AI Safety, Pilot Economics & Residual Risks

### Q6.1: "Why is AI relegated to Tier 3 (`T3_EXTRAS`) behind a feature flag, and why don't you show AI confidence scores to the doctor?"
- **Direct Answer:** Because in emergency obstetrics, **unverified AI on the critical path is a patient-safety hazard (`v8 §8`, `FINAL §16`)**:
  1. **Empirical Error Rates (`[V]`):** Vision-Language Models (VLMs) on handwritten clinical slips achieve $85\text{–}95\%$ accuracy (meaning $5\text{–}15\%$ error!), and Indic ASR Word Error Rates (WER) exceed $20\%$ on naturalistic rural Kannada/Hindi dialects (`v8 §8`, `FINAL §16`).
  2. **Why Confidence Scores & Explanations Are Banned (`§16`):** Empirical human-AI studies show that displaying AI explanations **increased clinician commission errors from $10\%$ to $21\%$** due to automation bias `[V]`, and LLM confidence scores are poorly calibrated `[V]`.
  3. **Cognitive Forcing Function (`423 ANCHOR_REQUIRED`):** When `T3_EXTRAS` is enabled, the server withholds any AI-extracted draft (`HTTP 423`) until the clinician manually commits two anchor fields (`need_class` and `mgso4_status`). Critical fields require manual re-entry, a fast-approve speed bump applies to AI drafts, and the entire platform runs at 100% capability with AI completely turned off.

---

### Q6.2: "How much does this cost to run for a 6-month district pilot, and why did your earlier research reports have three different numbers ($810, $900–$1,000, and $1,000–$1,500)?"
- **Direct Answer:** Reconciled in **`F18` (`FINAL §17`)**. The three earlier numbers were not contradictions—they priced three different subsets of the stack. Here is the exact reconciled monthly and 6-month table for **AWS Mumbai (`ap-south-1`) Multi-AZ** (without Kubernetes):

| Infrastructure Component | Monthly (USD) | 6-Month Total (USD) | Which Earlier Figure This Explains |
|---|---|---|---|
| Managed PostgreSQL 16 Multi-AZ (`db.t4g.medium`) | $\$95.00$ | $\$570.00$ | — |
| Storage: $2 \times 100\text{ GB gp3}$ | $\$23.00$ | $\$138.00$ | — |
| Application Load Balancer (ALB) | $\$22.00$ | $\$132.00$ | — |
| **Base Database + ALB Subtotal** | **$\$140.00$** | **$\$840.00$** | Explains Report 3's **$\$810$** ($\$30$ delta is ALB LCU rounding) |
| $2 \times$ Small App VMs (API + Poller/Relay/Monitor) | $\$26.00$ | $\$156.00$ | — |
| Backups / S3 ($8$) + Logs ($10$) + Data Transfer ($6$) | $\$24.00$ | $\$144.00$ | — |
| **Compute + DB + Ops Subtotal** | **$\$190.00$** | **$\$1,140.00$** | Sits at the top of `v4`'s lean **$\$900\text{–}\$1,000$** range |
| Telephony / Exotel IVR & DLT SMS Allowance | $\$25.00$ | $\$150.00$ | — |
| $10\%$ Operational Contingency on $\$215.00/\text{mo}$ | $\$21.50$ | $\$129.00$ | — |
| **Locked Full-Stack Pilot Total (`F18`)** | **$\$236.50/\text{mo}$** | **$\$1,419.00$ ($\approx \$1,420$)** | Matches `v8 §12`'s **$\$1,000\text{–}\$1,500$** full-pilot band |

---

### Q6.3: "Be completely honest: what are the top weaknesses or open risks still remaining in your system right now?"
- **Direct Answer:** Every single failure mode in our 55-row Failure & Attack Matrix (`FINAL §18`) is classified as `CLOSED` (with a named test), `BOUNDED` (with a stated technical residual and monitor alarm), or `OPEN` (with an assigned owner and closing evidence). Our **Top 5 Ranked Residual Risks (`FINAL §20`)** are:
  1. **`OPEN` — Voice Content Legality (`L1`, Owner: Legal Advisor):** The regulatory status of automated outbound voice calls reading de-identified clinical codes to pre-registered hospital duty numbers under TRAI TCCCPR is unsettled (`[GAP]`). We use a whitelisted sandbox with synthetic data now and require a written legal opinion before real-world use.
  2. **`OPEN` — DPDP s.8(7) Erasure vs. NMC 3-Year Retention (`L2`, Owner: Legal Advisor):** Applicability of telemedicine retention rules to handover records is unsettled (`[GAP]`). Retention is parameterised in `clinical_payload.expires_at` pending counsel review.
  3. **`OPEN` — Live Signer Key Theft (`S3`, Owner: T1):** While `rhp-sign` runs under a separate OS user (`UID 1002`, mode `0400`), a root-level host compromise could steal the live Ed25519 signing key until rotation. Closing evidence for pilot: Cloud KMS/HSM signing + key rotation drill log.
  4. **`OPEN` — Clinician & Receiver Adoption Incentives (`Rank #4`, Owner: T2):** Our anti-Goodhart queue and valid `DECLINE(reason)` vocabulary are hypotheses (`v7 §8`, `v8 §11`). Closing evidence: $\ge 3$ structured interviews with PHC clinicians, 108 crew/dispatchers, and CMOs, followed by an ICMR-ethics-reviewed shadow-mode pilot (`v8 §12`).
  5. **`BOUNDED` — No Physical Capacity Created (`Rank #5`, Owner: District Admin):** When every hospital in a district is genuinely full, the protocol cannot invent beds—it bounds the failure by surfacing `ESCALATED_TO_DISPATCHER` within $T_{max} \le B$ and logging structured bottleneck evidence.

---

## 7. Quick-Lookup Traceability Index (`F1–F20` & `I1–I16`)

Use this index during technical questioning to cite exact closures in under 3 seconds:

| Code | One-Line Technical Summary | Primary Test ID |
|---|---|---|
| **`F1` / `I14`** | Total lock order `referral > offer > deadline > outbox`; 2-phase poller; `rhp_require_lock` GUC trigger | `T-F1 lock_order_200way` |
| **`F2`** | Unified ACK window $A$ with notice rungs at $0$ (SSE/FCM), $A/4$ (Exotel IVR), $3A/4$ (proxy page); 4 signed profiles | `T-F2 profile_guard` |
| **`F3` / `I13`** | Concurrent slot notifications; $T_{max} = F \cdot (A + D + \epsilon) \le B$ verified at startup | `T-F3 tmax_validator` |
| **`F4`** | Complete 24-table PostgreSQL 16 DDL, `one_lease`, deferred `referral_lease_fk`, append-only triggers | `T-F4 ddl_load_fk_scan` |
| **`F5`** | 6 arrival cases `(a)–(f)`; 200m geofence emits `ARRIVAL_SUGGESTED` only; human confirms `ARRIVED` | `T-F5 arrival_cases` |
| **`F6`** | Reachability & Exit table; 9 outcomes; 2-stage `CLOSURE` deadline $\rightarrow$ `UNKNOWN_COUNTER_REFERRAL` | `T-F6 reachability_bfs` |
| **`F7` / `I6`** | Single-use enrollment ticket; Argon2id PIN in autonomous txn; per-session/call lockout; AMD + press-1 gate | `T-F7 pin_lockout_scope` |
| **`F8` / `I5`** | Separate OS user `rhp-sign` Ed25519 C2SP checkpoints; $O(\log N)$ Merkle proof; cold-key `RESTORE` | `T-F8 tamper_vs_restore` |
| **`F9` / `I11`** | `rhp_detail_ok` JSONB allowlist CHECK; 4h export buckets; $k \ge 5$ cell suppression | `T-F9 detail_check_fuzz` |
| **`F10` / `I10`** | Per-event SSE grant check; `GRANT_REVOKED` control frame; client DOM wipe | `T-F10 sse_revoke` |
| **`F11` / `I16`** | `GREATEST(clock_timestamp(), head_ts)` under referral lock; chrony slew-only; $>2\text{ s}$ NTP alarm | `T-F11 clock_step` |
| **`F12` / `I15`** | `offer_resource_confirmation.expires_at`; `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` | `T-F12 offline_stale` |
| **`F13` / `I12`** | `open_offers` CHECK $\le 2$; `SOFT_OPEN` late-accept rule; `COUNTER` inside remaining $D$ | `T-F13 open_cap` |
| **`F14` / `I4`** | Step 1 idempotency + advisory lock; `SAVEPOINT sp_cmd` storing domain rejections in `rejected_command` | `T-F14 idem_matrix` |
| **`F15`** | Zero bare "none" residuals in the 55-row failure matrix; every row has a stated bound and reason | `T-F15 residual_lint` |
| **`F16`** | Tiers `T0–T3` behind flags; mandatory second-by-second 30s live proof loop under `DEMO_FAST` | `T-F16 loop_rehearsal` |
| **`F17`** | Person A (server/Quint/YAML) vs. Person B (monitor from prose); 6 mutation tests `M1–M6` | `T-F17 mutation_suite` |
| **`F18`** | Reconciled 6-month AWS `ap-south-1` Multi-AZ cost table ($\$840$ base / $\$1,140$ app / $\$1,419$ full) | `T-F18 cost_recompute` |
| **`F19`** | Explicit 12-state `v7` $\rightarrow$ `RHP-1` (`hs_state`, `offer.status`, `tr_state`, `event.type`) mapping table | `T-F19 v7_map` |
| **`F20`** | `BROKEN_BUILD=1` isolated to `rhp_scratch_broken` minus `one_lease`; red banner; exit 78 on `REAL_DATA=1` | `T-F20 broken_isolation` |