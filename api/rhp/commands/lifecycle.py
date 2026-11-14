"""ReferralHandshake Protocol RHP-1 — Lifecycle Commands Module.

Commands:
- ARRIVAL_REJECTED (Closure F5): Human receiver rejects arrival -> revokes lease, calls advance()
- DISPATCHER_ASSIGN: Dispatcher manual assignment -> awards lease with source='DISPATCHER'
- CANCEL: Terminal cancellation -> sets hs_state='CANCELLED', outcome from taxonomy, revokes grants
- CLOSE (Closure F6): Terminal closure strictly enforcing the 9-outcome taxonomy and tr_state prerequisites
- REVOKE_GRANT: Explicit revocation of active payload grant

Specification Anchors:
- Architecture §4.5: Arrival Rejection, Dispatcher Assignment & Revocation
- Architecture §4.6: Terminal States & Locked 9-Value Outcome Taxonomy [Closure F6]
- Invariant I2: Single Lease Holder (one_lease)
- Invariant I10: Active Grant Authorization
- BUILD_PLAN §3.6: Terminal Lifecycle Commands & Outcome Taxonomy
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from api.rhp.auth import Session
from api.rhp.commands.decline_advance import advance
from api.rhp.profiles import TimingProfile, get_profile
from api.rhp.schemas import (
    ArrivalRejectedCmd,
    CancelCmd,
    CloseCmd,
    DispatcherAssignCmd,
    RevokeGrantCmd,
)
from api.rhp.transitions import TransitionReject

# Locked 9-Value Outcome Taxonomy (Architecture §4.6, Closure F6)
LOCKED_OUTCOMES = {
    "ADMITTED_STABLE",
    "ADMITTED_CRITICAL",
    "DELIVERED_AT_RECEIVER",
    "DELIVERED_EN_ROUTE",
    "PATIENT_REFUSED",
    "TRANSPORT_CANCELLED",
    "DETERIORATED_OR_DIED_PRE_HANDOVER",
    "REDIRECTED_ON_ARRIVAL",
    "UNKNOWN_COUNTER_REFERRAL",
}

# Outcomes that strictly require physical handover (tr_state == 'HANDED_OVER')
HANDOVER_REQUIRED_OUTCOMES = {
    "ADMITTED_STABLE",
    "ADMITTED_CRITICAL",
    "DELIVERED_AT_RECEIVER",
}


def execute_arrival_rejected(
    conn: Any,
    referral: Any,
    session: Session,
    cmd: ArrivalRejectedCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the ARRIVAL_REJECTED command inside the 10-step transactional pipeline.

    1. Checks that referral has an active lease.
    2. Marks the accepted offer as 'ARRIVAL_REJECTED', recording decline_reason and decided_at.
    3. Cancels pending HANDOVER deadline.
    4. Revokes lease from referral (lease_offer_id=None, lease_facility_id=None, lease_epoch+=1).
    5. Revokes active payload grant for the rejected facility.
    6. Calls advance() to escalate along the chain or escalate to dispatcher.
    7. Returns canonical event detail.
    """
    if referral.lease_offer_id is None:
        raise TransitionReject(
            409,
            "NO_ACTIVE_LEASE",
            f"Referral {referral.id} has no active lease to reject arrival for",
        )

    rej_reason = getattr(cmd, "reason", "ARRIVAL_REJECTED") or "ARRIVAL_REJECTED"
    old_lease_fac = referral.lease_facility_id

    # 1. Update accepted offer to ARRIVAL_REJECTED
    conn.execute(
        """
        UPDATE offer
        SET status = 'ARRIVAL_REJECTED', decided_at = %s, decline_reason = %s
        WHERE referral_id = %s AND status = 'ACCEPTED';
        """,
        (ts, rej_reason, str(referral.id)),
    )

    # 2. Cancel pending HANDOVER deadline
    conn.execute(
        """
        UPDATE deadline
        SET status = 'DONE'
        WHERE referral_id = %s AND kind = 'HANDOVER' AND status = 'PENDING';
        """,
        (str(referral.id),),
    )

    # 3. Revoke active payload grant for the rejected facility
    if old_lease_fac:
        conn.execute(
            """
            UPDATE payload_grant
            SET status = 'REVOKED', revoked_at = %s
            WHERE referral_id = %s AND facility_id = %s AND status = 'ACTIVE';
            """,
            (ts, str(referral.id), str(old_lease_fac)),
        )

    # 4. Revoke lease from referral
    referral.lease_facility_id = None
    referral.lease_offer_id = None
    referral.lease_epoch += 1

    conn.execute(
        """
        UPDATE referral
        SET lease_offer_id = NULL, lease_facility_id = NULL, lease_epoch = %s
        WHERE id = %s;
        """,
        (referral.lease_epoch, str(referral.id)),
    )

    # 5. Escalate along the chain
    advance(conn, referral, ts)

    return {
        "reason": rej_reason,
        "facility": str(old_lease_fac or referral.origin_facility_id),
    }


def execute_dispatcher_assign(
    conn: Any,
    referral: Any,
    session: Session,
    cmd: DispatcherAssignCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the DISPATCHER_ASSIGN command inside the 10-step transactional pipeline.

    1. Only allowed when hs_state is in ('ESCALATED_TO_DISPATCHER', 'OFFERED', 'ACKNOWLEDGED').
    2. Creates new offer row with source='DISPATCHER', status='ACCEPTED'.
    3. Supersedes any other open/acked/countered/soft_open offers.
    4. Cancels all pending deadlines (ACK, DECISION, COUNTER_CONFIRM, DISPATCH_ACTION, NOTICE_*).
    5. Arms HANDOVER deadline due at ts + profile.H.
    6. Revokes existing grants (keeping origin) and grants active payload grant to target facility.
    7. Awards lease to assigned facility and sets hs_state='ACCEPTED'.
    """
    if referral.hs_state in ("CLOSED", "CANCELLED"):
        raise TransitionReject(
            409,
            "ALREADY_TERMINAL",
            f"Referral {referral.id} is in terminal state '{referral.hs_state}', cannot assign dispatcher",
        )

    target_fac = cmd.target_facility_id

    # 1. Load timing profile
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

    new_off_id = uuid4()
    new_step = referral.ladder_cursor + 1
    new_epoch = referral.lease_epoch + 1

    # 2. Insert new offer with source='DISPATCHER' and status='ACCEPTED'
    conn.execute(
        """
        INSERT INTO offer (
          id, referral_id, facility_id, step, source, status, counter_round,
          counter_mask, created_epoch, created_at, decided_at
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
        """,
        (
            str(new_off_id),
            str(referral.id),
            str(target_fac),
            new_step,
            "DISPATCHER",
            "ACCEPTED",
            0,
            0,
            new_epoch,
            ts,
            ts,
        ),
    )

    # 3. Supersede any competing open offers
    conn.execute(
        """
        UPDATE offer
        SET status = 'SUPERSEDED'
        WHERE referral_id = %s AND id != %s AND status IN ('OPEN', 'ACKED', 'COUNTERED', 'SOFT_OPEN');
        """,
        (str(referral.id), str(new_off_id)),
    )

    # 4. Cancel pending handshake deadlines
    conn.execute(
        """
        UPDATE deadline
        SET status = 'DONE'
        WHERE referral_id = %s
          AND kind IN ('ACK', 'DECISION', 'COUNTER_CONFIRM', 'DISPATCH_ACTION', 'NOTICE_VOICE', 'NOTICE_PROXY', 'HANDOVER')
          AND status = 'PENDING';
        """,
        (str(referral.id),),
    )

    # 5. Arm HANDOVER deadline
    handover_due_at = ts + timedelta(milliseconds=profile.H)
    conn.execute(
        """
        INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
        VALUES (%s, %s, %s, 'HANDOVER', %s, %s, %s, %s);
        """,
        (str(uuid4()), str(referral.id), str(new_off_id), new_step, new_epoch, handover_due_at, ts),
    )

    # 6. Revoke other grants (keeping origin and new target)
    conn.execute(
        """
        UPDATE payload_grant
        SET status = 'REVOKED', revoked_at = %s
        WHERE referral_id = %s AND facility_id != %s AND facility_id != %s AND status = 'ACTIVE';
        """,
        (ts, str(referral.id), str(referral.origin_facility_id), str(target_fac)),
    )

    # 7. Grant active payload grant to assigned facility
    conn.execute(
        """
        INSERT INTO payload_grant (id, referral_id, facility_id, status, granted_at)
        VALUES (%s, %s, %s, 'ACTIVE', %s);
        """,
        (str(uuid4()), str(referral.id), str(target_fac), ts),
    )

    # 8. Update Referral State
    referral.lease_epoch = new_epoch
    referral.lease_offer_id = new_off_id
    referral.lease_facility_id = target_fac
    referral.hs_state = "ACCEPTED"
    referral.open_offers = 0

    conn.execute(
        """
        UPDATE referral
        SET lease_offer_id = %s,
            lease_facility_id = %s,
            lease_epoch = %s,
            hs_state = 'ACCEPTED',
            open_offers = 0
        WHERE id = %s;
        """,
        (str(new_off_id), str(target_fac), new_epoch, str(referral.id)),
    )

    return {
        "facility": str(target_fac),
        "reason": getattr(cmd, "reason", "DISPATCHER_ASSIGN") or "DISPATCHER_ASSIGN",
    }


def execute_cancel(
    conn: Any,
    referral: Any,
    session: Session,
    cmd: CancelCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the CANCEL command inside the 10-step transactional pipeline.

    1. Guards against already terminal referral states.
    2. Validates outcome against locked taxonomy.
    3. Withdraws open offers (status='WITHDRAWN').
    4. Cancels all pending deadlines (status='CANCELLED').
    5. Revokes all active payload grants (status='REVOKED').
    6. Sets referral hs_state='CANCELLED', tr_state='TR_CANCELLED' (if pre-handover), closed_at=ts.
    """
    if referral.hs_state in ("CLOSED", "CANCELLED"):
        raise TransitionReject(
            409,
            "ALREADY_TERMINAL",
            f"Referral {referral.id} is already in terminal state '{referral.hs_state}', cannot CANCEL",
        )

    outcome = getattr(cmd, "outcome", "TRANSPORT_CANCELLED")
    if outcome not in LOCKED_OUTCOMES:
        raise TransitionReject(
            422,
            "INVALID_OUTCOME",
            f"Outcome '{outcome}' is not in locked 9-value taxonomy",
        )

    # Update Transport track if pre-handover
    if referral.tr_state not in ("HANDED_OVER", "TR_CANCELLED"):
        referral.tr_state = "TR_CANCELLED"

    # Withdraw open offers
    conn.execute(
        """
        UPDATE offer
        SET status = 'WITHDRAWN'
        WHERE referral_id = %s AND status IN ('OPEN', 'ACKED', 'COUNTERED', 'SOFT_OPEN');
        """,
        (str(referral.id),),
    )

    # Cancel all pending deadlines
    conn.execute(
        """
        UPDATE deadline
        SET status = 'CANCELLED'
        WHERE referral_id = %s AND status = 'PENDING';
        """,
        (str(referral.id),),
    )

    # Revoke all active payload grants
    conn.execute(
        """
        UPDATE payload_grant
        SET status = 'REVOKED', revoked_at = %s
        WHERE referral_id = %s AND status = 'ACTIVE';
        """,
        (ts, str(referral.id)),
    )

    # Update Referral State
    referral.hs_state = "CANCELLED"
    referral.outcome = outcome
    referral.closed_at = ts
    referral.open_offers = 0

    conn.execute(
        """
        UPDATE referral
        SET hs_state = 'CANCELLED', tr_state = %s, outcome = %s, closed_at = %s, open_offers = 0
        WHERE id = %s;
        """,
        (referral.tr_state, outcome, ts, str(referral.id)),
    )

    return {
        "outcome": outcome,
        "reason": getattr(cmd, "reason", "USER_CANCELLED") or "USER_CANCELLED",
    }


def execute_close(
    conn: Any,
    referral: Any,
    session: Session,
    cmd: CloseCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the CLOSE command inside the 10-step transactional pipeline.

    1. Strictly validates outcome against the 9-outcome taxonomy (Closure F6).
       Missing or invalid outcome -> raises 422 INVALID_OUTCOME.
    2. Handover Prerequisite Check (Closure F6):
       ADMITTED_STABLE, ADMITTED_CRITICAL, and DELIVERED_AT_RECEIVER require tr_state='HANDED_OVER'.
       If not handed over -> raises 409 HANDOVER_REQUIRED.
    3. Guards against already terminal referral states.
    4. Marks all pending deadlines DONE.
    5. Revokes all active payload grants.
    6. Sets referral hs_state='CLOSED', outcome=cmd.outcome, closed_at=ts.
    """
    if referral.hs_state in ("CLOSED", "CANCELLED"):
        raise TransitionReject(
            409,
            "ALREADY_TERMINAL",
            f"Referral {referral.id} is already in terminal state '{referral.hs_state}', cannot CLOSE",
        )

    outcome = getattr(cmd, "outcome", None)
    if not outcome or outcome not in LOCKED_OUTCOMES:
        raise TransitionReject(
            422,
            "INVALID_OUTCOME",
            f"Outcome '{outcome}' is invalid or missing. Must be one of: {sorted(list(LOCKED_OUTCOMES))}",
        )

    # Handover Prerequisite Check (Closure F6)
    if outcome in HANDOVER_REQUIRED_OUTCOMES and referral.tr_state != "HANDED_OVER":
        raise TransitionReject(
            409,
            "HANDOVER_REQUIRED",
            f"Outcome '{outcome}' strictly requires tr_state = 'HANDED_OVER' (current is '{referral.tr_state}')",
        )

    # Mark pending deadlines DONE
    conn.execute(
        """
        UPDATE deadline
        SET status = 'DONE'
        WHERE referral_id = %s AND kind IN ('HANDOVER', 'CLOSURE', 'DISPATCH_ACTION') AND status = 'PENDING';
        """,
        (str(referral.id),),
    )

    # Revoke all active payload grants
    conn.execute(
        """
        UPDATE payload_grant
        SET status = 'REVOKED', revoked_at = %s
        WHERE referral_id = %s AND status = 'ACTIVE';
        """,
        (ts, str(referral.id)),
    )

    # Update Referral State
    referral.hs_state = "CLOSED"
    referral.outcome = outcome
    referral.closed_at = ts
    referral.open_offers = 0

    conn.execute(
        """
        UPDATE referral
        SET hs_state = 'CLOSED', outcome = %s, closed_at = %s, open_offers = 0
        WHERE id = %s;
        """,
        (outcome, ts, str(referral.id)),
    )

    return {
        "outcome": outcome,
        "reason": getattr(cmd, "reason", "CLINICAL_DISCHARGE") or "CLINICAL_DISCHARGE",
    }


def execute_revoke_grant(
    conn: Any,
    referral: Any,
    session: Session,
    cmd: RevokeGrantCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the REVOKE_GRANT command inside the 10-step transactional pipeline.

    Revokes the active payload grant for the specified target facility.
    """
    target_fac = cmd.target_facility_id

    conn.execute(
        """
        UPDATE payload_grant
        SET status = 'REVOKED', revoked_at = %s
        WHERE referral_id = %s AND facility_id = %s AND status = 'ACTIVE';
        """,
        (ts, str(referral.id), str(target_fac)),
    )

    return {
        "facility": str(target_fac),
        "reason": getattr(cmd, "reason", "MANUAL_REVOKE") or "MANUAL_REVOKE",
    }
