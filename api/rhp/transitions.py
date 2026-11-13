"""ReferralHandshake Protocol RHP-1 — Canonical State Transitions Loader & Guard Evaluator.

Specification Anchors:
- Architecture §4: State Sets, 15 Commands, Guard Logic & Transitions Table [F19]
- Architecture §5: Step 6 of apply_command() Transition Guard Evaluation
- Solution v8 §4: Two Independent Tracks, Soft-Open, 9 Outcomes & Loophole Closures
- BUILD_PLAN §1.5: Declarative transitions.yaml Loader & Lookup Engine (T-F19)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field

PINNED_TRANSITIONS_RAW_SHA256 = "262d75ec6af32c6caf718027b960a302a2f39e59b235bee2f7c5832359c3af29"
PINNED_TRANSITIONS_NORM_SHA256 = "d32d3a3c7fa5b80dbca2e8b508623521246808d24bb468c4773727f566837b31"


class TransitionReject(Exception):
    """Raised when a command transition violates protocol guards or state requirements."""

    def __init__(self, http_status: int, reason_code: str, message: str = ""):
        super().__init__(f"[{http_status}] {reason_code}: {message}")
        self.http_status = http_status
        self.reason_code = reason_code
        self.message = message


class CommandTransition(BaseModel):
    """Parsed declarative transition definition for an RHP-1 protocol command."""

    model_config = ConfigDict(extra="ignore")

    name: str
    id: Optional[int] = None
    description: str = ""
    actor_roles: List[str] = Field(default_factory=list)
    channels: List[str] = Field(default_factory=list)
    requires_pin: bool = False
    needs_pin: bool = False
    pin_exemption_roles: List[str] = Field(default_factory=list)
    pre_state: Dict[str, Any] = Field(default_factory=dict)
    effects: Dict[str, Any] = Field(default_factory=dict)
    deadlines: Dict[str, Any] = Field(default_factory=dict)
    errors: Dict[Any, Any] = Field(default_factory=dict)
    allowed_outcomes: List[str] = Field(default_factory=list)
    valid_transitions: Dict[str, List[str]] = Field(default_factory=dict)
    guards: Dict[str, Any] = Field(default_factory=dict)


class TransitionsTable:
    """In-memory loader and query engine for spec/transitions.yaml."""

    def __init__(
        self,
        spec_path: Optional[Union[str, Path]] = None,
        enforce_pinned_hash: bool = False,
    ):
        self.spec_path = self._resolve_spec_path(spec_path)
        self.enforce_pinned_hash = enforce_pinned_hash
        self._raw_spec: Dict[str, Any] = {}
        self._commands: Dict[str, CommandTransition] = {}
        self.load()

    def _resolve_spec_path(self, spec_path: Optional[Union[str, Path]]) -> Path:
        if spec_path is not None:
            p = Path(spec_path)
            if p.exists():
                return p
            raise FileNotFoundError(f"transitions.yaml not found at {spec_path}")

        candidates = [
            Path(__file__).resolve().parent.parent.parent / "spec" / "transitions.yaml",
            Path("spec/transitions.yaml"),
            Path("/app/spec/transitions.yaml"),
        ]
        for cand in candidates:
            if cand.exists():
                return cand
        raise FileNotFoundError("Could not locate spec/transitions.yaml in candidate paths")

    def load(self) -> None:
        """Loads and parses spec/transitions.yaml into memory."""
        content = self.spec_path.read_bytes()

        self.raw_sha256 = hashlib.sha256(content).hexdigest()
        self.norm_sha256 = hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()

        if self.enforce_pinned_hash:
            if (
                self.raw_sha256 != PINNED_TRANSITIONS_RAW_SHA256
                and self.norm_sha256 != PINNED_TRANSITIONS_NORM_SHA256
            ):
                raise ValueError(
                    f"transitions.yaml hash mismatch! Raw: {self.raw_sha256}, Norm: {self.norm_sha256}"
                )

        text = content.decode("utf-8")
        self._raw_spec = yaml.safe_load(text)

        raw_cmds = self._raw_spec.get("commands", {})
        self._commands = {}
        for cmd_name, cmd_data in raw_cmds.items():
            parsed = CommandTransition(
                name=cmd_name,
                id=cmd_data.get("id"),
                description=cmd_data.get("description", ""),
                actor_roles=cmd_data.get("actor_roles", []),
                channels=cmd_data.get("channels", []),
                requires_pin=cmd_data.get("requires_pin", False),
                needs_pin=cmd_data.get("needs_pin", False),
                pin_exemption_roles=cmd_data.get("pin_exemption_roles", []),
                pre_state=cmd_data.get("pre_state", {}),
                effects=cmd_data.get("effects", {}),
                deadlines=cmd_data.get("deadlines", {}),
                errors=cmd_data.get("errors", {}),
                allowed_outcomes=cmd_data.get("allowed_outcomes", []),
                valid_transitions=cmd_data.get("valid_transitions", {}),
                guards=cmd_data.get("guards", {}),
            )
            self._commands[cmd_name] = parsed

    # -------------------------------------------------------------------------
    # Introspection Queries
    # -------------------------------------------------------------------------
    def get_states(self) -> Dict[str, Any]:
        """Returns the complete state inventory (handshake, transport, offer)."""
        return self._raw_spec.get("states", {})

    def get_commands(self) -> Dict[str, CommandTransition]:
        """Returns all 15 parsed commands."""
        return self._commands

    def get_outcomes(self) -> Dict[str, Any]:
        """Returns the 9 outcome definitions from Section 3."""
        return self._raw_spec.get("outcomes", {})

    def get_invariants(self) -> Dict[str, Any]:
        """Returns protocol invariants and constants from Section 2."""
        return self._raw_spec.get("invariants", {})

    def get_v7_mappings(self) -> Dict[str, Any]:
        """Returns Section 5 v7-to-RHP-1 state mapping table."""
        return self._raw_spec.get("v7_mapping") or self._raw_spec.get("v7_state_mapping", {})

    # -------------------------------------------------------------------------
    # Core Step 6 Command Lookup & Validation
    # -------------------------------------------------------------------------
    def lookup(
        self,
        cmd_type: str,
        referral: Optional[Union[Dict[str, Any], Any]] = None,
        offer: Optional[Union[Dict[str, Any], Any]] = None,
        target_tr_state: Optional[str] = None,
    ) -> CommandTransition:
        """Looks up a command and validates it against current referral and offer states.

        Args:
            cmd_type: Command name (e.g. 'CREATE', 'ACK', 'ACCEPT', 'TR_UPDATE').
            referral: Optional dictionary or referral object containing hs_state, tr_state, lease_offer_id, etc.
            offer: Optional dictionary or offer object containing status, etc.
            target_tr_state: Optional new transport state requested for TR_UPDATE.

        Returns:
            CommandTransition: The validated command specification and effects.

        Raises:
            TransitionReject: If transition preconditions, guards, or role rules are violated.
        """
        if cmd_type not in self._commands:
            raise TransitionReject(409, "UNKNOWN_COMMAND", f"Unrecognized command: {cmd_type}")

        cmd = self._commands[cmd_type]
        pre = cmd.pre_state

        # Helper extractors
        def get_field(obj: Any, key: str) -> Any:
            if obj is None:
                return None
            if isinstance(obj, dict):
                return obj.get(key)
            return getattr(obj, key, None)

        hs_state = get_field(referral, "hs_state")
        tr_state = get_field(referral, "tr_state")
        lease_offer_id = get_field(referral, "lease_offer_id")
        lease_facility_id = get_field(referral, "lease_facility_id")

        offer_status = get_field(offer, "status")

        # 1. CREATE Guard: referral must not already exist
        if cmd_type == "CREATE":
            if pre.get("referral_exists") is False and referral is not None and hs_state is not None:
                raise TransitionReject(409, "REFERRAL_ALREADY_EXISTS", "Cannot CREATE referral that already exists")
            return cmd

        # For all other commands, referral must exist if specified
        if pre.get("referral_exists") is True and referral is not None and hs_state is None:
            raise TransitionReject(409, "REFERRAL_NOT_FOUND", "Target referral does not exist")

        # 2. Terminal Handshake Guard
        if pre.get("hs_non_terminal") and hs_state in ("CANCELLED", "CLOSED"):
            raise TransitionReject(
                409,
                "ALREADY_TERMINAL",
                f"Command {cmd_type} rejected: referral is already in terminal state '{hs_state}'",
            )

        # 3. Allowed Handshake States
        allowed_hs = pre.get("hs_state") or pre.get("allowed_hs")
        if allowed_hs is not None and hs_state is not None:
            if isinstance(allowed_hs, str):
                allowed_hs = [allowed_hs]
            if hs_state not in allowed_hs:
                raise TransitionReject(
                    409,
                    "INVALID_TRANSITION",
                    f"Command {cmd_type} requires hs_state in {allowed_hs}, got '{hs_state}'",
                )

        # 4. No Active Lease Precondition (for ACCEPT, CONFIRM_COUNTER)
        if pre.get("no_active_lease") and referral is not None:
            if hs_state == "ACCEPTED" or lease_offer_id is not None or lease_facility_id is not None:
                raise TransitionReject(
                    409,
                    "LEASE_HELD",
                    f"Command {cmd_type} rejected: referral already has an active lease held",
                )

        # 5. Offer Status Precondition
        target_status = pre.get("target_offer_status")
        if target_status is not None and offer is not None and offer_status is not None:
            if isinstance(target_status, str):
                target_status = [target_status]
            if offer_status not in target_status:
                if cmd_type == "ACCEPT" and offer_status in ("TIMED_OUT", "SUPERSEDED"):
                    raise TransitionReject(
                        409,
                        "LATE_ACCEPT_REJECTED",
                        f"Offer status '{offer_status}' is no longer open for ACCEPT",
                    )
                raise TransitionReject(
                    409,
                    "INVALID_OFFER_STATE",
                    f"Command {cmd_type} requires offer status in {target_status}, got '{offer_status}'",
                )

        # 6. Transport State Transitions (TR_UPDATE) — Completely independent of hs_state (I3)
        if cmd_type == "TR_UPDATE" and target_tr_state is not None and tr_state is not None:
            valid_next = cmd.valid_transitions.get(tr_state, [])
            if target_tr_state not in valid_next:
                raise TransitionReject(
                    409,
                    "INVALID_TR_TRANSITION",
                    f"TR_UPDATE from '{tr_state}' to '{target_tr_state}' not permitted. Allowed: {valid_next}",
                )

        return cmd


# Global singleton instance
TRANSITIONS = TransitionsTable()
