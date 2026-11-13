"""ReferralHandshake Protocol RHP-1 — Automated Self-Audit ST-5 (Claims Lexicon & Residual Linter).

Specification Anchors:
- Architecture §19: Claims Discipline & Forbidden Words [Closure F15]
- Invariant F15: Bounded & Open Residual Claims Lint
- Test Anchor: ST-5 / T-F15 / T-L3
"""

import subprocess
import sys
import pytest


def test_st5_claims_lexicon_zero_violations():
    """ST-5 / T-F15: Runs scripts/check_claims.py across the repository and verifies 0 violations."""
    cmd = [sys.executable, "scripts/check_claims.py"]
    res = subprocess.run(cmd, capture_output=True, text=True)

    assert res.returncode == 0, f"ST-5 Claims Linter detected violations:\n{res.stderr}\n{res.stdout}"
    assert "PASS (0 violations)" in res.stdout

