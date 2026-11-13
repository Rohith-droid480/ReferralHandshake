"""ReferralHandshake Protocol RHP-1 — ACK & RESOURCE_CONFIRM Command Test Suite.

Specification Anchors:
- Architecture §4.3: Offer Acknowledgement, Capability Confirmations & Soft-Open Expiry
- Architecture §6: Timing Model, Ladder Rungs, ACK Window A & Decision Window D [F2, F3, I13]
- Architecture §9: Role-Command Authorization & Cross-Facility Isolation [Invariant I6]
- Invariant I1: Timely Deadline Replacement (ACK/NOTICE -> DECISION)
- Invariant I12: Open Offers Bound (open_offers <= 2)
- Invariant I15: Live Resource Confirmation TTL (confirm_ttl)
- Closure F13: Soft-Open Closure Rule on Successor ACK
- BUILD_PLAN §3.2: ACK & RESOURCE_CONFIRM Commands, Capability TTL & Soft-Open Expiry
"""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.db import get_main_connection, reset_mock_db
from api.rhp.pipeline import apply_command


@pytest.fixture(autouse=True)
def setup_db():
    """Resets mock database before each test run."""
    reset_mock_db()
    with get_main_connection() as conn:
        if hasattr(conn, "db"):
            conn.db.offers = {}
            conn.db.deadlines = {}
            conn.db.events = []
            conn.db.outbox = []
            conn.db.rejected_commands = []
            conn.db.idempotency = {}
            conn.db.payload_grants = {}
            conn.db.offer_resource_confirmations = {}


# =============================================================================
# 1. ACK Command: Basic Transitions & Deadline Arming (Invariant I1)
# =============================================================================

def test_ack_cancels_notice_rungs_and_arms_decision_deadline():
    """Invariant I1: ACK cancels pending notice rungs and arms DECISION deadline."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"  # Clinician at Origin Facility 1
    roster_f2 = "00000000-0000-0000-0000-000000000020"  # CMO at Receiving Facility 2
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        # 1. Create referral
        status_create, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [target1],
                "mgso4_status": "GIVEN",
                "profile_id": "DEMO_FAST",
            },
            session_token=sess_f1,
            idem_key="ack-test-create-1",
        )
        assert status_create == 200
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # Prior to ACK: ACK, NOTICE_VOICE, NOTICE_PROXY are PENDING
        prior_deadlines = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id]
        for d in prior_deadlines:
            assert d["status"] == "PENDING"

        # 2. Receiving hospital (Facility 2) submits ACK
        status_ack, resp_ack = apply_command(
            conn,
            {
                "type": "ACK",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 2,
            },
            session_token=sess_f2,
            idem_key="ack-test-submit-1",
        )
        assert status_ack == 200
        assert resp_ack["status"] == "COMMITTED"

        # Assert offer is now ACKED
        off = conn.db.offers[off1_id]
        assert off["status"] == "ACKED"
        assert off["acked_by"] == roster_f2
        assert off["acked_at"] is not None

        # Assert prior notice deadlines marked DONE
        notice_deadlines = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id and d["kind"] in ("ACK", "NOTICE_VOICE", "NOTICE_PROXY")]
        for d in notice_deadlines:
            assert d["status"] == "DONE"

        # Assert DECISION deadline created and PENDING
        decision_deadlines = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id and d["kind"] == "DECISION"]
        assert len(decision_deadlines) == 1
        assert decision_deadlines[0]["status"] == "PENDING"
        assert decision_deadlines[0]["offer_id"] == off1_id

        # Assert referral hs_state is ACKNOWLEDGED
        assert conn.db.referrals[ref_id]["hs_state"] == "ACKNOWLEDGED"


def test_ack_rejects_already_acked_or_invalid_offer():
    """Closure F1: Submitting ACK on an offer not in OPEN status returns 409 INVALID_OFFER_STATE."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        # Create and ACK
        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [target1],
            },
            session_token=sess_f1,
            idem_key="ack-dup-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        apply_command(
            conn,
            {"type": "ACK", "referral_id": ref_id, "offer_id": off1_id, "expected_version": 2},
            session_token=sess_f2,
            idem_key="ack-dup-first-1",
        )

        # 2nd ACK on same offer (now ACKED) returns 409
        status_dup, resp_dup = apply_command(
            conn,
            {"type": "ACK", "referral_id": ref_id, "offer_id": off1_id, "expected_version": 3},
            session_token=sess_f2,
            idem_key="ack-dup-second-1",
        )
        assert status_dup == 409
        assert resp_dup["status"] == "REJECTED"


# =============================================================================
# 2. Soft-Open Closure Rule (Closure F13, Invariant I12)
# =============================================================================

def test_ack_closes_predecessor_soft_open_offer_to_timed_out():
    """Closure F13 & Invariant I12: When successor ACKs, predecessor SOFT_OPEN transitions to TIMED_OUT."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"  # Origin
    roster_f3 = "00000000-0000-0000-0000-000000000030"  # Facility 3 Consultant
    origin_fac = "00000000-0000-0000-0000-000000000001"
    fac1 = "00000000-0000-0000-0000-000000000002"
    fac2 = "00000000-0000-0000-0000-000000000003"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f3, _ = create_enrollment_ticket(conn, roster_f3, roster_f3)
        sess_f3, _ = redeem_enrollment_ticket(conn, token_f3, secrets.token_bytes(32), "pwa")

        # 1. Create referral with 2 facilities in SEQUENTIAL mode
        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [fac1, fac2],
            },
            session_token=sess_f1,
            idem_key="soft-open-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # 2. Simulate offer 1 entering SOFT_OPEN (via TIMEOUT in sequential mode) and offer 2 opening
        conn.db.offers[off1_id]["status"] = "SOFT_OPEN"

        off2_id = str(uuid4())
        conn.db.offers[off2_id] = {
            "id": off2_id,
            "referral_id": ref_id,
            "facility_id": fac2,
            "step": 2,
            "source": "CHAIN",
            "status": "OPEN",
            "counter_round": 0,
            "counter_mask": 0,
            "created_epoch": 0,
            "created_at": datetime.now(timezone.utc),
        }
        conn.db.referrals[ref_id]["open_offers"] = 2  # Off 1 is SOFT_OPEN, Off 2 is OPEN

        # Payload grant for fac1 is currently ACTIVE
        conn.db.payload_grants[f"{ref_id}:{fac1}"] = {
            "id": str(uuid4()),
            "referral_id": ref_id,
            "facility_id": fac1,
            "status": "ACTIVE",
            "granted_at": datetime.now(timezone.utc),
        }

        # 3. Off 2 (Facility 3) submits ACK
        status_ack, resp_ack = apply_command(
            conn,
            {
                "type": "ACK",
                "referral_id": ref_id,
                "offer_id": off2_id,
                "expected_version": 2,
            },
            session_token=sess_f3,
            idem_key="soft-open-ack-off2-1",
        )
        assert status_ack == 200

        # Assert Off 1 was closed to TIMED_OUT (Closure F13)
        assert conn.db.offers[off1_id]["status"] == "TIMED_OUT"

        # Assert Off 1's payload grant was REVOKED
        assert conn.db.payload_grants[f"{ref_id}:{fac1}"]["status"] == "REVOKED"

        # Assert open_offers is now 1 (Invariant I12)
        assert conn.db.referrals[ref_id]["open_offers"] == 1


# =============================================================================
# 3. RESOURCE_CONFIRM Command: Capability TTL Storage (Invariant I15)
# =============================================================================

def test_resource_confirm_stores_capabilities_with_ttl():
    """Invariant I15: RESOURCE_CONFIRM stores capability confirmations with valid TTL."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [target1],
            },
            session_token=sess_f1,
            idem_key="res-conf-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # 1. Facility 2 submits RESOURCE_CONFIRM for OT and BLOOD
        status_rc, resp_rc = apply_command(
            conn,
            {
                "type": "RESOURCE_CONFIRM",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 2,
                "candidate_pin": "4321",
                "capabilities": ["OT", "BLOOD"],
            },
            session_token=sess_f2,
            idem_key="res-conf-submit-1",
        )
        assert status_rc == 200
        assert resp_rc["status"] == "COMMITTED"

        # Assert confirmations persisted in mock DB with unexpired TTL
        confs = conn.db.offer_resource_confirmations
        assert f"{off1_id}:OT" in confs
        assert f"{off1_id}:BLOOD" in confs

        ot_conf = confs[f"{off1_id}:OT"]
        assert ot_conf["capability"] == "OT"
        assert ot_conf["confirmed_by"] == roster_f2
        assert ot_conf["expires_at"] > ot_conf["created_at"]
