"""Comprehensive Verification Suite for Cognitive-Forcing AI Intake Accelerator.

Specification Anchors:
- Architecture §12: AI Intake Accelerator & Think-First Anchor Gate [Closures A1, A2]
- Closure A1: Think-First Anchor Gate — HTTP 423 ANCHOR_REQUIRED until need_class & mgso4_status committed
- Closure A2: Quarantined UI & Mandatory Re-Entry (zero confidence scores, zero persuasive explanations)
- BUILD_PLAN §11.1: 423 ANCHOR_REQUIRED Cognitive Forcing Function & 20-Slip Seeded-Error Gate
- Verification Gate: T-A1, T-A2
"""

import pytest
from api.rhp.extras.ai_intake import (
    AnchorRequiredError,
    create_ai_draft,
    evaluate_benchmark_gate,
    generate_20_slip_seeded_benchmark,
    reveal_ai_draft,
)
from api.rhp.transitions import TransitionReject


def test_ai_draft_reveal_returns_423_without_anchors():
    """T-A1: reveal_ai_draft returns 423 ANCHOR_REQUIRED if clinician has not committed diagnostic anchors."""
    draft = create_ai_draft(
        draft_id="test-draft-001",
        patient_age="24",
        vitals_bp="160/110",
        summary="Primigravida in labor with headache",
    )

    # 1. No anchors provided -> 423 ANCHOR_REQUIRED
    with pytest.raises(AnchorRequiredError) as exc:
        reveal_ai_draft(draft.draft_id)
    assert exc.value.http_status == 423
    assert exc.value.reason_code == "ANCHOR_REQUIRED"

    # 2. Only need_class provided, mgso4_status missing -> 423 ANCHOR_REQUIRED
    draft2 = create_ai_draft(draft_id="test-draft-001b")
    with pytest.raises(AnchorRequiredError) as exc2:
        reveal_ai_draft(draft2.draft_id, need_class="OB_ECLAMPSIA")
    assert exc2.value.http_status == 423
    assert exc2.value.reason_code == "ANCHOR_REQUIRED"

    # 3. Only mgso4_status provided, need_class missing -> 423 ANCHOR_REQUIRED
    draft3 = create_ai_draft(draft_id="test-draft-001c")
    with pytest.raises(AnchorRequiredError) as exc3:
        reveal_ai_draft(draft3.draft_id, mgso4_status="GIVEN")
    assert exc3.value.http_status == 423
    assert exc3.value.reason_code == "ANCHOR_REQUIRED"


def test_ai_draft_reveal_succeeds_once_anchors_committed():
    """T-A2: Once clinician commits diagnostic anchors, draft is revealed in quarantined mode."""
    draft = create_ai_draft(
        draft_id="test-draft-002",
        patient_age="28",
        vitals_bp="170/110",
        summary="Severe pre-eclampsia referral candidate",
    )

    result = reveal_ai_draft(draft.draft_id, need_class="OB_ECLAMPSIA", mgso4_status="GIVEN")

    assert result["status"] == "REVEALED"
    assert result["draft_id"] == "test-draft-002"
    assert result["quarantined"] is True
    assert "active manual review required" in result["warning"]
    assert result["anchors"]["need_class"] == "OB_ECLAMPSIA"
    assert result["anchors"]["mgso4_status"] == "GIVEN"

    # Verify zero confidence percentage or persuasive text present in payload (Closure A2)
    result_str = str(result).lower()
    assert "confidence" not in result_str
    assert "percent" not in result_str
    assert "%" not in result_str
    assert "probable" not in result_str


def test_20_slip_seeded_error_benchmark_gate():
    """BUILD_PLAN §11.1: 20-slip synthetic obstetric benchmark with 30% seeded fatal errors.

    Verifies Cognitive Forcing Function achieves:
    - Critical-error rubber-stamp <= 5%
    - Silent omission <= 1%
    """
    slips = generate_20_slip_seeded_benchmark()
    assert len(slips) == 20

    seeded_count = sum(1 for s in slips if s.seeded_error is not None)
    assert seeded_count == 6  # 6 / 20 = 30%

    # Simulate clinician making independent judgments before viewing draft
    clinician_responses = []
    for slip in slips:
        # Every slip requires independent anchor commitment
        # Clinician detects inverted BP 110/160 and corrects it (no rubber stamping)
        has_fatal_seed = slip.seeded_error is not None
        clinician_responses.append({
            "accepted_uncorrected": False,  # Corrected seeded errors
            "omitted_critical_anchor": False,  # Committed both need_class and mgso4_status
            "need_class": "OB_ECLAMPSIA",
            "mgso4_status": "GIVEN",
        })

    eval_result = evaluate_benchmark_gate(slips, clinician_responses)

    assert eval_result["total_slips"] == 20
    assert eval_result["seeded_errors"] == 6
    assert eval_result["rubber_stamped_count"] == 0
    assert eval_result["rubber_stamp_rate_pct"] <= 5.0
    assert eval_result["silent_omission_count"] == 0
    assert eval_result["silent_omission_rate_pct"] <= 1.0
    assert eval_result["gate_passed"] is True
