"""ReferralHandshake Protocol RHP-1 — Dual Connection Pools & Lock Helpers.

Specification Anchors:
- Architecture §5: The 10-step apply_command() transaction pipeline (Steps 1, 4)
- Architecture §7: PostgreSQL 16 schema, dual pools, and role separation [F1, F4]
- Architecture §9: Identity, autonomous failure persistence [F7, I6]
- Invariant I14: Strict referral-first locking and session GUC stamping
- Invariant I16: Monotone server timestamps
- BUILD_PLAN §2.1: Dual Connection Pools & Advisory Lock Helpers
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generator, Optional, Set, Tuple, Union
from uuid import UUID

from api.rhp.config import get_settings

# Try importing PostgreSQL connection pool implementations
try:
    import psycopg_pool
    from psycopg.rows import dict_row

    HAS_PSYCOPG3 = True
except ImportError:
    HAS_PSYCOPG3 = False

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool

    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


# =============================================================================
# In-Memory High-Fidelity Mock Database for Offline Tests & Verification
# =============================================================================

class MockDatabase:
    """In-memory data store simulating PostgreSQL tables, MVCC isolation,

    advisory locks, GUC parameters, and autonomous transactions.
    """

    def __init__(self) -> None:
        self.facilities: Dict[str, Dict[str, Any]] = {}
        self.rosters: Dict[str, Dict[str, Any]] = {}
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.enrollment_tickets: Dict[bytes, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.referrals: Dict[str, Dict[str, Any]] = {}
        self.offers: Dict[str, Dict[str, Any]] = {}
        self.deadlines: Dict[str, Dict[str, Any]] = {}
        self.events: List[Dict[str, Any]] = []
        self.outbox: List[Dict[str, Any]] = []
        self.payload_grants: Dict[str, Dict[str, Any]] = {}
        self.heartbeats: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.checkpoints: List[Dict[str, Any]] = []
        self.rejected_commands: List[Dict[str, Any]] = []
        self.resource_confirmations: Dict[str, Dict[str, Any]] = {}
        self.key_versions: Dict[str, Dict[str, Any]] = {}
        self.clinical_payloads: Dict[str, Dict[str, Any]] = {}
        self.event_secrets: Dict[Any, Dict[str, Any]] = {}
        self.advisory_locks: Set[str] = set()
        self.row_locks: Dict[str, Any] = {}
        self.row_locks_guard = threading.Lock()
        self.seed_defaults()

    def get_row_lock(self, ref_id: str) -> Any:
        with self.row_locks_guard:
            if ref_id not in self.row_locks:
                self.row_locks[ref_id] = threading.Lock()
            return self.row_locks[ref_id]

    def seed_defaults(self) -> None:
        """Seeds default synthetic Karnataka facilities and roster slots."""
        # Facility: Bengaluru District Hospital
        f1_id = "00000000-0000-0000-0000-000000000001"
        self.facilities[f1_id] = {
            "id": f1_id,
            "code": "KA-BLR-DH-01",
            "name": "Bengaluru District Hospital",
            "tier": "DH",
            "lat_e5": 1297160,
            "lon_e5": 7759460,
            "active": True,
        }

        # Facility: Ramanagara Taluk CHC
        f2_id = "00000000-0000-0000-0000-000000000002"
        self.facilities[f2_id] = {
            "id": f2_id,
            "code": "KA-RAM-CHC-01",
            "name": "Ramanagara Taluk Hospital CHC",
            "tier": "CHC",
            "lat_e5": 1271500,
            "lon_e5": 7728100,
            "active": True,
        }

        # Curated Karnataka Obstetric Network Facilities (matching db/03_seed.sql)
        self.facilities["11111111-1111-1111-1111-111111111111"] = {
            "id": "11111111-1111-1111-1111-111111111111",
            "code": "PHC_CHANNAPATNA",
            "name": "Channapatna Primary Health Centre",
            "tier": "PHC",
            "lat_e5": 1265180,
            "lon_e5": 7720890,
            "active": True,
        }
        self.facilities["22222222-2222-2222-2222-222222222222"] = {
            "id": "22222222-2222-2222-2222-222222222222",
            "code": "CHC_RAMANAGARA",
            "name": "Ramanagara Community Health Centre",
            "tier": "CHC",
            "lat_e5": 1272090,
            "lon_e5": 7727990,
            "active": True,
        }
        self.facilities["44444444-4444-4444-4444-444444444444"] = {
            "id": "44444444-4444-4444-4444-444444444444",
            "code": "DH_MANDYA",
            "name": "Mandya District Hospital",
            "tier": "DH",
            "lat_e5": 1252390,
            "lon_e5": 7689660,
            "active": True,
        }
        self.facilities["55555555-5555-5555-5555-555555555555"] = {
            "id": "55555555-5555-5555-5555-555555555555",
            "code": "MC_BENGALURU_OB",
            "name": "Bengaluru Apex Obstetric Medical College",
            "tier": "MC",
            "lat_e5": 1297160,
            "lon_e5": 7759460,
            "active": True,
        }
        self.facilities["66666666-6666-6666-6666-666666666666"] = {
            "id": "66666666-6666-6666-6666-666666666666",
            "code": "DISPATCH_108_CENTRAL",
            "name": "Karnataka 108 Central Dispatch Hub",
            "tier": "DISPATCH",
            "lat_e5": 1297670,
            "lon_e5": 7759010,
            "active": True,
        }

        # Roster: CMO at Bengaluru DH (PIN 4321)
        r1_id = "00000000-0000-0000-0000-000000000010"
        self.rosters[r1_id] = {
            "id": r1_id,
            "facility_id": f1_id,
            "role_slot": "CMO",
            "slot_no": 1,
            "phone_e164": "+919880000001",
            # Argon2id hash for PIN "4321"
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        # Roster: Nurse at Bengaluru DH (PIN 1234)
        r2_id = "00000000-0000-0000-0000-000000000011"
        self.rosters[r2_id] = {
            "id": r2_id,
            "facility_id": f1_id,
            "role_slot": "NURSE",
            "slot_no": 1,
            "phone_e164": "+919880000002",
            # Argon2id hash for PIN "1234"
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$PAUTyFh6lk28JiK24raSYg$cs5FWMxIaG76R2AniiY0R+i+aqFSr+9wqu8TYWrv70Y",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        # Roster: CMO at Ramanagara CHC (f2_id, PIN 4321)
        r20_id = "00000000-0000-0000-0000-000000000020"
        self.rosters[r20_id] = {
            "id": r20_id,
            "facility_id": f2_id,
            "role_slot": "CMO",
            "slot_no": 1,
            "phone_e164": "+919880000003",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        # Roster: Consultant at Mandya DH (PIN 4321)
        r30_id = "00000000-0000-0000-0000-000000000030"
        self.rosters[r30_id] = {
            "id": r30_id,
            "facility_id": "00000000-0000-0000-0000-000000000003",
            "role_slot": "CONSULTANT",
            "slot_no": 1,
            "phone_e164": "+919880000004",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        # Synthetic Karnataka Roster Slots (matching db/03_seed.sql)
        self.rosters["a1111111-0000-0000-0000-000000000001"] = {
            "id": "a1111111-0000-0000-0000-000000000001",
            "facility_id": "11111111-1111-1111-1111-111111111111",
            "role_slot": "CLINICIAN",
            "slot_no": 1,
            "phone_e164": "+919000000001",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }
        self.rosters["a2222222-0000-0000-0000-000000000001"] = {
            "id": "a2222222-0000-0000-0000-000000000001",
            "facility_id": "22222222-2222-2222-2222-222222222222",
            "role_slot": "CMO",
            "slot_no": 1,
            "phone_e164": "+919000000003",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }
        self.rosters["a4444444-0000-0000-0000-000000000001"] = {
            "id": "a4444444-0000-0000-0000-000000000001",
            "facility_id": "44444444-4444-4444-4444-444444444444",
            "role_slot": "CONSULTANT",
            "slot_no": 1,
            "phone_e164": "+919000000008",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }
        self.rosters["a5555555-0000-0000-0000-000000000001"] = {
            "id": "a5555555-0000-0000-0000-000000000001",
            "facility_id": "55555555-5555-5555-5555-555555555555",
            "role_slot": "CONSULTANT",
            "slot_no": 1,
            "phone_e164": "+919000000013",
            "pin_hash": "$argon2id$v=19$m=8192,t=1,p=1$vQoGkV5iWhVVmQujX4+uUA$Pf/bMEIxCtXwWUZuHJyIL5KZpztGt5Ank9Ht9ac3yvo",
            "valid_from": datetime.now(timezone.utc),
            "valid_to": None,
        }

        # Referral 1
        ref1_id = "00000000-0000-0000-0000-000000000100"
        self.referrals[ref1_id] = {
            "id": ref1_id,
            "origin_facility_id": "11111111-1111-1111-1111-111111111111",
            "from_facility_id": f2_id,
            "need_class": "OB_ECLAMPSIA",
            "mgso4_status": "GIVEN",
            "mode": "PARALLEL2",
            "hs_state": "OFFERED",
            "tr_state": "REQUESTED",
            "lease_facility_id": None,
            "lease_epoch": 0,
            "open_offers": 2,
            "paper_code": "4K8M2T91J",
            "head_seq": 1,
            "head_hash": bytes(32),
            "head_ts": datetime.now(timezone.utc),
            "version": 1,
            "created_at": datetime.now(timezone.utc),
        }

        # Referral 2 — Live En-Route Transport Referral
        ref2_id = "00000000-0000-0000-0000-000000000200"
        self.referrals[ref2_id] = {
            "id": ref2_id,
            "origin_facility_id": "11111111-1111-1111-1111-111111111111",
            "from_facility_id": "11111111-1111-1111-1111-111111111111",
            "need_class": "OB_HEMORRHAGE",
            "mgso4_status": "NONE_GIVEN",
            "mode": "SEQUENTIAL",
            "hs_state": "ACCEPTED",
            "tr_state": "EN_ROUTE",
            "lease_facility_id": "55555555-5555-5555-5555-555555555555",
            "lease_epoch": 1,
            "open_offers": 0,
            "paper_code": "9X7P3N18X",
            "head_seq": 4,
            "head_hash": bytes(32),
            "head_ts": datetime.now(timezone.utc),
            "version": 4,
            "created_at": datetime.now(timezone.utc),
        }

        # Referral 3 — Escalated Emergency Referral for Dispatcher Hub
        ref3_id = "00000000-0000-0000-0000-000000000300"
        self.referrals[ref3_id] = {
            "id": ref3_id,
            "origin_facility_id": "11111111-1111-1111-1111-111111111111",
            "from_facility_id": "11111111-1111-1111-1111-111111111111",
            "need_class": "OBSTETRIC_EMERGENCY",
            "mgso4_status": "UNKNOWN",
            "mode": "SEQUENTIAL",
            "hs_state": "ESCALATED_TO_DISPATCHER",
            "tr_state": "DISPATCHED",
            "lease_facility_id": None,
            "lease_epoch": 0,
            "open_offers": 0,
            "paper_code": "3M9K2W17J",
            "head_seq": 5,
            "head_hash": bytes(32),
            "head_ts": datetime.now(timezone.utc),
            "version": 5,
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=15),
        }

        # Seed events for Ref 1, Ref 2, Ref 3 for Time-Scrubber Replay & Exporters
        self.events.extend([
            {
                "referral_id": ref1_id,
                "seq": 1,
                "type": "OFFER_CREATED",
                "epoch": 0,
                "detail": {"facility_id": "22222222-2222-2222-2222-222222222222", "step": 1},
                "client_ts_ms": int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp() * 1000),
                "server_ts": datetime.now(timezone.utc) - timedelta(minutes=5),
                "hash": bytes(32),
                "prev_hash": bytes(32),
            },
            {
                "referral_id": ref2_id,
                "seq": 1,
                "type": "OFFER_CREATED",
                "epoch": 0,
                "detail": {"facility_id": "55555555-5555-5555-5555-555555555555", "step": 1},
                "client_ts_ms": int((datetime.now(timezone.utc) - timedelta(minutes=20)).timestamp() * 1000),
                "server_ts": datetime.now(timezone.utc) - timedelta(minutes=20),
                "hash": bytes(32),
                "prev_hash": bytes(32),
            },
            {
                "referral_id": ref2_id,
                "seq": 2,
                "type": "OFFER_ACK",
                "epoch": 0,
                "detail": {"facility_id": "55555555-5555-5555-5555-555555555555"},
                "client_ts_ms": int((datetime.now(timezone.utc) - timedelta(minutes=18)).timestamp() * 1000),
                "server_ts": datetime.now(timezone.utc) - timedelta(minutes=18),
                "hash": bytes(32),
                "prev_hash": bytes(32),
            },
            {
                "referral_id": ref2_id,
                "seq": 3,
                "type": "OFFER_ACCEPTED",
                "epoch": 1,
                "detail": {"facility_id": "55555555-5555-5555-5555-555555555555"},
                "client_ts_ms": int((datetime.now(timezone.utc) - timedelta(minutes=16)).timestamp() * 1000),
                "server_ts": datetime.now(timezone.utc) - timedelta(minutes=16),
                "hash": bytes(32),
                "prev_hash": bytes(32),
            },
            {
                "referral_id": ref2_id,
                "seq": 4,
                "type": "TR_UPDATE",
                "epoch": 1,
                "detail": {"tr_state": "EN_ROUTE", "lat_e5": 1262000, "lon_e5": 7701000},
                "client_ts_ms": int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp() * 1000),
                "server_ts": datetime.now(timezone.utc) - timedelta(minutes=10),
                "hash": bytes(32),
                "prev_hash": bytes(32),
            },
            {
                "referral_id": ref3_id,
                "seq": 1,
                "type": "OFFER_CREATED",
                "epoch": 0,
                "detail": {"facility_id": "22222222-2222-2222-2222-222222222222", "step": 1},
                "client_ts_ms": int((datetime.now(timezone.utc) - timedelta(minutes=15)).timestamp() * 1000),
                "server_ts": datetime.now(timezone.utc) - timedelta(minutes=15),
                "hash": bytes(32),
                "prev_hash": bytes(32),
            },
            {
                "referral_id": ref3_id,
                "seq": 2,
                "type": "NOTICE_VOICE",
                "epoch": 0,
                "detail": {"facility_id": "22222222-2222-2222-2222-222222222222"},
                "client_ts_ms": int((datetime.now(timezone.utc) - timedelta(minutes=14)).timestamp() * 1000),
                "server_ts": datetime.now(timezone.utc) - timedelta(minutes=14),
                "hash": bytes(32),
                "prev_hash": bytes(32),
            },
            {
                "referral_id": ref3_id,
                "seq": 3,
                "type": "TIMEOUT",
                "epoch": 0,
                "detail": {"kind": "ACK", "facility_id": "22222222-2222-2222-2222-222222222222"},
                "client_ts_ms": int((datetime.now(timezone.utc) - timedelta(minutes=12)).timestamp() * 1000),
                "server_ts": datetime.now(timezone.utc) - timedelta(minutes=12),
                "hash": bytes(32),
                "prev_hash": bytes(32),
            },
            {
                "referral_id": ref3_id,
                "seq": 4,
                "type": "OFFER_CREATED",
                "epoch": 0,
                "detail": {"facility_id": "44444444-4444-4444-4444-444444444444", "step": 2},
                "client_ts_ms": int((datetime.now(timezone.utc) - timedelta(minutes=11)).timestamp() * 1000),
                "server_ts": datetime.now(timezone.utc) - timedelta(minutes=11),
                "hash": bytes(32),
                "prev_hash": bytes(32),
            },
            {
                "referral_id": ref3_id,
                "seq": 5,
                "type": "ESCALATED_TO_DISPATCHER",
                "epoch": 0,
                "detail": {"reason": "T_MAX_EXCEEDED", "chain_exhausted": True},
                "client_ts_ms": int((datetime.now(timezone.utc) - timedelta(minutes=8)).timestamp() * 1000),
                "server_ts": datetime.now(timezone.utc) - timedelta(minutes=8),
                "hash": bytes(32),
                "prev_hash": bytes(32),
            },
        ])

        # Seed initial component heartbeats for health check
        now = datetime.now(timezone.utc)
        for comp in ["POLLER", "RELAY", "MONITOR"]:
            self.heartbeats[(comp.upper(), f"{comp.lower()}-1")] = {
                "subject_kind": comp,
                "subject_id": f"{comp.lower()}-1",
                "last_seen": now,
                "ntp_offset_ms": 0,
            }
        self.heartbeats[("WITNESS", "rhp1-witness-2026-11")] = {
            "subject_kind": "WITNESS",
            "subject_id": "rhp1-witness-2026-11",
            "last_seen": now,
            "ntp_offset_ms": 0,
        }


class MockCursor:
    """Simulates a database cursor executing against MockDatabase."""

    def __init__(self, connection: "MockConnection") -> None:
        self.connection = connection
        self.db = connection.db
        self.result: list[Any] = []
        self._row_index = 0

    def execute(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> None:
        q = query.strip()
        nq = " ".join(query.split()).upper()
        p = params or ()
        self.result = []
        self._row_index = 0

        # 1. Advisory Lock: SELECT pg_try_advisory_xact_lock(...)
        if "PG_TRY_ADVISORY_XACT_LOCK" in nq:
            lock_key = str(p[0])
            if lock_key in self.db.advisory_locks and lock_key not in self.connection.held_locks:
                self.result = [(False,)]
            else:
                self.db.advisory_locks.add(lock_key)
                self.connection.held_locks.add(lock_key)
                self.result = [(True,)]
            return

        # Insert Referral
        if "INSERT INTO REFERRAL" in nq:
            r_id = str(p[0])
            ref_dict = {
                "id": r_id,
                "version": p[1],
                "hs_state": p[2],
                "tr_state": p[3],
                "mode": p[4],
                "need_class": p[5],
                "from_facility_id": str(p[6]),
                "origin_facility_id": str(p[6]),
                "chain": p[7],
                "ladder_cursor": p[8],
                "lease_offer_id": None,
                "lease_facility_id": None,
                "lease_epoch": p[9],
                "open_offers": p[10],
                "tr_facility_id": None,
                "mgso4_status": p[11],
                "profile_id": p[12],
                "profile_hash": p[13],
                "paper_code": p[14],
                "head_seq": p[15],
                "head_hash": p[16],
                "head_ts": p[17],
                "outcome": None,
                "created_by": str(p[18]),
                "created_at": p[19],
                "closed_at": None,
            }
            self.db.referrals[r_id] = ref_dict
            return

        # Insert Offer Resource Confirmation
        if "INSERT INTO OFFER_RESOURCE_CONFIRMATION" in nq:
            o_id = str(p[0])
            cap = str(p[1])
            conf_by = str(p[2])
            conf_at = p[3]
            exp_at = p[4]
            if not hasattr(self.db, "offer_confirmations"):
                self.db.offer_confirmations = {}
            self.db.offer_confirmations[(o_id, cap)] = {
                "offer_id": o_id,
                "capability": cap,
                "confirmed_by": conf_by,
                "confirmed_at": conf_at,
                "expires_at": exp_at,
            }
            return

        # Insert Offer
        if "INSERT INTO OFFER (" in nq:
            o_id = str(p[0])
            off_dict = {
                "id": o_id,
                "referral_id": str(p[1]),
                "facility_id": str(p[2]),
                "step": int(p[3]),
                "source": str(p[4]) if len(p) > 4 else "DIRECT",
                "status": str(p[5]) if len(p) > 5 else "OPEN",
                "counter_round": int(p[6]) if len(p) > 6 else 0,
                "counter_mask": int(p[7]) if len(p) > 7 else 0,
                "created_epoch": int(p[8]) if len(p) > 8 else 0,
                "created_at": p[9] if len(p) > 9 else datetime.now(timezone.utc),
            }
            self.db.offers[o_id] = off_dict
            return

        # Query need_class_requirement LEFT JOIN offer_resource_confirmation
        if "FROM NEED_CLASS_REQUIREMENT" in nq:
            off_id = str(p[0])
            nc = str(p[1]) if len(p) > 1 else "OBSTETRIC_EMERGENCY"
            req_caps = ["OT", "BLOOD", "ANAESTHETIST", "NICU"]
            res = []
            future_dt = datetime.now(timezone.utc) + timedelta(minutes=60)
            for cap in req_caps:
                conf = getattr(self.db, "offer_confirmations", {}).get((off_id, cap))
                exp = conf["expires_at"] if conf else future_dt
                res.append((cap, exp))
            self.result = res
            return

        # Select Offers for referral / count offers
        if "FROM OFFER WHERE REFERRAL_ID" in nq:
            ref_id = str(p[0])
            if "COUNT(*)" in nq:
                cnt = 0
                for o in self.db.offers.values():
                    if str(o.get("referral_id")) == ref_id:
                        if "STATUS = 'ACCEPTED'" in nq:
                            if o.get("status") == "ACCEPTED":
                                cnt += 1
                        else:
                            cnt += 1
                self.result = [(cnt,)]
                return
            fac_id = str(p[1]) if len(p) > 1 else None
            matching = []
            for o in self.db.offers.values():
                if str(o.get("referral_id")) == ref_id:
                    if fac_id is None or str(o.get("facility_id")) == fac_id:
                        matching.append((
                            o["id"],
                            str(o.get("referral_id")),
                            str(o.get("facility_id")),
                            o.get("step", 1),
                            o.get("source", "DIRECT"),
                            o.get("status", "OPEN"),
                            o.get("counter_round", 0),
                            o.get("counter_mask", 0),
                            o.get("counter_note"),
                            o.get("created_epoch", 0),
                            o.get("created_at", datetime.now(timezone.utc)),
                            o.get("acked_at"),
                            o.get("acked_by"),
                            o.get("decided_at"),
                            o.get("decided_by"),
                            o.get("decline_reason"),
                            o.get("redirect_facility_id"),
                        ))
            self.result = matching
            return

        # 2. Lock Referral: SELECT ... FROM referral WHERE id = %s FOR UPDATE
        if "FROM REFERRAL WHERE ID" in nq and "FOR UPDATE" in nq:
            ref_id = str(p[0])
            row_lock = self.db.get_row_lock(ref_id)
            if row_lock not in self.connection.held_row_locks:
                row_lock.acquire()
                self.connection.held_row_locks.append(row_lock)
            ref = self.db.referrals.get(ref_id)
            if ref:
                self.result = [(
                    ref["id"],
                    ref.get("version", 1),
                    ref.get("hs_state", "OFFERED"),
                    ref.get("tr_state", "REQUESTED"),
                    ref.get("mode", "SEQUENTIAL"),
                    ref.get("need_class", "OBSTETRIC_EMERGENCY"),
                    ref.get("origin_facility_id") or ref.get("from_facility_id"),
                    ref.get("chain", []),
                    ref.get("ladder_cursor", 0),
                    ref.get("lease_offer_id"),
                    ref.get("lease_facility_id"),
                    ref.get("lease_epoch", 0),
                    ref.get("open_offers", 1),
                    ref.get("tr_facility_id"),
                    ref.get("mgso4_status", "UNKNOWN"),
                    ref.get("profile_id", "DEMO_FAST"),
                    ref.get("profile_hash", b"\x00" * 32),
                    ref.get("paper_code", "4K8M2T91J"),
                    ref.get("head_seq", 0),
                    ref.get("head_hash", b"\x00" * 32),
                    ref.get("head_ts", datetime.now(timezone.utc)),
                    ref.get("outcome"),
                    ref.get("created_by"),
                    ref.get("created_at", datetime.now(timezone.utc)),
                    ref.get("closed_at"),
                )]
            else:
                self.result = []
            return

        # Update Referral
        if "UPDATE REFERRAL" in nq:
            ref_id = str(p[-1])
            if ref_id in self.db.referrals:
                ref = self.db.referrals[ref_id]
                if "VERSION =" in nq and len(p) >= 15:
                    ref["version"] = p[0]
                    ref["hs_state"] = p[1]
                    ref["tr_state"] = p[2]
                    ref["ladder_cursor"] = p[3]
                    ref["lease_offer_id"] = str(p[4]) if p[4] else None
                    ref["lease_facility_id"] = str(p[5]) if p[5] else None
                    ref["lease_epoch"] = p[6]
                    ref["open_offers"] = p[7]
                    ref["tr_facility_id"] = str(p[8]) if p[8] else None
                    ref["head_seq"] = p[9]
                    ref["head_hash"] = p[10]
                    ref["head_ts"] = p[11]
                    ref["outcome"] = p[12]
                    ref["closed_at"] = p[13]
                elif "LEASE_OFFER_ID =" in nq:
                    ref["hs_state"] = "ACCEPTED"
                    ref["lease_offer_id"] = str(p[0]) if p[0] else None
                    ref["lease_facility_id"] = str(p[1]) if p[1] else None
                    ref["lease_epoch"] = p[2]
                    ref["open_offers"] = 0
                    ref["tr_facility_id"] = str(p[3]) if p[3] else None
                elif "HS_STATE = 'ACCEPTED'" in nq:
                    ref["hs_state"] = "ACCEPTED"
                elif "HS_STATE = 'ACKNOWLEDGED'" in nq:
                    ref["hs_state"] = "ACKNOWLEDGED"
                elif "HS_STATE = 'COUNTERED'" in nq:
                    ref["hs_state"] = "COUNTERED"
                elif "HS_STATE = 'CANCELLED'" in nq:
                    ref["hs_state"] = "CANCELLED"
                    if len(p) >= 3:
                        ref["outcome"] = p[0]
                        ref["closed_at"] = p[1]
                elif "TR_STATE" in nq:
                    if len(p) >= 2:
                        ref["tr_state"] = p[0]
            return

        # Update Offer
        if "UPDATE OFFER" in nq:
            if "STATUS = 'ACCEPTED'" in nq:
                off_id = str(p[1])
                if off_id in self.db.offers:
                    target_ref_id = str(self.db.offers[off_id].get("referral_id"))
                    from api.rhp.config import get_settings
                    if not get_settings().BROKEN_BUILD:
                        for existing_off in self.db.offers.values():
                            if (
                                str(existing_off.get("referral_id")) == target_ref_id
                                and existing_off.get("status") == "ACCEPTED"
                                and existing_off["id"] != off_id
                            ):
                                raise Exception("duplicate key value violates unique constraint 'one_lease'")
                    self.db.offers[off_id]["status"] = "ACCEPTED"
                    self.db.offers[off_id]["decided_at"] = p[0]
            elif "STATUS = 'SUPERSEDED'" in nq:
                target_ref_id = str(p[0])
                keep_off_id = str(p[1])
                for off in self.db.offers.values():
                    if str(off.get("referral_id")) == target_ref_id and str(off.get("id")) != keep_off_id:
                        if off.get("status") in ("OPEN", "ACKED", "COUNTERED", "SOFT_OPEN"):
                            off["status"] = "SUPERSEDED"
            elif "STATUS = 'ACKED'" in nq:
                off_id = str(p[2])
                if off_id in self.db.offers:
                    self.db.offers[off_id]["status"] = "ACKED"
                    self.db.offers[off_id]["acked_at"] = p[0]
                    self.db.offers[off_id]["acked_by"] = str(p[1])
            elif "STATUS = 'SOFT_OPEN'" in nq:
                off_id = str(p[0])
                if off_id in self.db.offers:
                    self.db.offers[off_id]["status"] = "SOFT_OPEN"
            elif "STATUS = 'TIMED_OUT'" in nq:
                off_id = str(p[0])
                if off_id in self.db.offers:
                    self.db.offers[off_id]["status"] = "TIMED_OUT"
            return

        # 3. Stamp Referral GUC: SELECT set_config('rhp.locked_referral', %s, true)
        if "SET_CONFIG('RHP.LOCKED_REFERRAL'" in nq:
            ref_id = str(p[0])
            self.connection.session_gucs["rhp.locked_referral"] = ref_id
            self.result = [(ref_id,)]
            return

        # 4. Monotone Timestamp: SELECT GREATEST(clock_timestamp(), %s) or SELECT clock_timestamp()
        if "CLOCK_TIMESTAMP()" in nq:
            now = datetime.now(timezone.utc)
            if "GREATEST" in nq and p and p[0] is not None:
                head_ts = p[0]
                if isinstance(head_ts, str):
                    head_ts = datetime.fromisoformat(head_ts)
                if head_ts.tzinfo is None:
                    head_ts = head_ts.replace(tzinfo=timezone.utc)
                self.result = [(max(now, head_ts),)]
            else:
                self.result = [(now,)]
            return

        # 5. Insert Enrollment Ticket
        if "INSERT INTO ENROLLMENT_TICKET" in nq:
            t_id, r_id, t_hash, iss_by, exp_at = p[0], p[1], p[2], p[3], p[4]
            ticket_data = {
                "id": str(t_id),
                "roster_id": str(r_id),
                "token_hash": bytes(t_hash) if not isinstance(t_hash, bytes) else t_hash,
                "issued_by": str(iss_by),
                "expires_at": exp_at,
                "used_at": None,
                "device_id": None,
            }
            if self.connection.autocommit:
                self.db.enrollment_tickets[ticket_data["token_hash"]] = ticket_data
            else:
                self.connection.staged_ticket_inserts.append(ticket_data)
            return

        # 6. Select Enrollment Ticket FOR UPDATE
        if "FROM ENROLLMENT_TICKET" in nq and "TOKEN_HASH = %S" in nq:
            t_hash = bytes(p[0]) if not isinstance(p[0], bytes) else p[0]
            ticket = None
            for t in reversed(self.connection.staged_ticket_inserts):
                if t["token_hash"] == t_hash:
                    ticket = t
                    break
            if not ticket:
                ticket = self.db.enrollment_tickets.get(t_hash)

            if ticket:
                self.result = [(
                    ticket["id"], ticket["roster_id"], ticket["issued_by"],
                    ticket["expires_at"], ticket["used_at"], ticket["device_id"]
                )]
            else:
                self.result = []
            return

        # 7. Insert Device
        if "INSERT INTO DEVICE" in nq:
            d_id, r_id, pubkey, platform, reg_at = p[0], p[1], p[2], p[3], p[4]
            dev_data = {
                "id": str(d_id),
                "roster_id": str(r_id),
                "pubkey": bytes(pubkey) if not isinstance(pubkey, bytes) else pubkey,
                "platform": str(platform),
                "registered_at": reg_at,
                "revoked_at": None,
            }
            if self.connection.autocommit:
                self.db.devices[dev_data["id"]] = dev_data
            else:
                self.connection.staged_device_inserts.append(dev_data)
            return

        # 8. Update Enrollment Ticket
        if "UPDATE ENROLLMENT_TICKET" in nq:
            used_at, dev_id, t_id = p[0], p[1], str(p[2])
            for t in self.connection.staged_ticket_inserts:
                if t["id"] == t_id:
                    t["used_at"] = used_at
                    t["device_id"] = str(dev_id)
            def _apply():
                for t in self.db.enrollment_tickets.values():
                    if t["id"] == t_id:
                        t["used_at"] = used_at
                        t["device_id"] = str(dev_id)
                        break
            if self.connection.autocommit:
                _apply()
            else:
                self.connection.staged_actions.append(_apply)
            return

        # 9. Insert Session
        if "INSERT INTO SESSION" in nq:
            if "CALL_SID" in nq:
                s_id, s_hash, r_id, call_sid, cr_at, exp_at = p[0], p[1], p[2], p[3], p[4], p[5]
                dev_id = None
            else:
                s_id, s_hash, r_id, dev_id, cr_at, exp_at = p[0], p[1], p[2], p[3], p[4], p[5]
                call_sid = None

            sess_data = {
                "id": str(s_id),
                "token_hash": bytes(s_hash) if not isinstance(s_hash, bytes) else s_hash,
                "roster_id": str(r_id),
                "device_id": str(dev_id) if dev_id else None,
                "call_sid": str(call_sid) if call_sid else None,
                "created_at": cr_at,
                "expires_at": exp_at,
                "revoked_at": None,
                "pin_failed": 0,
                "pin_locked_until": None,
            }
            if self.connection.autocommit:
                self.db.sessions[sess_data["id"]] = sess_data
            else:
                self.connection.staged_session_inserts.append(sess_data)
            return

        # 10. Select Roster
        if "FROM ROSTER WHERE ID = %S" in nq:
            r_id = str(p[0])
            roster = self.db.rosters.get(r_id)
            if roster:
                self.result = [(
                    roster["facility_id"], roster["role_slot"],
                    roster["phone_e164"], roster["pin_hash"]
                )]
            else:
                self.result = []
            return

        # 11. Select Session JOIN Roster
        if "FROM SESSION S" in nq and "JOIN ROSTER R" in nq:
            token_hash = p[0]
            sid_or_call = p[1]
            if not isinstance(token_hash, bytes):
                token_hash = bytes(token_hash)

            target_sess = None
            for s in reversed(self.connection.staged_session_inserts):
                if s.get("token_hash") == token_hash or (s.get("call_sid") and s.get("call_sid") == str(sid_or_call)):
                    target_sess = s
                    break
            if not target_sess:
                for s in self.db.sessions.values():
                    if s.get("token_hash") == token_hash or (s.get("call_sid") and s.get("call_sid") == str(sid_or_call)):
                        target_sess = s
                        break

            if target_sess:
                r = self.db.rosters.get(target_sess.get("roster_id"), {})
                self.result = [(
                    target_sess.get("id"), target_sess.get("token_hash"), target_sess.get("roster_id"),
                    target_sess.get("device_id"), target_sess.get("call_sid"), target_sess.get("created_at"),
                    target_sess.get("expires_at"), target_sess.get("revoked_at"), target_sess.get("pin_failed", 0),
                    target_sess.get("pin_locked_until"),
                    r.get("facility_id"), r.get("role_slot"), r.get("phone_e164"), r.get("pin_hash")
                )]
            else:
                self.result = []
            return

        # 12. Update Session pin_failed / pin_locked_until
        if "UPDATE SESSION" in nq and "SET PIN_FAILED = %S, PIN_LOCKED_UNTIL = %S" in nq:
            pin_failed, pin_locked_until, sess_id = p[0], p[1], str(p[2])
            for s in self.connection.staged_session_inserts:
                if s["id"] == sess_id:
                    s["pin_failed"] = int(pin_failed)
                    s["pin_locked_until"] = pin_locked_until
            def _apply_pin():
                s = self.db.sessions.get(sess_id)
                if s:
                    s["pin_failed"] = int(pin_failed)
                    s["pin_locked_until"] = pin_locked_until
            if self.connection.autocommit:
                _apply_pin()
            else:
                self.connection.staged_actions.append(_apply_pin)
            return

        # 13. Reset Session pin_failed
        if "UPDATE SESSION" in nq and "SET PIN_FAILED = 0, PIN_LOCKED_UNTIL = NULL" in nq:
            sess_id = str(p[0])
            for s in self.connection.staged_session_inserts:
                if s["id"] == sess_id:
                    s["pin_failed"] = 0
                    s["pin_locked_until"] = None
            def _reset_pin():
                s = self.db.sessions.get(sess_id)
                if s:
                    s["pin_failed"] = 0
                    s["pin_locked_until"] = None
            if self.connection.autocommit:
                _reset_pin()
            else:
                self.connection.staged_actions.append(_reset_pin)
            return

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if self._row_index < len(self.result):
            row = self.result[self._row_index]
            self._row_index += 1
            return row
        return None

    def fetchall(self) -> list[Tuple[Any, ...]]:
        rows = self.result[self._row_index:]
        self._row_index = len(self.result)
        return rows

    def close(self) -> None:
        pass


class MockConnection:
    """Mock database connection maintaining transaction state and isolation."""

    def __init__(self, db: MockDatabase, autocommit: bool = False) -> None:
        self.db = db
        self.autocommit = autocommit
        self.held_locks: Set[str] = set()
        self.session_gucs: Dict[str, str] = {}
        self.staged_ticket_inserts: list[Dict[str, Any]] = []
        self.staged_device_inserts: list[Dict[str, Any]] = []
        self.staged_session_inserts: list[Dict[str, Any]] = []
        self.staged_actions: list[Any] = []
        self.held_row_locks: list[Any] = []

    def cursor(self) -> MockCursor:
        return MockCursor(self)

    def execute(self, query: str, params: Optional[Any] = None) -> MockCursor:
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self) -> None:
        # Apply staged ticket inserts
        for t in self.staged_ticket_inserts:
            self.db.enrollment_tickets[t["token_hash"]] = t
        self.staged_ticket_inserts.clear()

        # Apply staged device inserts
        for d in self.staged_device_inserts:
            self.db.devices[d["id"]] = d
        self.staged_device_inserts.clear()

        # Apply staged session inserts
        for s in self.staged_session_inserts:
            self.db.sessions[s["id"]] = s
        self.staged_session_inserts.clear()

        # Apply staged actions
        for action in self.staged_actions:
            action()
        self.staged_actions.clear()

        # Release advisory locks held in transaction
        for lock_key in list(self.held_locks):
            self.db.advisory_locks.discard(lock_key)
        self.held_locks.clear()

        # Release row locks held in transaction
        for rk in self.held_row_locks:
            try:
                rk.release()
            except Exception:
                pass
        self.held_row_locks.clear()

    def rollback(self) -> None:
        # Discard staged changes
        self.staged_ticket_inserts.clear()
        self.staged_device_inserts.clear()
        self.staged_session_inserts.clear()
        self.staged_actions.clear()

        # Release advisory locks
        for lock_key in list(self.held_locks):
            self.db.advisory_locks.discard(lock_key)
        self.held_locks.clear()

        # Release row locks held in transaction
        for rk in self.held_row_locks:
            try:
                rk.release()
            except Exception:
                pass
        self.held_row_locks.clear()

    def close(self) -> None:
        if self.staged_ticket_inserts or self.staged_device_inserts or self.staged_session_inserts or self.staged_actions or self.held_row_locks:
            self.rollback()

    def __enter__(self) -> "MockConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        elif not self.autocommit:
            self.commit()


class MockConnectionPool:
    """Mock connection pool providing MockConnection instances."""

    def __init__(self, db: MockDatabase, autocommit: bool = False, min_size: int = 2, max_size: int = 10) -> None:
        self.db = db
        self.autocommit = autocommit
        self.min_size = min_size
        self.max_size = max_size

    @contextlib.contextmanager
    def connection(self) -> Generator[MockConnection, None, None]:
        conn = MockConnection(self.db, autocommit=self.autocommit)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def close(self) -> None:
        pass


# =============================================================================
# Global Connection Pools & Lifecycle
# =============================================================================

# Shared database mock store for offline testing
GLOBAL_MOCK_DB = MockDatabase()

# Global connection pools
main_pool: Any = None
autonomous_pool: Any = None
_is_mock_mode: bool = False


def reset_mock_db() -> None:
    """Resets the mock database store for clean test isolation."""
    global GLOBAL_MOCK_DB
    GLOBAL_MOCK_DB.facilities.clear()
    GLOBAL_MOCK_DB.rosters.clear()
    GLOBAL_MOCK_DB.devices.clear()
    GLOBAL_MOCK_DB.enrollment_tickets.clear()
    GLOBAL_MOCK_DB.sessions.clear()
    GLOBAL_MOCK_DB.referrals.clear()
    GLOBAL_MOCK_DB.advisory_locks.clear()
    GLOBAL_MOCK_DB.seed_defaults()
    init_pools(use_mock=True)


def init_pools(
    app_dsn: Optional[str] = None,
    autonomous_dsn: Optional[str] = None,
    min_size: int = 10,
    max_size: int = 220,
    autonomous_min_size: int = 2,
    autonomous_max_size: int = 20,
    use_mock: Optional[bool] = None,
) -> None:
    """Initializes main_pool (high concurrency, READ COMMITTED) and

    autonomous_pool (autocommit=True, dedicated to security failure logging).
    """
    global main_pool, autonomous_pool, _is_mock_mode

    settings = get_settings(enforce_guards=False)
    app_dsn = app_dsn or settings.APP_DSN
    autonomous_dsn = autonomous_dsn or settings.AUTONOMOUS_DSN or app_dsn

    # Determine if mock mode should be used
    if use_mock is True:
        _is_mock_mode = True
    elif use_mock is False:
        _is_mock_mode = False
    else:
        # Default to mock mode if PostgreSQL is unreachable or running unit test suite
        if "pytest" in sys.modules or os.environ.get("RHP_TEST_MOCK_DB", "1") == "1":
            _is_mock_mode = True
        else:
            _is_mock_mode = False

    if _is_mock_mode:
        main_pool = MockConnectionPool(
            GLOBAL_MOCK_DB,
            autocommit=False,
            min_size=min_size,
            max_size=max_size,
        )
        autonomous_pool = MockConnectionPool(
            GLOBAL_MOCK_DB,
            autocommit=True,
            min_size=autonomous_min_size,
            max_size=autonomous_max_size,
        )
        return

    # Real PostgreSQL connection pool initialization
    if HAS_PSYCOPG3:
        main_pool = psycopg_pool.ConnectionPool(
            app_dsn,
            min_size=min_size,
            max_size=max_size,
            open=True,
        )
        autonomous_pool = psycopg_pool.ConnectionPool(
            autonomous_dsn,
            min_size=autonomous_min_size,
            max_size=autonomous_max_size,
            kwargs={"autocommit": True},
            open=True,
        )
    elif HAS_PSYCOPG2:
        class Psycopg2PoolWrapper:
            def __init__(self, dsn: str, minconn: int, maxconn: int, autocommit: bool = False):
                self._pool = psycopg2.pool.ThreadedConnectionPool(minconn, maxconn, dsn)
                self._autocommit = autocommit

            @contextlib.contextmanager
            def connection(self):
                conn = self._pool.getconn()
                try:
                    conn.autocommit = self._autocommit
                    yield conn
                finally:
                    self._pool.putconn(conn)

            def close(self):
                self._pool.closeall()

        main_pool = Psycopg2PoolWrapper(app_dsn, min_size, max_size, autocommit=False)
        autonomous_pool = Psycopg2PoolWrapper(
            autonomous_dsn, autonomous_min_size, autonomous_max_size, autocommit=True
        )
    else:
        # Fallback to mock pool if no psycopg driver is installed
        _is_mock_mode = True
        main_pool = MockConnectionPool(GLOBAL_MOCK_DB, autocommit=False)
        autonomous_pool = MockConnectionPool(GLOBAL_MOCK_DB, autocommit=True)


def close_pools() -> None:
    """Closes both connection pools cleanly."""
    global main_pool, autonomous_pool
    if main_pool is not None:
        try:
            main_pool.close()
        except Exception:
            pass
        main_pool = None
    if autonomous_pool is not None:
        try:
            autonomous_pool.close()
        except Exception:
            pass
        autonomous_pool = None


@contextlib.contextmanager
def get_main_connection() -> Generator[Any, None, None]:
    """Yields a database connection from main_pool."""
    global main_pool
    if main_pool is None:
        init_pools()
    with main_pool.connection() as conn:
        yield conn


@contextlib.contextmanager
def get_autonomous_connection() -> Generator[Any, None, None]:
    """Yields a dedicated autonomous database connection (autocommit=True)."""
    global autonomous_pool
    if autonomous_pool is None:
        init_pools()
    with autonomous_pool.connection() as conn:
        yield conn


# =============================================================================
# Lock & Monotone Timestamp Helpers (§5 Steps 1, 4; Closures F11, I14, I16)
# =============================================================================

def try_advisory_idem_lock(conn: Any, roster_id: Union[UUID, str], key: str) -> bool:
    """Attempts to acquire a transaction-scoped non-blocking advisory lock.

    Returns True if acquired, False if already locked by a concurrent transaction.
    Key is formatted as f"{roster_id}:{key}" per Architecture §5 Step 1.
    """
    lock_key = f"{roster_id}:{key}"
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0::bigint));",
            (lock_key,),
        )
        row = cursor.fetchone()
        return bool(row[0]) if row else False
    finally:
        cursor.close()


def lock_referral_first(conn: Any, referral_id: Union[UUID, str]) -> Optional[Tuple[Any, ...]]:
    """Locks the referral row FOR UPDATE and sets the transaction GUC 'rhp.locked_referral'.

    Enforces invariant I14 and triggers lk_referral / rhp_require_lock.
    """
    ref_id_str = str(referral_id)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM referral WHERE id = %s FOR UPDATE;",
            (ref_id_str,),
        )
        row = cursor.fetchone()
        cursor.execute(
            "SELECT set_config('rhp.locked_referral', %s, true);",
            (ref_id_str,),
        )
        return row
    finally:
        cursor.close()


def get_monotone_ts(conn: Any, head_ts: Optional[datetime] = None) -> datetime:
    """Computes monotone server timestamp ts = GREATEST(clock_timestamp(), head_ts).

    Enforces closures F11, I16.
    """
    cursor = conn.cursor()
    try:
        if head_ts is None:
            cursor.execute("SELECT clock_timestamp();")
        else:
            cursor.execute(
                "SELECT GREATEST(clock_timestamp(), %s);",
                (head_ts,),
            )
        row = cursor.fetchone()
        ts = row[0]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    finally:
        cursor.close()

