"""Tests for BROKEN_BUILD Isolation & Concurrency Sandbox (Gate T-F20, Closure F20, Invariant I2).

Specification Anchors:
- Architecture §6: Real Data Safety Boundary (REAL_DATA=0 enforced)
- Architecture §12: Broken-Build Concurrency Sandbox & Scratch Isolation [F20]
- Closure F20: Hard abort with code 78 if REAL_DATA=1 or pointing to production DB;
  Isolation to rhp_scratch_broken without one_lease;
  Monitor trips RED within <= 2 s upon double lease.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.config import Settings, check_boot_guards, get_settings
from api.rhp.db import get_main_connection
from api.rhp.pipeline import apply_command
from monitor.monitor import fold_events


# =============================================================================
# 1. Hard Abort Safety Boundary on REAL_DATA=1 (Gate T-F20)
# =============================================================================

def test_f20_broken_build_refuses_boot_on_real_data():
    """Closure F20 (Gate T-F20): Booting with BROKEN_BUILD=1 when REAL_DATA=1 MUST exit with code 78."""
    bad_settings = Settings(
        REAL_DATA=1,
        BROKEN_BUILD=1,
        APP_DSN="postgresql://rhp_scratch_app:rhp_scratch_local_dev_only@pg:5432/rhp_scratch_broken",
    )
    with pytest.raises(SystemExit) as exc_info:
        check_boot_guards(bad_settings)
    assert exc_info.value.code == 78


def test_f20_broken_build_refuses_boot_on_production_database():
    """Closure F20: BROKEN_BUILD=1 MUST refuse boot if APP_DSN does not target rhp_scratch_broken."""
    bad_settings = Settings(
        REAL_DATA=0,
        BROKEN_BUILD=1,
        APP_DSN="postgresql://rhp_app:rhp_app_local_dev_only@pg:5432/rhp_main",
    )
    with pytest.raises(SystemExit) as exc_info:
        check_boot_guards(bad_settings)
    assert exc_info.value.code == 78


def test_f20_demo_profiles_refuse_boot_on_real_data():
    """Closure F2: DEMO_FAST or DEMO_VOICE timing profiles MUST refuse boot if REAL_DATA=1."""
    bad_settings = Settings(
        REAL_DATA=1,
        PROFILE="DEMO_FAST",
        BROKEN_BUILD=0,
    )
    with pytest.raises(SystemExit) as exc_info:
        check_boot_guards(bad_settings)
    assert exc_info.value.code == 78


# =============================================================================
# 2. BROKEN_BUILD=1 Fault Injection & Runtime Monitor Alarm
# =============================================================================

def test_broken_build_1_allows_double_lease_and_trips_monitor_red():
    """Closure F20: When BROKEN_BUILD=1, competing offers both reach ACCEPTED and monitor trips RED."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1_fac = "00000000-0000-0000-0000-000000000002"
    target2_fac = "00000000-0000-0000-0000-000000000003"
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

        tok_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig, _ = redeem_enrollment_ticket(conn, tok_orig, secrets.token_bytes(32), "android")

        tok_t1, _ = create_enrollment_ticket(conn, roster_t1, roster_t1)
        sess_t1, _ = redeem_enrollment_ticket(conn, tok_t1, secrets.token_bytes(32), "android")

        tok_t2, _ = create_enrollment_ticket(conn, roster_t2, roster_t2)
        sess_t2, _ = redeem_enrollment_ticket(conn, tok_t2, secrets.token_bytes(32), "android")
        conn.commit()

        # Create PARALLEL2 referral with 2 open offers
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
            idem_key=f"broken-create-{uuid4().hex[:8]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]

        offers = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id]
        off1 = next(o for o in offers if o["facility_id"] == target1_fac)
        off2 = next(o for o in offers if o["facility_id"] == target2_fac)

        # Pre-confirm capabilities for both offers
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

    # Activate BROKEN_BUILD=1 environment setting
    broken_settings = Settings(
        REAL_DATA=0,
        BROKEN_BUILD=1,
        APP_DSN="postgresql://rhp_scratch_app:rhp_scratch_local_dev_only@pg:5432/rhp_scratch_broken",
    )

    with patch("api.rhp.config.get_settings", return_value=broken_settings), \
         patch("api.rhp.commands.accept.get_settings", return_value=broken_settings), \
         patch("api.rhp.transitions.get_settings", return_value=broken_settings):
        with get_main_connection() as conn:
            # 1. Accept first offer
            st1, resp1 = apply_command(
                conn,
                {"type": "ACCEPT", "referral_id": ref_id, "offer_id": off1["id"], "candidate_pin": "4321"},
                session_token=sess_t1,
                idem_key=f"broken-acc1-{uuid4().hex[:8]}",
            )
            assert st1 == 200
            conn.commit()

            # 2. Accept second offer -> in BROKEN_BUILD=1, lease guard is bypassed and superseding skipped
            st2, resp2 = apply_command(
                conn,
                {"type": "ACCEPT", "referral_id": ref_id, "offer_id": off2["id"], "candidate_pin": "4321"},
                session_token=sess_t2,
                idem_key=f"broken-acc2-{uuid4().hex[:8]}",
            )
            assert st2 == 200
            conn.commit()

            # 3. Assert double lease exists in DB
            db_accepted = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id and o["status"] == "ACCEPTED"]
            assert len(db_accepted) == 2, f"Expected 2 ACCEPTED offers in broken build, got {len(db_accepted)}"

            # 4. Feed into independent runtime monitor fold -> Invariant I2 violation MUST be detected
            ref = conn.db.referrals[ref_id]
            ref_events = [e for e in conn.db.events if e.get("referral_id") == ref_id]
            ref_offers = [o for o in conn.db.offers.values() if o.get("referral_id") == ref_id]
            state = fold_events(
                ref_events,
                roster_map=conn.db.rosters,
                referral_row=ref,
                offers_rows=ref_offers,
            )

            assert len(state.violations) > 0, "Monitor failed to trip RED on double lease!"
            i2_violations = [v for v in state.violations if v.invariant == "I2"]
            assert len(i2_violations) > 0, f"Expected Invariant I2 violation, found: {state.violations}"
            assert i2_violations[0].code in ("DOUBLE_LEASE_VIOLATION", "DB_MULTIPLE_ACCEPTED_OFFERS")


# =============================================================================
# 3. BROKEN_BUILD=0 Restoration & Green Monitor Recovery
# =============================================================================

def test_broken_build_0_enforces_single_lease_and_stays_green():
    """Closure F20: Switching back to BROKEN_BUILD=0 restores Invariant I2 single-lease protection."""
    roster_origin = "00000000-0000-0000-0000-000000000010"
    origin_fac = "00000000-0000-0000-0000-000000000001"
    target1_fac = "00000000-0000-0000-0000-000000000002"
    target2_fac = "00000000-0000-0000-0000-000000000003"
    roster_t1 = "00000000-0000-0000-0000-000000000020"
    roster_t2 = "00000000-0000-0000-0000-000000000030"

    with get_main_connection() as conn:
        tok_orig, _ = create_enrollment_ticket(conn, roster_origin, roster_origin)
        sess_orig, _ = redeem_enrollment_ticket(conn, tok_orig, secrets.token_bytes(32), "android")

        tok_t1, _ = create_enrollment_ticket(conn, roster_t1, roster_t1)
        sess_t1, _ = redeem_enrollment_ticket(conn, tok_t1, secrets.token_bytes(32), "android")

        tok_t2, _ = create_enrollment_ticket(conn, roster_t2, roster_t2)
        sess_t2, _ = redeem_enrollment_ticket(conn, tok_t2, secrets.token_bytes(32), "android")
        conn.commit()

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
            idem_key=f"green-create-{uuid4().hex[:8]}",
        )
        assert st_cr == 200
        ref_id = resp_cr["referral_id"]

        offers = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id]
        off1 = next(o for o in offers if o["facility_id"] == target1_fac)
        off2 = next(o for o in offers if o["facility_id"] == target2_fac)

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

        # 1. Accept first offer -> 200 OK
        st1, resp1 = apply_command(
            conn,
            {"type": "ACCEPT", "referral_id": ref_id, "offer_id": off1["id"], "candidate_pin": "4321"},
            session_token=sess_t1,
            idem_key=f"green-acc1-{uuid4().hex[:8]}",
        )
        assert st1 == 200
        conn.commit()

        # 2. Accept second offer -> rejected 409 LEASE_HELD
        st2, resp2 = apply_command(
            conn,
            {"type": "ACCEPT", "referral_id": ref_id, "offer_id": off2["id"], "candidate_pin": "4321"},
            session_token=sess_t2,
            idem_key=f"green-acc2-{uuid4().hex[:8]}",
        )
        assert st2 == 409
        assert resp2["reason"] in ("LEASE_HELD", "LATE_ACCEPT_REJECTED")

        # 3. Assert exactly 1 lease winner in DB
        db_accepted = [o for o in conn.db.offers.values() if o["referral_id"] == ref_id and o["status"] == "ACCEPTED"]
        assert len(db_accepted) == 1

        # 4. Feed events through monitor fold -> 0 violations (GREEN)
        ref = conn.db.referrals[ref_id]
        ref_events = [e for e in conn.db.events if e.get("referral_id") == ref_id]
        ref_offers = [o for o in conn.db.offers.values() if o.get("referral_id") == ref_id]
        state = fold_events(
            ref_events,
            roster_map=conn.db.rosters,
            referral_row=ref,
            offers_rows=ref_offers,
        )
        assert len(state.violations) == 0, f"Expected green monitor, got violations: {state.violations}"
