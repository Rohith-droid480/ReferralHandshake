#!/usr/bin/env bash
# =============================================================================
# ReferralHandshake (Protocol RHP-1) — Master Preflight & Rehearsal Runner
# Specification: BUILD_PLAN §12.3 / Definition of Done Preflight Suite
# =============================================================================

set -e
export PATH="$HOME/.local/bin:$PATH"

echo "=== [1/6] Running Syntax & Compilation Check ==="
python -m py_compile api/rhp/*.py tests/*.py

echo "=== [2/6] Running ST-5 / T-F15 Claims Discipline Linter ==="
python scripts/check_claims.py

echo "=== [3/6] Running Self-Audit Architectural Suites (ST-1..ST-4) ==="
python -m pytest -v tests/test_lock_order.py tests/test_tmax_profiles.py tests/test_ddl_constraints.py tests/test_idempotency_matrix.py

echo "=== [4/6] Running Tier T0 & T1 Acceptance Gates ==="
make gate-t0
make gate-t1

echo "=== [5/6] Running Tier T2 & T3 Acceptance Gates ==="
make gate-t2
make gate-t3

echo "=== [6/6] Running Toxiproxy Chaos & Claims Lexicon Suite ==="
python -m pytest -v tests/test_toxiproxy_chaos.py tests/test_claims_lexicon.py

echo "================================================================="
echo "  ALL PREFLIGHT & MASTER ACCEPTANCE GATES PASSED (T0..T3 CLEAN)  "
echo "================================================================="
exit 0
