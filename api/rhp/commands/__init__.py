"""ReferralHandshake Protocol RHP-1 — Protocol Command Modules.

Specification Anchors:
- Architecture §4: State Transition Rules & Guards
- Architecture §5: The 10-step apply_command() transaction contract
- BUILD_PLAN Module 3: Core Handshake Commands & Escalation Engine
"""

from api.rhp.commands.accept import execute_accept
from api.rhp.commands.ack_confirm import execute_ack, execute_resource_confirm
from api.rhp.commands.counter import execute_confirm_counter, execute_counter
from api.rhp.commands.create import execute_create, generate_paper_code, validate_paper_code
from api.rhp.commands.decline_advance import advance, execute_decline
from api.rhp.commands.lifecycle import (
    execute_arrival_rejected,
    execute_cancel,
    execute_close,
    execute_dispatcher_assign,
    execute_revoke_grant,
)

__all__ = [
    "execute_create",
    "generate_paper_code",
    "validate_paper_code",
    "execute_ack",
    "execute_resource_confirm",
    "execute_accept",
    "advance",
    "execute_decline",
    "execute_counter",
    "execute_confirm_counter",
    "execute_arrival_rejected",
    "execute_dispatcher_assign",
    "execute_cancel",
    "execute_close",
    "execute_revoke_grant",
]
