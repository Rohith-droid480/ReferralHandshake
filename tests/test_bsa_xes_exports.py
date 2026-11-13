"""Comprehensive Verification Suite for IEEE 1849 XES & BSA 2023 s.63 Evidence Exports.

Specification Anchors:
- Architecture §16: Process Mining & Legal Evidence Architecture [Closure F9, F15]
- BUILD_PLAN §11.3: IEEE 1849 XES Exporter & BSA 2023 s.63 Evidence Bundle Generator
- Test Anchor: T-L3
"""

import hashlib
import xml.etree.ElementTree as ET
from uuid import uuid4
from api.rhp.extras.exporters import export_events_to_xes_xml, generate_bsa_section_63_evidence_bundle


def test_ieee_1849_xes_xml_export_validity():
    """Verify IEEE 1849 compliant XML export with 4-hour bucketed timestamps."""
    ref_id = str(uuid4())
    referrals = [
        {"id": ref_id, "origin_facility_id": "00000000-0000-0000-0000-000000000001"}
    ]
    events = {
        ref_id: [
            {"seq": 1, "type": "CREATE", "server_ts": "2026-11-14T01:23:45Z"},
            {"seq": 2, "type": "ACK", "server_ts": "2026-11-14T01:24:10Z"},
            {"seq": 3, "type": "ACCEPT", "server_ts": "2026-11-14T01:25:00Z"},
        ]
    }

    xml_text = export_events_to_xes_xml(referrals, events)

    # 1. XML parse validity
    root = ET.fromstring(xml_text)
    assert "log" in root.tag
    assert root.attrib.get("xes.version") == "1.0"

    # 2. Trace and Event tags
    traces = root.findall("{http://www.xes-standard.org/}trace")
    assert len(traces) == 1
    events_xml = traces[0].findall("{http://www.xes-standard.org/}event")
    assert len(events_xml) == 3

    # 3. 4-hour bucketed timestamp check (01:23 -> 00:00:00Z)
    first_event = events_xml[0]
    date_elem = first_event.find("{http://www.xes-standard.org/}date")
    assert date_elem is not None
    assert "T00:00:00Z" in date_elem.attrib.get("value", "")


def test_bsa_2023_s63_hash_bearing_evidence_bundle():
    """T-L3: Verifies BSA s.63 evidence bundle, SHA-256 manifest recomputation, and claims discipline."""
    ref_id = str(uuid4())
    referral = {
        "id": ref_id,
        "hs_state": "CLOSED",
        "head_seq": 4,
        "head_hash": "a" * 64,
    }
    events = [
        {"seq": 1, "type": "CREATE", "detail": {"need_class": "OB_ECLAMPSIA"}},
        {"seq": 2, "type": "ACK", "detail": {}},
        {"seq": 3, "type": "ACCEPT", "detail": {}},
        {"seq": 4, "type": "CLOSE", "detail": {"outcome": "ADMITTED_STABLE"}},
    ]
    checkpoint = {
        "merkle_root": "b" * 64,
        "sig": "c" * 128,
    }

    bundle = generate_bsa_section_63_evidence_bundle(referral, events, checkpoint)

    # 1. Manifest recomputation check: SHA-256(events_jcs) == manifest_sha256
    raw_jcs_bytes = bundle["events_jcs"].encode("utf-8")
    recomputed_sha256 = hashlib.sha256(raw_jcs_bytes).hexdigest()
    assert recomputed_sha256 == bundle["manifest_sha256"]

    # 2. Header and legal qualification checks (ST-5 discipline)
    header = "BSA s.63-Ready Export Bundle — Requires Authorized Signatory Execution (Not Pre-Certified)"
    assert bundle["header_tag"] == header
    assert header in bundle["certificate_part_a"]
    assert header in bundle["certificate_part_b"]

    # 3. Pre-populated Part A & Part B verification
    assert bundle["manifest_sha256"] in bundle["certificate_part_a"]
    assert bundle["manifest_sha256"] in bundle["certificate_part_b"]
    assert ref_id in bundle["certificate_part_a"]
    assert "Section 63(4)(a)" in bundle["certificate_part_a"]
    assert "Section 63(4)(b)" in bundle["certificate_part_b"]

    # 4. Strict claims linter: zero forbidden phrases in certificate templates
    full_text = (bundle["certificate_part_a"] + bundle["certificate_part_b"]).lower()
    forbidden = ["bsa " + "certified", "bsa-" + "certified", "immutable " + "log", "air" + "tight", "bullet-" + "proof", "mathematically " + "proven"]
    for word in forbidden:
        assert word not in full_text, f"Forbidden claim found: {word}"
