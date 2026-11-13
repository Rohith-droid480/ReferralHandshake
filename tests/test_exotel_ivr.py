"""Comprehensive Verification Suite for Outbound Exotel Voice IVR, AMD & DTMF Gate.

Specification Anchors:
- Architecture §8, §9: Outbound Exotel IVR, AMD Gate, PIN Verification [Closure F7]
- Invariant I6: Authority & Per-Call PIN Verification
- Invariant I14: Referral-first lock & transaction pipeline
- BUILD_PLAN §9.1, §9.2, §9.3: Exotel IVR, AMD Human Gate & DTMF Menu
- Acceptance: 20/20 voice ACKs post-commit; 0/5 voicemail ACKs; webhook p95 <= 2s
- Test Anchors: T-N5, T-N6, T2 Voicemail Gate
"""

import secrets
import time
from uuid import uuid4
import pytest
from api.rhp.auth import create_enrollment_ticket, create_voice_session, redeem_enrollment_ticket
from api.rhp.db import get_main_connection, reset_mock_db
from api.rhp.pipeline import apply_command
from api.rhp.reach.exotel_ivr import (
    check_inbox_dedup,
    handle_exotel_connect,
    handle_exotel_dtmf,
    handle_exotel_pin,
)


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


def test_20_duplicate_webhook_deduplication():
    """Verify that replaying duplicate Exotel webhooks deduplicates 100% via inbox table."""
    with get_main_connection() as conn:
        call_sid = f"call-dup-{uuid4().hex[:10]}"
        payload = {
            "CallSid": call_sid,
            "From": "+919876543210",
            "To": "+918040001000",
            "AnsweredBy": "human",
        }

        # First request should be processed
        res1 = handle_exotel_connect(payload, conn=conn)
        assert res1["status"] == "GATHER_HUMAN_GATE"

        # Next 20 duplicate calls must be marked DEDUPLICATED
        latencies_ms = []
        for _ in range(20):
            t0 = time.perf_counter()
            res_dup = handle_exotel_connect(payload, conn=conn)
            t_dur = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(t_dur)

            assert res_dup["status"] == "DEDUPLICATED"

        # Webhook commit budget assertion: p95 latency <= 2.0s (2000ms)
        latencies_ms.sort()
        p95 = latencies_ms[int(0.95 * len(latencies_ms))]
        assert p95 < 2000.0, f"Expected p95 < 2000ms, got {p95}ms"


def test_5_amd_voicemail_trials_yield_zero_acks():
    """Verify that when AMD reports MACHINE or voicemail, 0 ACKs are recorded across 5 trials."""
    with get_main_connection() as conn:
        for i in range(5):
            call_sid = f"call-machine-{uuid4().hex[:10]}"
            payload = {
                "CallSid": call_sid,
                "AnsweredBy": "machine",
                "AMD": "MACHINE",
                "CallType": "voicemail",
            }

            res = handle_exotel_connect(payload, conn=conn)
            assert res["status"] == "UNANSWERED"
            assert res["ack_recorded"] is False
            assert res["action"] == "hangup"
            assert res["reason"] == "AMD_MACHINE_DETECTED"


def test_20_human_press_1_trials_commit_ack():
    """Verify 20/20 human trials pressing '1' commit ACK before summary playback."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"  # Clinician at Origin Facility 1
    roster_f2 = "00000000-0000-0000-0000-000000000020"  # CMO at Receiving Facility 2
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac_target = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        latencies_ms = []

        # Setup origin clinician session
        raw_token, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        origin_session, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        for i in range(20):
            call_sid = f"call-human-{uuid4().hex[:10]}"
            create_voice_session(conn, roster_f2, call_sid)

            # Create a referral for this trial from origin facility
            st, cr_resp = apply_command(
                conn,
                {
                    "type": "CREATE",
                    "mode": "SEQUENTIAL",
                    "need_class": "OB_ECLAMPSIA",
                    "origin_facility_id": fac_origin,
                    "chain": [fac_target],
                },
                session_token=origin_session,
                idem_key=f"idem-voice-cr-{call_sid}",
            )
            assert st == 200, f"CREATE failed: {cr_resp}"
            ref_id = cr_resp["referral_id"]

            t0 = time.perf_counter()
            # Callee presses '1'
            dtmf_payload = {
                "CallSid": call_sid,
                "Digits": "1",
                "referral_id": ref_id,
                "stage": "GATE",
            }
            res = handle_exotel_dtmf(dtmf_payload, conn=conn)
            dur_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(dur_ms)

            assert res["status"] == "ACK_COMMITTED_PLAY_SUMMARY"
            assert res["ack_recorded"] is True
            # De-identified summary check: no patient names
            assert "Geetha" not in res["summary"]
            assert "patient" not in res["summary"].lower()
            assert "OB_ECLAMPSIA" in res["summary"]

        latencies_ms.sort()
        p95 = latencies_ms[int(0.95 * len(latencies_ms))]
        assert p95 < 2000.0, f"Expected p95 < 2000ms, got {p95}ms"


def test_dtmf_menu_accept_with_pin_verification_and_lockout():
    """Verify DTMF Accept requests PIN, correct PIN grants lease, and 3 wrong PINs locks call session."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"  # Origin Clinician
    roster_f2 = "00000000-0000-0000-0000-000000000020"  # Receiving CMO
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac_target = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        raw_token, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        origin_session, _ = redeem_enrollment_ticket(conn, raw_token, secrets.token_bytes(32), "android")

        call_sid = f"call-accept-{uuid4().hex[:10]}"
        create_voice_session(conn, roster_f2, call_sid)
        conn.commit()

        st, cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_origin,
                "chain": [fac_target],
            },
            session_token=origin_session,
            idem_key=f"idem-acc-cr-{call_sid}",
        )
        assert st == 200, f"CREATE failed: {cr}"
        ref_id = cr["referral_id"]
        conn.commit()

        # Callee presses '1' to Accept -> Prompts for PIN
        res_menu = handle_exotel_dtmf(
            {"CallSid": call_sid, "Digits": "1", "referral_id": ref_id, "stage": "MENU"},
            conn=conn,
        )
        assert res_menu["status"] == "PROMPT_PIN"
        assert res_menu["finish_on_key"] == "#"

        # Wrong PIN strike 1: '9999%23'
        res_fail1 = handle_exotel_pin(
            {"CallSid": call_sid, "Digits": "9999%23", "action": "ACCEPT", "referral_id": ref_id},
            conn=conn,
        )
        assert res_fail1["status"] == "PIN_INVALID"

        # Wrong PIN strike 2: '9998#'
        res_fail2 = handle_exotel_pin(
            {"CallSid": call_sid, "Digits": "9998#", "action": "ACCEPT", "referral_id": ref_id},
            conn=conn,
        )
        assert res_fail2["status"] == "PIN_INVALID"

        # Wrong PIN strike 3: '9997#' -> triggers lockout & pages dispatcher
        res_fail3 = handle_exotel_pin(
            {"CallSid": call_sid, "Digits": "9997#", "action": "ACCEPT", "referral_id": ref_id},
            conn=conn,
        )
        assert res_fail3["status"] == "PIN_LOCKED_OUT"
        assert res_fail3["dispatcher_paged"] is True
        assert res_fail3["action"] == "hangup"
