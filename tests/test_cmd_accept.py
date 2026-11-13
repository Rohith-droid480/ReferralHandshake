"""ReferralHandshake Protocol RHP-1 — ACCEPT Command & Lease Arbitration Test Suite.

Specification Anchors:
- Architecture §4.3: Lease Award & Competing Offer Supersession
- Architecture §6: Handover Deadline H & Timing Profiles [F2, F3, I13]
- Architecture §7: Partial Unique Index one_lease [I2]
- Architecture §9: Role-Command Authorization & Cross-Facility Isolation [Invariant I6]
- Invariant I2: Single Lease Grant (at most one offer in status ACCEPTED, Gate T-C3)
- Invariant I8: Fencing Epoch & Version Optimistic Concurrency Control
- Invariant I15: Capability Staleness Guard (Reject 409 STALE_CONFIRMATION_RECONFIRM_REQUIRED, Gate T-I15)
- Closure F12: Live Resource Confirmation Verification on Lease Award (Gate T-F12)
- Closure F13: Superseding Competing Offers & Revoking Superseded Grants
- Verification Gates: T-C3, T-F12, T-I15
- BUILD_PLAN §3.3: ACCEPT Command, Single-Owner Lease Arbitration & I15 Staleness Check
"""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.db import get_main_connection, reset_mock_db
from api.rhp.pipeline import apply_command


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
            conn.db.offer_resource_confirmations = {}


# =============================================================================
# 1. Invariant I15: Capability Staleness Guard (Gate T-I15, Closure F12)
# =============================================================================

def test_accept_rejects_missing_capability_confirmation_i15():
    """Invariant I15 (Gate T-I15): Reject 409 STALE_CONFIRMATION_RECONFIRM_REQUIRED when capability unconfirmed."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"  # Facility 1 Clinician
    roster_f2 = "00000000-0000-0000-0000-000000000020"  # Facility 2 CMO
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        # 1. Create referral with OB_ECLAMPSIA requirements
        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [target1],
            },
            session_token=sess_f1,
            idem_key="accept-stale-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # 2. Receiving Facility 2 submits ACCEPT without confirming required capabilities -> 409
        status_rej, resp_rej = apply_command(
            conn,
            {
                "type": "ACCEPT",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 2,
                "candidate_pin": "4321",
            },
            session_token=sess_f2,
            idem_key="accept-stale-attempt-1",
        )
        assert status_rej == 409
        assert resp_rej["status"] == "REJECTED"
        assert resp_rej["reason"] == "STALE_CONFIRMATION_RECONFIRM_REQUIRED"


def test_accept_rejects_expired_capability_confirmation_i15():
    """Invariant I15 (Gate T-F12): Reject 409 STALE_CONFIRMATION_RECONFIRM_REQUIRED when TTL has expired."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"
    roster_f2 = "00000000-0000-0000-0000-000000000020"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1 = "00000000-0000-0000-0000-000000000002"

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "SEQUENTIAL",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [target1],
            },
            session_token=sess_f1,
            idem_key="accept-expired-create-1",
        )
        ref_id = resp_create["referral_id"]
        off1_id = [k for k, v in conn.db.offers.items() if v["referral_id"] == ref_id][0]

        # Populate confirmations with past expiration timestamp (already expired!)
        past_ts = datetime.now(timezone.utc) - timedelta(minutes=10)
        for cap in ["OT", "BLOOD", "ANAESTHETIST", "NICU"]:
            conn.db.offer_resource_confirmations[f"{off1_id}:{cap}"] = {
                "id": str(uuid4()),
                "offer_id": off1_id,
                "capability": cap,
                "confirmed_by": roster_f2,
                "expires_at": past_ts,  # Expired!
                "created_at": past_ts - timedelta(minutes=5),
            }

        # Attempting ACCEPT raises 409
        status_rej, resp_rej = apply_command(
            conn,
            {
                "type": "ACCEPT",
                "referral_id": ref_id,
                "offer_id": off1_id,
                "expected_version": 2,
                "candidate_pin": "4321",
            },
            session_token=sess_f2,
            idem_key="accept-expired-attempt-1",
        )
        assert status_rej == 409
        assert resp_rej["status"] == "REJECTED"
        assert resp_rej["reason"] == "STALE_CONFIRMATION_RECONFIRM_REQUIRED"


# =============================================================================
# 2. Invariant I2: Single Lease Grant & Offer Supersession (Gate T-C3)
# =============================================================================

def test_accept_grants_single_lease_and_supersedes_competing_offers():
    """Invariant I2 (Gate T-C3): ACCEPT awards exclusive lease, increments lease_epoch, supersedes others."""
    roster_f1 = "00000000-0000-0000-0000-000000000010"  # Origin Facility 1
    roster_f2 = "00000000-0000-0000-0000-000000000020"  # Facility 2 CMO
    roster_f3 = "00000000-0000-0000-0000-000000000030"  # Facility 3 Consultant
    origin_fac = "00000000-0000-0000-0000-000000000001"
    fac1 = "00000000-0000-0000-0000-000000000002"  # Facility 2
    fac2 = "00000000-0000-0000-0000-000000000003"  # Facility 3

    with get_main_connection() as conn:
        token_f1, _ = create_enrollment_ticket(conn, roster_f1, roster_f1)
        sess_f1, _ = redeem_enrollment_ticket(conn, token_f1, secrets.token_bytes(32), "android")

        token_f2, _ = create_enrollment_ticket(conn, roster_f2, roster_f2)
        sess_f2, _ = redeem_enrollment_ticket(conn, token_f2, secrets.token_bytes(32), "pwa")

        token_f3, _ = create_enrollment_ticket(conn, roster_f3, roster_f3)
        sess_f3, _ = redeem_enrollment_ticket(conn, token_f3, secrets.token_bytes(32), "pwa")

        # 1. Create in PARALLEL2 mode with 2 open offers
        _, resp_create = apply_command(
            conn,
            {
                "type": "CREATE",
                "mode": "PARALLEL2",
                "need_class": "OB_ECLAMPSIA",
                "origin_facility_id": origin_fac,
                "chain": [fac1, fac2],
            },
            session_token=sess_f1,
            idem_key="accept-parallel2-create-1",
        )
        ref_id = resp_create["referral_id"]
        offers = [v for v in conn.db.offers.values() if v["referral_id"] == ref_id]
        off1 = next(o for o in offers if o["facility_id"] == fac1)
        off2 = next(o for o in offers if o["facility_id"] == fac2)

        # 2. Confirm required capabilities for offer 1 with future TTL
        future_ts = datetime.now(timezone.utc) + timedelta(minutes=30)
        for cap in ["OT", "BLOOD", "ANAESTHETIST", "NICU"]:
            conn.db.offer_resource_confirmations[f"{off1['id']}:{cap}"] = {
                "id": str(uuid4()),
                "offer_id": off1["id"],
                "capability": cap,
                "confirmed_by": roster_f2,
                "expires_at": future_ts,
                "created_at": datetime.now(timezone.utc),
            }

        # 3. Off 1 (Facility 2) executes ACCEPT
        status_acc, resp_acc = apply_command(
            conn,
            {
                "type": "ACCEPT",
                "referral_id": ref_id,
                "offer_id": off1["id"],
                "expected_version": 2,
                "candidate_pin": "4321",
            },
            session_token=sess_f2,
            idem_key="accept-off1-cmd-1",
        )
        assert status_acc == 200
        assert resp_acc["status"] == "COMMITTED"

        # 4. Assert single-owner lease state (Invariant I2)
        r = conn.db.referrals[ref_id]
        assert r["hs_state"] == "ACCEPTED"
        assert r["lease_offer_id"] == off1["id"]
        assert r["lease_facility_id"] == fac1
        assert r["lease_epoch"] == 1
        assert r["open_offers"] == 0

        # Winning offer is ACCEPTED
        assert conn.db.offers[off1["id"]]["status"] == "ACCEPTED"

        # Competing offer 2 is SUPERSEDED (Closure F13)
        assert conn.db.offers[off2["id"]]["status"] == "SUPERSEDED"

        # Fac 2 (Facility 3) payload grant is REVOKED
        assert conn.db.payload_grants[f"{ref_id}:{fac2}"]["status"] == "REVOKED"

        # Fac 1 (Facility 2) payload grant is ACTIVE
        assert conn.db.payload_grants[f"{ref_id}:{fac1}"]["status"] == "ACTIVE"

        # HANDOVER deadline armed and PENDING
        handover_deadlines = [d for d in conn.db.deadlines.values() if d["referral_id"] == ref_id and d["kind"] == "HANDOVER"]
        assert len(handover_deadlines) == 1
        assert handover_deadlines[0]["status"] == "PENDING"

        # 5. Facility 3 attempts late ACCEPT -> Reject 409 LEASE_HELD
        status_late, resp_late = apply_command(
            conn,
            {
                "type": "ACCEPT",
                "referral_id": ref_id,
                "offer_id": off2["id"],
                "expected_version": 3,
                "candidate_pin": "4321",
            },
            session_token=sess_f3,
            idem_key="accept-off2-late-1",
        )
        assert status_late == 409
        assert resp_late["status"] == "REJECTED"
        assert resp_late["reason"] in ("LEASE_HELD", "LATE_ACCEPT_REJECTED")
