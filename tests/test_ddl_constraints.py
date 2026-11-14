"""Test Suite for 24-Table PostgreSQL 16 DDL, Triggers, Constraints & Role Grants (ST-3, T-F4).

Specification Anchors:
- Architecture §7: Complete 24-Table Relational Schema & Trigger Logic (F4)
- Architecture §18: Invariants I1, I2, I4, I5, I7, I9, I10, I11, I12, I14, I16
- BUILD_PLAN §1.2: Verification Gate (ST-3 / T-F4)
"""

import re
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# 24 Locked Tables from Architecture §7 and BUILD_PLAN §1.2
EXPECTED_24_TABLES = [
    "facility",
    "roster",
    "facility_capability",
    "need_class_requirement",
    "catchment_chain",
    "device",
    "enrollment_ticket",
    "session",
    "referral",
    "offer",
    "offer_resource_confirmation",
    "deadline",
    "event",
    "key_version",
    "event_secret",
    "clinical_payload",
    "payload_grant",
    "telemetry",
    "idempotency",
    "inbox",
    "outbox",
    "rejected_command",
    "checkpoint",
    "heartbeat",
]

# 12 Locked Triggers from Architecture §7
EXPECTED_12_TRIGGERS = [
    "event_ao",
    "checkpoint_ao",
    "rejected_ao",
    "event_guard",
    "lk_referral",
    "lk_offer",
    "lk_deadline",
    "lk_event",
    "lk_grant",
    "lk_outbox",
    "i1_pending_deadline",
    "offer_chain_guard",
]


@pytest.fixture(scope="module")
def schema_sql() -> str:
    schema_path = REPO_ROOT / "db" / "01_schema.sql"
    assert schema_path.exists(), f"Missing schema file: {schema_path}"
    with open(schema_path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def roles_sql() -> str:
    roles_path = REPO_ROOT / "db" / "02_roles.sql"
    assert roles_path.exists(), f"Missing roles file: {roles_path}"
    with open(roles_path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def seed_sql() -> str:
    seed_path = REPO_ROOT / "db" / "03_seed.sql"
    assert seed_path.exists(), f"Missing seed file: {seed_path}"
    with open(seed_path, "r", encoding="utf-8") as f:
        return f.read()


def test_st3_exact_24_tables_defined(schema_sql: str):
    """ST-3: Verifies that exactly the 24 locked tables are defined with CREATE TABLE."""
    created_tables = re.findall(r"CREATE\s+TABLE\s+([a-zA-Z0-9_]+)", schema_sql, re.IGNORECASE)
    assert len(created_tables) == 24, f"Expected exactly 24 tables, found {len(created_tables)}: {created_tables}"
    assert created_tables == EXPECTED_24_TABLES, f"Table list or sequence mismatch:\nFound: {created_tables}\nExpected: {EXPECTED_24_TABLES}"


def test_st3_all_12_triggers_defined(schema_sql: str):
    """ST-3: Verifies that all 12 append-only, lock guard, and constraint triggers are defined."""
    trigger_names = re.findall(r"CREATE\s+(?:CONSTRAINT\s+)?TRIGGER\s+([a-zA-Z0-9_]+)", schema_sql, re.IGNORECASE)
    assert len(trigger_names) == 12, f"Expected exactly 12 triggers, found {len(trigger_names)}: {trigger_names}"
    for expected_trig in EXPECTED_12_TRIGGERS:
        assert expected_trig in trigger_names, f"Missing trigger: {expected_trig}"


def test_i2_one_lease_partial_unique_index(schema_sql: str):
    """Invariant I2: Partial unique index one_lease on offer(referral_id) WHERE status = 'ACCEPTED'."""
    pattern = r"CREATE\s+UNIQUE\s+INDEX\s+one_lease\s+ON\s+offer\s*\(\s*referral_id\s*\)\s*WHERE\s+status\s*=\s*'ACCEPTED'"
    assert re.search(pattern, schema_sql, re.IGNORECASE), "Missing or malformed one_lease partial unique index (I2)"


def test_i10_one_active_grant_partial_unique_index(schema_sql: str):
    """Invariant I10: Partial unique index one_active_grant on payload_grant(referral_id, facility_id) WHERE revoked_at IS NULL."""
    pattern = r"CREATE\s+UNIQUE\s+INDEX\s+one_active_grant\s+ON\s+payload_grant\s*\(\s*referral_id\s*,\s*facility_id\s*\)\s*WHERE\s+revoked_at\s+IS\s+NULL"
    assert re.search(pattern, schema_sql, re.IGNORECASE), "Missing or malformed one_active_grant partial unique index (I10)"


def test_deferrable_referral_lease_fk(schema_sql: str):
    """Closure F4: Circular foreign key referral.lease_offer_id -> offer(id) is DEFERRABLE INITIALLY DEFERRED."""
    pattern = r"ALTER\s+TABLE\s+referral\s+ADD\s+CONSTRAINT\s+referral_lease_fk\s+FOREIGN\s+KEY\s*\(\s*lease_offer_id\s*\)\s*REFERENCES\s+offer\s*\(\s*id\s*\)\s*DEFERRABLE\s+INITIALLY\s+DEFERRED"
    assert re.search(pattern, schema_sql, re.IGNORECASE), "Missing DEFERRABLE INITIALLY DEFERRED referral_lease_fk"


def test_deferrable_i1_pending_deadline_trigger(schema_sql: str):
    """Invariant I1: Trigger i1_pending_deadline on referral is DEFERRABLE INITIALLY DEFERRED."""
    pattern = r"CREATE\s+CONSTRAINT\s+TRIGGER\s+i1_pending_deadline\s+AFTER\s+INSERT\s+OR\s+UPDATE\s+ON\s+referral\s+DEFERRABLE\s+INITIALLY\s+DEFERRED"
    assert re.search(pattern, schema_sql, re.IGNORECASE), "Missing DEFERRABLE INITIALLY DEFERRED constraint trigger i1_pending_deadline"


def test_append_only_triggers(schema_sql: str):
    """Closure F4: event, checkpoint, and rejected_command are protected by BEFORE UPDATE OR DELETE triggers."""
    for tbl in ("event", "checkpoint", "rejected_command"):
        pattern = rf"CREATE\s+TRIGGER\s+[a-zA-Z0-9_]+\s+BEFORE\s+UPDATE\s+OR\s+DELETE\s+ON\s+{tbl}"
        assert re.search(pattern, schema_sql, re.IGNORECASE), f"Missing append-only trigger on table {tbl}"


def test_i14_lock_guard_triggers(schema_sql: str):
    """Invariant I14: Lock check triggers enforce rhp_require_lock() on all mutating contract tables."""
    for tbl in ("referral", "offer", "deadline", "event", "payload_grant", "outbox"):
        pattern = rf"CREATE\s+TRIGGER\s+lk_[a-zA-Z0-9_]+\s+BEFORE\s+(?:INSERT|UPDATE|INSERT\s+OR\s+UPDATE)\s+ON\s+{tbl}\s+FOR\s+EACH\s+ROW\s+EXECUTE\s+FUNCTION\s+rhp_require_lock"
        assert re.search(pattern, schema_sql, re.IGNORECASE), f"Missing lock check trigger on {tbl}"


def test_rhp_allowed_and_detail_ok_refinements(schema_sql: str):
    """Refinements: OFFER_DECLINED includes reason and facility; OFFER_SOFT_EXPIRED includes step and facility."""
    assert "WHEN t='OFFER_DECLINED' THEN ARRAY['reason','facility']" in schema_sql
    assert "WHEN t='OFFER_SOFT_EXPIRED' THEN ARRAY['step','facility']" in schema_sql
    assert "rhp_detail_ok" in schema_sql


def test_least_privilege_roles(roles_sql: str):
    """Closure F4 / F17: Three roles defined with least-privilege grants and append-only revocations."""
    for role in ("rhp_app", "rhp_monitor", "rhp_witness"):
        assert f"rolname = '{role}'" in roles_sql, f"Role {role} creation missing from db/02_roles.sql"

    # rhp_app cannot UPDATE or DELETE from append-only audit tables
    assert "REVOKE UPDATE, DELETE ON event, checkpoint, rejected_command FROM rhp_app" in roles_sql

    # rhp_monitor has audit read access to state, but no access to PHI or secrets
    assert "GRANT SELECT ON event, referral, offer, deadline" in roles_sql
    # Column-level grant on roster for monitor strictly excludes phone_e164 and pin_hash
    assert "GRANT SELECT (id, facility_id, role_slot, slot_no, valid_from, valid_to) ON roster TO rhp_monitor" in roles_sql
    assert "pin_hash" not in roles_sql.split("GRANT SELECT (id, facility_id, role_slot, slot_no, valid_from, valid_to) ON roster")[1].split(";")[0]

    # rhp_witness has SELECT on event/referral/checkpoint and INSERT on checkpoint
    assert "GRANT SELECT ON event, referral, checkpoint TO rhp_witness" in roles_sql
    assert "GRANT INSERT ON checkpoint TO rhp_witness" in roles_sql


def test_synthetic_district_seed_data(seed_sql: str):
    """Sub-segment 1.3: Verifies facilities across tiers, 20 JUDGE_DESK slots, capabilities, and test devices."""
    # 6 facilities
    for code in (
        "PHC_CHANNAPATNA",
        "CHC_RAMANAGARA",
        "FRU_KANAKAPURA",
        "DH_MANDYA",
        "MC_BENGALURU_OB",
        "DISPATCH_108_CENTRAL",
    ):
        assert code in seed_sql, f"Missing synthetic facility {code} in seed.sql"

    # Need class requirements
    assert "OBSTETRIC_EMERGENCY" in seed_sql
    assert "'OT'" in seed_sql
    assert "'BLOOD'" in seed_sql
    assert "'ANAESTHETIST'" in seed_sql
    assert "'NICU'" in seed_sql

    # 20 JUDGE_DESK slots generated
    assert "JUDGE_DESK" in seed_sql
    assert "generate_series(1, 20)" in seed_sql

    # Argon2id pin hashes present
    assert "$argon2id$v=19$m=65536,t=2,p=2$" in seed_sql

    # Pre-registered test devices
    assert "INSERT INTO device" in seed_sql
    assert "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a" in seed_sql
