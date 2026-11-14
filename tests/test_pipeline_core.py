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
from datetime import datetime, timedelta, timezone
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


def test_attack_a6_i15_staleness_bypass():
    """Attack A-6 (Invariant I15, Closure F12): Expired capability confirmation rejects ACCEPT with 409 STALE_CONFIRMATION_RECONFIRM_REQUIRED."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    fac_id = "00000000-0000-0000-0000-000000000001"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        # 1. Create referral
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
            idem_key="a6-create-referral-1",
        )
        assert status == 200
        ref_id = resp["referral_id"]

        cur_off = conn.execute("SELECT id FROM offer WHERE referral_id = %s;", (str(ref_id),))
        off_id = cur_off.fetchone()[0]

        # 2. Seed an EXPIRED resource confirmation in offer_resource_confirmation
        now = datetime.now(timezone.utc)
        conn.db.offer_resource_confirmations[f"{off_id}:OT"] = {
            "offer_id": str(off_id),
            "capability": "OT",
            "confirmed_by": str(roster_id),
            "confirmed_at": now - timedelta(hours=2),
            "expires_at": now - timedelta(minutes=5),  # EXPIRED!
        }

        # 3. Destination clinician attempts to ACCEPT
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
            idem_key="a6-accept-expired-conf",
        )

        assert status_accept == 409
        assert resp_accept["status"] == "REJECTED"
        assert resp_accept["reason"] == "STALE_CONFIRMATION_RECONFIRM_REQUIRED"
        assert "confirmation is missing or expired" in resp_accept["message"]


def test_attack_a7_transaction_rollback_and_state_leak():
    """Attack A-7 (Closures F1, F14): Domain rejection cleanly rolls back state changes to savepoint and logs to rejected_command."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    fac_id = "00000000-0000-0000-0000-000000000001"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        # 1. Create referral
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
            idem_key="a7-create-referral-1",
        )
        assert status == 200
        ref_id = resp["referral_id"]
        v_before = resp["version"]

        # Check pre-rejection state via SQL
        cur_pre = conn.execute("SELECT version, hs_state FROM referral WHERE id = %s;", (str(ref_id),))
        row_pre = cur_pre.fetchone()
        assert row_pre[0] == v_before
        assert row_pre[1] == "OFFERED"

        # 2. Submit a domain rejection command (stale version 999)
        cur_off = conn.execute("SELECT id FROM offer WHERE referral_id = %s;", (str(ref_id),))
        off_id = cur_off.fetchone()[0]

        status_rej, resp_rej = apply_command(
            conn,
            {
                "type": "ACCEPT",
                "referral_id": ref_id,
                "offer_id": off_id,
                "expected_version": 999,
                "candidate_pin": "4321",
            },
            session_token=session_token,
            idem_key="a7-rejection-cmd-1",
        )
        assert status_rej == 412
        assert resp_rej["reason"] == "STALE_PRECONDITION"

        # 3. Query DB: State in referral table MUST be completely unchanged (no state leak across rollback)
        cur_post = conn.execute("SELECT version, hs_state FROM referral WHERE id = %s;", (str(ref_id),))
        row_post = cur_post.fetchone()
        assert row_post[0] == row_pre[0]
        assert row_post[1] == row_pre[1]

        # 4. Query rejected_command table: Rejection MUST be audited
        cur_rej = conn.execute("SELECT http_status, reason_code, command FROM rejected_command WHERE key = %s;", ("a7-rejection-cmd-1",))
        rej_row = cur_rej.fetchone()
        assert rej_row is not None
        assert rej_row[0] == 412
        assert rej_row[1] == "STALE_PRECONDITION"
        assert rej_row[2] == "ACCEPT"


def test_attack_a8_concurrency_race_child_locks():
    """Attack A-8 (Closure F1, Architecture §5 Step 6): apply_command explicitly acquires row locks on offer and deadline tables."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    fac_id = "00000000-0000-0000-0000-000000000001"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        # 1. Create referral
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
            idem_key="a8-create-referral-1",
        )
        assert status == 200
        ref_id = resp["referral_id"]

        cur_off = conn.execute("SELECT id FROM offer WHERE referral_id = %s;", (str(ref_id),))
        off_id = cur_off.fetchone()[0]

        # Reset held locks before ACK command
        if hasattr(conn, "held_table_locks"):
            conn.held_table_locks.clear()

        # 2. Submit ACK command, which executes Step 6 child locks
        status_ack, _ = apply_command(
            conn,
            {
                "type": "ACK",
                "referral_id": ref_id,
                "offer_id": off_id,
                "expected_version": 2,
            },
            session_token=session_token,
            idem_key="a8-ack-locks-cmd-1",
        )
        assert status_ack == 200

        # 3. Query pg_locks: verifies that RowExclusiveLock was acquired on both offer and deadline
        cur_locks = conn.execute("SELECT locktype, relation, mode FROM pg_locks;")
        locks = cur_locks.fetchall()
        locked_relations = {row[1]: row[2] for row in locks}

        assert "offer" in locked_relations
        assert locked_relations["offer"] == "RowExclusiveLock"
        assert "deadline" in locked_relations
        assert locked_relations["deadline"] == "RowExclusiveLock"


def test_attack_a9_incomplete_command_pipeline():
    """Attack A-9: Incomplete Command Pipeline (Defect D-8, Closure F1).

    Inputs a DECLINE or TIMEOUT command; steps run apply_command();
    Pass condition: Query the PostgreSQL database directly and assert the state reflects
    DECLINED or TIMED_OUT status, rather than remaining unchanged.
    """
    roster_id = "00000000-0000-0000-0000-000000000010"
    fac_id = "00000000-0000-0000-0000-000000000001"
    fac2_id = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        session_token, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        # 1. Create a referral with 2 facilities in the chain
        status_create, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_id,
                "expected_version": 0,
                "chain": [fac_id, fac2_id],
            },
            session_token=session_token,
            idem_key="a9-create-referral-1",
        )
        assert status_create == 200
        ref_id = resp_create["referral_id"]

        cur_off1 = conn.execute("SELECT id FROM offer WHERE referral_id = %s;", (str(ref_id),))
        off1_id = cur_off1.fetchone()[0]

        # 2. Execute DECLINE command on offer 1
        status_dec, resp_dec = apply_command(
            conn,
            {
                "type": "DECLINE",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 2,
                "candidate_pin": "4321",
                "reason": "NO_ICU_BEDS",
            },
            session_token=session_token,
            idem_key="a9-decline-cmd-1",
        )
        assert status_dec == 200

        # Query database directly: Assert offer 1 status changed to DECLINED
        cur_check_dec = conn.execute("SELECT status, decline_reason FROM offer WHERE id = %s;", (str(off1_id),))
        dec_row = cur_check_dec.fetchone()
        assert dec_row is not None
        assert dec_row[0] == "DECLINED"
        assert dec_row[1] == "NO_ICU_BEDS"

        # Assert ladder cursor advanced and created offer 2 with status OPEN
        cur_check_off2 = conn.execute("SELECT id, status FROM offer WHERE referral_id = %s AND id != %s;", (str(ref_id), str(off1_id)))
        off2_row = cur_check_off2.fetchone()
        assert off2_row is not None
        off2_id, off2_status = off2_row
        assert off2_status == "OPEN"

        # 3. Query pending deadline for offer 2 and execute TIMEOUT command
        cur_dl = conn.execute("SELECT id, kind FROM deadline WHERE referral_id = %s AND status = 'PENDING';", (str(ref_id),))
        dl_row = cur_dl.fetchone()
        assert dl_row is not None
        dl_id, dl_kind = dl_row

        status_timeout, resp_timeout = apply_command(
            conn,
            {
                "type": "TIMEOUT",
                "referral_id": ref_id,
                "deadline_id": dl_id,
                "kind": dl_kind,
                "channel": "SYSTEM",
                "expected_version": 3,
            },
            session_token=session_token,
            idem_key="a9-timeout-cmd-1",
        )
        assert status_timeout == 200

        # Query database directly: In SEQUENTIAL mode, last facility times out to TIMED_OUT (or SOFT_OPEN if continuing)
        cur_check_time = conn.execute("SELECT status FROM offer WHERE id = %s;", (str(off2_id),))
        time_row = cur_check_time.fetchone()
        assert time_row is not None
        assert time_row[0] in ("TIMED_OUT", "SOFT_OPEN")

        # Query deadline directly: Assert deadline is marked DONE
        cur_dl_done = conn.execute("SELECT status FROM deadline WHERE id = %s;", (str(dl_id),))
        assert cur_dl_done.fetchone()[0] == "DONE"



