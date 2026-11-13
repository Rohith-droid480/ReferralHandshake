"""Comprehensive Verification Suite for District Command Centre Analytics & Privacy Bucketing.

Specification Anchors:
- Architecture §15: APOT-Separated KPIs & Privacy Guardrails [Closure F9]
- BUILD_PLAN §10.3, §10.4: APOT Handover KPIs, networkx Referral Graph & 4h Bucketed k>=5 Suppression
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from api.rhp.extras.analytics import (
    bucket_4h_timestamp,
    bucket_and_suppress,
    build_referral_network_graph,
    compute_log_kpis,
    filter_active_capabilities,
    format_attestation_age,
)


def test_apot_kpis_separated_from_acceptance():
    """Verify APOT arrival-to-handover duration is computed independently from time-to-ACK."""
    base_time = datetime(2026, 11, 14, 10, 0, 0, tzinfo=timezone.utc)
    ref_id = str(uuid4())

    events = [
        # Referral created at T+0s
        {
            "referral_id": ref_id,
            "seq": 1,
            "type": "REFERRAL_CREATED",
            "server_ts": base_time.isoformat(),
        },
        # Offer ACKed at T+20s
        {
            "referral_id": ref_id,
            "seq": 2,
            "type": "OFFER_ACK",
            "server_ts": (base_time + timedelta(seconds=20)).isoformat(),
        },
        # Offer Accepted at T+35s
        {
            "referral_id": ref_id,
            "seq": 3,
            "type": "OFFER_ACCEPTED",
            "server_ts": (base_time + timedelta(seconds=35)).isoformat(),
        },
        # Ambulance Arrived at T+1200s (20 mins)
        {
            "referral_id": ref_id,
            "seq": 4,
            "type": "TR_UPDATE",
            "detail": {"tr_state": "ARRIVED"},
            "server_ts": (base_time + timedelta(seconds=1200)).isoformat(),
        },
        # Handover completed at T+1320s (22 mins, APOT handover duration = 120s)
        {
            "referral_id": ref_id,
            "seq": 5,
            "type": "TR_UPDATE",
            "detail": {"tr_state": "HANDED_OVER"},
            "server_ts": (base_time + timedelta(seconds=1320)).isoformat(),
        },
    ]

    kpis = compute_log_kpis(events)
    assert kpis["total_referrals"] == 1
    assert kpis["accepted_referrals"] == 1
    assert kpis["median_ack_latency_s"] == 20.0
    # APOT Handover Duration: 1320 - 1200 = 120.0 seconds
    assert kpis["median_apot_handover_s"] == 120.0


def test_capability_attestations_age_and_live_beds_exclusion():
    """Verify capability age calculation, expired filter, and strict exclusion of 'live beds'."""
    now = datetime(2026, 11, 14, 12, 0, 0, tzinfo=timezone.utc)

    confirmations = [
        # Active OT confirmation attested 1h 30m ago
        {
            "facility_id": "fac-001",
            "capability": "OT (Obstetric)",
            "confirmed_at": (now - timedelta(hours=1, minutes=30)).isoformat(),
            "expires_at": (now + timedelta(hours=2)).isoformat(),
        },
        # Expired Blood confirmation (expired 10 mins ago)
        {
            "facility_id": "fac-001",
            "capability": "Blood O-ve",
            "confirmed_at": (now - timedelta(hours=3)).isoformat(),
            "expires_at": (now - timedelta(minutes=10)).isoformat(),
        },
    ]

    active = filter_active_capabilities(confirmations, now=now)
    assert len(active) == 1
    assert active[0]["capability"] == "OT (Obstetric)"
    assert active[0]["age_label"] == "Attested 1h 30m ago"

    # Strict compliance: no 'live beds' in output
    for item in active:
        assert "live beds" not in item["capability"].lower()
        assert "live beds" not in item["age_label"].lower()


def test_referral_network_graph_with_networkx():
    """Verify directed network graph construction, betweenness centrality, and non-causal disclaimer."""
    records = [
        {"origin_facility_id": "PHC_01", "lease_facility_id": "CHC_02"},
        {"origin_facility_id": "PHC_01", "lease_facility_id": "CHC_02"},
        {"origin_facility_id": "CHC_02", "lease_facility_id": "DH_03"},
        {"origin_facility_id": "PHC_04", "lease_facility_id": "CHC_02"},
    ]

    graph_data = build_referral_network_graph(records)
    assert graph_data["label"] == "Descriptive Network Graph (Not Causal)"
    assert graph_data["node_count"] == 4
    assert graph_data["edge_count"] == 3

    # CHC_02 is the intermediate bridge between PHC and DH -> highest betweenness centrality
    chc_node = next(n for n in graph_data["nodes"] if n["id"] == "CHC_02")
    assert chc_node["betweenness_centrality"] > 0.0


def test_4h_bucketing_and_k_anonymity_suppression():
    """Verify 4h bucket truncation and k>=5 small-cell suppression."""
    base_time = datetime(2026, 11, 14, 10, 15, tzinfo=timezone.utc)
    # 10:15 falls in the 08:00 - 12:00 window -> bucketed to '2026-11-14 08:00'
    assert bucket_4h_timestamp(base_time) == "2026-11-14 08:00"

    # Create 4 referrals for Facility A (count < 5 -> suppressed)
    rows_fac_a = [
        {"facility_id": "FAC_A", "need_class": "OB_ECLAMPSIA", "created_at": base_time}
        for _ in range(4)
    ]
    # Create 5 referrals for Facility B (count == 5 -> emitted)
    rows_fac_b = [
        {"facility_id": "FAC_B", "need_class": "OB_ECLAMPSIA", "created_at": base_time}
        for _ in range(5)
    ]

    combined = rows_fac_a + rows_fac_b
    bucketed = bucket_and_suppress(combined, k=5)

    assert len(bucketed) == 2

    res_a = next(b for b in bucketed if b["facility_id"] == "FAC_A")
    assert res_a["is_suppressed"] is True
    assert res_a["count"] == "<5"

    res_b = next(b for b in bucketed if b["facility_id"] == "FAC_B")
    assert res_b["is_suppressed"] is False
    assert res_b["count"] == "5"
