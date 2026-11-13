"""Comprehensive Verification Suite for NRCeS/ABDM-Aligned FHIR R4 Bundle Exporter.

Specification Anchors:
- Architecture §16: Interoperability & FHIR R4 Export [Closure P3, F9]
- BUILD_PLAN §11.2: FHIR R4 Bundle Exporter (ServiceRequest, Task, Encounter, Communication)
- Test Anchor: T-P3
"""

from uuid import uuid4
from api.rhp.extras.exporters import export_referral_to_fhir_r4


def test_fhir_r4_bundle_structure_and_curated_resources():
    """T-P3: Verifies FHIR R4 collection bundle generation with ServiceRequest, Task, Encounter, Communication."""
    ref_id = str(uuid4())
    origin_fac = "00000000-0000-0000-0000-000000000001"
    lease_fac = "00000000-0000-0000-0000-000000000002"

    referral = {
        "id": ref_id,
        "hs_state": "CLOSED",
        "tr_state": "HANDED_OVER",
        "need_class": "OB_ECLAMPSIA",
        "origin_facility_id": origin_fac,
        "lease_facility_id": lease_fac,
    }

    events = [
        {"seq": 1, "type": "CREATE", "server_ts": "2026-11-14T02:00:00Z"},
        {"seq": 2, "type": "OFFER_DECLINED", "detail": {"reason": "BED_UNAVAILABLE"}, "server_ts": "2026-11-14T02:05:00Z"},
        {"seq": 3, "type": "TR_UPDATE", "detail": {"tr_state": "ARRIVED"}, "server_ts": "2026-11-14T02:30:00Z"},
        {"seq": 4, "type": "TR_UPDATE", "detail": {"tr_state": "HANDED_OVER"}, "server_ts": "2026-11-14T02:45:00Z"},
    ]

    bundle = export_referral_to_fhir_r4(referral, events)

    # 1. Bundle envelope validation
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["id"] == f"bundle-{ref_id}"
    assert bundle["total"] >= 3

    resource_types = [entry["resource"]["resourceType"] for entry in bundle["entry"]]
    assert "ServiceRequest" in resource_types
    assert "Task" in resource_types
    assert "Encounter" in resource_types
    assert "Communication" in resource_types

    # 2. ServiceRequest validation
    sr = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "ServiceRequest")
    assert sr["status"] == "completed"
    assert sr["intent"] == "order"
    assert sr["code"]["coding"][0]["code"] == "398254007"  # SNOMED Preeclampsia
    assert sr["requester"]["reference"] == f"Organization/{origin_fac}"
    assert sr["performer"][0]["reference"] == f"Organization/{lease_fac}"

    # 3. Task validation
    task = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Task")
    assert task["status"] == "completed"
    assert task["businessStatus"]["text"] == "CLOSED"
    assert task["focus"]["reference"] == f"ServiceRequest/sr-{ref_id}"
    assert task["owner"]["reference"] == f"Organization/{lease_fac}"

    # 4. Encounter validation
    enc = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Encounter")
    assert enc["status"] in ("arrived", "finished")
    assert enc["class"]["code"] == "EMER"

    # 5. Communication validation
    comm = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Communication")
    assert comm["status"] == "completed"
    assert "BED_UNAVAILABLE" in comm["payload"][0]["contentString"]


def test_fhir_r4_state_mappings():
    """Verify deterministic mapping of RHP-1 hs_state to FHIR Task.status."""
    test_cases = [
        ("CREATED", "requested"),
        ("OFFERED", "requested"),
        ("ACKNOWLEDGED", "received"),
        ("ACCEPTED", "accepted"),
        ("COUNTERED", "on-hold"),
        ("ESCALATED_TO_DISPATCHER", "on-hold"),
        ("CANCELLED", "cancelled"),
        ("CLOSED", "completed"),
    ]

    for hs_state, expected_task_status in test_cases:
        referral = {
            "id": str(uuid4()),
            "hs_state": hs_state,
            "need_class": "OB_PPH",
            "origin_facility_id": "00000000-0000-0000-0000-000000000001",
        }
        bundle = export_referral_to_fhir_r4(referral, [])
        task = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Task")
        assert task["status"] == expected_task_status
