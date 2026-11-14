"""Tests for Unified Intra-Facility Notice Ladder & Two-Stage Closure Timeout (§5, §6, Closures F2, F6).

Specification Anchors:
- Architecture §6: Notice ladder rungs (0: SSE+Push, A/4: NOTICE_VOICE, 3A/4: NOTICE_PROXY, A: ACK timeout)
- Closure F2: Early ACK cancels pending intra-facility notice rungs
- Closure F6: Two-stage CLOSURE timeout. On 1st expiry, emits CLOSURE_OVERDUE and re-arms step=2;
  on 2nd expiry, auto-closes with outcome='UNKNOWN_COUNTER_REFERRAL' (proxy=true, actor=system).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.commands.timeout import execute_timeout
from api.rhp.db import get_main_connection
from api.rhp.pipeline import apply_command
from api.rhp.poller import (
    ClaimedDeadline,
    execute_claimed_deadline,
    get_or_create_system_session,
    poll_once,
)


def test_early_ack_cancels_notice_voice_and_notice_proxy():
    """Closure F2: Early ACK immediately marks NOTICE_VOICE and NOTICE_PROXY as DONE."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac_target = "00000000-0000-0000-0000-000000000002"
    roster_target = "00000000-0000-0000-0000-000000000020"

    with get_main_connection() as conn:
        tok_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig, _ = redeem_enrollment_ticket(conn, tok_orig, secrets.token_bytes(32), "android")

        tok_t, _ = create_enrollment_ticket(conn, roster_target, roster_target)
        sess_t, _ = redeem_enrollment_ticket(conn, tok_t, secrets.token_bytes(32), "android")

        # 1. CREATE referral
        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_origin,
                "chain": [fac_target],
            },
            session_token=sess_orig,
            idem_key=f"idem-notice-ack-{uuid4().hex[:10]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]

        cur_off = conn.execute("SELECT id FROM offer WHERE referral_id = %s;", (ref_id,))
        off_id = cur_off.fetchone()[0]

        # Verify initial deadlines exist: ACK, NOTICE_VOICE, NOTICE_PROXY
        if hasattr(conn, "db"):
            dl_map = {d["kind"]: d["status"] for d in conn.db.deadlines.values() if d.get("referral_id") == str(ref_id)}
        else:
            cur_dls = conn.execute("SELECT id, referral_id, offer_id, kind, step, epoch, due_at, status FROM deadline WHERE referral_id = %s;", (ref_id,))
            dl_map = {row[3]: row[7] for row in cur_dls.fetchall()}
        assert dl_map.get("ACK") == "PENDING"
        assert dl_map.get("NOTICE_VOICE") == "PENDING"
        assert dl_map.get("NOTICE_PROXY") == "PENDING"

        # 2. Human ACK before notice rungs expire
        st_ack, resp_ack = apply_command(
            conn,
            {
                "type": "ACK",
                "referral_id": ref_id,
                "offer_id": off_id,
            },
            session_token=sess_t,
            idem_key=f"idem-ack-cancel-{uuid4().hex[:10]}",
        )
        assert st_ack == 200
        conn.commit()

        # Verify NOTICE_VOICE and NOTICE_PROXY are now marked DONE
        if hasattr(conn, "db"):
            dl_map_after = {d["kind"]: d["status"] for d in conn.db.deadlines.values() if d.get("referral_id") == str(ref_id)}
        else:
            cur_dls_after = conn.execute("SELECT id, referral_id, offer_id, kind, step, epoch, due_at, status FROM deadline WHERE referral_id = %s;", (ref_id,))
            dl_map_after = {row[3]: row[7] for row in cur_dls_after.fetchall()}
        assert dl_map_after.get("NOTICE_VOICE") == "DONE"
        assert dl_map_after.get("NOTICE_PROXY") == "DONE"
        assert dl_map_after.get("ACK") == "DONE"
        assert dl_map_after.get("DECISION") == "PENDING"


def test_notice_ladder_rungs_voice_and_proxy_emission():
    """Intra-facility notice ladder emits NOTICE_SENT events for NOTICE_VOICE (A/4) and NOTICE_PROXY (3A/4)."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac_target = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        tok_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig, _ = redeem_enrollment_ticket(conn, tok_orig, secrets.token_bytes(32), "android")

        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_origin,
                "chain": [fac_target],
            },
            session_token=sess_orig,
            idem_key=f"idem-ladder-rung-{uuid4().hex[:10]}",
        )
        ref_id = resp_cr["referral_id"]

        if hasattr(conn, "db"):
            v_dl = next(d for d in conn.db.deadlines.values() if d.get("referral_id") == str(ref_id) and d.get("kind") == "NOTICE_VOICE")
            v_id, v_step, v_epoch = v_dl["id"], v_dl["step"], v_dl["epoch"]
            p_dl = next(d for d in conn.db.deadlines.values() if d.get("referral_id") == str(ref_id) and d.get("kind") == "NOTICE_PROXY")
            p_id, p_step, p_epoch = p_dl["id"], p_dl["step"], p_dl["epoch"]
        else:
            cur_voice = conn.execute("SELECT id, step, epoch FROM deadline WHERE referral_id = %s AND kind = 'NOTICE_VOICE';", (ref_id,))
            v_id, v_step, v_epoch = cur_voice.fetchone()
            cur_proxy = conn.execute("SELECT id, step, epoch FROM deadline WHERE referral_id = %s AND kind = 'NOTICE_PROXY';", (ref_id,))
            p_id, p_step, p_epoch = cur_proxy.fetchone()

        sys_token = get_or_create_system_session(conn)

        # 1. Fire NOTICE_VOICE (A/4 rung)
        claimed_v = ClaimedDeadline(
            id=UUID(str(v_id)),
            referral_id=UUID(str(ref_id)),
            offer_id=None,
            kind="NOTICE_VOICE",
            step=v_step,
            epoch=v_epoch,
        )
        st_v, resp_v = execute_claimed_deadline(conn, claimed_v, system_session_token=sys_token)
        assert st_v == 200
        conn.commit()

        # 2. Fire NOTICE_PROXY (3A/4 rung)
        claimed_p = ClaimedDeadline(
            id=UUID(str(p_id)),
            referral_id=UUID(str(ref_id)),
            offer_id=None,
            kind="NOTICE_PROXY",
            step=p_step,
            epoch=p_epoch,
        )
        st_p, resp_p = execute_claimed_deadline(conn, claimed_p, system_session_token=sys_token)
        assert st_p == 200
        conn.commit()

        # Verify NOTICE_SENT events logged
        if hasattr(conn, "db"):
            evs = [e for e in conn.db.events if e.get("referral_id") == str(ref_id) and e.get("type") == "NOTICE_SENT"]
            channels = [e.get("detail", {}).get("channel") for e in evs]
            assert "VOICE" in channels
            assert ("DISPATCHER_PROXY" in channels or "PROXY" in channels)


def test_handover_overdue_rearming_preserves_invariant_i1():
    """Overdue handover deadline emits HANDOVER_OVERDUE and re-arms a new HANDOVER deadline (Invariant I1)."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac_target = "00000000-0000-0000-0000-000000000002"
    roster_target = "00000000-0000-0000-0000-000000000020"

    with get_main_connection() as conn:
        tok_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig, _ = redeem_enrollment_ticket(conn, tok_orig, secrets.token_bytes(32), "android")
        tok_t, _ = create_enrollment_ticket(conn, roster_target, roster_target)
        sess_t, _ = redeem_enrollment_ticket(conn, tok_t, secrets.token_bytes(32), "android")

        # 1. CREATE referral
        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_origin,
                "chain": [fac_target],
            },
            session_token=sess_orig,
            idem_key=f"idem-handover-cr-{uuid4().hex[:10]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]
        cur_off = conn.execute("SELECT id FROM offer WHERE referral_id = %s;", (ref_id,))
        off_id = cur_off.fetchone()[0]

        apply_command(
            conn,
            {"type": "ACK", "referral_id": ref_id, "offer_id": off_id},
            session_token=sess_t,
            idem_key=f"idem-handover-ack-{uuid4().hex[:10]}",
        )
        # Populate resource confirmations
        future_ts = datetime.now(timezone.utc) + timedelta(minutes=30)
        if hasattr(conn, "db"):
            for cap in ["OT", "BLOOD", "ANAESTHETIST", "NICU"]:
                conn.db.offer_resource_confirmations[f"{off_id}:{cap}"] = {
                    "id": str(uuid4()),
                    "offer_id": str(off_id),
                    "capability": cap,
                    "confirmed_by": roster_target,
                    "expires_at": future_ts,
                    "created_at": datetime.now(timezone.utc),
                }
        apply_command(
            conn,
            {
                "type": "ACCEPT",
                "referral_id": ref_id,
                "offer_id": off_id,
                "candidate_pin": "4321",
            },
            session_token=sess_t,
            idem_key=f"idem-handover-acc-{uuid4().hex[:10]}",
        )

        past = datetime.now(timezone.utc) - timedelta(minutes=60)
        if hasattr(conn, "db"):
            existing_h = next((d for d in conn.db.deadlines.values() if d.get("referral_id") == str(ref_id) and d.get("kind") == "HANDOVER" and d.get("status") == "PENDING"), None)
            if existing_h:
                dl_id = UUID(str(existing_h["id"]))
            else:
                dl_id = uuid4()
                conn.db.deadlines[str(dl_id)] = {
                    "id": str(dl_id),
                    "referral_id": str(ref_id),
                    "offer_id": None,
                    "kind": "HANDOVER",
                    "step": 1,
                    "epoch": 1,
                    "due_at": past,
                    "status": "PENDING",
                    "claimed_until": None,
                    "created_at": past,
                }
        else:
            cur_ex = conn.execute("SELECT id FROM deadline WHERE referral_id = %s AND kind = 'HANDOVER' AND status = 'PENDING';", (str(ref_id),))
            ex_row = cur_ex.fetchone() if cur_ex else None
            if ex_row:
                dl_id = UUID(str(ex_row[0]))
            else:
                dl_id = uuid4()
                conn.execute(
                    """
                    INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (str(dl_id), str(ref_id), None, "HANDOVER", 1, 1, past, past),
                )
        conn.commit()

        sys_token = get_or_create_system_session(conn)
        claimed = ClaimedDeadline(
            id=dl_id,
            referral_id=UUID(str(ref_id)),
            offer_id=None,
            kind="HANDOVER",
            step=1,
            epoch=1,
        )

        st, resp = execute_claimed_deadline(conn, claimed, system_session_token=sys_token)
        assert st == 200
        conn.commit()

        # Verify a new PENDING HANDOVER deadline row was inserted
        if hasattr(conn, "db"):
            new_row = next((d for d in conn.db.deadlines.values() if d.get("referral_id") == str(ref_id) and d.get("kind") == "HANDOVER" and d.get("status") == "PENDING"), None)
            assert new_row is not None
            assert new_row["status"] == "PENDING"
            assert int(new_row["step"]) == 2
        else:
            cur_new = conn.execute(
                "SELECT id, status, step FROM deadline WHERE referral_id = %s AND kind = 'HANDOVER' AND status = 'PENDING';",
                (str(ref_id),),
            )
            new_row = cur_new.fetchone()
            assert new_row is not None
            assert new_row[1] == "PENDING"
            assert int(new_row[2]) == 2


def test_two_stage_closure_timeout_auto_closes_with_unknown_counter_referral():
    """Closure F6: Stage 1 CLOSURE expiry emits CLOSURE_OVERDUE and re-arms step=2; Stage 2 expiry auto-closes with UNKNOWN_COUNTER_REFERRAL."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac_target = "00000000-0000-0000-0000-000000000002"
    roster_target = "00000000-0000-0000-0000-000000000020"

    with get_main_connection() as conn:
        tok_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig, _ = redeem_enrollment_ticket(conn, tok_orig, secrets.token_bytes(32), "android")
        tok_t, _ = create_enrollment_ticket(conn, roster_target, roster_target)
        sess_t, _ = redeem_enrollment_ticket(conn, tok_t, secrets.token_bytes(32), "android")

        # 1. CREATE referral
        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_origin,
                "chain": [fac_target],
            },
            session_token=sess_orig,
            idem_key=f"idem-closure-cr-{uuid4().hex[:10]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]
        cur_off = conn.execute("SELECT id FROM offer WHERE referral_id = %s;", (ref_id,))
        off_id = cur_off.fetchone()[0]

        apply_command(
            conn,
            {"type": "ACK", "referral_id": ref_id, "offer_id": off_id},
            session_token=sess_t,
            idem_key=f"idem-closure-ack-{uuid4().hex[:10]}",
        )
        # Populate resource confirmations
        future_ts = datetime.now(timezone.utc) + timedelta(minutes=30)
        if hasattr(conn, "db"):
            for cap in ["OT", "BLOOD", "ANAESTHETIST", "NICU"]:
                conn.db.offer_resource_confirmations[f"{off_id}:{cap}"] = {
                    "id": str(uuid4()),
                    "offer_id": str(off_id),
                    "capability": cap,
                    "confirmed_by": roster_target,
                    "expires_at": future_ts,
                    "created_at": datetime.now(timezone.utc),
                }
        st_acc, resp_acc = apply_command(
            conn,
            {
                "type": "ACCEPT",
                "referral_id": ref_id,
                "offer_id": off_id,
                "candidate_pin": "4321",
            },
            session_token=sess_t,
            idem_key=f"idem-closure-acc-{uuid4().hex[:10]}",
        )
        assert st_acc == 200

        # Update tr_state to HANDED_OVER
        if hasattr(conn, "db"):
            conn.db.referrals[str(ref_id)]["tr_state"] = "HANDED_OVER"
        else:
            conn.execute("UPDATE referral SET tr_state = 'HANDED_OVER' WHERE id = %s;", (str(ref_id),))

        # Stage 1 deadline
        dl1_id = uuid4()
        past = datetime.now(timezone.utc) - timedelta(hours=3)
        if hasattr(conn, "db"):
            conn.db.deadlines[str(dl1_id)] = {
                "id": str(dl1_id),
                "referral_id": str(ref_id),
                "offer_id": None,
                "kind": "CLOSURE",
                "step": 1,
                "epoch": 1,
                "due_at": past,
                "status": "PENDING",
                "claimed_until": None,
                "created_at": past,
            }
        else:
            conn.execute(
                """
                INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
                VALUES (%s, %s, NULL, 'CLOSURE', 1, 1, %s, %s);
                """,
                (str(dl1_id), str(ref_id), past, past),
            )
        conn.commit()

        sys_token = get_or_create_system_session(conn)

        # 1. Fire Stage 1 CLOSURE timeout -> emits CLOSURE_OVERDUE and re-arms step=2
        claimed1 = ClaimedDeadline(
            id=dl1_id,
            referral_id=UUID(str(ref_id)),
            offer_id=None,
            kind="CLOSURE",
            step=1,
            epoch=1,
        )
        st1, resp1 = execute_claimed_deadline(conn, claimed1, system_session_token=sys_token)
        assert st1 == 200
        conn.commit()

        # Referral remains ACCEPTED / unclosed after stage 1
        if hasattr(conn, "db"):
            ref_rec = conn.db.referrals[str(ref_id)]
            assert ref_rec["hs_state"] == "ACCEPTED"
            assert ref_rec.get("outcome") is None
            dl2 = next(d for d in conn.db.deadlines.values() if d.get("referral_id") == str(ref_id) and d.get("kind") == "CLOSURE" and d.get("status") == "PENDING")
            dl2_id, dl2_st, dl2_step = dl2["id"], dl2["status"], dl2["step"]
        else:
            cur_ref = conn.execute("SELECT hs_state, outcome FROM referral WHERE id = %s;", (str(ref_id),))
            row1 = cur_ref.fetchone()
            assert row1[0] == "ACCEPTED"
            assert row1[1] is None
            cur_dl2 = conn.execute(
                "SELECT id, status, step FROM deadline WHERE referral_id = %s AND kind = 'CLOSURE' AND status = 'PENDING';",
                (str(ref_id),),
            )
            dl2_row = cur_dl2.fetchone()
            assert dl2_row is not None
            dl2_id, dl2_st, dl2_step = dl2_row[0], dl2_row[1], dl2_row[2]

        assert dl2_st == "PENDING"
        assert int(dl2_step) == 2

        # 2. Fire Stage 2 CLOSURE timeout -> auto-closes with UNKNOWN_COUNTER_REFERRAL
        claimed2 = ClaimedDeadline(
            id=UUID(str(dl2_id)),
            referral_id=UUID(str(ref_id)),
            offer_id=None,
            kind="CLOSURE",
            step=2,
            epoch=1,
        )
        st2, resp2 = execute_claimed_deadline(conn, claimed2, system_session_token=sys_token)
        assert st2 == 200
        conn.commit()

        # Referral is now CLOSED with UNKNOWN_COUNTER_REFERRAL
        if hasattr(conn, "db"):
            ref_final = conn.db.referrals[str(ref_id)]
            assert ref_final["hs_state"] == "CLOSED"
            assert ref_final.get("outcome") == "UNKNOWN_COUNTER_REFERRAL"
        else:
            cur_ref_final = conn.execute("SELECT hs_state, outcome FROM referral WHERE id = %s;", (str(ref_id),))
            row_final = cur_ref_final.fetchone()
            assert row_final[0] == "CLOSED"
            assert row_final[1] == "UNKNOWN_COUNTER_REFERRAL"
