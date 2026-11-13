"""ReferralHandshake Protocol RHP-1 — District Command Centre Analytics & Network Graph.

Specification Anchors:
- Architecture §15: Audit Ledger, Governance & Analytics [Closure F9]
- BUILD_PLAN §10.3: District Command Centre, APOT KPIs & Capability Attestations
- BUILD_PLAN §10.4: Referral Network Graph (networkx) & 4-Hour Bucketed k>=5 Suppression
- Test Anchor: test_analytics_recompute.py

Key Requirements:
1. Anti-Goodhart KPIs:
   - Median and p95 Time-to-ACK (seconds)
   - APOT-Style Arrival-to-Handover Time (seconds from ARRIVED to HANDED_OVER)
   - Unanswered Offer Rate
   - ARRIVAL_REJECTED Broken-Commitment Rate
2. Capability Attestations with Age:
   - Attested Xh Ym ago (based on resource confirmation timestamp)
   - Expired attestations (expires_at <= now) are filtered out.
   - Strict ban on the phrase 'live beds'.
3. Referral Network Graph (networkx):
   - Builds networkx.DiGraph from origin_facility_id -> lease_facility_id / declined hops
   - Computes betweenness centrality
   - Labeled: 'Descriptive Network Graph (Not Causal)'
4. Privacy-Preserving Aggregations (k >= 5):
   - Truncates timestamps to 4-hour buckets (00:00, 04:00, 08:00, 12:00, 16:00, 20:00)
   - Masks cells with count < 5 as '<5', retains exact count when count >= 5.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import networkx as nx

logger = logging.getLogger("rhp.extras.analytics")


def format_attestation_age(confirmed_at: datetime, now: Optional[datetime] = None) -> str:
    """Formats the elapsed time since capability attestation as 'Attested Xh Ym ago'.

    Never uses the phrase 'live beds'.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    delta_s = max(0.0, (now - confirmed_at).total_seconds())
    hours = int(delta_s // 3600)
    minutes = int((delta_s % 3600) // 60)

    if hours > 0:
        return f"Attested {hours}h {minutes}m ago"
    return f"Attested {minutes}m ago"


def filter_active_capabilities(
    confirmations: List[Dict[str, Any]], now: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Filters out expired capability attestations and attaches elapsed age string.

    Guarantees no 'live beds' phrasing appears in output.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    active = []
    for c in confirmations:
        exp = c.get("expires_at")
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp.replace("Z", "+00:00"))

        if exp and exp > now:
            conf_at = c.get("confirmed_at")
            if isinstance(conf_at, str):
                conf_at = datetime.fromisoformat(conf_at.replace("Z", "+00:00"))
            elif conf_at is None:
                conf_at = now

            item = dict(c)
            item["age_label"] = format_attestation_age(conf_at, now)
            # Ensure compliance: remove any 'live beds' terminology if present in input
            item["capability"] = str(c.get("capability", "")).replace("live beds", "resource").strip()
            active.append(item)

    return active


def compute_log_kpis(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes APOT and anti-Goodhart KPIs strictly from the committed event log.

    Separates acceptance latency from physical handover duration.
    """
    # Group events by referral_id
    ref_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ev in events:
        ref_id = str(ev.get("referral_id", ""))
        if ref_id:
            ref_events[ref_id].append(ev)

    ack_latencies_s: List[float] = []
    apot_handover_latencies_s: List[float] = []
    unanswered_count = 0
    total_offers = 0
    arrival_rejected_count = 0
    accepted_count = 0

    for ref_id, evs in ref_events.items():
        evs_sorted = sorted(evs, key=lambda x: x.get("seq", 0))

        create_ts: Optional[datetime] = None
        first_ack_ts: Optional[datetime] = None
        arrived_ts: Optional[datetime] = None
        handed_over_ts: Optional[datetime] = None

        for ev in evs_sorted:
            ev_type = ev.get("type")
            ts = ev.get("server_ts")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

            if ev_type in ("REFERRAL_CREATED", "OFFER_CREATED"):
                total_offers += 1
                if not create_ts:
                    create_ts = ts
            elif ev_type == "OFFER_ACK" and not first_ack_ts:
                first_ack_ts = ts
            elif ev_type in ("OFFER_ACCEPTED", "LEASE_GRANTED"):
                accepted_count += 1
            elif ev_type == "TIMEOUT" and ev.get("detail", {}).get("kind") == "ACK":
                unanswered_count += 1
            elif ev_type == "ARRIVAL_REJECTED":
                arrival_rejected_count += 1
            elif ev_type == "TR_UPDATE":
                tr_st = ev.get("detail", {}).get("tr_state")
                if tr_st == "ARRIVED" and not arrived_ts:
                    arrived_ts = ts
                elif tr_st == "HANDED_OVER" and not handed_over_ts:
                    handed_over_ts = ts

        if create_ts and first_ack_ts:
            lat = max(0.0, (first_ack_ts - create_ts).total_seconds())
            ack_latencies_s.append(lat)

        if arrived_ts and handed_over_ts:
            handover_dur = max(0.0, (handed_over_ts - arrived_ts).total_seconds())
            apot_handover_latencies_s.append(handover_dur)

    ack_latencies_s.sort()
    apot_handover_latencies_s.sort()

    def _median(arr: List[float]) -> float:
        if not arr:
            return 0.0
        n = len(arr)
        return arr[n // 2] if n % 2 == 1 else (arr[n // 2 - 1] + arr[n // 2]) / 2.0

    def _p95(arr: List[float]) -> float:
        if not arr:
            return 0.0
        idx = int(0.95 * (len(arr) - 1))
        return arr[idx]

    return {
        "median_ack_latency_s": round(_median(ack_latencies_s), 2),
        "p95_ack_latency_s": round(_p95(ack_latencies_s), 2),
        "median_apot_handover_s": round(_median(apot_handover_latencies_s), 2),
        "p95_apot_handover_s": round(_p95(apot_handover_latencies_s), 2),
        "unanswered_offer_rate": round(unanswered_count / max(1, total_offers), 4),
        "arrival_rejected_rate": round(arrival_rejected_count / max(1, accepted_count), 4),
        "total_referrals": len(ref_events),
        "total_offers": total_offers,
        "accepted_referrals": accepted_count,
    }


def build_referral_network_graph(referral_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Builds a directed weighted networkx graph from referral origin and lease destinations.

    Returns the adjacency data, edge weights, and node betweenness centrality labeled
    as 'Descriptive Network Graph (Not Causal)'.
    """
    g = nx.DiGraph()

    for r in referral_records:
        origin = str(r.get("origin_facility_id", ""))
        target = str(r.get("lease_facility_id") or r.get("destination_facility_id") or "")
        if origin and target and origin != target:
            if g.has_edge(origin, target):
                g[origin][target]["weight"] += 1
            else:
                g.add_edge(origin, target, weight=1)
        elif origin:
            g.add_node(origin)

    centrality = nx.betweenness_centrality(g) if len(g) > 0 else {}

    nodes = [
        {"id": n, "betweenness_centrality": round(centrality.get(n, 0.0), 4)}
        for n in g.nodes()
    ]
    edges = [
        {"source": u, "target": v, "weight": d.get("weight", 1)}
        for u, v, d in g.edges(data=True)
    ]

    return {
        "label": "Descriptive Network Graph (Not Causal)",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def bucket_4h_timestamp(dt: datetime) -> str:
    """Truncates timestamp to 4-hour window (00:00, 04:00, 08:00, 12:00, 16:00, 20:00)."""
    hour_bucket = (dt.hour // 4) * 4
    bucket_dt = dt.replace(hour=hour_bucket, minute=0, second=0, microsecond=0)
    return bucket_dt.strftime("%Y-%m-%d %H:00")


def bucket_and_suppress(
    referral_rows: List[Dict[str, Any]], k: int = 5
) -> List[Dict[str, Any]]:
    """Aggregates referrals into 4-hour buckets by facility and need_class.

    Enforces k-anonymity privacy suppression: cells with count < k are masked as '<k'.
    """
    buckets: Dict[Tuple[str, str, str], int] = defaultdict(int)

    for row in referral_rows:
        fac = str(row.get("facility_id") or row.get("origin_facility_id") or "UNKNOWN")
        need = str(row.get("need_class") or "OBSTETRIC_EMERGENCY")

        ts_val = row.get("created_at") or row.get("server_ts") or datetime.now(timezone.utc)
        if isinstance(ts_val, str):
            ts_val = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))

        bucket_key = bucket_4h_timestamp(ts_val)
        buckets[(fac, need, bucket_key)] += 1

    results: List[Dict[str, Any]] = []
    for (fac, need, b_time), count in buckets.items():
        results.append({
            "facility_id": fac,
            "need_class": need,
            "bucket_4h": b_time,
            "count": str(count) if count >= k else f"<{k}",
            "is_suppressed": count < k,
            "raw_count": count if count >= k else None,
        })

    return sorted(results, key=lambda x: (x["bucket_4h"], x["facility_id"]))

