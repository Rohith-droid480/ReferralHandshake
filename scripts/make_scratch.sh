#!/usr/bin/env bash
# =============================================================================
# ReferralHandshake Protocol RHP-1 — Provision Isolated Scratch Database (F20)
# Provisions rhp_scratch_broken for BROKEN_BUILD=1 testing.
# EXPLICITLY DROPS one_lease index to allow concurrency double-lease demonstrations.
# =============================================================================
set -euo pipefail

PGHOST="${POSTGRES_HOST:-localhost}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-postgres}"
export PGPASSWORD="${POSTGRES_PASSWORD:-rhp_pg_super_local_dev_only}"

SCRATCH_DB="${RHP_SCRATCH_DB:-rhp_scratch_broken}"
SCRATCH_USER="${RHP_SCRATCH_USER:-rhp_scratch_app}"
SCRATCH_PASSWORD="${RHP_SCRATCH_PASSWORD:-rhp_scratch_local_dev_only}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Determine psql execution method (direct or via running rhp-pg docker container)
if command -v psql >/dev/null 2>&1; then
  run_psql() {
    psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "$@"
  }
elif command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^rhp-pg$"; then
  echo "psql not found locally; executing via rhp-pg docker container..."
  run_psql() {
    docker exec -i -e PGPASSWORD="${PGPASSWORD}" rhp-pg psql -U "${PGUSER}" "$@"
  }
else
  echo "ERROR: Neither psql nor running rhp-pg docker container found." >&2
  exit 1
fi

echo "=== Provisioning Scratch Database: ${SCRATCH_DB} on ${PGHOST}:${PGPORT} ==="

# 1. Terminate active connections and recreate scratch database
run_psql -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${SCRATCH_DB}' AND pid <> pg_backend_pid();"
run_psql -d postgres -c "DROP DATABASE IF EXISTS ${SCRATCH_DB};"
run_psql -d postgres -c "CREATE DATABASE ${SCRATCH_DB};"

# 2. Provision scratch user
run_psql -d postgres -c "
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${SCRATCH_USER}') THEN
      CREATE ROLE ${SCRATCH_USER} WITH LOGIN PASSWORD '${SCRATCH_PASSWORD}';
    ELSE
      ALTER ROLE ${SCRATCH_USER} WITH LOGIN PASSWORD '${SCRATCH_PASSWORD}';
    END IF;
  END \$\$;
"

# 3. Load base schema into scratch database
echo "Loading db/01_schema.sql into ${SCRATCH_DB}..."
run_psql -d "${SCRATCH_DB}" < "${REPO_ROOT}/db/01_schema.sql"

# 4. Load roles and grant scratch user permissions
echo "Loading db/02_roles.sql into ${SCRATCH_DB}..."
run_psql -d "${SCRATCH_DB}" < "${REPO_ROOT}/db/02_roles.sql"

run_psql -d "${SCRATCH_DB}" -c "
  GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO ${SCRATCH_USER};
  GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ${SCRATCH_USER};
  REVOKE UPDATE, DELETE ON event, checkpoint, rejected_command FROM ${SCRATCH_USER};
  GRANT DELETE ON event_secret, clinical_payload, idempotency, telemetry TO ${SCRATCH_USER};
"

# 5. Core F20 Defect Injection: Drop one_lease index
echo "Applying F20 defect: Dropping one_lease partial unique index on ${SCRATCH_DB}..."
run_psql -d "${SCRATCH_DB}" -c "DROP INDEX IF EXISTS one_lease;"

echo "=== Scratch Database ${SCRATCH_DB} Ready (one_lease DROPPED) ==="
