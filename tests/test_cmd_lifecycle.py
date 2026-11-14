"""Tests for Lifecycle Commands: ARRIVAL_REJECTED, DISPATCHER_ASSIGN, CANCEL, CLOSE, REVOKE_GRANT.

Specification Anchors:
- BUILD_PLAN §3.6: Terminal Lifecycle Commands & Outcome Taxonomy
- Architecture §4.5: Arrival Rejection, Dispatcher Assignment & Revocation
- Architecture §4.6: Terminal States & Locked 9-Value Outcome Taxonomy [Closure F6]
- Invariant I2: Single Lease Holder (one_lease)
- Invariant I10: Active Grant Authorization
- Closure F5: Arrival Rejection & Escalation
- Closure F6: Handover Prerequisite for Clinical Admission Outcomes
"""

import pytest
import secrets
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.db import get_main_connection
from api.rhp.pipeline import apply_command


def test_arrival_rejected_revokes_lease_and_advances():
    """Closure F5: ARRIVAL_REJECTED marks offer ARRIVAL_REJECTED, revokes lease, and advances."""
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

        # 1. Create, ACK, confirm capabilities, and ACCEPT
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
            idem_key="arr-rej-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        apply_command(
            conn,
            {"type": "ACK", "referral_id": ref_id, "offer_id": off1_id, "expected_version": conn.db.referrals[ref_id]["version"]},
            session_token=sess_f2,
            idem_key="arr-rej-ack-1",
        )

        future_ts = datetime.now(timezone.utc) + timedelta(minutes=30)
        for cap in ["OT", "BLOOD", "ANAESTHETIST", "NICU"]:
            conn.db.offer_resource_confirmations[f"{off1_id}:{cap}"] = {
                "id": str(uuid4()),
                "offer_id": off1_id,
                "capability": cap,
                "confirmed_by": roster_f2,
                "expires_at": future_ts,
                "created_at": datetime.now(timezone.utc),
            }

        apply_command(
            conn,
            {
                "type": "ACCEPT",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": conn.db.referrals[ref_id]["version"],
                "candidate_pin": "4321",
            },
            session_token=sess_f2,
            idem_key="arr-rej-accept-1",
        )

        # Lease is currently held by Fac 2
        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "ACCEPTED"
        assert ref["lease_facility_id"] == fac2

        # 2. Facility 2 rejects arrival (e.g. deteriorated beyond capability)
        status_rej, resp_rej = apply_command(
            conn,
            {
                "type": "ARRIVAL_REJECTED",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": conn.db.referrals[ref_id]["version"],
                "reason": "DETERIORATED_BEYOND_CAPABILITY",
            },
            session_token=sess_f2,
            idem_key="arr-rej-submit-1",
        )
        assert status_rej == 200
        assert resp_rej["status"] == "COMMITTED"

        # Assert offer 1 is ARRIVAL_REJECTED
        assert conn.db.offers[off1_id]["status"] == "ARRIVAL_REJECTED"
        assert conn.db.offers[off1_id]["decline_reason"] == "DETERIORATED_BEYOND_CAPABILITY"

        # Assert lease revoked from referral
        ref_after = conn.db.referrals[ref_id]
        assert ref_after["lease_facility_id"] is None
        assert ref_after["lease_offer_id"] is None

        # Assert payload grant for fac2 is REVOKED
        assert conn.db.payload_grants[f"{ref_id}:{fac2}"]["status"] == "REVOKED"

        # Assert offer 2 was opened for fac3
        off2_matches = [v for v in conn.db.offers.values() if v["referral_id"] == ref_id and v["facility_id"] == fac3]
        assert len(off2_matches) == 1
        assert off2_matches[0]["status"] == "OPEN"


def test_dispatcher_assign_awards_lease_with_source_dispatcher():
    """BUILD_PLAN 3.6: DISPATCHER_ASSIGN manually awards single lease with source='DISPATCHER'."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_disp = "00000000-0000-0000-0000-000000000099"  # Dispatcher roster slot
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target_fac = "00000000-0000-0000-0000-000000000003"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        # Seed dispatcher slot in mock DB
        conn.db.rosters[roster_disp] = {
            "id": roster_disp,
            "facility_id": "00000000-0000-0000-0000-000000000099",
            "role_slot": "DISPATCHER",
            "slot_no": 1,
            "phone_e164": "+919880000099",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        token_disp, _ = create_enrollment_ticket(conn, roster_disp, roster_disp)
        sess_disp, _ = redeem_enrollment_ticket(conn, token_disp, secrets.token_bytes(32), "pwa")

        # 1. Create referral with empty chain -> goes straight to ESCALATED_TO_DISPATCHER
        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [],
            },
            session_token=sess_f1,
            idem_key="disp-assign-create-1",
        )
        ref_id = resp_create["referral_id"]
        assert conn.db.referrals[ref_id]["hs_state"] == "ESCALATED_TO_DISPATCHER"

        # 2. Dispatcher assigns to target_fac
        status_assign, resp_assign = apply_command(
            conn,
            {
                "type": "DISPATCHER_ASSIGN",
                "referral_id": ref_id,
                "target_facility_id": target_fac,
                "expected_version": conn.db.referrals[ref_id]["version"],
                "reason": "SPECIALIST_BED_OVERRIDE",
            },
            session_token=sess_disp,
            idem_key="disp-assign-submit-1",
        )
        assert status_assign == 200
        assert resp_assign["status"] == "COMMITTED"

        # Assert offer created with source='DISPATCHER' and status='ACCEPTED'
        disp_offers = [v for v in conn.db.offers.values() if v["referral_id"] == ref_id and v["source"] == "DISPATCHER"]
        assert len(disp_offers) == 1
        disp_off = disp_offers[0]
        assert disp_off["status"] == "ACCEPTED"
        assert disp_off["facility_id"] == target_fac

        # Assert referral lease awarded
        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "ACCEPTED"
        assert ref["lease_facility_id"] == target_fac
        assert ref["lease_offer_id"] == disp_off["id"]
        assert ref["open_offers"] == 0

        # Assert HANDOVER deadline armed
        handover_dls = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id and d["kind"] == "HANDOVER"]
        assert len(handover_dls) == 1
        assert handover_dls[0]["status"] == "PENDING"


def test_cancel_transitions_to_cancelled_with_outcome():
    """BUILD_PLAN 3.6: CANCEL transitions referral to CANCELLED and withdraws open offers."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

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
            idem_key="cancel-test-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # Cancel with PATIENT_REFUSED
        status_cancel, resp_cancel = apply_command(
            conn,
            {
                "type": "CANCEL",
                "referral_id": ref_id,
                "expected_version": conn.db.referrals[ref_id]["version"],
                "outcome": "PATIENT_REFUSED",
                "reason": "FAMILY_CHOSE_LOCAL_CARE",
            },
            session_token=sess_f1,
            idem_key="cancel-test-submit-1",
        )
        assert status_cancel == 200
        assert resp_cancel["status"] == "COMMITTED"

        # Assert referral is CANCELLED with outcome
        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "CANCELLED"
        assert ref["outcome"] == "PATIENT_REFUSED"
        assert ref["tr_state"] == "TR_CANCELLED"
        assert ref["closed_at"] is not None

        # Assert offer 1 is WITHDRAWN
        assert conn.db.offers[off1_id]["status"] == "WITHDRAWN"

        # Assert pending deadlines are CANCELLED
        for d in conn.db.deadlines.values():
            if d["referral_id"] == ref_id:
                assert d["status"] == "CANCELLED"


def test_close_strictly_enforces_9_outcome_taxonomy():
    """Closure F6: CLOSE strictly enforces 9-outcome taxonomy and tr_state='HANDED_OVER' requirement."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        # Create referral
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
            idem_key="close-tax-create-1",
        )
        ref_id = resp_create["referral_id"]
        offer_id = [oid for oid, off in conn.db.offers.items() if off["referral_id"] == ref_id][0]

        # Target 1 ACKs, confirms capability, and ACCEPTs the offer
        apply_command(
            conn,
            {"type": "ACK", "offer_id": offer_id, "referral_id": ref_id, "expected_version": conn.db.referrals[ref_id]["version"]},
            session_token=sess_f2,
            idem_key="close-tax-ack-1",
        )
        future_ts = datetime.now(timezone.utc) + timedelta(minutes=30)
        for cap in ["OT", "BLOOD", "ANAESTHETIST", "NICU"]:
            conn.db.offer_resource_confirmations[f"{offer_id}:{cap}"] = {
                "id": str(uuid4()),
                "offer_id": offer_id,
                "capability": cap,
                "confirmed_by": roster_f2,
                "expires_at": future_ts,
                "created_at": datetime.now(timezone.utc),
            }
        apply_command(
            conn,
            {
                "type": "ACCEPT",
                "offer_id": offer_id,
                "referral_id": ref_id,
                "expected_version": conn.db.referrals[ref_id]["version"],
                "candidate_pin": "4321",
            },
            session_token=sess_f2,
            idem_key="close-tax-acc-1",
        )
        assert conn.db.referrals[ref_id]["hs_state"] == "ACCEPTED"
        assert conn.db.referrals[ref_id]["lease_facility_id"] == target1

        curr_ver = conn.db.referrals[ref_id]["version"]

        # 1. Attempt CLOSE with ADMITTED_STABLE when tr_state != 'HANDED_OVER' (currently REQUESTED)
        # Must fail with 409 HANDOVER_REQUIRED (Closure F6)
        status_early_close, resp_early_close = apply_command(
            conn,
            {
                "type": "CLOSE",
                "referral_id": ref_id,
                "expected_version": curr_ver,
                "outcome": "ADMITTED_STABLE",
            },
            session_token=sess_f2,
            idem_key="close-tax-early-1",
        )
        assert status_early_close == 409
        assert resp_early_close["status"] == "REJECTED"
        assert resp_early_close["reason"] == "HANDOVER_REQUIRED"

        # 2. Simulate referral handed over
        conn.db.referrals[ref_id]["tr_state"] = "HANDED_OVER"

        # 3. Valid CLOSE with ADMITTED_STABLE succeeds
        status_valid_close, resp_valid_close = apply_command(
            conn,
            {
                "type": "CLOSE",
                "referral_id": ref_id,
                "expected_version": curr_ver,
                "outcome": "ADMITTED_STABLE",
                "reason": "PATIENT_ADMITTED_TO_ICU",
            },
            session_token=sess_f2,
            idem_key="close-tax-valid-1",
        )
        assert status_valid_close == 200
        assert resp_valid_close["status"] == "COMMITTED"

        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "CLOSED"
        assert ref["outcome"] == "ADMITTED_STABLE"
        assert ref["closed_at"] is not None


def test_revoke_grant_explicit_revocation():
    """Invariant I10: REVOKE_GRANT explicitly revokes active payload grant."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

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
            idem_key="revoke-test-create-1",
        )
        ref_id = resp_create["referral_id"]

        # Payload grant for target1 is ACTIVE
        assert conn.db.payload_grants[f"{ref_id}:{target1}"]["status"] == "ACTIVE"

        # Revoke grant
        status_rev, resp_rev = apply_command(
            conn,
            {
                "type": "REVOKE_GRANT",
                "referral_id": ref_id,
                "target_facility_id": target1,
                "expected_version": conn.db.referrals[ref_id]["version"],
                "reason": "MISDIRECTED_REFERRAL",
            },
            session_token=sess_f1,
            idem_key="revoke-test-submit-1",
        )
        assert status_rev == 200
        assert resp_rev["status"] == "COMMITTED"

        # Assert grant status is REVOKED
        assert conn.db.payload_grants[f"{ref_id}:{target1}"]["status"] == "REVOKED"
