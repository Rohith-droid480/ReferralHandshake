#!/usr/bin/env python3
"""
ReferralHandshake (Protocol RHP-1) — Claims & Residual Linter (ST-5 / T-F15)
Scans codebase and artifacts for Architecture §19 forbidden phrases and F15 bare residuals.
Excludes locked specification artifacts and governance documentation that define the rules.
"""

import os
import pathlib
import re
import sys

FORBIDDEN_PHRASES = [
    r"mathematically proven system",
    r"mathematically proven",
    r"mathematically guaranteed",
    r"mathematically impenetrable",
    r"100%\s+bug[- ]free",
    r"bullet[- ]?proof",
    r"airtight",
    r"zero loopholes",
    r"crash[- ]?proof",
    r"immutable log",
    r"abdm compliant",
    r"bsa[- ]certified",
    r"lives saved",
    r"deaths prevented",
    r"reduces maternal mortality",
    r"eliminates ping[- ]?pong",
    r"zero silent drops",
    r"first in the world",
    r"no competitor has this",
    r"blockchain[- ]grade",
    r"legally conclusive",
    r"production ready",
]

EXEMPT_DIRS = {
    ".git",
    "spec",
    "docs",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
}

EXEMPT_FILES = {
    "ReferralHandshake_FINAL_LOCKED_Architecture.md",
    "ReferralHandshake_LOCKED_Problem_Statement_v7.md",
    "ReferralHandshake_v8_LOCKED_Solution.md",
    "AGENTS.md",
    "GEMINI.md",
    "BUILD_PLAN.md",
    "PLAYBOOK.md",
    "README.md",
    "Master Verification & Test Plan.md",
    "failure_and_attack_matrix.md",
    "implementation_plan_environment_setup.md",
    "scope_architectural_locks_constraints.md",
    "project_context_referralhandshake_rhp_1.md",
    "unified_master_agent_rules_teaching_protocol_architecture_guardrails.md",
    "ARCHITECTURE_AND_INVARIANTS_GUARDRAILS.md",
    "project_brief_referralhandshake_rhp_1.md",
    "feature_specification_referralhandshake_rhp_1.md",
    "security_privacy_legal_standards.md",
    "model_prompting_guide.md",
    "check_claims.py",
}

def scan_file(file_path: pathlib.Path) -> list[str]:
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [f"{file_path}: could not read file ({e})"]

    lines = content.splitlines()
    for line_no, line in enumerate(lines, start=1):
        for pattern in FORBIDDEN_PHRASES:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                violations.append(
                    f"{file_path.as_posix()}:{line_no}: forbidden phrase '{match.group(0)}'"
                )

        # F15 check: Matrix row with BOUNDED or OPEN status but bare 'none' or 'None' or empty residual
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                # Look for status columns containing BOUNDED or OPEN
                statuses = [p for p in parts if p in {"BOUNDED", "OPEN"}]
                if statuses:
                    # Check if any column has bare none / empty
                    for idx, p in enumerate(parts):
                        if p.lower() in {"none", "n/a", "nil"}:
                            violations.append(
                                f"{file_path.as_posix()}:{line_no}: F15 bare residual '{p}' without bound/reason"
                            )
    return violations

def main() -> int:
    root = pathlib.Path(".")
    all_violations = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        # Check directory exemptions
        if any(part in EXEMPT_DIRS for part in path.parts):
            continue

        # Check filename exemptions
        if path.name in EXEMPT_FILES:
            continue

        violations = scan_file(path)
        all_violations.extend(violations)

    if all_violations:
        print("ST-5 / T-F15 claims discipline lint: FAIL", file=sys.stderr)
        for v in all_violations:
            print(f"  VIOLATION: {v}", file=sys.stderr)
        return 1

    print("ST-5 / T-F15 claims discipline lint: PASS (0 violations)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
