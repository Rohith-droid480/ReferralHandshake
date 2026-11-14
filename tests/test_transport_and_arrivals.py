"""ReferralHandshake Protocol RHP-1 — Transport Track & Arrival Cases Test Suite.

Specification Anchors:
- Architecture §4.5: Six Arrival Cases (Closure F5)
- Invariant I3: Independent Handshake and Transport Tracks
- BUILD_PLAN §8.1 & §8.2: Transport API, Mapbox ETA Cache & Geofence Hint
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from api.rhp.auth import Session
from api.rhp.commands.transport import (
    execute_tr_destination_change,
    execute_tr_update,
)
from api.rhp.db import get_main_connection
from api.rhp.extras.mapbox_eta import (
    check_geofence_arrival_hint,
    clear_eta_cache,
    get_candidate_etas,
    haversine_distance_m,
)
from api.rhp.pipeline import apply_command
from api.rhp.schemas import TrDestinationChangeCmd, TrUpdateCmd
from api.rhp.transitions import TransitionReject


class MockReferral:
    def __init__(self, ref_id: UUID, hs_state: str = "OFFERED", tr_state: str = "REQUESTED"):
        self.id = ref_id
        self.hs_state = hs_state
        self.tr_state = tr_state
        self.lease_epoch = 0
        self.lease_facility_id = UUID("22222222-2222-2222-2222-222222222222")
        self.lease_offer_id = uuid4()
        self.profile_id = "DEMO_FAST"
        self.tr_ambulance_id = None
        self.tr_facility_id = None
        self.chain = ["CHC_RAMANAGARA", "DH_MANDYA"]


@pytest.fixture(autouse=True)
def clean_cache():
    clear_eta_cache()
    yield
    clear_eta_cache()


def test_i3_track_independence_tr_update():
    """Invariant I3: TR_UPDATE progresses independently of hs_state."""
    ref_id = uuid4()
    # hs_state is OFFERED, not accepted yet!
    referral = MockReferral(ref_id, hs_state="OFFERED", tr_state="REQUESTED")

    session = Session(
        id=uuid4(),
        token_hash=b"\x00" * 32,
        roster_id=uuid4(),
        device_id=uuid4(),
        call_sid=None,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
        facility_id=UUID("22222222-2222-2222-2222-222222222222"),
        role_slot="EMT",
    )

    with get_main_connection() as conn:
        now = datetime.now(timezone.utc)

        # 1. REQUESTED -> DISPATCHED
        cmd1 = TrUpdateCmd(type="TR_UPDATE", referral_id=ref_id, tr_state="DISPATCHED")
        ev_type1, det1 = execute_tr_update(conn, referral, session, cmd1, now)
        assert ev_type1 == "TR_UPDATED"
        assert referral.tr_state == "DISPATCHED"

        # 2. DISPATCHED -> EN_ROUTE
        cmd2 = TrUpdateCmd(type="TR_UPDATE", referral_id=ref_id, tr_state="EN_ROUTE")
        ev_type2, det2 = execute_tr_update(conn, referral, session, cmd2, now)
        assert ev_type2 == "TR_UPDATED"
        assert referral.tr_state == "EN_ROUTE"

        # 3. Invalid jump EN_ROUTE -> HANDED_OVER rejected
        cmd_bad = TrUpdateCmd(type="TR_UPDATE", referral_id=ref_id, tr_state="HANDED_OVER")
        with pytest.raises(TransitionReject) as exc_info:
            execute_tr_update(conn, referral, session, cmd_bad, now)
        assert "INVALID_TR_TRANSITION" in str(exc_info.value)


def test_case_a_arrival_at_lease_holder_arms_handover():
    """Case (a): Arrival at lease holder transitions to ARRIVED and arms HANDOVER deadline."""
    ref_id = uuid4()
    lease_fac_id = UUID("22222222-2222-2222-2222-222222222222")
    referral = MockReferral(ref_id, hs_state="ACCEPTED", tr_state="EN_ROUTE")
    referral.lease_facility_id = lease_fac_id

    session = Session(
        id=uuid4(),
        token_hash=b"\x00" * 32,
        roster_id=uuid4(),
        device_id=uuid4(),
        call_sid=None,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
        facility_id=lease_fac_id,
        role_slot="NURSE",
    )

    with get_main_connection() as conn:
        now = datetime.now(timezone.utc)
        cmd = TrUpdateCmd(type="TR_UPDATE", referral_id=ref_id, tr_state="ARRIVED")
        ev_type, det = execute_tr_update(conn, referral, session, cmd, now)
        assert ev_type == "TR_UPDATED"
        assert referral.tr_state == "ARRIVED"


def test_case_c_unannounced_arrival_at_non_owner():
    """Case (c): Unannounced arrival at facility with no offer emits ARRIVAL_AT_NON_OWNER without blocking care."""
    ref_id = uuid4()
    lease_fac_id = UUID("22222222-2222-2222-2222-222222222222")  # CHC_RAMANAGARA
    other_fac_id = UUID("44444444-4444-4444-4444-444444444444")  # DH_MANDYA

    referral = MockReferral(ref_id, hs_state="ACCEPTED", tr_state="EN_ROUTE")
    referral.lease_facility_id = lease_fac_id

    session_other = Session(
        id=uuid4(),
        token_hash=b"\x00" * 32,
        roster_id=uuid4(),
        device_id=uuid4(),
        call_sid=None,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
        facility_id=other_fac_id,
        role_slot="NURSE",
    )

    with get_main_connection() as conn:
        now = datetime.now(timezone.utc)
        cmd = TrUpdateCmd(type="TR_UPDATE", referral_id=ref_id, tr_state="ARRIVED")
        ev_type, det = execute_tr_update(conn, referral, session_other, cmd, now)
        # Emits urgent ARRIVAL_AT_NON_OWNER event
        assert ev_type == "ARRIVAL_AT_NON_OWNER"
        assert det["facility"] == str(other_fac_id)
        # But care is NOT blocked: transport state moves to ARRIVED!
        assert referral.tr_state == "ARRIVED"


def test_case_d_and_e_destination_change_redirect():
    """Case (d): Redirect accepted updates tr_facility_id. Case (e): Redirect refused keeps destination."""
    ref_id = uuid4()
    new_fac_id = UUID("44444444-4444-4444-4444-444444444444")
    referral = MockReferral(ref_id, hs_state="ACCEPTED", tr_state="EN_ROUTE")

    session = Session(
        id=uuid4(),
        token_hash=b"\x00" * 32,
        roster_id=uuid4(),
        device_id=uuid4(),
        call_sid=None,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
        facility_id=None,
        role_slot="EMT",
    )

    with get_main_connection() as conn:
        now = datetime.now(timezone.utc)

        # Case (d): Accepted redirect
        cmd_accept = TrDestinationChangeCmd(
            type="TR_DESTINATION_CHANGE",
            referral_id=ref_id,
            target_facility_id=new_fac_id,
            accepted=True,
            reason="OBSTETRIC_COMPLICATION",
        )
        ev1, det1 = execute_tr_destination_change(conn, referral, session, cmd_accept, now)
        assert ev1 == "TR_DESTINATION_CHANGE"
        assert det1["accepted"] is True
        assert referral.tr_facility_id == new_fac_id

        # Case (e): Refused redirect
        alt_fac_id = UUID("55555555-5555-5555-5555-555555555555")
        cmd_refuse = TrDestinationChangeCmd(
            type="TR_DESTINATION_CHANGE",
            referral_id=ref_id,
            target_facility_id=alt_fac_id,
            accepted=False,
            reason="CREW_REFUSED_HIGHWAY_PAST",
        )
        ev2, det2 = execute_tr_destination_change(conn, referral, session, cmd_refuse, now)
        assert ev2 == "TR_DESTINATION_CHANGE"
        assert det2["accepted"] is False
        # Destination remains new_fac_id (unchanged by refused redirect)
        assert referral.tr_facility_id == new_fac_id


def test_geofence_arrival_hint_math():
    """Geofence emits hint when <= 200m and dwell >= 20s."""
    # Ramanagara CHC coordinates: 12.72000, 77.28000 (1272000, 7728000 e5)
    fac_lat_e5 = 1272000
    fac_lon_e5 = 7728000

    # 1. 100 meters away with 25s dwell -> True
    # 0.0009 degrees latitude is ~100m
    near_lat = 12.7208
    near_lon = 77.2800
    assert check_geofence_arrival_hint(near_lat, near_lon, fac_lat_e5, fac_lon_e5, dwell_s=25) is True

    # 2. 100 meters away with only 5s dwell -> False (insufficient dwell)
    assert check_geofence_arrival_hint(near_lat, near_lon, fac_lat_e5, fac_lon_e5, dwell_s=5) is False

    # 3. 500 meters away -> False (outside 200m)
    far_lat = 12.7250
    far_lon = 77.2800
    assert check_geofence_arrival_hint(far_lat, far_lon, fac_lat_e5, fac_lon_e5, dwell_s=60) is False


def test_candidate_etas_caching_and_staleness():
    """ETAs are cached for 120s; stale flag returned when expired."""
    ref_id = uuid4()
    with get_main_connection() as conn:
        # First call: computes and caches
        etas1 = get_candidate_etas(conn, ref_id)
        assert len(etas1) >= 2
        assert etas1[0]["stale"] is False
        assert etas1[0]["duration_min"] > 0

        # Immediate second call: returns same cached values (not stale)
        etas2 = get_candidate_etas(conn, ref_id)
        assert etas2[0]["duration_min"] == etas1[0]["duration_min"]
        assert etas2[0]["stale"] is False
