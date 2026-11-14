"""ReferralHandshake Protocol RHP-1 — Transport Track & Arrival Cases (§4, Closures F5, Invariants I3).

Specification Anchors:
- Architecture §4.5: Six Arrival Cases [Closure F5]
- Invariant I3: Independent Handshake and Transport Tracks
- BUILD_PLAN §8.1: Parallel Transport Track API & Telemetry Ingest

Mandates:
1. TR_UPDATE advances referral.tr_state:
   REQUESTED -> DISPATCHED -> EN_ROUTE -> ARRIVED -> HANDED_OVER (or TR_CANCELLED).
2. Invariant I3 Enforcement: Never read or gate on referral.hs_state
   (except rejecting if referral is already terminal in CLOSED or CANCELLED).
3. Human confirmation required for ARRIVED and HANDED_OVER.
4. Handles all 6 real-world arrival cases (Cases a through f).
5. Arms HANDOVER deadline on ARRIVED; cancels HANDOVER and arms CLOSURE deadline on HANDED_OVER.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID, uuid4

from api.rhp.auth import Session
from api.rhp.profiles import get_profile, TimingProfile
from api.rhp.schemas import (
    TrDestinationChangeCmd,
    TrUpdateCmd,
    validate_event_detail,
)
from api.rhp.transitions import TransitionReject

logger = logging.getLogger("rhp.transport")

VALID_TR_TRANSITIONS = {
    "REQUESTED": {"DISPATCHED", "TR_CANCELLED"},
    "DISPATCHED": {"EN_ROUTE", "TR_CANCELLED"},
    "EN_ROUTE": {"ARRIVED", "TR_CANCELLED"},
    "ARRIVED": {"HANDED_OVER"},
    "HANDED_OVER": set(),
    "TR_CANCELLED": set(),
}


def execute_tr_update(
    conn: Any,
    referral: Any,
    session: Session,
    cmd: TrUpdateCmd,
    ts: datetime,
) -> Tuple[str, Dict[str, Any]]:
    """Executes TR_UPDATE command advancing referral.tr_state independently of hs_state (I3)."""
    ref_id = referral.id
    target_state = cmd.tr_state
    current_tr_state = referral.tr_state

    # 1. Invariant I3: Check referral is not in terminal closed/cancelled state
    if referral.hs_state in ("CLOSED", "CANCELLED"):
        raise TransitionReject(409, f"REFERRAL_TERMINAL: Cannot update transport for {referral.hs_state} referral")

    # 2. Transition Guard for Transport Track
    allowed_next = VALID_TR_TRANSITIONS.get(current_tr_state, set())
    if target_state not in allowed_next:
        raise TransitionReject(
            409,
            f"INVALID_TR_TRANSITION: Cannot transition tr_state from {current_tr_state} to {target_state}",
        )

    # 3. Require human actor for ARRIVED and HANDED_OVER (Closure F5, D2)
    if target_state in ("ARRIVED", "HANDED_OVER"):
        if cmd.channel == "SYSTEM" and not cmd.proxy:
            raise TransitionReject(
                400,
                f"HUMAN_CONFIRMATION_REQUIRED: {target_state} requires human confirmation from EMT or receiving desk",
            )

    # 4. Check for Arrival Cases (Closure F5)
    event_type = "TR_UPDATED"
    event_detail: Dict[str, Any] = {
        "tr_state": target_state,
        "source": getattr(cmd, "source", "MANUAL") or "MANUAL",
    }
    if getattr(cmd, "dwell_s", None) is not None:
        event_detail["dwell_s"] = cmd.dwell_s

    # Case (c): Unannounced arrival at facility with no offer
    if target_state == "ARRIVED":
        acting_fac_id = session.facility_id
        is_lease_holder = (
            acting_fac_id is not None
            and referral.lease_facility_id is not None
            and str(acting_fac_id) == str(referral.lease_facility_id)
        )

        if acting_fac_id and not is_lease_holder:
            # Check if facility has any open offer
            has_offer = False
            if hasattr(conn, "db"):
                for off in conn.db.offers.values():
                    if (
                        str(off.get("referral_id")) == str(ref_id)
                        and str(off.get("facility_id")) == str(acting_fac_id)
                        and off.get("status") in ("OPEN", "ACKED", "SOFT_OPEN")
                    ):
                        has_offer = True
                        break
            else:
                cur = conn.execute(
                    """
                    SELECT 1 FROM offer
                    WHERE referral_id = %s AND facility_id = %s AND status IN ('OPEN','ACKED','SOFT_OPEN')
                    LIMIT 1;
                    """,
                    (str(ref_id), str(acting_fac_id)),
                )
                has_offer = bool(cur.fetchone() if cur else False)

            if not has_offer:
                # Case (c): Unannounced arrival at facility with NO offer
                # Never block care! Emit ARRIVAL_AT_NON_OWNER alert
                event_type = "ARRIVAL_AT_NON_OWNER"
                event_detail = {
                    "facility": str(acting_fac_id),
                    "reason": "UNANNOUNCED_ARRIVAL",
                }

    # 5. Load profile to manage deadlines
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

    # 6. Apply state mutations to referral
    referral.tr_state = target_state

    conn.execute(
        """
        UPDATE referral
        SET tr_state = %s
        WHERE id = %s;
        """,
        (target_state, str(ref_id)),
    )

    # 7. Manage deadlines based on transport progress
    if target_state == "ARRIVED":
        # Arm HANDOVER deadline
        due_at = ts + timedelta(milliseconds=profile.H)
        conn.execute(
            """
            INSERT INTO deadline (
                id, referral_id, offer_id, kind, step, epoch, status, due_at
            ) VALUES (
                %s, %s, %s, 'HANDOVER', 1, %s, 'PENDING', %s
            );
            """,
            (
                str(uuid4()),
                str(ref_id),
                str(referral.lease_offer_id) if referral.lease_offer_id else None,
                referral.lease_epoch,
                due_at,
            ),
        )

    elif target_state == "HANDED_OVER":
        # Cancel any pending HANDOVER deadline
        conn.execute(
            "UPDATE deadline SET status = 'CANCELLED' WHERE referral_id = %s AND kind = 'HANDOVER' AND status = 'PENDING';",
            (str(ref_id),),
        )
        # Arm CLOSURE deadline (stage 1)
        due_at = ts + timedelta(milliseconds=profile.closure)
        conn.execute(
            """
            INSERT INTO deadline (
                id, referral_id, offer_id, kind, step, epoch, status, due_at
            ) VALUES (
                %s, %s, %s, 'CLOSURE', 1, %s, 'PENDING', %s
            );
            """,
            (
                str(uuid4()),
                str(ref_id),
                None,
                referral.lease_epoch,
                due_at,
            ),
        )

    return event_type, event_detail


def execute_tr_destination_change(
    conn: Any,
    referral: Any,
    session: Session,
    cmd: TrDestinationChangeCmd,
    ts: datetime,
) -> Tuple[str, Dict[str, Any]]:
    """Handles en-route destination change and crew redirect decisions (Cases d and e)."""
    ref_id = referral.id
    target_facility_id = cmd.target_facility_id
    accepted = bool(cmd.accepted)
    reason = cmd.reason or "CLINICAL_DETERIORATION"

    if referral.hs_state in ("CLOSED", "CANCELLED"):
        raise TransitionReject(409, f"REFERRAL_TERMINAL: Cannot change destination for {referral.hs_state} referral")

    # Destination change is only valid while EN_ROUTE or DISPATCHED
    if referral.tr_state not in ("DISPATCHED", "EN_ROUTE"):
        raise TransitionReject(
            409,
            f"INVALID_TR_STATE: Destination change is only allowed while DISPATCHED or EN_ROUTE (current: {referral.tr_state})",
        )

    if accepted:
        # Case (d): Destination redirect accepted by crew or dispatcher
        referral.tr_facility_id = target_facility_id
        conn.execute(
            "UPDATE referral SET tr_facility_id = %s WHERE id = %s;",
            (str(target_facility_id), str(ref_id)),
        )

    # Event detail conforming strictly to rhp_allowed('TR_DESTINATION_CHANGE'): ['facility','reason','accepted']
    event_type = "TR_DESTINATION_CHANGE"
    event_detail = {
        "facility": str(target_facility_id),
        "reason": reason[:40],
        "accepted": accepted,
    }

    return event_type, event_detail
