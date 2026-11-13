---
name: database-management
description: Manage ReferralHandshake (RHP-1) PostgreSQL 16 schema, 24-table DDL, append-only hash-chain triggers, I14 session GUC lock guards, deferred I1 constraint triggers, role privilege separation, crypto-shredding lifecycle, and scratch DB isolation.
owner_lane: Lane A (Database & Schema Authority)
tier_scope: T0, T1, T2, T3
spec_anchors:
  - ReferralHandshake_FINAL_LOCKED_Architecture.md (§1, §3, §5, §7, §10, §11, §12, §23)
  - ReferralHandshake_v8_LOCKED_Solution.md (§5, §10)
invariants_enforced:
  - I1
  - I2
  - I4
  - I5
  - I7
  - I9
  - I10
  - I11
  - I12
  - I14
  - I15
  - I16
codeowners_restricted:
  - db/schema.sql
---

# RHP-1 Database Management Skill (`database-management`)

## 1. Mission & PostgreSQL 16 Operational Posture
You are responsible for the **PostgreSQL 16** persistence layer of **ReferralHandshake (Protocol RHP-1)**.
* **Topology:** Single writable PostgreSQL 16 primary (`synchronous_commit=on`, `log_lock_waits=on`, `READ COMMITTED` transaction isolation).
* **Primary-Only Locking:** Row-level locks (`SELECT ... FOR UPDATE` and `FOR UPDATE SKIP LOCKED`) only exist on the writable primary (`[V]`, R04). Read replicas (in pilot Multi-AZ deployments) may serve read-only analytics projections only and must **never** be used for command processing.
* **Schema Lock (`db/schema.sql`):** All 24 tables, 2 domains, partial unique indexes, functions, triggers, and role grants defined in Architecture §7 are frozen and protected by `CODEOWNERS`.

---

## 2. The 24 Locked Tables & Invariant Mapping (§7)

Every table in the database maps directly to a contract concept and enforces specific invariants at the storage engine layer:

| # | Table Name | Primary Key | Key Constraints, Indexes & Triggers | Invariants Enforced |
|---|---|---|---|---|
| 1 | `facility` | `id (uuid)` | `code UNIQUE`, `tier IN ('PHC','CHC','FRU','DH','MC','DISPATCH')` | I7 |
| 2 | `roster` | `id (uuid)` | `UNIQUE (facility_id, role_slot, slot_no, valid_from)`, `role_slot` enum | I6 |
| 3 | `facility_capability` | `(facility_id, capability)` | `capability cap_t`, `expires_at` | I15 |
| 4 | `need_class_requirement` | `(need_class, capability)` | Maps `need_class_t` to required `cap_t` resources | I15 |
| 5 | `catchment_chain` | `(origin_facility_id, need_class, position)` | `position BETWEEN 1 AND 8`, `UNIQUE (origin_facility_id, need_class, target_facility_id)`, `CHECK (origin <> target)` | I7, I9 |
| 6 | `device` | `id (uuid)` | `octet_length(pubkey) = 32` (Ed25519), `revoked_at` | I6 |
| 7 | `enrollment_ticket` | `id (uuid)` | `token_hash UNIQUE`, single-use (`used_at`, `device_id`) | I6 |
| 8 | `session` | `id (uuid)` | `token_hash UNIQUE`, `call_sid UNIQUE`, `pin_failed`, `pin_locked_until`, `CHECK (device_id IS NOT NULL OR call_sid IS NOT NULL)` | I6 (F7) |
| 9 | `referral` | `id (uuid)` | `open_offers BETWEEN 0 AND 2`, `mgso4_status IN ('GIVEN','NONE_GIVEN','UNKNOWN')`, terminal outcome CHECK, `referral_lease_fk` (DEFERRABLE), `lk_referral`, `i1_pending_deadline` | I1, I2, I3, I5, I12, I14, I16 |
| 10 | `offer` | `id (uuid)` | `UNIQUE (referral_id, facility_id)`, partial unique index `one_lease WHERE status = 'ACCEPTED'`, `counter_round BETWEEN 0 AND 2`, `lk_offer`, `offer_chain_guard` | I2, I7, I9, I12, I14 |
| 11 | `offer_resource_confirmation` | `(offer_id, capability)` | `CHECK (expires_at > confirmed_at)` | I15 (F12) |
| 12 | `deadline` | `id (uuid)` | Partial indexes `deadline_due` and `deadline_ref` `WHERE status = 'PENDING'`, `lk_deadline` | I1, I14 (F1, F2) |
| 13 | `event` | `(referral_id, seq)` | `event_id UNIQUE`, `CHECK (rhp_detail_ok(type, detail))`, `octet_length(prev_hash)=32`, `octet_length(hash)=32`, `event_ao`, `event_guard`, `lk_event` | I4, I5, I11, I14, I16 |
| 14 | `key_version` | `id (uuid)` | `status IN ('ACTIVE','SHREDDED')`, `CHECK ((status='SHREDDED') = (wrapped_dek IS NULL))` | Privacy (§10) |
| 15 | `event_secret` | `(referral_id, seq)` | FK to `event(referral_id, seq)` and `key_version(id)` | Privacy (§10) |
| 16 | `clinical_payload` | `referral_id (uuid)` | Envelope-encrypted ISBAR+Dakshata ciphertext, `expires_at` | Privacy (§10) |
| 17 | `payload_grant` | `id (uuid)` | Partial unique index `one_active_grant ON (referral_id, facility_id) WHERE revoked_at IS NULL`, `lk_grant` | I10, I14 (F10) |
| 18 | `telemetry` | `id (bigserial)` | `event_id UNIQUE`, `kind IN ('GPS','OBS')`, append-only set-union merge | Offline merge (§5) |
| 19 | `idempotency` | `(actor_id, key)` | `length(key) BETWEEN 8 AND 80`, `status IN ('IN_FLIGHT','DONE')` | I4 (F14) |
| 20 | `inbox` | `id (bigserial)` | `UNIQUE (source, external_id)` for webhook deduplication | I4 (N5) |
| 21 | `outbox` | `id (bigserial)` | FK to `event(referral_id, event_seq)`, partial index `outbox_ready WHERE status = 'PENDING'`, `lk_outbox` | I4, I14 |
| 22 | `rejected_command` | `id (bigserial)` | `http_status IN (401,403,409,412,422,429)`, trigger `rejected_ao` | I8 |
| 23 | `checkpoint` | `id (bigserial)` | `kind IN ('REGULAR','RESTORE')`, `CHECK ((kind='RESTORE') = (cold_signature IS NOT NULL AND restore_from IS NOT NULL))`, trigger `checkpoint_ao` | I5 (F8) |
| 24 | `heartbeat` | `(subject_kind, subject_id)` | `subject_kind IN ('POLLER','RELAY','MONITOR','WITNESS','DEVICE')`, `ntp_offset_ms` | Liveness (§6, §14) |

---

## 3. Database Triggers & Stored Functions (§7)

You must ensure all 5 trigger families and 2 JSONB validation functions from Architecture §7 are loaded and never bypassed:

### 3.1 Session GUC Lock Guard (`rhp_require_lock` — I14 / F1)
```sql
CREATE FUNCTION rhp_require_lock() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rid text := to_jsonb(NEW) ->> (CASE WHEN TG_TABLE_NAME='referral' THEN 'id' ELSE 'referral_id' END);
BEGIN
  IF TG_OP='UPDATE' AND TG_TABLE_NAME='deadline' AND (NEW.status, NEW.due_at) IS NOT DISTINCT FROM (OLD.status, OLD.due_at) THEN RETURN NEW; END IF;
  IF TG_OP='UPDATE' AND TG_TABLE_NAME='outbox' THEN RETURN NEW; END IF;
  IF current_setting('rhp.locked_referral', true) IS DISTINCT FROM rid THEN RAISE EXCEPTION 'I14_LOCK_NOT_HELD'; END IF;
  RETURN NEW; END $$;
```
* **Why `deadline` and `outbox` have specific `UPDATE` exemptions:** Poller Phase 1 updates only `deadline.claimed_until` (`status` and `due_at` unchanged), and the Outbox Relay updates `outbox.status`, `attempts`, and `visible_after`. Neither alters contract state, so they run via single-statement `FOR UPDATE SKIP LOCKED` without locking `referral`. Any change to `deadline.status`, `deadline.due_at`, or `INSERT INTO outbox` enforces `rhp.locked_referral == referral_id`.

### 3.2 Append-Only & Hash-Chain Guard (`rhp_no_mutate`, `rhp_event_guard` — I4, I5, I16)
* `event_ao`, `checkpoint_ao`, and `rejected_ao` reject all `UPDATE` and `DELETE` operations unconditionally.
* `event_guard` verifies on every `INSERT INTO event` that:
  1. `NEW.seq = r.head_seq + 1` (gap-free per-referral sequence, I4),
  2. `NEW.prev_hash = r.head_hash` (cryptographic hash link, I5), and
  3. `NEW.server_ts >= r.head_ts` (monotone per-referral server timestamp, I16).

### 3.3 Deferred Liveness Constraint Trigger (`rhp_i1` — I1)
* `i1_pending_deadline` runs `AFTER INSERT OR UPDATE ON referral DEFERRABLE INITIALLY DEFERRED`. At `COMMIT`, if `NEW.hs_state NOT IN ('CLOSED', 'CANCELLED')` and no row exists in `deadline` with `referral_id = NEW.id AND status = 'PENDING'`, the transaction aborts with `I1_NO_PENDING_DEADLINE`.

### 3.4 Approved Catchment Chain Guard (`rhp_chain_guard` — I7)
* `offer_chain_guard` runs `BEFORE INSERT ON offer`. Whenever `NEW.source = 'CHAIN'`, it verifies `NEW.facility_id = ANY (referral.chain)`, raising `I7_NOT_IN_CHAIN` if the target was not in the snapshot chain.

### 3.5 PHI-Free `event.detail` Allowlist (`rhp_allowed`, `rhp_detail_ok` — I11 / F9)
* Every key in `event.detail` must belong to the array returned by `rhp_allowed(type)`, and every value must be a JSON boolean, a 1-to-12 digit integer (`^-?[0-9]{1,12}$`), an uppercase enum token (`^[A-Z0-9_]{1,40}$`), or a lowercase UUID. Free text and floating-point numbers are rejected at the database level.

---

## 4. Role Separation & Least-Privilege Matrix (§7)

Always create and enforce the three distinct database login roles:

| Role | Purpose | Allowed Operations | Explicitly Forbidden |
|---|---|---|---|
| `rhp_app` | FastAPI, Poller, Outbox Relay | `SELECT, INSERT, UPDATE` on public tables; `DELETE` **only** on `event_secret`, `clinical_payload`, `idempotency`, `telemetry` (for crypto-shredding and TTL purge) | `UPDATE` or `DELETE` on `event`, `checkpoint`, `rejected_command`; DDL modifications; superuser bypass |
| `rhp_monitor` | Independent Python Monitor (Person B) | `SELECT` on `event`, `referral`, `offer`, `deadline`, `checkpoint`, `heartbeat`, `outbox`, `rejected_command`; `INSERT, UPDATE` on `heartbeat` | Any access to `clinical_payload` or `event_secret`; any write to contract tables |
| `rhp_witness` | Separate-OS-User (`rhp-sign`) Witness | `SELECT` on `event`, `referral`, `checkpoint`; `INSERT` on `checkpoint`; `INSERT, UPDATE` on `heartbeat` | Any access to clinical tables or mutation of `referral`/`event` |

---

## 5. Crypto-Shredding, Backup Restore & Scratch DB Protocols

### 5.1 Envelope Encryption & Crypto-Shredding Walk-Through (D9 / §10)
When a referral reaches `clinical_payload.expires_at` (or post-closure retention expiry):
```sql
BEGIN;
DELETE FROM clinical_payload WHERE referral_id = $1;
DELETE FROM event_secret WHERE referral_id = $1;
UPDATE key_version
   SET wrapped_dek = NULL,
       status = 'SHREDDED',
       shredded_at = clock_timestamp()
 WHERE referral_id = $1 AND status = 'ACTIVE';
COMMIT;
```
* Because `event.secret_hash` stores `SHA-256(ciphertext)` inside the `event` row, deleting `event_secret` and `wrapped_dek` renders the PHI permanently unrecoverable while `event.hash` and the per-referral hash chain continue to verify 100%.
* Once all referrals in a monthly `kek_epoch` are shredded, destroy the KEK epoch key so historical WAL archives and logical backups become cryptographically unrecoverable.

### 5.2 Cold-Key Signed `RESTORE` Protocol (F8 / §7 / §11)
If the database is restored from a backup (causing `referral.head_seq` to regress below a previously witnessed `checkpoint`):
1. An operator holding the offline cold Ed25519 key signs `{restore_from_checkpoint_id, restored_at, head_map_hash}`.
2. Insert a `checkpoint` row with `kind = 'RESTORE'`, `restore_from = <old_checkpoint_id>`, and `cold_signature = <sig>`.
3. For each affected referral, append a `RESTORE` event linking `prev_hash = restored_head_hash` and continuing `seq`. Any head regression lacking a cold-key signed `RESTORE` checkpoint is flagged by the verifier as `TAMPER`.

### 5.3 Safe `BROKEN_BUILD` Scratch DB Isolation (F20 / §12)
* `scripts/make_scratch.sh` creates a separate database named `rhp_scratch_broken` using the §7 DDL **with `CREATE UNIQUE INDEX one_lease` omitted**.
* `rhp_scratch_broken` uses a dedicated database role that cannot authenticate to the primary `rhp` database (`pg_hba.conf` + role separation).
* If `BROKEN_BUILD=1` is set when `REAL_DATA=1` or when the target database name is not `rhp_scratch_broken`, the process must abort immediately with exit code `78`.

---

## 6. Verification Gates (Must Pass on Every Schema/DB Task)

1. **Gate DB-1 (`T-F4 ddl_load_fk_scan` / `ST-3`):** Load `db/schema.sql` into a clean PostgreSQL 16 container. Query `information_schema.tables` to confirm all 24 tables exist, `pg_indexes` to confirm `one_lease` and `one_active_grant` exist, and `pg_trigger` to confirm all 11 triggers are enabled.
2. **Gate DB-2 (`T-I14` Lock Trigger Test):** Attempt direct `INSERT` or `UPDATE` on `referral`, `offer`, `deadline` (changing `status`), `event`, `payload_grant`, and `outbox` without setting `rhp.locked_referral`. Verify every attempt fails with `I14_LOCK_NOT_HELD`.
3. **Gate DB-3 (`T-I1` Deferred Trigger Test):** Inside a transaction, insert a `referral` in state `OFFERED` without inserting a `PENDING` `deadline`. Attempt `COMMIT` and verify PostgreSQL aborts the commit with `I1_NO_PENDING_DEADLINE`.
4. **Gate DB-4 (`T-F8` Append-Only & Chain Guard Test):** Attempt `UPDATE` and `DELETE` on `event`, `checkpoint`, and `rejected_command` as `rhp_app`; verify permission denied and `APPEND_ONLY` trigger failure. Attempt out-of-order `seq` or mismatched `prev_hash` insert on `event`; verify `CHAIN_BREAK` exception.

---

## 7. Explicit DO / DO NOT Guardrails

### DO
* **DO** start PostgreSQL 16 with `-c synchronous_commit=on -c log_lock_waits=on`.
* **DO** break the creation cycle between `referral` and `offer` using `ALTER TABLE referral ADD CONSTRAINT referral_lease_fk FOREIGN KEY (lease_offer_id) REFERENCES offer(id) DEFERRABLE INITIALLY DEFERRED;`.
* **DO** store coordinates as integer micro/centi-degrees (`lat_e5 int`, `lon_e5 int`) and timestamps as `timestamptz` (`server_ts`) or `bigint` (`client_ts_ms`)—never floats.

### DO NOT
* **DO NOT** modify `db/schema.sql` to weaken any `CHECK` constraint, drop a trigger, or add unapproved columns.
* **DO NOT** run the FastAPI application using the `postgres` superuser role; always connect as `rhp_app`.
* **DO NOT** grant `rhp_monitor` or `rhp_witness` read access to `clinical_payload`, `event_secret`, or `key_version`.