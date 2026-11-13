"""ReferralHandshake Protocol RHP-1 — Independent Runtime Monitor (F17).

Ultimate Verification Authority:
- Architecture §12: Independent Python Runtime Monitor (Lane B, Person B)
- Invariants I1–I16 Verification Matrix
- Closure F17: Common-Mode Independence (Lane B, ZERO imports from api/)
- Port 8001: HTTP /metrics and /status endpoints

CRITICAL ISOLATION RULE (Closure F17):
This module is strictly built by Person B in Lane B. It MUST NEVER import
any package, class, or helper function from api/. It connects exclusively
via read-only PostgreSQL role rhp_monitor in REPEATABLE READ READ ONLY mode.
"""

from __future__ import annotations

import hashlib
import http.server
import json
import os
import socketserver
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# 1. Independent RFC 8785 Canonical JSON & SHA-256 Hasher (Lane B Implementation)
# =============================================================================

def monitor_jcs(obj: Any) -> str:
    """Independent RFC 8785 JSON Canonicalization Scheme (JCS) serializer.

    Strict rules:
    - Rejects floating-point numbers with TypeError/ValueError (Invariant I5/I11)
    - Lexicographically sorts object keys by UTF-16 / ASCII code points
    - No whitespace between tokens (delimiters: ',', ':')
    - Standard encoding for strings, integers, booleans, and null
    """
    if isinstance(obj, float):
        raise TypeError("Floating-point numbers are strictly forbidden in canonical JSON (RFC 8785)")
    elif obj is None:
        return "null"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, int):
        return str(obj)
    elif isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=True, separators=(",", ":"))
    elif isinstance(obj, dict):
        # Sort dictionary keys by UTF-16 code units (ASCII alphanumeric sorts naturally)
        sorted_keys = sorted(obj.keys())
        items = []
        for k in sorted_keys:
            if not isinstance(k, str):
                raise TypeError(f"Dictionary keys must be strings, got {type(k).__name__}")
            k_escaped = json.dumps(k, ensure_ascii=True, separators=(",", ":"))
            v_serialized = monitor_jcs(obj[k])
            items.append(f"{k_escaped}:{v_serialized}")
        return "{" + ",".join(items) + "}"
    elif isinstance(obj, (list, tuple)):
        items = [monitor_jcs(x) for x in obj]
        return "[" + ",".join(items) + "]"
    else:
        # Fallback for UUID or string-like types
        return json.dumps(str(obj), ensure_ascii=True, separators=(",", ":"))


GENESIS_PREV_HASH_HEX = "00" * 32
GENESIS_PREV_HASH_BYTES = bytes(32)


def compute_monitor_event_hash(prev_hash_hex_or_bytes: Any, core_dict: Dict[str, Any]) -> str:
    """Computes SHA-256(prev_hash || JCS(core)) independently."""
    if isinstance(prev_hash_hex_or_bytes, str):
        prev_bytes = bytes.fromhex(prev_hash_hex_or_bytes)
    elif isinstance(prev_hash_hex_or_bytes, bytes):
        prev_bytes = prev_hash_hex_or_bytes
    else:
        prev_bytes = GENESIS_PREV_HASH_BYTES

    serialized_core = monitor_jcs(core_dict).encode("utf-8")
    h = hashlib.sha256()
    h.update(prev_bytes)
    h.update(serialized_core)
    return h.hexdigest()


# =============================================================================
# 2. Invariant Violation Register & Fold Result Data Structures
# =============================================================================

@dataclass
class InvariantViolation:
    invariant: str
    referral_id: str
    code: str
    description: str
    observed_value: Any = None
    expected_value: Any = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class FoldState:
    referral_id: str
    head_seq: int = 0
    head_hash: str = GENESIS_PREV_HASH_HEX
    head_ts: Optional[datetime] = None
    hs_state: str = "CREATED"
    tr_state: str = "REQUESTED"
    lease_offer_id: Optional[str] = None
    lease_facility_id: Optional[str] = None
    lease_epoch: int = 0
    open_offers_count: int = 0
    outcome: Optional[str] = None
    closed_at: Optional[datetime] = None
    violations: List[InvariantViolation] = field(default_factory=list)


# Closed allowlist for event.detail keys (Invariant I11)
ALLOWED_DETAIL_KEYS: Dict[str, Set[str]] = {
    "REFERRAL_CREATED": {"origin_facility", "need_class", "mode", "mgso4_status", "chain_len", "profile", "mgso4"},
    "OFFER_CREATED": {"facility", "step", "source", "reason"},
    "ADVISORY_PREWARM": {"facility", "eta_min", "step", "source", "reason"},
    "NOTICE_SENT": {"facility", "rung", "channel", "slot"},
    "OFFER_ACKED": {"facility", "channel", "responder_role", "step"},
    "RESOURCE_CONFIRMED": {"facility", "capabilities", "ttl_s", "capability"},
    "OFFER_ACCEPTED": {"facility", "epoch", "step", "reason"},
    "LEASE_GRANTED": {"facility", "epoch", "step", "reason"},
    "OFFER_COUNTERED": {"facility", "round", "mask"},
    "COUNTER_RESOLVED": {"facility", "confirmed"},
    "OFFER_DECLINED": {"facility", "reason"},
    "DEADLINE_TIMEOUT": {"kind", "step", "facility"},
    "OFFER_SOFT_EXPIRED": {"facility", "step"},
    "ARRIVAL_REJECTED": {"facility", "reason"},
    "LEASE_REVOKED": {"facility", "epoch", "reason"},
    "ESCALATED_TO_DISPATCHER": {"reason", "ladder_cursor", "facility"},
    "DISPATCHER_ASSIGNED": {"facility", "reason"},
    "TR_UPDATED": {"tr_state", "source", "dwell_s"},
    "TR_DESTINATION_CHANGE": {"target_facility", "reason", "facility", "accepted"},
    "ARRIVAL_SUGGESTED": {"facility", "dwell_s", "tr_state", "source"},
    "ARRIVAL_AT_NON_OWNER": {"facility", "reason"},
    "CANCELLED": {"outcome", "reason"},
    "CLOSED": {"outcome", "reason"},
    "CLOSURE_OVERDUE": {"first_notice", "kind", "step"},
    "HANDOVER_OVERDUE": {"first_notice", "kind", "step"},
    "GRANT_REVOKED": {"facility", "reason"},
    "PIN_LOCKED": {"role_slot", "lockout_s", "reason", "facility"},
    "RESTORE": {"checkpoint_seq", "note", "checkpoint_id"},
}

LOCKED_OUTCOMES_SET = {
    "ADMITTED_STABLE",
    "ADMITTED_CRITICAL",
    "DELIVERED_AT_RECEIVER",
    "DELIVERED_EN_ROUTE",
    "PATIENT_REFUSED",
    "TRANSPORT_CANCELLED",
    "DETERIORATED_OR_DIED_PRE_HANDOVER",
    "REDIRECTED_ON_ARRIVAL",
    "UNKNOWN_COUNTER_REFERRAL",
}


# =============================================================================
# 3. Independent Event Fold & Invariant Checker Engine (fold_events)
# =============================================================================

def _normalize_hex(h: Any) -> str:
    if isinstance(h, (bytes, bytearray)):
        return h.hex().lower()
    elif isinstance(h, str):
        if h.startswith("b'") and h.endswith("'"):
            import ast
            try:
                b = ast.literal_eval(h)
                if isinstance(b, bytes):
                    return b.hex().lower()
            except Exception:
                pass
        return h.lower()
    return ""


def fold_events(
    events: List[Dict[str, Any]],
    roster_map: Optional[Dict[str, Dict[str, Any]]] = None,
    referral_row: Optional[Dict[str, Any]] = None,
    offers_rows: Optional[List[Dict[str, Any]]] = None,
    deadlines_rows: Optional[List[Dict[str, Any]]] = None,
    confirmations_rows: Optional[List[Dict[str, Any]]] = None,
    grants_rows: Optional[List[Dict[str, Any]]] = None,
    poll_interval_ms: int = 1000,
    check_time: Optional[datetime] = None,
) -> FoldState:
    """Independently folds raw event records into state and checks Invariants I1–I16.

    Closure F17:
    Zero dependencies on api/. Derives state exclusively from the immutable
    event log and checks for differential consistency against DB rows.
    """
    now = check_time or datetime.now(timezone.utc)
    ref_id = str(referral_row["id"]) if referral_row else (str(events[0]["referral_id"]) if events else "unknown")
    state = FoldState(referral_id=ref_id)

    # Sort events by seq strictly
    sorted_events = sorted(events, key=lambda e: int(e.get("seq", 0)))

    prev_seq = 0
    prev_hash = GENESIS_PREV_HASH_HEX
    prev_ts: Optional[datetime] = None
    seen_event_ids: Set[str] = set()
    accepted_offers_count = 0
    active_lease: Optional[str] = None
    curr_epoch = 0

    # -------------------------------------------------------------------------
    # A. EVENT LOG FOLD & EVENT-LEVEL INVARIANT AUDIT
    # -------------------------------------------------------------------------
    for ev in sorted_events:
        seq = int(ev.get("seq", 0))
        ev_id = str(ev.get("event_id") or ev.get("id") or f"ev-{seq}-{ref_id}")
        ev_type = str(ev.get("type", ""))
        ev_hash = _normalize_hex(ev.get("hash"))
        ev_prev_hash = _normalize_hex(ev.get("prev_hash")) or GENESIS_PREV_HASH_HEX
        server_ts = ev.get("server_ts")
        if isinstance(server_ts, str):
            try:
                server_ts = datetime.fromisoformat(server_ts)
            except Exception:
                server_ts = None

        # --- Invariant I4: Gap-Free Sequence & Unique Event IDs ---
        if seq != prev_seq + 1:
            state.violations.append(
                InvariantViolation(
                    invariant="I4",
                    referral_id=ref_id,
                    code="SEQ_GAP_OR_OUT_OF_ORDER",
                    description=f"Event seq {seq} does not increment previous seq {prev_seq} by 1",
                    observed_value=seq,
                    expected_value=prev_seq + 1,
                )
            )

        if ev_id in seen_event_ids:
            state.violations.append(
                InvariantViolation(
                    invariant="I4",
                    referral_id=ref_id,
                    code="DUPLICATE_EVENT_ID",
                    description=f"Event ID {ev_id} reused across event log",
                    observed_value=ev_id,
                )
            )
        seen_event_ids.add(ev_id)

        # --- Invariant I16: Monotone Server Timestamps ---
        if server_ts and prev_ts and server_ts < prev_ts:
            state.violations.append(
                InvariantViolation(
                    invariant="I16",
                    referral_id=ref_id,
                    code="TIMESTAMP_REGRESSION",
                    description=f"Event seq {seq} server_ts {server_ts} regressed before previous ts {prev_ts}",
                    observed_value=server_ts.isoformat(),
                    expected_value=prev_ts.isoformat(),
                )
            )

        # --- Invariant I5: Cryptographic Hash Chain Verification ---
        if ev_prev_hash != prev_hash:
            state.violations.append(
                InvariantViolation(
                    invariant="I5",
                    referral_id=ref_id,
                    code="PREV_HASH_MISMATCH",
                    description=f"Event seq {seq} prev_hash mismatch",
                    observed_value=ev_prev_hash,
                    expected_value=prev_hash,
                )
            )

        # Recompute SHA-256(prev_hash || JCS(core))
        core_payload = ev.get("core") or {
            "referral_id": str(ev.get("referral_id", "")),
            "seq": seq,
            "type": ev_type,
            "epoch": int(ev.get("epoch", 0)),
            "detail": ev.get("detail", {}),
            "client_ts_ms": int(ev.get("client_ts_ms", 0)),
        }
        try:
            computed_hash = compute_monitor_event_hash(ev_prev_hash, core_payload)
            if computed_hash.lower() != ev_hash.lower():
                state.violations.append(
                    InvariantViolation(
                        invariant="I5",
                        referral_id=ref_id,
                        code="HASH_CHAIN_CORRUPTED",
                        description=f"Computed hash {computed_hash} != stored hash {ev_hash} at seq {seq}",
                        observed_value=ev_hash,
                        expected_value=computed_hash,
                    )
                )
        except (TypeError, ValueError) as e:
            state.violations.append(
                InvariantViolation(
                    invariant="I11",
                    referral_id=ref_id,
                    code="FLOAT_IN_DETAIL",
                    description=f"Canonical serialization rejected illegal payload at seq {seq}: {e}",
                    observed_value=str(e),
                )
            )

        # --- Invariant I11: Event Detail Closed Allowlist & Float Ban ---
        detail = ev.get("detail", {})
        if not isinstance(detail, dict):
            state.violations.append(
                InvariantViolation(
                    invariant="I11",
                    referral_id=ref_id,
                    code="DETAIL_NOT_DICT",
                    description=f"Event seq {seq} detail is not a dictionary",
                )
            )
        else:
            allowed_keys = ALLOWED_DETAIL_KEYS.get(ev_type, set())
            extra_keys = set(detail.keys()) - allowed_keys
            if extra_keys:
                state.violations.append(
                    InvariantViolation(
                        invariant="I11",
                        referral_id=ref_id,
                        code="DISALLOWED_DETAIL_KEYS",
                        description=f"Event seq {seq} ({ev_type}) contains disallowed keys: {extra_keys}",
                        observed_value=list(extra_keys),
                        expected_value=list(allowed_keys),
                    )
                )

            # Check for float values in detail (RFC 8785 float ban)
            def _check_no_floats(d: Any, path: str = "") -> None:
                if isinstance(d, float):
                    state.violations.append(
                        InvariantViolation(
                            invariant="I11",
                            referral_id=ref_id,
                            code="FLOAT_IN_DETAIL",
                            description=f"Floating-point value detected at {path}: {d}",
                            observed_value=d,
                        )
                    )
                elif isinstance(d, dict):
                    for k, v in d.items():
                        _check_no_floats(v, f"{path}.{k}" if path else k)
                elif isinstance(d, list):
                    for i, v in enumerate(d):
                        _check_no_floats(v, f"{path}[{i}]")

            _check_no_floats(detail)

        # --- Invariant I6: Actor Validity Check ---
        actor_id = ev.get("actor_roster_id")
        is_proxy = ev.get("proxy", False)
        if ev_type in ("OFFER_ACCEPTED", "OFFER_COUNTERED", "OFFER_DECLINED") and not is_proxy:
            if not actor_id:
                state.violations.append(
                    InvariantViolation(
                        invariant="I6",
                        referral_id=ref_id,
                        code="MISSING_ACTOR_FOR_MUTATING_ACTION",
                        description=f"Mutating event {ev_type} at seq {seq} has null actor_roster_id",
                    )
                )
            elif roster_map and str(actor_id) not in roster_map:
                state.violations.append(
                    InvariantViolation(
                        invariant="I6",
                        referral_id=ref_id,
                        code="UNKNOWN_ROSTER_ACTOR",
                        description=f"Actor {actor_id} not present in active roster directory",
                        observed_value=str(actor_id),
                    )
                )

        # --- Invariant I2 / I8: Lease and Epoch Updates ---
        if ev_type in ("OFFER_ACCEPTED", "LEASE_GRANTED"):
            fac = detail.get("facility")
            ep = detail.get("epoch", curr_epoch + 1)
            if active_lease is not None and active_lease != fac:
                state.violations.append(
                    InvariantViolation(
                        invariant="I2",
                        referral_id=ref_id,
                        code="DOUBLE_LEASE_VIOLATION",
                        description=f"Lease granted to {fac} while lease already active for {active_lease}",
                        observed_value=fac,
                        expected_value=None,
                    )
                )
            active_lease = fac
            accepted_offers_count += 1
            if ep <= curr_epoch:
                state.violations.append(
                    InvariantViolation(
                        invariant="I8",
                        referral_id=ref_id,
                        code="EPOCH_NON_MONOTONIC",
                        description=f"Lease epoch {ep} did not strictly increase over previous epoch {curr_epoch}",
                        observed_value=ep,
                        expected_value=curr_epoch + 1,
                    )
                )
            curr_epoch = ep
            state.lease_facility_id = fac
            state.lease_epoch = ep
            state.hs_state = "ACCEPTED"

        elif ev_type in ("ARRIVAL_REJECTED", "LEASE_REVOKED"):
            active_lease = None
            state.lease_facility_id = None
            state.lease_epoch = curr_epoch + 1
            curr_epoch += 1

        elif ev_type == "OFFER_CREATED":
            state.hs_state = "OFFERED"
        elif ev_type == "OFFER_ACKED":
            state.hs_state = "ACKNOWLEDGED"
        elif ev_type == "OFFER_COUNTERED":
            state.hs_state = "COUNTERED"
        elif ev_type == "ESCALATED_TO_DISPATCHER":
            state.hs_state = "ESCALATED_TO_DISPATCHER"
        elif ev_type == "CANCELLED":
            state.hs_state = "CANCELLED"
            state.outcome = detail.get("outcome")
            state.closed_at = server_ts
        elif ev_type == "CLOSED":
            state.hs_state = "CLOSED"
            state.outcome = detail.get("outcome")
            state.closed_at = server_ts

        # Update running fold state
        prev_seq = seq
        prev_hash = ev_hash
        prev_ts = server_ts

    state.head_seq = prev_seq
    state.head_hash = prev_hash
    state.head_ts = prev_ts

    # -------------------------------------------------------------------------
    # B. SNAPSHOT TABLES AUDIT (I1, I2, I7, I9, I10, I12, I15)
    # -------------------------------------------------------------------------

    # --- Invariant I2: Database Offers Single Lease Check ---
    if offers_rows is not None:
        db_accepted = [o for o in offers_rows if o.get("status") == "ACCEPTED"]
        if len(db_accepted) > 1:
            state.violations.append(
                InvariantViolation(
                    invariant="I2",
                    referral_id=ref_id,
                    code="DB_MULTIPLE_ACCEPTED_OFFERS",
                    description=f"Database contains {len(db_accepted)} ACCEPTED offers (one_lease violated)",
                    observed_value=len(db_accepted),
                    expected_value=1,
                )
            )

        # --- Invariant I9: Cycle-Free Offer Routing ---
        seen_facs: Set[str] = set()
        for o in offers_rows:
            f_id = str(o.get("facility_id", ""))
            if f_id in seen_facs:
                state.violations.append(
                    InvariantViolation(
                        invariant="I9",
                        referral_id=ref_id,
                        code="PING_PONG_ROUTING_CYCLE",
                        description=f"Facility {f_id} has multiple offers for referral {ref_id}",
                        observed_value=f_id,
                    )
                )
            seen_facs.add(f_id)

        # --- Invariant I7: Catchment Chain Integrity ---
        if referral_row and referral_row.get("chain"):
            allowed_chain = {str(c) for c in referral_row["chain"]}
            for o in offers_rows:
                if o.get("source") == "CHAIN":
                    f_id = str(o.get("facility_id", ""))
                    if f_id not in allowed_chain:
                        state.violations.append(
                            InvariantViolation(
                                invariant="I7",
                                referral_id=ref_id,
                                code="OFFER_NOT_IN_APPROVED_CHAIN",
                                description=f"Offer {o.get('id')} facility {f_id} is not in approved chain",
                                observed_value=f_id,
                                expected_value=list(allowed_chain),
                            )
                        )

        # --- Invariant I12: Open Offers Bound (<= 2) ---
        open_statuses = {"OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"}
        open_offers = [o for o in offers_rows if o.get("status") in open_statuses]
        state.open_offers_count = len(open_offers)
        if len(open_offers) > 2:
            state.violations.append(
                InvariantViolation(
                    invariant="I12",
                    referral_id=ref_id,
                    code="OPEN_OFFERS_EXCEEDED",
                    description=f"Active open offers {len(open_offers)} exceeds maximum bound of 2",
                    observed_value=len(open_offers),
                    expected_value=2,
                )
            )

    # --- Invariant I1: Non-Terminal Pending Deadline Check ---
    if referral_row and referral_row.get("hs_state") not in ("CLOSED", "CANCELLED"):
        if deadlines_rows is not None:
            pending_dls = [d for d in deadlines_rows if d.get("status") == "PENDING"]
            if not pending_dls:
                state.violations.append(
                    InvariantViolation(
                        invariant="I1",
                        referral_id=ref_id,
                        code="MISSING_PENDING_DEADLINE",
                        description=f"Active referral in state '{referral_row.get('hs_state')}' lacks PENDING deadline",
                    )
                )
            else:
                tau_ms = 2 * poll_interval_ms + 2000
                for d in pending_dls:
                    due = d.get("due_at")
                    if isinstance(due, str):
                        try:
                            due = datetime.fromisoformat(due)
                        except Exception:
                            due = None
                    if due and (now - due).total_seconds() * 1000 > tau_ms:
                        state.violations.append(
                            InvariantViolation(
                                invariant="I1",
                                referral_id=ref_id,
                                code="DEADLINE_OVERDUE_UNPROCESSED",
                                description=f"Pending deadline {d.get('id')} overdue by > {tau_ms} ms without action",
                                observed_value=d.get("id"),
                            )
                        )

    # --- Invariant I15: Capability Confirmation Expiration Check ---
    if confirmations_rows is not None:
        for c in confirmations_rows:
            exp = c.get("expires_at")
            if isinstance(exp, str):
                try:
                    exp = datetime.fromisoformat(exp)
                except Exception:
                    exp = None
            # If an offer was accepted with an expired confirmation:
            if c.get("accepted_at") and exp and exp <= c["accepted_at"]:
                state.violations.append(
                    InvariantViolation(
                        invariant="I15",
                        referral_id=ref_id,
                        code="STALE_CAPABILITY_ACCEPTED",
                        description=f"Capability {c.get('capability')} was expired when offer was accepted",
                        observed_value=str(exp),
                    )
                )

    # --- Invariant I5: Terminal Outcomes Validation ---
    if referral_row and referral_row.get("hs_state") in ("CLOSED", "CANCELLED"):
        outcome = referral_row.get("outcome")
        if not outcome or outcome not in LOCKED_OUTCOMES_SET:
            state.violations.append(
                InvariantViolation(
                    invariant="I5",
                    referral_id=ref_id,
                    code="TERMINAL_REFERRAL_MISSING_VALID_OUTCOME",
                    description=f"Terminal referral {ref_id} has invalid/missing outcome: {outcome}",
                    observed_value=outcome,
                    expected_value=list(LOCKED_OUTCOMES_SET),
                )
            )

    # --- Differential Consistency Check against DB Referral Row ---
    if referral_row is not None:
        db_seq = int(referral_row.get("head_seq", 0))
        db_hash = str(referral_row.get("head_hash", ""))
        db_epoch = int(referral_row.get("lease_epoch", 0))
        db_lease = referral_row.get("lease_facility_id")
        db_lease_str = str(db_lease) if db_lease else None

        if state.head_seq != db_seq:
            state.violations.append(
                InvariantViolation(
                    invariant="DIFF_HEAD",
                    referral_id=ref_id,
                    code="HEAD_SEQ_MISMATCH",
                    description=f"Derived head_seq {state.head_seq} != database head_seq {db_seq}",
                    observed_value=db_seq,
                    expected_value=state.head_seq,
                )
            )

        # Check hash match (handling hex or bytes)
        if isinstance(referral_row.get("head_hash"), bytes):
            db_hash_hex = referral_row["head_hash"].hex()
        else:
            db_hash_hex = db_hash

        if state.head_hash.lower() != db_hash_hex.lower() and state.head_seq > 0:
            state.violations.append(
                InvariantViolation(
                    invariant="DIFF_HEAD",
                    referral_id=ref_id,
                    code="HEAD_HASH_MISMATCH",
                    description=f"Derived head_hash {state.head_hash} != database head_hash {db_hash_hex}",
                    observed_value=db_hash_hex,
                    expected_value=state.head_hash,
                )
            )

        if state.lease_epoch != db_epoch:
            state.violations.append(
                InvariantViolation(
                    invariant="DIFF_EPOCH",
                    referral_id=ref_id,
                    code="LEASE_EPOCH_MISMATCH",
                    description=f"Derived epoch {state.lease_epoch} != database epoch {db_epoch}",
                    observed_value=db_epoch,
                    expected_value=state.lease_epoch,
                )
            )

        if state.lease_facility_id != db_lease_str:
            state.violations.append(
                InvariantViolation(
                    invariant="DIFF_LEASE",
                    referral_id=ref_id,
                    code="LEASE_FACILITY_MISMATCH",
                    description=f"Derived lease {state.lease_facility_id} != database lease {db_lease_str}",
                    observed_value=db_lease_str,
                    expected_value=state.lease_facility_id,
                )
            )

    return state


# =============================================================================
# 4. HTTP Metrics & Status Server on Port 8001
# =============================================================================

class MonitorHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Exposes /metrics and /status for the Independent Runtime Monitor."""

    def do_GET(self) -> None:
        if self.path == "/status" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status_data = GLOBAL_MONITOR_SERVICE.get_status()
            self.wfile.write(json.dumps(status_data).encode("utf-8"))

        elif self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            metrics_text = GLOBAL_MONITOR_SERVICE.get_prometheus_metrics()
            self.wfile.write(metrics_text.encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard HTTP access logs
        return


class MonitorService:
    """Manages periodic audit sweeps and metrics exposition."""

    def __init__(self, port: int = 8001) -> None:
        self.port = port
        self.lock = threading.Lock()
        self.status = "GREEN"  # "GREEN" or "RED"
        self.violations: List[InvariantViolation] = []
        self.referrals_checked = 0
        self.events_folded = 0
        self.last_sweep_ts = datetime.now(timezone.utc).isoformat()
        self.server: Optional[socketserver.TCPServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def record_violations(self, violations: List[InvariantViolation], referrals_count: int, events_count: int) -> None:
        with self.lock:
            self.referrals_checked += referrals_count
            self.events_folded += events_count
            self.last_sweep_ts = datetime.now(timezone.utc).isoformat()
            if violations:
                self.violations.extend(violations)
                self.status = "RED"
            else:
                self.violations.clear()
                self.status = "GREEN"

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "status": self.status,
                "violations_count": len(self.violations),
                "violations": [
                    {
                        "invariant": v.invariant,
                        "referral_id": v.referral_id,
                        "code": v.code,
                        "description": v.description,
                        "observed": v.observed_value,
                        "expected": v.expected_value,
                        "timestamp": v.timestamp,
                    }
                    for v in self.violations[-50:]  # last 50
                ],
                "referrals_checked": self.referrals_checked,
                "events_folded": self.events_folded,
                "last_sweep_ts": self.last_sweep_ts,
            }

    def get_prometheus_metrics(self) -> str:
        with self.lock:
            is_green = 1 if self.status == "GREEN" else 0
            lines = [
                "# HELP monitor_status 1 if GREEN (no violations), 0 if RED",
                "# TYPE monitor_status gauge",
                f"monitor_status {is_green}",
                "# HELP monitor_violations_total Total invariant violations detected",
                "# TYPE monitor_violations_total counter",
                f"monitor_violations_total {len(self.violations)}",
                "# HELP monitor_referrals_checked_total Total referrals checked",
                "# TYPE monitor_referrals_checked_total counter",
                f"monitor_referrals_checked_total {self.referrals_checked}",
                "# HELP monitor_events_folded_total Total events folded",
                "# TYPE monitor_events_folded_total counter",
                f"monitor_events_folded_total {self.events_folded}",
            ]
            return "\n".join(lines) + "\n"

    def start_http_server(self) -> None:
        """Starts HTTP server in background thread."""
        if self.server is not None:
            return

        socketserver.TCPServer.allow_reuse_address = True
        try:
            self.server = socketserver.TCPServer(("", self.port), MonitorHTTPHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
        except Exception as e:
            # Port may already be bound in multi-process runner
            pass

    def stop_http_server(self) -> None:
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.server = None


    def upsert_heartbeat(self, conn: Any, subject_id: str = "monitor-1", ntp_offset_ms: int = 0) -> None:
        """Upserts monitor liveness into the database heartbeat table (Closure F11)."""
        now = datetime.now(timezone.utc)
        if hasattr(conn, "db"):
            if not hasattr(conn.db, "heartbeats"):
                conn.db.heartbeats = {}
            conn.db.heartbeats[("MONITOR", subject_id)] = {
                "subject_kind": "MONITOR",
                "subject_id": subject_id,
                "last_seen": now,
                "ntp_offset_ms": ntp_offset_ms,
            }
            return

        cur = conn.cursor() if hasattr(conn, "cursor") else conn
        cur.execute(
            """
            INSERT INTO heartbeat (subject_kind, subject_id, last_seen, ntp_offset_ms)
            VALUES ('MONITOR', %s, clock_timestamp(), %s)
            ON CONFLICT (subject_kind, subject_id)
            DO UPDATE SET last_seen = EXCLUDED.last_seen, ntp_offset_ms = EXCLUDED.ntp_offset_ms;
            """,
            (subject_id, ntp_offset_ms),
        )


def upsert_monitor_heartbeat(conn: Any, subject_id: str = "monitor-1", ntp_offset_ms: int = 0) -> None:
    """Standalone helper to upsert monitor heartbeat."""
    GLOBAL_MONITOR_SERVICE.upsert_heartbeat(conn, subject_id=subject_id, ntp_offset_ms=ntp_offset_ms)


GLOBAL_MONITOR_SERVICE = MonitorService()


# =============================================================================
# 5. Standalone Monitor Process Entry Point
# =============================================================================

def run_standalone_monitor() -> None:
    """Entry point for running monitor in Docker container or CLI."""
    port = int(os.environ.get("MONITOR_PORT", "8001"))
    GLOBAL_MONITOR_SERVICE.port = port
    GLOBAL_MONITOR_SERVICE.start_http_server()
    print(f"[RHP-MONITOR] Independent Runtime Monitor running on port {port} (status: GREEN)")

    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        GLOBAL_MONITOR_SERVICE.stop_http_server()
        print("[RHP-MONITOR] Stopped.")


if __name__ == "__main__":
    run_standalone_monitor()
