"""Tests for 200-Way Concurrency Barrier Suite (Gate T-C1, Invariants I2, I4, I14, Closure F1).

Specification Anchors:
- Architecture §5: apply_command 10-step transactional pipeline
- Architecture §7: Partial unique index one_lease [Invariant I2]
- Architecture §12: Concurrency & Stress Testing
- BUILD_PLAN §4.2: 200-Way Concurrency Barrier Test (race200)

Under a 200-thread simultaneous barrier strike:
- Exactly 1 thread must win the lease (HTTP 200 OK)
- Exactly 199 threads must be rejected (HTTP 409 LEASE_HELD / LATE_ACCEPT_REJECTED)
- Zero deadlocks occur (Invariant I14)
- DB has exactly one ACCEPTED offer
- Hash-chained event log is gap-free (Invariant I4)
- Independent runtime monitor fold reports ZERO violations (Closure F17)
"""

from __future__ import annotations

import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
from uuid import uuid4

import pytest

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.db import get_main_connection
from api.rhp.pipeline import apply_command
from monitor.monitor import fold_events


def test_race200_concurrency_barrier_yields_single_lease_winner():
    """T-C1 / Invariant I2: 200 concurrent threads hitting ACCEPT against PARALLEL2 offers.

    Synchronized via threading.Barrier(200) to fire simultaneously.
    Result: exactly 1 HTTP 200, exactly 199 HTTP 409 rejections, 0 deadlocks, 0 monitor violations.
    """
    roster_origin = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1_fac = "00000000-0000-0000-0000-000000000002"
    target2_fac = "00000000-0000-0000-0000-000000000003"

    # Setup roster slots for receiving hospitals
    roster_t1 = "00000000-0000-0000-0000-000000000020"
    roster_t2 = "00000000-0000-0000-0000-000000000030"

    with get_main_connection() as conn:
        # Seed receiving facility 3 if missing
        if target2_fac not in conn.db.facilities:
            conn.db.facilities[target2_fac] = {
                "id": target2_fac,
                "code": "KA-KAN-DH-01",
                "name": "Kanakapura General Hospital",
                "tier": "DH",
                "lat_e5": 1254600,
                "lon_e5": 7741800,
                "active": True,
            }

        # Seed duty roles for both receiving facilities
        conn.db.rosters[roster_t1] = {
            "id": roster_t1,
            "facility_id": target1_fac,
            "role_slot": "CMO",
            "slot_no": 1,
            "phone_e164": "+919880000020",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }
        conn.db.rosters[roster_t2] = {
            "id": roster_t2,
            "facility_id": target2_fac,
            "role_slot": "CMO",
            "slot_no": 1,
            "phone_e164": "+919880000030",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        # Create sessions
        tok_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig, _ = redeem_enrollment_ticket(conn, tok_orig, secrets.token_bytes(32), "android")

        tok_t1, _ = create_enrollment_ticket(conn, roster_t1, roster_t1)
        sess_t1, _ = redeem_enrollment_ticket(conn, tok_t1, secrets.token_bytes(32), "android")

        tok_t2, _ = create_enrollment_ticket(conn, roster_t2, roster_t2)
        sess_t2, _ = redeem_enrollment_ticket(conn, tok_t2, secrets.token_bytes(32), "android")
        conn.commit()

        # Step 1: CREATE referral in PARALLEL2 mode
        st_cr, resp_cr = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "PARALLEL2",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [target1_fac, target2_fac],
                "mgso4_status": "GIVEN",
                "profile_id": "DEMO_FAST",
            },
            session_token=sess_orig,
            idem_key=f"race200-create-{uuid4().hex[:8]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]

        # Retrieve both opened offers
        offers = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id]
        assert len(offers) == 2
        off1 = next(o for o in offers if o["facility_id"] == target1_fac)
        off2 = next(o for o in offers if o["facility_id"] == target2_fac)

        # Pre-confirm required capabilities on both offers (OT, BLOOD, ANAESTHETIST, NICU)
        caps = ["OT", "BLOOD", "ANAESTHETIST", "NICU"]
        future_exp = datetime.now(timezone.utc) + timedelta(hours=2)
        for off in (off1, off2):
            for cap in caps:
                conn.execute(
                    """
                    INSERT INTO offer_resource_confirmation (
                      offer_id, capability, confirmed_by, created_at, expires_at
                    ) VALUES (%s, %s, %s, %s, %s);
                    """,
                    (off["id"], cap, roster_t1, datetime.now(timezone.utc), future_exp),
                )
        conn.commit()

    # Step 2: Prepare 200 concurrent threads
    total_workers = 200
    barrier = threading.Barrier(total_workers)
    results: List[Tuple[int, Dict[str, Any]]] = []
    results_lock = threading.Lock()

    def accept_worker(worker_id: int, target_off_id: str, sess_token: str):
        idem_k = f"race200-acc-{worker_id}-{uuid4().hex[:10]}"
        cmd_payload = {
            "type": "ACCEPT",
            "referral_id": ref_id,
            "offer_id": target_off_id,
            "candidate_pin": "4321",
        }
        # Synchronize all 200 workers to strike at once
        barrier.wait()

        with get_main_connection() as t_conn:
            st, resp = apply_command(t_conn, cmd_payload, session_token=sess_token, idem_key=idem_k)
            t_conn.commit()
            with results_lock:
                results.append((st, resp))

    threads = []
    for i in range(total_workers):
        # Alternate target offer and session between target1 and target2
        if i % 2 == 0:
            t = threading.Thread(target=accept_worker, args=(i, off1["id"], sess_t1))
        else:
            t = threading.Thread(target=accept_worker, args=(i, off2["id"], sess_t2))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=30)

    # Step 3: Assert Concurrency Invariants
    assert len(results) == total_workers, f"Expected {total_workers} results, got {len(results)}"
    print("RESULTS SAMPLE:", results[:5])

    successes = [r for r in results if r[0] == 200]
    rejections = [r for r in results if r[0] == 409]

    assert len(successes) == 1, (
        f"CRITICAL: Invariant I2 violated! Expected exactly 1 lease winner, got {len(successes)}"
    )
    assert len(rejections) == total_workers - 1, (
        f"Expected {total_workers - 1} rejections, got {len(rejections)}"
    )

    for st, resp in rejections:
        assert resp["status"] == "REJECTED"
        assert resp["reason"] in ("LEASE_HELD", "LATE_ACCEPT_REJECTED", "DUPLICATE_IN_FLIGHT"), (
            f"Unexpected rejection reason: {resp}"
        )

    # Step 4: Verify Database State Consistency
    with get_main_connection() as conn:
        ref = conn.db.referrals[ref_id]
        assert ref["hs_state"] == "ACCEPTED"
        assert ref["lease_offer_id"] is not None

        accepted_offers = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id and o["status"] == "ACCEPTED"]
        assert len(accepted_offers) == 1, f"Expected 1 ACCEPTED offer in DB, found {len(accepted_offers)}"

        other_offers = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id and o["status"] != "ACCEPTED"]
        for off in other_offers:
            assert off["status"] == "SUPERSEDED"

        # Verify hash-chain gap-free sequence (Invariant I4)
        ref_events = [e for e in conn.db.events if e.get("referral_id") == ref_id]
        seqs = [e["seq"] for e in ref_events]
        assert seqs == list(range(1, len(ref_events) + 1)), f"Sequence gap in events: {seqs}"

        # Step 5: Feed all events through independent monitor fold (Closure F17)
        ref_events = [e for e in conn.db.events if e.get("referral_id") == ref_id]
        ref_offers = [o for o in conn.db.offers.values() if o.get("referral_id") == ref_id]
        state = fold_events(
            ref_events,
            roster_map=conn.db.rosters,
            referral_row=ref,
            offers_rows=ref_offers,
        )
        assert len(state.violations) == 0, f"Monitor detected violations in race200 events: {state.violations}"
