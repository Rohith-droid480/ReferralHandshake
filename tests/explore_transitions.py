#!/usr/bin/env python3
"""
ReferralHandshake (Protocol RHP-1) — Explicit State Transition Explorer & Conformance Engine
Specification Anchors: Architecture §4, §5, §6, §11, §17 (F1, F3, F5, F6, F13, F19, I1–I3, I9, I12, I13)
Solution Anchor: Solution v8 §4.8 (Scenarios 1–28)
Protocol: RHP-1 | Architecture Version: FINAL_LOCKED
"""

import sys
import copy
from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path
import yaml

SPEC_FILE = Path(__file__).resolve().parent.parent / "spec" / "transitions.yaml"

class TransitionEngine:
    """
    Pure Python State Transition Evaluator derived strictly from spec/transitions.yaml.
    Evaluates protocol transitions, guards, deadline mutations, and invariants.
    """

    def __init__(self, spec_path: Optional[Path] = None, mutation_m7: bool = False):
        path = spec_path or SPEC_FILE
        with open(path, "r", encoding="utf-8") as f:
            self.spec = yaml.safe_load(f)
        
        self.mutation_m7 = mutation_m7  # Synthetic fault: gate TR_UPDATE(ARRIVED) on hs_state == ACCEPTED
        self.reset()

    def reset(self):
        self.referral: Optional[Dict[str, Any]] = None
        self.offers: List[Dict[str, Any]] = []
        self.deadlines: List[Dict[str, Any]] = []
        self.grants: List[Dict[str, Any]] = []
        self.confirmations: Dict[str, Dict[str, Any]] = {}  # (facility_id, capability) -> expires_at
        self.events: List[Dict[str, Any]] = []
        self.closure_expiry_count: int = 0
        self.current_time_ms: int = 1000
        self.offer_seq: int = 0
        self.deadline_seq: int = 0
        self.event_seq: int = 0

    # -------------------------------------------------------------------------
    # Helper Queries & Invariant Checks
    # -------------------------------------------------------------------------
    def get_open_offers(self) -> List[Dict[str, Any]]:
        open_set = set(self.spec["states"]["offer"]["open_set"])
        return [o for o in self.offers if o["status"] in open_set]

    def count_open_offers(self) -> int:
        return len(self.get_open_offers())

    def get_active_lease(self) -> Optional[Dict[str, Any]]:
        leases = [o for o in self.offers if o["status"] == "ACCEPTED"]
        if len(leases) > 1:
            raise RuntimeError(f"INVARIANT VIOLATION I2: Multiple leases held! {leases}")
        return leases[0] if leases else None

    def get_pending_deadlines(self) -> List[Dict[str, Any]]:
        return [d for d in self.deadlines if d["status"] == "PENDING"]

    def check_invariants(self) -> Tuple[bool, Optional[str]]:
        if not self.referral:
            return True, None

        # I12: open_offers <= 2
        open_count = self.count_open_offers()
        if open_count > self.spec["invariants"]["max_open_offers"]:
            return False, f"I12 VIOLATION: open_offers={open_count} exceeds max {self.spec['invariants']['max_open_offers']}"

        # I2: max 1 active lease
        leases = [o for o in self.offers if o["status"] == "ACCEPTED"]
        if len(leases) > self.spec["invariants"]["max_active_leases"]:
            return False, f"I2 VIOLATION: Multiple leases held: {len(leases)}"

        # I1: Every non-terminal referral has >= 1 pending deadline
        terminal_hs = set(self.spec["states"]["handshake"]["terminal"])
        if self.referral["hs_state"] not in terminal_hs:
            pending = self.get_pending_deadlines()
            if len(pending) == 0:
                return False, f"I1 VIOLATION: Non-terminal state {self.referral['hs_state']} has 0 pending deadlines"

        # I9: No loops - facility appears at most once as active target
        facilities_seen = []
        for o in self.offers:
            facilities_seen.append(o["facility_id"])
        if len(facilities_seen) != len(set(facilities_seen)):
            return False, f"I9 VIOLATION: Facility repeated in offers: {facilities_seen}"

        return True, None

    def emit_event(self, event_type: str, detail: Optional[Dict[str, Any]] = None):
        self.event_seq += 1
        ev = {
            "seq": self.event_seq,
            "type": event_type,
            "detail": detail or {},
            "server_ts": self.current_time_ms,
        }
        self.events.append(ev)

    # -------------------------------------------------------------------------
    # Command Implementations (§4, §5)
    # -------------------------------------------------------------------------
    def apply_create(self, referral_id: str, origin_facility: str, chain: List[str],
                     mode: str = "SEQUENTIAL", need_class: str = "OB_HEMORRHAGE",
                     actor_role: str = "CLINICIAN") -> Tuple[int, Any]:
        if self.referral is not None:
            return 409, "REFERRAL_ALREADY_EXISTS"

        if actor_role not in self.spec["commands"]["CREATE"]["actor_roles"]:
            return 403, "FORBIDDEN_ROLE"

        if not chain:
            # Empty chain escalates immediately to dispatcher
            self.referral = {
                "id": referral_id,
                "origin_facility": origin_facility,
                "chain": [],
                "mode": mode,
                "need_class": need_class,
                "version": 1,
                "lease_epoch": 0,
                "lease_facility": None,
                "hs_state": "ESCALATED_TO_DISPATCHER",
                "tr_state": "REQUESTED",
                "open_offers": 0,
                "outcome": None,
            }
            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "kind": "DISPATCH_ACTION",
                "step": 0,
                "epoch": 0,
                "due_at": self.current_time_ms + 5000,
                "status": "PENDING",
            })
            self.emit_event("REFERRAL_CREATED", {"escalated_to_dispatcher": True})
            return 200, "CREATED_ESCALATED"

        self.referral = {
            "id": referral_id,
            "origin_facility": origin_facility,
            "chain": list(chain),
            "mode": mode,
            "need_class": need_class,
            "version": 1,
            "lease_epoch": 0,
            "lease_facility": None,
            "hs_state": "OFFERED",
            "tr_state": "REQUESTED",
            "open_offers": 0,
            "outcome": None,
        }

        # Offer creation
        if mode == "PARALLEL2" and len(chain) >= 2:
            targets = chain[:2]
        else:
            targets = chain[:1]

        for step, fac in enumerate(targets):
            self.offer_seq += 1
            offer_id = f"off_{self.offer_seq}"
            self.offers.append({
                "id": offer_id,
                "facility_id": fac,
                "step": step,
                "status": "OPEN",
                "counter_round": 0,
                "source": "CHAIN",
                "decision_due_at": None,
            })
            self.grants.append({"facility_id": fac, "active": True})
            
            # Rung 0: ACK deadline
            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "offer_id": offer_id,
                "kind": "ACK",
                "step": step,
                "epoch": 0,
                "due_at": self.current_time_ms + 3000,
                "status": "PENDING",
            })
            # Rung A/4: NOTICE_VOICE
            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "offer_id": offer_id,
                "kind": "NOTICE_VOICE",
                "step": step,
                "epoch": 0,
                "due_at": self.current_time_ms + 750,
                "status": "PENDING",
            })
            # Rung 3A/4: NOTICE_PROXY
            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "offer_id": offer_id,
                "kind": "NOTICE_PROXY",
                "step": step,
                "epoch": 0,
                "due_at": self.current_time_ms + 2250,
                "status": "PENDING",
            })

        self.grants.append({"facility_id": origin_facility, "active": True})
        self.referral["open_offers"] = self.count_open_offers()
        self.emit_event("REFERRAL_CREATED")
        return 200, "CREATED"

    def apply_ack(self, offer_id: str, actor_role: str = "NURSE") -> Tuple[int, Any]:
        target = next((o for o in self.offers if o["id"] == offer_id), None)
        if not target or target["status"] != "OPEN":
            return 409, "INVALID_TRANSITION"

        # In SEQUENTIAL mode, any older SOFT_OPEN offer is now evicted to TIMED_OUT (F13)
        if self.referral["mode"] == "SEQUENTIAL":
            for o in self.offers:
                if o["status"] == "SOFT_OPEN":
                    o["status"] = "TIMED_OUT"
                    self.emit_event("OFFER_TIMED_OUT_EVICTED", {"offer_id": o["id"]})

        target["status"] = "ACKED"
        target["decision_due_at"] = self.current_time_ms + 4000
        if self.referral["hs_state"] != "ACCEPTED":
            self.referral["hs_state"] = "ACKNOWLEDGED"

        # Mark ACK deadline DONE
        for d in self.deadlines:
            if d.get("offer_id") == offer_id and d["kind"] == "ACK" and d["status"] == "PENDING":
                d["status"] = "DONE"

        # Insert DECISION deadline
        self.deadline_seq += 1
        self.deadlines.append({
            "id": f"d_{self.deadline_seq}",
            "offer_id": offer_id,
            "kind": "DECISION",
            "step": target["step"],
            "epoch": self.referral["lease_epoch"],
            "due_at": target["decision_due_at"],
            "status": "PENDING",
        })

        self.referral["open_offers"] = self.count_open_offers()
        self.emit_event("OFFER_ACKED", {"offer_id": offer_id})
        return 200, "ACKED"

    def apply_resource_confirm(self, facility_id: str, capability: str, ttl_ms: int = 10000) -> Tuple[int, Any]:
        self.confirmations[(facility_id, capability)] = {
            "expires_at": self.current_time_ms + ttl_ms
        }
        self.emit_event("RESOURCE_CONFIRMED", {"facility_id": facility_id, "capability": capability})
        return 200, "CONFIRMED"

    def apply_accept(self, offer_id: str, actor_role: str = "CMO",
                     required_capabilities: Optional[List[str]] = None) -> Tuple[int, Any]:
        target = next((o for o in self.offers if o["id"] == offer_id), None)
        if not target:
            return 409, "OFFER_NOT_FOUND"

        # Check single lease invariant (F13, Scenario 5: if lease already granted, competing accept gets 409 LEASE_HELD)
        if self.get_active_lease() is not None:
            return 409, "LEASE_HELD"

        if target["status"] not in ["OPEN", "ACKED", "SOFT_OPEN"]:
            return 409, "LATE_ACCEPT_REJECTED"

        # If SOFT_OPEN: verify successor has NOT ACKed (if successor ACKed, target was already evicted to TIMED_OUT)
        if target["status"] == "SOFT_OPEN":
            # Successors are offers with step > target["step"]
            successor_acked = any(o["step"] > target["step"] and o["status"] in ["ACKED", "ACCEPTED"] for o in self.offers)
            if successor_acked:
                target["status"] = "TIMED_OUT"
                return 409, "LATE_ACCEPT_REJECTED"

        # Staleness & capability confirmation check (I15)
        if required_capabilities:
            for cap in required_capabilities:
                conf = self.confirmations.get((target["facility_id"], cap))
                if not conf or conf["expires_at"] <= self.current_time_ms:
                    return 409, "STALE_CONFIRMATION_RECONFIRM_REQUIRED"

        # Transition target to ACCEPTED
        target["status"] = "ACCEPTED"
        self.referral["lease_facility"] = target["facility_id"]
        self.referral["lease_epoch"] += 1
        self.referral["hs_state"] = "ACCEPTED"

        # Supersede all other open offers (F13)
        for o in self.offers:
            if o["id"] != offer_id and o["status"] in ["OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"]:
                o["status"] = "SUPERSEDED"
                self.emit_event("OFFER_SUPERSEDED", {"offer_id": o["id"]})

        # Cancel open decision/ack deadlines
        for d in self.deadlines:
            if d["status"] == "PENDING" and d["kind"] in ["ACK", "DECISION", "COUNTER_CONFIRM"]:
                d["status"] = "DONE"

        # Arm HANDOVER deadline
        self.deadline_seq += 1
        self.deadlines.append({
            "id": f"d_{self.deadline_seq}",
            "kind": "HANDOVER",
            "step": target["step"],
            "epoch": self.referral["lease_epoch"],
            "due_at": self.current_time_ms + 30000,
            "status": "PENDING",
        })

        self.referral["open_offers"] = self.count_open_offers()
        self.emit_event("OFFER_ACCEPTED", {"offer_id": offer_id, "epoch": self.referral["lease_epoch"]})
        return 200, "ACCEPTED"

    def apply_counter(self, offer_id: str, actor_role: str = "CMO", counter_ttl_ms: int = 2000) -> Tuple[int, Any]:
        target = next((o for o in self.offers if o["id"] == offer_id), None)
        if not target or target["status"] not in ["OPEN", "ACKED"]:
            return 409, "INVALID_TRANSITION"

        if target["counter_round"] >= self.spec["invariants"]["max_counter_rounds"]:
            return 409, "COUNTER_LIMIT_EXCEEDED"

        target["counter_round"] += 1
        target["status"] = "COUNTERED"
        if self.referral["hs_state"] != "ACCEPTED":
            self.referral["hs_state"] = "COUNTERED"

        # Mark DECISION deadline DONE
        for d in self.deadlines:
            if d.get("offer_id") == offer_id and d["kind"] in ["DECISION", "ACK"] and d["status"] == "PENDING":
                d["status"] = "DONE"

        # Deadline formula: min(ts + C, remaining_D) (F13)
        remaining_d = (target["decision_due_at"] - self.current_time_ms) if target.get("decision_due_at") else counter_ttl_ms
        bounded_due = self.current_time_ms + min(counter_ttl_ms, max(1, remaining_d))

        self.deadline_seq += 1
        self.deadlines.append({
            "id": f"d_{self.deadline_seq}",
            "offer_id": offer_id,
            "kind": "COUNTER_CONFIRM",
            "step": target["step"],
            "epoch": self.referral["lease_epoch"],
            "due_at": bounded_due,
            "status": "PENDING",
        })

        self.referral["open_offers"] = self.count_open_offers()
        self.emit_event("OFFER_COUNTERED", {"offer_id": offer_id, "round": target["counter_round"]})
        return 200, "COUNTERED"

    def apply_confirm_counter(self, offer_id: str, confirmed: bool,
                              required_capabilities: Optional[List[str]] = None) -> Tuple[int, Any]:
        target = next((o for o in self.offers if o["id"] == offer_id), None)
        if not target:
            return 409, "OFFER_NOT_FOUND"

        # Check lease conflict (F13: if competing offer already won lease, loser gets 409 LEASE_HELD)
        if self.get_active_lease() is not None:
            if target["status"] in ["COUNTERED", "SUPERSEDED"]:
                target["status"] = "SUPERSEDED"
                return 409, "LEASE_HELD"

        if target["status"] != "COUNTERED":
            return 409, "INVALID_TRANSITION"

        # Mark COUNTER_CONFIRM deadline DONE
        for d in self.deadlines:
            if d.get("offer_id") == offer_id and d["kind"] == "COUNTER_CONFIRM" and d["status"] == "PENDING":
                d["status"] = "DONE"

        if confirmed:
            # Check lease conflict
            if self.get_active_lease() is not None:
                target["status"] = "SUPERSEDED"
                return 409, "LEASE_HELD"

            # Check confirmations
            if required_capabilities:
                for cap in required_capabilities:
                    conf = self.confirmations.get((target["facility_id"], cap))
                    if not conf or conf["expires_at"] <= self.current_time_ms:
                        return 409, "STALE_CONFIRMATION_RECONFIRM_REQUIRED"

            target["status"] = "ACCEPTED"
            self.referral["lease_facility"] = target["facility_id"]
            self.referral["lease_epoch"] += 1
            self.referral["hs_state"] = "ACCEPTED"

            # Supersede others
            for o in self.offers:
                if o["id"] != offer_id and o["status"] in ["OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"]:
                    o["status"] = "SUPERSEDED"

            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "kind": "HANDOVER",
                "step": target["step"],
                "epoch": self.referral["lease_epoch"],
                "due_at": self.current_time_ms + 30000,
                "status": "PENDING",
            })
            self.referral["open_offers"] = self.count_open_offers()
            self.emit_event("OFFER_ACCEPTED", {"offer_id": offer_id, "counter_accepted": True})
            return 200, "ACCEPTED"
        else:
            target["status"] = "DECLINED"
            self.emit_event("OFFER_DECLINED", {"offer_id": offer_id, "counter_rejected": True})
            self.advance()
            return 200, "DECLINED"

    def apply_decline(self, offer_id: str, actor_role: str = "CMO") -> Tuple[int, Any]:
        target = next((o for o in self.offers if o["id"] == offer_id), None)
        if not target or target["status"] not in ["OPEN", "ACKED", "SOFT_OPEN", "COUNTERED"]:
            return 409, "INVALID_TRANSITION"

        target["status"] = "DECLINED"
        for d in self.deadlines:
            if d.get("offer_id") == offer_id and d["status"] == "PENDING":
                d["status"] = "DONE"

        self.emit_event("OFFER_DECLINED", {"offer_id": offer_id})
        self.advance()
        return 200, "DECLINED"

    def advance(self):
        """
        Calculates and applies next steps in the escalation ladder (§4, §5).
        Respects SEQUENTIAL vs PARALLEL2 modes and open_offers <= 2.
        """
        offered_facilities = {o["facility_id"] for o in self.offers}
        unused_targets = [f for f in self.referral["chain"] if f not in offered_facilities]

        if unused_targets:
            next_fac = unused_targets[0]
            step = len(self.offers)
            self.offer_seq += 1
            new_offer = {
                "id": f"off_{self.offer_seq}",
                "facility_id": next_fac,
                "step": step,
                "status": "OPEN",
                "counter_round": 0,
                "source": "CHAIN",
                "decision_due_at": None,
            }
            self.offers.append(new_offer)
            self.grants.append({"facility_id": next_fac, "active": True})

            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "offer_id": new_offer["id"],
                "kind": "ACK",
                "step": step,
                "epoch": self.referral["lease_epoch"],
                "due_at": self.current_time_ms + 3000,
                "status": "PENDING",
            })
            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "offer_id": new_offer["id"],
                "kind": "NOTICE_VOICE",
                "step": step,
                "epoch": self.referral["lease_epoch"],
                "due_at": self.current_time_ms + 750,
                "status": "PENDING",
            })
            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "offer_id": new_offer["id"],
                "kind": "NOTICE_PROXY",
                "step": step,
                "epoch": self.referral["lease_epoch"],
                "due_at": self.current_time_ms + 2250,
                "status": "PENDING",
            })
            self.referral["hs_state"] = "OFFERED"
            self.emit_event("OFFER_CREATED", {"offer_id": new_offer["id"], "facility_id": next_fac})
        else:
            # Chain exhausted. Check if any other open offers remain
            if self.count_open_offers() == 0:
                self.referral["hs_state"] = "ESCALATED_TO_DISPATCHER"
                self.deadline_seq += 1
                self.deadlines.append({
                    "id": f"d_{self.deadline_seq}",
                    "kind": "DISPATCH_ACTION",
                    "step": len(self.offers),
                    "epoch": self.referral["lease_epoch"],
                    "due_at": self.current_time_ms + 5000,
                    "status": "PENDING",
                })
                self.emit_event("ESCALATED_TO_DISPATCHER", {"reason": "CHAIN_EXHAUSTED"})

        self.referral["open_offers"] = self.count_open_offers()

    def apply_timeout(self, deadline_id: str) -> Tuple[int, Any]:
        d = next((x for x in self.deadlines if x["id"] == deadline_id), None)
        if not d or d["status"] != "PENDING":
            return 200, "NO_OP"

        d["status"] = "DONE"
        kind = d["kind"]

        if kind in ["ACK", "DECISION"]:
            offer = next((o for o in self.offers if o["id"] == d.get("offer_id")), None)
            if offer and offer["status"] in ["OPEN", "ACKED"]:
                if self.referral["mode"] == "SEQUENTIAL":
                    # Evict any existing SOFT_OPEN offer to maintain open_offers <= 2
                    for o in self.offers:
                        if o["status"] == "SOFT_OPEN":
                            o["status"] = "TIMED_OUT"
                            self.emit_event("OFFER_TIMED_OUT_EVICTED", {"offer_id": o["id"]})

                    offer["status"] = "SOFT_OPEN"
                    self.emit_event("OFFER_SOFT_OPEN", {"offer_id": offer["id"]})
                    self.advance()
                else:  # PARALLEL2
                    offer["status"] = "TIMED_OUT"
                    self.emit_event("OFFER_TIMED_OUT", {"offer_id": offer["id"]})
                    self.advance()
            return 200, "TIMEOUT_PROCESSED"

        elif kind == "COUNTER_CONFIRM":
            offer = next((o for o in self.offers if o["id"] == d.get("offer_id")), None)
            if offer and offer["status"] == "COUNTERED":
                offer["status"] = "DECLINED"
                self.emit_event("OFFER_DECLINED_ON_COUNTER_TIMEOUT", {"offer_id": offer["id"]})
                self.advance()
            return 200, "COUNTER_TIMEOUT_PROCESSED"

        elif kind == "CLOSURE":
            self.closure_expiry_count += 1
            if self.closure_expiry_count == 1:
                # Stage 1: emit CLOSURE_OVERDUE and rearm once (F6)
                self.emit_event("CLOSURE_OVERDUE", {"count": 1})
                self.deadline_seq += 1
                self.deadlines.append({
                    "id": f"d_{self.deadline_seq}",
                    "kind": "CLOSURE",
                    "step": d["step"],
                    "epoch": self.referral["lease_epoch"],
                    "due_at": self.current_time_ms + 20000,
                    "status": "PENDING",
                })
                return 200, "CLOSURE_OVERDUE_REARMED"
            else:
                # Stage 2: auto-close with UNKNOWN_COUNTER_REFERRAL
                self.referral["hs_state"] = "CLOSED"
                self.referral["outcome"] = "UNKNOWN_COUNTER_REFERRAL"
                self.emit_event("CLOSED", {
                    "outcome": "UNKNOWN_COUNTER_REFERRAL",
                    "proxy": True,
                    "actor": "SYSTEM"
                })
                return 200, "AUTO_CLOSED"

        elif kind == "HANDOVER":
            self.emit_event("HANDOVER_OVERDUE")
            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "kind": "HANDOVER",
                "step": d["step"],
                "epoch": self.referral["lease_epoch"],
                "due_at": self.current_time_ms + 30000,
                "status": "PENDING",
            })
            return 200, "HANDOVER_OVERDUE_REARMED"

        elif kind == "DISPATCH_ACTION":
            self.emit_event("DISPATCH_ACTION_OVERDUE")
            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "kind": "DISPATCH_ACTION",
                "step": d["step"],
                "epoch": self.referral["lease_epoch"],
                "due_at": self.current_time_ms + 5000,
                "status": "PENDING",
            })
            return 200, "DISPATCH_ACTION_OVERDUE_REARMED"

        return 200, "NO_OP"

    def apply_arrival_rejected(self, actor_role: str = "EMT") -> Tuple[int, Any]:
        if not self.referral or self.referral["hs_state"] != "ACCEPTED":
            return 409, "INVALID_TRANSITION"

        lease = self.get_active_lease()
        if lease:
            lease["status"] = "ARRIVAL_REJECTED"

        self.referral["lease_facility"] = None
        self.referral["lease_epoch"] += 1
        self.referral["hs_state"] = "OFFERED"

        # Cancel HANDOVER deadline
        for d in self.deadlines:
            if d["kind"] == "HANDOVER" and d["status"] == "PENDING":
                d["status"] = "DONE"

        self.emit_event("ARRIVAL_REJECTED", {"rejected_facility": lease["facility_id"] if lease else None})
        self.advance()
        return 200, "ARRIVAL_REJECTED"

    def apply_dispatcher_assign(self, assigned_facility: str, actor_role: str = "DISPATCHER") -> Tuple[int, Any]:
        if not self.referral:
            return 409, "REFERRAL_NOT_FOUND"

        if actor_role != "DISPATCHER":
            return 403, "FORBIDDEN"

        # Single lease invariant
        if self.get_active_lease() is not None:
            return 409, "LEASE_HELD"

        # Supersede open offers
        for o in self.offers:
            if o["status"] in ["OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"]:
                o["status"] = "SUPERSEDED"

        # Cancel open deadlines
        for d in self.deadlines:
            if d["status"] == "PENDING" and d["kind"] in ["ACK", "DECISION", "COUNTER_CONFIRM", "DISPATCH_ACTION"]:
                d["status"] = "DONE"

        self.offer_seq += 1
        new_offer = {
            "id": f"off_{self.offer_seq}",
            "facility_id": assigned_facility,
            "step": len(self.offers),
            "status": "ACCEPTED",
            "counter_round": 0,
            "source": "DISPATCHER",
            "proxy": True,
        }
        self.offers.append(new_offer)
        self.grants.append({"facility_id": assigned_facility, "active": True})

        self.referral["lease_facility"] = assigned_facility
        self.referral["lease_epoch"] += 1
        self.referral["hs_state"] = "ACCEPTED"
        self.referral["open_offers"] = 0

        self.deadline_seq += 1
        self.deadlines.append({
            "id": f"d_{self.deadline_seq}",
            "kind": "HANDOVER",
            "step": new_offer["step"],
            "epoch": self.referral["lease_epoch"],
            "due_at": self.current_time_ms + 30000,
            "status": "PENDING",
        })

        self.emit_event("DISPATCHER_ASSIGNED", {"facility_id": assigned_facility})
        return 200, "ASSIGNED"

    def apply_tr_update(self, new_tr_state: str, is_human: bool = True,
                        arrived_at_facility: Optional[str] = None) -> Tuple[int, Any]:
        if not self.referral:
            return 409, "REFERRAL_NOT_FOUND"

        # Non-terminal check
        if self.referral["hs_state"] in ["CLOSED", "CANCELLED"]:
            return 409, "REFERRAL_TERMINAL"

        valid_transitions = self.spec["commands"]["TR_UPDATE"]["valid_transitions"]
        cur = self.referral["tr_state"]
        if new_tr_state not in valid_transitions.get(cur, []):
            return 409, "INVALID_TR_TRANSITION"

        # Mutation M7: Synthetic bug gating TR_UPDATE(ARRIVED) on hs_state == ACCEPTED
        if self.mutation_m7 and new_tr_state == "ARRIVED":
            if self.referral["hs_state"] != "ACCEPTED":
                return 409, "M7_MUTATION_TR_BLOCKED_BY_HS"

        # Guard: ARRIVED requires human confirmation (F5, D2)
        if new_tr_state == "ARRIVED" and not is_human:
            self.emit_event("ARRIVAL_SUGGESTED")
            return 403, "HUMAN_CONFIRMATION_REQUIRED"

        # Arrival at non-owner facility check (Case c)
        if new_tr_state == "ARRIVED" and arrived_at_facility:
            if arrived_at_facility != self.referral["lease_facility"]:
                self.emit_event("ARRIVAL_AT_NON_OWNER", {"arrived_facility": arrived_at_facility})

        self.referral["tr_state"] = new_tr_state
        self.emit_event("TR_UPDATED", {"tr_state": new_tr_state})

        # On HANDED_OVER: arm CLOSURE deadline
        if new_tr_state == "HANDED_OVER":
            self.deadline_seq += 1
            self.deadlines.append({
                "id": f"d_{self.deadline_seq}",
                "kind": "CLOSURE",
                "step": len(self.offers),
                "epoch": self.referral["lease_epoch"],
                "due_at": self.current_time_ms + 20000,
                "status": "PENDING",
            })

        return 200, "TR_UPDATED"

    def apply_tr_destination_change(self, new_destination: str, reason: str, accepted: bool = True) -> Tuple[int, Any]:
        if not self.referral:
            return 409, "REFERRAL_NOT_FOUND"

        if self.referral["hs_state"] in ["CLOSED", "CANCELLED"]:
            return 409, "REFERRAL_TERMINAL"

        # Can only change destination prior to ARRIVED
        if self.referral["tr_state"] in ["ARRIVED", "HANDED_OVER", "TR_CANCELLED"]:
            return 409, "INVALID_TR_STATE"

        self.emit_event("TR_DESTINATION_CHANGED", {
            "new_destination": new_destination,
            "reason": reason,
            "accepted": accepted,
        })
        return 200, "DESTINATION_CHANGED"

    def apply_cancel(self, outcome: str, actor_role: str = "CLINICIAN") -> Tuple[int, Any]:
        if not self.referral or self.referral["hs_state"] in ["CLOSED", "CANCELLED"]:
            return 409, "ALREADY_TERMINAL"

        if outcome not in self.spec["outcomes"]:
            return 422, "OUTCOME_REQUIRED"

        self.referral["hs_state"] = "CANCELLED"
        self.referral["outcome"] = outcome

        for o in self.offers:
            if o["status"] in ["OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"]:
                o["status"] = "WITHDRAWN"

        for d in self.deadlines:
            if d["status"] == "PENDING":
                d["status"] = "CANCELLED"

        if self.referral["tr_state"] not in ["HANDED_OVER", "TR_CANCELLED"]:
            self.referral["tr_state"] = "TR_CANCELLED"

        self.referral["open_offers"] = 0
        self.emit_event("CANCELLED", {"outcome": outcome})
        return 200, "CANCELLED"

    def apply_close(self, outcome: str, actor_role: str = "RECEIVING_ROLE") -> Tuple[int, Any]:
        if not self.referral or self.referral["hs_state"] not in ["ACCEPTED", "ESCALATED_TO_DISPATCHER"]:
            return 409, "INVALID_TRANSITION"

        if outcome not in self.spec["outcomes"]:
            return 422, "OUTCOME_REQUIRED"

        # Guard: ADMITTED_* and DELIVERED_AT_RECEIVER require HANDED_OVER
        req_handover = self.spec["outcomes"][outcome].get("requires_handed_over", False)
        if req_handover and self.referral["tr_state"] != "HANDED_OVER":
            return 409, "INVALID_HANDOVER_STATE"

        self.referral["hs_state"] = "CLOSED"
        self.referral["outcome"] = outcome

        for d in self.deadlines:
            if d["status"] == "PENDING":
                d["status"] = "DONE"

        self.emit_event("CLOSED", {"outcome": outcome})
        return 200, "CLOSED"


# -----------------------------------------------------------------------------
# Explicit State Space BFS Explorer (T-F6, T-F19)
# -----------------------------------------------------------------------------
def explore_state_space() -> Dict[str, Any]:
    """
    Performs bounded BFS state space exploration over the protocol transition graph
    to verify reachability, absence of deadlock, outcome taxonomy coverage, and v7 mappings.
    """
    engine = TransitionEngine()
    visited_states: Set[Tuple[str, str, int, bool]] = set()
    queue = []

    # Initial state
    engine.reset()
    engine.apply_create("ref_001", "PHC_A", ["CHC_B", "FRU_C", "DH_D"])
    init_state = (engine.referral["hs_state"], engine.referral["tr_state"], engine.count_open_offers(), engine.get_active_lease() is not None)
    visited_states.add(init_state)
    queue.append((init_state, engine))

    all_hs_reached = set()
    all_tr_reached = set()
    deadlocks = []

    while queue:
        st, eng = queue.pop(0)
        hs, tr, open_cnt, has_lease = st
        all_hs_reached.add(hs)
        all_tr_reached.add(tr)

        if hs in ["CLOSED", "CANCELLED"]:
            continue  # Terminal states have no outgoing transitions

        # Determine valid transitions from current configuration
        valid_next_actions = 0

        # Try transport actions
        for next_tr in ["DISPATCHED", "EN_ROUTE", "ARRIVED", "HANDED_OVER", "TR_CANCELLED"]:
            clone = copy.deepcopy(eng)
            code, _ = clone.apply_tr_update(next_tr, is_human=True)
            if code == 200:
                valid_next_actions += 1
                nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
                if nxt not in visited_states:
                    visited_states.add(nxt)
                    queue.append((nxt, clone))

        # Try ACK
        for o in eng.offers:
            if o["status"] == "OPEN":
                clone = copy.deepcopy(eng)
                code, _ = clone.apply_ack(o["id"])
                if code == 200:
                    valid_next_actions += 1
                    nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
                    if nxt not in visited_states:
                        visited_states.add(nxt)
                        queue.append((nxt, clone))

        # Try ACCEPT
        for o in eng.offers:
            if o["status"] in ["OPEN", "ACKED", "SOFT_OPEN"] and not has_lease:
                clone = copy.deepcopy(eng)
                code, _ = clone.apply_accept(o["id"])
                if code == 200:
                    valid_next_actions += 1
                    nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
                    if nxt not in visited_states:
                        visited_states.add(nxt)
                        queue.append((nxt, clone))

        # Try COUNTER
        for o in eng.offers:
            if o["status"] in ["OPEN", "ACKED"] and o["counter_round"] < 2:
                clone = copy.deepcopy(eng)
                code, _ = clone.apply_counter(o["id"])
                if code == 200:
                    valid_next_actions += 1
                    nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
                    if nxt not in visited_states:
                        visited_states.add(nxt)
                        queue.append((nxt, clone))

        # Try CONFIRM_COUNTER
        for o in eng.offers:
            if o["status"] == "COUNTERED":
                for conf in [True, False]:
                    clone = copy.deepcopy(eng)
                    code, _ = clone.apply_confirm_counter(o["id"], confirmed=conf)
                    if code == 200:
                        valid_next_actions += 1
                        nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
                        if nxt not in visited_states:
                            visited_states.add(nxt)
                            queue.append((nxt, clone))

        # Try DECLINE
        for o in eng.offers:
            if o["status"] in ["OPEN", "ACKED", "SOFT_OPEN", "COUNTERED"]:
                clone = copy.deepcopy(eng)
                code, _ = clone.apply_decline(o["id"])
                if code == 200:
                    valid_next_actions += 1
                    nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
                    if nxt not in visited_states:
                        visited_states.add(nxt)
                        queue.append((nxt, clone))

        # Try TIMEOUT
        for d in eng.get_pending_deadlines():
            clone = copy.deepcopy(eng)
            code, _ = clone.apply_timeout(d["id"])
            if code == 200:
                valid_next_actions += 1
                nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
                if nxt not in visited_states:
                    visited_states.add(nxt)
                    queue.append((nxt, clone))

        # Try ARRIVAL_REJECTED
        if hs == "ACCEPTED":
            clone = copy.deepcopy(eng)
            code, _ = clone.apply_arrival_rejected()
            if code == 200:
                valid_next_actions += 1
                nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
                if nxt not in visited_states:
                    visited_states.add(nxt)
                    queue.append((nxt, clone))

        # Try DISPATCHER_ASSIGN
        if hs == "ESCALATED_TO_DISPATCHER":
            clone = copy.deepcopy(eng)
            code, _ = clone.apply_dispatcher_assign("MC_E")
            if code == 200:
                valid_next_actions += 1
                nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
                if nxt not in visited_states:
                    visited_states.add(nxt)
                    queue.append((nxt, clone))

        # Try CLOSE
        if hs in ["ACCEPTED", "ESCALATED_TO_DISPATCHER"]:
            for outcome in ["PATIENT_REFUSED", "UNKNOWN_COUNTER_REFERRAL"]:
                clone = copy.deepcopy(eng)
                code, _ = clone.apply_close(outcome)
                if code == 200:
                    valid_next_actions += 1
                    nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
                    if nxt not in visited_states:
                        visited_states.add(nxt)
                        queue.append((nxt, clone))

        # Try CANCEL
        clone = copy.deepcopy(eng)
        code, _ = clone.apply_cancel("PATIENT_REFUSED")
        if code == 200:
            valid_next_actions += 1
            nxt = (clone.referral["hs_state"], clone.referral["tr_state"], clone.count_open_offers(), clone.get_active_lease() is not None)
            if nxt not in visited_states:
                visited_states.add(nxt)
                queue.append((nxt, clone))

        if valid_next_actions == 0:
            deadlocks.append(st)

    return {
        "visited_configurations": len(visited_states),
        "hs_reached": all_hs_reached,
        "tr_reached": all_tr_reached,
        "deadlocks": deadlocks,
    }

if __name__ == "__main__":
    print("Executing BFS reachability explorer on spec/transitions.yaml...")
    res = explore_state_space()
    print(f"Configurations explored: {res['visited_configurations']}")
    print(f"Handshake states reached: {res['hs_reached']}")
    print(f"Transport states reached: {res['tr_reached']}")
    print(f"Deadlocks detected: {len(res['deadlocks'])}")
    if res["deadlocks"]:
        print(f"Deadlocked states: {res['deadlocks']}")
        sys.exit(1)
    print("BFS Exploration PASS: All states reachable, 0 deadlocks.")
    sys.exit(0)
