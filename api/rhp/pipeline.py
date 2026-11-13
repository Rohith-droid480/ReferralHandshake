"""ReferralHandshake Protocol RHP-1 — The 10-Step apply_command() Transactional Pipeline.

Specification Anchors:
- Architecture §5: Complete 10-step apply_command() transaction contract
- Architecture §7: Global lock hierarchy: referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox
- Invariant I4: Tamper-evident SHA-256 event hash chain
- Invariant I6: Role slot integrity, session validity, and BOLA prevention
- Invariant I8: Optimistic fencing on expected_version and expected_epoch (Reject 412)
- Invariant I11: RFC 8785 canonical JSON with strict float rejection and closed detail allowlist
- Invariant I14: Strict referral-first locking and transaction session GUC stamping (I14_LOCK_NOT_HELD)
- Invariant I15: Stale confirmation detection on ACCEPT (Reject 409 STALE_CONFIRMATION_RECONFIRM_REQUIRED)
- Invariant I16: Monotone server timestamps GREATEST(clock_timestamp(), r.head_ts)
- Closure F1: 10-step serial execution pipeline
- Closure F7: Autonomous brute-force failure persistence across command rollback
- Closure F9: Closed key allowlist for event details
- Closure F11: Clock monotonicity under referral lock
- Closure F12: Live resource confirmation expiration guard
- Closure F14: Scoped idempotency with exact replay of prior 200/409/412/422 outcomes
- BUILD_PLAN §2.5: The 10-Step apply_command() Transactional Pipeline
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from api.rhp.auth import AuthError, Session, load_session, verify_pin_or_lockout
from api.rhp.commands.accept import execute_accept
from api.rhp.commands.ack_confirm import execute_ack, execute_resource_confirm
from api.rhp.commands.counter import execute_confirm_counter, execute_counter
from api.rhp.commands.create import execute_create
from api.rhp.commands.decline_advance import advance, execute_decline
from api.rhp.commands.timeout import execute_timeout
from api.rhp.commands.lifecycle import (
    execute_arrival_rejected,
    execute_cancel,
    execute_close,
    execute_dispatcher_assign,
    execute_revoke_grant,
)
from api.rhp.crypto import GENESIS_PREV_HASH_BYTES, compute_event_hash, jcs
from api.rhp.db import get_monotone_ts
from api.rhp.schemas import BaseCommand, authorize, parse_command, validate_event_detail
from api.rhp.transitions import TRANSITIONS, TransitionReject


# =============================================================================
# Referral & Offer State Models
# =============================================================================

class ReferralState:
    """In-memory mutable view of a referral record during pipeline execution."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.id = UUID(str(data["id"]))
        self.version = int(data.get("version", 1))
        self.hs_state = str(data.get("hs_state", "CREATED"))
        self.tr_state = str(data.get("tr_state", "REQUESTED"))
        self.mode = str(data.get("mode", "SEQUENTIAL"))
        self.need_class = str(data.get("need_class", "OB_ECLAMPSIA"))
        self.origin_facility_id = UUID(str(data.get("origin_facility_id") or data["from_facility_id"]))
        self.from_facility_id = self.origin_facility_id
        self.chain = [UUID(str(c)) for c in data.get("chain", [])]
        self.ladder_cursor = int(data.get("ladder_cursor", 0))
        self.lease_offer_id = UUID(str(data["lease_offer_id"])) if data.get("lease_offer_id") else None
        self.lease_facility_id = UUID(str(data["lease_facility_id"])) if data.get("lease_facility_id") else None
        self.lease_epoch = int(data.get("lease_epoch", 0))
        self.open_offers = int(data.get("open_offers", 0))
        self.tr_facility_id = UUID(str(data["tr_facility_id"])) if data.get("tr_facility_id") else None
        self.mgso4_status = str(data.get("mgso4_status", "UNKNOWN"))
        self.profile_id = str(data.get("profile_id", "DEMO_FAST"))
        self.paper_code = str(data.get("paper_code", "DEMO-001"))
        self.head_seq = int(data.get("head_seq", 0))
        self.head_hash = bytes(data.get("head_hash", GENESIS_PREV_HASH_BYTES))
        self.head_ts = data.get("head_ts", datetime.now(timezone.utc))
        self.outcome = data.get("outcome")
        self.created_by = UUID(str(data.get("created_by", uuid4())))
        self.created_at = data.get("created_at", datetime.now(timezone.utc))
        self.closed_at = data.get("closed_at")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "version": self.version,
            "hs_state": self.hs_state,
            "tr_state": self.tr_state,
            "mode": self.mode,
            "need_class": self.need_class,
            "from_facility_id": str(self.origin_facility_id),
            "origin_facility_id": str(self.origin_facility_id),
            "chain": [str(c) for c in self.chain],
            "ladder_cursor": self.ladder_cursor,
            "lease_offer_id": str(self.lease_offer_id) if self.lease_offer_id else None,
            "lease_facility_id": str(self.lease_facility_id) if self.lease_facility_id else None,
            "lease_epoch": self.lease_epoch,
            "open_offers": self.open_offers,
            "tr_facility_id": str(self.tr_facility_id) if self.tr_facility_id else None,
            "mgso4_status": self.mgso4_status,
            "profile_id": self.profile_id,
            "head_seq": self.head_seq,
            "head_hash": self.head_hash,
            "head_ts": self.head_ts,
            "outcome": self.outcome,
        }


class OfferState:
    """In-memory mutable view of an offer record during pipeline execution."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.id = UUID(str(data["id"]))
        self.referral_id = UUID(str(data["referral_id"]))
        self.facility_id = UUID(str(data["facility_id"]))
        self.step = int(data.get("step", 0))
        self.source = str(data.get("source", "CHAIN"))
        self.status = str(data.get("status", "OPEN"))
        self.counter_round = int(data.get("counter_round", 0))
        self.counter_mask = int(data.get("counter_mask", 0))
        self.created_epoch = int(data.get("created_epoch", 0))
        self.created_at = data.get("created_at", datetime.now(timezone.utc))
        self.acked_at = data.get("acked_at")
        self.decided_at = data.get("decided_at")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "referral_id": str(self.referral_id),
            "facility_id": str(self.facility_id),
            "step": self.step,
            "source": self.source,
            "status": self.status,
            "counter_round": self.counter_round,
            "counter_mask": self.counter_mask,
            "created_epoch": self.created_epoch,
        }


# =============================================================================
# Invariant I14 Guard Helper
# =============================================================================

def assert_referral_locked(conn: Any, referral_id: Union[UUID, str]) -> None:
    """Enforces Invariant I14: Raises RuntimeError('I14_LOCK_NOT_HELD') if
    rhp.locked_referral transaction GUC does not match referral_id.
    """
    ref_str = str(referral_id)
    if hasattr(conn, "session_gucs"):
        current = conn.session_gucs.get("rhp.locked_referral")
        if current != ref_str:
            raise RuntimeError("I14_LOCK_NOT_HELD")
        return

    cur = conn.cursor()
    try:
        cur.execute("SELECT current_setting('rhp.locked_referral', true);")
        row = cur.fetchone()
        current = row[0] if row else None
        if current != ref_str:
            raise RuntimeError("I14_LOCK_NOT_HELD")
    finally:
        cur.close()


# =============================================================================
# The 10-Step apply_command() Transactional Pipeline (§5)
# =============================================================================

def apply_command(
    conn: Any,
    cmd_or_dict: Union[BaseCommand, Dict[str, Any]],
    session_token: str,
    idem_key: str,
) -> Tuple[int, Dict[str, Any]]:
    """Applies a state-changing command through the 10-step RHP-1 pipeline.

    All mutations and queries are strictly executed via conn.execute(...) SQL statements.
    Domain rejections rollback state changes to SAVEPOINT sp_cmd while logging to rejected_command.
    """
    now = datetime.now(timezone.utc)
    actor_id: Optional[UUID] = None
    ref_id: Optional[UUID] = None
    session: Optional[Session] = None
    cmd_type: str = "UNKNOWN"
    sp_created: bool = False
    ts: datetime = now

    # -------------------------------------------------------------------------
    # STEP 1: Idempotency (Before Referral Lock) (Closures F1, F14)
    # -------------------------------------------------------------------------
    if idem_key is None or len(str(idem_key)) < 8:
        raise TransitionReject(
            422,
            "MISSING_IDEMPOTENCY_KEY",
            "Idempotency-Key header is required and must be at least 8 characters",
        )

    # -------------------------------------------------------------------------
    # STEP 2: Session & Device Validation (Invariant I6, §9)
    # -------------------------------------------------------------------------
    session = load_session(conn, session_token)
    actor_id = session.roster_id

    # Parse and validate command payload with extra='forbid'
    if isinstance(cmd_or_dict, BaseCommand):
        cmd = cmd_or_dict
    else:
        cmd = parse_command(cmd_or_dict)
    cmd_type = cmd.type

    # Canonical request hash via RFC 8785 JCS canonical bytes
    canonical_body = jcs(cmd.model_dump(mode="json"))
    req_hash = hashlib.sha256(canonical_body).digest()

    # Pre-minted event_id uniqueness check (F14, Invariant I4)
    if getattr(cmd, "event_id", None):
        cur_ev = conn.execute(
            "SELECT 1 FROM event WHERE event_id = %s;",
            (str(cmd.event_id),),
        )
        if cur_ev and cur_ev.fetchone():
            raise TransitionReject(
                409,
                "DUPLICATE_EVENT_ID",
                f"Event with event_id '{cmd.event_id}' has already been committed",
            )

    # Acquire transaction-scoped advisory lock
    cur_adv = conn.execute(
        "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0));",
        (f"{actor_id}:{idem_key}",),
    )
    adv_row = cur_adv.fetchone()
    if not adv_row or not adv_row[0]:
        raise TransitionReject(
            409,
            "DUPLICATE_IN_FLIGHT",
            "A command with this idempotency key is currently executing",
        )

    # Query idempotency table
    cur_idem = conn.execute(
        "SELECT request_hash, status, http_status, response FROM idempotency WHERE actor_id = %s AND key = %s;",
        (str(actor_id), str(idem_key)),
    )
    stored_idem_row = cur_idem.fetchone()

    if stored_idem_row:
        stored_req_hash, stored_status, stored_http_status, stored_resp = stored_idem_row
        if bytes(stored_req_hash) != req_hash:
            raise TransitionReject(
                422,
                "KEY_REUSED_DIFFERENT_PAYLOAD",
                "Idempotency key has already been used with a different command payload",
            )
        if stored_status == "DONE":
            resp_parsed = json.loads(stored_resp) if isinstance(stored_resp, str) else stored_resp
            return int(stored_http_status), resp_parsed
        if stored_status == "IN_FLIGHT":
            raise TransitionReject(
                409,
                "DUPLICATE_IN_FLIGHT",
                "Command with this idempotency key is already in flight",
            )

    # Insert IN_FLIGHT status row
    conn.execute(
        """
        INSERT INTO idempotency (actor_id, key, request_hash, status, created_at, expires_at)
        VALUES (%s, %s, %s, 'IN_FLIGHT', %s, %s);
        """,
        (str(actor_id), str(idem_key), req_hash, now, now + timedelta(hours=48)),
    )

    # -------------------------------------------------------------------------
    # STEP 3: Step-Up PIN Verification (Argon2id, Closure F7)
    # -------------------------------------------------------------------------
    if cmd.needs_pin:
        verify_pin_or_lockout(conn, session, cmd.candidate_pin)

    # -------------------------------------------------------------------------
    # STEP 4: Lock Referral First & Monotone Clock (Invariants I14, I16, F11)
    # -------------------------------------------------------------------------
    referral: Optional[ReferralState] = None

    if cmd.type == "CREATE":
        ref_id = cmd.referral_id or uuid4()
        conn.execute("SELECT set_config('rhp.locked_referral', %s, true);", (str(ref_id),))
        ts = get_monotone_ts(conn)
        conn.execute("SAVEPOINT sp_cmd;")
        sp_created = True
    else:
        ref_id = cmd.referral_id
        if not ref_id:
            raise TransitionReject(400, "MISSING_REFERRAL_ID", "Command requires referral_id")

        cur_ref = conn.execute(
            """
            SELECT id, version, hs_state, tr_state, mode, need_class, origin_facility_id,
                   chain, ladder_cursor, lease_offer_id, lease_facility_id, lease_epoch,
                   open_offers, tr_facility_id, mgso4_status, profile_id, profile_hash,
                   paper_code, head_seq, head_hash, head_ts, outcome, created_by,
                   created_at, closed_at
            FROM referral
            WHERE id = %s
            FOR UPDATE;
            """,
            (str(ref_id),),
        )
        ref_row = cur_ref.fetchone()
        if not ref_row:
            raise TransitionReject(404, "REFERRAL_NOT_FOUND", f"Referral {ref_id} not found")

        conn.execute("SELECT set_config('rhp.locked_referral', %s, true);", (str(ref_id),))
        head_ts = ref_row[20]
        ts = get_monotone_ts(conn, head_ts)
        conn.execute("SAVEPOINT sp_cmd;")
        sp_created = True

        referral = ReferralState({
            "id": ref_row[0],
            "version": ref_row[1],
            "hs_state": ref_row[2],
            "tr_state": ref_row[3],
            "mode": ref_row[4],
            "need_class": ref_row[5],
            "origin_facility_id": ref_row[6],
            "chain": ref_row[7],
            "ladder_cursor": ref_row[8],
            "lease_offer_id": ref_row[9],
            "lease_facility_id": ref_row[10],
            "lease_epoch": ref_row[11],
            "open_offers": ref_row[12],
            "tr_facility_id": ref_row[13],
            "mgso4_status": ref_row[14],
            "profile_id": ref_row[15],
            "profile_hash": ref_row[16],
            "paper_code": ref_row[17],
            "head_seq": ref_row[18],
            "head_hash": ref_row[19],
            "head_ts": ref_row[20],
            "outcome": ref_row[21],
            "created_by": ref_row[22],
            "created_at": ref_row[23],
            "closed_at": ref_row[24],
        })

    try:
        # ---------------------------------------------------------------------
        # STEP 5: Authority & Fencing (Invariants I6, I8)
        # ---------------------------------------------------------------------
        if referral is not None and cmd.expected_version is not None:
            if cmd.expected_version != referral.version:
                raise TransitionReject(
                    412,
                    "STALE_PRECONDITION",
                    f"Optimistic version mismatch: expected {cmd.expected_version}, current {referral.version}",
                )

        if referral is not None and cmd.expected_epoch is not None:
            if cmd.expected_epoch != referral.lease_epoch:
                raise TransitionReject(
                    412,
                    "STALE_PRECONDITION",
                    f"Optimistic epoch mismatch: expected {cmd.expected_epoch}, current {referral.lease_epoch}",
                )

        # ---------------------------------------------------------------------
        # STEP 6: Transition Guard & Child Table Locks (Address D-6, F1)
        # ---------------------------------------------------------------------
        # Global Lock Order: referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox
        cur_offers = conn.execute(
            "SELECT * FROM offer WHERE referral_id = %s ORDER BY id FOR UPDATE;",
            (str(ref_id),),
        )
        offer_rows = cur_offers.fetchall()

        cur_deadlines = conn.execute(
            "SELECT * FROM deadline WHERE referral_id = %s ORDER BY id FOR UPDATE;",
            (str(ref_id),),
        )
        deadline_rows = cur_deadlines.fetchall()

        offers_list: List[OfferState] = []
        for o_r in offer_rows:
            offers_list.append(OfferState({
                "id": o_r[0],
                "referral_id": o_r[1],
                "facility_id": o_r[2],
                "step": o_r[3],
                "source": o_r[4],
                "status": o_r[5],
                "counter_round": o_r[6],
                "counter_mask": o_r[7],
                "created_epoch": o_r[9],
                "created_at": o_r[10],
                "acked_at": o_r[11],
                "acked_by": o_r[12],
                "decided_at": o_r[13],
            }))

        target_offer: Optional[OfferState] = None
        cmd_offer_id = getattr(cmd, "offer_id", None)
        if not cmd_offer_id and cmd.type == "TIMEOUT" and getattr(cmd, "deadline_id", None):
            cmd_dl_id = str(cmd.deadline_id)
            for d_r in deadline_rows:
                if str(d_r[0]) == cmd_dl_id and d_r[2]:
                    cmd_offer_id = d_r[2]
                    break

        if cmd_offer_id:
            for o in offers_list:
                if str(o.id) == str(cmd_offer_id):
                    target_offer = o
                    break
        elif cmd.type == "CONFIRM_COUNTER":
            for o in offers_list:
                if o.status == "COUNTERED":
                    target_offer = o
                    break
            if not target_offer and offers_list:
                target_offer = max(offers_list, key=lambda x: (x.step, x.created_at))
        elif offers_list:
            target_offer = max(offers_list, key=lambda x: (x.step, x.created_at))

        # Role-Command Authorization check (Invariant I6)
        authorize(conn, referral, target_offer, session, cmd, ts)

        # Transition matrix lookup against spec/transitions.yaml
        target_tr_state = getattr(cmd, "tr_state", None)
        trans_def = TRANSITIONS.lookup(
            cmd.type,
            referral.as_dict() if referral else None,
            target_offer.as_dict() if target_offer else None,
            target_tr_state,
        )

        # ---------------------------------------------------------------------
        # STEP 7: Staleness & Live Reconfirmation Check (Address D-7, F12, I15)
        # ---------------------------------------------------------------------
        if cmd.type == "ACCEPT" or (cmd.type == "CONFIRM_COUNTER" and getattr(cmd, "confirmed", False)):
            if target_offer is not None:
                if target_offer.status not in ("OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"):
                    raise TransitionReject(
                        409,
                        "LATE_ACCEPT_REJECTED",
                        f"Offer {target_offer.id} is in status {target_offer.status} and cannot be accepted",
                    )

            # Invariant I15: live capability TTL check
            if referral is not None and target_offer is not None:
                cur_reqs = conn.execute(
                    """
                    SELECT r.capability, c.expires_at
                    FROM need_class_requirement r
                    LEFT JOIN offer_resource_confirmation c
                      ON c.offer_id = %s AND c.capability = r.capability
                    WHERE r.need_class = %s;
                    """,
                    (str(target_offer.id), referral.need_class),
                )
                req_rows = cur_reqs.fetchall()
                for r_cap, c_exp in req_rows:
                    if c_exp is None or c_exp <= ts:
                        raise TransitionReject(
                            409,
                            "STALE_CONFIRMATION_RECONFIRM_REQUIRED",
                            f"Required capability '{r_cap}' confirmation is missing or expired for offer {target_offer.id}",
                        )

        # ---------------------------------------------------------------------
        # STEP 8: Genuine PostgreSQL State Mutations for ALL 15 Commands (Address D-8)
        # ---------------------------------------------------------------------
        event_type: str = "REFERRAL_CREATED"
        event_detail: Dict[str, Any] = {}
        seq = (referral.head_seq + 1) if referral else 1

        # 1. CREATE
        if cmd.type == "CREATE":
            event_type = "REFERRAL_CREATED"
            (
                ref_id,
                initial_hs,
                open_offers,
                chain_list,
                paper_code,
                event_detail,
                created_offers,
                outbox_entries,
            ) = execute_create(conn, cmd, session, ts, ref_id)

            referral = ReferralState({
                "id": str(ref_id),
                "version": 1,
                "hs_state": initial_hs,
                "tr_state": "REQUESTED",
                "mode": cmd.mode,
                "need_class": cmd.need_class,
                "origin_facility_id": str(cmd.origin_facility_id),
                "chain": [str(c) for c in chain_list],
                "ladder_cursor": len(created_offers) - 1 if created_offers else 0,
                "lease_epoch": 0,
                "open_offers": open_offers,
                "mgso4_status": cmd.mgso4_status,
                "profile_id": cmd.profile_id,
                "paper_code": paper_code,
                "head_seq": 0,
                "head_hash": GENESIS_PREV_HASH_BYTES,
                "head_ts": ts,
            })

        # 2. ACK
        elif cmd.type == "ACK" and referral is not None and target_offer is not None:
            event_type = "OFFER_ACKED"
            event_detail = execute_ack(conn, referral, target_offer, session, cmd, ts)

        # 3. RESOURCE_CONFIRM
        elif cmd.type == "RESOURCE_CONFIRM" and referral is not None and target_offer is not None:
            event_type = "RESOURCE_CONFIRMED"
            event_detail = execute_resource_confirm(conn, referral, target_offer, session, cmd, ts)

        # 4. ACCEPT
        elif cmd.type == "ACCEPT" and referral is not None and target_offer is not None:
            event_type = "OFFER_ACCEPTED"
            event_detail = execute_accept(conn, referral, target_offer, session, cmd, ts)

        # 5. COUNTER
        elif cmd.type == "COUNTER" and referral is not None and target_offer is not None:
            event_type = "OFFER_COUNTERED"
            event_detail = execute_counter(conn, referral, target_offer, session, cmd, ts)

        # 6. CONFIRM_COUNTER
        elif cmd.type == "CONFIRM_COUNTER" and referral is not None and target_offer is not None:
            event_type = "COUNTER_RESOLVED"
            event_detail = execute_confirm_counter(conn, referral, target_offer, session, cmd, ts)

        # 7. DECLINE
        elif cmd.type == "DECLINE" and referral is not None and target_offer is not None:
            event_type = "OFFER_DECLINED"
            event_detail = execute_decline(conn, referral, target_offer, session, cmd, ts)

        # 8. TIMEOUT
        elif cmd.type == "TIMEOUT" and referral is not None:
            ev_type, ev_detail = execute_timeout(conn, referral, target_offer, session, cmd, ts)
            if ev_type is not None:
                event_type = ev_type
                event_detail = ev_detail
            else:
                event_type = "DEADLINE_TIMEOUT"
                event_detail = {"kind": getattr(cmd, "kind", "ACK"), "step": int(getattr(cmd, "step", 0) or 0)}

        # 9. ARRIVAL_REJECTED
        elif cmd.type == "ARRIVAL_REJECTED" and referral is not None:
            event_type = "ARRIVAL_REJECTED"
            event_detail = execute_arrival_rejected(conn, referral, session, cmd, ts)

        # 10. DISPATCHER_ASSIGN
        elif cmd.type == "DISPATCHER_ASSIGN" and referral is not None:
            event_type = "DISPATCHER_ASSIGNED"
            event_detail = execute_dispatcher_assign(conn, referral, session, cmd, ts)

        # 11. TR_UPDATE
        elif cmd.type == "TR_UPDATE" and referral is not None:
            new_tr = cmd.tr_state
            referral.tr_state = new_tr
            if new_tr == "ARRIVED":
                if referral.lease_facility_id and session.facility_id and str(referral.lease_facility_id) != str(session.facility_id):
                    event_type = "ARRIVAL_AT_NON_OWNER"
                    event_detail = {"reason": "ARRIVAL_AT_NON_OWNER", "facility": str(session.facility_id)}
                else:
                    if getattr(cmd, "source", "MANUAL") == "GEOFENCE":
                        event_type = "ARRIVAL_SUGGESTED"
                        event_detail = {"tr_state": "ARRIVED", "source": "GEOFENCE", "dwell_s": getattr(cmd, "dwell_s", 0) or 0}
                    else:
                        event_type = "TR_UPDATED"
                        event_detail = {"tr_state": "ARRIVED", "source": getattr(cmd, "source", "MANUAL"), "dwell_s": getattr(cmd, "dwell_s", 0) or 0}
            elif new_tr == "HANDED_OVER":
                event_type = "TR_UPDATED"
                conn.execute(
                    "UPDATE deadline SET status = 'DONE' WHERE referral_id = %s AND kind = 'HANDOVER' AND status = 'PENDING';",
                    (str(ref_id),),
                )
                conn.execute(
                    """
                    INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
                    VALUES (%s, %s, %s, 'CLOSURE', %s, %s, %s, %s);
                    """,
                    (str(uuid4()), str(ref_id), str(referral.lease_offer_id) if referral.lease_offer_id else None, 0, referral.lease_epoch, ts + timedelta(hours=2), ts),
                )
                event_detail = {"tr_state": "HANDED_OVER", "source": getattr(cmd, "source", "MANUAL"), "dwell_s": getattr(cmd, "dwell_s", 0) or 0}
            else:
                event_type = "TR_UPDATED"
                event_detail = {"tr_state": new_tr, "source": getattr(cmd, "source", "MANUAL"), "dwell_s": getattr(cmd, "dwell_s", 0) or 0}

        # 12. TR_DESTINATION_CHANGE
        elif cmd.type == "TR_DESTINATION_CHANGE" and referral is not None:
            event_type = "TR_DESTINATION_CHANGE"
            target_fac = getattr(cmd, "target_facility_id")
            referral.tr_facility_id = target_fac
            event_detail = {
                "facility": str(target_fac),
                "reason": str(getattr(cmd, "reason", "REROUTE")),
                "accepted": bool(getattr(cmd, "accepted", False)),
            }

        # 13. CANCEL
        elif cmd.type == "CANCEL" and referral is not None:
            event_type = "CANCELLED"
            event_detail = execute_cancel(conn, referral, session, cmd, ts)

        # 14. CLOSE
        elif cmd.type == "CLOSE" and referral is not None:
            event_type = "CLOSED"
            event_detail = execute_close(conn, referral, session, cmd, ts)

        # 15. REVOKE_GRANT
        elif cmd.type == "REVOKE_GRANT" and referral is not None:
            event_type = "GRANT_REVOKED"
            event_detail = execute_revoke_grant(conn, referral, session, cmd, ts)

        else:
            event_type = f"{cmd.type}_APPLIED"
            event_detail = {}

        # ---------------------------------------------------------------------
        # STEP 9: Append Hash-Chained Event & Outbox Rows (Invariants I4, I5, F9)
        # ---------------------------------------------------------------------
        validate_event_detail(event_type, event_detail)

        event_id = getattr(cmd, "event_id", None) or uuid4()
        core_event = {
            "referral_id": str(ref_id),
            "seq": seq,
            "type": event_type,
            "epoch": referral.lease_epoch if referral else 0,
            "detail": event_detail,
            "client_ts_ms": int(ts.timestamp() * 1000),
        }

        canonical_core = jcs(core_event)
        event_hash = compute_event_hash(referral.head_hash if referral else GENESIS_PREV_HASH_BYTES, core_event)

        # Insert Event row
        secret_hash_val = getattr(cmd, "secret_hash", None)
        conn.execute(
            """
            INSERT INTO event (
              referral_id, seq, event_id, type, actor_roster_id, actor_facility_id,
              channel, proxy, proxy_for, epoch, detail, secret_hash, client_ts_ms,
              server_ts, prev_hash, hash
            ) VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
            """,
            (
                str(ref_id), seq, str(event_id), event_type, str(session.roster_id),
                str(session.facility_id) if session.facility_id else None,
                cmd.channel, cmd.proxy, str(cmd.proxy_for) if cmd.proxy_for else None,
                referral.lease_epoch if referral else 0, json.dumps(event_detail),
                secret_hash_val, core_event["client_ts_ms"], ts,
                referral.head_hash if referral else GENESIS_PREV_HASH_BYTES, event_hash,
            ),
        )

        # Update Referral head pointers & state
        if referral:
            referral.head_seq = seq
            referral.head_hash = event_hash
            referral.head_ts = ts
            referral.version += 1

            conn.execute(
                """
                UPDATE referral
                SET version = %s, hs_state = %s, tr_state = %s, ladder_cursor = %s,
                    lease_offer_id = %s, lease_facility_id = %s, lease_epoch = %s,
                    open_offers = %s, tr_facility_id = %s, head_seq = %s, head_hash = %s,
                    head_ts = %s, outcome = %s, closed_at = %s
                WHERE id = %s;
                """,
                (
                    referral.version, referral.hs_state, referral.tr_state, referral.ladder_cursor,
                    str(referral.lease_offer_id) if referral.lease_offer_id else None,
                    str(referral.lease_facility_id) if referral.lease_facility_id else None,
                    referral.lease_epoch, referral.open_offers,
                    str(referral.tr_facility_id) if referral.tr_facility_id else None,
                    referral.head_seq, referral.head_hash, referral.head_ts, referral.outcome,
                    referral.closed_at, str(ref_id),
                ),
            )

        # Insert Outbox Row (locked last in global lock hierarchy)
        conn.execute(
            """
            INSERT INTO outbox (
              referral_id, event_seq, channel, kind, status, visible_after, created_at
            ) VALUES (
              %s, %s, 'SSE', %s, 'PENDING', %s, %s
            );
            """,
            (str(ref_id), seq, event_type, ts, ts),
        )

        # ---------------------------------------------------------------------
        # STEP 10: Finalize & Mark Idempotency DONE
        # ---------------------------------------------------------------------
        resp_payload = {
            "status": "COMMITTED",
            "referral_id": str(ref_id),
            "version": referral.version if referral else 1,
            "head_seq": seq,
            "head_hash": event_hash.hex(),
            "event_id": str(event_id),
        }

        conn.execute(
            """
            UPDATE idempotency
            SET status = 'DONE', http_status = 200, response = %s
            WHERE actor_id = %s AND key = %s;
            """,
            (json.dumps(resp_payload), str(actor_id), str(idem_key)),
        )

        return 200, resp_payload

    except TransitionReject as exc:
        # ---------------------------------------------------------------------
        # SAVEPOINT REJECTION HANDLER (Architecture §5 Step 10)
        # ---------------------------------------------------------------------
        # Roll back state changes made after the savepoint if savepoint was created
        if sp_created:
            try:
                conn.execute("ROLLBACK TO SAVEPOINT sp_cmd;")
            except Exception:
                pass

        err_response = {
            "status": "REJECTED",
            "reason": exc.reason_code,
            "message": exc.message,
            "command": cmd_type,
        }

        # Log audit entry into rejected_command if actor is identified
        if actor_id:
            try:
                conn.execute(
                    """
                    INSERT INTO rejected_command (
                      actor_id, key, referral_id, command, http_status, reason_code, session_id, created_at
                    ) VALUES (
                      %s, %s, %s, %s, %s, %s, %s, %s
                    );
                    """,
                    (
                        str(actor_id), str(idem_key), str(ref_id) if ref_id else None,
                        cmd_type, exc.http_status, exc.reason_code, str(session.id) if session else None, ts,
                    ),
                )
            except Exception:
                pass

        # Store deterministic rejection in idempotency table so replays return exact outcome
        if actor_id and idem_key:
            try:
                conn.execute(
                    """
                    UPDATE idempotency
                    SET status = 'DONE', http_status = %s, response = %s
                    WHERE actor_id = %s AND key = %s;
                    """,
                    (exc.http_status, json.dumps(err_response), str(actor_id), str(idem_key)),
                )
            except Exception:
                pass

        return exc.http_status, err_response
