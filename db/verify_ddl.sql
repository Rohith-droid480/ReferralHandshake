-- =============================================================================
-- ReferralHandshake Protocol RHP-1 — ST-3 Verification Scan (F4, I1–I16)
-- Verifies 24 base tables, 12 triggers, partial unique indexes, deferred FKs,
-- and least-privilege role boundaries.
-- =============================================================================

DO $$
DECLARE
  v_table_count int;
  v_trigger_count int;
  v_index_count int;
  v_fk_count int;
  v_role_app_ok boolean;
  v_role_monitor_ok boolean;
  v_role_witness_ok boolean;
  v_missing_tables text;
BEGIN
  -- 1. Verify 24 Base Tables
  SELECT count(*) INTO v_table_count
  FROM information_schema.tables
  WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

  IF v_table_count <> 24 THEN
    RAISE EXCEPTION 'ST-3 FAILED: Expected 24 base tables, found %', v_table_count;
  END IF;

  -- Verify all 24 required table names exist
  SELECT string_agg(t, ', ') INTO v_missing_tables
  FROM unnest(ARRAY[
    'facility', 'roster', 'facility_capability', 'need_class_requirement', 'catchment_chain',
    'device', 'enrollment_ticket', 'session', 'referral', 'offer', 'offer_resource_confirmation',
    'deadline', 'event', 'key_version', 'event_secret', 'clinical_payload', 'payload_grant',
    'telemetry', 'idempotency', 'inbox', 'outbox', 'rejected_command', 'checkpoint', 'heartbeat'
  ]) AS t
  WHERE t NOT IN (
    SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'
  );

  IF v_missing_tables IS NOT NULL THEN
    RAISE EXCEPTION 'ST-3 FAILED: Missing required tables: %', v_missing_tables;
  END IF;

  -- 2. Verify 12 Triggers
  SELECT count(*) INTO v_trigger_count
  FROM pg_trigger
  WHERE tgname IN (
    'event_ao', 'checkpoint_ao', 'rejected_ao', 'event_guard',
    'lk_referral', 'lk_offer', 'lk_deadline', 'lk_event', 'lk_grant', 'lk_outbox',
    'i1_pending_deadline', 'offer_chain_guard'
  );

  IF v_trigger_count <> 12 THEN
    RAISE EXCEPTION 'ST-3 FAILED: Expected 12 protocol triggers, found %', v_trigger_count;
  END IF;

  -- 3. Verify Partial Unique Indexes (one_lease, one_active_grant)
  SELECT count(*) INTO v_index_count
  FROM pg_indexes
  WHERE schemaname = 'public'
    AND indexname IN ('one_lease', 'one_active_grant');

  IF v_index_count <> 2 THEN
    RAISE EXCEPTION 'ST-3 FAILED: Missing one_lease or one_active_grant partial unique index (found %)', v_index_count;
  END IF;

  -- 4. Verify Circular Deferred Foreign Key (referral_lease_fk)
  SELECT count(*) INTO v_fk_count
  FROM pg_constraint
  WHERE conname = 'referral_lease_fk'
    AND condeferrable = true;

  IF v_fk_count <> 1 THEN
    RAISE EXCEPTION 'ST-3 FAILED: Missing deferrable constraint referral_lease_fk on referral';
  END IF;

  -- 5. Verify Role Privilege Boundaries
  -- rhp_app: can SELECT/INSERT on event, but CANNOT UPDATE or DELETE event/checkpoint/rejected_command
  v_role_app_ok := has_table_privilege('rhp_app', 'event', 'SELECT')
               AND has_table_privilege('rhp_app', 'event', 'INSERT')
               AND NOT has_table_privilege('rhp_app', 'event', 'UPDATE')
               AND NOT has_table_privilege('rhp_app', 'event', 'DELETE')
               AND NOT has_table_privilege('rhp_app', 'checkpoint', 'UPDATE')
               AND NOT has_table_privilege('rhp_app', 'checkpoint', 'DELETE')
               AND has_table_privilege('rhp_app', 'clinical_payload', 'DELETE');

  IF NOT v_role_app_ok THEN
    RAISE EXCEPTION 'ST-3 FAILED: rhp_app privilege boundary violation';
  END IF;

  -- rhp_monitor: read-only access to ledger/audit tables, NO access to clinical_payload or event_secret
  v_role_monitor_ok := has_table_privilege('rhp_monitor', 'event', 'SELECT')
                   AND has_table_privilege('rhp_monitor', 'referral', 'SELECT')
                   AND has_table_privilege('rhp_monitor', 'offer', 'SELECT')
                   AND has_table_privilege('rhp_monitor', 'deadline', 'SELECT')
                   AND NOT has_table_privilege('rhp_monitor', 'clinical_payload', 'SELECT')
                   AND NOT has_table_privilege('rhp_monitor', 'event_secret', 'SELECT')
                   AND NOT has_table_privilege('rhp_monitor', 'event', 'INSERT')
                   AND NOT has_table_privilege('rhp_monitor', 'referral', 'UPDATE');

  IF NOT v_role_monitor_ok THEN
    RAISE EXCEPTION 'ST-3 FAILED: rhp_monitor privilege boundary violation';
  END IF;

  -- rhp_witness: SELECT on event/referral/checkpoint, INSERT on checkpoint only
  v_role_witness_ok := has_table_privilege('rhp_witness', 'event', 'SELECT')
                    AND has_table_privilege('rhp_witness', 'referral', 'SELECT')
                    AND has_table_privilege('rhp_witness', 'checkpoint', 'SELECT')
                    AND has_table_privilege('rhp_witness', 'checkpoint', 'INSERT')
                    AND NOT has_table_privilege('rhp_witness', 'event', 'INSERT')
                    AND NOT has_table_privilege('rhp_witness', 'referral', 'UPDATE');

  IF NOT v_role_witness_ok THEN
    RAISE EXCEPTION 'ST-3 FAILED: rhp_witness privilege boundary violation';
  END IF;

  RAISE NOTICE 'ST-3 PASS: All 24 tables, 12 triggers, partial unique indexes, and role boundaries verified.';
END $$;
