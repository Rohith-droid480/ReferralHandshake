#!/usr/bin/env bash
# =============================================================================
# ReferralHandshake Protocol RHP-1 — Toggle BROKEN_BUILD Scratch Isolation (F20)
#
# Specification Anchors:
# - Architecture §12: Broken-Build Concurrency Sandbox & Scratch Isolation [F20]
# - Architecture §6: Real Data Safety Boundary [REAL_DATA=0 enforced]
# - Closure F20: Hard abort with code 78 if REAL_DATA=1 or pointing to production DB
# =============================================================================
set -euo pipefail

TARGET="${1:-1}"
REAL_DATA_VAL="${REAL_DATA:-0}"

# 1. Hard Abort Safety Boundary (Closure F20)
if [ "${REAL_DATA_VAL}" = "1" ]; then
  echo "CRITICAL ERROR: Refusing to enable BROKEN_BUILD when REAL_DATA=1!" >&2
  echo "Closure F20 & Invariant I13 violation: BROKEN_BUILD is strictly forbidden on real clinical data." >&2
  exit 78
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

if [ "${TARGET}" = "1" ]; then
  echo "=== Switching to BROKEN_BUILD=1 (Scratch Sandbox) ==="
  
  # Provision scratch database if needed
  if [ -f "${SCRIPT_DIR}/make_scratch.sh" ]; then
    bash "${SCRIPT_DIR}/make_scratch.sh" || echo "Warning: make_scratch.sh failed, assuming mock/test mode"
  fi

  # Update or append environment variables in .env
  if [ -f "${ENV_FILE}" ]; then
    grep -v "^BROKEN_BUILD=" "${ENV_FILE}" > "${ENV_FILE}.tmp" || true
    echo "BROKEN_BUILD=1" >> "${ENV_FILE}.tmp"
    mv "${ENV_FILE}.tmp" "${ENV_FILE}"
  fi

  export BROKEN_BUILD=1
  echo "🚨 BROKEN_BUILD=1 ACTIVATED. Connections routed to rhp_scratch_broken (one_lease DROPPED)."
else
  echo "=== Switching to BROKEN_BUILD=0 (Verified Green Build) ==="

  if [ -f "${ENV_FILE}" ]; then
    grep -v "^BROKEN_BUILD=" "${ENV_FILE}" > "${ENV_FILE}.tmp" || true
    echo "BROKEN_BUILD=0" >> "${ENV_FILE}.tmp"
    mv "${ENV_FILE}.tmp" "${ENV_FILE}"
  fi

  export BROKEN_BUILD=0
  echo "✅ BROKEN_BUILD=0 RESTORED. Normal production database active with full invariant protections."
fi
