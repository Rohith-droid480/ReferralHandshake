# ReferralHandshake (Protocol RHP-1) — Architecture Integrity Specification

**System:** Referral Handshake Protocol (RHP-1) & Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0  
**Authority Precedence:** `ReferralHandshake_LOCKED_Problem_Statement_v7.md` $>$ Research `[V]` $>$ `ReferralHandshake_v8_LOCKED_Solution.md` $>$ `ReferralHandshake_FINAL_LOCKED_Architecture.md` $>$ `ReferralHandshake_3Gem_Antigravity_Workflow.md`  
**Operating Mode:** Synthetic Data Only (`REAL_DATA=0`)

---

## 1. The Coherence Rule & Architectural Boundaries

Every module, endpoint, worker, and UI surface in ReferralHandshake must be strictly one of the following three architectural primitives:
1. **(a) A State or Event in the Contract:** Authoritative state transitions executed exclusively inside `apply_command()` and persisted to the PostgreSQL 16 primary.
2. **(b) An Interface Producing or Consuming Contract Events:** Stateless channel adapters (React PWA desks, Android EMT app, Exotel outbound IVR, DLT SMS link, Crockford Base32 paper code, dispatcher proxy console).
3. **(c) A Read-Only Projection of the Committed Event Log:** Independent runtime monitor, separate-OS-user checkpoint witness/signer, pure-JS browser tamper verifier, command centre analytics, FHIR R4 exporter, and IEEE 1849 XES exporter.

Any feature or component that does not fit (a), (b), or (c) is out of scope and must be rejected during code review.

```
 PRODUCERS / CONSUMERS (Interfaces)              CORE (Authoritative Contract)            READERS (Log Projections)
 ┌──────────────────────────────┐   ┌──────────────────────────────────────┐   ┌─────────────────────────────────┐
 │ PWA Desks (QR join, SSE)     │   │ FastAPI apply_command() (10 steps)   │   │ Python Monitor (own transitions)│
 │ Android EMT App (Kotlin)     │──▶│ Lock order: referral > offer >       │──▶│ Witness/Signer (OS user 1002)   │
 │ Exotel IVR (outbound voice)  │   │   deadline > outbox; fencing; idem   │   │ Browser Verifier (pure JS)      │
 │ DLT SMS (static alert+link)  │   │ PostgreSQL 16 Primary, sync commit   │   │ Command Centre, XES, FHIR R4    │
 │ Paper Code (Crockford+mod37) │   │ Poller (2-phase) · Outbox Relay      │   │ Big Screen / Guarantee Arena    │
 │ Dispatcher Console (proxy)   │   └──────────────────────────────────────┘   └─────────────────────────────────┘
 └──────────────────────────────┘
```

### 1.1 Locked Technology Stack & Banned Technologies

| Layer | Locked Choice | Mandatory Constraints |
|---|---|---|
| **Database** | PostgreSQL 16 (single writable primary) | `synchronous_commit=on`, `log_lock_waits=on`, `READ COMMITTED` isolation with explicit `SELECT ... FOR UPDATE` row locks. Row locks never run on replicas `[V]`. |
| **API & Workers** | Python 3.12, FastAPI, `psycopg3`, Pydantic v2 | All request models enforce `model_config = ConfigDict(extra='forbid')`. Authoritative state writes occur only in `apply_command()`. |
| **Web Client** | React PWA | Server-Sent Events (SSE) over HTTP/2 with `Last-Event-ID` resume and $15\text{ s}$ heartbeats. Pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256`. |
| **Canonical JSON** | RFC 8785 JCS subset | ASCII keys; values restricted to integers, strings, and booleans. **Floating-point numbers are strictly prohibited.** |
| **Mobile Client** | Native Android Kotlin (T3) / PWA GPS Fallback (T1) | `FOREGROUND_SERVICE_TYPE_LOCATION`, `FusedLocationProviderClient`, Room outbox with `WorkManager`, empty-payload FCM wake ping. |
| **Voice & SMS** | Exotel Outbound IVR + DLT SMS | Trial $\le 10$ whitelisted numbers; webhook response $\le 2\text{ s}$ internal budget ($5\text{ s}$ Exotel hard limit `[V]`); AMD + press-1 gate. Static DLT SMS template ($\le 30$-char variable `[V]`). |
| **Maps & Routing** | Mapbox Directions & Matrix API | Server-side cached ($120\text{ s}$ TTL) for top candidates only (`mapbox/driving`: $25$ coords, $60\text{ req/min}$; `driving-traffic`: $10$ coords, $30\text{ req/min}$ `[V]`). |
| **Formal Verification** | Quint (`rhp1.qnt`) + Independent Python Monitor | Person A authors `transitions.yaml` and `rhp1.qnt`; Person B authors `monitor/monitor.py` from Section 2 prose alone without importing server code (`F17`). |
| **Fault Injection** | Toxiproxy + `asyncio.Barrier` | Used for `race200` concurrency tests and network partition/latency/reset resilience verification. |

**Banned Technologies (Zero Tolerance):**
- **NEVER** introduce blockchain, smart contracts, Kafka, Debezium, Redis, Kubernetes, WebSockets, WhatsApp, on-device LLMs, CRDTs for authoritative contract state, SQLite for the contract store, or floating-point values in canonical JSON payloads.

---

## 2. Invariants I1–I16 (The Contract Guarantees)

| ID | Type | Formal Predicate & Guarantee | Server / DB Enforcement Mechanism | Independent Monitor Detection Rule | Verification Test |
|---|---|---|---|---|---|
| **I1** | Liveness | Every non-terminal referral has $\ge 1$ `PENDING` deadline and a responsible role; overdue deadlines are acted on within tolerance $\tau$. | `DEFERRABLE INITIALLY DEFERRED` constraint trigger `i1_pending_deadline` on `referral` at `COMMIT`. | `now() - due_at > TAU_MS` ($2 \times \text{poll} + 2000\text{ ms}$) with status `PENDING` and no `DEADLINE_TIMEOUT` event. | `T-I1` |
| **I2** | Safety | At most one active ownership lease per referral; `lease_epoch` strictly increases on every lease grant/revocation. | Partial unique index `one_lease` on `offer(referral_id) WHERE status = 'ACCEPTED'` + `SELECT ... FOR UPDATE` on `referral`. | Count of `ACCEPTED` offers $> 1$, or `event.epoch <= st["epoch"]` on `LEASE_GRANTED` in event fold. | `T-I2`, `T-C1` |
| **I3** | Safety | Transport updates (`TR_UPDATE`, `TR_DESTINATION_CHANGE`) are accepted in every non-terminal `hs_state`; care is never blocked. | `TR_UPDATE` handler never reads `referral.hs_state` (except checking not terminal); `mgso4_status` allows `UNKNOWN`. | Any `rejected_command` for `TR_UPDATE` where reason $\neq$ terminal referral or invalid `tr_state` step. | `T-I3`, `T-K1` |
| **I4** | Safety | Each client `event_id` appears at most once; per-referral `seq` is strictly sequential ($1, 2, \dots, n$) with zero gaps. | `idempotency(actor_id, key)` PK, `event.event_id UNIQUE`, `event(referral_id, seq)` PK, trigger `rhp_event_guard`. | `e.seq != st["seq"] + 1` or duplicate `event_id` during event stream fold. | `T-I4`, `T-F14` |
| **I5** | Safety | Per-referral SHA-256 hash chain and Ed25519 checkpoint signatures verify; `CLOSED` or `CANCELLED` requires a valid `outcome`. | Triggers `event_ao`, `checkpoint_ao`, `rhp_event_guard`; `referral` CHECK `(hs_state IN ('CLOSED','CANCELLED')) = (outcome IS NOT NULL AND closed_at IS NOT NULL)`. | `SHA256(prev_hash || JCS(core)) != e.hash` or `e.prev_hash != st["head"]` or `DIFF_HEAD` mismatch. | `T-I5`, `T-F8` |
| **I6** | Safety | Every `ACCEPT`, `COUNTER`, or `DECLINE` originates from a rostered role on a registered device/number with a server-verified PIN, or is explicitly flagged `proxy=true`. | Steps 2, 3, and 5 of `apply_command()` verify `session`, Argon2id `pin_hash`, and active `roster` window. | Event actor lacks a valid `roster` record active at `server_ts` when `proxy = false`. | `T-I6` |
| **I7** | Safety | System-chosen escalation targets belong strictly to `referral.chain`; dispatcher overrides carry `source='DISPATCHER'`. | Trigger `offer_chain_guard` checks `NEW.source='CHAIN'` against `referral.chain` array. | Offer target $\notin$ `referral.chain` while `offer.source == 'CHAIN'`. | `T-I7` |
| **I8** | Safety | Commands carrying a stale `expected_version` or `expected_epoch` are rejected (`412`) and logged in `rejected_command`. | Step 5 of `apply_command()` checks `expected_version == r.version` and `expected_epoch == r.lease_epoch`; rolls back to `sp_cmd` on failure. | Any committed `event` with `e.epoch < st["epoch"]`. | `T-I8`, `M1` |
| **I9** | Safety | A facility is targeted at most once per referral (no $A \rightarrow B \rightarrow A$ referral loops). | `UNIQUE (referral_id, facility_id)` constraint on `offer` table + `advance()` filter. | Duplicate `facility_id` among `OFFER_CREATED` events for the same `referral_id`. | `T-I9` |
| **I10** | Safety | Clinical payload frames are transmitted only to subscribers holding an active (unrevoked) `payload_grant`. | Per-frame SSE authorization check against `payload_grant WHERE revoked_at IS NULL`; immediate `GRANT_REVOKED` frame on revocation. | Any clinical frame emitted to a session whose facility lacks an unrevoked `payload_grant` at `emit_ts`. | `T-I10`, `T-F10` |
| **I11** | Safety | `event.detail` contains only per-type allowlisted keys with closed enum strings, UUIDs, booleans, or $\le 12$-digit integers (PHI-free metadata). | Pydantic `Literal` schemas + PostgreSQL `CHECK (rhp_detail_ok(type, detail))` on `event`. | Scan of `event.detail` keys/values violating `rhp_allowed(type)` regex rules. | `T-I11`, `T-F9` |
| **I12** | Safety | Concurrent open offers (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) per referral never exceed $2$. | `referral.open_offers CHECK (open_offers BETWEEN 0 AND 2)` maintained under the referral row lock. | `r.open_offers > 2` or folded active offer count $> 2$. | `T-I12`, `T-F13` |
| **I13** | Safety | Configured worst-case escalation time satisfies $T_{max} = F \cdot (A + D + \epsilon) \le B$ for the active profile. | Startup profile validator `validate(profile, REAL_DATA)` refuses boot on violation or invalid Ed25519 cold signature. | Monitor recomputes $T_{max} \le B$ at startup and on `/healthz`. | `T-I13`, `T-F3` |
| **I14** | Safety | No contract-state write occurs without holding the `referral` row lock first in the global lock order. | Session GUC `rhp.locked_referral` set after `SELECT * FROM referral WHERE id=$1 FOR UPDATE`; enforced by trigger `rhp_require_lock`. | `pg_stat_database.deadlocks` delta $> 0$ or `I14_LOCK_NOT_HELD` exception. | `T-I14`, `T-F1` |
| **I15** | Safety | No ownership lease is granted unless every required resource confirmation for `need_class` is present and unexpired (`expires_at > server_ts`). | Step 7 of `apply_command()` verifies `offer_resource_confirmation.expires_at > ts` under lock; returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`. | `OFFER_ACCEPTED` committed where $\min(\text{expires\_at}) \le \text{server\_ts}$. | `T-I15`, `T-F12` |
| **I16** | Safety | Authoritative `server_ts` is monotonically non-decreasing per referral despite host NTP clock steps. | `ts = GREATEST(clock_timestamp(), referral.head_ts)` computed under `referral` lock; enforced by `rhp_event_guard`. | `e.server_ts_us < st["ts"]` in event fold. | `T-I16`, `T-F11` |

---

## 3. State Machines & Two-Track Independence

### 3.1 Handshake Track, Offer Status Track, and Transport Track

The **Handshake Track** (`referral.hs_state`) governs destination ownership, while the **Transport Track** (`referral.tr_state`) governs physical patient movement. They execute in parallel: transport events never read `hs_state` and never block patient dispatch (`I3`).

- **Handshake States (`hs_state`):** `CREATED`, `OFFERED`, `ACKNOWLEDGED`, `ACCEPTED`, `COUNTERED`, `ESCALATED_TO_DISPATCHER`, `CANCELLED`, `CLOSED`.
- **Offer States (`offer.status`):** `OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`, `ACCEPTED`, `DECLINED`, `TIMED_OUT`, `SUPERSEDED`, `ARRIVAL_REJECTED`, `WITHDRAWN`.
  - *Open Offer Set (`I12`):* $\text{OPEN\_SET} = \{\text{OPEN}, \text{ACKED}, \text{COUNTERED}, \text{SOFT\_OPEN}\}$. Always $|\text{OPEN\_SET}| \le 2$.
  - `referral.hs_state` always reflects the **lead offer** (the highest `step` among open offers, or `ACCEPTED` when a lease is held).
- **Transport States (`tr_state`):** `REQUESTED` $\rightarrow$ `DISPATCHED` $\rightarrow$ `EN_ROUTE` $\rightarrow$ `ARRIVED` $\rightarrow$ `HANDED_OVER`, or `TR_CANCELLED` (from `REQUESTED`, `DISPATCHED`, or `EN_ROUTE`). Destination updates occur via `TR_DESTINATION_CHANGE` at any state prior to `ARRIVED`.

### 3.2 Problem Statement v7 to RHP-1 State Mapping [F19]

| v7 Conceptual State | `referral.hs_state` | `offer.status` | `referral.tr_state` | Committed `event.type` |
|---|---|---|---|---|
| `CREATED` | `CREATED` (transient inside `CREATE` txn) | — | `REQUESTED` | `REFERRAL_CREATED` |
| `OFFERED` | `OFFERED` | `OPEN` | any | `OFFER_CREATED` |
| `ACKNOWLEDGED` | `ACKNOWLEDGED` | `ACKED` | any | `OFFER_ACKED` |
| `ACCEPTED` | `ACCEPTED` | `ACCEPTED` | any | `OFFER_ACCEPTED`, `LEASE_GRANTED` |
| `COUNTERED` | `COUNTERED` | `COUNTERED` | any | `OFFER_COUNTERED` |
| `DECLINED` | `OFFERED` or `ESCALATED_TO_DISPATCHER` (post-`advance()`) | `DECLINED` | any | `OFFER_DECLINED` |
| `TIMED_OUT` | `OFFERED` or `ESCALATED_TO_DISPATCHER` (post-`advance()`) | `TIMED_OUT` or `SOFT_OPEN` | any | `DEADLINE_TIMEOUT` |
| `ESCALATED` | `OFFERED` (`ladder_cursor + 1`) | next offer `OPEN` | any | `OFFER_CREATED` (`reason='ESCALATION'`) |
| `ARRIVAL_REJECTED` | `OFFERED` or `ESCALATED_TO_DISPATCHER` | `ARRIVAL_REJECTED` | `ARRIVED` | `ARRIVAL_REJECTED`, `LEASE_REVOKED` |
| `ESCALATED_TO_DISPATCHER` | `ESCALATED_TO_DISPATCHER` | — | any | `ESCALATED_TO_DISPATCHER` |
| `CANCELLED` | `CANCELLED` | `WITHDRAWN` | any / `TR_CANCELLED` | `CANCELLED` |
| `CLOSED` | `CLOSED` | — | `HANDED_OVER` or outcome-specific | `CLOSED` |

### 3.3 Reachability & Deterministic Exit Table [F6]

Every non-terminal state has a deterministic, timer-bounded path to a terminal state (`CLOSED` or `CANCELLED`):

| State | Reachable From `CREATED` Via | Deterministic Exit to Terminal State |
|---|---|---|
| `CREATED` | Initial state | Atomic `CREATE` transaction transitions immediately to `OFFERED` (if `cardinality(chain) >= 1`) or `ESCALATED_TO_DISPATCHER` (if `chain` is empty). |
| `OFFERED` | `CREATE` | `ACCEPT` $\rightarrow$ `ACCEPTED` $\rightarrow$ `CLOSE`; or silence/decline through at most $F$ facilities ($\le T_{max}$) $\rightarrow$ `ESCALATED_TO_DISPATCHER` $\rightarrow$ `CLOSE`/`CANCEL`; or `CANCEL`. |
| `ACKNOWLEDGED` | `ACK` | Bounded by `DECISION` deadline ($\le D$); exits via `ACCEPT`, `DECLINE`, `COUNTER`, `TIMEOUT`, or `CANCEL`. |
| `COUNTERED` | `COUNTER` | Bounded by `COUNTER_CONFIRM` deadline ($\le \min(C, \text{remaining } D)$) and `counter_round <= 2`; exits via `CONFIRM_COUNTER`, `TIMEOUT`, or `CANCEL`. |
| `ACCEPTED` | `ACCEPT` / `DISPATCHER_ASSIGN` | `HANDOVER` deadline fires `HANDOVER_OVERDUE` pages (re-armed) until `HANDED_OVER`; `HANDED_OVER` arms `CLOSURE` deadline (fires `CLOSURE_OVERDUE` once, then auto-closes with `UNKNOWN_COUNTER_REFERRAL` on second expiry); or `ARRIVAL_REJECTED` / `CANCEL`. |
| `ESCALATED_TO_DISPATCHER` | Chain exhausted | `DISPATCH_ACTION` deadline pages dispatcher repeatedly until `DISPATCHER_ASSIGN`, `CLOSE`, or `CANCEL`. |
| `CLOSED`, `CANCELLED` | Terminal states | — |

### 3.4 Arrival Semantics [F5] & Soft-Open / Parallel-2 Rules [F13]

**Six Arrival Cases [F5]:**
- **(a) Arrival at lease holder:** Android/PWA $200\text{ m}$ geofence + dwell time emits `ARRIVAL_SUGGESTED` only. Human EMT or receiving desk must confirm `TR_UPDATE(ARRIVED)`.
- **(b) Arrival at facility with `OPEN`, `ACKED`, or `SOFT_OPEN` offer:** Receiving desk may execute `ACCEPT` immediately, provided all `need_class_requirement` capabilities are confirmed and unexpired (`I15`).
- **(c) Unannounced arrival at facility with no offer:** Emits `ARRIVAL_AT_NON_OWNER` urgent alert and pages dispatcher; never blocks clinical treatment; dispatcher may issue `DISPATCHER_ASSIGN`.
- **(d) En-route destination change:** Crew or dispatcher issues `TR_DESTINATION_CHANGE` with mandatory reason enum; the system never autonomously reroutes a moving ambulance.
- **(e) Crew refuses redirect advisory:** `TR_DESTINATION_CHANGE(accepted=false)` is logged; ownership lease remains unchanged; dispatcher is paged.
- **(f) Ambulance past highway turn-off:** Redirect advisory displays detour ETA from cached Mapbox Matrix; crew decides; if continuing to original facility, handled as Case (c) upon arrival.

**Offer Cap, Soft-Open & Counter Rules [F13]:**
1. **Strict Cap (`I12`):** `open_offers` $\in \{0, 1, 2\}$ always.
2. **Sequential Soft-Open (`SEQUENTIAL` mode):** When step $k$ times out without decision and step $k+1$ is offered, offer $k$ transitions to `SOFT_OPEN` ($k$ `SOFT_OPEN` + $k+1$ `OPEN` $= 2$ open offers).
   - If $k$ submits `ACCEPT` before $k+1$ submits `ACK`, $k$ wins the lease and $k+1$ becomes `SUPERSEDED`.
   - As soon as $k+1$ commits `ACK`, $k$ transitions from `SOFT_OPEN` to `TIMED_OUT`; any subsequent `ACCEPT` from $k$ receives `409 LATE_ACCEPT_REJECTED`.
   - If $k+1$ also times out and $k+2$ is offered while $k$ is still `SOFT_OPEN`, $k$ transitions to `TIMED_OUT` immediately so $k+1$ (`SOFT_OPEN`) and $k+2$ (`OPEN`) preserve `open_offers <= 2`.
3. **Parallel-2 Mode (`PARALLEL2`):** Offers to `chain[0]` and `chain[1]` open simultaneously (`open_offers = 2`). On timeout, a `PARALLEL2` offer goes directly to `TIMED_OUT` (no `SOFT_OPEN`) before the next chain target opens.
4. **Counter-Offers:** Allowed up to `counter_round <= 2`. `COUNTER_CONFIRM` deadline is set to $\min(C, \text{remaining } D)$ so counter-offers never extend a facility's decision window $D$. If another open offer commits `ACCEPT` while an offer is `COUNTERED`, the `ACCEPT` wins under the referral lock and the `COUNTERED` offer becomes `SUPERSEDED`.

---

## 4. Command Pipeline, Global Lock Order & Background Workers

### 4.1 Global Lock Order Proof [F1, I14]

To guarantee deadlock freedom (`deadlocks_delta == 0` under 200-way concurrency), all multi-table transactions acquire row locks in one strict global hierarchy:

$$\text{referral} \longrightarrow \text{offer } (\text{ORDER BY id}) \longrightarrow \text{deadline } (\text{ORDER BY id}) \longrightarrow \text{outbox}$$

| Execution Path | Locks Acquired (in exact order) | Waits While Holding a Lock? |
|---|---|---|
| `apply_command()` | `pg_try_advisory_xact_lock` (non-blocking) $\rightarrow$ `referral` (`FOR UPDATE`) $\rightarrow$ `offer` (`ORDER BY id FOR UPDATE`) $\rightarrow$ `deadline` (`ORDER BY id FOR UPDATE`) $\rightarrow$ `outbox` (`INSERT`) | Only forward along the global hierarchy. |
| Poller Phase 1 (`tick`) | Claims due `deadline` rows via a single `UPDATE ... WHERE id IN (SELECT ... ORDER BY due_at LIMIT 50 FOR UPDATE SKIP LOCKED)` statement and **commits immediately**. | Never waits (`SKIP LOCKED`), holds zero locks across Phase 2. |
| Poller Phase 2 | Invokes `apply_command(TIMEOUT)` for each claimed deadline in a fresh transaction. | Identical to `apply_command()` (`referral` locked first). |
| Outbox Relay | Claims `outbox` rows via a single `UPDATE ... FOR UPDATE SKIP LOCKED` statement and commits. | Never waits (`SKIP LOCKED`). |
| Monitor & Witness | Connects with `REPEATABLE READ READ ONLY` transaction isolation. | Acquires zero row locks. |

Database trigger `rhp_require_lock` enforces `current_setting('rhp.locked_referral', true) = referral_id` on every contract-state write (`referral`, `offer`, `deadline` status/due_at, `event`, `payload_grant`, and `outbox` `INSERT`). Delivery bookkeeping (`outbox.status/attempts/visible_after` `UPDATE` and `deadline.claimed_until` `UPDATE`) is explicitly exempted in `rhp_require_lock` because it mutates no contract state.

### 4.2 The 10-Step `apply_command()` Pipeline

```python
import hashlib
import json
import psycopg

def jcs(obj: dict) -> bytes:
    """RFC 8785 canonical JSON subset: ASCII keys, int/str/bool values only (no floats)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def apply_command(conn: psycopg.Connection, cmd, sess, idem_key: str):
    if not idem_key or not (8 <= len(idem_key) <= 80):
        return http(422, "MISSING_IDEMPOTENCY_KEY")

    # STEP 1: IDEMPOTENCY (executed BEFORE acquiring any referral lock)
    req_hash = sha256(jcs(cmd.body_for_hash()))
    with conn.transaction():
        locked = conn.execute(
            "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"{sess.roster_id}:{idem_key}",)
        ).fetchone()[0]
        if not locked:
            return http(409, "DUPLICATE_IN_FLIGHT")

        row = conn.execute(
            "SELECT request_hash, status, http_status, response FROM idempotency "
            "WHERE actor_id = %s AND key = %s AND expires_at > clock_timestamp()",
            (sess.roster_id, idem_key)
        ).fetchone()
        if row:
            if bytes(row.request_hash) != req_hash:
                return http(422, "KEY_REUSED_DIFFERENT_PAYLOAD")
            if row.status == "DONE":
                return http(row.http_status, row.response)

        conn.execute(
            "INSERT INTO idempotency(actor_id, key, request_hash, status, created_at, expires_at) "
            "VALUES (%s, %s, %s, 'IN_FLIGHT', clock_timestamp(), clock_timestamp() + interval '48 hours') "
            "ON CONFLICT (actor_id, key) DO UPDATE SET "
            "request_hash = EXCLUDED.request_hash, status = 'IN_FLIGHT', "
            "created_at = clock_timestamp(), expires_at = clock_timestamp() + interval '48 hours'",
            (sess.roster_id, idem_key, req_hash)
        )

        # STEP 2: SESSION VALIDATION (read-only lookup of opaque token / device / roster)
        s = load_session(conn, sess)
        if not s.valid:
            return http(401, "SESSION_INVALID")

        # STEP 3: PIN VERIFICATION (Argon2id; failure counter incremented on autonomous connection)
        if cmd.needs_pin:
            if s.pin_locked_until and s.pin_locked_until > s.now:
                return finalize(conn, sess.roster_id, idem_key, 429, {"reason": "PIN_LOCKED"})
            if not argon2_verify(s.pin_hash, cmd.pin):
                locked_now = autonomous_pin_failed(s.id, s.roster_id)
                code = 429 if locked_now else 403
                reason = "PIN_LOCKED" if locked_now else "PIN_INVALID"
                return finalize(conn, sess.roster_id, idem_key, code, {"reason": reason})

        # STEP 4: LOCK REFERRAL FIRST, STAMP GUC (I14), COMPUTE MONOTONE SERVER TIME (I16)
        r = lock_or_create_referral(conn, cmd, s)
        conn.execute("SELECT set_config('rhp.locked_referral', %s, true)", (str(r.id),))
        ts = conn.execute("SELECT GREATEST(clock_timestamp(), %s)", (r.head_ts,)).fetchone()[0]

        conn.execute("SAVEPOINT sp_cmd")
        try:
            # STEP 5: AUTHORITY & FENCING (roster active window, facility match, version & epoch)
            authorize(conn, r, s, cmd, ts)   # raises Reject(403, ...)
            fence(r, cmd)                    # raises Reject(412, "STALE_VERSION_OR_EPOCH")

            # STEP 6: TRANSITION GUARD (lock offers & deadlines in ID order; lookup transitions.yaml)
            offers = conn.execute(
                "SELECT * FROM offer WHERE referral_id = %s ORDER BY id FOR UPDATE", (r.id,)
            ).fetchall()
            deadlines = conn.execute(
                "SELECT * FROM deadline WHERE referral_id = %s AND status = 'PENDING' ORDER BY id FOR UPDATE",
                (r.id,)
            ).fetchall()
            transition = TRANSITIONS.lookup(cmd.type, r, offers, deadlines, cmd)

            # STEP 7: STALENESS & EXPIRY CHECKS (I15 resource confirmations & late-accept status)
            check_confirmations_and_staleness(conn, r, offers, cmd, ts)

            # STEP 8: APPLY STATE MUTATIONS (offers, lease_epoch, open_offers, grants, deadlines)
            effects = transition.apply(conn, r, offers, deadlines, cmd, ts)

            # STEP 9: APPEND HASH-CHAINED EVENT, SECRET CIPHERTEXT, AND OUTBOX ROWS
            ev = append_event(conn, r, cmd, s, effects, ts)
            insert_outbox_rows(conn, r, ev, effects, ts)

            # STEP 10: FINALIZE IDEMPOTENCY RECORD AND COMMIT
            return finalize(conn, sess.roster_id, idem_key, 200, ev.view())

        except Reject as exc:
            conn.execute("ROLLBACK TO SAVEPOINT sp_cmd")  # Retains referral lock & GUC
            conn.execute(
                "INSERT INTO rejected_command(actor_id, key, referral_id, command, http_status, reason_code, session_id, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (sess.roster_id, idem_key, r.id, cmd.type, exc.code, exc.reason, s.id, ts)
            )
            return finalize(conn, sess.roster_id, idem_key, exc.code, {"reason": exc.reason})
```

---

## 5. Timing Math, Signed Profiles & Clock Monotonicity

### 5.1 Unified Offer-ACK Window & Notice Ladder [F2]

Every facility offer runs a single unified ACK window of duration $A$ with deterministic notice rungs stored as `deadline` rows:
- **$t = 0$ (Offer `OPEN`):** Push SSE frame + empty-payload FCM wake ping concurrently to all rostered slots $S$ at the target facility.
- **$t = A/4$ (`NOTICE_VOICE`):** Outbound Exotel IVR calls to slot $i \in \{0, \dots, S-1\}$ staggered at $A/4 + i \cdot \delta$, each with call budget $V$.
- **$t = 3A/4$ (`NOTICE_PROXY`):** Dispatcher console proxy page (prompts phone-assisted check).
- **$t = A$ (`ACK` Deadline Expiry):** If unacknowledged, triggers `TIMEOUT(ACK)` (`SEQUENTIAL`: offer becomes `SOFT_OPEN` and next facility opens; if already `ACKED` but undecided at $t=A$, sends `ADVISORY_PREWARM` to next facility). Once `ACK` occurs at any time $t \le A$, the notice ladder is cancelled and a hard `DECISION` deadline of duration $D$ is armed.

### 5.2 Signed Timing Profiles & $T_{max}$ Derivation [F3, I13]

In the worst case at a single facility, a receiver acknowledges at $A - \epsilon'$ and then remains silent through the full decision window $D$ (counter-offers sit inside $D$), consuming $A + D$. Including per-hop poller/apply overhead $\epsilon$ across at most $F$ facilities:

$$T_{max} = F \cdot (A + D + \epsilon) \le B$$

Furthermore, when voice is enabled, the voice stagger must finish inside the notice ladder before $3A/4$:

$$\frac{A}{4} + (S - 1) \cdot \delta + V \le \frac{3A}{4}$$

| Parameter | `PILOT_OB_CRITICAL` | `PILOT_STANDARD` | `DEMO_FAST` | `DEMO_VOICE` |
|---|---|---|---|---|
| **ACK Window $A$ ($\text{ms}$)** | $60000$ ($60\text{ s}$) | $120000$ ($120\text{ s}$) | $3000$ ($3\text{ s}$) | $45000$ ($45\text{ s}$) |
| **Decision Window $D$ ($\text{ms}$)** | $180000$ ($180\text{ s}$) | $300000$ ($300\text{ s}$) | $4000$ ($4\text{ s}$) | $20000$ ($20\text{ s}$) |
| **Notice Rungs ($0, A/4, 3A/4$ $\text{ms}$)** | $0 / 15000 / 45000$ | $0 / 30000 / 90000$ | $0 / 750 / 2250$ | $0 / 11250 / 33750$ |
| **Slots $S$, Stagger $\delta$, Voice Budget $V$ ($\text{ms}$)** | $3, 5000, 20000$ | $3, 10000, 20000$ | $3, 0, \text{off}$ | $1, 0, 20000$ |
| **Max Facilities $F$** | $3$ | $3$ | $3$ | $2$ |
| **Hop Overhead $\epsilon$ ($\text{ms}$)** | $3000$ ($3\text{ s}$) | $3000$ ($3\text{ s}$) | $1000$ ($1\text{ s}$) | $1000$ ($1\text{ s}$) |
| **Counter Confirm $C$ ($\text{ms}$)** | $90000$ | $150000$ | $2000$ | $10000$ |
| **Resource Confirm TTL `confirm_ttl` ($\text{ms}$)** | $120000$ | $180000$ | $10000$ | $60000$ |
| **`HANDOVER` / `DISPATCH_ACTION` / `CLOSURE` ($\text{ms}$)** | $7200000 / 300000 / 86400000$ | $7200000 / 300000 / 86400000$ | $30000 / 5000 / 20000$ | $60000 / 10000 / 60000$ |
| **Computed $T_{max} = F \cdot (A + D + \epsilon)$** | $3 \cdot 243\text{ s} = 729\text{ s}$ | $3 \cdot 423\text{ s} = 1269\text{ s}$ | $3 \cdot 8\text{ s} = 24\text{ s}$ | $2 \cdot 66\text{ s} = 132\text{ s}$ |
| **Hard Upper Bound $B$ ($\text{ms}$)** | $900000$ ($900\text{ s}$) | $1500000$ ($1500\text{ s}$) | $25000$ ($25\text{ s}$) | $150000$ ($150\text{ s}$) |
| **Allowed When `REAL_DATA=1`?** | Yes | Yes | **No (Refuses Boot)** | **No (Refuses Boot)** |

---

## 6. F1–F20 Architectural Closure Traceability

| Fix ID | v4/v5 Defect Closed | Exact Architectural Mechanism | Verification Test |
|---|---|---|---|
| **F1** | Poller held deadline locks across commands | Global lock order `referral > offer > deadline > outbox`; 2-phase poller; `rhp_require_lock` trigger (`I14`). | `T-F1` (`lock_order_200way`) |
| **F2** | Notice ladder raced offer ACK | Notice rungs at $0, A/4, 3A/4$ inside ACK window $A$; 4 signed profiles; demo profiles abort if `REAL_DATA=1`. | `T-F2` (`profile_guard`) |
| **F3** | $T_{max}$ double-counted slots & was unbounded | Concurrent slot notification; $T_{max} = F \cdot (A + D + \epsilon) \le B$ enforced at startup (`I13`). | `T-F3` (`tmax_validator`) |
| **F4** | Incomplete DDL | Complete 24-table PostgreSQL 16 DDL with `one_lease`, deferred FKs, CHECKs, and append-only triggers. | `T-F4` (`ddl_load_fk_scan`) |
| **F5** | Ambiguous arrival handling | 6 explicit arrival cases (a)–(f); $200\text{ m}$ geofence emits `ARRIVAL_SUGGESTED` only; human confirms `ARRIVED`. | `T-F5` (`arrival_cases`) |
| **F6** | Unclosed referrals / dead ends | Reachability & Exit table; 9 outcome enums; 2-stage `CLOSURE` deadline auto-closing with `UNKNOWN_COUNTER_REFERRAL`. | `T-F6` (`reachability_bfs`) |
| **F7** | PIN lockout DoS & voicemail false ACK | Single-use `enrollment_ticket` $\rightarrow$ device key $\rightarrow$ opaque session; autonomous Argon2id failure counter scoped per `session_id`/`call_sid`; AMD + press-1 gate. | `T-F7` (`pin_lockout_scope`) |
| **F8** | Witness & backup restore ambiguity | Separate-OS-user Ed25519 signer (`rhp-sign`); binary Merkle inclusion proofs; cold-key signed `RESTORE` checkpoint. | `T-F8` (`tamper_vs_restore`) |
| **F9** | Free-text PHI risk in `event.detail` | Per-type key allowlist (`rhp_allowed`) + regex value check (`rhp_detail_ok`); 4-hour export buckets + $k \ge 5$ suppression (`I11`). | `T-F9` (`detail_check_fuzz`) |
| **F10** | SSE streams outlived revoked grants | Per-frame `payload_grant` authorization check + immediate `GRANT_REVOKED` control frame (`I10`). | `T-F10` (`sse_revoke`) |
| **F11** | Host clock steps broke event order | `GREATEST(clock_timestamp(), referral.head_ts)` under referral lock (`I16`); chrony slew-only; $> 2\text{ s}$ NTP offset alarm. | `T-F11` (`clock_step`) |
| **F12** | Stale offline `ACCEPT` granted lease | Online `RESOURCE_CONFIRM` with `expires_at`; step 7 rejects expired confirmations with `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` (`I15`). | `T-F12` (`offline_stale`) |
| **F13** | Open-offer count undefined | `open_offers CHECK (open_offers BETWEEN 0 AND 2)` (`I12`); explicit `SOFT_OPEN`, `PARALLEL2`, and `COUNTER` overlap rules. | `T-F13` (`open_cap`) |
| **F14** | Replay edge cases undefined | Step 1 idempotency with `pg_try_advisory_xact_lock`, `(actor_id, key)` scope, `request_hash`, and 8-case replay matrix. | `T-F14` (`idem_matrix`) |
| **F15** | Unbounded "none" residuals in matrix | Every failure-matrix row carries a concrete technical bound, reason, and status (`CLOSED`, `BOUNDED`, `OPEN`). | `T-F15` (`residual_lint`) |
| **F16** | Vague demo scope | Tiers T0–T3 behind feature flags; second-by-second 30-second live proof loop on `DEMO_FAST`. | `T-F16` (`loop_rehearsal`) |
| **F17** | Common-mode bug between spec & monitor | Person A writes server/`transitions.yaml`/`rhp1.qnt`; Person B writes `monitor/monitor.py` from prose alone; verified by 6 mutation tests (M1–M6). | `T-F17` (`mutation_suite`) |
| **F18** | Conflicting pilot cloud cost figures | Single reconciled 6-month AWS `ap-south-1` Multi-AZ cost table ($\approx \$1,419$ for 6 months). | `T-F18` (`cost_recompute`) |
| **F19** | Implicit v7-to-RHP-1 state mapping | Explicit 12-state mapping table tying v7 states to `hs_state`, `offer.status`, `tr_state`, and `event.type`. | `T-F19` (`v7_map`) |
| **F20** | `BROKEN_BUILD` risk near real data | Isolated `rhp_scratch_broken` DB without `one_lease`; hard abort (exit 78) if `REAL_DATA=1` or non-scratch DSN; flashing red UI banner. | `T-F20` (`broken_isolation`) |

---

## 7. Tiers T0–T3 & Multi-Agent File-Ownership Boundaries

| Tier | Feature Flag | Scope & Deliverables | Cut Precedence |
|---|---|---|---|
| **T0 (Core & Proof)** | Always On | FastAPI `apply_command()`, PostgreSQL 16 DDL, 2-phase poller, outbox relay, React PWA desks with rotating QR, independent Python monitor, witness/signer + browser verifier, `BROKEN_BUILD` scratch DB. | **Never Cut** |
| **T1 (Transport & Proxy)** | `T1_TRANSPORT=1` | PWA ambulance foreground GPS client, dispatcher console with proxy entry and override, time-scrubber replay view. | Cut 3rd |
| **T2 (Reach Layer)** | `T2_REACH=1` | Outbound Exotel IVR with AMD + press-1 gate, DLT-compliant SMS alert stub, Crockford Base32 + mod-37 paper code linking. | Cut 2nd |
| **T3 (Extras)** | `T3_EXTRAS=1` | Native Android Kotlin foreground location app, AI intake accelerator with Cognitive Forcing Functions, FHIR R4 & XES exporters. | Cut 1st |

**CODEOWNERS & Common-Mode Isolation Rules (`F17`):**
- `/spec/**` (`transitions.yaml`, `rhp1.qnt`, conformance vectors, signed profiles) and `/db/schema.sql` are **READ-ONLY** to automated builder tasks unless an explicit human-approved `SPEC-DEVIATION` is logged.
- **Lane A (Person A):** Owns `/api/**`, `/db/**`, `/spec/**`, and `/witness/**`.
- **Lane B (Person B):** Owns `/monitor/**`, `/pwa/**`, and `/android/**`. The `/monitor/**` workspace must never import `/api/**` modules and connects exclusively via the read-only PostgreSQL role `rhp_monitor`.