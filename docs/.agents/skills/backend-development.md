---
name: backend-development
description: Enforce ReferralHandshake (RHP-1) backend engineering rules for Python 3.12, FastAPI, psycopg3, the 10-step apply_command() pipeline, two-phase deadline poller, visibility-timeout outbox relay, Exotel IVR webhooks, and witness checkpoint signing.
owner_lane: Lane A (Core / Poller / Relay / Witness) & Lane B (Reach Adapters)
tier_scope: T0, T1, T2, T3
spec_anchors:
  - ReferralHandshake_FINAL_LOCKED_Architecture.md (§0, §3, §4, §5, §6, §8, §9, §10, §11, §16)
  - ReferralHandshake_v8_LOCKED_Solution.md (§3, §4, §5, §6, §8)
  - ReferralHandshake_LOCKED_Problem_Statement_v7.md (§5, §6)
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
  - spec/transitions.yaml
  - spec/rhp1.qnt
  - db/schema.sql
  - monitor/
---

# RHP-1 Backend Development Skill (`backend-development`)

## 1. Mission & Coherence Rule
You are building the **ReferralHandshake (Protocol RHP-1)** backend in **Python 3.12**, **FastAPI**, **psycopg3**, and **Pydantic v2 (`extra='forbid'`)** backed by a single writable **PostgreSQL 16** primary (`synchronous_commit=on`, `READ COMMITTED`).

**The Coherence Rule (Non-Negotiable):** Every backend module, endpoint, and background worker you write must be strictly one of:
1. **(a)** A state or event transition in the RHP-1 contract executed exclusively through `apply_command()`,
2. **(b)** An interface adapter producing or consuming those events (REST API, SSE hub, Exotel voice webhook, FCM wake adapter, DLT SMS adapter, Paper code resolver), or
3. **(c)** A read-only projection of the committed event log (Witness/Signer, FHIR R4 exporter, XES exporter, KPI aggregator).

Anything outside (a), (b), or (c) is out of scope and forbidden.

---

## 2. Locked Stack & Banned Technologies

| Category | Locked Implementation | Strictly Banned (Immediate Audit Reject) |
|---|---|---|
| Runtime & Web | Python 3.12, FastAPI, Uvicorn, Pydantic v2 (`ConfigDict(extra='forbid')`) | Django, Flask, GraphQL, WebSockets, gRPC |
| Database Driver | `psycopg` (v3) synchronous/async pool, explicit SQL transactions (`READ COMMITTED`) | SQLAlchemy ORM magic, Django ORM, SQLite, Redis, MongoDB |
| Concurrency & Locks | Per-referral `SELECT ... FOR UPDATE`, `pg_try_advisory_xact_lock`, `FOR UPDATE SKIP LOCKED` | Distributed locks (Redlock/ZooKeeper), global file locks, CRDTs for contract state |
| Messaging & Queue | Same-transaction PostgreSQL `outbox` + `inbox` tables, SSE (`Last-Event-ID`) | Kafka, Debezium, RabbitMQ, Celery, WhatsApp APIs |
| Canonical JSON | RFC 8785 JCS subset (ASCII keys, `int`, `str`, `bool` only; **zero floats**) | Floating-point numbers in canonical JSON payloads or event details |
| Cryptography | `cryptography` (AES-256-GCM, AES-KW, Ed25519), `argon2-cffi` (Argon2id), `hashlib.sha256` | Blockchain, smart contracts, custom unverified primitives |

---

## 3. Global Lock Order & Concurrency Discipline (F1 / I14)

Every transaction in the backend that touches contract state **must** acquire locks in this strict total order:

$$\text{referral} \longrightarrow \text{offer (ORDER BY id)} \longrightarrow \text{deadline (ORDER BY id)} \longrightarrow \text{outbox}$$

### 3.1 Lock Order Rules across All Paths
| Execution Path | Lock Acquisition Sequence | Waits While Holding Another Lock? |
|---|---|---|
| `apply_command()` | 1. `pg_try_advisory_xact_lock(hashtextextended(actor:key, 0))` (non-blocking)<br>2. `SELECT * FROM referral WHERE id = %s FOR UPDATE`<br>3. `SELECT set_config('rhp.locked_referral', id::text, true)`<br>4. `SELECT * FROM offer WHERE referral_id = %s ORDER BY id FOR UPDATE`<br>5. `SELECT * FROM deadline WHERE referral_id = %s ORDER BY id FOR UPDATE`<br>6. `INSERT INTO outbox ...` | Only forward in the global order. Never locks more than one referral per transaction. |
| Poller Phase 1 | Single statement: `UPDATE deadline SET claimed_until = ... WHERE id IN (... FOR UPDATE SKIP LOCKED) RETURNING ...` committed immediately. | **No.** Skips locked rows and commits before Phase 2. |
| Poller Phase 2 | Invokes `apply_command(TimeoutCmd)` per claimed deadline in a fresh transaction. | Same as `apply_command()` (locks `referral` first). |
| Outbox Relay | Single statement: `UPDATE outbox SET visible_after = ... WHERE id IN (... FOR UPDATE SKIP LOCKED) RETURNING *` committed immediately. | **No.** Delivery bookkeeping is exempt from `rhp_require_lock`. |
| Monitor & Witness | `REPEATABLE READ READ ONLY` transaction snapshot. | **No.** Zero row locks taken. |

> **CRITICAL (I14 Enforcement):** PostgreSQL trigger `rhp_require_lock` fires `BEFORE INSERT OR UPDATE` on `referral`, `offer`, `deadline` (when `status` or `due_at` changes), `event`, `payload_grant`, and `outbox` (on `INSERT`). If `current_setting('rhp.locked_referral', true)` does not equal the target `referral_id`, PostgreSQL raises `I14_LOCK_NOT_HELD`. Never write to these tables outside `apply_command()`.

---

## 4. The 10-Step `apply_command()` Pipeline (§5)

All 14 contract commands (`CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `COUNTER`, `CONFIRM_COUNTER`, `DECLINE`, `TIMEOUT`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`, `TR_UPDATE`, `CANCEL`, `CLOSE`, `REVOKE_GRANT`) must execute through this exact 10-step pipeline:

```python
import hashlib
import json
from dataclasses import dataclass
from typing import Any
import psycopg
from psycopg.rows import namedtuple_row

def jcs(obj: dict[str, Any]) -> bytes:
    """RFC 8785 JCS canonicalizer for RHP-1 (ASCII keys, int/str/bool only; floats forbidden)."""
    def _check(v: Any) -> None:
        if isinstance(v, float):
            raise ValueError("FLOATS_FORBIDDEN_IN_JCS")
        if isinstance(v, dict):
            for k, val in v.items():
                if not isinstance(k, str) or not k.isascii():
                    raise ValueError("NON_ASCII_KEY_IN_JCS")
                _check(val)
        elif isinstance(v, list):
            for item in v:
                _check(item)
    _check(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

class Reject(Exception):
    def __init__(self, code: int, reason: str, detail: dict[str, Any] | None = None):
        self.code = code
        self.reason = reason
        self.detail = detail or {"error": reason}

def apply_command(
    conn: psycopg.Connection,
    cmd: Any,
    sess: Any,
    idem_key: str,
    autonomous_dsn: str,
) -> tuple[int, dict[str, Any]]:
    """
    Executes a single RHP-1 contract command under READ COMMITTED isolation.
    Strictly enforces Steps 1-10 from Architecture §5.
    """
    if not idem_key or not (8 <= len(idem_key) <= 80):
        return 422, {"error": "MISSING_IDEMPOTENCY_KEY"}

    req_hash = sha256_bytes(jcs(cmd.body_for_hash()))
    lock_key = f"{sess.roster_id}:{idem_key}"

    with conn.transaction():
        conn.row_factory = namedtuple_row

        # STEP 1: IDEMPOTENCY (Before any referral lock)
        locked = conn.execute(
            "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))",
            (lock_key,),
        ).fetchone()[0]
        if not locked:
            return 409, {"error": "DUPLICATE_IN_FLIGHT"}

        row = conn.execute(
            """
            SELECT request_hash, status, http_status, response
              FROM idempotency
             WHERE actor_id = %s AND key = %s
            """,
            (sess.roster_id, idem_key),
        ).fetchone()

        if row is not None:
            if bytes(row.request_hash) != req_hash:
                return 422, {"error": "KEY_REUSED_DIFFERENT_PAYLOAD"}
            if row.status == "DONE":
                return row.http_status, row.response

        conn.execute(
            """
            INSERT INTO idempotency (actor_id, key, request_hash, status, created_at, expires_at)
            VALUES (%s, %s, %s, 'IN_FLIGHT', clock_timestamp(), clock_timestamp() + interval '48 hours')
            ON CONFLICT (actor_id, key) DO UPDATE SET status = 'IN_FLIGHT'
            """,
            (sess.roster_id, idem_key, req_hash),
        )

        # STEP 2: SESSION VALIDATION (Read-only check on session/device/roster)
        s = load_and_check_session(conn, sess)
        if not s.valid:
            return finalize_idempotency(conn, sess.roster_id, idem_key, 401, {"error": "SESSION_INVALID"})

        # STEP 3: PIN VERIFICATION (Argon2id; failure counter on SEPARATE autonomous connection)
        if cmd.needs_pin:
            if s.pin_locked_until and s.pin_locked_until > s.now:
                return finalize_idempotency(conn, sess.roster_id, idem_key, 429, {"error": "PIN_LOCKED"})
            if not argon2_verify(s.pin_hash, cmd.pin):
                autonomous_pin_failed(autonomous_dsn, s.id, cmd.referral_id, sess.roster_id)
                return finalize_idempotency(conn, sess.roster_id, idem_key, 403, {"error": "PIN_INVALID"})

        # STEP 4: LOCK REFERRAL FIRST, STAMP SESSION GUC, COMPUTE MONOTONE SERVER TIMESTAMP (I14, I16)
        if cmd.type == "CREATE":
            conn.execute("SELECT set_config('rhp.locked_referral', %s, true)", (str(cmd.referral_id),))
            ts = conn.execute("SELECT clock_timestamp()").fetchone()[0]
            r = create_initial_referral_row(conn, cmd, s, ts)
        else:
            r = conn.execute(
                "SELECT * FROM referral WHERE id = %s FOR UPDATE",
                (cmd.referral_id,),
            ).fetchone()
            if r is None:
                return finalize_idempotency(conn, sess.roster_id, idem_key, 409, {"error": "REFERRAL_NOT_FOUND"})
            conn.execute("SELECT set_config('rhp.locked_referral', %s, true)", (str(r.id),))
            ts = conn.execute("SELECT GREATEST(clock_timestamp(), %s)", (r.head_ts,)).fetchone()[0]

        conn.execute("SAVEPOINT sp_cmd")
        try:
            # STEP 5: AUTHORITY & FENCING (Roster active at ts, facility match, version -> 412, epoch -> 409/412)
            authorize_actor(conn, r, s, cmd, ts)
            fence_version_and_epoch(r, cmd)

            # STEP 6: TRANSITION GUARD (From transitions.yaml; lock offers then deadlines in ID order)
            offers = conn.execute(
                "SELECT * FROM offer WHERE referral_id = %s ORDER BY id FOR UPDATE",
                (r.id,),
            ).fetchall()
            deadlines = conn.execute(
                "SELECT * FROM deadline WHERE referral_id = %s ORDER BY id FOR UPDATE",
                (r.id,),
            ).fetchall()
            transition = lookup_transition(cmd, r, offers, deadlines)

            # STEP 7: STALENESS & CONFIRMATIONS (I15 confirmation expiry; offer status for offline ACCEPT)
            check_resource_confirmations_and_staleness(conn, r, offers, cmd, ts)

            # STEP 8: APPLY EFFECTS (Offers, lease_epoch, grants, deadlines WHERE id=$1 AND status='PENDING')
            effects = transition.apply(conn, r, offers, deadlines, cmd, s, ts)

            # STEP 9: APPEND HASH-CHAINED EVENT(S) & OUTBOX ROWS (Outbox written last)
            ev_view = append_events_and_outbox(conn, r, cmd, s, effects, ts)

            # STEP 10: FINALIZE IDEMPOTENCY ROW & COMMIT
            return finalize_idempotency(conn, sess.roster_id, idem_key, 200, ev_view)

        except Reject as exc:
            # Rollback partial state mutations while keeping referral row lock and idempotency row
            conn.execute("ROLLBACK TO SAVEPOINT sp_cmd")
            conn.execute(
                """
                INSERT INTO rejected_command
                    (actor_id, key, referral_id, command, http_status, reason_code, session_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (sess.roster_id, idem_key, r.id, cmd.type, exc.code, exc.reason, s.id, ts),
            )
            return finalize_idempotency(conn, sess.roster_id, idem_key, exc.code, exc.detail)
```

---

## 5. Exact Semantics for Tracks, Leases, Offers & Deadlines

### 5.1 Two Independent Tracks (I3 & D1/D2)
1. **Transport Never Reads `hs_state`:** `TR_UPDATE` and `TR_DESTINATION_CHANGE` handlers must **never** branch on or reject because of `referral.hs_state` (except rejecting if `hs_state IN ('CLOSED', 'CANCELLED')`).
2. **Geofence Is Only a Hint (F5):** Automatic GPS proximity ($200\text{ m}$ + dwell) may only emit `ARRIVAL_SUGGESTED`. Transitioning `tr_state` to `ARRIVED` requires a human actor (`EMT`, `NURSE`, `CMO`, `CONSULTANT`, or `DISPATCHER`).
3. **$\text{MgSO}_4$ Status Never Blocks Care (D1):** `mgso4_status` (`GIVEN`, `NONE_GIVEN`, `UNKNOWN`) is answer-required, never knowledge-required. `UNKNOWN` is completely valid at `CREATE` and sets a red verification banner on the receiving desk without delaying offer creation or ambulance dispatch.

### 5.2 Separate `version` and `lease_epoch` (D7 / I2 / I8)
* **`referral.version`:** Increments by 1 on every state-changing command. If `cmd.expected_version != referral.version`, raise `Reject(412, "STALE_VERSION")` and log to `rejected_command`.
* **`referral.lease_epoch`:** Monotonically increments by 1 on every ownership change (`ACCEPT`, `CONFIRM_COUNTER(true)`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`).
* **Lost Race vs Stale Precondition:** When two facilities race to `ACCEPT` at the same valid preconditions or an offer is no longer open due to a peer winning the lease, return `409 LEASE_HELD` or `409 LATE_ACCEPT_REJECTED`—never `412`.

### 5.3 Open-Offer Cap, Soft-Open & Counter Rules (F13 / I12)
* **Open Statuses:** `OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`. `referral.open_offers` must equal the count of offers in these 4 statuses and satisfies `CHECK (open_offers BETWEEN 0 AND 2)`.
* **`SEQUENTIAL` Mode Overlap:**
  * Steady state = 1 `OPEN` offer.
  * When offer $k$ times out (`ACK` or `DECISION`), if target $k+1$ exists in `referral.chain`, offer $k$ transitions to `SOFT_OPEN` and offer $k+1$ opens as `OPEN` (`open_offers = 2`).
  * **Cap Preservation:** If offer $k-1$ is still `SOFT_OPEN` when offer $k+1$ opens, offer $k-1$ immediately transitions to `TIMED_OUT` so `open_offers` never exceeds 2.
  * **Late-Accept Resolution:** If facility $k$ (`SOFT_OPEN`) sends `ACCEPT` *before* facility $k+1$ sends `ACK`, facility $k$ wins the lease and offer $k+1$ becomes `SUPERSEDED`. Once facility $k+1$ sends `ACK`, offer $k$ immediately transitions from `SOFT_OPEN` to `TIMED_OUT`, and any late `ACCEPT` from $k$ is rejected with `409 LATE_ACCEPT_REJECTED`.
* **`PARALLEL2` Mode:**
  * Opens `chain[0]` and `chain[1]` simultaneously (`open_offers = 2`).
  * Timed-out offers in `PARALLEL2` transition directly to `TIMED_OUT` (no `SOFT_OPEN`) and open the next unused chain target.
* **`COUNTER` Rules:**
  * Maximum 2 counter rounds per offer (`counter_round BETWEEN 0 AND 2`).
  * Replaces the offer's `DECISION` deadline with `COUNTER_CONFIRM` due at $\min(C, \text{remaining } D)$ so counter-offers never extend the facility decision window $D$.

---

## 6. Stateless Workers: Poller, Outbox Relay & Witness Signer

### 6.1 Two-Phase Deadline Poller (F1)
Never hold a `deadline` lock while calling `apply_command()`.
* **Phase 1:** Claim up to 50 due rows in a single autocommitted `UPDATE ... FOR UPDATE SKIP LOCKED` statement setting `claimed_until = clock_timestamp() + interval '5 seconds'`.
* **Phase 2:** Loop over claimed rows and invoke `apply_command(conn, TimeoutCmd(...), SYSTEM_SESSION, idem_key=f"timeout:{d.id}")`. Inside `TIMEOUT`, re-verify `deadline.status == 'PENDING'` and matching `step`/`epoch` under the referral lock; if already `DONE` or `CANCELLED`, return `200` no-op.

### 6.2 Outbox Relay & Stream Revocation (F10 / I10)
* Claim pending `outbox` rows via `FOR UPDATE SKIP LOCKED` with a 30-second visibility timeout (`visible_after = clock_timestamp() + interval '30 seconds'`, `attempts = attempts + 1`).
* After adapter delivery, mark `status = 'SENT'`. If `attempts > 8`, mark `status = 'DEAD'` and page the dispatcher.
* **Per-Event SSE Authorization (I10):** Before emitting any SSE frame containing clinical data, check that the subscriber's `(facility_id, role_slot)` holds an active, unrevoked `payload_grant` (`revoked_at IS NULL`) at emit time and re-verify on every 15-second heartbeat. When `GRANT_REVOKED` occurs, push the `GRANT_REVOKED` control frame immediately and strip clinical fields from that subscriber's stream.

### 6.3 Timing Profile Validator (F2 / F3 / I13)
At process startup and on `/healthz`, execute the profile validator:
$$T_{\max} = F \cdot (A + D + \epsilon) \le B$$
If ` p.F * (p.A + p.D + p.eps) > p.B `, or if `p.voice` is enabled and `p.A // 4 + (p.S - 1) * p.delta + p.V > (3 * p.A) // 4`, or if `p.demo and REAL_DATA == 1`, or if the cold-key Ed25519 signature over the canonical profile fails, **refuse boot immediately (`sys.exit(78)`)**.

### 6.4 Exotel Voice Webhook & Paper Code Rules (F7 / §8)
* **Exotel Outbound IVR:**
  1. Require AMD check + mandatory keypress gate (`"Press 1 to hear a referral"`, 8s timeout). Voicemail or silence must never trigger `ACK`.
  2. Only after DTMF `1` is received may `apply_command(ACK, channel='VOICE')` execute.
  3. Deduplicate webhook retries via `INSERT INTO inbox(source, external_id, payload_sha256) ... ON CONFLICT DO NOTHING`.
  4. Enforce a strict **2-second webhook execution budget** (Exotel hard timeout is 5s `[V]`). Play spoken `"recorded"` audio only *after* `apply_command()` commits.
  5. Scope PIN lockout to `session.call_sid` (3 strikes $\rightarrow$ hang up + `PIN_LOCKED` + dispatcher page).
* **Paper Code (Crockford Base32 + Mod 37 Checksum):**
  * 8 Crockford Base32 characters (40-bit integer $N$) + 1 check character representing $N \bmod 37$ mapped to `0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U`. Rate-limit lookups to 10/min per session.

---

## 7. Verification Gates (Must Pass Before Merging Any Backend Step)

1. **Gate B-1 (Lock & Deadlock Check — `T-F1`):** Run `race200` (200 concurrent `ACCEPT` + `TIMEOUT` calls). Verify `pg_stat_database.deadlocks` delta is `0` and `rhp_require_lock` raises zero `I14_LOCK_NOT_HELD` errors.
2. **Gate B-2 (Idempotency Matrix — `T-F14`):** Run all 8 idempotency edge cases (replay 200, replay 409/412/422, reused key with mutated payload $\rightarrow$ 422, concurrent in-flight $\rightarrow$ 409, crash before commit, expired key $>48\text{ h}$ hitting `event.event_id UNIQUE`, missing key $\rightarrow$ 422, same `event_id` with new key $\rightarrow$ 409).
3. **Gate B-3 (Profile & Boot Guard — `T-F2`, `T-F3`):** Verify startup aborts with exit code `78` when `REAL_DATA=1` with `DEMO_FAST`/`DEMO_VOICE`, when $T_{\max} > B$, or when `BROKEN_BUILD=1` points to any DB other than `rhp_scratch_broken`.
4. **Gate B-4 (JSONB & JCS Sanitization — `T-F9`):** Fuzz `event.detail` with free-text PHI strings and floating-point numbers; verify 100% rejection by Pydantic and `rhp_detail_ok()`.

---

## 8. Explicit DO / DO NOT Guardrails

### DO
* **DO** pass every state mutation through `apply_command()` using the exact 10-step sequence.
* **DO** use `SAVEPOINT sp_cmd` after locking `referral` so domain rejections (`403`, `409`, `412`, `422`) roll back partial state changes while preserving the `rejected_command` audit insert and the `idempotency` `DONE` record.
* **DO** increment `session.pin_failed` on a separate autonomous database connection so rolling back a failed command transaction cannot erase the failed PIN attempt counter.
* **DO** compute server timestamps via `SELECT GREATEST(clock_timestamp(), referral.head_ts)` while holding the `referral` row lock (I16).

### DO NOT
* **DO NOT** touch or edit `spec/transitions.yaml`, `spec/rhp1.qnt`, `db/schema.sql`, or anything in `monitor/` without an explicit human-approved `SPEC-DEVIATION` (protected by `CODEOWNERS`).
* **DO NOT** import any backend module into `monitor/` or share helper code between `api/` and `monitor/` (violates Common-Mode Independence F17).
* **DO NOT** allow `TR_UPDATE` to inspect or block on `referral.hs_state` (violates I3).
* **DO NOT** include floating-point numbers in any JCS-hashed dictionary or `event.detail` JSONB column.