"""ReferralHandshake Protocol RHP-1 — DECLINE Command & advance() Escalation Engine.

Specification Anchors:
- Architecture §4.3: Sequential / Parallel Offer Escalation
- Architecture §4.5: Decline Handling & Structured Reasons
- Architecture §6: Notice Ladder Rungs & Signed Profiles [F2, F3, I13]
- Invariant I7: Approved Catchment Chain Integrity
- Invariant I9: Cycle-Free Routing (no A -> B -> A loops)
- Invariant I12: Open Offers Bound (open_offers <= 2)
- Closure F13: Soft-Open Escalation & Open Offer Bound Enforcement
- BUILD_PLAN §3.4: DECLINE Command & advance() Escalation Engine
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from api.rhp.auth import Session
from api.rhp.profiles import TimingProfile, get_profile
from api.rhp.schemas import DeclineCmd
from api.rhp.transitions import TransitionReject

# Structured decline reasons recognized by RHP-1 (Architecture §4.5)
VALID_DECLINE_REASONS = {
    "NO_CAPACITY",
    "EQUIPMENT_FAILURE",
    "STAFF_UNAVAILABLE",
    "OUT_OF_SCOPE",
    "CLINICAL_DISCRETION",
    "BEDS_FULL",
    "NICU_FULL",
    "OT_UNAVAILABLE",
    "SPECIALIST_UNAVAILABLE",
    "DECLINED",
    "COUNTER_REJECTED",
    "ARRIVAL_REJECTED",
}


def advance(
    conn: Any,
    referral: Any,
    ts: datetime,
) -> Tuple[Optional[UUID], Optional[str], str]:
    """Escalates a referral to the next facility in its approved catchment chain.

    Enforces:
    1. Invariant I9 (No A -> B -> A loops): Never re-offers to a facility that has already
       had an offer created for this referral, or the origin facility.
    2. Invariant I12 & Closure F13 (open_offers <= 2): Closes any predecessor SOFT_OPEN offer
       to TIMED_OUT and revokes its payload grant.
    3. Escalation Fallback: If the chain is exhausted or all candidates have been visited,
       transitions to ESCALATED_TO_DISPATCHER and arms the DISPATCH_ACTION deadline.

    Returns:
        (new_offer_id, next_facility_id, new_hs_state)
    """
    ref_id = referral.id
    chain = getattr(referral, "chain", []) or []

    # 1. Load active timing profile
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

    # 2. Invariant I9: Identify all facilities already offered for this referral
    cur_offered = conn.execute(
        "SELECT facility_id FROM offer WHERE referral_id = %s;",
        (str(ref_id),),
    )
    offered_rows = cur_offered.fetchall() if cur_offered else []
    visited_facilities: Set[str] = {str(r[0]) for r in offered_rows}
    # Origin facility is also excluded from being offered as destination
    visited_facilities.add(str(referral.origin_facility_id))

    # 3. Invariant I12 & Closure F13: Soft-open cleanup
    # Any predecessor SOFT_OPEN offer must be closed to TIMED_OUT to ensure open_offers <= 2
    cur_soft = conn.execute(
        "SELECT id, facility_id FROM offer WHERE referral_id = %s AND status = 'SOFT_OPEN';",
        (str(ref_id),),
    )
    soft_rows = cur_soft.fetchall() if cur_soft else []
    for soft_id, soft_fac in soft_rows:
        conn.execute(
            "UPDATE offer SET status = 'TIMED_OUT' WHERE id = %s;",
            (str(soft_id),),
        )
        conn.execute(
            """
            UPDATE payload_grant
            SET status = 'REVOKED', revoked_at = %s
            WHERE referral_id = %s AND facility_id = %s AND status = 'ACTIVE';
            """,
            (ts, str(ref_id), str(soft_fac)),
        )

    # 4. Find next eligible candidate facility in chain
    start_cursor = referral.ladder_cursor + 1
    next_index: Optional[int] = None
    next_fac: Optional[str] = None

    for idx in range(start_cursor, len(chain)):
        candidate = str(chain[idx])
        if candidate not in visited_facilities:
            next_index = idx
            next_fac = candidate
            break

    # 5. Case A: Eligible facility found -> Open new offer
    if next_index is not None and next_fac is not None:
        referral.ladder_cursor = next_index
        next_off_id = uuid4()

        conn.execute(
            """
            INSERT INTO offer (
              id, referral_id, facility_id, step, source, status, counter_round,
              counter_mask, created_epoch, created_at
            ) VALUES (
              %s, %s, %s, %s, 'CHAIN', 'OPEN', 0, 0, %s, %s
            );
            """,
            (str(next_off_id), str(ref_id), next_fac, next_index, referral.lease_epoch, ts),
        )

        # Active payload grant for next offered facility
        conn.execute(
            """
            INSERT INTO payload_grant (id, referral_id, facility_id, status, granted_at)
            VALUES (%s, %s, %s, 'ACTIVE', %s);
            """,
            (str(uuid4()), str(ref_id), next_fac, ts),
        )

        # Arm Notice Rungs & ACK deadline for new offer
        ack_due_at = ts + timedelta(milliseconds=profile.A)
        conn.execute(
            """
            INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
            VALUES (%s, %s, %s, 'ACK', %s, %s, %s, %s);
            """,
            (str(uuid4()), str(ref_id), str(next_off_id), next_index, referral.lease_epoch, ack_due_at, ts),
        )

        rung1_ms = profile.rungs[1] if len(profile.rungs) > 1 else profile.A // 4
        rung2_ms = profile.rungs[2] if len(profile.rungs) > 2 else (3 * profile.A) // 4

        conn.execute(
            """
            INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
            VALUES (%s, %s, %s, 'NOTICE_VOICE', %s, %s, %s, %s);
            """,
            (str(uuid4()), str(ref_id), str(next_off_id), next_index, referral.lease_epoch, ts + timedelta(milliseconds=rung1_ms), ts),
        )

        conn.execute(
            """
            INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
            VALUES (%s, %s, %s, 'NOTICE_PROXY', %s, %s, %s, %s);
            """,
            (str(uuid4()), str(ref_id), str(next_off_id), next_index, referral.lease_epoch, ts + timedelta(milliseconds=rung2_ms), ts),
        )

        referral.hs_state = "OFFERED"
        referral.open_offers = 1

        conn.execute(
            """
            UPDATE referral
            SET ladder_cursor = %s, hs_state = 'OFFERED', open_offers = 1
            WHERE id = %s;
            """,
            (next_index, str(ref_id)),
        )

        return next_off_id, next_fac, "OFFERED"

    # 6. Case B: Chain exhausted -> Escalate to dispatcher
    referral.hs_state = "ESCALATED_TO_DISPATCHER"
    referral.open_offers = 0

    dispatch_due_at = ts + timedelta(milliseconds=profile.dispatch_action)
    conn.execute(
        """
        INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
        VALUES (%s, %s, NULL, 'DISPATCH_ACTION', 0, %s, %s, %s);
        """,
        (str(uuid4()), str(ref_id), referral.lease_epoch, dispatch_due_at, ts),
    )

    conn.execute(
        """
        UPDATE referral
        SET hs_state = 'ESCALATED_TO_DISPATCHER', open_offers = 0
        WHERE id = %s;
        """,
        (str(ref_id),),
    )

    return None, None, "ESCALATED_TO_DISPATCHER"


def execute_decline(
    conn: Any,
    referral: Any,
    target_offer: Any,
    session: Session,
    cmd: DeclineCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the DECLINE command inside the 10-step transactional pipeline.

    1. Checks target offer state in ('OPEN', 'ACKED', 'COUNTERED', 'SOFT_OPEN').
    2. Updates offer status to 'DECLINED', recording reason and decided_at.
    3. Cancels pending deadlines for this offer.
    4. Revokes payload grant for the declining facility.
    5. Calls advance() to escalate along the chain or escalate to dispatcher.
    6. Returns canonical event detail.
    """
    if target_offer is None:
        raise TransitionReject(404, "OFFER_NOT_FOUND", "No target offer found for DECLINE")

    if target_offer.status not in ("OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"):
        raise TransitionReject(
            409,
            "INVALID_OFFER_STATE",
            f"Offer {target_offer.id} is in status '{target_offer.status}', cannot DECLINE "
            f"(must be 'OPEN', 'ACKED', 'COUNTERED', or 'SOFT_OPEN')",
        )

    decline_reason = getattr(cmd, "reason", "DECLINED") or "DECLINED"

    # 1. Update target offer
    conn.execute(
        """
        UPDATE offer
        SET status = 'DECLINED', decided_at = %s, decline_reason = %s
        WHERE id = %s;
        """,
        (ts, decline_reason, str(target_offer.id)),
    )
    target_offer.status = "DECLINED"
    target_offer.decided_at = ts
    target_offer.decline_reason = decline_reason

    # 2. Cancel pending deadlines for this offer
    conn.execute(
        """
        UPDATE deadline
        SET status = 'DONE'
        WHERE referral_id = %s
          AND (offer_id = %s OR offer_id IS NULL)
          AND kind IN ('ACK', 'DECISION', 'COUNTER_CONFIRM', 'NOTICE_VOICE', 'NOTICE_PROXY')
          AND status = 'PENDING';
        """,
        (str(referral.id), str(target_offer.id)),
    )

    # 3. Revoke active payload grant for the declining facility
    conn.execute(
        """
        UPDATE payload_grant
        SET status = 'REVOKED', revoked_at = %s
        WHERE referral_id = %s AND facility_id = %s AND status = 'ACTIVE';
        """,
        (ts, str(referral.id), str(target_offer.facility_id)),
    )

    # 4. Escalate via advance()
    advance(conn, referral, ts)

    return {
        "reason": decline_reason,
        "facility": str(target_offer.facility_id),
    }
