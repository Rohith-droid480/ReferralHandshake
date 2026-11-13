"""ReferralHandshake Protocol RHP-1 — CREATE Command Unit & Conformance Test Suite.

Specification Anchors:
- Architecture §4.3: Initial Offer Opening & Sequential vs Parallel2 Mode Selection
- Architecture §4.4: Escalation to Dispatcher on Empty Catchment Chain
- Architecture §6: Timing Model, Ladder Rungs & Profile Bounds [F2, F3, I13]
- Architecture §8: Paper Code (9-char Crockford Base32 + mod-37 check) [F7]
- Invariant I1: Pending Deadlines & Timely Notification (Gate T-I1)
- Invariant I7: Catchment Chain Integrity & Target Authorization (Gate T-I7)
- Invariant I12: Open Offers Bound (open_offers <= 2)
- Defect D1: Pre-referral MgSO4 status is answer-required, never knowledge-required
- Verification Gates: T-I1, T-I7
- BUILD_PLAN §3.1: CREATE Command, Chain Snapshot, Mode Selection, Initial Offers, Grants & Deadlines
"""

import secrets
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.commands.create import (
    CROCKFORD_BASE32_ALPHABET,
    CROCKFORD_CHECK_ALPHABET,
    generate_paper_code,
    validate_paper_code,
)
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


# =============================================================================
# 1. Paper Code Generator & Validator Unit Tests (Architecture §8)
# =============================================================================

def test_paper_code_generation_and_validation():
    """Architecture §8: 9-char Crockford Base32 + mod-37 check character properties."""
    for _ in range(50):
        code = generate_paper_code()
        assert len(code) == 9
        # First 8 chars in Crockford Base32 alphabet
        for ch in code[:8]:
            assert ch in CROCKFORD_BASE32_ALPHABET
        # 9th char in Crockford check alphabet
        assert code[8] in CROCKFORD_CHECK_ALPHABET
        # Validates successfully
        assert validate_paper_code(code) is True


def test_paper_code_detects_single_symbol_mutation():
    """Architecture §8: Any single-symbol corruption is detected by mod 37 prime check."""
    for _ in range(20):
        code = generate_paper_code()
        # Mutate first symbol
        orig_char = code[0]
        mutated_char = "Z" if orig_char != "Z" else "A"
        bad_code = mutated_char + code[1:]
        assert validate_paper_code(bad_code) is False

        # Mutate check symbol
        orig_check = code[8]
        mutated_check = "*" if orig_check != "*" else "0"
        bad_check_code = code[:8] + mutated_check
        assert validate_paper_code(bad_check_code) is False


def test_paper_code_detects_adjacent_transposition():
    """Architecture §8: Adjacent transpositions (a-b)*32^i*31 != 0 mod 37 are always detected."""
    for _ in range(20):
        code = generate_paper_code()
        # Find adjacent unequal characters in body
        for i in range(7):
            if code[i] != code[i + 1]:
                transposed = list(code)
                transposed[i], transposed[i + 1] = transposed[i + 1], transposed[i]
                transposed_code = "".join(transposed)
                assert validate_paper_code(transposed_code) is False
                break


# =============================================================================
# 2. CREATE Command: SEQUENTIAL Mode & Deadlines (Gate T-I1)
# =============================================================================

def test_create_sequential_mode_opens_single_offer_and_deadlines():
    """Invariant I1 (Gate T-I1): Sequential CREATE arms ACK and NOTICE deadlines and opens 1 offer."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"
    target2 = "00000000-0000-0000-0000-000000000003"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        status, resp = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [target1, target2],
                "mgso4_status": "GIVEN",
                "profile_id": "DEMO_FAST",
            },
            session_token=session_token,
            idem_key="create-sequential-test-1",
        )
        assert status == 200
        ref_id = resp["referral_id"]

        # 1. Assert referral state
        r = conn.db.referrals[ref_id]
        assert r["hs_state"] == "OFFERED"
        assert r["open_offers"] == 1
        assert r["mode"] == "SEQUENTIAL"
        assert r["mgso4_status"] == "GIVEN"
        assert validate_paper_code(r["paper_code"]) is True

        # 2. Assert exactly 1 offer opened for target1 with step 1
        ref_offers = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id]
        assert len(ref_offers) == 1
        off = ref_offers[0]
        assert off["facility_id"] == target1
        assert off["status"] == "OPEN"
        assert off["step"] == 1
        assert off["source"] == "CHAIN"

        # 3. Invariant I1: Assert ACK, NOTICE_VOICE, NOTICE_PROXY deadlines exist and are PENDING
        ref_deadlines = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id]
        deadline_kinds = {d["kind"] for d in ref_deadlines}
        assert "ACK" in deadline_kinds
        assert "NOTICE_VOICE" in deadline_kinds
        assert "NOTICE_PROXY" in deadline_kinds
        for d in ref_deadlines:
            assert d["status"] == "PENDING"
            assert d["offer_id"] == off["id"]

        # 4. Assert active payload grants for origin and target1
        grants = conn.db.payload_grants
        assert f"{ref_id}:{origin_fac}" in grants
        assert grants[f"{ref_id}:{origin_fac}"]["status"] == "ACTIVE"
        assert f"{ref_id}:{target1}" in grants
        assert grants[f"{ref_id}:{target1}"]["status"] == "ACTIVE"


# =============================================================================
# 3. CREATE Command: PARALLEL2 Mode (Invariant I12)
# =============================================================================

def test_create_parallel2_mode_opens_two_offers():
    """Invariant I12: PARALLEL2 mode opens up to 2 concurrent offers (open_offers == 2)."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"
    target2 = "00000000-0000-0000-0000-000000000003"
    target3 = "00000000-0000-0000-0000-000000000004"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        status, resp = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "PARALLEL2",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [target1, target2, target3],
                "mgso4_status": "NONE_GIVEN",
                "profile_id": "DEMO_FAST",
            },
            session_token=session_token,
            idem_key="create-parallel2-test-1",
        )
        assert status == 200
        ref_id = resp["referral_id"]

        r = conn.db.referrals[ref_id]
        assert r["hs_state"] == "OFFERED"
        assert r["open_offers"] == 2
        assert r["mode"] == "PARALLEL2"

        # Assert exactly 2 offers opened (target1 and target2)
        ref_offers = sorted([o for o in conn.db.offers.values() if o["referral_id"] == ref_id], key=lambda x: x["step"])
        assert len(ref_offers) == 2
        assert ref_offers[0]["facility_id"] == target1
        assert ref_offers[0]["step"] == 1
        assert ref_offers[1]["facility_id"] == target2
        assert ref_offers[1]["step"] == 2

        # Assert both offers have ACK deadlines
        ack_deadlines = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id and d["kind"] == "ACK"]
        assert len(ack_deadlines) == 2


# =============================================================================
# 4. CREATE Command: Empty Catchment Chain Escalation
# =============================================================================

def test_create_empty_chain_escalates_to_dispatcher_and_arms_dispatch_action():
    """Architecture §4.4: Empty chain creates referral in ESCALATED_TO_DISPATCHER with DISPATCH_ACTION."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        status, resp = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [],  # Empty chain!
                "mgso4_status": "UNKNOWN",
                "profile_id": "DEMO_FAST",
            },
            session_token=session_token,
            idem_key="create-empty-chain-test-1",
        )
        assert status == 200
        ref_id = resp["referral_id"]

        r = conn.db.referrals[ref_id]
        assert r["hs_state"] == "ESCALATED_TO_DISPATCHER"
        assert r["open_offers"] == 0
        assert len(r["chain"]) == 0

        # Assert DISPATCH_ACTION deadline exists
        ref_deadlines = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id]
        assert len(ref_deadlines) == 1
        assert ref_deadlines[0]["kind"] == "DISPATCH_ACTION"
        assert ref_deadlines[0]["status"] == "PENDING"
        assert ref_deadlines[0]["offer_id"] is None


# =============================================================================
# 5. Invariant I7: Catchment Chain Integrity (Gate T-I7)
# =============================================================================

def test_create_rejects_unapproved_target_facility_i7():
    """Invariant I7 (Gate T-I7): Reject 422 I7_NOT_IN_CHAIN if target facility is not in approved catchment."""
    roster_id = "a1111111-0000-0000-0000-000000000001"  # Clinician at PHC Channapatna
    origin_fac = "11111111-1111-1111-1111-111111111111"  # PHC Channapatna
    approved_target = "22222222-2222-2222-2222-222222222222"  # CHC Ramanagara
    unapproved_target = "99999999-9999-9999-9999-999999999999"  # Rogue facility

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        # 1. Chain with unapproved target raises 422 I7_NOT_IN_CHAIN
        status_bad, resp_bad = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OBSTETRIC_EMERGENCY",
                "origin_facility_id": origin_fac,
                "chain": [approved_target, unapproved_target],
                "mgso4_status": "GIVEN",
                "profile_id": "DEMO_FAST",
            },
            session_token=session_token,
            idem_key="create-unapproved-catchment-1",
        )
        assert status_bad == 422
        assert resp_bad["status"] == "REJECTED"
        assert resp_bad["reason"] == "I7_NOT_IN_CHAIN"

        # 2. Chain with only approved targets passes cleanly
        status_ok, resp_ok = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OBSTETRIC_EMERGENCY",
                "origin_facility_id": origin_fac,
                "chain": [approved_target],
                "mgso4_status": "GIVEN",
                "profile_id": "DEMO_FAST",
            },
            session_token=session_token,
            idem_key="create-approved-catchment-1",
        )
        assert status_ok == 200
        assert resp_ok["status"] == "COMMITTED"


# =============================================================================
# 6. Defect D1: Pre-referral MgSO4 Status Never Blocks Care
# =============================================================================

def test_create_mgso4_unknown_passes_without_blocking():
    """Defect D1: mgso4_status=UNKNOWN never blocks creation or ambulance dispatch."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        status, resp = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [target1],
                "mgso4_status": "UNKNOWN",  # Unknown dose administered
                "profile_id": "DEMO_FAST",
            },
            session_token=session_token,
            idem_key="create-mgso4-unknown-1",
        )
        assert status == 200
        ref_id = resp["referral_id"]
        assert conn.db.referrals[ref_id]["mgso4_status"] == "UNKNOWN"
