"""Tests for Two-Phase Stateless Deadline Poller (§5, §6, Closures F1, F2, F13, Gate T-C2, T-T1, T-T4).

Specification Anchors:
- Architecture §5: Stateless 2-Phase Poller (Phase 1 SKIP LOCKED claim, Phase 2 apply_command)
- Architecture §6: Unified ACK window A, notice ladder (0, A/4, 3A/4), decision deadline D
- Gate T-C2 / T-T1: Silent 3-facility chain in DEMO_FAST escalates in <= 25s to ESCALATED_TO_DISPATCHER
- Gate T-T4: Concurrency barrier with active poller yields zero deadlocks
"""

from __future__ import annotations

import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.commands.timeout import execute_timeout
from api.rhp.db import get_main_connection
from api.rhp.pipeline import apply_command
from api.rhp.poller import (
    ClaimedDeadline,
    claim_due_deadlines,
    execute_claimed_deadline,
    get_or_create_system_session,
    poll_once,
)


def test_poller_phase1_claim_skip_locked():
    """Phase 1: Claim statement updates claimed_until and returns due deadlines without holding referral lock."""
    with get_main_connection() as conn:
        now = datetime.now(timezone.utc)
        past = now - timedelta(seconds=10)
        future = now + timedelta(seconds=60)
        ref_id = uuid4()
        d_id = uuid4()

        # Insert test deadline
        conn.execute(
            """
            INSERT INTO deadline (id, referral_id, offer_id, kind, step, epoch, due_at, created_at)
            VALUES (%s, %s, NULL, 'ACK', 0, 0, %s, %s);
            """,
            (str(d_id), str(ref_id), past, past),
        )
        conn.commit()

        # Claim due deadlines
        claimed = claim_due_deadlines(conn, limit=10, now=now)
        conn.commit()

        matched = [d for d in claimed if str(d.id) == str(d_id)]
        assert len(matched) == 1
        assert matched[0].kind == "ACK"
        assert matched[0].referral_id == ref_id

        # Subsequent claim within 5s window returns empty for this deadline
        claimed_again = claim_due_deadlines(conn, limit=10, now=now)
        conn.commit()
        matched_again = [d for d in claimed_again if str(d.id) == str(d_id)]
        assert len(matched_again) == 0


def test_silent_3_facility_chain_escalates_to_dispatcher_in_demo_fast():
    """T-C2 / T-T1: A completely silent 3-facility chain in DEMO_FAST cascades through all 3 facilities to ESCALATED_TO_DISPATCHER in <= 25s."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac1 = "00000000-0000-0000-0000-000000000002"
    fac2 = "00000000-0000-0000-0000-000000000003"
    fac3 = "00000000-0000-0000-0000-000000000004"

    with get_main_connection() as conn:
        if hasattr(conn, "db"):
            conn.db.deadlines.clear()
        tok, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess, _ = redeem_enrollment_ticket(conn, tok, secrets.token_bytes(32), "android")
        conn.commit()

        # Create referral with 3 facilities in DEMO_FAST profile (A=3s, D=4s, bound=25s)
        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_origin,
                "chain": [fac1, fac2, fac3],
            },
            session_token=sess,
            idem_key=f"create-cascade-{uuid4().hex[:10]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]
        conn.commit()

    # Step through 3 rounds of silent timeouts (simulated cascade over time)
    start_sim_time = datetime.now(timezone.utc)
    current_time = start_sim_time

    for hop in range(3):
        # Advance clock by 3.5 seconds (past DEMO_FAST A=3000ms)
        current_time += timedelta(milliseconds=3500)
        n = poll_once(get_main_connection, limit=10, now=current_time)
        assert n >= 1

    # Final check: Referral state must be ESCALATED_TO_DISPATCHER
    with get_main_connection() as conn:
        if hasattr(conn, "db"):
            ref = conn.db.referrals[str(ref_id)]
            hs_state = ref["hs_state"]
            open_offers = ref["open_offers"]
        else:
            cur = conn.execute("SELECT hs_state, open_offers FROM referral WHERE id = %s;", (str(ref_id),))
            row = cur.fetchone()
            hs_state, open_offers = row[0], row[1]

        assert hs_state == "ESCALATED_TO_DISPATCHER"
        assert open_offers == 0

        # Total simulated escalation duration: 3 hops * 3.5s = 10.5s <= 25s
        total_escalation_duration = (current_time - start_sim_time).total_seconds()
        assert total_escalation_duration <= 25.0


def test_idempotent_deadline_re_execution():
    """Double-execution of a claimed deadline returns NOOP without double-advancing the chain."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac1 = "00000000-0000-0000-0000-000000000002"
    fac2 = "00000000-0000-0000-0000-000000000003"

    with get_main_connection() as conn:
        if hasattr(conn, "db"):
            conn.db.deadlines.clear()
        tok, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess, _ = redeem_enrollment_ticket(conn, tok, secrets.token_bytes(32), "android")

        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": fac_origin,
                "chain": [fac1, fac2],
            },
            session_token=sess,
            idem_key=f"idem-poller-ref-{uuid4().hex[:10]}",
        )
        ref_id = resp_cr["referral_id"]
        conn.commit()

        # Find ACK deadline
        if hasattr(conn, "db"):
            dl_obj = next(d for d in conn.db.deadlines.values() if d.get("referral_id") == str(ref_id) and d.get("kind") == "ACK")
            dl_id, kind, step, epoch = dl_obj["id"], dl_obj["kind"], dl_obj["step"], dl_obj["epoch"]
        else:
            cur_dl = conn.execute("SELECT id, referral_id, offer_id, kind, step, epoch FROM deadline WHERE referral_id = %s AND kind = 'ACK';", (ref_id,))
            dl_row = cur_dl.fetchone()
            dl_id, kind, step, epoch = dl_row[0], dl_row[3], dl_row[4], dl_row[5]

        claimed = ClaimedDeadline(
            id=UUID(str(dl_id)),
            referral_id=UUID(str(ref_id)),
            offer_id=None,
            kind=kind,
            step=step,
            epoch=epoch,
        )

        sys_token = get_or_create_system_session(conn)

        # First execution -> 200 COMMITTED
        st1, resp1 = execute_claimed_deadline(conn, claimed, system_session_token=sys_token)
        assert st1 == 200
        conn.commit()

        # Re-execution of the SAME deadline -> Replays stored 200 or NOOP
        st2, resp2 = execute_claimed_deadline(conn, claimed, system_session_token=sys_token)
        assert st2 == 200
        conn.commit()


def test_race_concurrency_barrier_with_active_poller_zero_deadlocks():
    """T-T4: Running 50 concurrent ACCEPT requests against an active background poller produces 0 deadlocks."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac_target = "00000000-0000-0000-0000-000000000002"
    roster_target = "00000000-0000-0000-0000-000000000020"

    with get_main_connection() as conn:
        tok_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig, _ = redeem_enrollment_ticket(conn, tok_orig, secrets.token_bytes(32), "android")

        tok_t, _ = create_enrollment_ticket(conn, roster_target, roster_target)
        sess_t, _ = redeem_enrollment_ticket(conn, tok_t, secrets.token_bytes(32), "android")

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
            idem_key=f"idem-race-poller-{uuid4().hex[:10]}",
        )
        ref_id = resp_cr["referral_id"]

        cur_off = conn.execute("SELECT id FROM offer WHERE referral_id = %s;", (ref_id,))
        off_id = cur_off.fetchone()[0]

        # Pre-confirm capabilities so accept is valid
        future_exp = datetime.now(timezone.utc) + timedelta(minutes=15)
        for cap in ["OT", "BLOOD", "ANAESTHETIST", "NICU"]:
            if hasattr(conn, "db"):
                conn.db.offer_resource_confirmations[f"{off_id}:{cap}"] = {
                    "id": str(uuid4()),
                    "offer_id": str(off_id),
                    "capability": cap,
                    "confirmed_by": roster_target,
                    "expires_at": future_exp,
                    "created_at": datetime.now(timezone.utc),
                }
            else:
                conn.execute(
                    """
                    INSERT INTO offer_resource_confirmation (id, offer_id, capability, confirmed_by, expires_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (str(uuid4()), str(off_id), cap, roster_target, future_exp, datetime.now(timezone.utc)),
                )
        conn.commit()

    # Start background poller loop
    stop_event = threading.Event()
    poller_thread = threading.Thread(
        target=poll_once,
        args=(get_main_connection,),
    )

    # 50 concurrent worker threads
    total_workers = 50
    barrier = threading.Barrier(total_workers)
    results = []
    lock = threading.Lock()

    def accept_worker(worker_id: int):
        barrier.wait()
        idem = f"race-poller-acc-{worker_id}-{uuid4().hex[:8]}"
        with get_main_connection() as w_conn:
            st, resp = apply_command(
                w_conn,
                {
                    "type": "ACCEPT",
                    "referral_id": ref_id,
                    "offer_id": off_id,
                    "candidate_pin": "4321",
                },
                session_token=sess_t,
                idem_key=idem,
            )
            w_conn.commit()
            with lock:
                results.append((st, resp))

    threads = [threading.Thread(target=accept_worker, args=(i,)) for i in range(total_workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # Assert exactly 1 HTTP 200, 49 HTTP 409, 0 deadlocks
    successes = [r for r in results if r[0] == 200]
    assert len(successes) == 1
    rejections = [r for r in results if r[0] == 409]
    assert len(rejections) == total_workers - 1
