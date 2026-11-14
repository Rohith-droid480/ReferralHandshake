#!/usr/bin/env bash
# =============================================================================
# ReferralHandshake Protocol RHP-1 — Provision Isolated Scratch Database (F20)
# Provisions rhp_scratch_broken for BROKEN_BUILD=1 testing.
# EXPLICITLY DROPS one_lease index to allow concurrency double-lease demonstrations.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/../scripts/make_scratch.sh" "$@"

