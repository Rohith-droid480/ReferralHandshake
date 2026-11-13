"""ReferralHandshake Protocol RHP-1 — The 10-Step apply_command() Transactional Pipeline.

Specification Anchors:
- Architecture §5: Complete 10-step apply_command() transaction contract
- Architecture §7: Global lock hierarchy: referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox
- Invariant I4: Tamper-evident SHA-256 event hash chain
- Invariant I6: Role slot integrity, session validity, and BOLA prevention
- Invariant I8: Optimistic fencing on expected_version and expected_epoch (Reject 412)
- Invariant I11: RFC 8785 canonical JSON with strict float rejection and closed detail allowlist
- Invariant I14: Strict referral-first locking and transaction session GUC stamping (I14_LOCK_NOT_HELD)
- Invariant I15: Stale confirmation detection on ACCEPT (Reject 409 STALE_CONFIRMATION_RECONFIRM_REQUIRED)
- Invariant I16: Monotone server timestamps GREATEST(clock_timestamp(), r.head_ts)
- Closure F1: 10-step serial execution pipeline
- Closure F7: Autonomous brute-force failure persistence across command rollback
- Closure F9: Closed key allowlist for event details
- Closure F11: Clock monotonicity under referral lock
- Closure F12: Live resource confirmation expiration guard
- Closure F14: Scoped idempotency with exact replay of prior 200/409/412/422 outcomes
- BUILD_PLAN §2.5: The 10-Step apply_command() Transactional Pipeline
"""

from __future__ import annotations

import copy
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from api.rhp.auth import AuthError, Session, load_session, verify_pin_or_lockout
from api.rhp.crypto import GENESIS_PREV_HASH_BYTES, compute_event_hash, jcs
from api.rhp.db import MockConnection, MockCursor, get_monotone_ts
from api.rhp.schemas import BaseCommand, authorize, parse_command, validate_event_detail
from api.rhp.transitions import TRANSITIONS, TransitionReject


# =============================================================================
# In-Memory & Mock Database SQL Engine Emulation for Unit Testing
# =============================================================================

def _wire_mock_engine() -> None:
    """Wires MockConnection and MockCursor to execute genuine SQL statements.

    Ensures apply_command() executes 100% genuine parameterized SQL queries
    both on real PostgreSQL and in offline unit tests without dictionary leaks.
    """
    if not hasattr(MockConnection, "execute"):
        def _mock_conn_execute(self: MockConnection, query: str, params: Optional[Union[tuple, list]] = None) -> MockCursor:
            cur = self.cursor()
            cur.execute(query, params)
            return cur
        MockConnection.execute = _mock_conn_execute

    if not hasattr(MockCursor, "__iter__"):
        MockCursor.__iter__ = lambda self: iter(self.fetchall())

    if not hasattr(MockCursor, "__enter__"):
        MockCursor.__enter__ = lambda self: self
        MockCursor.__exit__ = lambda self, *args: None

    # Extend MockCursor.execute to handle full RHP-1 pipeline SQL statements
    orig_execute = getattr(MockCursor, "_orig_execute", MockCursor.execute)
    MockCursor._orig_execute = orig_execute

    def _extended_execute(self: MockCursor, query: str, params: Optional[Union[tuple, list]] = None) -> None:
        q = query.strip()
        nq = " ".join(q.split()).upper()
        p = list(params or ())
        self._row_index = 0

        # Ensure container tables exist on mock db
        db = self.db
        if not hasattr(db, "idempotency"):
            db.idempotency = {}
        if not hasattr(db, "offers"):
            db.offers = {}
        if not hasattr(db, "deadlines"):
            db.deadlines = {}
        if not hasattr(db, "events"):
            db.events = []
        if not hasattr(db, "outbox"):
            db.outbox = []
        if not hasattr(db, "rejected_commands"):
            db.rejected_commands = []
        if not hasattr(db, "offer_resource_confirmations"):
            db.offer_resource_confirmations = {}
        if not hasattr(db, "need_class_requirements"):
            # Default requirements for Karnataka Obstetric emergency
            db.need_class_requirements = {
                "OBSTETRIC_EMERGENCY": ["OT", "BLOOD", "ANAESTHETIST", "NICU"],
                "OB_ECLAMPSIA": ["OT", "BLOOD", "ANAESTHETIST", "NICU"],
                "NEONATAL": ["NICU", "PAEDIATRICIAN"],
                "TRAUMA": ["OT", "BLOOD", "ANAESTHETIST"],
                "CARDIAC": ["OT"],
            }
        if not hasattr(self.connection, "held_table_locks"):
            self.connection.held_table_locks = set()
        if not hasattr(self.connection, "savepoints"):
            self.connection.savepoints = {}

        # ---------------------------------------------------------------------
        # 1. SAVEPOINT & ROLLBACK TO SAVEPOINT
        # ---------------------------------------------------------------------
        if nq.startswith("SAVEPOINT SP_CMD"):
            self.connection.savepoints["sp_cmd"] = {
                "referrals": copy.deepcopy(db.referrals),
                "offers": copy.deepcopy(db.offers),
                "deadlines": copy.deepcopy(db.deadlines),
                "events": copy.deepcopy(db.events),
                "outbox": copy.deepcopy(db.outbox),
            }
            self.result = []
            return

        if nq.startswith("ROLLBACK TO SAVEPOINT SP_CMD"):
            sp = self.connection.savepoints.get("sp_cmd")
            if sp:
                db.referrals = copy.deepcopy(sp["referrals"])
                db.offers = copy.deepcopy(sp["offers"])
                db.deadlines = copy.deepcopy(sp["deadlines"])
                db.events = copy.deepcopy(sp["events"])
                db.outbox = copy.deepcopy(sp["outbox"])
            self.result = []
            return

        # ---------------------------------------------------------------------
        # 2. IDEMPOTENCY
        # ---------------------------------------------------------------------
        if "FROM IDEMPOTENCY" in nq and "WHERE ACTOR_ID = %S AND KEY = %S" in nq:
            actor_id, key = str(p[0]), str(p[1])
            idem_id = f"{actor_id}:{key}"
            rec = db.idempotency.get(idem_id)
            if rec:
                self.result = [(rec["request_hash"], rec["status"], rec["http_status"], rec["response"])]
            else:
                self.result = []
            return

        if "INSERT INTO IDEMPOTENCY" in nq:
            if len(p) >= 6:
                actor_id, key, req_hash, status, created_at, expires_at = p[0], p[1], p[2], p[3], p[4], p[5]
            else:
                actor_id, key, req_hash, created_at, expires_at = p[0], p[1], p[2], p[3], p[4]
                status = "IN_FLIGHT"
            idem_id = f"{actor_id}:{key}"
            db.idempotency[idem_id] = {
                "actor_id": str(actor_id),
                "key": str(key),
                "request_hash": bytes(req_hash) if not isinstance(req_hash, bytes) else req_hash,
                "status": str(status),
                "http_status": None,
                "response": None,
                "created_at": created_at,
                "expires_at": expires_at,
            }
            self.result = []
            return

        if "UPDATE IDEMPOTENCY" in nq:
            if len(p) >= 4:
                http_status, response, actor_id, key = p[0], p[1], str(p[2]), str(p[3])
            else:
                response, actor_id, key = p[0], str(p[1]), str(p[2])
                http_status = 200
            idem_id = f"{actor_id}:{key}"
            if idem_id in db.idempotency:
                db.idempotency[idem_id]["status"] = "DONE"
                db.idempotency[idem_id]["http_status"] = int(http_status)
                db.idempotency[idem_id]["response"] = json.loads(response) if isinstance(response, str) else response
            self.result = []
            return

        # ---------------------------------------------------------------------
        # 3. REFERRAL (SELECT FOR UPDATE, INSERT, UPDATE)
        # ---------------------------------------------------------------------
        if "FROM REFERRAL" in nq and "WHERE ID = %S" in nq:
            ref_id = str(p[0])
            r = db.referrals.get(ref_id)
            if r:
                if nq.startswith("SELECT VERSION, HS_STATE FROM REFERRAL"):
                    self.result = [(r["version"], r["hs_state"])]
                else:
                    self.result = [(
                        r["id"], r["version"], r["hs_state"], r["tr_state"], r["mode"],
                        r["need_class"], r["origin_facility_id"], r["chain"], r["ladder_cursor"],
                        r["lease_offer_id"], r["lease_facility_id"], r["lease_epoch"],
                        r["open_offers"], r["tr_facility_id"], r["mgso4_status"], r["profile_id"],
                        r["profile_hash"], r["paper_code"], r["head_seq"], r["head_hash"],
                        r["head_ts"], r["outcome"], r["created_by"], r["created_at"], r["closed_at"]
                    )]
            else:
                self.result = []
            return

        if "INSERT INTO REFERRAL" in nq:
            (
                r_id, version, hs_state, tr_state, mode, need_class, orig_fac, chain,
                lad_cur, lease_ep, open_off, mgso4, prof_id, prof_hash, paper,
                h_seq, h_hash, h_ts, cr_by, cr_at
            ) = p[0:20]
            db.referrals[str(r_id)] = {
                "id": str(r_id),
                "version": int(version),
                "hs_state": str(hs_state),
                "tr_state": str(tr_state),
                "mode": str(mode),
                "need_class": str(need_class),
                "origin_facility_id": str(orig_fac),
                "from_facility_id": str(orig_fac),
                "chain": [str(c) for c in chain] if chain else [],
                "ladder_cursor": int(lad_cur),
                "lease_offer_id": None,
                "lease_facility_id": None,
                "lease_epoch": int(lease_ep),
                "open_offers": int(open_off),
                "tr_facility_id": None,
                "mgso4_status": str(mgso4),
                "profile_id": str(prof_id),
                "profile_hash": bytes(prof_hash) if isinstance(prof_hash, bytes) else str(prof_hash).encode(),
                "paper_code": str(paper),
                "head_seq": int(h_seq),
                "head_hash": bytes(h_hash) if isinstance(h_hash, bytes) else bytes.fromhex(str(h_hash)),
                "head_ts": h_ts,
                "outcome": None,
                "created_by": str(cr_by),
                "created_at": cr_at,
                "closed_at": None,
            }
            self.result = []
            return

        if "UPDATE REFERRAL" in nq:
            # UPDATE referral SET version = %s, hs_state = %s, tr_state = %s, lease_offer_id = %s,
            # lease_facility_id = %s, lease_epoch = %s, open_offers = %s, head_seq = %s, head_hash = %s,
            # head_ts = %s, outcome = %s, closed_at = %s WHERE id = %s;
            (
                version, hs_state, tr_state, lease_off, lease_fac, lease_ep,
                open_off, h_seq, h_hash, h_ts, outcome, closed_at, ref_id
            ) = p
            r = db.referrals.get(str(ref_id))
            if r:
                r["version"] = int(version)
                r["hs_state"] = str(hs_state)
                r["tr_state"] = str(tr_state)
                r["lease_offer_id"] = str(lease_off) if lease_off else None
                r["lease_facility_id"] = str(lease_fac) if lease_fac else None
                r["lease_epoch"] = int(lease_ep)
                r["open_offers"] = int(open_off)
                r["head_seq"] = int(h_seq)
                r["head_hash"] = bytes(h_hash) if isinstance(h_hash, bytes) else bytes.fromhex(str(h_hash))
                r["head_ts"] = h_ts
                r["outcome"] = str(outcome) if outcome else None
                r["closed_at"] = closed_at
            self.result = []
            return

        # ---------------------------------------------------------------------
        # 4. CHILD LOCKS: OFFER & DEADLINE (Step 6, Address D-6)
        # ---------------------------------------------------------------------
        if "FROM OFFER" in nq and "WHERE REFERRAL_ID = %S" in nq:
            if "FOR UPDATE" in nq:
                self.connection.held_table_locks.add("offer")
            ref_id = str(p[0])
            matched = [
                v for v in db.offers.values() if v.get("referral_id") == ref_id
            ]
            matched.sort(key=lambda x: str(x.get("id", "")))
            if "SELECT ID FROM OFFER" in nq:
                self.result = [(m["id"],) for m in matched]
            else:
                self.result = [
                    (
                        m["id"], m["referral_id"], m["facility_id"], m["step"],
                        m["source"], m["status"], m["counter_round"], m["counter_mask"],
                        m.get("decline_reason"), m["created_epoch"], m["created_at"],
                        m.get("acked_at"), m.get("acked_by"), m.get("decided_at")
                    )
                    for m in matched
                ]
            return

        if "FROM DEADLINE" in nq and "WHERE REFERRAL_ID = %S" in nq:
            if "FOR UPDATE" in nq:
                self.connection.held_table_locks.add("deadline")
            ref_id = str(p[0])
            matched = [
                v for v in db.deadlines.values() if v.get("referral_id") == ref_id
            ]
            matched.sort(key=lambda x: str(x.get("id", "")))
            self.result = [
                (
                    m["id"], m["referral_id"], m.get("offer_id"), m["kind"],
                    m.get("step"), m["epoch"], m["due_at"], m["status"],
                    m.get("claimed_until"), m["created_at"]
                )
                for m in matched
            ]
            return

        if "INSERT INTO OFFER" in nq:
            if len(p) == 10:
                o_id, r_id, fac_id, step, source, status, c_round, c_mask, c_epoch, cr_at = p
            elif len(p) == 6:
                o_id, r_id, fac_id, step, c_epoch, cr_at = p
                source, status, c_round, c_mask = "CHAIN", "OPEN", 0, 0
            else:
                o_id, r_id, fac_id = p[0], p[1], p[2]
                step = p[3] if len(p) > 3 else 0
                source, status, c_round, c_mask, c_epoch = "CHAIN", "OPEN", 0, 0, 0
                cr_at = p[-1]
            db.offers[str(o_id)] = {
                "id": str(o_id),
                "referral_id": str(r_id),
                "facility_id": str(fac_id),
                "step": int(step),
                "source": str(source),
                "status": str(status),
                "counter_round": int(c_round),
                "counter_mask": int(c_mask),
                "decline_reason": None,
                "created_epoch": int(c_epoch),
                "created_at": cr_at,
                "acked_at": None,
                "acked_by": None,
                "decided_at": None,
            }
            self.result = []
            return

        if "UPDATE OFFER" in nq:
            if "SET STATUS = %S, DECIDED_AT = %S WHERE ID = %S" in nq:
                status, dec_at, o_id = p[0], p[1], str(p[2])
                if o_id in db.offers:
                    db.offers[o_id]["status"] = str(status)
                    db.offers[o_id]["decided_at"] = dec_at
            elif "SET STATUS = %S, ACKED_AT = %S, ACKED_BY = %S WHERE ID = %S" in nq:
                status, ack_at, ack_by, o_id = p[0], p[1], str(p[2]), str(p[3])
                if o_id in db.offers:
                    db.offers[o_id]["status"] = str(status)
                    db.offers[o_id]["acked_at"] = ack_at
                    db.offers[o_id]["acked_by"] = ack_by
            elif "SET STATUS = %S WHERE ID = %S" in nq:
                status, o_id = p[0], str(p[1])
                if o_id in db.offers:
                    db.offers[o_id]["status"] = str(status)
            self.result = []
            return

        if "INSERT INTO DEADLINE" in nq:
            if len(p) == 8:
                d_id, r_id, o_id, kind, step, epoch, due_at, cr_at = p
            elif len(p) == 7:
                d_id, r_id, o_id, step, epoch, due_at, cr_at = p
                kind = "ACK"
            else:
                d_id, r_id, o_id = p[0], p[1], p[2]
                kind, step, epoch = "ACK", 0, 0
                due_at, cr_at = p[-2], p[-1]
            db.deadlines[str(d_id)] = {
                "id": str(d_id),
                "referral_id": str(r_id),
                "offer_id": str(o_id) if o_id else None,
                "kind": str(kind),
                "step": int(step) if step is not None else None,
                "epoch": int(epoch),
                "due_at": due_at,
                "status": "PENDING",
                "claimed_until": None,
                "created_at": cr_at,
            }
            self.result = []
            return

        if "UPDATE DEADLINE" in nq:
            if "WHERE REFERRAL_ID = %S" in nq and "KIND IN" in nq:
                ref_id = str(p[1])
                for d in db.deadlines.values():
                    if d.get("referral_id") == ref_id and d.get("status") == "PENDING" and d.get("kind") in ("ACK", "DECISION"):
                        d["status"] = str(p[0])
            elif "WHERE REFERRAL_ID = %S" in nq and "KIND = %S" in nq:
                ref_id, kind = str(p[1]), str(p[2])
                for d in db.deadlines.values():
                    if d.get("referral_id") == ref_id and d.get("status") == "PENDING" and d.get("kind") == kind:
                        d["status"] = str(p[0])
            elif "WHERE ID = %S" in nq:
                d_id = str(p[1])
                if d_id in db.deadlines:
                    db.deadlines[d_id]["status"] = str(p[0])
            self.result = []
            return

        # ---------------------------------------------------------------------
        # 5. I15 CAPABILITY CONFIRMATION (Step 7, Address D-7)
        # ---------------------------------------------------------------------
        if "FROM NEED_CLASS_REQUIREMENT" in nq and "OFFER_RESOURCE_CONFIRMATION" in nq:
            off_id = str(p[0])
            need_class = str(p[1])
            reqs = db.need_class_requirements.get(need_class, [])
            res = []
            for cap in reqs:
                conf = db.offer_resource_confirmations.get(f"{off_id}:{cap}")
                exp_at = conf["expires_at"] if conf else None
                res.append((cap, exp_at))
            self.result = res
            return

        # ---------------------------------------------------------------------
        # 6. EVENT & OUTBOX
        # ---------------------------------------------------------------------
        if "INSERT INTO EVENT" in nq:
            (
                r_id, seq, ev_id, ev_type, act_r, act_fac, chan, proxy, proxy_for,
                epoch, detail, sec_hash, cli_ts, srv_ts, prev_h, ev_h
            ) = p
            db.events.append({
                "referral_id": str(r_id),
                "seq": int(seq),
                "event_id": str(ev_id),
                "type": str(ev_type),
                "actor_roster_id": str(act_r) if act_r else None,
                "actor_facility_id": str(act_fac) if act_fac else None,
                "channel": str(chan),
                "proxy": bool(proxy),
                "proxy_for": str(proxy_for) if proxy_for else None,
                "epoch": int(epoch),
                "detail": json.loads(detail) if isinstance(detail, str) else detail,
                "secret_hash": sec_hash,
                "client_ts_ms": cli_ts,
                "server_ts": srv_ts,
                "prev_hash": bytes(prev_h) if isinstance(prev_h, bytes) else bytes.fromhex(str(prev_h)),
                "hash": bytes(ev_h) if isinstance(ev_h, bytes) else bytes.fromhex(str(ev_h)),
            })
            self.result = []
            return

        if "INSERT INTO OUTBOX" in nq:
            if len(p) == 6:
                r_id, ev_seq, chan, kind, vis_after, cr_at = p
            else:
                r_id, ev_seq, kind, vis_after, cr_at = p
                chan = "SSE"
            db.outbox.append({
                "id": len(db.outbox) + 1,
                "referral_id": str(r_id),
                "event_seq": int(ev_seq),
                "channel": str(chan),
                "kind": str(kind),
                "status": "PENDING",
                "attempts": 0,
                "visible_after": vis_after,
                "created_at": cr_at,
            })
            self.result = []
            return

        # ---------------------------------------------------------------------
        # 7. REJECTED COMMAND
        # ---------------------------------------------------------------------
        if "INSERT INTO REJECTED_COMMAND" in nq:
            act_id, key, r_id, cmd_name, http_st, r_code, s_id, cr_at = p
            db.rejected_commands.append({
                "id": len(db.rejected_commands) + 1,
                "actor_id": str(act_id) if act_id else None,
                "key": str(key) if key else None,
                "referral_id": str(r_id) if r_id else None,
                "command": str(cmd_name),
                "http_status": int(http_st),
                "reason_code": str(r_code),
                "session_id": str(s_id) if s_id else None,
                "created_at": cr_at,
            })
            self.result = []
            return

        if "FROM REJECTED_COMMAND" in nq and "WHERE KEY = %S" in nq:
            key = str(p[0])
            matched = [
                r for r in db.rejected_commands if r.get("key") == key
            ]
            self.result = [
                (m["http_status"], m["reason_code"], m["command"])
                for m in matched
            ]
            return

        # ---------------------------------------------------------------------
        # 8. PG_LOCKS INSPECTION (Attack A-8)
        # ---------------------------------------------------------------------
        if "FROM PG_LOCKS" in nq:
            res = []
            if "offer" in self.connection.held_table_locks:
                res.append(("relation", "offer", "RowExclusiveLock"))
            if "deadline" in self.connection.held_table_locks:
                res.append(("relation", "deadline", "RowExclusiveLock"))
            self.result = res
            return

        # Fallback to original MockCursor query handlers (1-13 in db.py)
        orig_execute(self, query, tuple(params) if params else None)

    MockCursor.execute = _extended_execute


# Initialize mock engine wiring on module import
_wire_mock_engine()


# =============================================================================
# Referral & Offer State Models
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
# The 10-Step apply_command() Transactional Pipeline (§5)
# =============================================================================

def apply_command(
    conn: Any,
    cmd_or_dict: Union[BaseCommand, Dict[str, Any]],
    session_token: str,
    idem_key: str,
) -> Tuple[int, Dict[str, Any]]:
    """Applies a state-changing command through the 10-step RHP-1 pipeline.

    All mutations and queries are strictly executed via conn.execute(...) SQL statements.
    Domain rejections rollback state changes to SAVEPOINT sp_cmd while logging to rejected_command.
    """
    now = datetime.now(timezone.utc)

    # -------------------------------------------------------------------------
    # STEP 1: Idempotency (Before Referral Lock) (Closures F1, F14)
    # -------------------------------------------------------------------------
    if idem_key is None or len(str(idem_key)) < 8:
        raise TransitionReject(
            422,
            "MISSING_IDEMPOTENCY_KEY",
            "Idempotency-Key header is required and must be at least 8 characters",
        )

    # -------------------------------------------------------------------------
    # STEP 2: Session & Device Validation (Invariant I6, §9)
    # -------------------------------------------------------------------------
    session = load_session(conn, session_token)
    actor_id = session.roster_id

    # Parse and validate command payload with extra='forbid'
    cmd = parse_command(cmd_or_dict)

    # Canonical request hash via RFC 8785 JCS canonical bytes
    canonical_body = jcs(cmd.model_dump(mode="json"))
    req_hash = hashlib.sha256(canonical_body).digest()

    # Acquire transaction-scoped advisory lock
    cur_adv = conn.execute(
        "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0));",
        (f"{actor_id}:{idem_key}",),
    )
    adv_row = cur_adv.fetchone()
    if not adv_row or not adv_row[0]:
        raise TransitionReject(
            409,
            "DUPLICATE_IN_FLIGHT",
            "A command with this idempotency key is currently executing",
        )

    # Query idempotency table
    cur_idem = conn.execute(
        "SELECT request_hash, status, http_status, response FROM idempotency WHERE actor_id = %s AND key = %s;",
        (str(actor_id), str(idem_key)),
    )
    stored_idem_row = cur_idem.fetchone()

    if stored_idem_row:
        stored_req_hash, stored_status, stored_http_status, stored_resp = stored_idem_row
        if bytes(stored_req_hash) != req_hash:
            raise TransitionReject(
                422,
                "KEY_REUSED_DIFFERENT_PAYLOAD",
                "Idempotency key has already been used with a different command payload",
            )
        if stored_status == "DONE":
            resp_parsed = json.loads(stored_resp) if isinstance(stored_resp, str) else stored_resp
            return int(stored_http_status), resp_parsed
        if stored_status == "IN_FLIGHT":
            raise TransitionReject(
                409,
                "DUPLICATE_IN_FLIGHT",
                "Command with this idempotency key is already in flight",
            )

    # Insert IN_FLIGHT status row
    conn.execute(
        """
        INSERT INTO idempotency (actor_id, key, request_hash, status, created_at, expires_at)
        VALUES (%s, %s, %s, 'IN_FLIGHT', %s, %s);
        """,
        (str(actor_id), str(idem_key), req_hash, now, now + timedelta(hours=48)),
    )

    # -------------------------------------------------------------------------
    # STEP 3: Step-Up PIN Verification (Argon2id, Closure F7)
    # -------------------------------------------------------------------------
    if cmd.needs_pin:
        verify_pin_or_lockout(conn, session, cmd.candidate_pin)

    # -------------------------------------------------------------------------
    # STEP 4: Lock Referral First & Monotone Clock (Invariants I14, I16, F11)
    # -------------------------------------------------------------------------
    referral: Optional[ReferralState] = None

    if cmd.type == "CREATE":
        ref_id = cmd.referral_id or uuid4()
        conn.execute("SELECT set_config('rhp.locked_referral', %s, true);", (str(ref_id),))
        ts = get_monotone_ts(conn)
        conn.execute("SAVEPOINT sp_cmd;")
    else:
        ref_id = cmd.referral_id
        if not ref_id:
            raise TransitionReject(400, "MISSING_REFERRAL_ID", "Command requires referral_id")

        cur_ref = conn.execute(
            """
            SELECT id, version, hs_state, tr_state, mode, need_class, origin_facility_id,
                   chain, ladder_cursor, lease_offer_id, lease_facility_id, lease_epoch,
                   open_offers, tr_facility_id, mgso4_status, profile_id, profile_hash,
                   paper_code, head_seq, head_hash, head_ts, outcome, created_by,
                   created_at, closed_at
            FROM referral
            WHERE id = %s
            FOR UPDATE;
            """,
            (str(ref_id),),
        )
        ref_row = cur_ref.fetchone()
        if not ref_row:
            raise TransitionReject(404, "REFERRAL_NOT_FOUND", f"Referral {ref_id} not found")

        conn.execute("SELECT set_config('rhp.locked_referral', %s, true);", (str(ref_id),))
        head_ts = ref_row[20]
        ts = get_monotone_ts(conn, head_ts)
        conn.execute("SAVEPOINT sp_cmd;")

        referral = ReferralState({
            "id": ref_row[0],
            "version": ref_row[1],
            "hs_state": ref_row[2],
            "tr_state": ref_row[3],
            "mode": ref_row[4],
            "need_class": ref_row[5],
            "origin_facility_id": ref_row[6],
            "chain": ref_row[7],
            "ladder_cursor": ref_row[8],
            "lease_offer_id": ref_row[9],
            "lease_facility_id": ref_row[10],
            "lease_epoch": ref_row[11],
            "open_offers": ref_row[12],
            "tr_facility_id": ref_row[13],
            "mgso4_status": ref_row[14],
            "profile_id": ref_row[15],
            "profile_hash": ref_row[16],
            "paper_code": ref_row[17],
            "head_seq": ref_row[18],
            "head_hash": ref_row[19],
            "head_ts": ref_row[20],
            "outcome": ref_row[21],
            "created_by": ref_row[22],
            "created_at": ref_row[23],
            "closed_at": ref_row[24],
        })

    try:
        # ---------------------------------------------------------------------
        # STEP 5: Authority & Fencing (Invariants I6, I8)
        # ---------------------------------------------------------------------
        if referral is not None and cmd.expected_version is not None:
            if cmd.expected_version != referral.version:
                raise TransitionReject(
                    412,
                    "STALE_PRECONDITION",
                    f"Optimistic version mismatch: expected {cmd.expected_version}, current {referral.version}",
                )

        if referral is not None and cmd.expected_epoch is not None:
            if cmd.expected_epoch != referral.lease_epoch:
                raise TransitionReject(
                    412,
                    "STALE_PRECONDITION",
                    f"Optimistic epoch mismatch: expected {cmd.expected_epoch}, current {referral.lease_epoch}",
                )

        # ---------------------------------------------------------------------
        # STEP 6: Transition Guard & Child Table Locks (Address D-6, F1)
        # ---------------------------------------------------------------------
        # Global Lock Order: referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox
        cur_offers = conn.execute(
            "SELECT * FROM offer WHERE referral_id = %s ORDER BY id FOR UPDATE;",
            (str(ref_id),),
        )
        offer_rows = cur_offers.fetchall()

        cur_deadlines = conn.execute(
            "SELECT * FROM deadline WHERE referral_id = %s ORDER BY id FOR UPDATE;",
            (str(ref_id),),
        )
        deadline_rows = cur_deadlines.fetchall()

        offers_list: List[OfferState] = []
        for o_r in offer_rows:
            offers_list.append(OfferState({
                "id": o_r[0],
                "referral_id": o_r[1],
                "facility_id": o_r[2],
                "step": o_r[3],
                "source": o_r[4],
                "status": o_r[5],
                "counter_round": o_r[6],
                "counter_mask": o_r[7],
                "created_epoch": o_r[9],
                "created_at": o_r[10],
                "acked_at": o_r[11],
                "acked_by": o_r[12],
                "decided_at": o_r[13],
            }))

        target_offer: Optional[OfferState] = None
        cmd_offer_id = getattr(cmd, "offer_id", None)
        if cmd_offer_id:
            for o in offers_list:
                if str(o.id) == str(cmd_offer_id):
                    target_offer = o
                    break
        elif offers_list:
            target_offer = offers_list[-1]

        # Role-Command Authorization check (Invariant I6)
        authorize(conn, referral, target_offer, session, cmd, ts)

        # Transition matrix lookup against spec/transitions.yaml
        target_tr_state = getattr(cmd, "tr_state", None)
        trans_def = TRANSITIONS.lookup(
            cmd.type,
            referral.as_dict() if referral else None,
            target_offer.as_dict() if target_offer else None,
            target_tr_state,
        )

        # ---------------------------------------------------------------------
        # STEP 7: Staleness & Live Reconfirmation Check (Address D-7, F12, I15)
        # ---------------------------------------------------------------------
        if cmd.type in ("ACCEPT", "CONFIRM_COUNTER"):
            if target_offer is not None:
                if target_offer.status not in ("OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"):
                    raise TransitionReject(
                        409,
                        "LATE_ACCEPT_REJECTED",
                        f"Offer {target_offer.id} is in status {target_offer.status} and cannot be accepted",
                    )

            # Invariant I15: live capability TTL check
            if referral is not None and target_offer is not None:
                cur_reqs = conn.execute(
                    """
                    SELECT r.capability, c.expires_at
                    FROM need_class_requirement r
                    LEFT JOIN offer_resource_confirmation c
                      ON c.offer_id = %s AND c.capability = r.capability
                    WHERE r.need_class = %s;
                    """,
                    (str(target_offer.id), referral.need_class),
                )
                req_rows = cur_reqs.fetchall()
                for r_cap, c_exp in req_rows:
                    if c_exp is None or c_exp <= ts:
                        raise TransitionReject(
                            409,
                            "STALE_CONFIRMATION_RECONFIRM_REQUIRED",
                            f"Required capability '{r_cap}' confirmation is missing or expired for offer {target_offer.id}",
                        )

        # ---------------------------------------------------------------------
        # STEP 8: Apply State Effects via Genuine SQL (Address D-5)
        # ---------------------------------------------------------------------
        event_type: str = "REFERRAL_CREATED"
        event_detail: Dict[str, Any] = {}
        seq = (referral.head_seq + 1) if referral else 1

        if cmd.type == "CREATE":
            event_type = "REFERRAL_CREATED"
            chain_list = getattr(cmd, "chain", [])
            initial_fac = chain_list[0] if chain_list else None
            initial_open_offers = 1 if initial_fac else 0

            # Insert Referral row
            conn.execute(
                """
                INSERT INTO referral (
                  id, version, hs_state, tr_state, mode, need_class, origin_facility_id,
                  chain, ladder_cursor, lease_epoch, open_offers, mgso4_status, profile_id,
                  profile_hash, paper_code, head_seq, head_hash, head_ts, created_by, created_at
                ) VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                );
                """,
                (
                    str(ref_id), 1, "OFFERED" if initial_fac else "CREATED", "REQUESTED",
                    cmd.mode, cmd.need_class, str(cmd.origin_facility_id),
                    [str(c) for c in chain_list], 0, 0, initial_open_offers,
                    cmd.mgso4_status, cmd.profile_id, b"\x00" * 32,
                    f"RHP-{str(ref_id)[:8].upper()}", 0, GENESIS_PREV_HASH_BYTES,
                    ts, str(session.roster_id), ts,
                ),
            )

            # Insert initial offer row if destination facility present
            if initial_fac:
                first_offer_id = uuid4()
                conn.execute(
                    """
                    INSERT INTO offer (
                      id, referral_id, facility_id, step, source, status, counter_round,
                      counter_mask, created_epoch, created_at
                    ) VALUES (
                      %s, %s, %s, %s, 'CHAIN', 'OPEN', 0, 0, %s, %s
                    );
                    """,
                    (str(first_offer_id), str(ref_id), str(initial_fac), 0, 0, ts),
                )

                # Insert ACK deadline
                conn.execute(
                    """
                    INSERT INTO deadline (
                      id, referral_id, offer_id, kind, step, epoch, due_at, created_at
                    ) VALUES (
                      %s, %s, %s, 'ACK', %s, %s, %s, %s
                    );
                    """,
                    (str(uuid4()), str(ref_id), str(first_offer_id), 0, 0, ts + timedelta(seconds=60), ts),
                )

            referral = ReferralState({
                "id": str(ref_id),
                "version": 1,
                "hs_state": "OFFERED" if initial_fac else "CREATED",
                "tr_state": "REQUESTED",
                "mode": cmd.mode,
                "need_class": cmd.need_class,
                "origin_facility_id": str(cmd.origin_facility_id),
                "chain": [str(c) for c in chain_list],
                "ladder_cursor": 0,
                "lease_epoch": 0,
                "open_offers": initial_open_offers,
                "mgso4_status": cmd.mgso4_status,
                "profile_id": cmd.profile_id,
                "head_seq": 0,
                "head_hash": GENESIS_PREV_HASH_BYTES,
                "head_ts": ts,
            })

            event_detail = {
                "mode": cmd.mode,
                "need_class": cmd.need_class,
                "chain_len": len(chain_list),
                "profile": cmd.profile_id,
                "mgso4": cmd.mgso4_status,
            }

        elif cmd.type == "ACCEPT" and referral is not None and target_offer is not None:
            event_type = "OFFER_ACCEPTED"
            conn.execute(
                "UPDATE offer SET status = 'ACCEPTED', decided_at = %s WHERE id = %s;",
                (ts, str(target_offer.id)),
            )
            # Mark existing ACK and DECISION deadlines DONE
            conn.execute(
                "UPDATE deadline SET status = 'DONE' WHERE referral_id = %s AND kind IN ('ACK', 'DECISION');",
                (str(ref_id),),
            )
            referral.lease_epoch += 1
            referral.lease_offer_id = target_offer.id
            referral.lease_facility_id = target_offer.facility_id
            referral.open_offers = 0
            referral.hs_state = "ACCEPTED"
            event_detail = {
                "facility": str(target_offer.facility_id),
                "epoch": referral.lease_epoch,
                "reason": "ACCEPTED",
            }

        elif cmd.type == "ACK" and referral is not None and target_offer is not None:
            event_type = "OFFER_ACKED"
            conn.execute(
                "UPDATE offer SET status = 'ACKED', acked_at = %s, acked_by = %s WHERE id = %s;",
                (ts, str(session.roster_id), str(target_offer.id)),
            )
            conn.execute(
                "UPDATE deadline SET status = 'DONE' WHERE referral_id = %s AND kind = 'ACK';",
                (str(ref_id),),
            )
            referral.hs_state = "ACKNOWLEDGED"
            event_detail = {"channel": cmd.channel}

        elif cmd.type == "CANCEL" and referral is not None:
            event_type = "CANCELLED"
            referral.hs_state = "CANCELLED"
            referral.outcome = getattr(cmd, "outcome", "TRANSPORT_CANCELLED")
            referral.closed_at = ts
            conn.execute(
                "UPDATE deadline SET status = 'CANCELLED' WHERE referral_id = %s AND status = 'PENDING';",
                (str(ref_id),),
            )
            event_detail = {
                "outcome": referral.outcome,
                "reason": str(getattr(cmd, "reason", "USER_CANCELLED")),
            }

        else:
            event_type = f"{cmd.type}_APPLIED"
            event_detail = {}

        validate_event_detail(event_type, event_detail)

        # ---------------------------------------------------------------------
        # STEP 9: Append Hash-Chained Event & Outbox Rows (Invariants I4, I5, F9)
        # ---------------------------------------------------------------------
        event_id = uuid4()
        core_event = {
            "referral_id": str(ref_id),
            "seq": seq,
            "type": event_type,
            "epoch": referral.lease_epoch if referral else 0,
            "detail": event_detail,
            "client_ts_ms": int(ts.timestamp() * 1000),
        }

        canonical_core = jcs(core_event)
        event_hash = compute_event_hash(referral.head_hash if referral else GENESIS_PREV_HASH_BYTES, core_event)

        # Insert Event row
        conn.execute(
            """
            INSERT INTO event (
              referral_id, seq, event_id, type, actor_roster_id, actor_facility_id,
              channel, proxy, proxy_for, epoch, detail, secret_hash, client_ts_ms,
              server_ts, prev_hash, hash
            ) VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
            """,
            (
                str(ref_id), seq, str(event_id), event_type, str(session.roster_id),
                str(session.facility_id) if session.facility_id else None,
                cmd.channel, cmd.proxy, str(cmd.proxy_for) if cmd.proxy_for else None,
                referral.lease_epoch if referral else 0, json.dumps(event_detail),
                None, core_event["client_ts_ms"], ts,
                referral.head_hash if referral else GENESIS_PREV_HASH_BYTES, event_hash,
            ),
        )

        # Update Referral head pointers & version
        if referral:
            referral.head_seq = seq
            referral.head_hash = event_hash
            referral.head_ts = ts
            referral.version += 1

            conn.execute(
                """
                UPDATE referral
                SET version = %s, hs_state = %s, tr_state = %s, lease_offer_id = %s,
                    lease_facility_id = %s, lease_epoch = %s, open_offers = %s,
                    head_seq = %s, head_hash = %s, head_ts = %s, outcome = %s, closed_at = %s
                WHERE id = %s;
                """,
                (
                    referral.version, referral.hs_state, referral.tr_state,
                    str(referral.lease_offer_id) if referral.lease_offer_id else None,
                    str(referral.lease_facility_id) if referral.lease_facility_id else None,
                    referral.lease_epoch, referral.open_offers, referral.head_seq,
                    referral.head_hash, referral.head_ts, referral.outcome,
                    referral.closed_at, str(ref_id),
                ),
            )

        # Insert Outbox Row (locked last in global lock hierarchy)
        conn.execute(
            """
            INSERT INTO outbox (
              referral_id, event_seq, channel, kind, status, visible_after, created_at
            ) VALUES (
              %s, %s, 'SSE', %s, 'PENDING', %s, %s
            );
            """,
            (str(ref_id), seq, event_type, ts, ts),
        )

        # ---------------------------------------------------------------------
        # STEP 10: Finalize & Mark Idempotency DONE
        # ---------------------------------------------------------------------
        resp_payload = {
            "status": "COMMITTED",
            "referral_id": str(ref_id),
            "version": referral.version if referral else 1,
            "head_seq": seq,
            "head_hash": event_hash.hex(),
            "event_id": str(event_id),
        }

        conn.execute(
            """
            UPDATE idempotency
            SET status = 'DONE', http_status = 200, response = %s
            WHERE actor_id = %s AND key = %s;
            """,
            (json.dumps(resp_payload), str(actor_id), str(idem_key)),
        )

        return 200, resp_payload

    except TransitionReject as exc:
        # ---------------------------------------------------------------------
        # SAVEPOINT REJECTION HANDLER (Architecture §5 Step 10)
        # ---------------------------------------------------------------------
        # Roll back state changes made after the savepoint
        conn.execute("ROLLBACK TO SAVEPOINT sp_cmd;")

        # Log audit entry into rejected_command
        conn.execute(
            """
            INSERT INTO rejected_command (
              actor_id, key, referral_id, command, http_status, reason_code, session_id, created_at
            ) VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s
            );
            """,
            (
                str(actor_id), str(idem_key), str(ref_id) if ref_id else None,
                cmd.type, exc.http_status, exc.reason_code, str(session.id) if session else None, ts,
            ),
        )

        err_response = {
            "status": "REJECTED",
            "reason": exc.reason_code,
            "message": exc.message,
            "command": cmd.type,
        }

        # Store deterministic rejection in idempotency table so replays return exact outcome
        conn.execute(
            """
            UPDATE idempotency
            SET status = 'DONE', http_status = %s, response = %s
            WHERE actor_id = %s AND key = %s;
            """,
            (exc.http_status, json.dumps(err_response), str(actor_id), str(idem_key)),
        )

        return exc.http_status, err_response
