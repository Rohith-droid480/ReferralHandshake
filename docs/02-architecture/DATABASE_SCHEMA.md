# ReferralHandshake (Protocol RHP-1) — Database Schema Specification

**Database Engine:** PostgreSQL 16 (Single Writable Primary)  
**Required Runtime Flags:** `synchronous_commit=on`, `log_lock_waits=on`  
**Default Isolation Level:** `READ COMMITTED` with explicit per-referral `SELECT ... FOR UPDATE` (Monitor and Witness use `REPEATABLE READ READ ONLY`)  
**Total Locked Tables:** 24 tables (`F4` closure)

---

## 1. PostgreSQL 16 Operational & Concurrency Rules

1. **Primary-Only Row Locking:** PostgreSQL row-level locks (`SELECT ... FOR UPDATE`) cannot be acquired on hot standbys (`[V]`). All contract writes, poller claims, and outbox relays execute exclusively against the single writable primary instance. Read-only projections may query a synchronous standby in production pilots, but the Independent Runtime Monitor (`rhp_monitor`) and Witness Signer (`rhp_witness`) read snapshots from the primary in `T0`–`T3` to guarantee zero replication-lag false positives.
2. **Global Lock Acquisition Order (`F1`, `I14`):**
   Every transaction that mutates contract state must acquire locks strictly in this order:
   $$\text{referral} \rightarrow \text{offer (ORDER BY id)} \rightarrow \text{deadline (ORDER BY id)} \rightarrow \text{outbox}$$
   Before mutating any row in `referral`, `offer`, `deadline` (when changing `status` or `due_at`), `event`, `payload_grant`, or inserting into `outbox`, the transaction must acquire `SELECT * FROM referral WHERE id = $1 FOR UPDATE` and set the transaction-scoped session GUC:
   ```sql
   SELECT set_config('rhp.locked_referral', $1::text, true);
   ```
   The PL/pgSQL trigger `rhp_require_lock()` verifies this GUC on every `INSERT` or `UPDATE` and aborts any out-of-order write with `RAISE EXCEPTION 'I14_LOCK_NOT_HELD'`.
3. **Delivery Bookkeeping Exemption (`I14`):**
   Updates to `deadline.claimed_until` (Poller Phase 1) and `outbox.status`, `outbox.attempts`, `outbox.visible_after` (Outbox Relay) do not alter contract state and are explicitly exempted inside `rhp_require_lock()` so stateless workers can claim rows via a single non-blocking `UPDATE ... FOR UPDATE SKIP LOCKED` statement without locking `referral`.

---

## 2. 24-Table Inventory & Invariant Mapping

| # | Table Name | Category | Primary Key | Enforced Invariants & Closures |
|---|---|---|---|---|
| 1 | `facility` | Directory | `id (uuid)` | Curated Karnataka facility registry (`PHC`, `CHC`, `FRU`, `DH`, `MC`, `DISPATCH`) |
| 2 | `roster` | Authority | `id (uuid)` | `I6` (rostered duty roles, validity windows, Argon2id `pin_hash`, E.164 phone) |
| 3 | `facility_capability` | Capability | `(facility_id, capability)` | Timestamped capability attestations with `expires_at` (`D15`, never "live beds") |
| 4 | `need_class_requirement` | Capability | `(need_class, capability)` | Maps clinical pathway `need_class` to required `cap_t` resources for `I15` |
| 5 | `catchment_chain` | Escalation | `(origin_facility_id, need_class, position)` | `I7` (district-approved ordered escalation targets, `origin <> target`) |
| 6 | `device` | Authority | `id (uuid)` | `I6`, `F7` (Ed25519 32-byte `pubkey` bound to a rostered slot) |
| 7 | `enrollment_ticket` | Authority | `id (uuid)` | `F7` (single-use 15-minute enrollment token hash issued by `ADMIN`) |
| 8 | `session` | Authority | `id (uuid)` | `F7`, `I6` (opaque session token hash or Exotel `call_sid`; per-session `pin_failed` lockout) |
| 9 | `referral` | Contract Core | `id (uuid)` | `I1`–`I3`, `I5`, `I12`, `I14`, `I16` (dual tracks `hs_state`/`tr_state`, `version`, `lease_epoch`, `open_offers <= 2`, `head_seq`, `head_hash`, `head_ts`) |
| 10 | `offer` | Contract Core | `id (uuid)` | `I2` (`one_lease` partial unique index), `I7` (`offer_chain_guard`), `I9` (`UNIQUE(referral_id, facility_id)`), `F13` |
| 11 | `offer_resource_confirmation` | Contract Core | `(offer_id, capability)` | `I15`, `F12` (per-capability confirmation with `expires_at > confirmed_at`) |
| 12 | `deadline` | Timers | `id (uuid)` | `I1` (`i1_pending_deadline` constraint trigger), `F1`, `F2` (durable timers + `claimed_until`) |
| 13 | `event` | Audit Log | `(referral_id, seq)` | `I4`, `I5`, `I11`, `I16` (append-only trigger `event_ao`, gap-free/monotone trigger `event_guard`, allowlist CHECK `rhp_detail_ok`) |
| 14 | `key_version` | Privacy / Crypto | `id (uuid)` | `D9` (per-referral AES-256-GCM DEK wrapped by `kek_epoch`; `SHREDDED` sets `wrapped_dek = NULL`) |
| 15 | `event_secret` | Privacy / Crypto | `(referral_id, seq)` | `D9` (envelope-encrypted event secret bound into `event.secret_hash`) |
| 16 | `clinical_payload` | Privacy / Crypto | `referral_id (uuid)` | `D9` (envelope-encrypted ISBAR + Dakshata handover payload with `expires_at`) |
| 17 | `payload_grant` | Privacy / Stream | `id (uuid)` | `I10`, `F10` (`one_active_grant` partial unique index; `revoked_at` triggers `GRANT_REVOKED`) |
| 18 | `telemetry` | Observations | `id (bigserial)` | `I4` (append-only GPS and vitals observations with `event_id UNIQUE` for set-union offline merge) |
| 19 | `idempotency` | Exactly-Once | `(actor_id, key)` | `I4`, `F14` (Step 1 command deduplication, `request_hash`, stored HTTP status & response) |
| 20 | `inbox` | Reach Dedupe | `id (bigserial)` | `I4` (`UNIQUE(source, external_id)` deduplicating Exotel/SMS webhook retries) |
| 21 | `outbox` | Async Delivery | `id (bigserial)` | `I4`, `F1` (same-transaction notification queue with `visible_after` retry backoff) |
| 22 | `rejected_command` | Fencing Audit | `id (bigserial)` | `I8` (append-only trigger `rejected_ao`; records every `401/403/409/412/422/429` domain rejection) |
| 23 | `checkpoint` | Integrity | `id (bigserial)` | `I5`, `F8` (append-only trigger `checkpoint_ao`; 5 s Ed25519 Merkle roots + cold-key `RESTORE` checkpoints) |
| 24 | `heartbeat` | Liveness | `(subject_kind, subject_id)` | `F11` (tracks `POLLER`, `RELAY`, `MONITOR`, `WITNESS`, `DEVICE` liveness and `ntp_offset_ms`) |

---

## 3. Complete PostgreSQL 16 DDL (`db/schema.sql`)

```sql
-- =============================================================================
-- ReferralHandshake (Protocol RHP-1) — Complete Locked PostgreSQL 16 Schema
-- Authority: ReferralHandshake_FINAL_LOCKED_Architecture.md §7 (24 Tables)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE DOMAIN need_class_t AS text
  CHECK (VALUE IN ('OBSTETRIC_EMERGENCY','NEONATAL','TRAUMA','CARDIAC','STROKE'));

CREATE DOMAIN cap_t AS text
  CHECK (VALUE IN ('OT','BLOOD','ANAESTHETIST','PAEDIATRICIAN','NICU'));

-- 1. facility
CREATE TABLE facility(
  id uuid PRIMARY KEY,
  code text UNIQUE NOT NULL,
  name text NOT NULL,
  tier text NOT NULL CHECK (tier IN ('PHC','CHC','FRU','DH','MC','DISPATCH')),
  lat_e5 int,
  lon_e5 int,
  active boolean NOT NULL DEFAULT true
);

-- 2. roster
CREATE TABLE roster(
  id uuid PRIMARY KEY,
  facility_id uuid NOT NULL REFERENCES facility,
  role_slot text NOT NULL CHECK (role_slot IN ('NURSE','CMO','CONSULTANT','CLINICIAN','EMT','DISPATCHER','ADMIN','JUDGE_DESK')),
  slot_no smallint NOT NULL DEFAULT 1,
  phone_e164 text,
  pin_hash text,
  valid_from timestamptz NOT NULL DEFAULT now(),
  valid_to timestamptz,
  UNIQUE (facility_id, role_slot, slot_no, valid_from)
);

-- 3. facility_capability
CREATE TABLE facility_capability(
  facility_id uuid NOT NULL REFERENCES facility,
  capability cap_t NOT NULL,
  attested_at timestamptz NOT NULL,
  attested_by uuid REFERENCES roster,
  expires_at timestamptz NOT NULL,
  PRIMARY KEY (facility_id, capability)
);

-- 4. need_class_requirement
CREATE TABLE need_class_requirement(
  need_class need_class_t NOT NULL,
  capability cap_t NOT NULL,
  PRIMARY KEY (need_class, capability)
);

-- 5. catchment_chain
CREATE TABLE catchment_chain(
  origin_facility_id uuid NOT NULL REFERENCES facility,
  need_class need_class_t NOT NULL,
  position smallint NOT NULL CHECK (position BETWEEN 1 AND 8),
  target_facility_id uuid NOT NULL REFERENCES facility,
  approved_by text NOT NULL,
  approved_at timestamptz NOT NULL,
  PRIMARY KEY (origin_facility_id, need_class, position),
  UNIQUE (origin_facility_id, need_class, target_facility_id),
  CHECK (origin_facility_id <> target_facility_id)
);

-- 6. device
CREATE TABLE device(
  id uuid PRIMARY KEY,
  roster_id uuid NOT NULL REFERENCES roster,
  pubkey bytea NOT NULL CHECK (octet_length(pubkey)=32),
  platform text NOT NULL,
  registered_at timestamptz NOT NULL,
  revoked_at timestamptz
);

-- 7. enrollment_ticket
CREATE TABLE enrollment_ticket(
  id uuid PRIMARY KEY,
  roster_id uuid NOT NULL REFERENCES roster,
  token_hash bytea UNIQUE NOT NULL,
  issued_by uuid NOT NULL REFERENCES roster,
  expires_at timestamptz NOT NULL,
  used_at timestamptz,
  device_id uuid REFERENCES device
);

-- 8. session
CREATE TABLE session(
  id uuid PRIMARY KEY,
  token_hash bytea UNIQUE NOT NULL,
  roster_id uuid NOT NULL REFERENCES roster,
  device_id uuid REFERENCES device,
  call_sid text UNIQUE,
  created_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  pin_failed smallint NOT NULL DEFAULT 0,
  pin_locked_until timestamptz,
  CHECK (device_id IS NOT NULL OR call_sid IS NOT NULL)
);

-- 9. referral
CREATE TABLE referral(
  id uuid PRIMARY KEY,
  version int NOT NULL DEFAULT 1,
  hs_state text NOT NULL CHECK (hs_state IN ('CREATED','OFFERED','ACKNOWLEDGED','ACCEPTED','COUNTERED','ESCALATED_TO_DISPATCHER','CANCELLED','CLOSED')),
  tr_state text NOT NULL DEFAULT 'REQUESTED' CHECK (tr_state IN ('REQUESTED','DISPATCHED','EN_ROUTE','ARRIVED','HANDED_OVER','TR_CANCELLED')),
  mode text NOT NULL CHECK (mode IN ('SEQUENTIAL','PARALLEL2')),
  need_class need_class_t NOT NULL,
  origin_facility_id uuid NOT NULL REFERENCES facility,
  chain uuid[] NOT NULL CHECK (cardinality(chain) BETWEEN 0 AND 8),
  ladder_cursor smallint NOT NULL DEFAULT 0,
  lease_offer_id uuid,
  lease_facility_id uuid REFERENCES facility,
  lease_epoch bigint NOT NULL DEFAULT 0,
  open_offers smallint NOT NULL DEFAULT 0 CHECK (open_offers BETWEEN 0 AND 2),
  tr_facility_id uuid REFERENCES facility,
  mgso4_status text NOT NULL DEFAULT 'UNKNOWN' CHECK (mgso4_status IN ('GIVEN','NONE_GIVEN','UNKNOWN')),
  profile_id text NOT NULL,
  profile_hash bytea NOT NULL,
  paper_code text UNIQUE NOT NULL,
  head_seq bigint NOT NULL DEFAULT 0,
  head_hash bytea NOT NULL DEFAULT decode(repeat('00',32),'hex'),
  head_ts timestamptz NOT NULL,
  outcome text CHECK (outcome IN ('ADMITTED_STABLE','ADMITTED_CRITICAL','DELIVERED_AT_RECEIVER','DELIVERED_EN_ROUTE','PATIENT_REFUSED','TRANSPORT_CANCELLED','DETERIORATED_OR_DIED_PRE_HANDOVER','REDIRECTED_ON_ARRIVAL','UNKNOWN_COUNTER_REFERRAL')),
  created_by uuid NOT NULL REFERENCES roster,
  created_at timestamptz NOT NULL,
  closed_at timestamptz,
  CHECK ((hs_state IN ('CLOSED','CANCELLED')) = (outcome IS NOT NULL AND closed_at IS NOT NULL)),
  CHECK ((lease_offer_id IS NULL) = (lease_facility_id IS NULL))
);

-- 10. offer
CREATE TABLE offer(
  id uuid PRIMARY KEY,
  referral_id uuid NOT NULL REFERENCES referral,
  facility_id uuid NOT NULL REFERENCES facility,
  step smallint NOT NULL,
  source text NOT NULL CHECK (source IN ('CHAIN','DISPATCHER')),
  status text NOT NULL CHECK (status IN ('OPEN','ACKED','COUNTERED','SOFT_OPEN','ACCEPTED','DECLINED','TIMED_OUT','SUPERSEDED','ARRIVAL_REJECTED','WITHDRAWN')),
  counter_round smallint NOT NULL DEFAULT 0 CHECK (counter_round BETWEEN 0 AND 2),
  counter_mask int NOT NULL DEFAULT 0,
  decline_reason text CHECK (decline_reason ~ '^[A-Z_]{1,40}$'),
  created_epoch bigint NOT NULL,
  created_at timestamptz NOT NULL,
  acked_at timestamptz,
  acked_by uuid REFERENCES roster,
  decided_at timestamptz,
  UNIQUE (referral_id, facility_id) -- I9: A facility is a target at most once per referral
);

-- I2: At most one active ownership lease per referral
CREATE UNIQUE INDEX one_lease ON offer (referral_id) WHERE status = 'ACCEPTED';

ALTER TABLE referral
  ADD CONSTRAINT referral_lease_fk
  FOREIGN KEY (lease_offer_id) REFERENCES offer(id)
  DEFERRABLE INITIALLY DEFERRED;

-- 11. offer_resource_confirmation
CREATE TABLE offer_resource_confirmation(
  offer_id uuid NOT NULL REFERENCES offer,
  capability cap_t NOT NULL,
  confirmed_by uuid NOT NULL REFERENCES roster,
  confirmed_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  PRIMARY KEY (offer_id, capability),
  CHECK (expires_at > confirmed_at)
);

-- 12. deadline
CREATE TABLE deadline(
  id uuid PRIMARY KEY,
  referral_id uuid NOT NULL REFERENCES referral,
  offer_id uuid REFERENCES offer,
  kind text NOT NULL CHECK (kind IN ('ACK','DECISION','COUNTER_CONFIRM','NOTICE_VOICE','NOTICE_PROXY','HANDOVER','DISPATCH_ACTION','CLOSURE')),
  step smallint,
  epoch bigint NOT NULL,
  due_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','DONE','CANCELLED')),
  claimed_until timestamptz,
  created_at timestamptz NOT NULL
);

CREATE INDEX deadline_due ON deadline (due_at) WHERE status = 'PENDING';
CREATE INDEX deadline_ref ON deadline (referral_id) WHERE status = 'PENDING';

-- I11: Event detail allowlist functions
CREATE FUNCTION rhp_allowed(t text) RETURNS text[] LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE
  WHEN t='REFERRAL_CREATED' THEN ARRAY['mode','need_class','chain_len','profile','mgso4']
  WHEN t IN ('OFFER_CREATED','ADVISORY_PREWARM') THEN ARRAY['step','facility','source','reason']
  WHEN t='NOTICE_SENT' THEN ARRAY['channel','rung','slot']
  WHEN t='OFFER_ACKED' THEN ARRAY['channel']
  WHEN t='RESOURCE_CONFIRMED' THEN ARRAY['capability']
  WHEN t IN ('OFFER_ACCEPTED','LEASE_GRANTED','LEASE_REVOKED') THEN ARRAY['facility','epoch','reason']
  WHEN t='OFFER_COUNTERED' THEN ARRAY['round','mask']
  WHEN t='COUNTER_RESOLVED' THEN ARRAY['confirmed']
  WHEN t='OFFER_DECLINED' THEN ARRAY['reason']
  WHEN t IN ('DEADLINE_TIMEOUT','CLOSURE_OVERDUE','HANDOVER_OVERDUE') THEN ARRAY['kind','step']
  WHEN t IN ('ARRIVAL_REJECTED','ESCALATED_TO_DISPATCHER','GRANT_REVOKED','PIN_LOCKED','ARRIVAL_AT_NON_OWNER') THEN ARRAY['reason','facility']
  WHEN t='DISPATCHER_ASSIGNED' THEN ARRAY['facility','reason']
  WHEN t IN ('TR_UPDATED','ARRIVAL_SUGGESTED') THEN ARRAY['tr_state','source','dwell_s']
  WHEN t='TR_DESTINATION_CHANGE' THEN ARRAY['facility','reason','accepted']
  WHEN t IN ('CANCELLED','CLOSED') THEN ARRAY['outcome','reason']
  WHEN t='RESTORE' THEN ARRAY['checkpoint_id']
  ELSE ARRAY[]::text[] END $$;

CREATE FUNCTION rhp_detail_ok(t text, d jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT jsonb_typeof(d)='object' AND NOT EXISTS (
   SELECT 1 FROM jsonb_each(d) e
   WHERE NOT (e.key = ANY (rhp_allowed(t)))
      OR NOT ( jsonb_typeof(e.value)='boolean'
            OR (jsonb_typeof(e.value)='number' AND e.value::text ~ '^-?[0-9]{1,12}$')
            OR (jsonb_typeof(e.value)='string' AND ((e.value #>> '{}') ~ '^[A-Z0-9_]{1,40}$'
                 OR (e.value #>> '{}') ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')))) $$;

-- 13. event
CREATE TABLE event(
  referral_id uuid NOT NULL REFERENCES referral,
  seq bigint NOT NULL CHECK (seq >= 1),
  event_id uuid NOT NULL UNIQUE,
  type text NOT NULL CHECK (type IN ('REFERRAL_CREATED','OFFER_CREATED','ADVISORY_PREWARM','NOTICE_SENT','OFFER_ACKED','RESOURCE_CONFIRMED','OFFER_ACCEPTED','LEASE_GRANTED','OFFER_COUNTERED','COUNTER_RESOLVED','OFFER_DECLINED','DEADLINE_TIMEOUT','OFFER_SOFT_EXPIRED','ARRIVAL_REJECTED','LEASE_REVOKED','ESCALATED_TO_DISPATCHER','DISPATCHER_ASSIGNED','TR_UPDATED','TR_DESTINATION_CHANGE','ARRIVAL_SUGGESTED','ARRIVAL_AT_NON_OWNER','CANCELLED','CLOSED','CLOSURE_OVERDUE','HANDOVER_OVERDUE','GRANT_REVOKED','PIN_LOCKED','RESTORE')),
  actor_roster_id uuid REFERENCES roster,
  actor_facility_id uuid REFERENCES facility,
  channel text NOT NULL CHECK (channel IN ('PWA','ANDROID','VOICE','SMS_LINK','PAPER','DISPATCHER_PROXY','SYSTEM')),
  proxy boolean NOT NULL DEFAULT false,
  proxy_for uuid REFERENCES roster,
  epoch bigint NOT NULL,
  detail jsonb NOT NULL DEFAULT '{}' CHECK (rhp_detail_ok(type, detail)),
  secret_hash bytea,
  client_ts_ms bigint,
  server_ts timestamptz NOT NULL,
  prev_hash bytea NOT NULL CHECK (octet_length(prev_hash)=32),
  hash bytea NOT NULL CHECK (octet_length(hash)=32),
  PRIMARY KEY (referral_id, seq)
);

-- 14. key_version
CREATE TABLE key_version(
  id uuid PRIMARY KEY,
  referral_id uuid NOT NULL REFERENCES referral,
  kek_epoch text NOT NULL,
  wrapped_dek bytea,
  status text NOT NULL CHECK (status IN ('ACTIVE','SHREDDED')),
  created_at timestamptz NOT NULL,
  shredded_at timestamptz,
  CHECK ((status='SHREDDED') = (wrapped_dek IS NULL))
);

-- 15. event_secret
CREATE TABLE event_secret(
  referral_id uuid NOT NULL,
  seq bigint NOT NULL,
  key_id uuid NOT NULL REFERENCES key_version,
  nonce bytea NOT NULL,
  ciphertext bytea NOT NULL,
  PRIMARY KEY (referral_id, seq),
  FOREIGN KEY (referral_id, seq) REFERENCES event
);

-- 16. clinical_payload
CREATE TABLE clinical_payload(
  referral_id uuid PRIMARY KEY REFERENCES referral,
  key_id uuid NOT NULL REFERENCES key_version,
  nonce bytea NOT NULL,
  ciphertext bytea NOT NULL,
  schema_ver smallint NOT NULL,
  expires_at timestamptz NOT NULL
);

-- 17. payload_grant
CREATE TABLE payload_grant(
  id uuid PRIMARY KEY,
  referral_id uuid NOT NULL REFERENCES referral,
  facility_id uuid NOT NULL REFERENCES facility,
  key_id uuid NOT NULL REFERENCES key_version,
  granted_at timestamptz NOT NULL,
  revoked_at timestamptz,
  revoke_reason text
);

CREATE UNIQUE INDEX one_active_grant ON payload_grant (referral_id, facility_id) WHERE revoked_at IS NULL;

-- 18. telemetry
CREATE TABLE telemetry(
  id bigserial PRIMARY KEY,
  referral_id uuid NOT NULL REFERENCES referral,
  device_id uuid NOT NULL REFERENCES device,
  event_id uuid UNIQUE NOT NULL,
  kind text NOT NULL CHECK (kind IN ('GPS','OBS')),
  lat_e5 int,
  lon_e5 int,
  acc_m int,
  obs_code text CHECK (obs_code ~ '^[A-Z_]{1,20}$'),
  obs_val int,
  client_ts_ms bigint NOT NULL,
  server_ts timestamptz NOT NULL
);

-- 19. idempotency
CREATE TABLE idempotency(
  actor_id uuid NOT NULL REFERENCES roster,
  key text NOT NULL CHECK (length(key) BETWEEN 8 AND 80),
  request_hash bytea NOT NULL,
  status text NOT NULL CHECK (status IN ('IN_FLIGHT','DONE')),
  http_status int,
  response jsonb,
  created_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  PRIMARY KEY (actor_id, key)
);

-- 20. inbox
CREATE TABLE inbox(
  id bigserial PRIMARY KEY,
  source text NOT NULL,
  external_id text NOT NULL,
  payload_sha256 bytea NOT NULL,
  received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  processed_at timestamptz,
  UNIQUE (source, external_id)
);

-- 21. outbox
CREATE TABLE outbox(
  id bigserial PRIMARY KEY,
  referral_id uuid NOT NULL,
  event_seq bigint NOT NULL,
  channel text NOT NULL CHECK (channel IN ('SSE','FCM','VOICE','SMS','PROXY_PAGE')),
  target_roster_id uuid REFERENCES roster,
  kind text NOT NULL,
  status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','SENT','DEAD')),
  attempts smallint NOT NULL DEFAULT 0,
  visible_after timestamptz NOT NULL,
  created_at timestamptz NOT NULL,
  FOREIGN KEY (referral_id, event_seq) REFERENCES event
);

CREATE INDEX outbox_ready ON outbox (visible_after) WHERE status = 'PENDING';

-- 22. rejected_command
CREATE TABLE rejected_command(
  id bigserial PRIMARY KEY,
  actor_id uuid REFERENCES roster,
  key text,
  referral_id uuid REFERENCES referral,
  command text NOT NULL,
  http_status int NOT NULL CHECK (http_status IN (401,403,409,412,422,429)),
  reason_code text NOT NULL,
  session_id uuid REFERENCES session,
  created_at timestamptz NOT NULL
);

-- 23. checkpoint
CREATE TABLE checkpoint(
  id bigserial PRIMARY KEY,
  taken_at timestamptz NOT NULL,
  kind text NOT NULL CHECK (kind IN ('REGULAR','RESTORE')),
  tree_size int NOT NULL,
  root_hash bytea NOT NULL,
  signature bytea NOT NULL,
  signer_key_id text NOT NULL,
  restore_from bigint REFERENCES checkpoint(id),
  cold_signature bytea,
  CHECK ((kind='RESTORE') = (cold_signature IS NOT NULL AND restore_from IS NOT NULL))
);

-- 24. heartbeat
CREATE TABLE heartbeat(
  subject_kind text NOT NULL CHECK (subject_kind IN ('POLLER','RELAY','MONITOR','WITNESS','DEVICE')),
  subject_id text NOT NULL,
  last_seen timestamptz NOT NULL,
  ntp_offset_ms int,
  PRIMARY KEY (subject_kind, subject_id)
);

-- =============================================================================
-- Triggers: Append-Only, Chain Continuity (I4/I5/I16), Lock Guard (I14),
--           Pending Deadline Liveness (I1), Catchment Chain Guard (I7)
-- =============================================================================

CREATE FUNCTION rhp_no_mutate() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'APPEND_ONLY %', TG_TABLE_NAME;
END $$;

CREATE TRIGGER event_ao BEFORE UPDATE OR DELETE ON event FOR EACH ROW EXECUTE FUNCTION rhp_no_mutate();
CREATE TRIGGER checkpoint_ao BEFORE UPDATE OR DELETE ON checkpoint FOR EACH ROW EXECUTE FUNCTION rhp_no_mutate();
CREATE TRIGGER rejected_ao BEFORE UPDATE OR DELETE ON rejected_command FOR EACH ROW EXECUTE FUNCTION rhp_no_mutate();

CREATE FUNCTION rhp_event_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r referral%ROWTYPE;
BEGIN
  SELECT * INTO r FROM referral WHERE id = NEW.referral_id;
  IF NEW.seq <> r.head_seq + 1 OR NEW.prev_hash <> r.head_hash OR NEW.server_ts < r.head_ts THEN
    RAISE EXCEPTION 'CHAIN_BREAK seq=%', NEW.seq;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER event_guard BEFORE INSERT ON event FOR EACH ROW EXECUTE FUNCTION rhp_event_guard();

CREATE FUNCTION rhp_require_lock() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rid text := to_jsonb(NEW) ->> (CASE WHEN TG_TABLE_NAME='referral' THEN 'id' ELSE 'referral_id' END);
BEGIN
  IF TG_OP='UPDATE' AND TG_TABLE_NAME='deadline' AND (NEW.status, NEW.due_at) IS NOT DISTINCT FROM (OLD.status, OLD.due_at) THEN
    RETURN NEW;
  END IF;
  IF TG_OP='UPDATE' AND TG_TABLE_NAME='outbox' THEN
    RETURN NEW;
  END IF;
  IF current_setting('rhp.locked_referral', true) IS DISTINCT FROM rid THEN
    RAISE EXCEPTION 'I14_LOCK_NOT_HELD';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER lk_referral BEFORE INSERT OR UPDATE ON referral FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE TRIGGER lk_offer    BEFORE INSERT OR UPDATE ON offer    FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE TRIGGER lk_deadline BEFORE INSERT OR UPDATE ON deadline FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE TRIGGER lk_event    BEFORE INSERT ON event              FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE TRIGGER lk_grant    BEFORE INSERT OR UPDATE ON payload_grant FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE TRIGGER lk_outbox   BEFORE INSERT OR UPDATE ON outbox   FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();

CREATE FUNCTION rhp_i1() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.hs_state NOT IN ('CLOSED','CANCELLED') AND
     NOT EXISTS (SELECT 1 FROM deadline WHERE referral_id=NEW.id AND status='PENDING') THEN
    RAISE EXCEPTION 'I1_NO_PENDING_DEADLINE';
  END IF;
  RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER i1_pending_deadline AFTER INSERT OR UPDATE ON referral
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rhp_i1();

CREATE FUNCTION rhp_chain_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.source='CHAIN' AND NOT (NEW.facility_id = ANY ((SELECT chain FROM referral WHERE id=NEW.referral_id))) THEN
    RAISE EXCEPTION 'I7_NOT_IN_CHAIN';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER offer_chain_guard BEFORE INSERT ON offer FOR EACH ROW EXECUTE FUNCTION rhp_chain_guard();

-- =============================================================================
-- Database Roles & Least-Privilege Grants
-- =============================================================================

CREATE ROLE rhp_app LOGIN;
CREATE ROLE rhp_monitor LOGIN;
CREATE ROLE rhp_witness LOGIN;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO rhp_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rhp_app, rhp_witness;
REVOKE UPDATE, DELETE ON event, checkpoint, rejected_command FROM rhp_app;
GRANT DELETE ON event_secret, clinical_payload, idempotency, telemetry TO rhp_app; -- purge and crypto-shred only

GRANT SELECT ON event, referral, offer, deadline, checkpoint, heartbeat, outbox, rejected_command TO rhp_monitor;
GRANT SELECT ON event, referral, checkpoint TO rhp_witness;
GRANT INSERT ON checkpoint TO rhp_witness;
GRANT INSERT, UPDATE ON heartbeat TO rhp_witness, rhp_monitor;
```

---

## 4. Production SQL Transaction Templates

### 4.1 Autonomous PIN Failure Counter (`F7`, Step 3 of `apply_command`)
Because a failed PIN check returns HTTP `403` and does not commit a contract state transition, the failure counter must execute on a separate autonomous connection so transaction rollback cannot erase failed brute-force attempts:

```sql
-- Executed on autonomous connection when argon2_verify() returns False:
UPDATE session
   SET pin_failed = pin_failed + 1,
       pin_locked_until = CASE
         WHEN pin_failed + 1 = 1 THEN clock_timestamp()
         WHEN pin_failed + 1 = 2 THEN clock_timestamp() + interval '5 seconds'
         WHEN pin_failed + 1 = 3 THEN clock_timestamp() + interval '30 seconds'
         ELSE clock_timestamp() + interval '120 seconds'
       END
 WHERE id = $1
RETURNING pin_failed, pin_locked_until;
```
When `pin_failed >= 3`, the handler also records a `PIN_LOCKED` event and outbox `PROXY_PAGE` alert for the dispatcher. Repeated lockouts across sessions on the same `roster_id` suspend the roster slot (`valid_to = clock_timestamp()`) pending `ADMIN` review.

### 4.2 Atomic `CREATE` Referral Transaction (Steps 4–9 of `apply_command`)

```sql
-- Inside apply_command(CREATE) transaction:
SELECT set_config('rhp.locked_referral', $1::text, true);

INSERT INTO referral(
  id, version, hs_state, tr_state, mode, need_class, origin_facility_id,
  chain, ladder_cursor, lease_offer_id, lease_facility_id, lease_epoch,
  open_offers, tr_facility_id, mgso4_status, profile_id, profile_hash,
  paper_code, head_seq, head_hash, head_ts, created_by, created_at
) VALUES (
  $1, 1,
  CASE WHEN cardinality($7::uuid[]) = 0 THEN 'ESCALATED_TO_DISPATCHER' ELSE 'OFFERED' END,
  'REQUESTED', $2, $3, $4,
  $7::uuid[],
  CASE WHEN cardinality($7::uuid[]) = 0 THEN 0
       WHEN $2 = 'PARALLEL2' AND cardinality($7::uuid[]) >= 2 THEN 2
       ELSE 1 END,
  NULL, NULL, 0,
  CASE WHEN cardinality($7::uuid[]) = 0 THEN 0
       WHEN $2 = 'PARALLEL2' AND cardinality($7::uuid[]) >= 2 THEN 2
       ELSE 1 END,
  $7[1], $5, $6, $8,
  $9, 0, decode(repeat('00',32),'hex'), $10, $11, $10
);

-- Insert key_version, clinical_payload, initial offer(s), deadlines (ACK, NOTICE_VOICE, NOTICE_PROXY),
-- payload_grant(s) for origin + offered facilities, then append REFERRAL_CREATED and OFFER_CREATED events,
-- update referral(head_seq, head_hash, head_ts), and insert outbox rows.
```

### 4.3 Crypto-Shredding & Retention Purge Job (`D9`, Section 10)

```sql
-- 1. Purge expired clinical payloads and event secrets, then shred per-referral DEKs:
WITH expired_refs AS (
  SELECT referral_id, key_id
    FROM clinical_payload
   WHERE expires_at <= clock_timestamp()
)
DELETE FROM event_secret
 WHERE referral_id IN (SELECT referral_id FROM expired_refs);

DELETE FROM clinical_payload
 WHERE expires_at <= clock_timestamp();

UPDATE key_version
   SET wrapped_dek = NULL,
       status = 'SHREDDED',
       shredded_at = clock_timestamp()
 WHERE status = 'ACTIVE'
   AND referral_id NOT IN (SELECT referral_id FROM clinical_payload);

-- 2. Purge expired idempotency keys (> 48 hours old):
DELETE FROM idempotency
 WHERE expires_at <= clock_timestamp()
   AND status = 'DONE';
```

### 4.4 Cold-Key Signed `RESTORE` Procedure (`F8`)
When restoring the primary database from a backup after catastrophic storage loss, the operator signs `{restore_from_checkpoint_id, restored_at_us, head_map_hash}` using the offline Ed25519 cold key and executes:

```sql
-- 1. Insert RESTORE checkpoint (as rhp_witness):
INSERT INTO checkpoint(
  taken_at, kind, tree_size, root_hash, signature,
  signer_key_id, restore_from, cold_signature
) VALUES (
  clock_timestamp(), 'RESTORE', $1, $2, $3,
  $4, $5, $6
) RETURNING id;

-- 2. For each active referral, under its referral lock (as rhp_app):
SELECT * FROM referral WHERE id = $1 FOR UPDATE;
SELECT set_config('rhp.locked_referral', $1::text, true);
-- Append event(type='RESTORE', detail=jsonb_build_object('checkpoint_id', $checkpoint_id), prev_hash=r.head_hash, seq=r.head_seq+1)
-- Update referral SET head_seq = head_seq + 1, head_hash = $new_hash, head_ts = GREATEST(clock_timestamp(), head_ts);
```

### 4.5 Scratch Database Creation for `BROKEN_BUILD` (`F20`, `scripts/make_scratch.sh`)
The scratch database `rhp_scratch_broken` loads `db/schema.sql` and intentionally drops the `one_lease` partial unique index so that when `BROKEN_BUILD=1` disables the Python lease check in `apply_command(ACCEPT)`, two concurrent hospital desks can both insert `status = 'ACCEPTED'` rows and trip the Independent Runtime Monitor (`I2` violation) within $\le 2\text{ s}$:

```sql
-- Executed ONLY against database rhp_scratch_broken:
DROP INDEX IF EXISTS one_lease;
ALTER TABLE referral DROP CONSTRAINT IF EXISTS referral_lease_fk;
```