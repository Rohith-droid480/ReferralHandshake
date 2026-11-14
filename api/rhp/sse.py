"""Per-Frame Authorized SSE Distribution Hub (§5, §9, Closures F10, Invariant I10).

Specification Anchors:
- Authenticates GET /v1/stream via rhp_session cookie or Bearer token (load_session).
- Supports Last-Event-ID header (outbox.id) to replay missed events upon reconnection.
- Emits a ': heartbeat\\n\\n' comment frame every 15 seconds; re-verifies session validity.
- Per-Frame Grant Evaluation (Invariant I10):
    Before serializing each SSE frame for subscriber (facility_id, role_slot), queries
    whether an active payload_grant (status = 'ACTIVE' and revoked_at IS NULL) exists.
    If grant is revoked:
      - Immediately emits an 'event: GRANT_REVOKED\\ndata: {...}\\n\\n' control frame.
      - Strips all clinical payload fields (PHI, diagnosis, mgso4) from subsequent events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple
from uuid import UUID

from api.rhp.auth import AuthError, Session, load_session

logger = logging.getLogger("rhp.sse")

# Fields considered confidential patient health information (PHI)
PHI_FIELDS: Set[str] = {
    "patient_name",
    "patient_phone",
    "clinical_payload",
    "diagnosis",
    "mgso4",
    "mgso4_status",
    "clinical_notes",
    "parity",
    "gestational_age",
    "vitals",
}


def format_sse_frame(
    event_type: str,
    data: Dict[str, Any],
    event_id: Optional[int] = None,
) -> str:
    """Formats an event payload into an RFC-compliant SSE text frame."""
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    if event_type:
        lines.append(f"event: {event_type}")
    data_str = json.dumps(data)
    lines.append(f"data: {data_str}")
    return "\n".join(lines) + "\n\n"


def format_heartbeat_frame() -> str:
    """Formats an SSE comment heartbeat frame."""
    return ": heartbeat\n\n"


def has_active_payload_grant(
    conn: Any,
    referral_id: UUID,
    facility_id: Optional[UUID],
) -> bool:
    """Enforces Invariant I10: Checks whether facility currently holds an unrevoked payload grant."""
    if not facility_id:
        return False

    ref_str = str(referral_id)
    fac_str = str(facility_id)

    # In-memory MockDatabase support
    if hasattr(conn, "db"):
        grant_key = f"{ref_str}:{fac_str}"
        grant = conn.db.payload_grants.get(grant_key)
        if grant:
            st = grant.get("status", "ACTIVE")
            rev = grant.get("revoked_at")
            return st == "ACTIVE" and rev is None

        # Check in dict values if key format differs
        for g in conn.db.payload_grants.values():
            if str(g.get("referral_id")) == ref_str and str(g.get("facility_id")) == fac_str:
                return g.get("status") == "ACTIVE" and g.get("revoked_at") is None
        return False

    # Real PostgreSQL Statement
    cur = conn.execute(
        """
        SELECT 1 FROM payload_grant
        WHERE referral_id = %s
          AND facility_id = %s
          AND status = 'ACTIVE'
          AND revoked_at IS NULL;
        """,
        (ref_str, fac_str),
    )
    return bool(cur and cur.fetchone())


def strip_phi(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively removes confidential PHI fields from an event payload (Invariant I10)."""
    cleaned: Dict[str, Any] = {}
    for k, v in data.items():
        if k in PHI_FIELDS:
            continue
        if isinstance(v, dict):
            cleaned[k] = strip_phi(v)
        elif isinstance(v, list):
            cleaned[k] = [strip_phi(item) if isinstance(item, dict) else item for item in v]
        else:
            cleaned[k] = v
    return cleaned


class SSESubscriber:
    """Represents an active client SSE subscription stream."""

    def __init__(self, session: Session, last_event_id: Optional[int] = None) -> None:
        self.session = session
        self.last_event_id = last_event_id
        self.queue: queue.Queue[str] = queue.Queue(maxsize=500)
        self.connected_at = datetime.now(timezone.utc)
        self.active = True
        self.revoked_referrals: Set[str] = set()

    def push_frame(self, frame: str) -> bool:
        """Pushes a frame to the subscriber queue; drops if queue is full."""
        if not self.active:
            return False
        try:
            self.queue.put_nowait(frame)
            return True
        except queue.Full:
            logger.warning(f"Subscriber {self.session.id} queue full, dropping frame")
            return False

    def close(self) -> None:
        self.active = False


class SSEHub:
    """Central authorized Server-Sent Events hub for distributing outbox events."""

    def __init__(self) -> None:
        self.subscribers: List[SSESubscriber] = []
        self._lock = threading.Lock()

    def subscribe(
        self,
        session: Session,
        last_event_id: Optional[int] = None,
    ) -> SSESubscriber:
        """Registers a new authenticated subscriber stream."""
        sub = SSESubscriber(session=session, last_event_id=last_event_id)
        with self._lock:
            self.subscribers.append(sub)
        logger.info(f"SSE subscriber joined: {session.id} (facility: {session.facility_id}, role: {session.role_slot})")
        return sub

    def unsubscribe(self, sub: SSESubscriber) -> None:
        """Removes a subscriber stream."""
        sub.close()
        with self._lock:
            if sub in self.subscribers:
                self.subscribers.remove(sub)
        logger.info(f"SSE subscriber disconnected: {sub.session.id}")

    def filter_and_format_for_subscriber(
        self,
        conn: Any,
        sub: SSESubscriber,
        outbox_id: int,
        referral_id: UUID,
        event_type: str,
        detail: Dict[str, Any],
    ) -> Optional[str]:
        """Evaluates authorization and Invariant I10 grant status for a specific subscriber."""
        fac_id = sub.session.facility_id
        role = sub.session.role_slot
        ref_str = str(referral_id)

        # Dispatchers receive all public control frames
        if role == "DISPATCHER":
            return format_sse_frame(event_type, detail, event_id=outbox_id)

        # Check live payload grant
        grant_active = has_active_payload_grant(conn, referral_id, fac_id)

        # Handle revocation transition
        if event_type == "GRANT_REVOKED":
            target_fac = detail.get("facility")
            if str(target_fac) == str(fac_id) or not grant_active:
                sub.revoked_referrals.add(ref_str)
                # Emit mandatory GRANT_REVOKED control frame
                return format_sse_frame(
                    "GRANT_REVOKED",
                    {"referral_id": ref_str, "status": "REVOKED"},
                    event_id=outbox_id,
                )

        if not grant_active or ref_str in sub.revoked_referrals:
            # Strip all PHI fields
            sanitized = strip_phi(detail)
            # Retain only structural routing identifiers
            public_detail = {
                "referral_id": ref_str,
                "type": event_type,
                "sanitized": True,
            }
            for k in ("step", "facility", "status", "epoch", "outcome"):
                if k in sanitized:
                    public_detail[k] = sanitized[k]
            return format_sse_frame(event_type, public_detail, event_id=outbox_id)

        # Grant active: send full frame
        return format_sse_frame(event_type, detail, event_id=outbox_id)

    def broadcast_outbox_event(self, item: Dict[str, Any]) -> int:
        """Broadcasts an outbox item to all active subscribers, filtering per subscriber."""
        outbox_id = int(item.get("id", 0))
        ref_id_str = item.get("referral_id")
        if not ref_id_str:
            return 0
        ref_id = UUID(str(ref_id_str))
        kind = item.get("kind", "OUTBOX")
        detail = item.get("detail", {})

        # Use main connection to check live payload grants
        from api.rhp.db import get_main_connection

        delivered = 0
        with get_main_connection() as conn:
            with self._lock:
                active_subs = list(self.subscribers)

            for sub in active_subs:
                if not sub.active:
                    continue
                frame = self.filter_and_format_for_subscriber(
                    conn, sub, outbox_id, ref_id, kind, detail
                )
                if frame:
                    if sub.push_frame(frame):
                        delivered += 1

        return delivered

    def replay_missed_events(
        self,
        conn: Any,
        sub: SSESubscriber,
        from_id: int,
    ) -> int:
        """Replays missed outbox frames for a reconnecting subscriber (Last-Event-ID)."""
        replayed = 0
        if hasattr(conn, "db"):
            candidates = [r for r in conn.db.outbox if r.get("id", 0) > from_id and r.get("channel") == "SSE"]
            candidates.sort(key=lambda x: x.get("id", 0))
            for item in candidates:
                ref_id = UUID(str(item["referral_id"]))
                kind = item.get("kind", "UPDATE")
                detail = item.get("detail", {})
                frame = self.filter_and_format_for_subscriber(
                    conn, sub, item["id"], ref_id, kind, detail
                )
                if frame and sub.push_frame(frame):
                    replayed += 1
            return replayed

        cur = conn.execute(
            """
            SELECT id, referral_id, kind FROM outbox
            WHERE id > %s AND channel = 'SSE'
            ORDER BY id ASC
            LIMIT 100;
            """,
            (from_id,),
        )
        rows = cur.fetchall() if cur else []
        for r in rows:
            o_id, r_id, k = r[0], UUID(str(r[1])), r[2]
            frame = self.filter_and_format_for_subscriber(conn, sub, o_id, r_id, k, {})
            if frame and sub.push_frame(frame):
                replayed += 1
        return replayed


# Global singleton SSE Hub
_GLOBAL_SSE_HUB: Optional[SSEHub] = None
_HUB_LOCK = threading.Lock()


def get_sse_hub() -> SSEHub:
    """Returns the singleton SSEHub instance."""
    global _GLOBAL_SSE_HUB
    with _HUB_LOCK:
        if _GLOBAL_SSE_HUB is None:
            _GLOBAL_SSE_HUB = SSEHub()
        return _GLOBAL_SSE_HUB
