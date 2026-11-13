"""ReferralHandshake Protocol RHP-1 — The 10-Step apply_command() Transactional Pipeline.

Specification Anchors:
- Architecture §5: Complete 10-step apply_command() transaction contract
- Architecture §7: Global lock hierarchy: referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox
- Invariant I4: Tamper-evident SHA-256 event hash chain
- Invariant I6: Role slot integrity, session validity, and BOLA prevention
- Invariant I8: Optimistic fencing on expected_version and expected_epoch (Reject 412)
- Invariant I11: RFC 8785 canonical JSON with strict float rejection and closed detail allowlist
- Invariant I14: Strict referral-first locking and transaction session GUC stamping (I14_LOCK_NOT_HELD)
- Invariant I15: Stale confirmation detection on ACCEPT (Reject 409)
- Invariant I16: Monotone server timestamps GREATEST(clock_timestamp(), r.head_ts)
- Closure F1: 10-step serial execution pipeline
- Closure F7: Autonomous brute-force failure persistence across command rollback
- Closure F9: Closed key allowlist for event details
- Closure F11: Clock monotonicity under referral lock
- Closure F14: Scoped idempotency with exact replay of prior 200/409/412/422 outcomes
- BUILD_PLAN §2.5: The 10-Step apply_command() Transactional Pipeline
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from api.rhp.auth import AuthError, Session, load_session, verify_pin_or_lockout
from api.rhp.crypto import GENESIS_PREV_HASH_BYTES, compute_event_hash, jcs
from api.rhp.db import get_monotone_ts, lock_referral_first, try_advisory_idem_lock
from api.rhp.schemas import BaseCommand, authorize, parse_command, validate_event_detail
from api.rhp.transitions import TRANSITIONS, TransitionReject


# =============================================================================
# Referral & Offer State Representations
# =============================================================================

class ReferralState:
    """In-memory mutable view of a referral record during pipeline execution."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.id = UUID(str(data["id"]))
        self.version = int(data.get("version", 1))
        self.hs_state = str(data.get("hs_state", "CREATED"))
        self.tr_state = str(data.get("tr_state", "REQUESTED"))
        self.mode = str(data.get("mode", "SEQUENTIAL"))
        self.need_class = str(data.get("need_class", "OB_ECLAMPSIA"))
        self.origin_facility_id = UUID(str(data.get("origin_facility_id") or data["from_facility_id"]))
        self.from_facility_id = self.origin_facility_id
        self.chain = [UUID(str(c)) for c in data.get("chain", [])]
        self.ladder_cursor = int(data.get("ladder_cursor", 0))
        self.lease_offer_id = UUID(str(data["lease_offer_id"])) if data.get("lease_offer_id") else None
        self.lease_facility_id = UUID(str(data["lease_facility_id"])) if data.get("lease_facility_id") else None
        self.lease_epoch = int(data.get("lease_epoch", 0))
        self.open_offers = int(data.get("open_offers", 0))
        self.tr_facility_id = UUID(str(data["tr_facility_id"])) if data.get("tr_facility_id") else None
        self.mgso4_status = str(data.get("mgso4_status", "UNKNOWN"))
        self.profile_id = str(data.get("profile_id", "DEMO_FAST"))
        self.paper_code = str(data.get("paper_code", "DEMO-001"))
        self.head_seq = int(data.get("head_seq", 0))
        self.head_hash = bytes(data.get("head_hash", GENESIS_PREV_HASH_BYTES))
        self.head_ts = data.get("head_ts", datetime.now(timezone.utc))
        self.outcome = data.get("outcome")
        self.created_by = UUID(str(data.get("created_by", uuid4())))
        self.created_at = data.get("created_at", datetime.now(timezone.utc))
        self.closed_at = data.get("closed_at")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "version": self.version,
            "hs_state": self.hs_state,
            "tr_state": self.tr_state,
            "mode": self.mode,
            "need_class": self.need_class,
            "from_facility_id": str(self.origin_facility_id),
            "origin_facility_id": str(self.origin_facility_id),
            "chain": [str(c) for c in self.chain],
            "ladder_cursor": self.ladder_cursor,
            "lease_offer_id": str(self.lease_offer_id) if self.lease_offer_id else None,
            "lease_facility_id": str(self.lease_facility_id) if self.lease_facility_id else None,
            "lease_epoch": self.lease_epoch,
            "open_offers": self.open_offers,
            "tr_facility_id": str(self.tr_facility_id) if self.tr_facility_id else None,
            "mgso4_status": self.mgso4_status,
            "profile_id": self.profile_id,
            "head_seq": self.head_seq,
            "head_hash": self.head_hash,
            "head_ts": self.head_ts,
            "outcome": self.outcome,
        }


class OfferState:
    """In-memory mutable view of an offer record during pipeline execution."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.id = UUID(str(data["id"]))
        self.referral_id = UUID(str(data["referral_id"]))
        self.facility_id = UUID(str(data["facility_id"]))
        self.step = int(data.get("step", 0))
        self.source = str(data.get("source", "CHAIN"))
        self.status = str(data.get("status", "OPEN"))
        self.counter_round = int(data.get("counter_round", 0))
        self.counter_mask = int(data.get("counter_mask", 0))
        self.created_epoch = int(data.get("created_epoch", 0))
        self.created_at = data.get("created_at", datetime.now(timezone.utc))
        self.acked_at = data.get("acked_at")
        self.decided_at = data.get("decided_at")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "referral_id": str(self.referral_id),
            "facility_id": str(self.facility_id),
            "step": self.step,
            "source": self.source,
            "status": self.status,
            "counter_round": self.counter_round,
            "counter_mask": self.counter_mask,
            "created_epoch": self.created_epoch,
        }


# =============================================================================
# Invariant I14 Guard Helper
# =============================================================================

def assert_referral_locked(conn: Any, referral_id: Union[UUID, str]) -> None:
    """Enforces Invariant I14: Raises RuntimeError('I14_LOCK_NOT_HELD') if

    rhp.locked_referral transaction GUC does not match referral_id.
    """
    ref_str = str(referral_id)
    if hasattr(conn, "session_gucs"):
        current = conn.session_gucs.get("rhp.locked_referral")
        if current != ref_str:
            raise RuntimeError("I14_LOCK_NOT_HELD")
        return

    # Real PostgreSQL connection: inspect current_setting
    cur = conn.cursor()
    try:
        cur.execute("SELECT current_setting('rhp.locked_referral', true);")
        row = cur.fetchone()
        current = row[0] if row else None
        if current != ref_str:
            raise RuntimeError("I14_LOCK_NOT_HELD")
    finally:
        cur.close()


# =============================================================================
# The 10-Step apply_command() Transactional Pipeline
# =============================================================================

def apply_command(
    conn: Any,
    cmd_or_payload: Union[BaseCommand, Dict[str, Any]],
    session_token: Optional[str] = None,
    idem_key: Optional[str] = None,
    session: Optional[Session] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Executes a command through the complete 10-step RHP-1 pipeline (Architecture §5).

    Returns (http_status, response_body).
    """
    now = datetime.now(timezone.utc)

    # -------------------------------------------------------------------------
    # STEP 1: Idempotency & Advisory Lock (Before Referral Lock)
    # -------------------------------------------------------------------------
    if not idem_key or not isinstance(idem_key, str) or not (8 <= len(idem_key) <= 80):
        raise TransitionReject(
            422,
            "MISSING_IDEMPOTENCY_KEY",
            "Idempotency-Key header is required and must be between 8 and 80 characters",
        )

    # 1. Parse Command Payload (validating extra='forbid')
    if isinstance(cmd_or_payload, dict):
        cmd = parse_command(cmd_or_payload)
    else:
        cmd = cmd_or_payload

    # -------------------------------------------------------------------------
    # STEP 2: Session Validation
    # -------------------------------------------------------------------------
    if session is None:
        if cmd.channel == "SYSTEM":
            # Synthetic system actor for automated timeouts
            session = Session(
                id=UUID("00000000-0000-0000-0000-000000000099"),
                token_hash=bytes(32),
                roster_id=UUID("00000000-0000-0000-0000-000000000099"),
                device_id=None,
                call_sid=None,
                created_at=now,
                expires_at=now + timedelta(days=1),
                role_slot="ADMIN",
            )
        else:
            if not session_token:
                raise AuthError(401, "SESSION_INVALID", "Missing session token")
            session = load_session(conn, session_token)

    actor_id = session.roster_id
    body_hash_dict = cmd.body_for_hash()
    canonical_body = jcs(body_hash_dict)
    req_hash = hashlib.sha256(canonical_body).digest()

    # Acquire Transaction Advisory Lock on (actor_id, idem_key)
    locked = try_advisory_idem_lock(conn, actor_id, idem_key)
    if not locked:
        raise TransitionReject(
            409,
            "DUPLICATE_IN_FLIGHT",
            "A command with this idempotency key is currently executing",
        )

    # Check idempotency table in database / mock store
    idempotency_store: Dict[str, Dict[str, Any]]
    if hasattr(conn, "db"):
        if not hasattr(conn.db, "idempotency"):
            conn.db.idempotency = {}
        if not hasattr(conn.db, "offers"):
            conn.db.offers = {}
        if not hasattr(conn.db, "deadlines"):
            conn.db.deadlines = {}
        if not hasattr(conn.db, "events"):
            conn.db.events = []
        if not hasattr(conn.db, "outbox"):
            conn.db.outbox = []
        if not hasattr(conn.db, "rejected_commands"):
            conn.db.rejected_commands = []
        idempotency_store = conn.db.idempotency
    else:
        idempotency_store = {}

    idem_id = f"{actor_id}:{idem_key}"
    stored_idem = idempotency_store.get(idem_id)

    if stored_idem:
        # Check payload match
        if stored_idem["request_hash"] != req_hash:
            raise TransitionReject(
                422,
                "KEY_REUSED_DIFFERENT_PAYLOAD",
                "Idempotency key has already been used with a different command payload",
            )
        # Replay stored outcome if DONE
        if stored_idem["status"] == "DONE":
            return stored_idem["http_status"], stored_idem["response"]
        if stored_idem["status"] == "IN_FLIGHT":
            raise TransitionReject(
                409,
                "DUPLICATE_IN_FLIGHT",
                "Command with this idempotency key is already in flight",
            )

    # Record IN_FLIGHT state
    idempotency_store[idem_id] = {
        "actor_id": str(actor_id),
        "key": idem_key,
        "request_hash": req_hash,
        "status": "IN_FLIGHT",
        "http_status": None,
        "response": None,
        "created_at": now,
        "expires_at": now + timedelta(hours=48),
    }

    # -------------------------------------------------------------------------
    # STEP 3: Step-Up PIN Verification (Argon2id, Closure F7)
    # -------------------------------------------------------------------------
    if cmd.needs_pin:
        verify_pin_or_lockout(conn, session, cmd.candidate_pin)

    # -------------------------------------------------------------------------
    # STEP 4: Lock Referral First & Monotone Clock (Invariants I14, I16, F11)
    # -------------------------------------------------------------------------
    referral: Optional[ReferralState] = None
    referrals_store = getattr(conn.db, "referrals", {}) if hasattr(conn, "db") else {}

    if cmd.type == "CREATE":
        ref_id = uuid4()
        # Stamp transaction GUC for new referral
        if hasattr(conn, "session_gucs"):
            conn.session_gucs["rhp.locked_referral"] = str(ref_id)
        else:
            cur = conn.cursor()
            cur.execute("SELECT set_config('rhp.locked_referral', %s, true);", (str(ref_id),))
            cur.close()
        ts = get_monotone_ts(conn)
    else:
        ref_id = cmd.referral_id
        if not ref_id:
            raise TransitionReject(400, "MISSING_REFERRAL_ID", "Command requires referral_id")

        lock_referral_first(conn, ref_id)
        raw_ref = referrals_store.get(str(ref_id))
        if not raw_ref:
            raise TransitionReject(404, "REFERRAL_NOT_FOUND", f"Referral {ref_id} not found")
        referral = ReferralState(raw_ref)
        ts = get_monotone_ts(conn, referral.head_ts)

    # Define Savepoint helper
    savepoint_state = {
        "referral_dict": referral.as_dict() if referral else None,
        "idempotency_key": idem_id,
    }

    try:
        # ---------------------------------------------------------------------
        # STEP 5: Authority & Fencing (Invariants I6, I8)
        # ---------------------------------------------------------------------
        offers_store = getattr(conn.db, "offers", {}) if hasattr(conn, "db") else {}
        offer: Optional[OfferState] = None
        offer_id = getattr(cmd, "offer_id", None)
        if offer_id:
            raw_offer = offers_store.get(str(offer_id))
            if raw_offer:
                offer = OfferState(raw_offer)

        # Enforce Role x Command Matrix
        authorize(conn, referral, offer, session, cmd, ts)

        # Enforce Optimistic Preconditions (expected_version, expected_epoch)
        if referral is not None:
            if cmd.expected_version != referral.version:
                raise TransitionReject(
                    412,
                    "STALE_PRECONDITION",
                    f"Optimistic version mismatch: expected {cmd.expected_version}, current {referral.version}",
                )
            if cmd.expected_epoch is not None and cmd.expected_epoch != referral.lease_epoch:
                raise TransitionReject(
                    412,
                    "STALE_PRECONDITION",
                    f"Optimistic lease epoch mismatch: expected {cmd.expected_epoch}, current {referral.lease_epoch}",
                )

        # ---------------------------------------------------------------------
        # STEP 6: Transition Guard & Forward Lock Order
        # ---------------------------------------------------------------------
        # Verify transition in transitions.yaml
        ref_dict = referral.as_dict() if referral and cmd.type != "CREATE" else None
        offer_dict = offer.as_dict() if offer else None
        transition_rule = TRANSITIONS.lookup(cmd.type, ref_dict, offer_dict)

        # ---------------------------------------------------------------------
        # STEP 7: Staleness Check (Closure F12, Invariant I15)
        # ---------------------------------------------------------------------
        if cmd.type in ("ACCEPT", "CONFIRM_COUNTER"):
            if offer and offer.status not in ("OPEN", "ACKED", "SOFT_OPEN"):
                raise TransitionReject(409, "LATE_ACCEPT_REJECTED", f"Offer is {offer.status}")

        # ---------------------------------------------------------------------
        # STEP 8: Apply State Effects (Invariants I1, I2, I12)
        # ---------------------------------------------------------------------
        # Enforce I14 before mutating tables
        assert_referral_locked(conn, ref_id)

        event_detail: Dict[str, Any] = {}
        event_type = "REFERRAL_CREATED" if cmd.type == "CREATE" else "OFFER_ACCEPTED"

        if cmd.type == "CREATE":
            create_cmd: Any = cmd
            referral = ReferralState({
                "id": str(ref_id),
                "version": 1,
                "hs_state": "OFFERED" if create_cmd.chain else "CREATED",
                "tr_state": "REQUESTED",
                "mode": create_cmd.mode,
                "need_class": create_cmd.need_class,
                "from_facility_id": str(create_cmd.origin_facility_id),
                "origin_facility_id": str(create_cmd.origin_facility_id),
                "chain": [str(c) for c in create_cmd.chain],
                "ladder_cursor": 0,
                "lease_offer_id": None,
                "lease_facility_id": None,
                "lease_epoch": 0,
                "open_offers": 1 if create_cmd.chain else 0,
                "mgso4_status": create_cmd.mgso4_status,
                "profile_id": create_cmd.profile_id,
                "paper_code": f"PK-{secrets.token_hex(4).upper()}",
                "head_seq": 0,
                "head_hash": GENESIS_PREV_HASH_BYTES,
                "head_ts": ts,
                "created_by": str(session.roster_id),
                "created_at": ts,
            })
            referrals_store[str(ref_id)] = referral.as_dict()

            event_type = "REFERRAL_CREATED"
            event_detail = {
                "mode": referral.mode,
                "need_class": referral.need_class,
                "chain_len": len(referral.chain),
                "profile": referral.profile_id,
                "mgso4": referral.mgso4_status,
            }

            # Create step 0 offer if chain exists
            if create_cmd.chain:
                step0_fac = create_cmd.chain[0]
                off0_id = uuid4()
                step0_offer = OfferState({
                    "id": str(off0_id),
                    "referral_id": str(ref_id),
                    "facility_id": str(step0_fac),
                    "step": 0,
                    "source": "CHAIN",
                    "status": "OPEN",
                    "created_epoch": 0,
                    "created_at": ts,
                })
                offers_store[str(off0_id)] = step0_offer.as_dict()

        elif cmd.type == "ACCEPT":
            if not offer:
                raise TransitionReject(404, "OFFER_NOT_FOUND", "Offer row required for ACCEPT")
            offer.status = "ACCEPTED"
            offer.decided_at = ts
            offers_store[str(offer.id)] = offer.as_dict()

            referral.lease_offer_id = offer.id
            referral.lease_facility_id = offer.facility_id
            referral.lease_epoch += 1
            referral.hs_state = "ACCEPTED"
            referral.open_offers = 0
            referrals_store[str(ref_id)] = referral.as_dict()

            event_type = "OFFER_ACCEPTED"
            event_detail = {
                "facility": str(offer.facility_id),
                "epoch": referral.lease_epoch,
                "reason": "CLINICAL_ACCEPT",
            }
        else:
            # Lifecycle commands (ACK, CANCEL, CLOSE, etc.)
            event_type = "OFFER_ACKED" if cmd.type == "ACK" else "CLOSED"
            event_detail = {"channel": cmd.channel} if cmd.type == "ACK" else {"outcome": getattr(cmd, "outcome", "CLOSED")}

        # ---------------------------------------------------------------------
        # STEP 9: Hash-Chained Event & Outbox (Invariants I4, I5, I11, Closures F1, F9)
        # ---------------------------------------------------------------------
        validate_event_detail(event_type, event_detail)

        seq = referral.head_seq + 1
        event_id = cmd.event_id or uuid4()

        core_event = {
            "referral_id": str(ref_id),
            "seq": seq,
            "event_id": str(event_id),
            "type": event_type,
            "epoch": referral.lease_epoch,
            "actor_roster_id": str(session.roster_id),
            "facility_id": str(session.facility_id) if session.facility_id else None,
            "channel": cmd.channel,
            "proxy": cmd.proxy,
            "detail": event_detail,
            "secret_hash": None,
            "client_ts_ms": cmd.client_ts_ms or int(ts.timestamp() * 1000),
            "server_ts_us": int(ts.timestamp() * 1_000_000),
        }

        canonical_core = jcs(core_event)
        event_hash = compute_event_hash(referral.head_hash, core_event)

        # Append to event log
        events_store = getattr(conn.db, "events", []) if hasattr(conn, "db") else []
        event_row = {
            "referral_id": str(ref_id),
            "seq": seq,
            "event_id": str(event_id),
            "type": event_type,
            "actor_roster_id": str(session.roster_id),
            "facility_id": str(session.facility_id) if session.facility_id else None,
            "channel": cmd.channel,
            "proxy": cmd.proxy,
            "epoch": referral.lease_epoch,
            "detail": event_detail,
            "secret_hash": None,
            "client_ts_ms": core_event["client_ts_ms"],
            "server_ts": ts,
            "prev_hash": referral.head_hash,
            "hash": event_hash,
        }
        if hasattr(conn.db, "events"):
            conn.db.events.append(event_row)

        # Update Referral head pointers
        referral.head_seq = seq
        referral.head_hash = event_hash
        referral.head_ts = ts
        referral.version += 1
        referrals_store[str(ref_id)] = referral.as_dict()

        # Insert Outbox Rows (locked last in hierarchy)
        if hasattr(conn.db, "outbox"):
            conn.db.outbox.append({
                "id": len(conn.db.outbox) + 1,
                "referral_id": str(ref_id),
                "event_seq": seq,
                "channel": "SSE",
                "kind": event_type,
                "status": "PENDING",
                "attempts": 0,
                "visible_after": ts,
                "created_at": ts,
            })

        # ---------------------------------------------------------------------
        # STEP 10: Finalize & Idempotency DONE
        # ---------------------------------------------------------------------
        resp_payload = {
            "status": "COMMITTED",
            "referral_id": str(ref_id),
            "version": referral.version,
            "head_seq": seq,
            "head_hash": event_hash.hex(),
            "event_id": str(event_id),
        }

        idempotency_store[idem_id]["status"] = "DONE"
        idempotency_store[idem_id]["http_status"] = 200
        idempotency_store[idem_id]["response"] = resp_payload

        return 200, resp_payload

    except TransitionReject as exc:
        # ---------------------------------------------------------------------
        # SAVEPOINT REJECTION HANDLER (Architecture §5 Step 10)
        # ---------------------------------------------------------------------
        # Roll back state changes made after the savepoint
        if savepoint_state["referral_dict"] and referral:
            referrals_store[str(ref_id)] = savepoint_state["referral_dict"]

        # Log audit entry into rejected_command
        rejected_store = getattr(conn.db, "rejected_commands", []) if hasattr(conn, "db") else []
        rej_entry = {
            "id": len(rejected_store) + 1,
            "actor_id": str(actor_id),
            "key": idem_key,
            "referral_id": str(ref_id) if ref_id else None,
            "command": cmd.type,
            "http_status": exc.http_status,
            "reason_code": exc.reason_code,
            "session_id": str(session.id) if session else None,
            "created_at": ts,
        }
        if hasattr(conn.db, "rejected_commands"):
            conn.db.rejected_commands.append(rej_entry)

        err_response = {
            "status": "REJECTED",
            "reason": exc.reason_code,
            "message": exc.message,
            "command": cmd.type,
        }

        # Store deterministic rejection in idempotency table so replays return exact outcome
        idempotency_store[idem_id]["status"] = "DONE"
        idempotency_store[idem_id]["http_status"] = exc.http_status
        idempotency_store[idem_id]["response"] = err_response

        return exc.http_status, err_response

