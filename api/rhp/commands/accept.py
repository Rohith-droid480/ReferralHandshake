"""ReferralHandshake Protocol RHP-1 — ACCEPT Command Module.

Specification Anchors:
- Architecture §4.3: Acceptance & Lease Granting
- Architecture §6: Handover Deadline H & Timing Profiles [F2, F3, I13]
- Architecture §7: Partial Unique Index one_lease [I2] & Deferred Lease FK
- Invariant I2: Single Lease Grant (at most one offer in status ACCEPTED)
- Invariant I8: Fencing Epoch & Optimistic Concurrency Control
- Invariant I15: Capability Staleness Guard (Reject 409 STALE_CONFIRMATION_RECONFIRM_REQUIRED)
- Closure F12: Live Resource Confirmation Verification on Lease Award
- Closure F13: Superseding Competing Offers & Revoking Superseded Grants
- BUILD_PLAN §3.3: ACCEPT Command, Single-Owner Lease Arbitration & I15 Staleness Check
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from api.rhp.auth import Session
from api.rhp.profiles import TimingProfile, get_profile
from api.rhp.schemas import AcceptCmd
from api.rhp.transitions import TransitionReject


def execute_accept(
    conn: Any,
    referral: Any,
    target_offer: Any,
    session: Session,
    cmd: AcceptCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the ACCEPT command inside the 10-step transactional pipeline.

    1. Validates single lease availability (Invariant I2).
    2. Validates offer status (cannot accept TIMED_OUT or SUPERSEDED offers).
    3. Validates Invariant I15: All required capabilities for referral.need_class
       must have unexpired confirmations in offer_resource_confirmation.
    4. Transitions winning offer to ACCEPTED (protected by partial unique index one_lease).
    5. Increments referral.lease_epoch, assigns lease_offer_id and lease_facility_id.
    6. Supersedes all other open offers on this referral and revokes their payload grants.
    7. Cancels pending ACK/DECISION/NOTICE deadlines and arms the HANDOVER deadline (due at ts + profile.H).
    8. Returns canonical event detail {"facility": ..., "epoch": ..., "reason": "ACCEPTED"}.
    """
    if target_offer is None:
        raise TransitionReject(404, "OFFER_NOT_FOUND", "No target offer found for ACCEPT")

    # 1. Invariant I2: Lease Availability Check
    if referral.lease_offer_id is not None:
        raise TransitionReject(
            409,
            "LEASE_HELD",
            f"Referral {referral.id} already has an active lease granted to offer {referral.lease_offer_id}",
        )

    # 2. Offer Status Guard & Late Accept Rejection
    if target_offer.status in ("TIMED_OUT", "SUPERSEDED"):
        raise TransitionReject(
            409,
            "LATE_ACCEPT_REJECTED",
            f"Offer {target_offer.id} is in status '{target_offer.status}'; late accept rejected",
        )

    if target_offer.status not in ("OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"):
        raise TransitionReject(
            409,
            "INVALID_OFFER_STATE",
            f"Offer {target_offer.id} is in status '{target_offer.status}', cannot ACCEPT "
            f"(must be 'OPEN', 'ACKED', 'COUNTERED', or 'SOFT_OPEN')",
        )

    # 3. Invariant I15 & Closure F12: Capability Staleness Check
    cur = conn.execute(
        """
        SELECT r.capability, c.expires_at
        FROM need_class_requirement r
        LEFT JOIN offer_resource_confirmation c
          ON c.capability = r.capability AND c.offer_id = %s
        WHERE r.need_class = %s;
        """,
        (str(target_offer.id), referral.need_class),
    )
    req_rows = cur.fetchall() if cur else []

    for cap, exp in req_rows:
        if exp is None or exp <= ts:
            raise TransitionReject(
                409,
                "STALE_CONFIRMATION_RECONFIRM_REQUIRED",
                f"Capability '{cap}' confirmation has expired or is missing (expired at {exp}, current {ts})",
            )

    # 4. Load timing profile for Handover deadline H
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

    # 5. Grant Lease: Update winning offer status
    conn.execute(
        """
        UPDATE offer
        SET status = 'ACCEPTED', decided_at = %s
        WHERE id = %s;
        """,
        (ts, str(target_offer.id)),
    )
    target_offer.status = "ACCEPTED"
    target_offer.decided_at = ts

    # 6. Update Referral Lease State & Epoch (Invariant I8)
    referral.lease_epoch += 1
    referral.lease_offer_id = target_offer.id
    referral.lease_facility_id = target_offer.facility_id
    referral.tr_facility_id = target_offer.facility_id
    referral.open_offers = 0
    referral.hs_state = "ACCEPTED"

    conn.execute(
        """
        UPDATE referral
        SET hs_state = 'ACCEPTED',
            lease_offer_id = %s,
            lease_facility_id = %s,
            lease_epoch = %s,
            open_offers = 0,
            tr_facility_id = %s
        WHERE id = %s;
        """,
        (
            str(target_offer.id),
            str(target_offer.facility_id),
            referral.lease_epoch,
            str(target_offer.facility_id),
            str(referral.id),
        ),
    )

    # 7. Supersede all other open offers on this referral
    conn.execute(
        """
        UPDATE offer
        SET status = 'SUPERSEDED'
        WHERE referral_id = %s
          AND id != %s
          AND status IN ('OPEN', 'ACKED', 'COUNTERED', 'SOFT_OPEN');
        """,
        (str(referral.id), str(target_offer.id)),
    )

    # 8. Cancel pending deadlines (ACK, DECISION, COUNTER_CONFIRM, NOTICE_VOICE, NOTICE_PROXY)
    conn.execute(
        """
        UPDATE deadline
        SET status = 'DONE'
        WHERE referral_id = %s
          AND kind IN ('ACK', 'DECISION', 'COUNTER_CONFIRM', 'NOTICE_VOICE', 'NOTICE_PROXY')
          AND status = 'PENDING';
        """,
        (str(referral.id),),
    )

    # 9. Arm HANDOVER deadline due at ts + profile.H
    handover_due_at = ts + timedelta(milliseconds=profile.H)
    conn.execute(
        """
        INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            str(uuid4()),
            str(referral.id),
            str(target_offer.id),
            "HANDOVER",
            target_offer.step,
            referral.lease_epoch,
            handover_due_at,
            ts,
        ),
    )

    # 10. Revoke superseded payload grants (preserving origin and lease facilities)
    conn.execute(
        """
        UPDATE payload_grant
        SET status = 'REVOKED', revoked_at = %s, revoke_reason = 'SUPERSEDED'
        WHERE referral_id = %s
          AND facility_id != %s
          AND facility_id != %s
          AND status = 'ACTIVE';
        """,
        (
            ts,
            str(referral.id),
            str(referral.origin_facility_id),
            str(target_offer.facility_id),
        ),
    )

    # Ensure active payload grant for lease facility
    conn.execute(
        """
        INSERT INTO payload_grant (id, referral_id, facility_id, status, granted_at)
        VALUES (%s, %s, %s, 'ACTIVE', %s);
        """,
        (str(uuid4()), str(referral.id), str(target_offer.facility_id), ts),
    )

    return {
        "facility": str(target_offer.facility_id),
        "epoch": referral.lease_epoch,
        "reason": "ACCEPTED",
    }
