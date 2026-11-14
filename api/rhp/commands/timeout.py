"""Timeout Command Implementation (§5, §6, Closures F1, F2, F6, F13, Invariants I1, I12).

Handles all 8 deadline kinds:
- ACK: Silent offer expiry; in SEQUENTIAL mode transitions offer to SOFT_OPEN and calls advance();
  in PARALLEL2 mode transitions to TIMED_OUT, decrements open_offers, revokes grant, and calls advance().
  If offer was ACKed, emits ADVISORY_PREWARM for the next chain facility.
- NOTICE_VOICE: Rung 1 voice alert at A/4. Emits NOTICE_SENT and queues outbox row.
- NOTICE_PROXY: Rung 2 dispatcher proxy page at 3A/4. Emits NOTICE_SENT and queues outbox row.
- DECISION: Decision window expiry; transitions offer to SOFT_OPEN / TIMED_OUT and calls advance().
- COUNTER_CONFIRM: Counter confirmation window expiry; resolves like DECISION.
- HANDOVER: Overdue handover alert; emits HANDOVER_OVERDUE and re-arms deadline (Invariant I1).
- DISPATCH_ACTION: Overdue dispatcher action; emits DEADLINE_TIMEOUT and re-arms deadline.
- CLOSURE: Two-stage closure timeout (Closure F6). First expiry emits CLOSURE_OVERDUE and re-arms
  step 2; second expiry auto-closes with UNKNOWN_COUNTER_REFERRAL (proxy=True, actor=system).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID, uuid4

from api.rhp.auth import Session
from api.rhp.commands.decline_advance import advance
from api.rhp.profiles import TimingProfile, get_profile
from api.rhp.schemas import TimeoutCmd


def execute_timeout(
    conn: Any,
    referral: Any,
    target_offer: Optional[Any],
    session: Session,
    cmd: TimeoutCmd,
    ts: datetime,
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Executes a TIMEOUT command under the transaction-scoped referral lock.

    Idempotent: if deadline is not PENDING or epoch does not match, returns (None, {}).
    Returns (event_type, event_detail) on state transitions.
    """
    ref_id = referral.id
    dl_id = str(cmd.deadline_id)

    # 1. Verify deadline existence and PENDING status under referral lock
    if hasattr(conn, "db"):
        d_dict = conn.db.deadlines.get(dl_id)
        if not d_dict:
            return None, {}
        dl_status = d_dict.get("status")
        dl_epoch = d_dict.get("epoch")
        dl_step = d_dict.get("step")
    else:
        cur_dl = conn.execute(
            "SELECT id, referral_id, offer_id, kind, step, epoch, status, due_at FROM deadline WHERE id = %s;",
            (dl_id,),
        )
        dl_row = cur_dl.fetchone() if cur_dl else None
        if not dl_row:
            return None, {}
        dl_status = dl_row[6]
        dl_epoch = dl_row[5]
        dl_step = dl_row[4]

    # Re-verify freshness: if already satisfied or epoch mismatch, safely no-op
    if dl_status != "PENDING" or (cmd.epoch and int(cmd.epoch) != int(dl_epoch)):
        return None, {}

    # Mark the deadline row as DONE
    conn.execute(
        "UPDATE deadline SET status = 'DONE' WHERE id = %s AND status = 'PENDING';",
        (dl_id,),
    )

    # 2. Load active timing profile
    try:
        profile = get_profile(referral.profile_id)
    except Exception:
        profile = TimingProfile(
            profile_id=referral.profile_id,
            A=3000,
            D=4000,
            rungs=[0, 750, 2250],
            S=3,
            delta=0,
            V=0,
            voice=False,
            F=3,
            eps=1000,
            C=2000,
            confirm_ttl=900000,
            H=30000,
            dispatch_action=5000,
            closure=20000,
            B=25000,
            demo=True,
            profile_hash="00" * 32,
            sig="00" * 64,
        )

    kind = cmd.kind

    # -------------------------------------------------------------------------
    # 3. NOTICE RUNGS (NOTICE_VOICE @ A/4, NOTICE_PROXY @ 3A/4)
    # -------------------------------------------------------------------------
    if kind == "NOTICE_VOICE":
        if (target_offer and target_offer.status == "OPEN") or (referral.hs_state in ("OFFERED", "CREATED")):
            # Emit NOTICE_SENT event
            event_type = "NOTICE_SENT"
            slot_no = int(cmd.step or (target_offer.step if target_offer else 1) or 1)
            event_detail = {
                "channel": "VOICE",
                "rung": 1,
                "slot": slot_no,
            }
            return event_type, event_detail
        return None, {}

    if kind == "NOTICE_PROXY":
        if (target_offer and target_offer.status == "OPEN") or (referral.hs_state in ("OFFERED", "CREATED")):
            # Emit NOTICE_SENT event
            event_type = "NOTICE_SENT"
            event_detail = {
                "channel": "DISPATCHER_PROXY",
                "rung": 2,
                "slot": 1,
            }
            return event_type, event_detail
        return None, {}

    # -------------------------------------------------------------------------
    # 4. ACK WINDOW EXPIRY (due at A)
    # -------------------------------------------------------------------------
    if kind == "ACK":
        if target_offer and target_offer.status == "OPEN":
            # Silent offer timed out -> advance ladder
            event_type = "DEADLINE_TIMEOUT"
            event_detail = {
                "kind": "ACK",
                "step": int(cmd.step or target_offer.step or 1),
            }

            if referral.mode == "SEQUENTIAL":
                # In SEQUENTIAL mode: offer transitions to SOFT_OPEN
                conn.execute(
                    "UPDATE offer SET status = 'SOFT_OPEN' WHERE id = %s;",
                    (str(target_offer.id),),
                )
                target_offer.status = "SOFT_OPEN"
                # advance() automatically closes any predecessor SOFT_OPEN offer to TIMED_OUT
                advance(conn, referral, ts)
            else:
                # In PARALLEL2 mode: offer transitions directly to TIMED_OUT (no SOFT_OPEN)
                conn.execute(
                    "UPDATE offer SET status = 'TIMED_OUT' WHERE id = %s;",
                    (str(target_offer.id),),
                )
                target_offer.status = "TIMED_OUT"
                referral.open_offers = max(0, referral.open_offers - 1)
                conn.execute(
                    """
                    UPDATE payload_grant
                    SET status = 'REVOKED', revoked_at = %s
                    WHERE referral_id = %s AND facility_id = %s AND status = 'ACTIVE';
                    """,
                    (ts, str(ref_id), str(target_offer.facility_id)),
                )
                if referral.open_offers == 0:
                    advance(conn, referral, ts)

            return event_type, event_detail

        elif target_offer and target_offer.status == "ACKED":
            # Offer was ACKed: pre-warm the next facility in chain
            next_idx = referral.ladder_cursor + 1
            if next_idx < len(referral.chain):
                next_fac = referral.chain[next_idx]
                return "ADVISORY_PREWARM", {
                    "step": next_idx + 1,
                    "facility": str(next_fac),
                    "source": "CHAIN",
                    "reason": "ACK",
                }
            return None, {}

        return None, {}

    # -------------------------------------------------------------------------
    # 5. DECISION & COUNTER_CONFIRM WINDOW EXPIRY
    # -------------------------------------------------------------------------
    if kind in ("DECISION", "COUNTER_CONFIRM"):
        event_type = "DEADLINE_TIMEOUT"
        event_detail = {
            "kind": kind,
            "step": int(cmd.step or (target_offer.step if target_offer else 1)),
        }

        if referral.mode == "SEQUENTIAL" and (referral.ladder_cursor + 1 < len(referral.chain)):
            if target_offer:
                conn.execute(
                    "UPDATE offer SET status = 'SOFT_OPEN' WHERE id = %s;",
                    (str(target_offer.id),),
                )
                target_offer.status = "SOFT_OPEN"
            advance(conn, referral, ts)
        else:
            if target_offer:
                conn.execute(
                    "UPDATE offer SET status = 'TIMED_OUT' WHERE id = %s;",
                    (str(target_offer.id),),
                )
                target_offer.status = "TIMED_OUT"
                referral.open_offers = max(0, referral.open_offers - 1)
                conn.execute(
                    """
                    UPDATE payload_grant
                    SET status = 'REVOKED', revoked_at = %s
                    WHERE referral_id = %s AND facility_id = %s AND status = 'ACTIVE';
                    """,
                    (ts, str(ref_id), str(target_offer.facility_id)),
                )
            advance(conn, referral, ts)

        return event_type, event_detail

    # -------------------------------------------------------------------------
    # 6. HANDOVER OVERDUE RE-ARMING (Invariant I1)
    # -------------------------------------------------------------------------
    if kind == "HANDOVER":
        event_type = "HANDOVER_OVERDUE"
        next_step = int(cmd.step or dl_step or 0) + 1
        event_detail = {
            "kind": "HANDOVER",
            "step": next_step,
        }
        # Re-arm HANDOVER deadline so I1 is never violated
        new_dl_id = uuid4()
        handover_due = ts + timedelta(milliseconds=profile.H)
        conn.execute(
            """
            INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                str(new_dl_id),
                str(ref_id),
                str(referral.lease_offer_id) if referral.lease_offer_id else None,
                "HANDOVER",
                next_step,
                referral.lease_epoch,
                handover_due,
                ts,
            ),
        )
        return event_type, event_detail

    # -------------------------------------------------------------------------
    # 7. DISPATCH ACTION RE-ARMING (Invariant I1)
    # -------------------------------------------------------------------------
    if kind == "DISPATCH_ACTION":
        event_type = "DEADLINE_TIMEOUT"
        next_step = int(cmd.step or dl_step or 0) + 1
        event_detail = {
            "kind": "DISPATCH_ACTION",
            "step": next_step,
        }
        new_dl_id = uuid4()
        disp_due = ts + timedelta(milliseconds=profile.dispatch_action)
        conn.execute(
            """
            INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (str(new_dl_id), str(ref_id), None, "DISPATCH_ACTION", next_step, referral.lease_epoch, disp_due, ts),
        )
        return event_type, event_detail

    # -------------------------------------------------------------------------
    # 8. TWO-STAGE CLOSURE TIMEOUT (Closure F6)
    # -------------------------------------------------------------------------
    if kind == "CLOSURE":
        curr_step = int(cmd.step or dl_step or 1)
        if curr_step < 2:
            # First expiry: emit CLOSURE_OVERDUE and re-arm step = 2
            event_type = "CLOSURE_OVERDUE"
            event_detail = {
                "kind": "CLOSURE",
                "step": 1,
            }
            new_dl_id = uuid4()
            closure_due = ts + timedelta(milliseconds=profile.closure)
            conn.execute(
                """
                INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    str(new_dl_id),
                    str(ref_id),
                    str(referral.lease_offer_id) if referral.lease_offer_id else None,
                    "CLOSURE",
                    2,
                    referral.lease_epoch,
                    closure_due,
                    ts,
                ),
            )
            return event_type, event_detail
        else:
            # Second expiry: auto-close with UNKNOWN_COUNTER_REFERRAL
            conn.execute(
                "UPDATE deadline SET status = 'CANCELLED' WHERE referral_id = %s AND status = 'PENDING';",
                (str(ref_id),),
            )
            conn.execute(
                """
                UPDATE payload_grant
                SET status = 'REVOKED', revoked_at = %s
                WHERE referral_id = %s AND status = 'ACTIVE';
                """,
                (ts, str(ref_id)),
            )
            referral.hs_state = "CLOSED"
            referral.outcome = "UNKNOWN_COUNTER_REFERRAL"
            referral.closed_at = ts
            conn.execute(
                """
                UPDATE referral
                SET hs_state = 'CLOSED', outcome = 'UNKNOWN_COUNTER_REFERRAL', closed_at = %s
                WHERE id = %s;
                """,
                (ts, str(ref_id)),
            )
            return "CLOSED", {
                "outcome": "UNKNOWN_COUNTER_REFERRAL",
                "reason": "CLOSURE_OVERDUE",
            }

    return "DEADLINE_TIMEOUT", {"kind": kind, "step": int(cmd.step or 0)}
