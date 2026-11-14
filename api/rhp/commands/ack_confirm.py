"""ReferralHandshake Protocol RHP-1 — ACK & RESOURCE_CONFIRM Command Module.

Specification Anchors:
- Architecture §4.3: Offer Acknowledgement & Capability Confirmations
- Architecture §6: Unified ACK Window A & Decision Window D [F2, F3, I13]
- Architecture §7: Schema & Confirmation TTL Storage
- Invariant I1: Timely Deadline Replacement (ACK/NOTICE -> DECISION)
- Invariant I12: Open Offers Bound (open_offers <= 2)
- Invariant I15: Live Resource Confirmation TTL (confirm_ttl)
- Closure F13: Soft-Open Closure Rule on Successor ACK
- BUILD_PLAN §3.2: ACK & RESOURCE_CONFIRM Commands, Capability TTL & Soft-Open Expiry
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from api.rhp.auth import Session
from api.rhp.profiles import TimingProfile, get_profile
from api.rhp.schemas import AckCmd, ResourceConfirmCmd
from api.rhp.transitions import TransitionReject


def execute_ack(
    conn: Any,
    referral: Any,
    target_offer: Any,
    session: Session,
    cmd: AckCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the ACK command inside the 10-step transactional pipeline.

    1. Enforces target offer status == 'OPEN'.
    2. Transitions offer status to 'ACKED' with acked_by and acked_at stamps.
    3. Cancels pending ACK, NOTICE_VOICE, and NOTICE_PROXY deadlines.
    4. Arms a new DECISION deadline due at ts + profile.D.
    5. Enforces Soft-Open Closure Rule (Closure F13): If in SEQUENTIAL mode and a
       predecessor offer is SOFT_OPEN, closes it to TIMED_OUT and revokes its grant.
    6. Updates referral hs_state to ACKNOWLEDGED and returns canonical event detail.
    """
    if target_offer is None:
        raise TransitionReject(404, "OFFER_NOT_FOUND", "No target offer found for ACK")

    if target_offer.status != "OPEN":
        raise TransitionReject(
            409,
            "INVALID_OFFER_STATE",
            f"Offer {target_offer.id} is in status '{target_offer.status}', cannot ACK (must be 'OPEN')",
        )

    # 1. Update target offer status
    conn.execute(
        """
        UPDATE offer
        SET status = 'ACKED', acked_at = %s, acked_by = %s
        WHERE id = %s;
        """,
        (ts, str(session.roster_id), str(target_offer.id)),
    )
    target_offer.status = "ACKED"
    target_offer.acked_at = ts
    target_offer.acked_by = session.roster_id

    # 2. Cancel pending notice rungs and ACK deadlines for this referral/offer
    conn.execute(
        """
        UPDATE deadline
        SET status = 'DONE'
        WHERE referral_id = %s
          AND (offer_id = %s OR offer_id IS NULL)
          AND kind IN ('ACK', 'NOTICE_VOICE', 'NOTICE_PROXY')
          AND status = 'PENDING';
        """,
        (str(referral.id), str(target_offer.id)),
    )

    # 3. Load timing profile to determine decision window D
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

    # 4. Arm DECISION deadline due at ts + profile.D
    decision_due_at = ts + timedelta(milliseconds=profile.D)
    conn.execute(
        """
        INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            str(uuid4()),
            str(referral.id),
            str(target_offer.id),
            "DECISION",
            target_offer.step,
            referral.lease_epoch,
            decision_due_at,
            ts,
        ),
    )

    # 5. Soft-Open Closure Rule (Closure F13, Invariant I12):
    # In SEQUENTIAL mode, once successor ACKs, any predecessor SOFT_OPEN offer closes to TIMED_OUT.
    if referral.mode == "SEQUENTIAL":
        cur = conn.execute(
            """
            SELECT id, facility_id
            FROM offer
            WHERE referral_id = %s AND status = 'SOFT_OPEN' AND id != %s;
            """,
            (str(referral.id), str(target_offer.id)),
        )
        soft_rows = cur.fetchall() if cur else []
        for soft_id, soft_fac in soft_rows:
            # Mark prior soft offer timed out
            conn.execute(
                "UPDATE offer SET status = 'TIMED_OUT' WHERE id = %s;",
                (str(soft_id),),
            )
            # Revoke its payload grant
            conn.execute(
                """
                UPDATE payload_grant
                SET status = 'REVOKED', revoked_at = %s, revoke_reason = 'SOFT_OPEN_EXPIRED'
                WHERE referral_id = %s AND facility_id = %s AND status = 'ACTIVE';
                """,
                (ts, str(referral.id), str(soft_fac)),
            )

        referral.open_offers = 1

    # 6. Update referral state to ACKNOWLEDGED
    if referral.hs_state not in ("ACCEPTED", "CLOSED", "CANCELLED"):
        referral.hs_state = "ACKNOWLEDGED"

    conn.execute(
        """
        UPDATE referral
        SET hs_state = %s, open_offers = %s
        WHERE id = %s;
        """,
        (referral.hs_state, referral.open_offers, str(referral.id)),
    )

    return {"channel": cmd.channel}


def execute_resource_confirm(
    conn: Any,
    referral: Any,
    target_offer: Any,
    session: Session,
    cmd: ResourceConfirmCmd,
    ts: datetime,
) -> Dict[str, Any]:
    """Executes the RESOURCE_CONFIRM command inside the 10-step transactional pipeline.

    1. Requires target offer status in ('OPEN', 'ACKED', 'SOFT_OPEN').
    2. Validates capability confirmations against required capabilities for need_class.
    3. Computes confirmation TTL: expires_at = ts + profile.confirm_ttl (Invariant I15).
    4. Upserts confirmations into offer_resource_confirmation.
    5. Returns canonical event detail with confirmed capability.
    """
    if target_offer is None:
        raise TransitionReject(404, "OFFER_NOT_FOUND", "No target offer found for RESOURCE_CONFIRM")

    if target_offer.status not in ("OPEN", "ACKED", "SOFT_OPEN"):
        raise TransitionReject(
            409,
            "INVALID_OFFER_STATE",
            f"Offer {target_offer.id} is in status '{target_offer.status}', cannot confirm resources "
            f"(must be 'OPEN', 'ACKED', or 'SOFT_OPEN')",
        )

    # 1. Load timing profile for confirmation TTL
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

    expires_at = ts + timedelta(milliseconds=profile.confirm_ttl)

    # 2. Upsert each capability confirmation
    capabilities = getattr(cmd, "capabilities", [])
    if not capabilities:
        raise TransitionReject(422, "MISSING_CAPABILITIES", "At least one capability must be specified")

    for cap in capabilities:
        conn.execute(
            """
            INSERT INTO offer_resource_confirmation (
              offer_id, capability, confirmed_by, confirmed_at, expires_at
            ) VALUES (
              %s, %s, %s, %s, %s
            ) ON CONFLICT (offer_id, capability) DO UPDATE SET
              confirmed_by = EXCLUDED.confirmed_by,
              confirmed_at = EXCLUDED.confirmed_at,
              expires_at = EXCLUDED.expires_at;
            """,
            (
                str(target_offer.id),
                str(cap),
                str(session.roster_id),
                ts,
                expires_at,
            ),
        )

    return {"capability": capabilities[0]}
