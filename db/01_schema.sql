CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE DOMAIN need_class_t AS text CHECK (VALUE IN ('OBSTETRIC_EMERGENCY','NEONATAL','TRAUMA','CARDIAC','STROKE'));
CREATE DOMAIN cap_t AS text CHECK (VALUE IN ('OT','BLOOD','ANAESTHETIST','PAEDIATRICIAN','NICU'));

CREATE TABLE facility(
  id uuid PRIMARY KEY, code text UNIQUE NOT NULL, name text NOT NULL,
  tier text NOT NULL CHECK (tier IN ('PHC','CHC','FRU','DH','MC','DISPATCH')),
  lat_e5 int, lon_e5 int, active boolean NOT NULL DEFAULT true);
CREATE TABLE roster(
  id uuid PRIMARY KEY, facility_id uuid NOT NULL REFERENCES facility,
  role_slot text NOT NULL CHECK (role_slot IN ('NURSE','CMO','CONSULTANT','CLINICIAN','EMT','DISPATCHER','ADMIN','JUDGE_DESK')),
  slot_no smallint NOT NULL DEFAULT 1, phone_e164 text, pin_hash text,
  valid_from timestamptz NOT NULL DEFAULT now(), valid_to timestamptz,
  UNIQUE (facility_id, role_slot, slot_no, valid_from));
CREATE TABLE facility_capability(
  facility_id uuid NOT NULL REFERENCES facility, capability cap_t NOT NULL,
  attested_at timestamptz NOT NULL, attested_by uuid REFERENCES roster, expires_at timestamptz NOT NULL,
  PRIMARY KEY (facility_id, capability));
CREATE TABLE need_class_requirement(
  need_class need_class_t NOT NULL, capability cap_t NOT NULL, PRIMARY KEY (need_class, capability));
CREATE TABLE catchment_chain(
  origin_facility_id uuid NOT NULL REFERENCES facility, need_class need_class_t NOT NULL,
  position smallint NOT NULL CHECK (position BETWEEN 1 AND 8),
  target_facility_id uuid NOT NULL REFERENCES facility,
  approved_by text NOT NULL, approved_at timestamptz NOT NULL,
  PRIMARY KEY (origin_facility_id, need_class, position),
  UNIQUE (origin_facility_id, need_class, target_facility_id),
  CHECK (origin_facility_id <> target_facility_id));
CREATE TABLE device(
  id uuid PRIMARY KEY, roster_id uuid NOT NULL REFERENCES roster,
  pubkey bytea NOT NULL CHECK (octet_length(pubkey)=32), platform text NOT NULL,
  registered_at timestamptz NOT NULL, revoked_at timestamptz);
CREATE TABLE enrollment_ticket(
  id uuid PRIMARY KEY, roster_id uuid NOT NULL REFERENCES roster, token_hash bytea UNIQUE NOT NULL,
  issued_by uuid NOT NULL REFERENCES roster, expires_at timestamptz NOT NULL,
  used_at timestamptz, device_id uuid REFERENCES device);
CREATE TABLE session(
  id uuid PRIMARY KEY, token_hash bytea UNIQUE NOT NULL, roster_id uuid NOT NULL REFERENCES roster,
  device_id uuid REFERENCES device, call_sid text UNIQUE,
  created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL, revoked_at timestamptz,
  pin_failed smallint NOT NULL DEFAULT 0, pin_locked_until timestamptz,
  CHECK (device_id IS NOT NULL OR call_sid IS NOT NULL));

CREATE TABLE referral(
  id uuid PRIMARY KEY, version int NOT NULL DEFAULT 1,
  hs_state text NOT NULL CHECK (hs_state IN ('CREATED','OFFERED','ACKNOWLEDGED','ACCEPTED','COUNTERED','ESCALATED_TO_DISPATCHER','CANCELLED','CLOSED')),
  tr_state text NOT NULL DEFAULT 'REQUESTED' CHECK (tr_state IN ('REQUESTED','DISPATCHED','EN_ROUTE','ARRIVED','HANDED_OVER','TR_CANCELLED')),
  mode text NOT NULL CHECK (mode IN ('SEQUENTIAL','PARALLEL2')),
  need_class need_class_t NOT NULL, origin_facility_id uuid NOT NULL REFERENCES facility,
  chain uuid[] NOT NULL CHECK (cardinality(chain) BETWEEN 0 AND 8),
  ladder_cursor smallint NOT NULL DEFAULT 0,
  lease_offer_id uuid, lease_facility_id uuid REFERENCES facility, lease_epoch bigint NOT NULL DEFAULT 0,
  open_offers smallint NOT NULL DEFAULT 0 CHECK (open_offers BETWEEN 0 AND 2),
  tr_facility_id uuid REFERENCES facility,
  mgso4_status text NOT NULL DEFAULT 'UNKNOWN' CHECK (mgso4_status IN ('GIVEN','NONE_GIVEN','UNKNOWN')),
  profile_id text NOT NULL, profile_hash bytea NOT NULL, paper_code text UNIQUE NOT NULL,
  head_seq bigint NOT NULL DEFAULT 0, head_hash bytea NOT NULL DEFAULT decode(repeat('00',32),'hex'),
  head_ts timestamptz NOT NULL,
  outcome text CHECK (outcome IN ('ADMITTED_STABLE','ADMITTED_CRITICAL','DELIVERED_AT_RECEIVER','DELIVERED_EN_ROUTE','PATIENT_REFUSED','TRANSPORT_CANCELLED','DETERIORATED_OR_DIED_PRE_HANDOVER','REDIRECTED_ON_ARRIVAL','UNKNOWN_COUNTER_REFERRAL')),
  created_by uuid NOT NULL REFERENCES roster, created_at timestamptz NOT NULL, closed_at timestamptz,
  CHECK ((hs_state IN ('CLOSED','CANCELLED')) = (outcome IS NOT NULL AND closed_at IS NOT NULL)),
  CHECK ((lease_offer_id IS NULL) = (lease_facility_id IS NULL)));
CREATE TABLE offer(
  id uuid PRIMARY KEY, referral_id uuid NOT NULL REFERENCES referral,
  facility_id uuid NOT NULL REFERENCES facility, step smallint NOT NULL,
  source text NOT NULL CHECK (source IN ('CHAIN','DISPATCHER')),
  status text NOT NULL CHECK (status IN ('OPEN','ACKED','COUNTERED','SOFT_OPEN','ACCEPTED','DECLINED','TIMED_OUT','SUPERSEDED','ARRIVAL_REJECTED','WITHDRAWN')),
  counter_round smallint NOT NULL DEFAULT 0 CHECK (counter_round BETWEEN 0 AND 2),
  counter_mask int NOT NULL DEFAULT 0, decline_reason text CHECK (decline_reason ~ '^[A-Z_]{1,40}$'),
  created_epoch bigint NOT NULL, created_at timestamptz NOT NULL,
  acked_at timestamptz, acked_by uuid REFERENCES roster, decided_at timestamptz,
  UNIQUE (referral_id, facility_id));                                  -- I9
CREATE UNIQUE INDEX one_lease ON offer (referral_id) WHERE status = 'ACCEPTED';   -- I2
ALTER TABLE referral ADD CONSTRAINT referral_lease_fk FOREIGN KEY (lease_offer_id) REFERENCES offer(id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE offer_resource_confirmation(
  offer_id uuid NOT NULL REFERENCES offer, capability cap_t NOT NULL,
  confirmed_by uuid NOT NULL REFERENCES roster, confirmed_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
  PRIMARY KEY (offer_id, capability), CHECK (expires_at > confirmed_at));
CREATE TABLE deadline(
  id uuid PRIMARY KEY, referral_id uuid NOT NULL REFERENCES referral, offer_id uuid REFERENCES offer,
  kind text NOT NULL CHECK (kind IN ('ACK','DECISION','COUNTER_CONFIRM','NOTICE_VOICE','NOTICE_PROXY','HANDOVER','DISPATCH_ACTION','CLOSURE')),
  step smallint, epoch bigint NOT NULL, due_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','DONE','CANCELLED')),
  claimed_until timestamptz, created_at timestamptz NOT NULL);
CREATE INDEX deadline_due ON deadline (due_at) WHERE status = 'PENDING';
CREATE INDEX deadline_ref ON deadline (referral_id) WHERE status = 'PENDING';

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
  WHEN t='OFFER_DECLINED' THEN ARRAY['reason','facility']
  WHEN t='OFFER_SOFT_EXPIRED' THEN ARRAY['step','facility']
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

CREATE TABLE event(
  referral_id uuid NOT NULL REFERENCES referral, seq bigint NOT NULL CHECK (seq >= 1),
  event_id uuid NOT NULL UNIQUE,
  type text NOT NULL CHECK (type IN ('REFERRAL_CREATED','OFFER_CREATED','ADVISORY_PREWARM','NOTICE_SENT','OFFER_ACKED','RESOURCE_CONFIRMED','OFFER_ACCEPTED','LEASE_GRANTED','OFFER_COUNTERED','COUNTER_RESOLVED','OFFER_DECLINED','DEADLINE_TIMEOUT','OFFER_SOFT_EXPIRED','ARRIVAL_REJECTED','LEASE_REVOKED','ESCALATED_TO_DISPATCHER','DISPATCHER_ASSIGNED','TR_UPDATED','TR_DESTINATION_CHANGE','ARRIVAL_SUGGESTED','ARRIVAL_AT_NON_OWNER','CANCELLED','CLOSED','CLOSURE_OVERDUE','HANDOVER_OVERDUE','GRANT_REVOKED','PIN_LOCKED','RESTORE')),
  actor_roster_id uuid REFERENCES roster, actor_facility_id uuid REFERENCES facility,
  channel text NOT NULL CHECK (channel IN ('PWA','ANDROID','VOICE','SMS_LINK','PAPER','DISPATCHER_PROXY','SYSTEM')),
  proxy boolean NOT NULL DEFAULT false, proxy_for uuid REFERENCES roster,
  epoch bigint NOT NULL, detail jsonb NOT NULL DEFAULT '{}' CHECK (rhp_detail_ok(type, detail)),
  secret_hash bytea, client_ts_ms bigint, server_ts timestamptz NOT NULL,
  prev_hash bytea NOT NULL CHECK (octet_length(prev_hash)=32), hash bytea NOT NULL CHECK (octet_length(hash)=32),
  PRIMARY KEY (referral_id, seq));
CREATE TABLE key_version(
  id uuid PRIMARY KEY, referral_id uuid NOT NULL REFERENCES referral, kek_epoch text NOT NULL,
  wrapped_dek bytea, status text NOT NULL CHECK (status IN ('ACTIVE','SHREDDED')),
  created_at timestamptz NOT NULL, shredded_at timestamptz,
  CHECK ((status='SHREDDED') = (wrapped_dek IS NULL)));
CREATE TABLE event_secret(
  referral_id uuid NOT NULL, seq bigint NOT NULL, key_id uuid NOT NULL REFERENCES key_version,
  nonce bytea NOT NULL, ciphertext bytea NOT NULL, PRIMARY KEY (referral_id, seq),
  FOREIGN KEY (referral_id, seq) REFERENCES event);
CREATE TABLE clinical_payload(
  referral_id uuid PRIMARY KEY REFERENCES referral, key_id uuid NOT NULL REFERENCES key_version,
  nonce bytea NOT NULL, ciphertext bytea NOT NULL, schema_ver smallint NOT NULL, expires_at timestamptz NOT NULL);
CREATE TABLE payload_grant(
  id uuid PRIMARY KEY, referral_id uuid NOT NULL REFERENCES referral, facility_id uuid NOT NULL REFERENCES facility,
  key_id uuid NOT NULL REFERENCES key_version, granted_at timestamptz NOT NULL,
  revoked_at timestamptz, revoke_reason text);
CREATE UNIQUE INDEX one_active_grant ON payload_grant (referral_id, facility_id) WHERE revoked_at IS NULL;
CREATE TABLE telemetry(
  id bigserial PRIMARY KEY, referral_id uuid NOT NULL REFERENCES referral, device_id uuid NOT NULL REFERENCES device,
  event_id uuid UNIQUE NOT NULL, kind text NOT NULL CHECK (kind IN ('GPS','OBS')),
  lat_e5 int, lon_e5 int, acc_m int, obs_code text CHECK (obs_code ~ '^[A-Z_]{1,20}$'), obs_val int,
  client_ts_ms bigint NOT NULL, server_ts timestamptz NOT NULL);
CREATE TABLE idempotency(
  actor_id uuid NOT NULL REFERENCES roster, key text NOT NULL CHECK (length(key) BETWEEN 8 AND 80),
  request_hash bytea NOT NULL, status text NOT NULL CHECK (status IN ('IN_FLIGHT','DONE')),
  http_status int, response jsonb, created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
  PRIMARY KEY (actor_id, key));
CREATE TABLE inbox(
  id bigserial PRIMARY KEY, source text NOT NULL, external_id text NOT NULL, payload_sha256 bytea NOT NULL,
  received_at timestamptz NOT NULL DEFAULT clock_timestamp(), processed_at timestamptz, UNIQUE (source, external_id));
CREATE TABLE outbox(
  id bigserial PRIMARY KEY, referral_id uuid NOT NULL, event_seq bigint NOT NULL,
  channel text NOT NULL CHECK (channel IN ('SSE','FCM','VOICE','SMS','PROXY_PAGE')),
  target_roster_id uuid REFERENCES roster, kind text NOT NULL,
  status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','SENT','DEAD')),
  attempts smallint NOT NULL DEFAULT 0, visible_after timestamptz NOT NULL, created_at timestamptz NOT NULL,
  FOREIGN KEY (referral_id, event_seq) REFERENCES event);
CREATE INDEX outbox_ready ON outbox (visible_after) WHERE status = 'PENDING';
CREATE TABLE rejected_command(
  id bigserial PRIMARY KEY, actor_id uuid REFERENCES roster, key text, referral_id uuid REFERENCES referral,
  command text NOT NULL, http_status int NOT NULL CHECK (http_status IN (401,403,409,412,422,429)),
  reason_code text NOT NULL, session_id uuid REFERENCES session, created_at timestamptz NOT NULL);
CREATE TABLE checkpoint(
  id bigserial PRIMARY KEY, taken_at timestamptz NOT NULL,
  kind text NOT NULL CHECK (kind IN ('REGULAR','RESTORE')), tree_size int NOT NULL,
  root_hash bytea NOT NULL, signature bytea NOT NULL, signer_key_id text NOT NULL,
  restore_from bigint REFERENCES checkpoint(id), cold_signature bytea,
  CHECK ((kind='RESTORE') = (cold_signature IS NOT NULL AND restore_from IS NOT NULL)));
CREATE TABLE heartbeat(
  subject_kind text NOT NULL CHECK (subject_kind IN ('POLLER','RELAY','MONITOR','WITNESS','DEVICE')),
  subject_id text NOT NULL, last_seen timestamptz NOT NULL, ntp_offset_ms int,
  PRIMARY KEY (subject_kind, subject_id));

-- append-only, chain guard, lock guard (I14), I1 at commit, chain-target guard (I7)
CREATE FUNCTION rhp_no_mutate() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'APPEND_ONLY %', TG_TABLE_NAME; END $$;
CREATE TRIGGER event_ao BEFORE UPDATE OR DELETE ON event FOR EACH ROW EXECUTE FUNCTION rhp_no_mutate();
CREATE TRIGGER checkpoint_ao BEFORE UPDATE OR DELETE ON checkpoint FOR EACH ROW EXECUTE FUNCTION rhp_no_mutate();
CREATE TRIGGER rejected_ao BEFORE UPDATE OR DELETE ON rejected_command FOR EACH ROW EXECUTE FUNCTION rhp_no_mutate();
CREATE FUNCTION rhp_event_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r referral%ROWTYPE;
BEGIN SELECT * INTO r FROM referral WHERE id = NEW.referral_id;
  IF NEW.seq <> r.head_seq + 1 OR NEW.prev_hash <> r.head_hash OR NEW.server_ts < r.head_ts THEN
    RAISE EXCEPTION 'CHAIN_BREAK seq=%', NEW.seq; END IF;
  RETURN NEW; END $$;
CREATE TRIGGER event_guard BEFORE INSERT ON event FOR EACH ROW EXECUTE FUNCTION rhp_event_guard();
CREATE FUNCTION rhp_require_lock() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rid text := to_jsonb(NEW) ->> (CASE WHEN TG_TABLE_NAME='referral' THEN 'id' ELSE 'referral_id' END);
BEGIN
  IF TG_OP='UPDATE' AND TG_TABLE_NAME='deadline' AND (NEW.status, NEW.due_at) IS NOT DISTINCT FROM (OLD.status, OLD.due_at) THEN RETURN NEW; END IF;
  IF TG_OP='UPDATE' AND TG_TABLE_NAME='outbox' THEN RETURN NEW; END IF;
  IF current_setting('rhp.locked_referral', true) IS DISTINCT FROM rid THEN RAISE EXCEPTION 'I14_LOCK_NOT_HELD'; END IF;
  RETURN NEW; END $$;
CREATE TRIGGER lk_referral BEFORE INSERT OR UPDATE ON referral FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE TRIGGER lk_offer    BEFORE INSERT OR UPDATE ON offer    FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE TRIGGER lk_deadline BEFORE INSERT OR UPDATE ON deadline FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE TRIGGER lk_event    BEFORE INSERT ON event              FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE TRIGGER lk_grant    BEFORE INSERT OR UPDATE ON payload_grant FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE TRIGGER lk_outbox   BEFORE INSERT OR UPDATE ON outbox   FOR EACH ROW EXECUTE FUNCTION rhp_require_lock();
CREATE FUNCTION rhp_i1() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NEW.hs_state NOT IN ('CLOSED','CANCELLED') AND
        NOT EXISTS (SELECT 1 FROM deadline WHERE referral_id=NEW.id AND status='PENDING') THEN
     RAISE EXCEPTION 'I1_NO_PENDING_DEADLINE'; END IF; RETURN NULL; END $$;
CREATE CONSTRAINT TRIGGER i1_pending_deadline AFTER INSERT OR UPDATE ON referral
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rhp_i1();
CREATE FUNCTION rhp_chain_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NEW.source='CHAIN' AND NOT (NEW.facility_id = ANY ((SELECT chain FROM referral WHERE id=NEW.referral_id))) THEN
        RAISE EXCEPTION 'I7_NOT_IN_CHAIN'; END IF; RETURN NEW; END $$;
CREATE TRIGGER offer_chain_guard BEFORE INSERT ON offer FOR EACH ROW EXECUTE FUNCTION rhp_chain_guard();