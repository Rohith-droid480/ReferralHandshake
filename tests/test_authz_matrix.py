"""ReferralHandshake Protocol RHP-1 — Role-Command Authorization Matrix & Schema Test Suite.

Specification Anchors:
- Architecture §5: apply_command() transaction pipeline (Step 5: Authority & Fencing)
- Architecture §7: rhp_allowed, rhp_detail_ok [Closure F9, Invariant I11]
- Architecture §9: Identity & Role-Command Authorization Matrix [Invariant I6]
- Invariant I6: Role slot integrity, session validity, and BOLA prevention
- Invariant I11: RFC 8785 canonical JSON with strict float rejection and closed detail allowlist
- Closure F9: Closed key allowlist for event details (zero free-text clinical notes)
- Verification Gates: T-I6, T-I6b, T-F9
- BUILD_PLAN §2.4: Role-Command Authorization Matrix & Strict Pydantic Schemas
"""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from api.rhp.auth import AuthError, Session, create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.db import get_main_connection, reset_mock_db
from api.rhp.pipeline import OfferState, ReferralState, apply_command
from api.rhp.schemas import (
    AcceptCmd,
    CreateCmd,
    authorize,
    parse_command,
    validate_event_detail,
)
from api.rhp.transitions import TransitionReject


@pytest.fixture(autouse=True)
def setup_db():
    """Resets mock database before each test run."""
    reset_mock_db()


def test_cross_facility_accept_returns_403():
    """BOLA Prevention & Acceptance Criterion: Cross-facility accepts return 403 CROSS_FACILITY_FORBIDDEN."""
    # Roster 10 is at Facility 1 (Bengaluru DH)
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    fac1_id = "00000000-0000-0000-0000-000000000001"
    fac2_id = "00000000-0000-0000-0000-000000000002"  # Ramanagara CHC

    with get_main_connection() as conn:
        token, sess = create_enrollment_ticket(conn, roster_f1, roster_f1)
        session_token, _ = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        # 1. Create referral with offer directed to Facility 2
        status, resp = apply_command(
            conn,
            {
                "type": "CREATE",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac1_id,
                "expected_version": 0,
                "chain": [fac2_id],
            },
            session_token=session_token,
            idem_key="create-for-cross-fac-1",
        )
        assert status == 200
        ref_id = resp["referral_id"]
        off_id = list(conn.db.offers.keys())[0]

        # 2. Clinician at Facility 1 attempts to ACCEPT the offer for Facility 2 -> MUST RETURN 403
        status_accept, resp_accept = apply_command(
            conn,
            {
                "type": "ACCEPT",
                "referral_id": ref_id,
                "offer_id": off_id,
                "expected_version": 2,
                "candidate_pin": "4321",
            },
            session_token=session_token,
            idem_key="cross-accept-attempt-1",
        )
        assert status_accept == 403
        assert resp_accept["status"] == "REJECTED"
        assert resp_accept["reason"] == "CROSS_FACILITY_FORBIDDEN"


def test_extra_json_fields_return_422():
    """Acceptance Criterion: Strict extra='forbid' models reject unknown JSON fields with 422."""
    fac_id = "00000000-0000-0000-0000-000000000001"

    # Attempt to parse payload with unexpected injection field
    with pytest.raises(TransitionReject) as exc_info:
        parse_command({
            "type": "CREATE",
            "need_class": "OB_ECLAMPSIA",
            "origin_facility_id": fac_id,
            "expected_version": 0,
            "chain": [fac_id],
            "injected_extra_field": "forbidden_payload",
        })

    assert exc_info.value.http_status == 422
    assert exc_info.value.reason_code == "INVALID_COMMAND_PAYLOAD"
    assert "Extra inputs are not permitted" in exc_info.value.message


def test_fuzzing_event_detail_blocks_free_text_patient_data():
    """Invariant I11 & Closure F9 (Gate T-F9): Fuzzing event.detail with free-text patient names is blocked."""
    # Valid detail passes
    validate_event_detail("REFERRAL_CREATED", {
        "mode": "SEQUENTIAL",
        "need_class": "OB_ECLAMPSIA",
        "chain_len": 2,
        "profile": "DEMO_FAST",
        "mgso4": "GIVEN",
    })

    # Free-text patient name must be rejected
    with pytest.raises(ValueError) as exc_info:
        validate_event_detail("REFERRAL_CREATED", {
            "mode": "SEQUENTIAL",
            "need_class": "OB_ECLAMPSIA",
            "chain_len": 2,
            "profile": "DEMO_FAST",
            "mgso4": "Patient Ananya Rao given 4g loading dose",  # Free-text clinical leak!
        })
    assert "Free-text and patient names are strictly forbidden" in str(exc_info.value)

    # Disallowed detail key must be rejected
    with pytest.raises(ValueError) as exc_key:
        validate_event_detail("REFERRAL_CREATED", {
            "mode": "SEQUENTIAL",
            "patient_aadhaar": "123456789012",
        })
    assert "Forbidden detail key 'patient_aadhaar'" in str(exc_key.value)


def test_fuzzing_event_detail_blocks_floating_point_numbers():
    """Invariant I11 & RFC 8785 Canonical JSON: Floats are strictly prohibited in event.detail."""
    with pytest.raises(TypeError) as exc_info:
        validate_event_detail("REFERRAL_CREATED", {
            "mode": "SEQUENTIAL",
            "chain_len": 2.5,  # Float!
        })
    assert "Floating point numbers strictly forbidden" in str(exc_info.value)


def test_roster_inactivity_window_enforcement():
    """Invariant I6 (Gate T-I6): Duty window expiry immediately revokes authorization with 403 ROSTER_INACTIVE."""
    now = datetime.now(timezone.utc)
    expired_roster_id = "00000000-0000-0000-0000-000000000099"
    fac_id = "00000000-0000-0000-0000-000000000001"

    with get_main_connection() as conn:
        # Seed an expired roster slot in DB
        conn.db.rosters[expired_roster_id] = {
            "id": expired_roster_id,
            "facility_id": fac_id,
            "role_slot": "CMO",
            "slot_no": 1,
            "phone_e164": "+919880000099",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": now - timedelta(hours=8),
            "valid_to": now - timedelta(minutes=10),  # Expired 10 mins ago!
        }

        token, _ = create_enrollment_ticket(conn, expired_roster_id, expired_roster_id)
        session_token, sess = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        # Attempt CREATE command with expired roster
        status, resp = apply_command(
            conn,
            {
                "type": "CREATE",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_id,
                "expected_version": 0,
            },
            session_token=session_token,
            idem_key="expired-roster-cmd-1",
        )
        assert status == 403
        assert resp["status"] == "REJECTED"
        assert resp["reason"] == "ROSTER_INACTIVE"


def test_dispatcher_proxy_privileges():
    """Dispatcher without proxy=True is rejected; with proxy=True and proxy_for succeeds."""
    disp_roster_id = "00000000-0000-0000-0000-000000000050"
    fac_id = "00000000-0000-0000-0000-000000000001"
    now = datetime.now(timezone.utc)

    with get_main_connection() as conn:
        conn.db.rosters[disp_roster_id] = {
            "id": disp_roster_id,
            "facility_id": fac_id,
            "role_slot": "DISPATCHER",
            "slot_no": 1,
            "phone_e164": "+919880000050",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": now,
            "valid_to": None,
        }

        token, _ = create_enrollment_ticket(conn, disp_roster_id, disp_roster_id)
        session_token, sess = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        # Dispatcher attempting receiving desk command without proxy=True raises 403 DISPATCHER_PROXY_REQUIRED
        cmd_no_proxy = parse_command({
            "type": "ACK",
            "referral_id": str(uuid4()),
            "offer_id": str(uuid4()),
            "expected_version": 1,
            "proxy": False,
        })
        with pytest.raises(AuthError) as exc_disp:
            authorize(conn, None, None, sess, cmd_no_proxy, now)
        assert exc_disp.value.http_status == 403
        assert exc_disp.value.reason_code == "DISPATCHER_PROXY_REQUIRED"

        # Dispatcher with proxy=True and proxy_for is authorized
        cmd_proxy = parse_command({
            "type": "ACK",
            "referral_id": str(uuid4()),
            "offer_id": str(uuid4()),
            "expected_version": 1,
            "proxy": True,
            "proxy_for": UUID("00000000-0000-0000-0000-000000000010"),
        })
        # Should not raise
        authorize(conn, None, None, sess, cmd_proxy, now)


def test_origin_facility_mismatch_rejection():
    """Clinician cannot create a referral on behalf of a foreign origin facility."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"  # at Facility 1
    fac2_id = "00000000-0000-0000-0000-000000000002"     # Facility 2

    with get_main_connection() as conn:
        token, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        session_token, _ = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        status, resp = apply_command(
            conn,
            {
                "type": "CREATE",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac2_id,  # Mismatch with clinician's facility!
                "expected_version": 0,
            },
            session_token=session_token,
            idem_key="origin-fac-mismatch-1",
        )
        assert status == 403
        assert resp["reason"] == "ORIGIN_FACILITY_MISMATCH"

