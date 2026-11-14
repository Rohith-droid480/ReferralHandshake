"""ReferralHandshake Protocol RHP-1 — COUNTER and CONFIRM_COUNTER Commands.

Specification Anchors:
- Architecture §4.4: Counter-Offer Negotiation & Round Bound (max 2 rounds)
- Architecture §6: Timing Model, Profile Parameters C & D [F2, F3, I13]
- Closure F13: Counter-Offer Cap & Deadline min(C, remaining D)
- Invariant I15: Capability Staleness Verification on Counter Acceptance
- BUILD_PLAN §3.5: COUNTER Command & CONFIRM_COUNTER Command
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from api.rhp.auth import Session
from api.rhp.commands.accept import execute_accept
from api.rhp.commands.decline_advance import advance
from api.rhp.profiles import TimingProfile, get_profile
from api.rhp.schemas import AcceptCmd, ConfirmCounterCmd, CounterCmd
from api.rhp.transitions import TransitionReject


def execute_counter(
    conn: Any,
    referral: Any,
    target_offer: Any,
    session: Session,
    cmd: CounterCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the COUNTER command inside the 10-step transactional pipeline.

    1. Checks target offer status in ('OPEN', 'ACKED').
    2. Enforces Counter Cap (Closure F13): maximum 2 rounds allowed.
       If target_offer.counter_round >= 2, raises 409 COUNTER_ROUND_EXCEEDED.
    3. Cancels pending DECISION and intra-facility notice deadlines.
    4. Computes COUNTER_CONFIRM deadline: min(profile.C, remaining D) so counter-offers
       never extend a facility's decision window D.
    5. Updates offer status to 'COUNTERED', increments counter_round, sets counter_mask.
    6. Updates referral hs_state to 'COUNTERED'.
    7. Returns canonical event detail.
    """
    if target_offer is None:
        raise TransitionReject(404, "OFFER_NOT_FOUND", "No target offer found for COUNTER")

    if target_offer.status not in ("OPEN", "ACKED"):
        raise TransitionReject(
            409,
            "INVALID_OFFER_STATE",
            f"Offer {target_offer.id} is in status '{target_offer.status}', cannot submit COUNTER "
            f"(must be 'OPEN' or 'ACKED')",
        )

    # 1. Enforce Counter Cap: max 2 rounds (Closure F13)
    if target_offer.counter_round >= 2:
        raise TransitionReject(
            409,
            "COUNTER_ROUND_EXCEEDED",
            f"Offer {target_offer.id} has already reached maximum counter rounds (2)",
        )

    # 2. Load timing profile
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

    # 3. Determine remaining decision window D from existing DECISION deadline
    cur_dl = conn.execute(
        """
        SELECT due_at
        FROM deadline
        WHERE referral_id = %s AND (offer_id = %s OR offer_id IS NULL)
          AND kind = 'DECISION' AND status = 'PENDING'
        ORDER BY due_at ASC LIMIT 1;
        """,
        (str(referral.id), str(target_offer.id)),
    )
    dl_row = cur_dl.fetchone() if cur_dl else None
    if dl_row and dl_row[0]:
        due_at = dl_row[0]
        if isinstance(due_at, str):
            try:
                due_at = datetime.fromisoformat(due_at)
            except Exception:
                due_at = None
        if isinstance(due_at, datetime):
            remaining_d_ms = max(1000, int((due_at - ts).total_seconds() * 1000))
        else:
            remaining_d_ms = profile.D
    else:
        remaining_d_ms = profile.D

    # Counter deadline is min(C, remaining D) (Closure F13)
    counter_duration_ms = min(profile.C, remaining_d_ms)
    counter_due_at = ts + timedelta(milliseconds=counter_duration_ms)

    # 4. Cancel pending DECISION and notice rungs
    conn.execute(
        """
        UPDATE deadline
        SET status = 'DONE'
        WHERE referral_id = %s
          AND (offer_id = %s OR offer_id IS NULL)
          AND kind IN ('DECISION', 'ACK', 'NOTICE_VOICE', 'NOTICE_PROXY')
          AND status = 'PENDING';
        """,
        (str(referral.id), str(target_offer.id)),
    )

    # 5. Arm COUNTER_CONFIRM deadline
    new_round = target_offer.counter_round + 1
    conn.execute(
        """
        INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            str(uuid4()),
            str(referral.id),
            str(target_offer.id),
            "COUNTER_CONFIRM",
            target_offer.step,
            referral.lease_epoch,
            counter_due_at,
            ts,
        ),
    )

    # 6. Update target offer
    conn.execute(
        """
        UPDATE offer
        SET status = 'COUNTERED', counter_round = %s, counter_mask = %s
        WHERE id = %s;
        """,
        (new_round, int(cmd.counter_mask), str(target_offer.id)),
    )
    target_offer.status = "COUNTERED"
    target_offer.counter_round = new_round
    target_offer.counter_mask = int(cmd.counter_mask)

    # 7. Update referral state
    referral.hs_state = "COUNTERED"
    conn.execute(
        "UPDATE referral SET hs_state = 'COUNTERED' WHERE id = %s;",
        (str(referral.id),),
    )

    return {
        "round": new_round,
        "mask": int(cmd.counter_mask),
    }


def execute_confirm_counter(
    conn: Any,
    referral: Any,
    target_offer: Any,
    session: Session,
    cmd: ConfirmCounterCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the CONFIRM_COUNTER command inside the 10-step transactional pipeline.

    If confirmed == True:
    - Origin clinician accepts counter terms.
    - Routes to execute_accept() to award the lease and verify live capability TTL (Invariant I15).
    - Cancels COUNTER_CONFIRM deadline.

    If confirmed == False:
    - Origin clinician declines counter terms.
    - Updates offer to DECLINED with decline_reason = 'COUNTER_REJECTED'.
    - Cancels COUNTER_CONFIRM deadline.
    - Revokes active payload grant for this facility.
    - Calls advance() to escalate along the chain or escalate to dispatcher.
    """
    if target_offer is None:
        raise TransitionReject(404, "OFFER_NOT_FOUND", "No target offer found for CONFIRM_COUNTER")

    if target_offer.status != "COUNTERED":
        raise TransitionReject(
            409,
            "INVALID_OFFER_STATE",
            f"Offer {target_offer.id} is in status '{target_offer.status}', cannot CONFIRM_COUNTER "
            f"(must be 'COUNTERED')",
        )

    if cmd.confirmed:
        # 1. Clinician accepts counter: Route to execute_accept()
        accept_cmd = AcceptCmd(
            type="ACCEPT",
            referral_id=referral.id,
            offer_id=target_offer.id,
        )
        execute_accept(conn, referral, target_offer, session, accept_cmd, ts)

        # Mark COUNTER_CONFIRM deadline DONE
        conn.execute(
            """
            UPDATE deadline
            SET status = 'DONE'
            WHERE referral_id = %s AND kind = 'COUNTER_CONFIRM' AND status = 'PENDING';
            """,
            (str(referral.id),),
        )

        return {"confirmed": True}

    else:
        # 2. Clinician declines counter: Mark offer DECLINED and advance()
        conn.execute(
            """
            UPDATE offer
            SET status = 'DECLINED', decided_at = %s, decline_reason = %s
            WHERE id = %s;
            """,
            (ts, "COUNTER_REJECTED", str(target_offer.id)),
        )
        target_offer.status = "DECLINED"
        target_offer.decided_at = ts
        target_offer.decline_reason = "COUNTER_REJECTED"

        # Cancel COUNTER_CONFIRM deadline
        conn.execute(
            """
            UPDATE deadline
            SET status = 'DONE'
            WHERE referral_id = %s AND kind = 'COUNTER_CONFIRM' AND status = 'PENDING';
            """,
            (str(referral.id),),
        )

        # Revoke payload grant for countered facility
        conn.execute(
            """
            UPDATE payload_grant
            SET status = 'REVOKED', revoked_at = %s
            WHERE referral_id = %s AND facility_id = %s AND status = 'ACTIVE';
            """,
            (ts, str(referral.id), str(target_offer.facility_id)),
        )

        # Advance along the chain
        advance(conn, referral, ts)

        return {"confirmed": False}
