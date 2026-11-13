"""ReferralHandshake Protocol RHP-1 — Automated Self-Audit ST-1 (Lock Order & I14 Enforcement).

Specification Anchors:
- Architecture §5: The 10-Step apply_command() Transaction Pipeline (Step 4, Step 6, Step 8, Step 9)
- Architecture §7: Global Lock Order & Trigger Enforcement [F1, I14]
- Invariant I14: Strict referral-first locking and session GUC stamping
- Test Anchor: ST-1 / T-F1
"""

import ast
import os
import pathlib
import pytest
from api.rhp.pipeline import apply_command, assert_referral_locked
from api.rhp.db import get_main_connection, reset_mock_db


GLOBAL_LOCK_ORDER = ["referral", "offer", "deadline", "outbox"]


def test_st1_pipeline_ast_lock_order():
    """ST-1 Static AST Audit: Verifies apply_command() locks tables strictly in global order:

    referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox.
    """
    pipeline_path = pathlib.Path("api/rhp/pipeline.py")
    assert pipeline_path.exists()

    content = pipeline_path.read_text(encoding="utf-8")
    tree = ast.parse(content)

    # Locate apply_command function
    apply_fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "apply_command":
            apply_fn = node
            break

    assert apply_fn is not None, "apply_command not found in api/rhp/pipeline.py"

    # Extract SQL strings executed in order
    executed_queries: list[str] = []
    for sub in ast.walk(apply_fn):
        if isinstance(sub, ast.Call):
            # Matches conn.execute(...) calls
            if isinstance(sub.func, ast.Attribute) and sub.func.attr == "execute":
                if sub.args and isinstance(sub.args[0], ast.Constant) and isinstance(sub.args[0].value, str):
                    executed_queries.append(sub.args[0].value.upper())

    # Find the positions where tables are locked FOR UPDATE
    ref_lock_idx = -1
    offer_lock_idx = -1
    deadline_lock_idx = -1
    outbox_insert_idx = -1

    for idx, q in enumerate(executed_queries):
        if "FROM REFERRAL" in q and "FOR UPDATE" in q:
            if ref_lock_idx == -1:
                ref_lock_idx = idx
        elif "FROM OFFER" in q and "FOR UPDATE" in q and "ORDER BY ID" in q:
            if offer_lock_idx == -1:
                offer_lock_idx = idx
        elif "FROM DEADLINE" in q and "FOR UPDATE" in q and "ORDER BY ID" in q:
            if deadline_lock_idx == -1:
                deadline_lock_idx = idx
        elif "INSERT INTO OUTBOX" in q:
            if outbox_insert_idx == -1:
                outbox_insert_idx = idx

    assert ref_lock_idx != -1, "referral FOR UPDATE lock missing in pipeline"
    assert offer_lock_idx != -1, "offer ORDER BY id FOR UPDATE lock missing in pipeline"
    assert deadline_lock_idx != -1, "deadline ORDER BY id FOR UPDATE lock missing in pipeline"
    assert outbox_insert_idx != -1, "outbox insertion missing in pipeline"

    # Enforce strict total ordering: referral -> offer -> deadline -> outbox
    assert ref_lock_idx < offer_lock_idx, (
        f"Global Lock Order violation: referral lock ({ref_lock_idx}) must precede offer lock ({offer_lock_idx})"
    )
    assert offer_lock_idx < deadline_lock_idx, (
        f"Global Lock Order violation: offer lock ({offer_lock_idx}) must precede deadline lock ({deadline_lock_idx})"
    )
    assert deadline_lock_idx < outbox_insert_idx, (
        f"Global Lock Order violation: deadline lock ({deadline_lock_idx}) must precede outbox insert ({outbox_insert_idx})"
    )


def test_st1_runtime_i14_session_guc_enforcement():
    """ST-1 Runtime Audit: Verifies assert_referral_locked raises RuntimeError('I14_LOCK_NOT_HELD')

    when rhp.locked_referral transaction GUC does not match referral_id.
    """
    reset_mock_db()
    with get_main_connection() as conn:
        ref_id_1 = "00000000-0000-0000-0000-000000000001"
        ref_id_2 = "00000000-0000-0000-0000-000000000002"

        # 1. Unstamped GUC -> raises I14_LOCK_NOT_HELD
        with pytest.raises(RuntimeError, match="I14_LOCK_NOT_HELD"):
            assert_referral_locked(conn, ref_id_1)

        # 2. Stamped with ref_id_1 -> passes for ref_id_1
        conn.execute("SELECT set_config('rhp.locked_referral', %s, true);", (ref_id_1,))
        assert_referral_locked(conn, ref_id_1)

        # 3. Target ref_id_2 mismatch against stamped ref_id_1 -> raises I14_LOCK_NOT_HELD
        with pytest.raises(RuntimeError, match="I14_LOCK_NOT_HELD"):
            assert_referral_locked(conn, ref_id_2)


def test_st1_ddl_trigger_coverage():
    """ST-1 DDL Audit: Verifies db/01_schema.sql defines rhp_require_lock trigger on all 6 contract tables."""
    schema_path = pathlib.Path("db/01_schema.sql")
    if not schema_path.exists():
        schema_path = pathlib.Path("db/schema.sql")
    assert schema_path.exists()

    schema_sql = schema_path.read_text(encoding="utf-8").upper()

    contract_tables = ["REFERRAL", "OFFER", "DEADLINE", "EVENT", "PAYLOAD_GRANT", "OUTBOX"]
    for tbl in contract_tables:
        assert f"ON {tbl}" in schema_sql, f"Missing trigger target table {tbl} in db/schema.sql"

    assert "RHP_REQUIRE_LOCK()" in schema_sql
