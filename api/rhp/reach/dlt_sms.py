"""ReferralHandshake Protocol RHP-1 — TRAI DLT-Compliant Static SMS Alert Adapter.

Specification Anchors:
- Architecture §8, §9: Multi-Channel Outbox Adapters & Privacy Guardrails [Closure P2]
- BUILD_PLAN §9.4: TRAI DLT-Compliant Static SMS Alert Adapter
- Test Anchor: T-P2 (test_dlt_sms_lint.py)

Enforces:
1. Strict static template: "RHP alert: new referral. Open {#var#}"
2. {#var#} is strictly <= 30 characters and matches ^[A-Za-z0-9/_.-]{1,30}$
3. Complete prohibition of PHI, patient identifiers, and freeform clinical text.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

# Static TRAI DLT Registered Template
DLT_TEMPLATE = "RHP alert: new referral. Open {#var#}"
DLT_VAR_REGEX = re.compile(r"^[A-Za-z0-9/_.-]{1,30}$")

# Disallowed clinical keywords and PHI markers that must never appear in SMS
BANNED_CLINICAL_TERMS = {
    "patient", "eclampsia", "pre-eclampsia", "bp", "vitals", "mgso4",
    "seizure", "bleeding", "pph", "sepsis", "labour", "gravida",
    "para", "gestation", "foetal", "fetal", "hr", "spo2", "icu", "nicu"
}


class DLTSMSValidationError(ValueError):
    """Raised when an SMS payload violates TRAI DLT length or content safety constraints."""
    pass


def validate_dlt_variable(var_val: str) -> None:
    """Validates that a variable to be inserted into the DLT template conforms to TRAI rules.

    Raises DLTSMSValidationError if length > 30, invalid characters, or clinical terms detected.
    """
    if not isinstance(var_val, str):
        raise DLTSMSValidationError(f"Variable must be a string, got {type(var_val).__name__}")

    if len(var_val) == 0:
        raise DLTSMSValidationError("DLT variable cannot be empty")

    if len(var_val) > 30:
        raise DLTSMSValidationError(
            f"DLT variable length {len(var_val)} exceeds maximum permitted length of 30 characters"
        )

    if not DLT_VAR_REGEX.match(var_val):
        raise DLTSMSValidationError(
            f"DLT variable '{var_val}' contains invalid characters; must match '^[A-Za-z0-9/_.-]{{1,30}}$'"
        )

    # Check for banned clinical / PHI text in variable
    lower_val = var_val.lower()
    for term in BANNED_CLINICAL_TERMS:
        if term in lower_val:
            raise DLTSMSValidationError(
                f"DLT variable contains banned clinical or PHI keyword '{term}'"
            )


def format_dlt_sms(var_val: str, **kwargs: Any) -> str:
    """Formats the DLT message by inserting the validated variable into the static template.

    Any additional kwargs representing clinical text or patient names trigger a hard error.
    """
    if kwargs:
        raise DLTSMSValidationError(
            f"Passing additional clinical or demographic fields to SMS adapter is strictly prohibited: {list(kwargs.keys())}"
        )

    validate_dlt_variable(var_val)
    return f"RHP alert: new referral. Open {var_val}"


def send_dlt_sms(phone_e164: str, var_val: str) -> Dict[str, Any]:
    """Stub/Dispatcher for sending TRAI DLT compliant SMS.

    Validates phone format (+91...) and variable bounds before sending.
    """
    if not re.match(r"^\+[1-9]\d{7,14}$", phone_e164):
        raise DLTSMSValidationError(f"Invalid E.164 phone number: '{phone_e164}'")

    rendered = format_dlt_sms(var_val)
    return {
        "status": "QUEUED",
        "to": phone_e164,
        "message": rendered,
        "template_id": "DLT-RHP-REF-01",
        "var": var_val,
    }

