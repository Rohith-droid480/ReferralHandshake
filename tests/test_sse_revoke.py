"""Tests for Per-Frame Authorized SSE Hub & Dynamic PHI Stripping (§5, §9, Closures F10, Invariant I10).

Specification Anchors:
- Invariant I10 / Closure F10: Per-frame payload grant evaluation
- Gate T-F10: Subscribing as Hospital B, declining offer immediately pushes GRANT_REVOKED control frame
- Gate T-N3: Subsequent frames have zero clinical fields (PHI stripped)
- Last-Event-ID reconnection replay
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.db import get_main_connection
from api.rhp.main import app
from api.rhp.pipeline import apply_command
from api.rhp.sse import (
    SSEHub,
    format_sse_frame,
    get_sse_hub,
    has_active_payload_grant,
    strip_phi,
)


def test_sse_endpoint_unauthorized_without_session():
    """Connecting to /v1/stream without valid rhp_session cookie or Bearer token returns 401."""
    client = TestClient(app)
    response = client.get("/v1/stream")
    assert response.status_code == 401


def test_strip_phi_removes_sensitive_clinical_fields():
    """strip_phi recursively removes confidential fields (Invariant I10)."""
    raw_payload = {
        "referral_id": "00000000-0000-0000-0000-000000000001",
        "step": 1,
        "facility": "00000000-0000-0000-0000-000000000002",
        "patient_name": "Radha Devi",
        "patient_phone": "+919876543210",
        "diagnosis": "Severe Pre-Eclampsia",
        "mgso4_status": "GIVEN",
        "clinical_payload": {"bp_systolic": 180, "bp_diastolic": 115},
        "vitals": {"hr": 92},
        "epoch": 1,
    }

    sanitized = strip_phi(raw_payload)
    assert "patient_name" not in sanitized
    assert "patient_phone" not in sanitized
    assert "diagnosis" not in sanitized
    assert "mgso4_status" not in sanitized
    assert "clinical_payload" not in sanitized
    assert "vitals" not in sanitized
    assert sanitized["referral_id"] == "00000000-0000-0000-0000-000000000001"
    assert sanitized["step"] == 1
    assert sanitized["epoch"] == 1


def test_per_frame_grant_revocation_pushes_grant_revoked_and_strips_phi():
    """T-F10 / T-N3: When Hospital B's grant is revoked, SSE immediately pushes GRANT_REVOKED and strips PHI from subsequent events."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac_b = "00000000-0000-0000-0000-000000000002"
    roster_b = "00000000-0000-0000-0000-000000000020"

    with get_main_connection() as conn:
        tok_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig, _ = redeem_enrollment_ticket(conn, tok_orig, secrets.token_bytes(32), "android")

        tok_b, _ = create_enrollment_ticket(conn, roster_b, roster_b)
        sess_b_token, sess_b = redeem_enrollment_ticket(conn, tok_b, secrets.token_bytes(32), "android")

        # 1. CREATE referral offering to Hospital B -> active payload grant
        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_origin,
                "chain": [fac_b],
            },
            session_token=sess_orig,
            idem_key=f"idem-sse-create-{uuid4().hex[:10]}",
        )
        ref_id = resp_cr["referral_id"]
        cur_off = conn.execute("SELECT id FROM offer WHERE referral_id = %s;", (ref_id,))
        off_b_id = cur_off.fetchone()[0]
        conn.commit()

        # Verify active payload grant exists for Hospital B
        assert has_active_payload_grant(conn, UUID(ref_id), UUID(fac_b)) is True

        # 2. Subscribe as Hospital B
        hub = get_sse_hub()
        sub_b = hub.subscribe(session=sess_b)

        # 3. Simulate event while grant is ACTIVE -> Hospital B receives full frame
        frame_active = hub.filter_and_format_for_subscriber(
            conn,
            sub_b,
            outbox_id=1,
            referral_id=UUID(ref_id),
            event_type="OFFER_CREATED",
            detail={
                "step": 1,
                "facility": fac_b,
                "diagnosis": "Severe Pre-Eclampsia",
                "mgso4_status": "GIVEN",
            },
        )
        assert frame_active is not None
        assert "Severe Pre-Eclampsia" in frame_active
        assert "GIVEN" in frame_active

        # 4. Hospital B declines the offer -> DECLINE revokes payload grant
        st_dec, resp_dec = apply_command(
            conn,
            {
                "type": "DECLINE",
                "referral_id": ref_id,
                "offer_id": off_b_id,
                "reason": "NO_NICU",
                "candidate_pin": "4321",
            },
            session_token=sess_b_token,
            idem_key=f"idem-sse-dec-{uuid4().hex[:10]}",
        )
        assert st_dec == 200
        conn.commit()

        # Verify payload grant is now REVOKED
        assert has_active_payload_grant(conn, UUID(ref_id), UUID(fac_b)) is False

        # 5. Broadcast GRANT_REVOKED frame -> Hospital B receives control frame
        frame_revoked = hub.filter_and_format_for_subscriber(
            conn,
            sub_b,
            outbox_id=2,
            referral_id=UUID(ref_id),
            event_type="GRANT_REVOKED",
            detail={"reason": "DECLINE", "facility": fac_b},
        )
        assert frame_revoked is not None
        assert "event: GRANT_REVOKED" in frame_revoked
        assert '"status": "REVOKED"' in frame_revoked

        # 6. Subsequent event -> Hospital B receives sanitized frame with ZERO PHI fields
        frame_subsequent = hub.filter_and_format_for_subscriber(
            conn,
            sub_b,
            outbox_id=3,
            referral_id=UUID(ref_id),
            event_type="TR_UPDATED",
            detail={
                "tr_state": "DISPATCHED",
                "diagnosis": "Sensitive Patient Data",
                "patient_name": "Secret Name",
            },
        )
        assert frame_subsequent is not None
        assert "Sensitive Patient Data" not in frame_subsequent
        assert "Secret Name" not in frame_subsequent
        assert '"sanitized": true' in frame_subsequent.lower()

        hub.unsubscribe(sub_b)


def test_sse_last_event_id_replay():
    """Last-Event-ID header replays missed events from outbox with id > last_event_id."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    fac_origin = "00000000-0000-0000-0000-000000000001"

    with get_main_connection() as conn:
        tok_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig_token, sess_orig = redeem_enrollment_ticket(conn, tok_orig, secrets.token_bytes(32), "android")

        # Seed outbox events
        ref_id = uuid4()
        now = datetime.now(timezone.utc)
        if hasattr(conn, "db"):
            conn.db.outbox.extend([
                {"id": 10, "referral_id": str(ref_id), "event_seq": 1, "channel": "SSE", "kind": "EVENT_A", "status": "SENT", "detail": {}, "visible_after": now},
                {"id": 11, "referral_id": str(ref_id), "event_seq": 2, "channel": "SSE", "kind": "EVENT_B", "status": "SENT", "detail": {}, "visible_after": now},
                {"id": 12, "referral_id": str(ref_id), "event_seq": 3, "channel": "SSE", "kind": "EVENT_C", "status": "SENT", "detail": {}, "visible_after": now},
            ])

        hub = get_sse_hub()
        sub = hub.subscribe(session=sess_orig, last_event_id=10)

        # Replay events with id > 10
        replayed = hub.replay_missed_events(conn, sub, from_id=10)
        assert replayed >= 2

        # Verify queued frames contain id 11 and 12
        frames = []
        while not sub.queue.empty():
            frames.append(sub.queue.get_nowait())

        assert any("id: 11" in f for f in frames)
        assert any("id: 12" in f for f in frames)
        hub.unsubscribe(sub)
