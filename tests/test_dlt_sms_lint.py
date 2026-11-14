"""Unit and Linter Tests for TRAI DLT-Compliant Static SMS Alert Adapter.

Specification Anchors:
- BUILD_PLAN §9.4: TRAI DLT-Compliant Static SMS Alert Adapter [Closure P2]
- Test Anchor: T-P2
"""

import pytest
from api.rhp.reach.dlt_sms import (
    DLTSMSValidationError,
    format_dlt_sms,
    send_dlt_sms,
    validate_dlt_variable,
)


def test_dlt_valid_variable_formatting():
    """Valid short paths and Crockford paper codes format strictly into template."""
    var1 = "r/9K7M2W34X"
    rendered = format_dlt_sms(var1)
    assert rendered == "RHP alert: new referral. Open r/9K7M2W34X"

    var2 = "h.rhp.in/c12"
    assert format_dlt_sms(var2) == "RHP alert: new referral. Open h.rhp.in/c12"


def test_dlt_variable_exceeding_30_chars_rejected():
    """Variables strictly longer than 30 characters must be rejected."""
    long_var = "a" * 31
    with pytest.raises(DLTSMSValidationError, match="exceeds maximum permitted length of 30"):
        validate_dlt_variable(long_var)


def test_dlt_variable_with_disallowed_characters_rejected():
    """Characters outside ^[A-Za-z0-9/_.-]{1,30}$ must be rejected."""
    invalid_vars = [
        "has spaces in path",
        "code#123",
        "link?id=123",
        "open&read=1",
        "path;cmd",
        "path<script>",
        "unicode_ಭಾರತ",
    ]
    for var in invalid_vars:
        with pytest.raises(DLTSMSValidationError):
            validate_dlt_variable(var)


def test_dlt_clinical_text_or_phi_strictly_prohibited():
    """Any attempt to pass clinical text or PHI in the variable must trigger a hard error."""
    clinical_vars = [
        "patient_geetha",
        "severe_eclampsia",
        "bp_160_110",
        "mgso4_given",
        "vitals_unstable",
    ]
    for var in clinical_vars:
        with pytest.raises(DLTSMSValidationError, match="banned clinical or PHI keyword"):
            validate_dlt_variable(var)


def test_dlt_kwargs_with_clinical_text_rejected():
    """Passing free-form clinical notes or patient details as kwargs to format_dlt_sms is forbidden."""
    with pytest.raises(DLTSMSValidationError, match="strictly prohibited"):
        format_dlt_sms("r/9K7M2W34X", patient_name="Geetha", diagnosis="Eclampsia")


def test_dlt_send_sms_dispatcher():
    """send_dlt_sms correctly validates E.164 numbers and returns queued payload."""
    res = send_dlt_sms("+919876543210", "r/9K7M2W34X")
    assert res["status"] == "QUEUED"
    assert res["to"] == "+919876543210"
    assert res["message"] == "RHP alert: new referral. Open r/9K7M2W34X"

    # Invalid phone format rejected
    with pytest.raises(DLTSMSValidationError, match="Invalid E.164 phone number"):
        send_dlt_sms("9876543210", "r/9K7M2W34X")

