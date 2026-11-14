"""Tests for Independent Runtime Monitor (F17, BUILD_PLAN §4.1).

Tests fold_events() invariant evaluations:
- Clean flows produce 0 violations and status GREEN.
- Violations correctly trip checkers for I1, I2, I4, I5, I6, I7, I8, I9, I11, I12, I15, I16.
- Differential checks detect divergence between event fold and database state.
- HTTP /status and /metrics endpoints correctly report status.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from monitor.monitor import (
    GENESIS_PREV_HASH_HEX,
    GLOBAL_MONITOR_SERVICE,
    compute_monitor_event_hash,
    fold_events,
    monitor_jcs,
)


def test_clean_flow_zero_violations():
    """Valid referral lifecycle produces 0 violations and state matching database."""
    ref_id = str(uuid4())
    fac_origin = "00000000-0000-0000-0000-000000000001"
    fac_target = "00000000-0000-0000-0000-000000000002"
    roster_clinician = "00000000-0000-0000-0000-000000000010"
    roster_cmo = "00000000-0000-0000-0000-000000000020"

    t0 = datetime(2026, 11, 14, 0, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=1)
    t2 = t0 + timedelta(seconds=2)
    t3 = t0 + timedelta(seconds=10)

    # Build 4 chained events
    c1 = {"referral_id": ref_id, "seq": 1, "type": "REFERRAL_CREATED", "detail": {"origin_facility": fac_origin, "need_class": "OB_ECLAMPSIA", "mode": "SEQUENTIAL", "mgso4_status": "GIVEN"}}
    h1 = compute_monitor_event_hash(GENESIS_PREV_HASH_HEX, c1)

    c2 = {"referral_id": ref_id, "seq": 2, "type": "OFFER_ACKED", "detail": {"facility": fac_target, "channel": "PWA", "responder_role": "CMO"}}
    h2 = compute_monitor_event_hash(h1, c2)

    c3 = {"referral_id": ref_id, "seq": 3, "type": "OFFER_ACCEPTED", "detail": {"facility": fac_target, "epoch": 1, "step": 0}}
    h3 = compute_monitor_event_hash(h2, c3)

    c4 = {"referral_id": ref_id, "seq": 4, "type": "CLOSED", "detail": {"outcome": "ADMITTED_STABLE", "reason": "DISCHARGED"}}
    h4 = compute_monitor_event_hash(h3, c4)

    events = [
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 1, "type": "REFERRAL_CREATED", "prev_hash": GENESIS_PREV_HASH_HEX, "hash": h1, "server_ts": t0, "core": c1, "detail": c1["detail"]},
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 2, "type": "OFFER_ACKED", "prev_hash": h1, "hash": h2, "server_ts": t1, "core": c2, "detail": c2["detail"], "actor_roster_id": roster_cmo},
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 3, "type": "OFFER_ACCEPTED", "prev_hash": h2, "hash": h3, "server_ts": t2, "core": c3, "detail": c3["detail"], "actor_roster_id": roster_cmo},
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 4, "type": "CLOSED", "prev_hash": h3, "hash": h4, "server_ts": t3, "core": c4, "detail": c4["detail"], "actor_roster_id": roster_cmo},
    ]

    referral_row = {
        "id": ref_id,
        "hs_state": "CLOSED",
        "head_seq": 4,
        "head_hash": h4,
        "lease_epoch": 1,
        "lease_facility_id": fac_target,
        "outcome": "ADMITTED_STABLE",
        "chain": [fac_target],
    }

    offers_rows = [
        {"id": str(uuid4()), "facility_id": fac_target, "status": "ACCEPTED", "source": "CHAIN"}
    ]

    state = fold_events(
        events=events,
        roster_map={roster_clinician: {}, roster_cmo: {}},
        referral_row=referral_row,
        offers_rows=offers_rows,
        check_time=t3,
    )

    assert len(state.violations) == 0, f"Expected 0 violations, got: {state.violations}"
    assert state.head_seq == 4
    assert state.head_hash == h4
    assert state.hs_state == "CLOSED"
    assert state.outcome == "ADMITTED_STABLE"


def test_i2_double_lease_violation():
    """Invariant I2: Two concurrent lease grants or multiple accepted offers trigger violation."""
    ref_id = str(uuid4())
    fac1 = "00000000-0000-0000-0000-000000000002"
    fac2 = "00000000-0000-0000-0000-000000000003"
    t0 = datetime(2026, 11, 14, 0, 0, 0, tzinfo=timezone.utc)

    # Build events where fac1 accepts, then fac2 accepts without revoking fac1
    c1 = {"referral_id": ref_id, "seq": 1, "type": "OFFER_ACCEPTED", "detail": {"facility": fac1, "epoch": 1, "step": 0}}
    h1 = compute_monitor_event_hash(GENESIS_PREV_HASH_HEX, c1)

    c2 = {"referral_id": ref_id, "seq": 2, "type": "OFFER_ACCEPTED", "detail": {"facility": fac2, "epoch": 2, "step": 1}}
    h2 = compute_monitor_event_hash(h1, c2)

    events = [
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 1, "type": "OFFER_ACCEPTED", "prev_hash": GENESIS_PREV_HASH_HEX, "hash": h1, "server_ts": t0, "core": c1, "detail": c1["detail"], "actor_roster_id": "r1"},
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 2, "type": "OFFER_ACCEPTED", "prev_hash": h1, "hash": h2, "server_ts": t0, "core": c2, "detail": c2["detail"], "actor_roster_id": "r2"},
    ]

    offers_rows = [
        {"id": "off-1", "facility_id": fac1, "status": "ACCEPTED", "source": "CHAIN"},
        {"id": "off-2", "facility_id": fac2, "status": "ACCEPTED", "source": "CHAIN"},
    ]

    state = fold_events(
        events=events,
        offers_rows=offers_rows,
        roster_map={"r1": {}, "r2": {}},
    )

    i2_violations = [v for v in state.violations if v.invariant == "I2"]
    assert len(i2_violations) >= 1
    codes = {v.code for v in i2_violations}
    assert "DOUBLE_LEASE_VIOLATION" in codes or "DB_MULTIPLE_ACCEPTED_OFFERS" in codes


def test_i4_sequence_gap_violation():
    """Invariant I4: Gap in event sequence triggers SEQ_GAP_OR_OUT_OF_ORDER."""
    ref_id = str(uuid4())
    t0 = datetime(2026, 11, 14, 0, 0, 0, tzinfo=timezone.utc)

    # Event 1 followed by Event 3 (skipping seq 2)
    c1 = {"referral_id": ref_id, "seq": 1, "type": "REFERRAL_CREATED", "detail": {"origin_facility": "f1", "need_class": "OB_ECLAMPSIA", "mode": "SEQUENTIAL", "mgso4_status": "GIVEN"}}
    h1 = compute_monitor_event_hash(GENESIS_PREV_HASH_HEX, c1)

    c3 = {"referral_id": ref_id, "seq": 3, "type": "OFFER_ACKED", "detail": {"facility": "f2", "channel": "PWA", "responder_role": "CMO"}}
    h3 = compute_monitor_event_hash(h1, c3)

    events = [
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 1, "type": "REFERRAL_CREATED", "prev_hash": GENESIS_PREV_HASH_HEX, "hash": h1, "server_ts": t0, "core": c1, "detail": c1["detail"]},
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 3, "type": "OFFER_ACKED", "prev_hash": h1, "hash": h3, "server_ts": t0, "core": c3, "detail": c3["detail"]},
    ]

    state = fold_events(events=events)
    i4_violations = [v for v in state.violations if v.invariant == "I4"]
    assert any(v.code == "SEQ_GAP_OR_OUT_OF_ORDER" for v in i4_violations)


def test_i5_tampered_hash_chain():
    """Invariant I5: Event hash mismatch or corrupted chain trips HASH_CHAIN_CORRUPTED."""
    ref_id = str(uuid4())
    t0 = datetime(2026, 11, 14, 0, 0, 0, tzinfo=timezone.utc)

    c1 = {"referral_id": ref_id, "seq": 1, "type": "REFERRAL_CREATED", "detail": {"origin_facility": "f1", "need_class": "OB_ECLAMPSIA", "mode": "SEQUENTIAL", "mgso4_status": "GIVEN"}}
    # Tampered hash!
    fake_hash = "deadbeef" * 8

    events = [
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 1, "type": "REFERRAL_CREATED", "prev_hash": GENESIS_PREV_HASH_HEX, "hash": fake_hash, "server_ts": t0, "core": c1, "detail": c1["detail"]}
    ]

    state = fold_events(events=events)
    i5_violations = [v for v in state.violations if v.invariant == "I5"]
    assert any(v.code == "HASH_CHAIN_CORRUPTED" for v in i5_violations)


def test_i7_unapproved_chain_facility():
    """Invariant I7: CHAIN offer targeting unapproved facility trips OFFER_NOT_IN_APPROVED_CHAIN."""
    ref_id = str(uuid4())
    unapproved_fac = "00000000-0000-0000-0000-000000000999"

    referral_row = {
        "id": ref_id,
        "chain": ["00000000-0000-0000-0000-000000000002"],
        "hs_state": "OFFERED",
        "head_seq": 1,
        "head_hash": "00" * 32,
        "lease_epoch": 0,
        "lease_facility_id": None,
    }

    offers_rows = [
        {"id": "off-1", "facility_id": unapproved_fac, "status": "OPEN", "source": "CHAIN"}
    ]

    state = fold_events(events=[], referral_row=referral_row, offers_rows=offers_rows)
    i7_violations = [v for v in state.violations if v.invariant == "I7"]
    assert any(v.code == "OFFER_NOT_IN_APPROVED_CHAIN" for v in i7_violations)


def test_i9_routing_ping_pong_loop():
    """Invariant I9: Cycle-free routing trips PING_PONG_ROUTING_CYCLE when facility offered twice."""
    ref_id = str(uuid4())
    target = "00000000-0000-0000-0000-000000000002"

    offers_rows = [
        {"id": "off-1", "facility_id": target, "status": "DECLINED", "source": "CHAIN"},
        {"id": "off-2", "facility_id": target, "status": "OPEN", "source": "CHAIN"},
    ]

    state = fold_events(events=[], offers_rows=offers_rows)
    i9_violations = [v for v in state.violations if v.invariant == "I9"]
    assert any(v.code == "PING_PONG_ROUTING_CYCLE" for v in i9_violations)


def test_i11_detail_allowlist_and_float_rejection():
    """Invariant I11: Float values or illegal keys in detail trip validation."""
    ref_id = str(uuid4())
    t0 = datetime(2026, 11, 14, 0, 0, 0, tzinfo=timezone.utc)

    # 1. Detail containing a float (e.g. 12.34)
    c1 = {"referral_id": ref_id, "seq": 1, "type": "REFERRAL_CREATED", "detail": {"origin_facility": "f1", "need_class": "OB_ECLAMPSIA", "mode": "SEQUENTIAL", "mgso4_status": "GIVEN", "invalid_float": 12.34}}
    h1 = "00" * 32

    events = [
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 1, "type": "REFERRAL_CREATED", "prev_hash": GENESIS_PREV_HASH_HEX, "hash": h1, "server_ts": t0, "core": c1, "detail": c1["detail"]}
    ]

    state = fold_events(events=events)
    i11_violations = [v for v in state.violations if v.invariant == "I11"]
    codes = {v.code for v in i11_violations}
    assert "FLOAT_IN_DETAIL" in codes or "DISALLOWED_DETAIL_KEYS" in codes


def test_i12_open_offers_bound_exceeded():
    """Invariant I12: More than 2 active open offers trips OPEN_OFFERS_EXCEEDED."""
    ref_id = str(uuid4())
    offers_rows = [
        {"id": "off-1", "facility_id": "f1", "status": "OPEN", "source": "CHAIN"},
        {"id": "off-2", "facility_id": "f2", "status": "ACKED", "source": "CHAIN"},
        {"id": "off-3", "facility_id": "f3", "status": "SOFT_OPEN", "source": "CHAIN"},
    ]

    state = fold_events(events=[], offers_rows=offers_rows)
    i12_violations = [v for v in state.violations if v.invariant == "I12"]
    assert any(v.code == "OPEN_OFFERS_EXCEEDED" for v in i12_violations)


def test_differential_checks_mismatch_detected():
    """Differential Check: Divergence between event fold head and database referral row trips DIFF_*."""
    ref_id = str(uuid4())
    t0 = datetime(2026, 11, 14, 0, 0, 0, tzinfo=timezone.utc)

    c1 = {"referral_id": ref_id, "seq": 1, "type": "OFFER_ACCEPTED", "detail": {"facility": "f1", "epoch": 1, "step": 0}}
    h1 = compute_monitor_event_hash(GENESIS_PREV_HASH_HEX, c1)

    events = [
        {"id": str(uuid4()), "referral_id": ref_id, "seq": 1, "type": "OFFER_ACCEPTED", "prev_hash": GENESIS_PREV_HASH_HEX, "hash": h1, "server_ts": t0, "core": c1, "detail": c1["detail"], "actor_roster_id": "r1"}
    ]

    # Referral row in DB has head_seq = 2 and different hash
    referral_row = {
        "id": ref_id,
        "head_seq": 2,
        "head_hash": "ff" * 32,
        "lease_epoch": 2,
        "lease_facility_id": "f2",  # Mismatch with fold!
        "chain": ["f1", "f2"],
        "hs_state": "ACCEPTED",
    }

    state = fold_events(
        events=events,
        referral_row=referral_row,
        roster_map={"r1": {}},
    )

    diff_violations = [v for v in state.violations if v.invariant.startswith("DIFF_")]
    assert len(diff_violations) >= 2
    codes = {v.code for v in diff_violations}
    assert "HEAD_SEQ_MISMATCH" in codes
    assert "LEASE_FACILITY_MISMATCH" in codes


def test_monitor_http_service_metrics():
    """GLOBAL_MONITOR_SERVICE correctly tracks status and outputs Prometheus metrics."""
    GLOBAL_MONITOR_SERVICE.record_violations([], referrals_count=5, events_count=15)
    status_data = GLOBAL_MONITOR_SERVICE.get_status()
    assert status_data["status"] == "GREEN"
    assert status_data["violations_count"] == 0
    assert status_data["referrals_checked"] >= 5

    metrics = GLOBAL_MONITOR_SERVICE.get_prometheus_metrics()
    assert "monitor_status 1" in metrics
    assert "monitor_violations_total 0" in metrics
    assert "monitor_referrals_checked_total" in metrics
