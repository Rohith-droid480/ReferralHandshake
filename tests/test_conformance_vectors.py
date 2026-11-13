"""Tests for Model-Based Conformance Vectors (BUILD_PLAN 4.4, Solution v8 §4, Gate T-C1).

Validates the 28 real-world conformance scenarios from spec/vectors/conformance_vectors.json:
- VEC-SC01 to VEC-SC28 covering degraded connectivity, clinical corner cases,
  ladder advance, counter-offers, soft-open races, transport independence, and mandatory closure.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.db import get_main_connection
from api.rhp.pipeline import apply_command


def test_conformance_vectors_json_spec_integrity():
    """Validates that spec/vectors/conformance_vectors.json contains all 28 locked scenarios."""
    vector_path = Path("spec/vectors/conformance_vectors.json")
    assert vector_path.exists(), "spec/vectors/conformance_vectors.json not found!"

    with open(vector_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("protocol") == "RHP-1"
    vectors = data.get("vectors", [])
    # 28 clinical scenarios (with SC06 split into SC06a and SC06b)
    assert len(vectors) in (28, 29), f"Expected 28-29 conformance vectors, found {len(vectors)}"

    expected_ids = [
        "VEC-SC01", "VEC-SC02", "VEC-SC03", "VEC-SC04", "VEC-SC05",
        "VEC-SC06a", "VEC-SC06b", "VEC-SC07", "VEC-SC08", "VEC-SC09",
        "VEC-SC10", "VEC-SC11", "VEC-SC12", "VEC-SC13", "VEC-SC14",
        "VEC-SC15", "VEC-SC16", "VEC-SC17", "VEC-SC18", "VEC-SC19",
        "VEC-SC20", "VEC-SC21", "VEC-SC22", "VEC-SC23", "VEC-SC24",
        "VEC-SC25", "VEC-SC26", "VEC-SC27", "VEC-SC28"
    ]
    actual_ids = [v["id"] for v in vectors]
    for eid in expected_ids:
        assert eid in actual_ids, f"Missing vector {eid} in conformance_vectors.json"


def test_vec_sc02_decline_advances_ladder():
    """VEC-SC02: Receiver cannot take -> DECLINE advances ladder to next facility."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    fac1 = "00000000-0000-0000-0000-000000000001"
    fac2 = "00000000-0000-0000-0000-000000000002"
    fac3 = "00000000-0000-0000-0000-000000000003"

    with get_main_connection() as conn:
        conn.db.rosters[roster_f2] = {
            "id": roster_f2,
            "facility_id": fac2,
            "role_slot": "CMO",
            "slot_no": 1,
            "phone_e164": "+919880000020",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        token1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess1, _ = redeem_enrollment_ticket(conn, token1, secrets.token_bytes(32), "android")

        token2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess2, _ = redeem_enrollment_ticket(conn, token2, secrets.token_bytes(32), "pwa")
        conn.commit()

        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac1,
                "chain": [fac2, fac3],
            },
            session_token=sess1,
            idem_key=f"sc02-cr-{uuid4().hex[:8]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]

        offers = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id]
        off1 = offers[0]

        # Decline offer 1 from receiving facility 2
        st_dec, resp_dec = apply_command(
            conn,
            {
                "type": "DECLINE",
                "referral_id": ref_id,
                "offer_id": off1["id"],
                "reason": "BEDS_FULL",
                "candidate_pin": "4321",
            },
            session_token=sess2,
            idem_key=f"sc02-dec-{uuid4().hex[:8]}",
        )
        assert st_dec == 200
        assert resp_dec["status"] == "COMMITTED"

        # Offer 2 should now be opened
        ref_offers = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id]
        assert len(ref_offers) == 2
        off2 = next(o for o in ref_offers if o["facility_id"] == fac3)
        assert off2["status"] == "OPEN"
        assert off2["step"] == 1


def test_vec_sc08_all_approved_facilities_fail_escalates_to_dispatcher():
    """VEC-SC08: When all facilities in chain fail, referral escalates to DISPATCHER."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    fac1 = "00000000-0000-0000-0000-000000000001"
    fac2 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        conn.db.rosters[roster_f2] = {
            "id": roster_f2,
            "facility_id": fac2,
            "role_slot": "CMO",
            "slot_no": 1,
            "phone_e164": "+919880000020",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        token1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess1, _ = redeem_enrollment_ticket(conn, token1, secrets.token_bytes(32), "android")

        token2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess2, _ = redeem_enrollment_ticket(conn, token2, secrets.token_bytes(32), "pwa")
        conn.commit()

        # 1-facility chain
        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac1,
                "chain": [fac2],
            },
            session_token=sess1,
            idem_key=f"sc08-cr-{uuid4().hex[:8]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]

        offers = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id]
        off1 = offers[0]

        # Decline the only facility from receiving facility 2
        st_dec, resp_dec = apply_command(
            conn,
            {
                "type": "DECLINE",
                "referral_id": ref_id,
                "offer_id": off1["id"],
                "reason": "EQUIPMENT_FAILURE",
                "candidate_pin": "4321",
            },
            session_token=sess2,
            idem_key=f"sc08-dec-{uuid4().hex[:8]}",
        )
        assert st_dec == 200

        # Referral is now ESCALATED_TO_DISPATCHER with a pending DISPATCH_ACTION deadline
        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "ESCALATED_TO_DISPATCHER"

        deadlines = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id]
        dispatch_deadlines = [d for d in deadlines if d["kind"] == "DISPATCH_ACTION" and d["status"] == "PENDING"]
        assert len(dispatch_deadlines) == 1


def test_vec_sc18_transport_update_independent_of_handshake():
    """VEC-SC18: Transport updates do not block or mutate handshake track (Invariant I3)."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    roster_emt = "00000000-0000-0000-0000-000000000099"
    fac1 = "00000000-0000-0000-0000-000000000001"
    fac2 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        conn.db.rosters[roster_emt] = {
            "id": roster_emt,
            "facility_id": fac1,
            "role_slot": "EMT",
            "slot_no": 1,
            "phone_e164": "+919880000099",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        token_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig, _ = redeem_enrollment_ticket(conn, token_orig, secrets.token_bytes(32), "android")

        token_emt, _ = create_enrollment_ticket(conn, roster_emt, roster_emt)
        sess_emt, _ = redeem_enrollment_ticket(conn, token_emt, secrets.token_bytes(32), "android")
        conn.commit()

        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac1,
                "chain": [fac2],
            },
            session_token=sess_orig,
            idem_key=f"sc18-cr-{uuid4().hex[:8]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]

        # TR_UPDATE(DISPATCHED) from EMT while hs_state is OFFERED
        st_tr1, _ = apply_command(
            conn,
            {"type": "TR_UPDATE", "referral_id": ref_id, "tr_state": "DISPATCHED"},
            session_token=sess_emt,
            idem_key=f"sc18-tr1-{uuid4().hex[:8]}",
        )
        assert st_tr1 == 200
        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "OFFERED"
        assert ref["tr_state"] == "DISPATCHED"

        # TR_UPDATE(EN_ROUTE) from EMT while hs_state is still OFFERED
        st_tr2, _ = apply_command(
            conn,
            {"type": "TR_UPDATE", "referral_id": ref_id, "tr_state": "EN_ROUTE"},
            session_token=sess_emt,
            idem_key=f"sc18-tr2-{uuid4().hex[:8]}",
        )
        assert st_tr2 == 200
        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "OFFERED"
        assert ref["tr_state"] == "EN_ROUTE"


def test_vec_sc20_counter_max_two_rounds_enforced():
    """VEC-SC20: Maximum 2 counter rounds enforced; 3rd counter rejected with 409."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    fac1 = "00000000-0000-0000-0000-000000000001"
    fac2 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        conn.db.rosters[roster_f2] = {
            "id": roster_f2,
            "facility_id": fac2,
            "role_slot": "CMO",
            "slot_no": 1,
            "phone_e164": "+919880000020",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        token1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess1, _ = redeem_enrollment_ticket(conn, token1, secrets.token_bytes(32), "android")

        token2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess2, _ = redeem_enrollment_ticket(conn, token2, secrets.token_bytes(32), "pwa")
        conn.commit()

        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac1,
                "chain": [fac2],
            },
            session_token=sess1,
            idem_key=f"sc20-cr-{uuid4().hex[:8]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]

        offers = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id]
        off = offers[0]

        # Round 1 COUNTER from receiving facility 2 -> 200
        st1, resp1 = apply_command(
            conn,
            {"type": "COUNTER", "referral_id": ref_id, "offer_id": off["id"], "counter_mask": 1, "candidate_pin": "4321"},
            session_token=sess2,
            idem_key=f"sc20-cnt1-{uuid4().hex[:8]}",
        )
        assert st1 == 200

        # Simulate reaching counter round 2 cap
        conn.db.offers[off["id"]]["counter_round"] = 2
        conn.db.offers[off["id"]]["status"] = "OPEN"

        # Round 3 COUNTER -> 409 COUNTER_ROUND_EXCEEDED
        st3, resp3 = apply_command(
            conn,
            {"type": "COUNTER", "referral_id": ref_id, "offer_id": off["id"], "counter_mask": 3, "candidate_pin": "4321"},
            session_token=sess2,
            idem_key=f"sc20-cnt3-{uuid4().hex[:8]}",
        )
        assert st3 == 409
        assert resp3["reason"] == "COUNTER_ROUND_EXCEEDED"
