"""Tests for DECLINE Command & advance() Escalation Engine.

Specification Anchors:
- BUILD_PLAN §3.4: DECLINE Command & advance() Escalation Engine
- Architecture §4.3: Offer Escalation & Mode Selection
- Architecture §4.5: Decline Handling & Structured Reasons
- Invariant I7: Catchment Chain Target Authorization
- Invariant I9: Cycle-Free Routing (no A -> B -> A loops)
- Invariant I12: Open Offers Bound (open_offers <= 2)
- Closure F13: Soft-Open Overlap & Escalation Invariants
"""

import pytest
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.db import get_main_connection
from api.rhp.pipeline import apply_command


def test_decline_advances_to_next_chain_facility():
    """BUILD_PLAN 3.4: Submitting DECLINE marks offer DECLINED and advances to next chain facility."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"  # Origin Clinician
    roster_f2 = "00000000-0000-0000-0000-000000000020"  # Facility 2 CMO
    origin_fac = "00000000-0000-0000-0000-000000000001"
    fac2 = "00000000-0000-0000-0000-000000000002"
    fac3 = "00000000-0000-0000-0000-000000000003"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        # 1. Create referral with 2 targets in chain
        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [fac2, fac3],
            },
            session_token=sess_f1,
            idem_key="decline-adv-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # 2. Facility 2 submits DECLINE with structured reason
        status_dec, resp_dec = apply_command(
            conn,
            {
                "type": "DECLINE",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 2,
                "candidate_pin": "4321",
                "reason": "NO_CAPACITY",
            },
            session_token=sess_f2,
            idem_key="decline-adv-submit-1",
        )
        assert status_dec == 200
        assert resp_dec["status"] == "COMMITTED"

        # Assert offer 1 is DECLINED with reason
        off1 = conn.db.offers[off1_id]
        assert off1["status"] == "DECLINED"
        assert off1["decline_reason"] == "NO_CAPACITY"

        # Assert offer 1's payload grant is REVOKED
        assert conn.db.payload_grants[f"{ref_id}:{fac2}"]["status"] == "REVOKED"

        # Assert offer 2 was opened for fac3
        off2_matches = [v for v in conn.db.offers.values() if v["referral_id"] == ref_id and v["facility_id"] == fac3]
        assert len(off2_matches) == 1
        off2 = off2_matches[0]
        assert off2["status"] == "OPEN"
        assert off2["step"] == 1

        # Assert active payload grant for fac3
        assert conn.db.payload_grants[f"{ref_id}:{fac3}"]["status"] == "ACTIVE"

        # Assert referral cursor advanced and hs_state is OFFERED
        ref = conn.db.referrals[ref_id]
        assert ref["ladder_cursor"] == 1
        assert ref["hs_state"] == "OFFERED"
        assert ref["open_offers"] == 1


def test_decline_escalates_to_dispatcher_when_chain_exhausted():
    """BUILD_PLAN 3.4: When all facilities in chain decline, referral escalates to dispatcher."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    fac2 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        # 1. Create with single target
        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [fac2],
            },
            session_token=sess_f1,
            idem_key="decline-exhaust-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # 2. Only facility declines -> chain exhausted
        status_dec, resp_dec = apply_command(
            conn,
            {
                "type": "DECLINE",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 2,
                "candidate_pin": "4321",
                "reason": "EQUIPMENT_FAILURE",
            },
            session_token=sess_f2,
            idem_key="decline-exhaust-submit-1",
        )
        assert status_dec == 200

        # Referral must escalate to dispatcher
        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "ESCALATED_TO_DISPATCHER"
        assert ref["open_offers"] == 0

        # DISPATCH_ACTION deadline armed
        dispatch_dls = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id and d["kind"] == "DISPATCH_ACTION"]
        assert len(dispatch_dls) == 1
        assert dispatch_dls[0]["status"] == "PENDING"


def test_advance_enforces_i9_no_ping_pong_loop():
    """Invariant I9: advance() skips facilities already offered, preventing A -> B -> A loops."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    fac2 = "00000000-0000-0000-0000-000000000002"
    fac3 = "00000000-0000-0000-0000-000000000003"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        # Chain has a duplicate entry attempting loop: [fac2, fac2, fac3]
        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [fac2, fac2, fac3],
            },
            session_token=sess_f1,
            idem_key="i9-loop-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # fac2 declines; advance() must skip the 2nd fac2 in chain and offer fac3
        status_dec, _ = apply_command(
            conn,
            {
                "type": "DECLINE",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 2,
                "candidate_pin": "4321",
                "reason": "BEDS_FULL",
            },
            session_token=sess_f2,
            idem_key="i9-loop-decline-1",
        )
        assert status_dec == 200

        # Assert offer was given to fac3 (skipping duplicate fac2 per Invariant I9)
        open_offers = [v for v in conn.db.offers.values() if v["referral_id"] == ref_id and v["status"] == "OPEN"]
        assert len(open_offers) == 1
        assert open_offers[0]["facility_id"] == fac3
        assert open_offers[0]["step"] == 2


def test_advance_closes_predecessor_soft_open_to_timed_out_i12():
    """Invariant I12 & Closure F13: advance() closes any prior SOFT_OPEN offer to maintain open_offers <= 2."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f3 = "00000000-0000-0000-0000-000000000030"  # Facility 3 Consultant
    origin_fac = "00000000-0000-0000-0000-000000000001"
    fac2 = "00000000-0000-0000-0000-000000000002"
    fac3 = "00000000-0000-0000-0000-000000000003"
    fac4 = "00000000-0000-0000-0000-000000000004"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f3, _ = create_enrollment_ticket(conn, roster_f3, roster_f3)
        sess_f3, _ = redeem_enrollment_ticket(conn, token_f3, secrets.token_bytes(32), "pwa")

        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [fac2, fac3, fac4],
            },
            session_token=sess_f1,
            idem_key="soft-dec-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # Simulate Off 1 entering SOFT_OPEN and Off 2 opening
        conn.db.offers[off1_id]["status"] = "SOFT_OPEN"
        off2_id = str(uuid4())
        conn.db.offers[off2_id] = {
            "id": off2_id,
            "referral_id": ref_id,
            "facility_id": fac3,
            "step": 1,
            "source": "CHAIN",
            "status": "OPEN",
            "counter_round": 0,
            "counter_mask": 0,
            "created_epoch": 0,
            "created_at": datetime.now(timezone.utc),
        }
        conn.db.referrals[ref_id]["open_offers"] = 2
        conn.db.referrals[ref_id]["ladder_cursor"] = 1

        # Off 2 declines
        status_dec, _ = apply_command(
            conn,
            {
                "type": "DECLINE",
                "referral_id": ref_id,
                "offer_id": off2_id,
                "expected_version": 2,
                "candidate_pin": "4321",
                "reason": "STAFF_UNAVAILABLE",
            },
            session_token=sess_f3,
            idem_key="soft-dec-submit-off2-1",
        )
        assert status_dec == 200

        # Assert prior SOFT_OPEN offer 1 was closed to TIMED_OUT
        assert conn.db.offers[off1_id]["status"] == "TIMED_OUT"

        # Assert new offer 3 opened for fac4, open_offers is bounded to 1
        assert conn.db.referrals[ref_id]["open_offers"] == 1
        off3_matches = [v for v in conn.db.offers.values() if v["referral_id"] == ref_id and v["facility_id"] == fac4]
        assert len(off3_matches) == 1
        assert off3_matches[0]["status"] == "OPEN"


def test_decline_rejects_already_terminal_or_invalid_offer():
    """Closure F1: DECLINE on already DECLINED or TIMED_OUT offer returns 409 INVALID_OFFER_STATE."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    fac2 = "00000000-0000-0000-0000-000000000002"

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
                "chain": [fac2],
            },
            session_token=sess_f1,
            idem_key="dec-dup-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # 1st DECLINE
        apply_command(
            conn,
            {"type": "DECLINE", "referral_id": ref_id, "offer_id": off1_id, "expected_version": 2, "candidate_pin": "4321", "reason": "NO_CAPACITY"},
            session_token=sess_f2,
            idem_key="dec-dup-first-1",
        )

        # 2nd DECLINE on same offer
        status_dup, resp_dup = apply_command(
            conn,
            {"type": "DECLINE", "referral_id": ref_id, "offer_id": off1_id, "expected_version": 3, "candidate_pin": "4321", "reason": "NO_CAPACITY"},
            session_token=sess_f2,
            idem_key="dec-dup-second-1",
        )
        assert status_dup == 409
        assert resp_dup["status"] == "REJECTED"
