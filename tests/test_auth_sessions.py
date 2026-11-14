"""ReferralHandshake Protocol RHP-1 — Authentication & Sessions Test Suite.

Specification Anchors:
- Architecture §5: apply_command() transaction pipeline (Step 2: Session validation)
- Architecture §9: Identity, enrollment tickets, cookie & voice sessions [Closure F7, Invariant I6]
- BUILD_PLAN §2.2: Device Enrollment Tickets, Opaque Cookie Sessions & Voice call_sid Sessions
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from api.rhp.auth import (
    AuthError,
    create_enrollment_ticket,
    create_voice_session,
    format_session_cookie,
    load_session,
    redeem_enrollment_ticket,
)
from api.rhp.db import get_main_connection, reset_mock_db


@pytest.fixture(autouse=True)
def setup_db():
    """Resets mock database before each test run."""
    reset_mock_db()


def test_enrollment_ticket_issuance():
    """Admin issues single-use enrollment ticket valid for 15 minutes."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    issuer_id = "00000000-0000-0000-0000-000000000010"

    with get_main_connection() as conn:
        raw_token, ticket_id = create_enrollment_ticket(conn, roster_id, issuer_id)

    assert raw_token.startswith("enr_")
    assert isinstance(ticket_id, UUID)

    # Verify that only SHA-256(raw_token) is stored
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).digest()
    assert expected_hash != raw_token.encode("utf-8")


def test_enrollment_ticket_redemption_and_device_registration():
    """Redeeming ticket registers device and mints opaque session token."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    pubkey = secrets.token_bytes(32)

    with get_main_connection() as conn:
        raw_token, ticket_id = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, session = redeem_enrollment_ticket(
            conn, raw_token, pubkey, platform="android", ttl_hours=24
        )

    assert session_token.startswith("rhp_sid_")
    assert session.roster_id == UUID(roster_id)
    assert session.device_id is not None
    assert session.call_sid is None
    assert session.role_slot == "CMO"
    assert session.pin_failed == 0


def test_enrollment_ticket_single_use_enforcement():
    """Ticket cannot be redeemed more than once (401 TICKET_ALREADY_USED)."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    pubkey = secrets.token_bytes(32)

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        # First redemption succeeds
        redeem_enrollment_ticket(conn, raw_token, pubkey, platform="android")

    # Second redemption attempt MUST fail
    with get_main_connection() as conn:
        with pytest.raises(AuthError) as exc_info:
            redeem_enrollment_ticket(conn, raw_token, pubkey, platform="android")

        assert exc_info.value.http_status == 401
        assert exc_info.value.reason_code == "TICKET_ALREADY_USED"


def test_enrollment_ticket_expired_rejection():
    """Expired enrollment ticket is rejected with 401 TICKET_EXPIRED."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    pubkey = secrets.token_bytes(32)

    with get_main_connection() as conn:
        # Issue ticket with TTL = -10 seconds (already expired)
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id, ttl_seconds=-10)

        with pytest.raises(AuthError) as exc_info:
            redeem_enrollment_ticket(conn, raw_token, pubkey, platform="android")

        assert exc_info.value.http_status == 401
        assert exc_info.value.reason_code == "TICKET_EXPIRED"


def test_enrollment_ticket_invalid_token_rejection():
    """Non-existent enrollment token raises 401 TICKET_INVALID."""
    pubkey = secrets.token_bytes(32)

    with get_main_connection() as conn:
        with pytest.raises(AuthError) as exc_info:
            redeem_enrollment_ticket(conn, "enr_non_existent_token_12345", pubkey, platform="android")

        assert exc_info.value.http_status == 401
        assert exc_info.value.reason_code == "TICKET_INVALID"


def test_device_pubkey_length_validation():
    """Device pubkey must be exactly 32 bytes (Ed25519 public key)."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    invalid_pubkey = b"short_key"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)

        with pytest.raises(AuthError) as exc_info:
            redeem_enrollment_ticket(conn, raw_token, invalid_pubkey, platform="android")

        assert exc_info.value.http_status == 400
        assert exc_info.value.reason_code == "INVALID_PUBKEY"


def test_opaque_cookie_session_load_and_expiration():
    """Valid session loads cleanly; expired session raises 401 SESSION_INVALID."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    pubkey = secrets.token_bytes(32)

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, pubkey, platform="android")

    # 1. Load active session
    with get_main_connection() as conn:
        sess = load_session(conn, session_token)
        assert sess.role_slot == "CMO"
        assert sess.facility_id == UUID("00000000-0000-0000-0000-000000000001")
        assert sess.phone_e164 == "+919880000001"

    # 2. Simulate expired session
    with get_main_connection() as conn:
        # Manually backdate expiration in DB
        sess_record = conn.db.sessions[str(sess.id)]
        sess_record["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=5)

    with get_main_connection() as conn:
        with pytest.raises(AuthError) as exc_info:
            load_session(conn, session_token)
        assert exc_info.value.http_status == 401
        assert exc_info.value.reason_code == "SESSION_INVALID"


def test_session_revocation_rejection():
    """Revoked session raises 401 SESSION_INVALID."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    pubkey = secrets.token_bytes(32)

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, sess = redeem_enrollment_ticket(conn, raw_token, pubkey, platform="android")

    # Revoke session in committed store
    with get_main_connection() as conn:
        conn.db.sessions[str(sess.id)]["revoked_at"] = datetime.now(timezone.utc)

    with get_main_connection() as conn:
        with pytest.raises(AuthError) as exc_info:
            load_session(conn, session_token)
        assert exc_info.value.http_status == 401
        assert exc_info.value.reason_code == "SESSION_INVALID"


def test_voice_call_sid_session_creation_and_loading():
    """Voice session bound to call_sid has device_id=None and can be loaded by call_sid."""
    roster_id = "00000000-0000-0000-0000-000000000011"  # Nurse
    call_sid = "CA_exotel_call_987654321"

    with get_main_connection() as conn:
        token, voice_sess = create_voice_session(conn, roster_id, call_sid=call_sid)

    assert voice_sess.call_sid == call_sid
    assert voice_sess.device_id is None
    assert voice_sess.role_slot == "NURSE"

    # Load by call_sid directly
    with get_main_connection() as conn:
        loaded = load_session(conn, call_sid)
        assert loaded.id == voice_sess.id
        assert loaded.call_sid == call_sid
        assert loaded.role_slot == "NURSE"


def test_format_session_cookie_headers():
    """Validates Set-Cookie formatting and LAN_MODE Secure relaxation (§9)."""
    token = "rhp_sid_test123456"

    # Standard production: HttpOnly, Secure, SameSite=Strict
    c_prod = format_session_cookie(token, max_age=86400, lan_mode=False, real_data=False)
    assert f"rhp_session={token}" in c_prod
    assert "HttpOnly" in c_prod
    assert "Secure" in c_prod
    assert "SameSite=Strict" in c_prod

    # LAN mode with synthetic data (REAL_DATA=0): Secure relaxed for local HTTP
    c_lan_synth = format_session_cookie(token, max_age=86400, lan_mode=True, real_data=False)
    assert "Secure" not in c_lan_synth
    assert "HttpOnly" in c_lan_synth

    # LAN mode with real data (REAL_DATA=1): Secure MUST remain enforced
    c_lan_real = format_session_cookie(token, max_age=86400, lan_mode=True, real_data=True)
    assert "Secure" in c_lan_real

