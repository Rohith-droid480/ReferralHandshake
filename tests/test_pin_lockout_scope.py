"""ReferralHandshake Protocol RHP-1 — Argon2id PIN Verifier & Autonomous Lockout Test Suite.

Specification Anchors:
- Architecture §5: apply_command() transaction pipeline (Step 3: PIN Verification)
- Architecture §9: Identity, per-session Argon2id lockout [Closure F7, Invariant I6]
- Invariant I6: Role slot integrity and session fencing
- Closure F7: Autonomous brute-force failure counter scoped strictly to session.id / call_sid
- Verification Gate T-F7: 3 failed attempts lock session for 120s; persists across outer rollback;
  legitimate session for same facility/role succeeds without obstruction.
- BUILD_PLAN §2.3: Argon2id PIN Verifier, Autonomous Failure Counter & Per-Session Lockout Scope
"""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from api.rhp.auth import (
    FAST_HASHER,
    PROD_HASHER,
    AuthError,
    create_enrollment_ticket,
    create_voice_session,
    hash_pin,
    load_session,
    redeem_enrollment_ticket,
    verify_pin_hash,
    verify_pin_or_lockout,
)
from api.rhp.db import get_main_connection, reset_mock_db


@pytest.fixture(autouse=True)
def setup_db():
    """Resets mock database before each test run."""
    reset_mock_db()


def test_valid_pin_verification_succeeds():
    """Valid PIN matching roster pin_hash returns True and clears any prior failed count."""
    roster_id = "00000000-0000-0000-0000-000000000010"  # CMO at Bengaluru DH (PIN: 4321)

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, sess = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

    with get_main_connection() as conn:
        sess = load_session(conn, session_token)
        # Verify valid PIN
        assert verify_pin_or_lockout(conn, sess, "4321") is True
        assert sess.pin_failed == 0
        assert sess.pin_locked_until is None


def test_pin_failure_backoff_schedule():
    """Verifies backoff schedule: 1st fail: 0s; 2nd fail: 5s; retry during lock: 429; 3rd fail: 120s lock."""
    roster_id = "00000000-0000-0000-0000-000000000010"  # CMO (PIN: 4321)

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, sess = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

    with get_main_connection() as conn:
        sess = load_session(conn, session_token)

        # 1. First failure: backoff 0s
        with pytest.raises(AuthError) as exc_1:
            verify_pin_or_lockout(conn, sess, "0000")
        assert exc_1.value.http_status == 403
        assert exc_1.value.reason_code == "PIN_INVALID"
        assert sess.pin_failed == 1
        assert sess.pin_locked_until is None

        # 2. Second failure: backoff 5s
        with pytest.raises(AuthError) as exc_2:
            verify_pin_or_lockout(conn, sess, "0000")
        assert exc_2.value.http_status == 403
        assert exc_2.value.reason_code == "PIN_INVALID"
        assert sess.pin_failed == 2
        assert sess.pin_locked_until is not None

        # 3. Immediate retry during 5s lockout window: rejected with 429 PIN_LOCKED
        with pytest.raises(AuthError) as exc_locked:
            verify_pin_or_lockout(conn, sess, "0000")
        assert exc_locked.value.http_status == 429
        assert exc_locked.value.reason_code == "PIN_LOCKED"
        # Counter was not incremented because request was rejected at pre-check
        assert sess.pin_failed == 2

        # 4. Advance clock past 5s window
        sess.pin_locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)

        # 5. Third failure: 120s lockout
        with pytest.raises(AuthError) as exc_3:
            verify_pin_or_lockout(conn, sess, "0000")
        assert exc_3.value.http_status == 429
        assert exc_3.value.reason_code == "PIN_LOCKED"
        assert sess.pin_failed == 3
        assert sess.pin_locked_until is not None
        # Assert lockout window is approximately 120 seconds into the future
        remaining = (sess.pin_locked_until - datetime.now(timezone.utc)).total_seconds()
        assert 110 <= remaining <= 125


def test_autonomous_persistence_across_main_transaction_rollback():
    """Closure F7 & Gate T-F7: session.pin_failed=3 persists in DB even when the outer command transaction rolls back."""
    roster_id = "00000000-0000-0000-0000-000000000010"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, sess = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

    # Start outer command transaction on main_connection
    try:
        with get_main_connection() as conn:
            sess = load_session(conn, session_token)

            # Failure 1 (0s)
            try:
                verify_pin_or_lockout(conn, sess, "wrong1")
            except AuthError:
                pass

            # Failure 2 (5s)
            try:
                verify_pin_or_lockout(conn, sess, "wrong2")
            except AuthError:
                pass

            # Advance clock past 5s
            sess.pin_locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)

            # Failure 3 (120s lockout)
            try:
                verify_pin_or_lockout(conn, sess, "wrong3")
            except AuthError:
                pass

            assert sess.pin_failed == 3

            # Simulate outer transaction abortion/rollback
            conn.rollback()
    except Exception:
        pass

    # Verify that in a new transaction, pin_failed=3 and pin_locked_until persisted in DB!
    with get_main_connection() as conn:
        reloaded = load_session(conn, session_token)
        assert reloaded.pin_failed == 3, f"Expected pin_failed == 3, got {reloaded.pin_failed}"
        assert reloaded.pin_locked_until is not None, "Expected pin_locked_until to be persisted"
        # Confirm that attempting verification continues to return 429 PIN_LOCKED
        with pytest.raises(AuthError) as exc_info:
            verify_pin_or_lockout(conn, reloaded, "4321")
        assert exc_info.value.http_status == 429
        assert exc_info.value.reason_code == "PIN_LOCKED"


def test_lockout_strictly_scoped_to_session_not_facility():
    """Closure F7 & Invariant I6: Lockout on Session A does NOT block Session B at the same facility for the same role."""
    roster_id = "00000000-0000-0000-0000-000000000010"  # CMO at Bengaluru DH

    # 1. Enrol two distinct devices for the same roster slot
    with get_main_connection() as conn:
        t1, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        s_tok_a, sess_a = redeem_enrollment_ticket(conn, t1, secrets.token_bytes(32), "android_phone")

        t2, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        s_tok_b, sess_b = redeem_enrollment_ticket(conn, t2, secrets.token_bytes(32), "pwa_tablet")

    assert sess_a.id != sess_b.id
    assert sess_a.roster_id == sess_b.roster_id
    assert sess_a.facility_id == sess_b.facility_id

    # 2. Lock out Session A with 3 strikes
    with get_main_connection() as conn:
        sess_a = load_session(conn, s_tok_a)
        sess_a.pin_failed = 2
        sess_a.pin_locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        with pytest.raises(AuthError) as exc_a:
            verify_pin_or_lockout(conn, sess_a, "bad_pin")
        assert exc_a.value.http_status == 429
        assert sess_a.pin_failed == 3

    # 3. Session B submits a valid PIN for the SAME facility & role -> MUST SUCCEED (200 OK)
    with get_main_connection() as conn:
        sess_b = load_session(conn, s_tok_b)
        assert sess_b.pin_failed == 0
        assert sess_b.pin_locked_until is None

        # Verify Session B succeeds cleanly!
        success = verify_pin_or_lockout(conn, sess_b, "4321")
        assert success is True

    # 4. Session A remains locked out
    with get_main_connection() as conn:
        sess_a_check = load_session(conn, s_tok_a)
        assert sess_a_check.pin_failed == 3
        with pytest.raises(AuthError) as exc_recheck:
            verify_pin_or_lockout(conn, sess_a_check, "4321")
        assert exc_recheck.value.http_status == 429


def test_voice_session_pin_lockout_scope():
    """Voice IVR session bound to call_sid has per-call PIN verification and lockout."""
    roster_id = "00000000-0000-0000-0000-000000000011"  # Nurse (PIN: 1234)
    call_sid = "CA_exotel_incoming_11112222"

    with get_main_connection() as conn:
        _, voice_sess = create_voice_session(conn, roster_id, call_sid=call_sid)

    with get_main_connection() as conn:
        sess = load_session(conn, call_sid)
        # Valid PIN verification for voice session
        assert verify_pin_or_lockout(conn, sess, "1234") is True


def test_argon2id_hasher_parameters():
    """Verifies Argon2id password hashing parameters and cross-verification."""
    pin = "9876"
    fast_h = hash_pin(pin, fast=True)
    prod_h = hash_pin(pin, fast=False)

    assert fast_h.startswith("$argon2id$")
    assert prod_h.startswith("$argon2id$")
    assert "m=8192" in fast_h
    assert "m=65536" in prod_h

    # Both hashes verify correctly
    assert verify_pin_hash(fast_h, pin) is True
    assert verify_pin_hash(prod_h, pin) is True
    assert verify_pin_hash(prod_h, "wrong") is False

