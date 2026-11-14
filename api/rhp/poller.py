"""Two-Phase Stateless Deadline Poller (§5, §6, Closures F1, F2, F6, Invariant I1).

Phase 1 (Single Committed Claim Statement, No Referral Lock):
  UPDATE deadline
     SET claimed_until = clock_timestamp() + interval '5 seconds'
   WHERE id IN (
         SELECT id FROM deadline
          WHERE status = 'PENDING'
            AND due_at <= clock_timestamp()
            AND (claimed_until IS NULL OR claimed_until < clock_timestamp())
          ORDER BY due_at
          LIMIT 50
          FOR UPDATE SKIP LOCKED
   )
  RETURNING id, referral_id, offer_id, kind, step, epoch;

Phase 2 (Per-Deadline Command Execution under Referral Lock):
  For each claimed row d, invoke:
    apply_command(conn, TimeoutCmd(referral_id=d.referral_id, deadline_id=d.id, ...),
                  session_token=SYSTEM_SESSION, idem_key=f"timeout:{d.id}:{d.epoch}")
  Under the referral lock, apply_command re-verifies deadline status == 'PENDING' and epoch,
  making double-firing 100% idempotent.

Heartbeats:
  Every 5 seconds, upserts row into heartbeat(subject_kind='POLLER', subject_id=poller_id, ...).
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.commands.timeout import execute_timeout  # Ensures timeout command logic is loaded
from api.rhp.config import get_settings
from api.rhp.pipeline import apply_command

logger = logging.getLogger("rhp.poller")

# Cached system session token
_CACHED_SYSTEM_TOKEN: Optional[str] = None
_SYSTEM_TOKEN_LOCK = threading.Lock()


def _parse_uuid(val: Any) -> Optional[UUID]:
    """Safely parses a UUID, returning None if invalid or absent."""
    if not val:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except Exception:
        return None


@dataclass(frozen=True)
class ClaimedDeadline:
    """Represents a deadline row claimed during Phase 1."""

    id: UUID
    referral_id: UUID
    offer_id: Optional[UUID]
    kind: str
    step: Optional[int]
    epoch: int
    due_at: Optional[datetime] = None


def get_or_create_system_session(conn: Any) -> str:
    """Retrieves or creates a system session token for automated poller commands."""
    global _CACHED_SYSTEM_TOKEN
    with _SYSTEM_TOKEN_LOCK:
        if _CACHED_SYSTEM_TOKEN is not None:
            try:
                from api.rhp.auth import load_session
                load_session(conn, _CACHED_SYSTEM_TOKEN)
                return _CACHED_SYSTEM_TOKEN
            except Exception:
                _CACHED_SYSTEM_TOKEN = None

        # Use dispatch admin roster if available, or first available roster
        roster_candidates = [
            "a6666666-0000-0000-0000-000000000005",
            "00000000-0000-0000-0000-000000000010",
        ]
        target_roster = roster_candidates[0]
        if hasattr(conn, "db") and target_roster not in conn.db.rosters:
            target_roster = next(iter(conn.db.rosters.keys()), roster_candidates[1])

        raw_tok, _ = create_enrollment_ticket(conn, target_roster, target_roster, ttl_seconds=86400 * 30)
        token, _ = redeem_enrollment_ticket(conn, raw_tok, secrets.token_bytes(32), "android", ttl_hours=720)
        conn.commit()
        _CACHED_SYSTEM_TOKEN = token
        return token


def claim_due_deadlines(
    conn: Any,
    limit: int = 50,
    now: Optional[datetime] = None,
) -> List[ClaimedDeadline]:
    """Phase 1: Claims up to `limit` due deadlines using FOR UPDATE SKIP LOCKED.

    Commits immediately; holds zero referral locks.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # In-memory MockDatabase support
    if hasattr(conn, "db"):
        matched: List[Dict[str, Any]] = []
        for d in conn.db.deadlines.values():
            if d.get("status") == "PENDING":
                due = d.get("due_at")
                if isinstance(due, str):
                    due = datetime.fromisoformat(due)
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)

                claimed = d.get("claimed_until")
                if isinstance(claimed, str):
                    claimed = datetime.fromisoformat(claimed)
                if claimed and claimed.tzinfo is None:
                    claimed = claimed.replace(tzinfo=timezone.utc)

                if due <= now and (claimed is None or claimed < now):
                    matched.append(d)

        matched.sort(key=lambda x: x.get("due_at", now))
        claimed_rows = matched[:limit]
        for d in claimed_rows:
            d["claimed_until"] = now + timedelta(seconds=5)

        return [
            ClaimedDeadline(
                id=_parse_uuid(d["id"]) or UUID("00000000-0000-0000-0000-000000000000"),
                referral_id=_parse_uuid(d["referral_id"]) or UUID("00000000-0000-0000-0000-000000000000"),
                offer_id=_parse_uuid(d.get("offer_id")),
                kind=str(d["kind"]),
                step=int(d["step"]) if d.get("step") is not None else None,
                epoch=int(d["epoch"]),
                due_at=d.get("due_at"),
            )
            for d in claimed_rows
        ]

    # Real PostgreSQL Statement
    cur = conn.execute(
        """
        UPDATE deadline
           SET claimed_until = clock_timestamp() + interval '5 seconds'
         WHERE id IN (
               SELECT id FROM deadline
                WHERE status = 'PENDING'
                  AND due_at <= clock_timestamp()
                  AND (claimed_until IS NULL OR claimed_until < clock_timestamp())
                ORDER BY due_at
                LIMIT %s
                FOR UPDATE SKIP LOCKED
         )
        RETURNING id, referral_id, offer_id, kind, step, epoch, due_at;
        """,
        (limit,),
    )
    rows = cur.fetchall() if cur else []
    return [
        ClaimedDeadline(
            id=_parse_uuid(r[0]) or UUID("00000000-0000-0000-0000-000000000000"),
            referral_id=_parse_uuid(r[1]) or UUID("00000000-0000-0000-0000-000000000000"),
            offer_id=_parse_uuid(r[2]),
            kind=str(r[3]),
            step=int(r[4]) if r[4] is not None else None,
            epoch=int(r[5]),
            due_at=r[6],
        )
        for r in rows
    ]


def execute_claimed_deadline(
    conn: Any,
    claimed: ClaimedDeadline,
    system_session_token: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Phase 2: Invokes apply_command under referral lock for a claimed deadline."""
    if system_session_token is None:
        system_session_token = get_or_create_system_session(conn)

    idem_key = f"timeout:{claimed.id}:{claimed.epoch}"
    cmd_payload = {
        "type": "TIMEOUT",
        "referral_id": str(claimed.referral_id),
        "deadline_id": str(claimed.id),
        "kind": claimed.kind,
        "step": claimed.step,
        "epoch": claimed.epoch,
        "channel": "SYSTEM",
    }

    status, resp = apply_command(
        conn,
        cmd_payload,
        session_token=system_session_token,
        idem_key=idem_key,
    )
    return status, resp


def upsert_heartbeat(
    conn: Any,
    subject_kind: str,
    subject_id: str,
    ntp_offset_ms: int = 0,
) -> None:
    """Upserts worker liveness into heartbeat table (Closure F11)."""
    now = datetime.now(timezone.utc)
    # File-backed IPC for mock multi-process mode (only outside pytest)
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        ipc_path = os.path.join(tempfile.gettempdir(), "rhp_heartbeats_ipc.json")
        try:
            data = {}
            if os.path.exists(ipc_path):
                with open(ipc_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data[f"{subject_kind.upper()}:{subject_id}"] = {
                "subject_kind": subject_kind.upper(),
                "subject_id": subject_id,
                "last_seen": now.isoformat(),
                "ntp_offset_ms": ntp_offset_ms,
            }
            with open(ipc_path + ".tmp", "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(ipc_path + ".tmp", ipc_path)
        except Exception:
            pass

    if hasattr(conn, "db"):
        if not hasattr(conn.db, "heartbeats"):
            conn.db.heartbeats = {}
        conn.db.heartbeats[(subject_kind.upper(), subject_id)] = {
            "subject_kind": subject_kind.upper(),
            "subject_id": subject_id,
            "last_seen": now,
            "ntp_offset_ms": ntp_offset_ms,
        }
        return

    conn.execute(
        """
        INSERT INTO heartbeat (subject_kind, subject_id, last_seen, ntp_offset_ms)
        VALUES (%s, %s, clock_timestamp(), %s)
        ON CONFLICT (subject_kind, subject_id)
        DO UPDATE SET last_seen = EXCLUDED.last_seen, ntp_offset_ms = EXCLUDED.ntp_offset_ms;
        """,
        (subject_kind, subject_id, ntp_offset_ms),
    )


def poll_once(
    get_connection_func: Callable[[], Any],
    limit: int = 50,
    now: Optional[datetime] = None,
    system_session_token: Optional[str] = None,
) -> int:
    """Executes a single 2-phase poll cycle across independent transactions.

    Returns the number of deadlines executed.
    """
    # Phase 1: Claim statement on auto-committed connection
    with get_connection_func() as conn1:
        claimed = claim_due_deadlines(conn1, limit=limit, now=now)
        conn1.commit()

    if not claimed:
        return 0

    executed_count = 0
    # Phase 2: Per-deadline transaction
    for dl in claimed:
        try:
            with get_connection_func() as conn2:
                status, resp = execute_claimed_deadline(
                    conn2,
                    dl,
                    system_session_token=system_session_token,
                )
                conn2.commit()
                if status == 200:
                    executed_count += 1
        except Exception as e:
            logger.warning(f"Error executing deadline {dl.id}: {e}")

    return executed_count


def run_poller_loop(
    get_connection_func: Callable[[], Any],
    stop_event: Optional[threading.Event] = None,
    interval_ms: Optional[int] = None,
    poller_id: str = "poller-1",
) -> None:
    """Runs the continuous background poller loop with 5s heartbeats."""
    if stop_event is None:
        stop_event = threading.Event()

    settings = get_settings()
    if interval_ms is None:
        interval_ms = 250 if getattr(settings, "profile", "DEMO_FAST") == "DEMO_FAST" else 1000

    last_hb = 0.0
    sleep_sec = interval_ms / 1000.0

    while not stop_event.is_set():
        now_ts = time.time()
        # 5-second Heartbeat
        if now_ts - last_hb >= 5.0:
            try:
                with get_connection_func() as conn_hb:
                    upsert_heartbeat(conn_hb, "POLLER", poller_id, ntp_offset_ms=0)
                    conn_hb.commit()
                last_hb = now_ts
            except Exception as e:
                logger.warning(f"Failed to upsert poller heartbeat: {e}")

        # Execute single poll cycle
        try:
            poll_once(get_connection_func, limit=50)
        except Exception as e:
            logger.warning(f"Poller cycle error: {e}")

        stop_event.wait(timeout=sleep_sec)


if __name__ == "__main__":
    from api.rhp.db import get_main_connection
    print("[RHP-POLLER] Starting 2-phase stateless deadline poller daemon...")
    run_poller_loop(get_main_connection)

