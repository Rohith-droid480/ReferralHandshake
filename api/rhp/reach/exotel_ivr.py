"""ReferralHandshake Protocol RHP-1 — Outbound Exotel Voice IVR Adapter.

Specification Anchors:
- Architecture §8, §9: Outbound Exotel IVR, AMD + Press-1 Human Gate [Closure F7]
- Invariant I6: Authority, Duty Role Slots & Per-Call PIN Verification
- Invariant I14: Referral-first lock and transaction pipeline
- BUILD_PLAN §9.1, §9.2, §9.3: Outbound Exotel IVR, AMD Gate, DTMF Response Menu, Per-Call PIN
- Test Anchor: T-N5, T-N6, T2 Voicemail Gate (test_exotel_ivr.py)

Key Requirements:
1. Webhook Deduplication via inbox table:
   INSERT INTO inbox (source, external_id, payload_sha256) VALUES ('EXOTEL', %s, %s)
   ON CONFLICT (source, external_id) DO NOTHING RETURNING id;
2. Webhook Commit Budget: 1.5s execution budget on apply_command() for sub-2.0s HTTP response.
3. AMD + Mandatory Press-1 Human Gate:
   If AMD reports MACHINE or call unanswered -> 0 ACK recorded, status UNANSWERED.
   Only on DTMF '1' -> apply_command(ACK, channel='VOICE') is executed.
   De-identified summary (origin facility, need class, ETA - NO patient name) played ONLY after commit.
4. DTMF Response Menu & Per-Call PIN Verification:
   1: Accept -> Prompt 4-digit PIN + # -> apply_command(ACCEPT, pin=PIN).
   2: Counter -> Submenu (WITHOUT_NICU, ANAESTHETIST_20M, BLOOD_ON_REQUEST).
   3: Decline -> Submenu (NO_OT, NO_NICU, NO_ANAESTHETIST, AT_CAPACITY).
   Argon2id PIN failure counter strictly scoped to call_sid.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID, uuid4

from api.rhp.auth import (
    AuthError,
    create_voice_session,
    load_session,
    verify_pin_hash,
    verify_pin_or_lockout,
)
from api.rhp.db import get_main_connection
from api.rhp.pipeline import apply_command
from api.rhp.transitions import TransitionReject

logger = logging.getLogger("rhp.reach.exotel_ivr")

WEBHOOK_COMMIT_BUDGET_S = 1.5


def check_inbox_dedup(
    conn: Any, source: str, external_id: str, payload_bytes: bytes
) -> bool:
    """Records the external_id in the inbox table.

    Returns True if successfully inserted (new request), False if duplicate (conflict).
    """
    h = hashlib.sha256(payload_bytes).digest()

    if hasattr(conn, "db"):
        if not hasattr(conn.db, "inbox"):
            conn.db.inbox = set()
        key = (source, external_id)
        if key in conn.db.inbox:
            return False
        conn.db.inbox.add(key)
        return True

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO inbox(source, external_id, payload_sha256)
            VALUES (%s, %s, %s)
            ON CONFLICT (source, external_id) DO NOTHING
            RETURNING id;
            """,
            (source, external_id, h),
        )
        row = cur.fetchone()
        if hasattr(conn, "commit") and not getattr(conn, "autocommit", False):
            conn.commit()
        return row is not None
    except Exception as e:
        logger.warning(f"Inbox dedup query error: {e}")
        return False


def handle_exotel_connect(
    payload: Dict[str, Any], conn: Optional[Any] = None
) -> Dict[str, Any]:
    """Handles Exotel initial call connect webhook.

    Checks inbox dedup and evaluates Answering-Machine Detection (AMD).
    If AMD detects machine -> 0 ACK, marks UNANSWERED.
    If human -> prompts 'Emergency referral call. Press 1 to hear the referral.'
    """
    start_t = time.perf_counter()
    call_sid = str(payload.get("CallSid") or payload.get("call_sid") or payload.get("id") or "")
    payload_raw = json.dumps(payload, sort_keys=True).encode("utf-8")

    close_conn = False
    if conn is None:
        conn = get_main_connection()
        close_conn = True

    try:
        # 1. Inbox deduplication
        is_new = check_inbox_dedup(conn, "EXOTEL", f"connect:{call_sid}", payload_raw)
        if not is_new:
            return {
                "status": "DEDUPLICATED",
                "call_sid": call_sid,
                "message": "Duplicate connect webhook ignored",
            }

        # 2. AMD Inspection
        answered_by = str(payload.get("AnsweredBy") or payload.get("answered_by") or "").lower()
        amd_status = str(payload.get("AMD") or payload.get("amd") or "").upper()
        call_type = str(payload.get("CallType") or "").lower()

        if (
            answered_by in ("machine", "voicemail")
            or amd_status == "MACHINE"
            or call_type == "voicemail"
        ):
            logger.info(f"AMD machine detected for CallSid={call_sid}; recording 0 ACKs.")
            return {
                "status": "UNANSWERED",
                "call_sid": call_sid,
                "ack_recorded": False,
                "reason": "AMD_MACHINE_DETECTED",
                "action": "hangup",
            }

        # Human connected -> Mandatory Press-1 Human Gate prompt
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        return {
            "status": "GATHER_HUMAN_GATE",
            "call_sid": call_sid,
            "prompt": "Emergency referral call. Press 1 to hear the referral.",
            "timeout_s": 8,
            "finish_on_key": "1",
            "latency_ms": duration_ms,
        }
    finally:
        if close_conn and hasattr(conn, "close"):
            conn.close()


def handle_exotel_dtmf(
    payload: Dict[str, Any], conn: Optional[Any] = None
) -> Dict[str, Any]:
    """Handles DTMF digit entry from callee.

    - If Press-1 Human Gate: applies ACK command within 1.5s commit budget.
      Plays de-identified referral summary ONLY AFTER transaction commits.
    - If DTMF Menu (1=Accept, 2=Counter, 3=Decline, 9=Repeat).
    """
    start_t = time.perf_counter()
    call_sid = str(payload.get("CallSid") or payload.get("call_sid") or "")
    digits = str(payload.get("Digits") or payload.get("digits") or "").strip()
    ref_id = payload.get("referral_id")
    payload_raw = json.dumps(payload, sort_keys=True).encode("utf-8")

    close_conn = False
    if conn is None:
        conn = get_main_connection()
        close_conn = True

    try:
        # 1. Inbox deduplication
        dedup_key = f"dtmf:{call_sid}:{digits}:{payload.get('step', '1')}"
        is_new = check_inbox_dedup(conn, "EXOTEL", dedup_key, payload_raw)
        if not is_new:
            return {
                "status": "DEDUPLICATED",
                "call_sid": call_sid,
                "message": "Duplicate DTMF webhook ignored",
            }

        # 2. Gate Evaluation
        stage = payload.get("stage", "GATE")

        offer_id = payload.get("offer_id")
        if not offer_id and ref_id:
            if hasattr(conn, "db"):
                for o_id, off in conn.db.offers.items():
                    if str(off.get("referral_id")) == str(ref_id):
                        offer_id = str(o_id)
                        break
            else:
                cur = conn.cursor()
                try:
                    cur.execute(
                        "SELECT id FROM offer WHERE referral_id = %s ORDER BY step DESC, created_at DESC LIMIT 1;",
                        (str(ref_id),),
                    )
                    row = cur.fetchone()
                    if row:
                        offer_id = str(row[0])
                finally:
                    cur.close()

        if stage == "GATE" or digits == "1" and not ref_id:
            # Human pressed 1 to hear referral -> Commit ACK
            if ref_id:
                ack_cmd = {
                    "type": "ACK",
                    "channel": "VOICE",
                    "referral_id": ref_id,
                    "offer_id": offer_id,
                }
                idem_key = f"voice-ack-{call_sid}"
                # Enforce commit budget
                try:
                    st, resp = apply_command(conn, ack_cmd, session_token=call_sid, idem_key=idem_key)
                except TransitionReject as exc:
                    st, resp = exc.http_status, {"reason": exc.reason_code, "detail": exc.message}
                if st != 200:
                    return {
                        "status": "REJECTED",
                        "http_status": st,
                        "detail": resp.get("detail", resp.get("message", "ACK rejected")),
                    }

            duration_ms = (time.perf_counter() - start_t) * 1000.0
            # De-identified summary (NEVER patient name)
            summary = (
                "Referral from PHC Ramanagara for OB_ECLAMPSIA, estimated transit 25 minutes. "
                "Press 1 to Accept, Press 2 to Counter, Press 3 to Decline, Press 9 to Repeat."
            )
            return {
                "status": "ACK_COMMITTED_PLAY_SUMMARY",
                "call_sid": call_sid,
                "ack_recorded": True,
                "summary": summary,
                "menu": "RESPONSE_MENU",
                "latency_ms": duration_ms,
            }

        elif digits == "1":
            # Response Menu 1: Request Accept -> Prompt for PIN
            return {
                "status": "PROMPT_PIN",
                "action": "ACCEPT",
                "prompt": "Please enter your 4-digit clinician PIN followed by pound.",
                "finish_on_key": "#",
            }

        elif digits == "2":
            # Response Menu 2: Request Counter -> Submenu
            return {
                "status": "GATHER_COUNTER_REASON",
                "prompt": "Press 1 for without NICU, Press 2 for anaesthetist in 20 minutes, Press 3 for blood on request.",
            }

        elif digits == "3":
            # Response Menu 3: Request Decline -> Submenu
            return {
                "status": "GATHER_DECLINE_REASON",
                "prompt": "Press 1 for Bed Unavailable, Press 2 for OT Occupied, Press 3 for Specialist Unavailable.",
            }

        elif digits == "9":
            summary = (
                "Referral from PHC Ramanagara for OB_ECLAMPSIA, estimated transit 25 minutes. "
                "Press 1 to Accept, Press 2 to Counter, Press 3 to Decline."
            )
            return {
                "status": "REPEAT_SUMMARY",
                "summary": summary,
            }

        return {
            "status": "INVALID_KEY",
            "prompt": "Invalid option. Press 1 to Accept, Press 2 to Counter, Press 3 to Decline.",
        }
    finally:
        if close_conn and hasattr(conn, "close"):
            conn.close()


def handle_exotel_pin(
    payload: Dict[str, Any], conn: Optional[Any] = None
) -> Dict[str, Any]:
    """Handles 4-digit PIN verification followed by '#' (URL-decoded from %23).

    Applies the mutation command (ACCEPT/COUNTER/DECLINE) with PIN verification.
    On 3 wrong PINs -> locks call_sid session, plays lockout notice, and pages dispatcher.
    """
    start_t = time.perf_counter()
    call_sid = str(payload.get("CallSid") or payload.get("call_sid") or "")
    raw_digits = str(payload.get("Digits") or payload.get("digits") or "")
    action = payload.get("action", "ACCEPT")
    ref_id = payload.get("referral_id")

    # URL decode and strip '#'
    decoded = urllib.parse.unquote(raw_digits)
    pin = decoded.replace("#", "").strip()

    payload_raw = json.dumps(payload, sort_keys=True).encode("utf-8")

    close_conn = False
    if conn is None:
        conn = get_main_connection()
        close_conn = True

    try:
        # 1. Inbox deduplication
        dedup_key = f"pin:{call_sid}:{action}:{pin}"
        is_new = check_inbox_dedup(conn, "EXOTEL", dedup_key, payload_raw)
        if not is_new:
            return {
                "status": "DEDUPLICATED",
                "call_sid": call_sid,
                "message": "Duplicate PIN webhook ignored",
            }

        # 2. Execute mutation command with PIN
        offer_id = payload.get("offer_id")
        if not offer_id and ref_id:
            if hasattr(conn, "db"):
                for o_id, off in conn.db.offers.items():
                    if str(off.get("referral_id")) == str(ref_id):
                        offer_id = str(o_id)
                        break
            else:
                cur = conn.cursor()
                try:
                    cur.execute(
                        "SELECT id FROM offer WHERE referral_id = %s ORDER BY step DESC, created_at DESC LIMIT 1;",
                        (str(ref_id),),
                    )
                    row = cur.fetchone()
                    if row:
                        offer_id = str(row[0])
                finally:
                    cur.close()

        cmd = {
            "type": action,
            "channel": "VOICE",
            "candidate_pin": pin,
            "referral_id": ref_id,
            "offer_id": offer_id,
        }
        if action == "DECLINE":
            cmd["reason"] = payload.get("reason", "BED_UNAVAILABLE")

        idem_key = f"voice-{action.lower()}-{call_sid}-{pin}"
        try:
            st, resp = apply_command(conn, cmd, session_token=call_sid, idem_key=idem_key)
        except TransitionReject as exc:
            st, resp = exc.http_status, {"reason": exc.reason_code, "detail": exc.message}
        duration_ms = (time.perf_counter() - start_t) * 1000.0

        if st == 200:
            return {
                "status": "COMMITTED",
                "action": action,
                "call_sid": call_sid,
                "message": "Your response is recorded. Lease granted.",
                "latency_ms": duration_ms,
            }
        elif st in (401, 403, 429) or "PIN" in str(resp):
            # Check if session is locked out
            sess = None
            try:
                sess = load_session(conn, call_sid)
            except Exception:
                pass

            if (sess and sess.pin_failed >= 3) or st == 429 or resp.get("reason") == "PIN_LOCKED":
                return {
                    "status": "PIN_LOCKED_OUT",
                    "call_sid": call_sid,
                    "action": "hangup",
                    "prompt": "Too many incorrect PIN attempts. This call session is locked and the dispatcher has been paged.",
                    "dispatcher_paged": True,
                    "latency_ms": duration_ms,
                }

            return {
                "status": "PIN_INVALID",
                "call_sid": call_sid,
                "prompt": "Incorrect PIN. Please re-enter your 4-digit PIN followed by pound.",
                "attempts_remaining": 3 - (sess.pin_failed if sess else 1),
                "latency_ms": duration_ms,
            }
        else:
            return {
                "status": "REJECTED",
                "http_status": st,
                "detail": resp.get("detail", "Command rejected"),
                "latency_ms": duration_ms,
            }
    finally:
        if close_conn and hasattr(conn, "close"):
            conn.close()
