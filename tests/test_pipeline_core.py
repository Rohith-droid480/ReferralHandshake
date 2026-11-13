"""ReferralHandshake Protocol RHP-1 — 10-Step apply_command() Pipeline Core Test Suite.

Specification Anchors:
- Architecture §5: The 10-step apply_command() transaction pipeline
- Invariant I4: Tamper-evident SHA-256 event hash chain
- Invariant I8: Optimistic fencing on expected_version and expected_epoch (Reject 412)
- Invariant I14: Strict referral-first locking and transaction session GUC stamping (I14_LOCK_NOT_HELD)
- Invariant I16: Monotone server timestamps GREATEST(clock_timestamp(), r.head_ts)
- Closure F1: Total lock order referral -> offer -> deadline -> outbox
- Closure F14: Scoped idempotency with exact replay of prior 200/409/412/422 outcomes
- Verification Gates: T-I8, T-I14, T-I16
- BUILD_PLAN §2.5: The 10-Step apply_command() Transactional Pipeline
"""

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.crypto import GENESIS_PREV_HASH_BYTES, compute_event_hash
from api.rhp.db import get_main_connection, reset_mock_db
from api.rhp.pipeline import apply_command, assert_referral_locked
from api.rhp.transitions import TransitionReject


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


def test_direct_table_writes_without_locked_referral_raise_i14():
    """Invariant I14 (Gate T-I14): Direct table writes without rhp.locked_referral raise I14_LOCK_NOT_HELD."""
    ref_id = uuid4()

    with get_main_connection() as conn:
        # 1. Without rhp.locked_referral stamped, assert_referral_locked raises RuntimeError("I14_LOCK_NOT_HELD")
        with pytest.raises(RuntimeError) as exc_info:
            assert_referral_locked(conn, ref_id)
        assert "I14_LOCK_NOT_HELD" in str(exc_info.value)

        # 2. When stamped with a foreign referral ID, raises I14_LOCK_NOT_HELD
        conn.session_gucs["rhp.locked_referral"] = str(uuid4())
        with pytest.raises(RuntimeError) as exc_mismatch:
            assert_referral_locked(conn, ref_id)
        assert "I14_LOCK_NOT_HELD" in str(exc_mismatch.value)

        # 3. When stamped with target ref_id, passes cleanly
        conn.session_gucs["rhp.locked_referral"] = str(ref_id)
        assert_referral_locked(conn, ref_id)  # Does not raise


def test_stale_expected_version_returns_412_and_logs_rejected_command():
    """Invariant I8 (Gate T-I8): Stale expected_version returns 412 and logs to rejected_command."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    fac_id = "00000000-0000-0000-0000-000000000001"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        # 1. Create a referral (advances version to 2)
        status_create, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_id,
                "expected_version": 0,
                "chain": [fac_id],
            },
            session_token=session_token,
            idem_key="create-version-fencing-1",
        )
        assert status_create == 200
        ref_id = resp_create["referral_id"]
        off_id = [k for k, v in conn.db.offers.items() if v.get("referral_id") == str(ref_id)][0]

        # 2. Submit ACCEPT with stale expected_version = 99
        status_412, resp_412 = apply_command(
            conn,
            {
                "type": "ACCEPT",
                "referral_id": ref_id,
                "offer_id": off_id,
                "expected_version": 99,  # Stale! Current is 2
                "candidate_pin": "4321",
            },
            session_token=session_token,
            idem_key="stale-version-attempt-1",
        )
        assert status_412 == 412
        assert resp_412["status"] == "REJECTED"
        assert resp_412["reason"] == "STALE_PRECONDITION"

        # 3. Verify that an entry was logged to rejected_command table
        assert len(conn.db.rejected_commands) >= 1
        entry = conn.db.rejected_commands[-1]
        assert entry["http_status"] == 412
        assert entry["reason_code"] == "STALE_PRECONDITION"
        assert entry["command"] == "ACCEPT"
        assert entry["key"] == "stale-version-attempt-1"


def test_replaying_same_idempotency_key_returns_exact_stored_412_response():
    """Closure F14: Replaying the same Idempotency-Key returns the exact stored 412 response."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    fac_id = "00000000-0000-0000-0000-000000000001"
    idem_key = "replay-test-key-412"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        # 1. Create referral
        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_id,
                "expected_version": 0,
                "chain": [fac_id],
            },
            session_token=session_token,
            idem_key="create-for-replay-1",
        )
        ref_id = resp_create["referral_id"]
        off_id = [k for k, v in conn.db.offers.items() if v.get("referral_id") == str(ref_id)][0]

        accept_payload = {
            "type": "ACCEPT",
            "referral_id": ref_id,
            "offer_id": off_id,
            "expected_version": 99,  # Stale
            "candidate_pin": "4321",
        }

        # 2. First execution: triggers 412 and stores it
        status_1, resp_1 = apply_command(
            conn, accept_payload, session_token=session_token, idem_key=idem_key
        )
        assert status_1 == 412

        # 3. Second execution (replay with exact same key and payload): returns stored 412 immediately
        status_2, resp_2 = apply_command(
            conn, accept_payload, session_token=session_token, idem_key=idem_key
        )
        assert status_2 == 412
        assert resp_2 == resp_1


def test_reusing_idempotency_key_with_different_payload_returns_422():
    """Closure F14: Reusing an Idempotency-Key with a different payload returns 422 KEY_REUSED_DIFFERENT_PAYLOAD."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    fac_id = "00000000-0000-0000-0000-000000000001"
    idem_key = "reused-key-diff-payload-1"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        # First command with key
        status_1, _ = apply_command(
            conn,
            {
                "type": "CREATE",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_id,
                "expected_version": 0,
            },
            session_token=session_token,
            idem_key=idem_key,
        )
        assert status_1 == 200

        # Second command with SAME key but different payload -> MUST RETURN 422
        with pytest.raises(TransitionReject) as exc_info:
            apply_command(
                conn,
                {
                    "type": "CREATE",
                    "need_class": "OB_PPH",  # Different need class!
                    "origin_facility_id": fac_id,
                    "expected_version": 0,
                },
                session_token=session_token,
                idem_key=idem_key,
            )
        assert exc_info.value.http_status == 422
        assert exc_info.value.reason_code == "KEY_REUSED_DIFFERENT_PAYLOAD"


def test_missing_or_short_idempotency_key_returns_422():
    """Missing or short (< 8 chars) Idempotency-Key raises 422 MISSING_IDEMPOTENCY_KEY."""
    fac_id = "00000000-0000-0000-0000-000000000001"

    with get_main_connection() as conn:
        with pytest.raises(TransitionReject) as exc_missing:
            apply_command(
                conn,
                {
                    "type": "CREATE",
                    "need_class": "OB_ECLAMPSIA",
                    "origin_facility_id": fac_id,
                    "expected_version": 0,
                },
                session_token="token",
                idem_key=None,
            )
        assert exc_missing.value.http_status == 422
        assert exc_missing.value.reason_code == "MISSING_IDEMPOTENCY_KEY"

        with pytest.raises(TransitionReject) as exc_short:
            apply_command(
                conn,
                {
                    "type": "CREATE",
                    "need_class": "OB_ECLAMPSIA",
                    "origin_facility_id": fac_id,
                    "expected_version": 0,
                },
                session_token="token",
                idem_key="short",  # < 8 chars
            )
        assert exc_short.value.http_status == 422
        assert exc_short.value.reason_code == "MISSING_IDEMPOTENCY_KEY"


def test_event_hash_chain_and_outbox_emission():
    """Invariants I4, I5, Closure F1: apply_command commits SHA-256 hash-chained event and outbox row."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    fac_id = "00000000-0000-0000-0000-000000000001"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        status, resp = apply_command(
            conn,
            {
                "type": "CREATE",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_id,
                "expected_version": 0,
                "chain": [fac_id],
            },
            session_token=session_token,
            idem_key="create-hash-chain-1",
        )
        assert status == 200

        # Assert event row was created
        assert len(conn.db.events) >= 1
        ev = conn.db.events[-1]
        assert ev["seq"] == 1
        assert ev["type"] == "REFERRAL_CREATED"
        assert ev["prev_hash"] == GENESIS_PREV_HASH_BYTES
        assert len(ev["hash"]) == 32

        # Assert outbox row was created last
        assert len(conn.db.outbox) >= 1
        ob = conn.db.outbox[-1]
        assert ob["kind"] == "REFERRAL_CREATED"
        assert ob["status"] == "PENDING"
        assert ob["channel"] == "SSE"

