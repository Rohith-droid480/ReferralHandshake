"""ReferralHandshake Protocol RHP-1 — Pytest Test Configuration & Mock DB Fixtures.

Moves all in-memory mock SQL engine emulation strictly into the tests/ directory (satisfying D-9).
Ensures production code in api/rhp/pipeline.py remains 100% genuine parameterized SQL queries
without any mock engine wiring or in-memory dictionary state.
"""

from __future__ import annotations

import copy
import json
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from api.rhp.db import MockConnection, MockCursor


def _wire_mock_engine() -> None:
    """Wires MockConnection and MockCursor to execute genuine SQL statements.

    Ensures apply_command() executes 100% genuine parameterized SQL queries
    both on real PostgreSQL and in offline unit tests without dictionary leaks in production code.
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
        if not hasattr(db, "payload_grants"):
            db.payload_grants = {}
        if not hasattr(db, "need_class_requirements"):
            # Default requirements for Karnataka Obstetric emergency
            db.need_class_requirements = {
                "OBSTETRIC_EMERGENCY": ["OT", "BLOOD", "ANAESTHETIST", "NICU"],
                "OB_ECLAMPSIA": ["OT", "BLOOD", "ANAESTHETIST", "NICU"],
                "NEONATAL": ["NICU", "PAEDIATRICIAN"],
                "TRAUMA": ["OT", "BLOOD", "ANAESTHETIST"],
                "CARDIAC": ["OT"],
            }
        if not hasattr(db, "catchment_chains"):
            db.catchment_chains = {
                ("11111111-1111-1111-1111-111111111111", "OBSTETRIC_EMERGENCY"): [
                    "22222222-2222-2222-2222-222222222222",
                    "44444444-4444-4444-4444-444444444444",
                    "55555555-5555-5555-5555-555555555555",
                ],
                ("11111111-1111-1111-1111-111111111111", "OB_ECLAMPSIA"): [
                    "22222222-2222-2222-2222-222222222222",
                    "44444444-4444-4444-4444-444444444444",
                    "55555555-5555-5555-5555-555555555555",
                ],
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
                "payload_grants": copy.deepcopy(db.payload_grants),
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
                db.payload_grants = copy.deepcopy(sp.get("payload_grants", {}))
            self.result = []
            return

        # ---------------------------------------------------------------------
        # 2. IDEMPOTENCY
        # ---------------------------------------------------------------------
        if "FROM IDEMPOTENCY" in nq and "WHERE ACTOR_ID = %S AND KEY = %S" in nq:
            actor_id, key = str(p[0]), str(p[1])
            idem_id = f"{actor_id}:{key}"
            rec = db.idempotency.get(idem_id)
            if rec and (rec.get("expires_at") is None or rec["expires_at"] > datetime.now(timezone.utc)):
                self.result = [(rec["request_hash"], rec["status"], rec.get("http_status"), rec.get("response"))]
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
            if "FOR UPDATE" in nq and hasattr(db, "get_row_lock"):
                lock = db.get_row_lock(ref_id)
                if not hasattr(self.connection, "held_row_locks"):
                    self.connection.held_row_locks = []
                if lock not in self.connection.held_row_locks:
                    lock.acquire()
                    self.connection.held_row_locks.append(lock)
            r = db.referrals.get(ref_id)
            if r:
                if nq.startswith("SELECT VERSION, HS_STATE FROM REFERRAL"):
                    self.result = [(r["version"], r["hs_state"])]
                elif nq.startswith("SELECT HS_STATE FROM REFERRAL"):
                    self.result = [(r["hs_state"],)]
                elif nq.startswith("SELECT VERSION FROM REFERRAL"):
                    self.result = [(r["version"],)]
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
            # Handles parameterized updates to referral table
            ref_id = str(p[-1])
            r = db.referrals.get(ref_id)
            if r:
                if len(p) == 15:
                    (
                        version, hs_state, tr_state, lad_cur, lease_off, lease_fac, lease_ep,
                        open_off, tr_fac, h_seq, h_hash, h_ts, outcome, closed_at, _
                    ) = p
                    r["ladder_cursor"] = int(lad_cur) if lad_cur is not None else 0
                    r["tr_facility_id"] = str(tr_fac) if tr_fac else None
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
                elif len(p) == 13:
                    (
                        version, hs_state, tr_state, lease_off, lease_fac, lease_ep,
                        open_off, h_seq, h_hash, h_ts, outcome, closed_at, _
                    ) = p
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
                elif "HS_STATE = 'ESCALATED_TO_DISPATCHER'" in nq:
                    r["hs_state"] = "ESCALATED_TO_DISPATCHER"
                    r["open_offers"] = 0
                    self.result = []
                    return
                elif "HS_STATE = 'OFFERED'" in nq:
                    r["hs_state"] = "OFFERED"
                    if len(p) >= 2 and isinstance(p[0], int):
                        r["ladder_cursor"] = int(p[0])
                    r["open_offers"] = 1
                    self.result = []
                    return
                elif "HS_STATE = 'COUNTERED'" in nq:
                    r["hs_state"] = "COUNTERED"
                    self.result = []
                    return
                elif "HS_STATE = 'CANCELLED'" in nq:
                    r["hs_state"] = "CANCELLED"
                    r["open_offers"] = 0
                    if len(p) == 4:
                        r["tr_state"] = str(p[0])
                        r["outcome"] = str(p[1])
                        r["closed_at"] = p[2]
                    elif len(p) >= 3:
                        r["outcome"] = str(p[0])
                        r["closed_at"] = p[1]
                    self.result = []
                    return
                elif "HS_STATE = 'CLOSED'" in nq:
                    r["hs_state"] = "CLOSED"
                    r["open_offers"] = 0
                    if len(p) >= 3:
                        r["outcome"] = str(p[0])
                        r["closed_at"] = p[1]
                    self.result = []
                    return
                elif "LEASE_OFFER_ID = NULL" in nq or "LEASE_OFFER_ID IS NULL" in nq:
                    r["lease_offer_id"] = None
                    r["lease_facility_id"] = None
                    if len(p) >= 2 and isinstance(p[0], int):
                        r["lease_epoch"] = int(p[0])
                    self.result = []
                    return
                elif len(p) == 4 and "LEASE_OFFER_ID" in nq:
                    r["hs_state"] = "ACCEPTED"
                    r["lease_offer_id"] = str(p[0])
                    r["lease_facility_id"] = str(p[1])
                    r["lease_epoch"] = int(p[2])
                    r["open_offers"] = 0
                    r["tr_facility_id"] = str(p[1])
                    self.result = []
                    return
                elif len(p) == 5 and "LEASE_OFFER_ID" in nq:
                    r["hs_state"] = "ACCEPTED"
                    r["lease_offer_id"] = str(p[0])
                    r["lease_facility_id"] = str(p[1])
                    r["lease_epoch"] = int(p[2])
                    r["open_offers"] = 0
                    r["tr_facility_id"] = str(p[3])
                    self.result = []
                    return
                elif len(p) == 3 and "HS_STATE" in nq and "OPEN_OFFERS" in nq:
                    r["hs_state"] = str(p[0])
                    r["open_offers"] = int(p[1])
                    self.result = []
                    return
                elif len(p) >= 12:
                    version = p[0]
                    hs_state = p[1]
                    tr_state = p[2]
                    lease_off = p[3]
                    lease_fac = p[4]
                    lease_ep = p[5]
                    open_off = p[6]
                    h_seq = p[7]
                    h_hash = p[8]
                    h_ts = p[9]
                    outcome = p[10]
                    closed_at = p[11]

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
        # 4. CHILD LOCKS: OFFER & DEADLINE (Step 6)
        # ---------------------------------------------------------------------
        if ("FROM OFFER " in nq or "FROM OFFER\n" in nq) and "WHERE REFERRAL_ID = %S" in nq and "OFFER_RESOURCE_CONFIRMATION" not in nq:
            if "FOR UPDATE" in nq:
                self.connection.held_table_locks.add("offer")
            ref_id = str(p[0])
            matched = [
                v for v in db.offers.values() if v.get("referral_id") == ref_id
            ]
            if len(p) > 1 and "AND ID != %S" in nq:
                excl_id = str(p[1])
                matched = [m for m in matched if str(m.get("id")) != excl_id]
            matched.sort(key=lambda x: str(x.get("id", "")))
            if "SELECT ID, STATUS FROM OFFER" in nq:
                self.result = [(m["id"], m["status"]) for m in matched]
            elif "SELECT ID, FACILITY_ID FROM OFFER" in nq:
                if "STATUS = 'SOFT_OPEN'" in nq:
                    matched = [m for m in matched if m.get("status") == "SOFT_OPEN"]
                self.result = [(m["id"], m["facility_id"]) for m in matched]
            elif "SELECT FACILITY_ID FROM OFFER" in nq:
                self.result = [(m["facility_id"],) for m in matched]
            elif "SELECT ID FROM OFFER" in nq:
                self.result = [(m["id"],) for m in matched]
            elif "SELECT STATUS, FACILITY_ID FROM OFFER" in nq:
                self.result = [(m["status"], m["facility_id"]) for m in matched]
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

        if ("FROM OFFER " in nq or "FROM OFFER\n" in nq) and "WHERE ID = %S" in nq and "OFFER_RESOURCE_CONFIRMATION" not in nq:
            off_id = str(p[0])
            off = db.offers.get(off_id)
            if off:
                if "SELECT STATUS, DECLINE_REASON FROM OFFER" in nq:
                    self.result = [(off["status"], off.get("decline_reason"))]
                elif "SELECT STATUS FROM OFFER" in nq:
                    self.result = [(off["status"],)]
                else:
                    self.result = [(
                        off["id"], off["referral_id"], off["facility_id"], off["step"],
                        off["source"], off["status"], off["counter_round"], off["counter_mask"],
                        off.get("decline_reason"), off["created_epoch"], off["created_at"],
                        off.get("acked_at"), off.get("acked_by"), off.get("decided_at")
                    )]
            else:
                self.result = []
            return

        if "FROM DEADLINE" in nq and "WHERE REFERRAL_ID = %S" in nq:
            if "FOR UPDATE" in nq:
                self.connection.held_table_locks.add("deadline")
            ref_id = str(p[0])
            matched = [
                v for v in db.deadlines.values() if v.get("referral_id") == ref_id
            ]
            if "STATUS = 'PENDING'" in nq:
                matched = [m for m in matched if m.get("status") == "PENDING"]
            matched.sort(key=lambda x: str(x.get("id", "")))
            if "SELECT ID, KIND FROM DEADLINE" in nq:
                self.result = [(m["id"], m["kind"]) for m in matched]
            elif "SELECT DUE_AT FROM DEADLINE" in nq:
                if "KIND = 'DECISION'" in nq:
                    matched = [m for m in matched if m.get("kind") == "DECISION"]
                self.result = [(m["due_at"],) for m in matched]
            else:
                self.result = [
                    (
                        m["id"], m["referral_id"], m.get("offer_id"), m["kind"],
                        m.get("step"), m["epoch"], m["due_at"], m["status"],
                        m.get("claimed_until"), m["created_at"]
                    )
                    for m in matched
                ]
            return

        if "FROM DEADLINE" in nq and "WHERE ID = %S" in nq:
            d_id = str(p[0])
            d = db.deadlines.get(d_id)
            if d:
                if "SELECT STATUS FROM DEADLINE" in nq:
                    self.result = [(d["status"],)]
                else:
                    self.result = [(
                        d["id"], d["referral_id"], d.get("offer_id"), d["kind"],
                        d.get("step"), d["epoch"], d["due_at"], d["status"],
                        d.get("claimed_until"), d["created_at"]
                    )]
            else:
                self.result = []
            return

        if ("INSERT INTO OFFER (" in nq or "INSERT INTO OFFER " in nq) and "OFFER_RESOURCE_CONFIRMATION" not in nq:
            if len(p) == 11:
                o_id, r_id, fac_id, step, source, status, c_round, c_mask, c_epoch, cr_at, dec_at = p
            elif len(p) == 10:
                o_id, r_id, fac_id, step, source, status, c_round, c_mask, c_epoch, cr_at = p
                dec_at = None
            elif len(p) == 6:
                o_id, r_id, fac_id, step, c_epoch, cr_at = p
                source, status, c_round, c_mask, dec_at = "CHAIN", "OPEN", 0, 0, None
            else:
                o_id, r_id, fac_id = p[0], p[1], p[2]
                step = p[3] if len(p) > 4 and isinstance(p[3], (int, str)) else 0
                source, status, c_round, c_mask, c_epoch = "CHAIN", "OPEN", 0, 0, 0
                cr_at = p[-1]
                dec_at = None
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
                "decided_at": dec_at,
            }
            self.result = []
            return

        if "UPDATE OFFER " in nq and "OFFER_RESOURCE_CONFIRMATION" not in nq:
            if "DECLINE_REASON" in nq and "WHERE ID = %S" in nq:
                if len(p) >= 4:
                    status, dec_at, dec_reason, o_id = str(p[0]), p[1], str(p[2]), str(p[3])
                elif len(p) == 3:
                    status = "DECLINED"
                    dec_at, dec_reason, o_id = p[0], str(p[1]), str(p[2])
                else:
                    status = "DECLINED"
                    dec_reason = "COUNTER_REJECTED" if "COUNTER_REJECTED" in nq else "DECLINED"
                    dec_at, o_id = p[0], str(p[1])
                if o_id in db.offers:
                    db.offers[o_id]["status"] = status
                    db.offers[o_id]["decided_at"] = dec_at
                    db.offers[o_id]["decline_reason"] = dec_reason
            elif "SET STATUS = 'ARRIVAL_REJECTED'" in nq:
                dec_at, dec_reason, r_id = p[0], p[1], str(p[2])
                for off in db.offers.values():
                    if off.get("referral_id") == r_id and off.get("status") == "ACCEPTED":
                        off["status"] = "ARRIVAL_REJECTED"
                        off["decided_at"] = dec_at
                        off["decline_reason"] = dec_reason
            elif "SET STATUS = 'COUNTERED'" in nq:
                c_round, c_mask, o_id = int(p[0]), int(p[1]), str(p[2])
                if o_id in db.offers:
                    db.offers[o_id]["status"] = "COUNTERED"
                    db.offers[o_id]["counter_round"] = c_round
                    db.offers[o_id]["counter_mask"] = c_mask
            elif "SET STATUS = 'SUPERSEDED'" in nq:
                r_id, excl_id = str(p[0]), str(p[1])
                for off in db.offers.values():
                    if off.get("referral_id") == r_id and str(off.get("id")) != excl_id and off.get("status") in ("OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"):
                        off["status"] = "SUPERSEDED"
            elif "SET STATUS = 'WITHDRAWN'" in nq:
                r_id = str(p[0])
                for off in db.offers.values():
                    if off.get("referral_id") == r_id and off.get("status") in ("OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"):
                        off["status"] = "WITHDRAWN"
            elif "SET STATUS = 'TIMED_OUT' WHERE REFERRAL_ID = %S AND STATUS = 'SOFT_OPEN'" in nq:
                r_id, excl_id = str(p[0]), str(p[1])
                for off in db.offers.values():
                    if off.get("referral_id") == r_id and str(off.get("id")) != excl_id and off.get("status") == "SOFT_OPEN":
                        off["status"] = "TIMED_OUT"
            elif "SET STATUS = 'SOFT_OPEN' WHERE ID = %S" in nq:
                o_id = str(p[0])
                if o_id in db.offers:
                    db.offers[o_id]["status"] = "SOFT_OPEN"
            elif "SET STATUS = 'TIMED_OUT' WHERE ID = %S" in nq:
                o_id = str(p[0])
                if o_id in db.offers:
                    db.offers[o_id]["status"] = "TIMED_OUT"
            elif "SET STATUS = 'ACCEPTED', DECIDED_AT = %S WHERE ID = %S" in nq:
                dec_at, o_id = p[0], str(p[1])
                if o_id in db.offers:
                    db.offers[o_id]["status"] = "ACCEPTED"
                    db.offers[o_id]["decided_at"] = dec_at
            elif "SET STATUS = %S, DECIDED_AT = %S WHERE ID = %S" in nq:
                status, dec_at, o_id = p[0], p[1], str(p[2])
                if o_id in db.offers:
                    db.offers[o_id]["status"] = str(status)
                    db.offers[o_id]["decided_at"] = dec_at
            elif "SET STATUS = 'ACKED', ACKED_AT = %S, ACKED_BY = %S WHERE ID = %S" in nq:
                ack_at, ack_by, o_id = p[0], str(p[1]), str(p[2])
                if o_id in db.offers:
                    db.offers[o_id]["status"] = "ACKED"
                    db.offers[o_id]["acked_at"] = ack_at
                    db.offers[o_id]["acked_by"] = ack_by
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

        # ---------------------------------------------------------------------
        # 5. DEADLINE INSERT & UPDATE
        # ---------------------------------------------------------------------
        if "INSERT INTO DEADLINE" in nq:
            if len(p) == 8:
                d_id, r_id, o_id, kind, step, epoch, due_at, cr_at = p
            elif len(p) == 7:
                d_id, r_id, o_id, step, epoch, due_at, cr_at = p
                kind = "HANDOVER" if "HANDOVER" in nq else ("DECISION" if "DECISION" in nq else ("COUNTER_CONFIRM" if "COUNTER_CONFIRM" in nq else ("DISPATCH_ACTION" if "DISPATCH_ACTION" in nq else "ACK")))
            else:
                d_id, r_id, o_id = p[0], p[1], p[2]
                kind = "HANDOVER" if "HANDOVER" in nq else ("DECISION" if "DECISION" in nq else ("COUNTER_CONFIRM" if "COUNTER_CONFIRM" in nq else ("DISPATCH_ACTION" if "DISPATCH_ACTION" in nq else "ACK")))
                step, epoch = 0, 0
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
            if "KIND IN" in nq:
                if "SET STATUS = %S" in nq:
                    st_val = str(p[0])
                    ref_id = str(p[1])
                else:
                    st_val = "CANCELLED" if "CANCELLED" in nq else "DONE"
                    ref_id = str(p[0])
                kinds = [k.strip().strip("'") for k in nq.split("KIND IN (")[1].split(")")[0].split(",")]
                for d in db.deadlines.values():
                    if d.get("referral_id") == ref_id and d.get("status") == "PENDING":
                        if d.get("kind") in kinds:
                            d["status"] = st_val
            elif "WHERE REFERRAL_ID = %S" in nq and "KIND = %S" in nq:
                if len(p) >= 3:
                    st_val = str(p[0])
                    ref_id, kind = str(p[1]), str(p[2])
                else:
                    st_val = "DONE"
                    ref_id, kind = str(p[0]), str(p[1])
                for d in db.deadlines.values():
                    if d.get("referral_id") == ref_id and d.get("status") == "PENDING" and d.get("kind") == kind:
                        d["status"] = st_val
            elif "WHERE REFERRAL_ID = %S AND STATUS = 'PENDING'" in nq:
                if len(p) >= 2:
                    st_val = str(p[0])
                    ref_id = str(p[1])
                else:
                    st_val = "CANCELLED" if "CANCELLED" in nq else "DONE"
                    ref_id = str(p[0])
                for d in db.deadlines.values():
                    if d.get("referral_id") == ref_id and d.get("status") == "PENDING":
                        d["status"] = st_val
            elif "WHERE ID = %S" in nq:
                if len(p) >= 2:
                    st_val = str(p[0])
                    d_id = str(p[1])
                else:
                    st_val = "DONE"
                    d_id = str(p[0])
                if d_id in db.deadlines:
                    db.deadlines[d_id]["status"] = st_val
            self.result = []
            return

        # ---------------------------------------------------------------------
        # 6. PAYLOAD GRANTS & CAPABILITY CONFIRMATIONS
        # ---------------------------------------------------------------------
        if "INSERT INTO PAYLOAD_GRANT" in nq:
            if len(p) >= 5:
                g_id, r_id, fac_id, status, gr_at = p[0], p[1], p[2], p[3], p[4]
            else:
                g_id, r_id, fac_id, gr_at = p[0], p[1], p[2], p[3]
                status = "ACTIVE"
            db.payload_grants[f"{r_id}:{fac_id}"] = {
                "id": str(g_id),
                "referral_id": str(r_id),
                "facility_id": str(fac_id),
                "status": str(status),
                "granted_at": gr_at,
                "revoked_at": None,
            }
            self.result = []
            return

        if "UPDATE PAYLOAD_GRANT" in nq:
            if "REVOKED" in nq:
                rev_at = p[0]
                r_id = str(p[1])
                for grant in db.payload_grants.values():
                    if grant.get("referral_id") == r_id and grant.get("status") == "ACTIVE":
                        if "WHERE REFERRAL_ID = %S AND FACILITY_ID = %S" in nq:
                            target_fac = str(p[2])
                            if grant.get("facility_id") == target_fac:
                                grant["status"] = "REVOKED"
                                grant["revoked_at"] = rev_at
                        else:
                            grant["status"] = "REVOKED"
                            grant["revoked_at"] = rev_at
            self.result = []
            return

        if "FROM CATCHMENT_CHAIN" in nq:
            orig_fac = str(p[0])
            need_class = str(p[1])
            chains = db.catchment_chains.get((orig_fac, need_class), [])
            self.result = [(c,) for c in chains]
            return

        if "INSERT INTO OFFER_RESOURCE_CONFIRMATION" in nq:
            if len(p) == 5:
                off_id, cap, conf_by, cr_at, exp_at = p
                c_id = str(uuid4())
            else:
                c_id, off_id, cap, conf_by, exp_at, cr_at = p[:6]
            db.offer_resource_confirmations[f"{off_id}:{cap}"] = {
                "id": str(c_id),
                "offer_id": str(off_id),
                "capability": str(cap),
                "confirmed_by": str(conf_by),
                "expires_at": exp_at,
                "created_at": cr_at,
            }
            self.result = []
            return

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
        # 7. EVENT & OUTBOX
        # ---------------------------------------------------------------------
        if "FROM EVENT" in nq and "WHERE EVENT_ID = %S" in nq:
            ev_id_check = str(p[0])
            matched = [e for e in db.events if e.get("event_id") == ev_id_check]
            self.result = [(1,)] if matched else []
            return

        if "INSERT INTO EVENT" in nq:
            (
                r_id, seq, ev_id, ev_type, act_r, act_fac, chan, proxy, proxy_for,
                epoch, detail, sec_hash, cli_ts, srv_ts, prev_h, ev_h
            ) = p
            ev_id_str = str(ev_id)
            if any(e.get("event_id") == ev_id_str for e in db.events):
                raise RuntimeError("DUPLICATE_EVENT_ID")
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
        # 8. REJECTED COMMAND
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
        # 9. PG_LOCKS INSPECTION (Attack A-8)
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


# Wire mock engine when tests are loaded
_wire_mock_engine()


@pytest.fixture(autouse=True)
def wire_mock_test_engine():
    """Autouse fixture to ensure the mock engine is wired before every test."""
    _wire_mock_engine()
    yield
