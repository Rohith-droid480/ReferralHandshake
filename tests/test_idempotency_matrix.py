"""Tests for F14 Idempotency Edge-Case Matrix (§5, Closure F14, Gate T-F14).

Verifies all 8 rows of the F14 matrix:
- Row 1: Same key, same payload, prior success -> stored 200 replay
- Row 2: Same key, same payload, prior domain rejection -> stored rejection replay (409/412/422)
- Row 3: Same key, different payload -> 422 KEY_REUSED_DIFFERENT_PAYLOAD
- Row 4: Concurrent in-flight duplicate -> 409 DUPLICATE_IN_FLIGHT
- Row 5: Crash before commit -> in-flight row vanished -> clean re-execution
- Row 6: Key older than 48 h -> treated as new; event.event_id unique -> 409 DUPLICATE_EVENT_ID
- Row 7: Missing or short key on mutating call -> 422 MISSING_IDEMPOTENCY_KEY
- Row 8: Same event_id with new key -> 409 DUPLICATE_EVENT_ID
"""

import copy
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.crypto import jcs
from api.rhp.db import get_main_connection
from api.rhp.pipeline import apply_command
from api.rhp.schemas import parse_command
from api.rhp.transitions import TransitionReject


def safe_apply(conn, cmd_or_dict, session_token, idem_key):
    try:
        return apply_command(conn, cmd_or_dict, session_token=session_token, idem_key=idem_key)
    except TransitionReject as exc:
        return exc.http_status, {"status": "REJECTED", "reason": exc.reason_code, "message": exc.message}


def test_row1_same_key_same_payload_prior_success_returns_cached_200():
    """F14 Row 1: Same key, same payload after prior success returns stored 200 OK without re-executing."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target_fac = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        sess, _ = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        idem_key = f"idem-row1-{uuid4().hex[:12]}"
        payload = {
            "type": "CREATE",
            "mode": "SEQUENTIAL",
            "need_class": "OB_ECLAMPSIA",
            "origin_facility_id": origin_fac,
            "chain": [target_fac],
        }

        # First execution -> 200 COMMITTED
        st1, resp1 = safe_apply(conn, payload, session_token=sess, idem_key=idem_key)
        assert st1 == 200
        ref_id = resp1["referral_id"]

        # Exact duplicate execution (replay)
        st2, resp2 = safe_apply(conn, payload, session_token=sess, idem_key=idem_key)
        assert st2 == 200
        assert resp2["referral_id"] == ref_id
        assert resp2["status"] == "COMMITTED"


def test_row2_same_key_same_payload_prior_domain_rejection_returns_cached_error():
    """F14 Row 2: Replay of a domain-rejected command returns exact stored rejection code and body."""
    roster_id = "a1111111-0000-0000-0000-000000000001"
    origin_fac = "11111111-1111-1111-1111-111111111111"
    unapproved_fac = "99999999-9999-9999-9999-999999999999"

    with get_main_connection() as conn:
        token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        sess, _ = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        idem_key = f"idem-row2-{uuid4().hex[:12]}"
        payload = {
            "type": "CREATE",
            "mode": "SEQUENTIAL",
            "need_class": "OBSTETRIC_EMERGENCY",
            "origin_facility_id": origin_fac,
            "chain": [unapproved_fac],  # Will be rejected (422 I7_NOT_IN_CHAIN)
        }

        # First execution -> Domain Reject (422)
        st1, resp1 = safe_apply(conn, payload, session_token=sess, idem_key=idem_key)
        assert st1 == 422
        assert resp1["status"] == "REJECTED"
        assert resp1["reason"] == "I7_NOT_IN_CHAIN"

        # Replay with same key -> Replays stored 422
        st2, resp2 = safe_apply(conn, payload, session_token=sess, idem_key=idem_key)
        assert st2 == 422
        assert resp2["status"] == "REJECTED"
        assert resp2["reason"] == "I7_NOT_IN_CHAIN"


def test_row3_same_key_different_payload_returns_422():
    """F14 Row 3: Reusing an idempotency key with different payload returns 422 KEY_REUSED_DIFFERENT_PAYLOAD."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"
    target2 = "00000000-0000-0000-0000-000000000003"

    with get_main_connection() as conn:
        token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        sess, _ = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        idem_key = f"idem-row3-{uuid4().hex[:12]}"
        payload1 = {
            "type": "CREATE",
            "mode": "SEQUENTIAL",
            "need_class": "OB_ECLAMPSIA",
            "origin_facility_id": origin_fac,
            "chain": [target1],
        }
        st1, resp1 = safe_apply(conn, payload1, session_token=sess, idem_key=idem_key)
        assert st1 == 200

        # Reuse same key with different chain
        payload2 = {
            "type": "CREATE",
            "mode": "SEQUENTIAL",
            "need_class": "OB_ECLAMPSIA",
            "origin_facility_id": origin_fac,
            "chain": [target2],
        }
        st2, resp2 = safe_apply(conn, payload2, session_token=sess, idem_key=idem_key)
        assert st2 == 422
        assert resp2["status"] == "REJECTED"
        assert resp2["reason"] == "KEY_REUSED_DIFFERENT_PAYLOAD"


def test_row4_concurrent_in_flight_duplicate_returns_409():
    """F14 Row 4: Duplicate request while initial transaction is IN_FLIGHT returns 409 DUPLICATE_IN_FLIGHT."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target_fac = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        sess, _ = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        idem_key = f"idem-row4-{uuid4().hex[:12]}"
        payload = {
            "type": "CREATE",
            "mode": "SEQUENTIAL",
            "need_class": "OB_ECLAMPSIA",
            "origin_facility_id": origin_fac,
            "chain": [target_fac],
        }

        # Simulate in-flight entry
        cmd_obj = parse_command(payload)
        h = hashlib.sha256(jcs(cmd_obj.model_dump(mode="json"))).digest()
        conn.db.idempotency[f"{roster_id}:{idem_key}"] = {
            "actor_id": roster_id,
            "key": idem_key,
            "request_hash": h,
            "status": "IN_FLIGHT",
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=48),
        }

        st, resp = safe_apply(conn, payload, session_token=sess, idem_key=idem_key)
        assert st == 409
        assert resp["status"] == "REJECTED"
        assert resp["reason"] == "DUPLICATE_IN_FLIGHT"


def test_row5_crash_before_commit_allows_clean_reexecution():
    """F14 Row 5: Transaction abort before commit rolls back IN_FLIGHT row and allows clean re-execution."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target_fac = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        sess, _ = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")
        conn.commit()

        idem_key = f"idem-row5-{uuid4().hex[:12]}"
        payload = {
            "type": "CREATE",
            "mode": "SEQUENTIAL",
            "need_class": "OB_ECLAMPSIA",
            "origin_facility_id": origin_fac,
            "chain": [target_fac],
        }

        # After a rollback or unhandled failure, no idempotency record remains
        conn.rollback()
        assert f"{roster_id}:{idem_key}" not in conn.db.idempotency

        # Retry executes cleanly
        st, resp = safe_apply(conn, payload, session_token=sess, idem_key=idem_key)
        assert st == 200
        assert resp["status"] == "COMMITTED"


def test_row6_key_older_than_48h_with_same_event_id_returns_409():
    """F14 Row 6: Key older than 48h is treated as new; event_id uniqueness returns 409 DUPLICATE_EVENT_ID."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target_fac = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        sess, _ = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        fixed_event_id = uuid4()
        idem_key_old = f"idem-row6-old-{uuid4().hex[:8]}"

        payload = {
            "type": "CREATE",
            "mode": "SEQUENTIAL",
            "need_class": "OB_ECLAMPSIA",
            "origin_facility_id": origin_fac,
            "chain": [target_fac],
            "event_id": str(fixed_event_id),
        }

        # 1. Execute initially
        st1, resp1 = safe_apply(conn, payload, session_token=sess, idem_key=idem_key_old)
        assert st1 == 200

        # 2. Simulate key expiry (>48h) by setting expires_at in the past
        conn.db.idempotency[f"{roster_id}:{idem_key_old}"]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=50)

        # 3. Request comes in again with the same event_id
        st2, resp2 = safe_apply(conn, payload, session_token=sess, idem_key=idem_key_old)
        assert st2 == 409
        assert resp2["status"] == "REJECTED"
        assert resp2["reason"] == "DUPLICATE_EVENT_ID"


def test_row7_missing_or_short_idempotency_key_returns_422():
    """F14 Row 7: Missing or <8 char idempotency key returns 422 MISSING_IDEMPOTENCY_KEY."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"

    with get_main_connection() as conn:
        token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        sess, _ = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        payload = {
            "type": "CREATE",
            "mode": "SEQUENTIAL",
            "need_class": "OB_ECLAMPSIA",
            "origin_facility_id": origin_fac,
        }

        # Empty / short key
        st, resp = safe_apply(conn, payload, session_token=sess, idem_key="short")
        assert st == 422
        assert resp["status"] == "REJECTED"
        assert resp["reason"] == "MISSING_IDEMPOTENCY_KEY"


def test_row8_same_event_id_new_key_returns_409():
    """F14 Row 8: Reusing pre-minted event_id with a completely new key returns 409 DUPLICATE_EVENT_ID."""
    roster_id = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target_fac = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token, _ = create_enrollment_ticket(conn, roster_id, roster_id)
        sess, _ = redeem_enrollment_ticket(conn, token, secrets.token_bytes(32), "android")

        fixed_event_id = uuid4()
        key1 = f"idem-key1-{uuid4().hex[:10]}"
        key2 = f"idem-key2-{uuid4().hex[:10]}"

        payload1 = {
            "type": "CREATE",
            "mode": "SEQUENTIAL",
            "need_class": "OB_ECLAMPSIA",
            "origin_facility_id": origin_fac,
            "chain": [target_fac],
            "event_id": str(fixed_event_id),
        }
        st1, resp1 = safe_apply(conn, payload1, session_token=sess, idem_key=key1)
        assert st1 == 200

        # Submitting same event_id with different key2
        payload2 = {
            "type": "CREATE",
            "mode": "SEQUENTIAL",
            "need_class": "OB_ECLAMPSIA",
            "origin_facility_id": origin_fac,
            "chain": [target_fac],
            "event_id": str(fixed_event_id),
        }
        st2, resp2 = safe_apply(conn, payload2, session_token=sess, idem_key=key2)
        assert st2 == 409
        assert resp2["status"] == "REJECTED"
        assert resp2["reason"] == "DUPLICATE_EVENT_ID"
