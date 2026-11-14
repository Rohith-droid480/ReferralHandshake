"""Test Suite for Protocol RHP-1 Canonical State Transitions Table (T-F19).

Specification Anchors:
- Architecture §4: Canonical Transitions Table & Guard Logic [F19]
- Architecture §18: Invariants I1, I2, I3, I6, I9, I12, I13
- Solution v8 §4: 12-State v7 Mapping, Two Independent Tracks & 9 Outcomes
- BUILD_PLAN §1.5: Verification Gate (T-F19)
"""

import sys
from pathlib import Path
import pytest

# Ensure api directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "api") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "api"))

from rhp.transitions import TRANSITIONS, TransitionsTable, TransitionReject


def test_t_f19_spec_loads_and_commands_count():
    """T-F19: transitions.yaml loads cleanly and parses all 15 commands."""
    commands = TRANSITIONS.get_commands()
    assert len(commands) == 15, f"Expected 15 commands, got {len(commands)}"

    expected_cmds = [
        "CREATE",
        "ACK",
        "RESOURCE_CONFIRM",
        "ACCEPT",
        "COUNTER",
        "CONFIRM_COUNTER",
        "DECLINE",
        "TIMEOUT",
        "ARRIVAL_REJECTED",
        "DISPATCHER_ASSIGN",
        "TR_UPDATE",
        "TR_DESTINATION_CHANGE",
        "CANCEL",
        "CLOSE",
        "REVOKE_GRANT",
    ]
    for cmd_name in expected_cmds:
        assert cmd_name in commands, f"Missing command: {cmd_name}"


def test_t_f19_states_inventory():
    """T-F19: Verifies 8 hs_states, 6 tr_states, and 10 offer_statuses."""
    states = TRANSITIONS.get_states()
    assert "handshake" in states
    assert "transport" in states
    assert "offer" in states

    # 8 Handshake States
    hs_all = states["handshake"]["all"]
    assert len(hs_all) == 8
    assert set(hs_all) == {
        "CREATED",
        "OFFERED",
        "ACKNOWLEDGED",
        "ACCEPTED",
        "COUNTERED",
        "ESCALATED_TO_DISPATCHER",
        "CANCELLED",
        "CLOSED",
    }
    assert states["handshake"]["initial"] == "CREATED"
    assert set(states["handshake"]["terminal"]) == {"CANCELLED", "CLOSED"}

    # 6 Transport States
    tr_all = states["transport"]["all"]
    assert len(tr_all) == 6
    assert set(tr_all) == {
        "REQUESTED",
        "DISPATCHED",
        "EN_ROUTE",
        "ARRIVED",
        "HANDED_OVER",
        "TR_CANCELLED",
    }
    assert states["transport"]["initial"] == "REQUESTED"
    assert set(states["transport"]["terminal"]) == {"HANDED_OVER", "TR_CANCELLED"}

    # 10 Offer Statuses
    off_all = states["offer"]["all"]
    assert len(off_all) == 10
    assert set(off_all) == {
        "OPEN",
        "ACKED",
        "COUNTERED",
        "SOFT_OPEN",
        "ACCEPTED",
        "DECLINED",
        "TIMED_OUT",
        "SUPERSEDED",
        "ARRIVAL_REJECTED",
        "WITHDRAWN",
    }
    assert set(states["offer"]["open_set"]) == {"OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"}


def test_t_f19_12_state_v7_mapping():
    """T-F19: Verifies the 12 legacy v7 states are mapped to exact RHP-1 state compositions."""
    mappings = TRANSITIONS.get_v7_mappings()
    expected_v7 = [
        "CREATED",
        "OFFERED",
        "ACKNOWLEDGED",
        "ACCEPTED",
        "COUNTERED",
        "DECLINED",
        "TIMED_OUT",
        "ESCALATED",
        "ARRIVAL_REJECTED",
        "ESCALATED_TO_DISPATCHER",
        "CANCELLED",
        "CLOSED",
    ]
    for st in expected_v7:
        assert st in mappings, f"Missing v7 mapping for: {st}"


def test_t_f19_9_outcome_taxonomy():
    """F6 / Section 3: Verifies 9 locked outcomes and required handover constraints."""
    outcomes = TRANSITIONS.get_outcomes()
    assert len(outcomes) == 9

    expected_outcomes = [
        "ADMITTED_STABLE",
        "ADMITTED_CRITICAL",
        "DELIVERED_AT_RECEIVER",
        "DELIVERED_EN_ROUTE",
        "PATIENT_REFUSED",
        "TRANSPORT_CANCELLED",
        "DETERIORATED_OR_DIED_PRE_HANDOVER",
        "REDIRECTED_ON_ARRIVAL",
        "UNKNOWN_COUNTER_REFERRAL",
    ]
    for o in expected_outcomes:
        assert o in outcomes, f"Missing outcome: {o}"

    # Verify handover requirements
    assert outcomes["ADMITTED_STABLE"]["requires_handed_over"] is True
    assert outcomes["ADMITTED_CRITICAL"]["requires_handed_over"] is True
    assert outcomes["DELIVERED_AT_RECEIVER"]["requires_handed_over"] is True
    assert outcomes["DELIVERED_EN_ROUTE"]["requires_handed_over"] is False
    assert outcomes["UNKNOWN_COUNTER_REFERRAL"]["requires_handed_over"] is False


def test_t_f19_pin_requirements_enforced():
    """F7 / I6: Mutating commands require PIN verification; exemptions strictly scoped."""
    commands = TRANSITIONS.get_commands()

    # Mutating commands requiring PIN
    assert commands["CREATE"].requires_pin is True
    assert commands["ACCEPT"].requires_pin is True
    assert commands["COUNTER"].requires_pin is True
    assert commands["CONFIRM_COUNTER"].requires_pin is True
    assert commands["DECLINE"].requires_pin is True
    assert commands["RESOURCE_CONFIRM"].requires_pin is True
    assert commands["CLOSE"].requires_pin is True
    assert commands["CANCEL"].requires_pin is True
    assert commands["ARRIVAL_REJECTED"].requires_pin is True
    assert commands["DISPATCHER_ASSIGN"].requires_pin is True

    # Non-mutating or push-acknowledgement commands without PIN
    assert commands["ACK"].requires_pin is False
    assert commands["TR_UPDATE"].requires_pin is False
    assert commands["TIMEOUT"].requires_pin is False
    assert commands["REVOKE_GRANT"].requires_pin is False

    # SYSTEM role exemption on CLOSE for automatic stage 2 closure
    assert "SYSTEM" in commands["CLOSE"].pin_exemption_roles


def test_transition_lookup_valid_ack():
    """Confirms ACK lookup succeeds when referral is OFFERED and offer is OPEN."""
    cmd = TRANSITIONS.lookup("ACK", {"hs_state": "OFFERED"}, {"status": "OPEN"})
    assert cmd.name == "ACK"
    assert "ACKED" in cmd.effects["target_offer"]["status"]


def test_transition_lookup_accept_guards():
    """Confirms ACCEPT enforces lease absence and open offer statuses."""
    # Valid accept from OPEN
    cmd = TRANSITIONS.lookup("ACCEPT", {"hs_state": "OFFERED", "lease_offer_id": None}, {"status": "OPEN"})
    assert cmd.name == "ACCEPT"

    # Valid accept from SOFT_OPEN
    cmd_soft = TRANSITIONS.lookup("ACCEPT", {"hs_state": "OFFERED", "lease_offer_id": None}, {"status": "SOFT_OPEN"})
    assert cmd_soft.name == "ACCEPT"

    # Reject if lease already held (I2)
    with pytest.raises(TransitionReject) as exc:
        TRANSITIONS.lookup("ACCEPT", {"hs_state": "ACCEPTED", "lease_offer_id": "uuid-1"}, {"status": "OPEN"})
    assert exc.value.reason_code == "LEASE_HELD"

    # Late accept rejected if offer already TIMED_OUT or SUPERSEDED
    with pytest.raises(TransitionReject) as exc:
        TRANSITIONS.lookup("ACCEPT", {"hs_state": "OFFERED", "lease_offer_id": None}, {"status": "TIMED_OUT"})
    assert exc.value.reason_code == "LATE_ACCEPT_REJECTED"

    with pytest.raises(TransitionReject) as exc:
        TRANSITIONS.lookup("ACCEPT", {"hs_state": "OFFERED", "lease_offer_id": None}, {"status": "SUPERSEDED"})
    assert exc.value.reason_code == "LATE_ACCEPT_REJECTED"


def test_i3_track_independence_tr_update():
    """Invariant I3: TR_UPDATE never blocks on or reads hs_state."""
    # Valid TR_UPDATE progression from REQUESTED -> DISPATCHED across various hs_states
    for hs in ("CREATED", "OFFERED", "ACKNOWLEDGED", "COUNTERED", "ESCALATED_TO_DISPATCHER", "ACCEPTED"):
        cmd = TRANSITIONS.lookup(
            "TR_UPDATE",
            {"hs_state": hs, "tr_state": "REQUESTED"},
            target_tr_state="DISPATCHED",
        )
        assert cmd.name == "TR_UPDATE"

    # Invalid TR progression (e.g. ARRIVED -> DISPATCHED)
    with pytest.raises(TransitionReject) as exc:
        TRANSITIONS.lookup(
            "TR_UPDATE",
            {"hs_state": "ACCEPTED", "tr_state": "ARRIVED"},
            target_tr_state="DISPATCHED",
        )
    assert exc.value.reason_code == "INVALID_TR_TRANSITION"


def test_cancel_already_terminal_rejection():
    """Confirms CANCEL is rejected if referral is already in terminal state."""
    with pytest.raises(TransitionReject) as exc:
        TRANSITIONS.lookup("CANCEL", {"hs_state": "CLOSED"}, None)
    assert exc.value.reason_code == "ALREADY_TERMINAL"

    with pytest.raises(TransitionReject) as exc:
        TRANSITIONS.lookup("CANCEL", {"hs_state": "CANCELLED"}, None)
    assert exc.value.reason_code == "ALREADY_TERMINAL"
