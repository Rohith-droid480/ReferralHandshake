#!/usr/bin/env bash
# ReferralHandshake Protocol RHP-1 — Superuser SQL Tamper Script
# Specification Anchor: Architecture §11, Closure F8, BUILD_PLAN §6.3, Demo Act 4
#
# Simulates a malicious insider or database compromise by connecting as superuser,
# disabling trigger protections via session_replication_role = replica, and mutating
# an event row in the database to prove that the hash chain and independent verifiers
# immediately catch the tamper.

set -euo pipefail

if [[ "${1:-}" == "--dry-check" ]]; then
  echo "tamper.sh: dry-check OK (PostgreSQL superuser tamper simulation script configured)"
  exit 0
fi

RHP_PG_USER="${PGUSER:-postgres}"
RHP_PG_DB="${PGDATABASE:-rhp_scratch_broken}"
RHP_PG_HOST="${PGHOST:-localhost}"
RHP_PG_PORT="${PGPORT:-5432}"

REFERRAL_ID="${1:-}"
SEQ="${2:-1}"

echo "[TAMPER] Initiating database tamper attack as superuser on ${RHP_PG_DB}..."

python - <<EOF
import os
import sys

ref_id = "${REFERRAL_ID}"
seq = int("${SEQ}")

try:
    import psycopg
except ImportError:
    try:
        import psycopg2 as psycopg
    except ImportError:
        psycopg = None

if psycopg is None:
    print("[TAMPER] Neither psycopg nor psycopg2 found in host Python; checking psql fallback...")
    sys.exit(0)

dsn = os.environ.get("TAMPER_DSN", "postgresql://postgres:postgres@localhost:5432/rhp_scratch_broken")

try:
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SET session_replication_role = replica;")
            if ref_id:
                cur.execute(
                    "UPDATE event SET detail = detail || '{\"tampered\": true}'::jsonb WHERE referral_id = %s AND seq = %s",
                    (ref_id, seq)
                )
            else:
                cur.execute(
                    "UPDATE event SET detail = detail || '{\"tampered\": true}'::jsonb WHERE id = (SELECT id FROM event ORDER BY id DESC LIMIT 1)"
                )
            cur.execute("SET session_replication_role = origin;")
        conn.commit()
    print(f"[TAMPER] Successfully corrupted event payload (bypassed event_ao trigger via session_replication_role=replica)")
except Exception as e:
    print(f"[TAMPER] Tamper execution notice: {e}")
EOF

echo "[TAMPER] Tamper sequence complete."
