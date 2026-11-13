-- =============================================================================
-- ReferralHandshake Protocol RHP-1 — Least-Privilege Database Roles & Grants
-- Specification Anchor: Architecture §7, §9, §11, §12 (F4, F8, F17)
-- =============================================================================

-- Idempotent Role Creation with Local Development Passwords
DO $$
BEGIN
  -- Application Role
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rhp_app') THEN
    CREATE ROLE rhp_app WITH LOGIN PASSWORD 'rhp_app_local_dev_only';
  ELSE
    ALTER ROLE rhp_app WITH LOGIN PASSWORD 'rhp_app_local_dev_only';
  END IF;

  -- Independent Runtime Monitor Role (Person B / Read-Only Invariant Auditor)
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rhp_monitor') THEN
    CREATE ROLE rhp_monitor WITH LOGIN PASSWORD 'rhp_monitor_local_dev_only';
  ELSE
    ALTER ROLE rhp_monitor WITH LOGIN PASSWORD 'rhp_monitor_local_dev_only';
  END IF;

  -- Witness Checkpoint Signer Role (Separate OS User 1002 / Ed25519 Merkle Signer)
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rhp_witness') THEN
    CREATE ROLE rhp_witness WITH LOGIN PASSWORD 'rhp_witness_local_dev_only';
  ELSE
    ALTER ROLE rhp_witness WITH LOGIN PASSWORD 'rhp_witness_local_dev_only';
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 1. Application Role Privileges (rhp_app)
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO rhp_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rhp_app;

-- Enforce append-only invariants: application cannot UPDATE or DELETE historical evidence
REVOKE UPDATE, DELETE ON event, checkpoint, rejected_command FROM rhp_app;

-- Grant selective DELETE for cryptographic shredding and TTL cache purges
GRANT DELETE ON event_secret, clinical_payload, idempotency, telemetry TO rhp_app;

-- -----------------------------------------------------------------------------
-- 2. Independent Monitor Role Privileges (rhp_monitor)
-- -----------------------------------------------------------------------------
-- Audit access to state and ledger tables without access to PHI or secrets
GRANT SELECT ON event, referral, offer, deadline, checkpoint, heartbeat, outbox, rejected_command, offer_resource_confirmation, need_class_requirement TO rhp_monitor;

-- Column-level grant on roster: monitor verifies I1-I16 duty roles without reading phone_e164 or pin_hash
GRANT SELECT (id, facility_id, role_slot, slot_no, valid_from, valid_to) ON roster TO rhp_monitor;

-- Liveness heartbeat reporting
GRANT INSERT, UPDATE ON heartbeat TO rhp_monitor;

-- -----------------------------------------------------------------------------
-- 3. Witness Signer Role Privileges (rhp_witness)
-- -----------------------------------------------------------------------------
-- Read-only snapshot of referral heads and event hash chain
GRANT SELECT ON event, referral, checkpoint TO rhp_witness;
GRANT INSERT ON checkpoint TO rhp_witness;
GRANT INSERT, UPDATE ON heartbeat TO rhp_witness;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rhp_witness;
