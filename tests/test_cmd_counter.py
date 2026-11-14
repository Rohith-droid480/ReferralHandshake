"""Tests for COUNTER and CONFIRM_COUNTER Commands.

Specification Anchors:
- BUILD_PLAN §3.5: COUNTER Command & CONFIRM_COUNTER Command
- Architecture §4.4: Counter-Offer Negotiation & Round Bound (max 2 rounds)
- Architecture §6: Timing Model, Profile Parameters C & D [F2, F3, I13]
- Closure F13: Counter-Offer Cap & Deadline min(C, remaining D)
- Invariant I15: Capability Staleness Verification on Counter Acceptance
"""

import pytest
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.db import get_main_connection
from api.rhp.pipeline import apply_command


def test_counter_arms_counter_confirm_deadline_replacing_decision():
    """BUILD_PLAN 3.5 & Closure F13: COUNTER replaces DECISION with COUNTER_CONFIRM deadline."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        # 1. Create and ACK
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
            idem_key="cnt-test-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        apply_command(
            conn,
            {"type": "ACK", "referral_id": ref_id, "offer_id": off1_id, "expected_version": 2},
            session_token=sess_f2,
            idem_key="cnt-test-ack-1",
        )

        # Confirm DECISION deadline is pending
        decision_dls = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id and d["kind"] == "DECISION"]
        assert len(decision_dls) == 1
        assert decision_dls[0]["status"] == "PENDING"

        # 2. Facility 2 submits COUNTER with mask=5
        status_cnt, resp_cnt = apply_command(
            conn,
            {
                "type": "COUNTER",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 3,
                "candidate_pin": "4321",
                "counter_mask": 5,
            },
            session_token=sess_f2,
            idem_key="cnt-test-submit-1",
        )
        assert status_cnt == 200
        assert resp_cnt["status"] == "COMMITTED"

        # Assert offer is COUNTERED with round 1 and mask 5
        off1 = conn.db.offers[off1_id]
        assert off1["status"] == "COUNTERED"
        assert off1["counter_round"] == 1
        assert off1["counter_mask"] == 5

        # Assert referral hs_state is COUNTERED
        assert conn.db.referrals[ref_id]["hs_state"] == "COUNTERED"

        # Assert DECISION deadline marked DONE
        for d in conn.db.deadlines.values():
            if d["referral_id"] == ref_id and d["kind"] == "DECISION":
                assert d["status"] == "DONE"

        # Assert COUNTER_CONFIRM deadline armed and PENDING
        counter_dls = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id and d["kind"] == "COUNTER_CONFIRM"]
        assert len(counter_dls) == 1
        assert counter_dls[0]["status"] == "PENDING"


def test_counter_rejects_round_3_exceeded():
    """Closure F13: Maximum 2 counter rounds allowed; a 3rd round returns 409 COUNTER_ROUND_EXCEEDED."""
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
            idem_key="cnt-round-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # Simulate offer already at round 2
        conn.db.offers[off1_id]["counter_round"] = 2
        conn.db.offers[off1_id]["status"] = "OPEN"

        # Attempt round 3 COUNTER -> 409 COUNTER_ROUND_EXCEEDED
        status_cnt3, resp_cnt3 = apply_command(
            conn,
            {
                "type": "COUNTER",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 2,
                "candidate_pin": "4321",
                "counter_mask": 3,
            },
            session_token=sess_f2,
            idem_key="cnt-round3-attempt-1",
        )
        assert status_cnt3 == 409
        assert resp_cnt3["status"] == "REJECTED"
        assert resp_cnt3["reason"] == "COUNTER_ROUND_EXCEEDED"


def test_confirm_counter_true_grants_lease():
    """BUILD_PLAN 3.5: CONFIRM_COUNTER(confirmed=True) accepts counter terms and awards single lease."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"  # Origin Clinician
    roster_f2 = "00000000-0000-0000-0000-000000000020"  # Facility 2 CMO
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        # 1. Create, ACK, and confirm resources
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
            idem_key="confirm-true-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        apply_command(
            conn,
            {"type": "ACK", "referral_id": ref_id, "offer_id": off1_id, "expected_version": 2},
            session_token=sess_f2,
            idem_key="confirm-true-ack-1",
        )

        apply_command(
            conn,
            {
                "type": "RESOURCE_CONFIRM",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 3,
                "candidate_pin": "4321",
                "capabilities": ["OT", "BLOOD", "ANAESTHETIST", "NICU"],
            },
            session_token=sess_f2,
            idem_key="confirm-true-rc-1",
        )

        # 2. Facility 2 counters
        apply_command(
            conn,
            {
                "type": "COUNTER",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 4,
                "candidate_pin": "4321",
                "counter_mask": 1,
            },
            session_token=sess_f2,
            idem_key="confirm-true-cnt-1",
        )

        # 3. Origin clinician confirms counter terms (confirmed = True)
        status_conf, resp_conf = apply_command(
            conn,
            {
                "type": "CONFIRM_COUNTER",
                "referral_id": ref_id,
                "expected_version": 5,
                "confirmed": True,
            },
            session_token=sess_f1,
            idem_key="confirm-true-submit-1",
        )
        assert status_conf == 200
        assert resp_conf["status"] == "COMMITTED"

        # Assert winning offer is ACCEPTED
        assert conn.db.offers[off1_id]["status"] == "ACCEPTED"

        # Assert lease granted to Facility 2
        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "ACCEPTED"
        assert ref["lease_facility_id"] == target1
        assert ref["lease_epoch"] == 1
        assert ref["open_offers"] == 0

        # Assert HANDOVER deadline armed
        handover_dls = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id and d["kind"] == "HANDOVER"]
        assert len(handover_dls) == 1
        assert handover_dls[0]["status"] == "PENDING"


def test_confirm_counter_false_declines_and_advances():
    """BUILD_PLAN 3.5: CONFIRM_COUNTER(confirmed=False) marks offer DECLINED and advances along chain."""
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
            idem_key="confirm-false-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        apply_command(
            conn,
            {"type": "ACK", "referral_id": ref_id, "offer_id": off1_id, "expected_version": 2},
            session_token=sess_f2,
            idem_key="confirm-false-ack-1",
        )

        apply_command(
            conn,
            {
                "type": "COUNTER",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 3,
                "candidate_pin": "4321",
                "counter_mask": 2,
            },
            session_token=sess_f2,
            idem_key="confirm-false-cnt-1",
        )

        # Origin clinician rejects counter terms (confirmed = False)
        status_conf, resp_conf = apply_command(
            conn,
            {
                "type": "CONFIRM_COUNTER",
                "referral_id": ref_id,
                "expected_version": 4,
                "confirmed": False,
            },
            session_token=sess_f1,
            idem_key="confirm-false-submit-1",
        )
        assert status_conf == 200
        assert resp_conf["status"] == "COMMITTED"

        # Assert offer 1 is DECLINED with reason 'COUNTER_REJECTED'
        assert conn.db.offers[off1_id]["status"] == "DECLINED"
        assert conn.db.offers[off1_id]["decline_reason"] == "COUNTER_REJECTED"

        # Assert offer 1 payload grant REVOKED
        assert conn.db.payload_grants[f"{ref_id}:{fac2}"]["status"] == "REVOKED"

        # Assert offer 2 opened for fac3
        off2_matches = [v for v in conn.db.offers.values() if v["referral_id"] == ref_id and v["facility_id"] == fac3]
        assert len(off2_matches) == 1
        assert off2_matches[0]["status"] == "OPEN"

        # Assert referral state is OFFERED
        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "OFFERED"
        assert ref["open_offers"] == 1
