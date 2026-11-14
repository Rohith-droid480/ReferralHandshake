"""ReferralHandshake Protocol RHP-1 — Strict Pydantic Schemas & Role-Command Authorization.

Specification Anchors:
- Architecture §4: State machines & declarative transition tables
- Architecture §5: apply_command() transaction pipeline (Step 5: Authority & Fencing)
- Architecture §7: PostgreSQL 16 schema, rhp_allowed, rhp_detail_ok [Closure F9, Invariant I11]
- Architecture §9: Identity & Role-Command Authorization Matrix [Invariant I6]
- Invariant I8: Optimistic fencing on expected_version and expected_epoch
- Invariant I11: Closed allowlist for event.detail (zero free-text clinical notes, zero floats)
- BUILD_PLAN §2.4: Role-Command Authorization Matrix & Strict Pydantic Schemas
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Set, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.rhp.auth import AuthError, Session
from api.rhp.transitions import TransitionReject

# =============================================================================
# Event Detail Closed Allowlist & Validation (Invariant I11, Closure F9)
# =============================================================================

UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
IDENTIFIER_REGEX = re.compile(r"^[A-Z0-9_]{1,40}$")

ALLOWED_EVENT_DETAILS: Dict[str, Set[str]] = {
    "REFERRAL_CREATED": {"mode", "need_class", "chain_len", "profile", "mgso4"},
    "OFFER_CREATED": {"step", "facility", "source", "reason"},
    "ADVISORY_PREWARM": {"step", "facility", "source", "reason"},
    "NOTICE_SENT": {"channel", "rung", "slot"},
    "OFFER_ACKED": {"channel"},
    "RESOURCE_CONFIRMED": {"capability"},
    "OFFER_ACCEPTED": {"facility", "epoch", "reason"},
    "LEASE_GRANTED": {"facility", "epoch", "reason"},
    "LEASE_REVOKED": {"facility", "epoch", "reason"},
    "OFFER_COUNTERED": {"round", "mask"},
    "COUNTER_RESOLVED": {"confirmed"},
    "OFFER_DECLINED": {"reason", "facility"},
    "OFFER_SOFT_EXPIRED": {"step", "facility"},
    "DEADLINE_TIMEOUT": {"kind", "step"},
    "CLOSURE_OVERDUE": {"kind", "step"},
    "HANDOVER_OVERDUE": {"kind", "step"},
    "ARRIVAL_REJECTED": {"reason", "facility"},
    "ESCALATED_TO_DISPATCHER": {"reason", "facility"},
    "GRANT_REVOKED": {"reason", "facility"},
    "PIN_LOCKED": {"reason", "facility"},
    "ARRIVAL_AT_NON_OWNER": {"reason", "facility"},
    "DISPATCHER_ASSIGNED": {"facility", "reason"},
    "TR_UPDATED": {"tr_state", "source", "dwell_s"},
    "ARRIVAL_SUGGESTED": {"tr_state", "source", "dwell_s"},
    "TR_DESTINATION_CHANGE": {"facility", "reason", "accepted"},
    "CANCELLED": {"outcome", "reason"},
    "CLOSED": {"outcome", "reason"},
    "RESTORE": {"checkpoint_id"},
}


def validate_event_detail(event_type: str, detail: Dict[str, Any]) -> None:
    """Enforces Invariant I11: event.detail keys must match rhp_allowed(type).

    Values must be boolean, integer (<= 12 digits), or uppercase identifier / UUID.
    Strictly forbids floats, free-text clinical notes, and patient identifiers.
    """
    if event_type not in ALLOWED_EVENT_DETAILS:
        raise ValueError(f"Unknown event type '{event_type}'")

    allowed_keys = ALLOWED_EVENT_DETAILS[event_type]
    for key, val in detail.items():
        if key not in allowed_keys:
            raise ValueError(
                f"Forbidden detail key '{key}' for event type '{event_type}'. "
                f"Allowed keys: {sorted(allowed_keys)}"
            )

        # Strictly forbid floats (IEEE 754 canonical JSON violation)
        if isinstance(val, float):
            raise TypeError(
                f"Floating point numbers strictly forbidden in canonical event detail (key '{key}')"
            )

        if isinstance(val, bool):
            continue

        if isinstance(val, int):
            if not (-10**12 <= val <= 10**12):
                raise ValueError(f"Integer value for key '{key}' out of 12-digit bound: {val}")
            continue

        if isinstance(val, str):
            if IDENTIFIER_REGEX.match(val) or UUID_REGEX.match(val):
                continue
            raise ValueError(
                f"Invalid string value for key '{key}'. Must be uppercase identifier or UUID. "
                f"Free-text and patient names are strictly forbidden: '{val}'"
            )

        raise TypeError(f"Unsupported data type '{type(val).__name__}' for event detail key '{key}'")


# =============================================================================
# Strict Command Pydantic Models (extra='forbid', Invariants I8, I11)
# =============================================================================

class BaseCommand(BaseModel):
    """Base schema for all RHP-1 protocol commands with extra='forbid'."""

    model_config = ConfigDict(extra="forbid")

    type: str
    referral_id: Optional[UUID] = None
    expected_version: Optional[int] = Field(default=None, ge=0, description="Optimistic referral version (Invariant I8)")
    expected_epoch: Optional[int] = Field(default=None, ge=0, description="Optimistic lease epoch (Invariant I8)")
    event_id: Optional[UUID] = Field(default=None, description="Pre-minted client event UUID")
    channel: Literal["PWA", "ANDROID", "VOICE", "SMS_LINK", "PAPER", "DISPATCHER_PROXY", "SYSTEM"] = "PWA"
    proxy: bool = False
    proxy_for: Optional[UUID] = None
    reason: Optional[str] = None
    client_ts_ms: Optional[int] = None
    candidate_pin: Optional[str] = None
    secret_hash: Optional[Union[bytes, str]] = None

    def body_for_hash(self) -> Dict[str, Any]:
        """Returns canonical dictionary for idempotency hash computation (Closure F14)."""
        d = self.model_dump(mode="json", exclude={"candidate_pin"})
        return {k: v for k, v in d.items() if v is not None}

    @property
    def needs_pin(self) -> bool:
        """True if command performs a mutating clinical action requiring step-up PIN verification."""
        return False


class CreateCmd(BaseCommand):
    type: Literal["CREATE"] = "CREATE"
    referral_id: Optional[UUID] = None
    mode: Literal["SEQUENTIAL", "PARALLEL2"] = "SEQUENTIAL"
    need_class: str
    origin_facility_id: UUID
    chain: List[UUID] = Field(default_factory=list)
    mgso4_status: Literal["GIVEN", "NONE_GIVEN", "UNKNOWN"] = "UNKNOWN"
    profile_id: str = "DEMO_FAST"
    clinical_payload: Optional[Dict[str, Any]] = None


class AckCmd(BaseCommand):
    type: Literal["ACK"] = "ACK"
    referral_id: UUID
    offer_id: UUID


class ResourceConfirmCmd(BaseCommand):
    type: Literal["RESOURCE_CONFIRM"] = "RESOURCE_CONFIRM"
    referral_id: UUID
    offer_id: UUID
    capabilities: List[str]

    @property
    def needs_pin(self) -> bool:
        return True


class AcceptCmd(BaseCommand):
    type: Literal["ACCEPT"] = "ACCEPT"
    referral_id: UUID
    offer_id: Optional[UUID] = None

    @property
    def needs_pin(self) -> bool:
        return True


class CounterCmd(BaseCommand):
    type: Literal["COUNTER"] = "COUNTER"
    referral_id: UUID
    offer_id: UUID
    counter_mask: int = Field(ge=0)
    reason: Optional[str] = None

    @property
    def needs_pin(self) -> bool:
        return True


class ConfirmCounterCmd(BaseCommand):
    type: Literal["CONFIRM_COUNTER"] = "CONFIRM_COUNTER"
    referral_id: UUID
    confirmed: bool


class DeclineCmd(BaseCommand):
    type: Literal["DECLINE"] = "DECLINE"
    referral_id: UUID
    offer_id: Optional[UUID] = None
    reason: Optional[str] = None

    @property
    def needs_pin(self) -> bool:
        return True


class TimeoutCmd(BaseCommand):
    type: Literal["TIMEOUT"] = "TIMEOUT"
    referral_id: UUID
    deadline_id: UUID
    kind: str
    step: Optional[int] = None
    epoch: int = 0
    channel: Literal["SYSTEM"] = "SYSTEM"


class ArrivalRejectedCmd(BaseCommand):
    type: Literal["ARRIVAL_REJECTED"] = "ARRIVAL_REJECTED"
    referral_id: UUID
    offer_id: UUID
    reason: str


class DispatcherAssignCmd(BaseCommand):
    type: Literal["DISPATCHER_ASSIGN"] = "DISPATCHER_ASSIGN"
    referral_id: UUID
    target_facility_id: UUID
    reason: str


class TrUpdateCmd(BaseCommand):
    type: Literal["TR_UPDATE"] = "TR_UPDATE"
    referral_id: UUID
    tr_state: Literal["REQUESTED", "DISPATCHED", "EN_ROUTE", "ARRIVED", "HANDED_OVER", "TR_CANCELLED"]
    source: Literal["GPS", "MANUAL", "GEOFENCE"] = "MANUAL"
    dwell_s: Optional[int] = None


class TrDestinationChangeCmd(BaseCommand):
    type: Literal["TR_DESTINATION_CHANGE"] = "TR_DESTINATION_CHANGE"
    referral_id: UUID
    target_facility_id: UUID
    reason: str
    accepted: bool = False


class CancelCmd(BaseCommand):
    type: Literal["CANCEL"] = "CANCEL"
    referral_id: UUID
    outcome: Literal[
        "PATIENT_REFUSED",
        "TRANSPORT_CANCELLED",
        "DELIVERED_EN_ROUTE",
        "DETERIORATED_OR_DIED_PRE_HANDOVER",
    ]
    reason: Optional[str] = None


class CloseCmd(BaseCommand):
    type: Literal["CLOSE"] = "CLOSE"
    referral_id: UUID
    outcome: Literal[
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
    reason: Optional[str] = None


class RevokeGrantCmd(BaseCommand):
    type: Literal["REVOKE_GRANT"] = "REVOKE_GRANT"
    referral_id: UUID
    target_facility_id: UUID
    reason: str


COMMAND_MODELS: Dict[str, type[BaseCommand]] = {
    "CREATE": CreateCmd,
    "ACK": AckCmd,
    "RESOURCE_CONFIRM": ResourceConfirmCmd,
    "ACCEPT": AcceptCmd,
    "COUNTER": CounterCmd,
    "CONFIRM_COUNTER": ConfirmCounterCmd,
    "DECLINE": DeclineCmd,
    "TIMEOUT": TimeoutCmd,
    "ARRIVAL_REJECTED": ArrivalRejectedCmd,
    "DISPATCHER_ASSIGN": DispatcherAssignCmd,
    "TR_UPDATE": TrUpdateCmd,
    "TR_DESTINATION_CHANGE": TrDestinationChangeCmd,
    "CANCEL": CancelCmd,
    "CLOSE": CloseCmd,
    "REVOKE_GRANT": RevokeGrantCmd,
}


def parse_command(payload: Dict[str, Any]) -> BaseCommand:
    """Parses and validates a command payload using strict extra='forbid' models.

    Raises TransitionReject(422, 'INVALID_COMMAND_PAYLOAD') on validation failure.
    """
    cmd_type = payload.get("type")
    if not cmd_type or cmd_type not in COMMAND_MODELS:
        raise TransitionReject(422, "UNKNOWN_COMMAND_TYPE", f"Command type '{cmd_type}' is unrecognized")

    model_cls = COMMAND_MODELS[cmd_type]
    try:
        return model_cls(**payload)
    except Exception as e:
        raise TransitionReject(422, "INVALID_COMMAND_PAYLOAD", f"Pydantic schema validation error: {e}")


# =============================================================================
# Role-Command Authorization Matrix & Roster Validity Check (§9, Invariant I6)
# =============================================================================

def authorize(
    conn: Any,
    referral: Optional[Any],
    offer: Optional[Any],
    session: Session,
    cmd: BaseCommand,
    ts: datetime,
) -> None:
    """Enforces object-level authorization (BOLA prevention), role slot integrity,

    and active duty window constraints (Closure F9, Invariant I6).
    """
    # 1. System channel bypasses human roster checks for automated timeouts
    if cmd.channel == "SYSTEM":
        if cmd.type in ("TIMEOUT", "CLOSE"):
            return
        raise AuthError(403, "SYSTEM_CHANNEL_FORBIDDEN", "SYSTEM channel restricted to automated jobs")

    # 2. Check active duty window on roster slot (Invariant I6)
    if hasattr(conn, "db"):
        r_data = conn.db.rosters.get(str(session.roster_id))
        if not r_data:
            raise AuthError(403, "ROSTER_NOT_FOUND", "Roster slot not found")
        v_from = r_data.get("valid_from", datetime.now(timezone.utc))
        v_to = r_data.get("valid_to")
    else:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT valid_from, valid_to FROM roster WHERE id = %s;",
                (str(session.roster_id),),
            )
            r_row = cursor.fetchone()
            if not r_row:
                raise AuthError(403, "ROSTER_NOT_FOUND", "Roster slot not found")
            v_from, v_to = r_row[0], r_row[1]
        finally:
            cursor.close()

    if isinstance(v_from, str):
        v_from = datetime.fromisoformat(v_from)
    if v_from.tzinfo is None:
        v_from = v_from.replace(tzinfo=timezone.utc)

    if v_to is not None:
        if isinstance(v_to, str):
            v_to = datetime.fromisoformat(v_to)
        if v_to.tzinfo is None:
            v_to = v_to.replace(tzinfo=timezone.utc)

    if ts < v_from or (v_to is not None and ts >= v_to):
        raise AuthError(
            403,
            "ROSTER_INACTIVE",
            f"Roster slot {session.roster_id} is inactive at timestamp {ts.isoformat()}",
        )

    role = session.role_slot
    actor_fac = session.facility_id

    # 3. Dispatcher Role Privileges & Proxy Gate
    if role == "DISPATCHER":
        if cmd.type in ("DISPATCHER_ASSIGN", "CANCEL", "CLOSE", "TR_UPDATE", "TR_DESTINATION_CHANGE"):
            return
        if cmd.proxy:
            if not cmd.proxy_for:
                raise AuthError(400, "PROXY_TARGET_REQUIRED", "Dispatcher proxy commands must specify proxy_for")
            return
        raise AuthError(
            403,
            "DISPATCHER_PROXY_REQUIRED",
            f"Dispatcher must submit {cmd.type} with proxy=true and proxy_for",
        )

    # 4. Origin Facility Commands: CREATE, CONFIRM_COUNTER
    if cmd.type == "CREATE":
        if role not in ("CLINICIAN", "CMO", "NURSE"):
            raise AuthError(403, "ROLE_UNAUTHORIZED", f"Role {role} cannot create referrals")
        if actor_fac != getattr(cmd, "origin_facility_id", None):
            raise AuthError(403, "ORIGIN_FACILITY_MISMATCH", "Actor cannot create referral for foreign origin facility")
        return

    if cmd.type == "CONFIRM_COUNTER":
        if role not in ("CLINICIAN", "CMO", "NURSE"):
            raise AuthError(403, "ROLE_UNAUTHORIZED", f"Role {role} cannot confirm counter-offers")
        origin_fac = getattr(referral, "origin_facility_id", None) if referral else None
        if actor_fac != origin_fac:
            raise AuthError(403, "ORIGIN_FACILITY_MISMATCH", "Only origin facility clinician can confirm counter-offer")
        return

    # 5. Receiving Hospital Desk Commands: ACK, RESOURCE_CONFIRM, ACCEPT, COUNTER, DECLINE
    if cmd.type in ("ACK", "RESOURCE_CONFIRM", "ACCEPT", "COUNTER", "DECLINE"):
        if role not in ("NURSE", "CMO", "CONSULTANT", "JUDGE_DESK"):
            raise AuthError(403, "ROLE_UNAUTHORIZED", f"Role {role} cannot execute receiving desk command {cmd.type}")

        offer_fac = getattr(offer, "facility_id", None) if offer else None
        if not offer_fac or actor_fac != offer_fac:
            raise AuthError(
                403,
                "CROSS_FACILITY_FORBIDDEN",
                f"Actor facility {actor_fac} does not match offer receiving facility {offer_fac}",
            )
        return

    # 6. Transport Execution Commands: TR_UPDATE, TR_DESTINATION_CHANGE
    if cmd.type in ("TR_UPDATE", "TR_DESTINATION_CHANGE"):
        if role == "EMT":
            return
        # Receiving desk can confirm arrival or handover
        tr_state = getattr(cmd, "tr_state", None)
        lease_fac = getattr(referral, "lease_facility_id", None) if referral else None
        if tr_state in ("ARRIVED", "HANDED_OVER") and lease_fac and actor_fac == lease_fac:
            return
        raise AuthError(403, "ROLE_UNAUTHORIZED", f"Role {role} unauthorized for transport update")

    # 7. Terminal Commands: CLOSE, CANCEL, ARRIVAL_REJECTED
    if cmd.type == "CLOSE":
        if role == "DISPATCHER":
            return
        lease_fac = getattr(referral, "lease_facility_id", None) if referral else None
        if lease_fac and actor_fac == lease_fac and role in ("NURSE", "CMO", "CONSULTANT"):
            return
        raise AuthError(403, "ROLE_UNAUTHORIZED", f"Role {role} cannot close referral")

    if cmd.type == "CANCEL":
        if role == "DISPATCHER":
            return
        origin_fac = getattr(referral, "origin_facility_id", None) if referral else None
        if origin_fac and actor_fac == origin_fac and role in ("CLINICIAN", "CMO"):
            return
        raise AuthError(403, "ROLE_UNAUTHORIZED", f"Role {role} cannot cancel referral")

    if cmd.type == "ARRIVAL_REJECTED":
        offer_fac = getattr(offer, "facility_id", None) if offer else None
        if offer_fac and actor_fac == offer_fac and role in ("NURSE", "CMO", "CONSULTANT"):
            return
        raise AuthError(403, "ROLE_UNAUTHORIZED", f"Role {role} cannot reject arrival")

