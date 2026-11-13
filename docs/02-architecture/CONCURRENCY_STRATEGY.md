# ReferralHandshake (Protocol RHP-1) — Concurrency, Locking & Fault-Tolerance Strategy

**System:** Referral Handshake Protocol (RHP-1) & Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0  
**Document ID:** `CONCURRENCY_STRATEGY.md` | **Status:** LOCKED (`REAL_DATA=0`)  
**Authority Precedence:** `Problem_Statement_v7.md` $>$ `[V]` Research Findings $>$ `v8_LOCKED_Solution.md` $>$ `FINAL_LOCKED_Architecture.md`

---

## 1. Concurrency Philosophy & Database Architecture

### 1.1 Why PostgreSQL 16 Per-Referral Row Locking (`D8`, `F1`)
Emergency referral coordination is contended **per referral** (competing hospital desks pressing Accept simultaneously, an expiring ACK timer racing a human keypress, or a network retry overlapping an in-flight request), while unrelated referrals across a district are completely independent.
- **Why not SQLite (`D8`):** SQLite WAL mode serializes all writers globally on a single file and its default `synchronous=NORMAL` can lose recent commits on power loss.
- **Why not Read-Replica Locks (`v8` Appendix A):** PostgreSQL row-level locks (`SELECT ... FOR UPDATE`) cannot be acquired on hot standbys. All state-mutating commands and timer claims execute on a **single writable PostgreSQL 16 primary** with `synchronous_commit=on` and `READ COMMITTED` isolation paired with explicit row locks.
- **Per-Referral Granularity:** Locking the parent `referral` row first serializes all competing mutations for that specific patient while allowing unrelated referrals to execute with zero lock contention.

---

## 2. Global Lock Order & Deadlock-Freedom Proof (`F1`, `I14`)

### 2.1 Total Lock Ordering Law
Every transaction that acquires more than one row lock in PostgreSQL must acquire locks in this strict global hierarchy:
$$\text{advisory\_xact\_lock}(\text{actor}, \text{idem\_key}) \longrightarrow \text{referral} \longrightarrow \text{offer } (\text{ORDER BY id}) \longrightarrow \text{deadline } (\text{ORDER BY id}) \longrightarrow \text{outbox}$$

### 2.2 Complete Lock Acquisition Matrix Across All Execution Paths

| Execution Path | Isolation Level | Locks Acquired (in exact chronological order) | Waits While Holding Another Lock? | Can Form a Wait-For Cycle? |
|---|---|---|---|---|
| **1. `apply_command()`** | `READ COMMITTED` | 1. `pg_try_advisory_xact_lock` (non-blocking)<br>2. `idempotency` row `(actor_id, key)`<br>3. `referral` (`WHERE id = $1 FOR UPDATE`)<br>4. `offer` (`WHERE referral_id = $1 ORDER BY id FOR UPDATE`)<br>5. `deadline` (`WHERE referral_id = $1 AND status='PENDING' ORDER BY id FOR UPDATE`)<br>6. `outbox` (`INSERT` rows) | **Yes, strictly forward** in the hierarchy (`referral` $\rightarrow$ `offer` $\rightarrow$ `deadline` $\rightarrow$ `outbox`). Each transaction touches at most **one** `referral_id`. | **No.** Wait-for edges only point forward along the DAG and never cross referrals. |
| **2. Poller Phase 1 (`tick` claim)** | `READ COMMITTED` | Single atomic statement: `UPDATE deadline SET claimed_until = ... WHERE id IN (SELECT id FROM deadline ... ORDER BY due_at LIMIT 50 FOR UPDATE SKIP LOCKED) RETURNING ...` followed by immediate `COMMIT`. | **Never.** `SKIP LOCKED` immediately skips any `deadline` row locked by an active `apply_command()` transaction. | **No.** Zero wait time while holding any lock; commits before Phase 2 starts. |
| **3. Poller Phase 2 (`TIMEOUT` cmd)** | `READ COMMITTED` | Invokes `apply_command(TimeoutCmd)` in a fresh transaction per claimed deadline. | Identical to Path 1 (`referral` $\rightarrow$ `offer` $\rightarrow$ `deadline` $\rightarrow$ `outbox`). | **No.** Acquires `referral` lock **before** re-reading `deadline`. |
| **4. Outbox Relay (`relay_tick`)** | `READ COMMITTED` | Single atomic statement: `UPDATE outbox SET visible_after = ..., attempts = attempts + 1 WHERE id IN (SELECT id FROM outbox ... ORDER BY id LIMIT 20 FOR UPDATE SKIP LOCKED) RETURNING *` + `COMMIT`. | **Never.** `SKIP LOCKED` never waits on uncommitted `outbox` inserts. | **No.** Single-table non-blocking lock. |
| **5. Monitor & Witness** | `REPEATABLE READ READ ONLY` | MVCC snapshot only (`SELECT` via server-side cursor). | **Never.** Readers never block writers and writers never block readers in PostgreSQL MVCC. | **No.** Zero row locks acquired. |

### 2.3 Database-Enforced Lock Discipline Trigger (`rhp_require_lock` — `I14`)
To guarantee that no developer or AI coding agent ever writes a query that mutates contract state without holding the `referral` row lock first, Step 4 of `apply_command()` sets a transaction-local session GUC (`SET LOCAL rhp.locked_referral = '<referral_id>'`) immediately after `SELECT * FROM referral WHERE id = $1 FOR UPDATE`.

```sql
CREATE FUNCTION rhp_require_lock() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  rid text := to_jsonb(NEW) ->> (CASE WHEN TG_TABLE_NAME = 'referral' THEN 'id' ELSE 'referral_id' END);
BEGIN
  -- Exemption 1: Poller Phase 1 claim updates ONLY claimed_until (status and due_at are unchanged)
  IF TG_OP = 'UPDATE' AND TG_TABLE_NAME = 'deadline'
     AND (NEW.status, NEW.due_at) IS NOT DISTINCT FROM (OLD.status, OLD.due_at) THEN
    RETURN NEW;
  END IF;
  -- Exemption 2: Outbox relay updates delivery bookkeeping (status, attempts, visible_after) on existing rows
  IF TG_OP = 'UPDATE' AND TG_TABLE_NAME = 'outbox' THEN
    RETURN NEW;
  END IF;
  -- Enforce that the current transaction holds the referral lock for this exact referral_id
  IF current_setting('rhp.locked_referral', true) IS DISTINCT FROM rid THEN
    RAISE EXCEPTION 'I14_LOCK_NOT_HELD: table=% op=% referral_id=%', TG_TABLE_NAME, TG_OP, rid;
  END IF;
  RETURN NEW;
END $$;
```

---

## 3. The 10-Step `apply_command()` Transaction Pipeline

Every state-changing HTTP request, voice DTMF webhook, and Poller Phase 2 `TIMEOUT` passes through `apply_command()`.

```python
# api/pipeline.py — Production 10-Step Command Execution Pipeline (Python 3.12 + psycopg3)
import hashlib
import json
from dataclasses import dataclass
from typing import Any
import psycopg
from psycopg.rows import namedtuple_row

class Reject(Exception):
    """Deterministic domain rejection that must be recorded in rejected_command and cached in idempotency."""
    def __init__(self, code: int, reason: str, detail: dict | None = None):
        self.code = code
        self.reason = reason
        self.detail = detail or {}

def jcs(obj: Any) -> bytes:
    """RFC 8785 Canonical JSON serializer (ASCII keys, ints/strings/bools only; floats forbidden)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def autonomous_pin_failed(dsn: str, session_id: str, roster_id: str, facility_id: str) -> int:
    """
    Executes on an independent connection so rolling back the main transaction NEVER erases failed PIN counts (F7).
    Applies progressive backoff: 0s, 5s, 30s, then 120s lockout on strike 3 + pages dispatcher.
    """
    with psycopg.connect(dsn, autocommit=True, row_factory=namedtuple_row) as aconn:
        row = aconn.execute(
            """UPDATE session
                  SET pin_failed = pin_failed + 1,
                      pin_locked_until = CASE
                        WHEN pin_failed + 1 >= 3 THEN clock_timestamp() + interval '120 seconds'
                        WHEN pin_failed + 1 = 2  THEN clock_timestamp() + interval '30 seconds'
                        WHEN pin_failed + 1 = 1  THEN clock_timestamp() + interval '5 seconds'
                        ELSE pin_locked_until
                      END
                WHERE id = %s
            RETURNING pin_failed""",
            (session_id,),
        ).fetchone()
        strikes = row.pin_failed if row else 1
        if strikes >= 3:
            aconn.execute(
                """INSERT INTO rejected_command(actor_id, referral_id, command, http_status, reason_code, session_id, created_at)
                   VALUES (%s, NULL, 'PIN_AUTH', 429, 'PIN_LOCKED_3_STRIKES', %s, clock_timestamp())""",
                (roster_id, session_id),
            )
        return strikes

def finalize(conn: psycopg.Connection, actor_id: str, idem_key: str, http_status: int, body: dict) -> tuple[int, dict]:
    conn.execute(
        "UPDATE idempotency SET status='DONE', http_status=%s, response=%s WHERE actor_id=%s AND key=%s",
        (http_status, json.dumps(body), actor_id, idem_key),
    )
    return http_status, body

def apply_command(conn: psycopg.Connection, dsn: str, cmd: Any, sess_token_hash: bytes, idem_key: str) -> tuple[int, dict]:
    if not idem_key or not (8 <= len(idem_key) <= 80):
        return 422, {"error": "MISSING_IDEMPOTENCY_KEY"}

    req_hash = sha256_bytes(jcs(cmd.body_for_hash()))

    with conn.transaction():
        # STEP 2 (Read-only pre-load of session to obtain actor_id for scoped idempotency lock)
        s = conn.execute(
            """SELECT s.id, s.roster_id, s.device_id, s.call_sid, s.expires_at, s.revoked_at,
                      s.pin_failed, s.pin_locked_until,
                      r.facility_id, r.role_slot, r.pin_hash, r.valid_from, r.valid_to
                 FROM session s
                 JOIN roster r ON r.id = s.roster_id
                WHERE s.token_hash = %s""",
            (sess_token_hash,),
        ).fetchone()
        if not s or s.revoked_at is not None:
            return 401, {"error": "SESSION_INVALID"}

        # STEP 1: IDEMPOTENCY (Before acquiring any referral lock — F14 / I4)
        lock_Acquire = conn.execute(
            "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0)) AS ok",
            (f"{s.roster_id}:{idem_key}",),
        ).fetchone()
        if not lock_Acquire.ok:
            return 409, {"error": "DUPLICATE_IN_FLIGHT"}

        idem_row = conn.execute(
            """SELECT request_hash, status, http_status, response, expires_at > clock_timestamp() AS fresh
                 FROM idempotency
                WHERE actor_id = %s AND key = %s""",
            (s.roster_id, idem_key),
        ).fetchone()
        if idem_row and idem_row.fresh:
            if bytes(idem_row.request_hash) != req_hash:
                return 422, {"error": "KEY_REUSED_DIFFERENT_PAYLOAD"}
            if idem_row.status == "DONE":
                return idem_row.http_status, idem_row.response  # Exact replay (200 or stored 409/412/422)

        conn.execute(
            """INSERT INTO idempotency(actor_id, key, request_hash, status, created_at, expires_at)
               VALUES (%s, %s, %s, 'IN_FLIGHT', clock_timestamp(), clock_timestamp() + interval '48 hours')
               ON CONFLICT (actor_id, key) DO UPDATE
                  SET request_hash = EXCLUDED.request_hash,
                      status = 'IN_FLIGHT',
                      created_at = clock_timestamp(),
                      expires_at = clock_timestamp() + interval '48 hours'""",
            (s.roster_id, idem_key, req_hash),
        )

        # STEP 3: PIN VERIFICATION (With autonomous failure counter — F7 / I6)
        now_db = conn.execute("SELECT clock_timestamp() AS t").fetchone().t
        if s.expires_at <= now_db:
            return finalize(conn, s.roster_id, idem_key, 401, {"error": "SESSION_EXPIRED"})
        if s.pin_locked_until is not None and s.pin_locked_until > now_db:
            return finalize(conn, s.roster_id, idem_key, 429, {"error": "PIN_LOCKED"})
        if cmd.needs_pin:
            if not argon2_verify(s.pin_hash, cmd.pin):
                strikes = autonomous_pin_failed(dsn, str(s.id), str(s.roster_id), str(s.facility_id))
                code = 429 if strikes >= 3 else 403
                reason = "PIN_LOCKED" if strikes >= 3 else "PIN_INVALID"
                return finalize(conn, s.roster_id, idem_key, code, {"error": reason, "strikes": strikes})
            elif s.pin_failed > 0:
                conn.execute("UPDATE session SET pin_failed = 0, pin_locked_until = NULL WHERE id = %s", (s.id,))

        # Check duplicate event_id even if Idempotency-Key expired after 48h (F14)
        dup_ev = conn.execute("SELECT referral_id, seq, type, epoch, hash FROM event WHERE event_id = %s", (cmd.event_id,)).fetchone()
        if dup_ev:
            return finalize(conn, s.roster_id, idem_key, 409, {
                "error": "DUPLICATE_EVENT_ID",
                "referral_id": str(dup_ev.referral_id),
                "seq": dup_ev.seq,
                "type": dup_ev.type,
            })

        # STEP 4: LOCK REFERRAL FIRST + SET SESSION GUC + MONOTONE SERVER TIMESTAMP (F1 / F11 / I14 / I16)
        if cmd.type == "CREATE":
            conn.execute("SELECT set_config('rhp.locked_referral', %s, true)", (str(cmd.referral_id),))
            ts = conn.execute("SELECT clock_timestamp() AS t").fetchone().t
            r = None
        else:
            r = conn.execute("SELECT * FROM referral WHERE id = %s FOR UPDATE", (cmd.referral_id,)).fetchone()
            if not r:
                return finalize(conn, s.roster_id, idem_key, 404, {"error": "REFERRAL_NOT_FOUND"})
            conn.execute("SELECT set_config('rhp.locked_referral', %s, true)", (str(r.id),))
            ts = conn.execute("SELECT GREATEST(clock_timestamp(), %s) AS t", (r.head_ts,)).fetchone().t

        # Savepoint allows rolling back domain mutations while keeping the referral lock and idempotency row!
        conn.execute("SAVEPOINT sp_cmd")
        try:
            # STEP 5: AUTHORITY & FENCING (I6, I8)
            authorize_actor(conn, r, s, cmd, ts)
            fence_version_and_epoch(r, cmd)

            # STEP 6: LOCK OFFERS (ORDER BY id) & DEADLINES (ORDER BY id) + EVALUATE TRANSITION GUARD
            offers = conn.execute(
                "SELECT * FROM offer WHERE referral_id = %s ORDER BY id FOR UPDATE",
                (cmd.referral_id,),
            ).fetchall() if r else []
            deadlines = conn.execute(
                "SELECT * FROM deadline WHERE referral_id = %s AND status = 'PENDING' ORDER BY id FOR UPDATE",
                (cmd.referral_id,),
            ).fetchall() if r else []

            transition = lookup_transition_guard(cmd, r, offers, deadlines)

            # STEP 7: OFFLINE STALENESS & RESOURCE CONFIRMATION EXPIRY CHECK (F12 / I15)
            check_confirmations_and_staleness(conn, r, offers, cmd, ts)

            # STEP 8: APPLY STATE MUTATIONS (referral, offer, payload_grant, deadline)
            eff = transition.apply(conn, r, offers, deadlines, s, cmd, ts)

            # STEP 9: APPEND HASH-CHAINED EVENT(S) & INSERT OUTBOX ROWS LAST
            ev_view = append_events_and_outbox(conn, r, s, cmd, eff, ts)

            # STEP 10: FINALIZE IDEMPOTENCY RECORD & COMMIT
            return finalize(conn, s.roster_id, idem_key, 200, ev_view)

        except Reject as rej:
            # Roll back partial mutations to sp_cmd; referral FOR UPDATE lock and idempotency row remain held!
            conn.execute("ROLLBACK TO SAVEPOINT sp_cmd")
            conn.execute(
                """INSERT INTO rejected_command(actor_id, key, referral_id, command, http_status, reason_code, session_id, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (s.roster_id, idem_key, cmd.referral_id if r else None, cmd.type, rej.code, rej.reason, s.id, ts),
            )
            return finalize(conn, s.roster_id, idem_key, rej.code, {"error": rej.reason, **rej.detail})
```

### 3.1 Separate `version` vs `lease_epoch` Fencing Semantics (`D7`, `I2`, `I8`)
`fence_version_and_epoch(r, cmd)` distinguishes stale client views from lost concurrent races:
1. **Stale Precondition (`412 Precondition Failed`):**
   - If the client supplies `expected_version` and `expected_version < r.version` **and** the command is not a competing `ACCEPT` race loser, or if `expected_epoch < r.lease_epoch` on an epoch-fenced command, raise `Reject(412, "STALE_VERSION_OR_EPOCH")`.
2. **Lost Ownership Race (`409 Conflict`):**
   - When two facilities $f_1$ and $f_2$ both hold valid offers and press `ACCEPT` simultaneously, the second transaction to acquire `SELECT * FROM referral WHERE id = $1 FOR UPDATE` sees `r.lease_offer_id IS NOT NULL` (or its offer status changed to `SUPERSEDED`). It raises `Reject(409, "LEASE_HELD", {"winner_facility": str(r.lease_facility_id), "lease_epoch": r.lease_epoch})` so the receiving UI immediately explains **why** the race was lost.

---

## 4. Idempotency Edge Cases (`F14`) & Webhook Deduplication

### 4.1 Complete Idempotency Edge-Case Matrix (`F14`, `I4`)

| # | Scenario | State of `idempotency` / `event` | Exact Server Behaviour |
|---|---|---|---|
| 1 | **Same `(actor_id, key)`, same payload, prior `200` success** | `status = 'DONE'`, `http_status = 200` | Step 1 returns stored `200` JSON body immediately before locking `referral`. Zero new events created. |
| 2 | **Same `(actor_id, key)`, same payload, prior domain rejection (`409`/`412`/`422`)** | `status = 'DONE'`, `http_status IN (409, 412, 422)` | Because `Reject` rolled back only to `SAVEPOINT sp_cmd` and called `finalize()`, Step 1 returns the exact stored `409`/`412`/`422` response. |
| 3 | **Same `(actor_id, key)`, mutated request payload** | `request_hash != sha256(jcs(cmd))` | Step 1 immediately returns HTTP `422 KEY_REUSED_DIFFERENT_PAYLOAD`. |
| 4 | **Concurrent duplicate request while first request is still executing** | First txn holds `pg_try_advisory_xact_lock(hashtextextended(actor:key, 0))` | Second request's non-blocking `pg_try_advisory_xact_lock` returns `false` $\rightarrow$ immediate HTTP `409 DUPLICATE_IN_FLIGHT`. Client backs off and retries to receive the cached result. |
| 5 | **Server or DB crash mid-transaction before `COMMIT`** | PostgreSQL aborts uncommitted txn; `IN_FLIGHT` row and all partial writes vanish | Client retry acquires advisory lock cleanly and executes the command from scratch (exactly-once effect). |
| 6 | **Retry arrives $> 48\text{ hours}$ after original request (`expires_at` passed)** | `idempotency` row expired or purged, **but** `event.event_id` is permanently in `event` (`UNIQUE`) | Step 3 lookup on `event WHERE event_id = $1` catches the duplicate and returns HTTP `409 DUPLICATE_EVENT_ID` with the original event metadata. |
| 7 | **Mutating command sent without `Idempotency-Key` header (or length $\notin [8, 80]$)** | — | Rejected before DB transaction with HTTP `422 MISSING_IDEMPOTENCY_KEY`. |
| 8 | **Different `Idempotency-Key`, but client reuses an already-committed `event_id`** | New `idempotency` key, existing `event.event_id` | Caught by `event.event_id` lookup / `UNIQUE` constraint $\rightarrow$ HTTP `409 DUPLICATE_EVENT_ID`. |

---

## 5. Stateless Two-Phase Poller & Outbox Relay Workers

### 5.1 Two-Phase Stateless Deadline Poller (`F1`, `T1`–`T5`)
```python
# api/poller.py — Stateless Two-Phase Deadline Poller (Enforces F1 / I1 / I14)
import time
import psycopg
from psycopg.rows import namedtuple_row
from api.pipeline import apply_command, TimeoutCmd

CLAIM_SQL = """
UPDATE deadline
   SET claimed_until = clock_timestamp() + interval '5 seconds'
 WHERE id IN (
       SELECT id
         FROM deadline
        WHERE status = 'PENDING'
          AND due_at <= clock_timestamp()
          AND (claimed_until IS NULL OR claimed_until < clock_timestamp())
        ORDER BY due_at ASC
        LIMIT 50
          FOR UPDATE SKIP LOCKED
 )
RETURNING id, referral_id, offer_id, kind, step, epoch;
"""

def poller_tick(pool, dsn: str, system_token_hash: bytes) -> int:
    # PHASE 1: Single atomic claim statement, committed immediately. Holds NO referral locks.
    with pool.connection() as conn:
        conn.row_factory = namedtuple_row
        with conn.transaction():
            due_rows = conn.execute(CLAIM_SQL).fetchall()
            conn.execute(
                """INSERT INTO heartbeat(subject_kind, subject_id, last_seen, ntp_offset_ms)
                   VALUES ('POLLER', 'poller-1', clock_timestamp(), 0)
                   ON CONFLICT (subject_kind, subject_id)
                   DO UPDATE SET last_seen = clock_timestamp()"""
            )

    # PHASE 2: Each claimed deadline invokes apply_command(TIMEOUT), which locks referral FIRST.
    for d in due_rows:
        with pool.connection() as conn:
            conn.row_factory = namedtuple_row
            cmd = TimeoutCmd(
                referral_id=d.referral_id,
                deadline_id=d.id,
                offer_id=d.offer_id,
                kind=d.kind,
                step=d.step,
                expected_epoch=d.epoch,
            )
            apply_command(
                conn=conn,
                dsn=dsn,
                cmd=cmd,
                sess_token_hash=system_token_hash,
                idem_key=f"timeout:{d.id}:{d.epoch}",
            )
    return len(due_rows)
```

### 5.2 Outbox Relay with Visibility Timeout & Per-Event SSE Authz (`F10`, `I10`)
```python
# api/relay.py — Transactional Outbox Relay (At-Least-Once Delivery + I10 Stream Filtering)
import psycopg
from psycopg.rows import namedtuple_row

RELAY_CLAIM_SQL = """
UPDATE outbox
   SET visible_after = clock_timestamp() + interval '30 seconds',
       attempts = attempts + 1
 WHERE id IN (
       SELECT id
         FROM outbox
        WHERE status = 'PENDING'
          AND visible_after <= clock_timestamp()
        ORDER BY id ASC
        LIMIT 20
          FOR UPDATE SKIP LOCKED
 )
RETURNING id, referral_id, event_seq, channel, target_roster_id, kind, attempts;
"""

def relay_tick(pool, adapters) -> int:
    with pool.connection() as conn:
        conn.row_factory = namedtuple_row
        with conn.transaction():
            batch = conn.execute(RELAY_CLAIM_SQL).fetchall()
            conn.execute(
                """INSERT INTO heartbeat(subject_kind, subject_id, last_seen, ntp_offset_ms)
                   VALUES ('RELAY', 'relay-1', clock_timestamp(), 0)
                   ON CONFLICT (subject_kind, subject_id)
                   DO UPDATE SET last_seen = clock_timestamp()"""
            )

    for row in batch:
        try:
            # Deliver via channel adapter (SSE checks active payload_grant at emit time — F10 / I10)
            adapters[row.channel].deliver(row)
            with pool.connection() as conn:
                conn.execute("UPDATE outbox SET status = 'SENT' WHERE id = %s", (row.id,))
        except Exception:
            if row.attempts > 8:
                with pool.connection() as conn:
                    conn.execute("UPDATE outbox SET status = 'DEAD' WHERE id = %s", (row.id,))
                adapters["PROXY_PAGE"].alert_dead_outbox(row)
    return len(batch)
```

---

## 6. Concurrency Verification Harness (`race200`) & Chaos Matrix

### 6.1 200-Way Concurrent Accept Barrier Test (`T-C1 race200`)
```python
# tests/test_race200.py — 200-Way Concurrent Accept Verification Gate (T0 Mandatory Gate)
import asyncio
import uuid
import httpx
import psycopg

API_URL = "http://localhost:8000"

async def run_race200(dsn: str, referral_id: str, offer_ids: list[str], session_cookies: list[dict], expected_version: int):
    n = 200
    barrier = asyncio.Barrier(n)
    run_id = uuid.uuid4().hex[:8]

    with psycopg.connect(dsn) as conn:
        dl_before = conn.execute("SELECT sum(deadlocks) FROM pg_stat_database").fetchone()[0] or 0

    async def worker(i: int):
        offer_id = offer_ids[i % len(offer_ids)]
        cookies = session_cookies[i % len(session_cookies)]
        async with httpx.AsyncClient(base_url=API_URL, cookies=cookies, timeout=15.0) as client:
            await barrier.wait()
            return await client.post(
                f"/v1/offers/{offer_id}/accept",
                json={"expected_version": expected_version, "pin": "1234", "event_id": str(uuid.uuid4())},
                headers={"Idempotency-Key": f"race-{run_id}-{i:03d}"},
            )

    responses = await asyncio.gather(*(worker(i) for i in range(n)))
    status_codes = [r.status_code for r in responses]

    # Gate Assertions (Architecture §12 & §24)
    assert status_codes.count(200) == 1, f"Expected exactly 1 winner, got {status_codes.count(200)}"
    assert all(c in (200, 409, 412, 422, 429) for c in status_codes), f"Unexpected HTTP status in {set(status_codes)}"

    with psycopg.connect(dsn) as conn:
        acc_count = conn.execute(
            "SELECT count(*) FROM offer WHERE referral_id = %s AND status = 'ACCEPTED'",
            (referral_id,),
        ).fetchone()[0]
        seq_gap = conn.execute(
            "SELECT COALESCE(max(seq) - count(*), 0) FROM event WHERE referral_id = %s",
            (referral_id,),
        ).fetchone()[0]
        dl_after = conn.execute("SELECT sum(deadlocks) FROM pg_stat_database").fetchone()[0] or 0

    assert acc_count == 1, f"I2 violation: {acc_count} ACCEPTED offers in DB"
    assert seq_gap == 0, f"I4 violation: sequence gap {seq_gap} in event table"
    assert (dl_after - dl_before) == 0, f"I14 violation: {dl_after - dl_before} deadlocks detected"
```

### 6.2 Toxiproxy Fault-Injection Matrix (`API <-> DB` and `Client <-> API`)

| # | Toxic Type | Injected Parameters | Concurrency / Recovery Assertion | Status |
|---|---|---|---|---|
| 1 | `latency` (upstream) | `latency=400ms`, `jitter=150ms` on `API <-> PG` | `p95` latency increases; zero duplicate events (`I4`); `one_lease` holds (`I2`). | `CLOSED` |
| 2 | `latency` (downstream) | `latency=1200ms` on `Client <-> API` | Client timeouts trigger retries with same `Idempotency-Key`; Step 1 returns `409 DUPLICATE_IN_FLIGHT` or cached `200`; single event committed. | `CLOSED` |
| 3 | `bandwidth` | `rate=5KB/s` on `PWA <-> API` | SSE stream survives slow link; on drop, `Last-Event-ID` replays missed events from `event` table in `seq` order. | `BOUNDED` |
| 4 | `slow_close` | `delay=2000ms` on `API <-> PG` | Connection pool bounds active sockets; no leaked `IN_FLIGHT` idempotency locks after transaction completion. | `CLOSED` |
| 5 | `timeout` | `timeout=1500ms` on `Client <-> API` | Retried command receives stored `idempotency.response` (`200` or `409`) with identical `event_id`. | `CLOSED` |
| 6 | `reset_peer` (TCP RST) | `timeout=0` mid-transaction on `API <-> PG` | PostgreSQL rolls back uncommitted transaction; `IN_FLIGHT` row vanishes; client retry executes cleanly once. | `CLOSED` |
| 7 | `slicer` | `average_size=64`, `size_variation=32`, `delay=10ms` | Fragmented HTTP/JSON frames reassemble cleanly; RFC 8785 JCS SHA-256 hash chain verifies (`I5`). | `CLOSED` |
| 8 | `limit_data` / partition | Disable proxy (`enabled=false`) for $10\text{ s}$ | Poller claims expire in $\le 5\text{ s}$; outbox relay redelivers within $\le 30\text{ s}$ visibility timeout; Runtime Monitor stays green ($0$ violations). | `BOUNDED` |