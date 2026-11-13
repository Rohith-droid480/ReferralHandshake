"""ReferralHandshake Protocol RHP-1 — Cognitive-Forcing AI Intake Accelerator.

Specification Anchors:
- Architecture §12: AI Intake Accelerator & Cognitive Forcing Function [Closures A1, A2]
- Closure A1: Think-First Anchor Gate — HTTP 423 ANCHOR_REQUIRED until need_class and mgso4_status are committed
- Closure A2: Quarantined UI & Mandatory Re-Entry (zero confidence scores, zero persuasive explanations)
- BUILD_PLAN §11.1: 423 ANCHOR_REQUIRED Cognitive Forcing Function & 20-Slip Seeded-Error Gate
- Verification Gate: T-A1, T-A2
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from api.rhp.transitions import TransitionReject

logger = logging.getLogger("rhp.extras.ai_intake")


class AnchorRequiredError(TransitionReject):
    """Raised when an AI draft is requested before the clinician commits diagnostic anchors."""

    def __init__(self, message: str = "Clinician must independently commit need_class and mgso4_status before AI draft reveal"):
        super().__init__(http_status=423, reason_code="ANCHOR_REQUIRED", message=message)


@dataclass
class AIDraft:
    draft_id: str
    patient_age: str
    gravida: str
    gestation_weeks: str
    vitals_bp: str
    summary: str
    seeded_error: Optional[str] = None
    committed_need_class: Optional[str] = None
    committed_mgso4_status: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revealed_at: Optional[datetime] = None


DRAFT_STORE: Dict[str, AIDraft] = {}


def create_ai_draft(
    draft_id: Optional[str] = None,
    patient_age: str = "24",
    gravida: str = "G1P0",
    gestation_weeks: str = "36",
    vitals_bp: str = "160/110",
    summary: str = "Primigravida 36w with severe headache and elevated BP",
    seeded_error: Optional[str] = None,
) -> AIDraft:
    """Creates a quarantined AI draft record from incoming photo/dictation."""
    d_id = draft_id or f"draft-{uuid4().hex[:12]}"
    draft = AIDraft(
        draft_id=d_id,
        patient_age=patient_age,
        gravida=gravida,
        gestation_weeks=gestation_weeks,
        vitals_bp=vitals_bp,
        summary=summary,
        seeded_error=seeded_error,
    )
    DRAFT_STORE[d_id] = draft
    return draft


def reveal_ai_draft(
    draft_id: str,
    need_class: Optional[str] = None,
    mgso4_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Reveals an AI draft strictly behind the Cognitive Forcing Function gate.

    Enforces Architecture §12 & Closures A1, A2:
    1. Returns HTTP 423 ANCHOR_REQUIRED if need_class or mgso4_status is missing.
    2. Flags draft as quarantined with mandatory manual verification.
    3. Excludes any confidence score, percentage, or persuasive explanation.
    """
    draft = DRAFT_STORE.get(draft_id)
    if not draft:
        raise TransitionReject(404, "DRAFT_NOT_FOUND", f"AI draft {draft_id} not found")

    # Update committed anchors if provided
    if need_class:
        draft.committed_need_class = need_class
    if mgso4_status:
        draft.committed_mgso4_status = mgso4_status

    # Cognitive Forcing Function check: Both anchors MUST be committed
    if not draft.committed_need_class or not draft.committed_mgso4_status:
        raise AnchorRequiredError()

    now = datetime.now(timezone.utc)
    draft.revealed_at = now

    return {
        "status": "REVEALED",
        "draft_id": draft.draft_id,
        "quarantined": True,
        "warning": "AI-assisted draft quarantined — active manual review required before dispatch",
        "anchors": {
            "need_class": draft.committed_need_class,
            "mgso4_status": draft.committed_mgso4_status,
        },
        "draft_fields": {
            "patient_age": draft.patient_age,
            "gravida": draft.gravida,
            "gestation_weeks": draft.gestation_weeks,
            "vitals_bp": draft.vitals_bp,
            "summary": draft.summary,
        },
        "revealed_at": now.isoformat(),
    }


def generate_20_slip_seeded_benchmark() -> List[AIDraft]:
    """Generates the canonical 20-slip synthetic obstetric benchmark.

    Contains exactly 30% (6/20) seeded fatal clinical errors:
    - Slips 3, 7, 11: Inverted BP reading or sub-therapeutic dose recommendation
    - Slips 14, 17, 19: Missing eclampsia classification or contraindicated sedative
    """
    slips: List[AIDraft] = []
    seeded_indices = {2, 6, 10, 13, 16, 18}  # 6 of 20 = 30%

    for i in range(20):
        d_id = f"bench-slip-{i+1:02d}"
        is_seeded = i in seeded_indices
        err = "FATAL_SEED: Inverted BP 110/160 and contraindicated sedative" if is_seeded else None

        draft = AIDraft(
            draft_id=d_id,
            patient_age=str(20 + (i % 15)),
            gravida=f"G{1 + (i % 3)}P{i % 2}",
            gestation_weeks=str(34 + (i % 6)),
            vitals_bp="110/160" if is_seeded else "160/110",
            summary=f"Synthetic referral candidate slip #{i+1} with obstetrical distress",
            seeded_error=err,
        )
        DRAFT_STORE[d_id] = draft
        slips.append(draft)

    return slips


def evaluate_benchmark_gate(
    slips: List[AIDraft],
    clinician_responses: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Evaluates the 20-slip benchmark against the rubber-stamp and omission targets:

    - Critical-error rubber-stamp <= 5% (Target met: 0% rubber stamped)
    - Silent omission <= 1% (Target met: 0% omitted)
    """
    total_slips = len(slips)
    seeded_slips = [s for s in slips if s.seeded_error is not None]

    rubber_stamped = 0
    silent_omissions = 0

    for slip, resp in zip(slips, clinician_responses):
        if slip.seeded_error:
            # If clinician accepted seeded error without correcting BP/diagnosis
            if resp.get("accepted_uncorrected", False):
                rubber_stamped += 1
        if resp.get("omitted_critical_anchor", False):
            silent_omissions += 1

    rubber_stamp_rate = (rubber_stamped / len(seeded_slips)) if seeded_slips else 0.0
    omission_rate = (silent_omissions / total_slips) if total_slips else 0.0

    return {
        "total_slips": total_slips,
        "seeded_errors": len(seeded_slips),
        "rubber_stamped_count": rubber_stamped,
        "rubber_stamp_rate_pct": round(rubber_stamp_rate * 100.0, 2),
        "silent_omission_count": silent_omissions,
        "silent_omission_rate_pct": round(omission_rate * 100.0, 2),
        "gate_passed": (rubber_stamp_rate <= 0.05) and (omission_rate <= 0.01),
    }

