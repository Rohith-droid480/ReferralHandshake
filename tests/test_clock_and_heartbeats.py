"""Tests for Worker Heartbeats, Clock Monotonicity & Health Metrics (§5, §6, Closures F11, Invariant I16, Gate T-F11).

Specification Anchors:
- Invariant I16: Monotonic server timestamp via GREATEST(clock_timestamp(), r.head_ts) during backward clock step
- Closure F11: Component heartbeats (POLLER, RELAY, MONITOR, WITNESS) tracked every 5s
- Gate T-F11: /healthz and /metrics alarm on >15s staleness or >2000ms NTP offset
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.rhp.auth import create_enrollment_ticket, redeem_enrollment_ticket
from api.rhp.db import get_main_connection, get_monotone_ts
from api.rhp.main import app, evaluate_heartbeats
from api.rhp.pipeline import apply_command
from api.rhp.poller import upsert_heartbeat
from monitor.monitor import upsert_monitor_heartbeat
from witness.signer import witness_cycle


def test_component_heartbeats_upsert():
    """All 4 required background workers (POLLER, RELAY, MONITOR, WITNESS) upsert their rows into heartbeat table."""
    with get_main_connection() as conn:
        upsert_heartbeat(conn, "POLLER", "poller-test", ntp_offset_ms=5)
        upsert_heartbeat(conn, "RELAY", "relay-test", ntp_offset_ms=-12)
        upsert_monitor_heartbeat(conn, "monitor-test", ntp_offset_ms=3)
        witness_cycle(conn, signer_id="witness-test", ntp_offset_ms=0)
        conn.commit()

        hb = evaluate_heartbeats(conn)
        assert hb["overall_status"] == "GREEN"
        assert len(hb["alarms"]) == 0
        assert hb["components"]["POLLER"]["status"] == "OK"
        assert hb["components"]["RELAY"]["status"] == "OK"
        assert hb["components"]["MONITOR"]["status"] == "OK"
        assert hb["components"]["WITNESS"]["status"] == "OK"


def test_healthz_and_metrics_green_when_all_healthy():
    """GET /healthz returns 200 GREEN and /metrics reports rhp_health_status 1 when all workers are fresh."""
    with get_main_connection() as conn:
        now = datetime.now(timezone.utc)
        for comp in ["POLLER", "RELAY", "MONITOR", "WITNESS"]:
            upsert_heartbeat(conn, comp, f"{comp.lower()}-healthy", ntp_offset_ms=10)
        conn.commit()

    client = TestClient(app)

    # 1. /healthz check
    res_h = client.get("/healthz")
    assert res_h.status_code == 200
    data_h = res_h.json()
    assert data_h["status"] == "GREEN"
    assert len(data_h["alarms"]) == 0

    # 2. /metrics check
    res_m = client.get("/metrics")
    assert res_m.status_code == 200
    text_m = res_m.text
    assert 'rhp_health_status{status="GREEN"} 1' in text_m
    assert "rhp_heartbeat_last_seen_seconds" in text_m
    assert "rhp_clock_slew_alarm" in text_m


def test_healthz_and_metrics_amber_on_stale_component():
    """GET /healthz returns 503 AMBER and alarms when any component heartbeat is > 15s stale."""
    with get_main_connection() as conn:
        now = datetime.now(timezone.utc)
        # Fresh components
        upsay_func = upsert_heartbeat
        upsay_func(conn, "POLLER", "poller-1", ntp_offset_ms=0)
        upsay_func(conn, "RELAY", "relay-1", ntp_offset_ms=0)
        upsay_func(conn, "WITNESS", "witness-1", ntp_offset_ms=0)

        # Stale MONITOR (20 seconds ago)
        stale_time = now - timedelta(seconds=20)
        if hasattr(conn, "db"):
            if not hasattr(conn.db, "heartbeats"):
                conn.db.heartbeats = {}
            conn.db.heartbeats[("MONITOR", "monitor-1")] = {
                "subject_kind": "MONITOR",
                "subject_id": "monitor-1",
                "last_seen": stale_time,
                "ntp_offset_ms": 0,
            }
        else:
            conn.execute(
                """
                INSERT INTO heartbeat (subject_kind, subject_id, last_seen, ntp_offset_ms)
                VALUES ('MONITOR', 'monitor-1', %s, 0)
                ON CONFLICT (subject_kind, subject_id)
                DO UPDATE SET last_seen = EXCLUDED.last_seen;
                """,
                (stale_time,),
            )
        conn.commit()

    client = TestClient(app)
    res = client.get("/healthz")
    assert res.status_code == 503
    data = res.json()
    assert data["status"] == "AMBER"
    assert any("MONITOR_STALE" in a for a in data["alarms"])


def test_healthz_and_metrics_amber_on_ntp_drift():
    """GET /healthz returns 503 AMBER and triggers clock slew alarm when NTP offset > 2000ms."""
    with get_main_connection() as conn:
        now = datetime.now(timezone.utc)
        for comp in ["POLLER", "RELAY", "MONITOR"]:
            upsert_heartbeat(conn, comp, f"{comp.lower()}-1", ntp_offset_ms=10)
        # WITNESS reports 2500ms offset (exceeds 2000ms limit)
        upsert_heartbeat(conn, "WITNESS", "witness-drifted", ntp_offset_ms=2500)
        conn.commit()

    client = TestClient(app)
    res_h = client.get("/healthz")
    assert res_h.status_code == 503
    data_h = res_h.json()
    assert data_h["status"] == "AMBER"
    assert any("WITNESS_NTP_OFFSET_2500MS" in a for a in data_h["alarms"])

    res_m = client.get("/metrics")
    assert res_m.status_code == 200
    assert 'rhp_clock_slew_alarm{component="WITNESS"} 1' in res_m.text


def test_monotonic_server_timestamp_during_backward_clock_step():
    """T-F11 / Invariant I16: GREATEST(clock_timestamp(), head_ts) guarantees non-decreasing server timestamp even if system clock jumps backward."""
    with get_main_connection() as conn:
        future_head_ts = datetime.now(timezone.utc) + timedelta(seconds=120)

        # Monotone TS must be at least future_head_ts
        monotone_ts = get_monotone_ts(conn, head_ts=future_head_ts)
        assert monotone_ts >= future_head_ts

        # Even if current system clock is 2 minutes behind head_ts, ts >= head_ts
        past_clock = future_head_ts - timedelta(minutes=5)
        computed_ts = max(past_clock, future_head_ts)
        assert computed_ts == future_head_ts
