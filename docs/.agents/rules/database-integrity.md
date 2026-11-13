---
trigger: glob
globs: ["db/**", "api/**", "monitor/**", "witness/**", "scripts/**", "**/*.sql", "**/*.py"]
authority: ReferralHandshake_FINAL_LOCKED_Architecture.md
sections: "§5, §7, §12, §23"
invariants: "I1, I2, I4, I5, I7, I9, I11, I12, I14, I15, I16"
---

# `.agents/rules/database-integrity.md` — PostgreSQL 16 Schema, Lock Order & Trigger Integrity

This rule file governs all database schema definitions, SQL queries, transaction boundaries, row locks, triggers, and role permissions for **ReferralHandshake (Protocol RHP-1)**.

---

## 1. PostgreSQL 16 Single-Primary Configuration (`D8`, `F1`)

1. **Engine & Durability:** PostgreSQL 16 single writable primary configured with `synchronous_commit=on` and `log_lock_waits=on`.
2. **Isolation Level:** `READ COMMITTED` for `rhp_app` transactions combined with explicit per-referral row locking (`SELECT ... FOR UPDATE`).
3. **Read-Only Snapshots:** `rhp_monitor` and `rhp_witness` **MUST** use `REPEATABLE READ READ ONLY` transactions and server-side cursors (`DECLARE ... CURSOR`) so they take zero row locks and see a single consistent snapshot.
4. **No Hot-Standby Locking:** Row locks (`SELECT ... FOR UPDATE`) cannot execute on read replicas. All command pipelines, poller claims, and outbox relays **MUST** connect to the primary.

---

## 2. Global Lock Order Proof & Session GUC Enforcement (`F1`, `I14`)

### 2.1 Total Lock Hierarchy
Every multi-table transaction **MUST** acquire row locks strictly in this forward order:
$$\text{referral} \longrightarrow \text{offer } (\text{ORDER BY id}) \longrightarrow \text{deadline } (\text{ORDER BY id}) \longrightarrow \text{outbox}$$

| Execution Path | Locks Acquired (in exact order) | Waits While Holding Another Lock? | Deadlock Possible? |
|---|---|---|---|
| `apply_command()` | `pg_try_advisory_xact_lock` (non-blocking) $\rightarrow$ `referral` (`FOR UPDATE`) $\rightarrow$ `offer` (`ORDER BY id FOR UPDATE`) $\rightarrow$ `deadline` (`ORDER BY id FOR UPDATE`) $\rightarrow$ `outbox` (`INSERT`) | Only forward in the total order (single referral per txn) | **No** |
| **Poller Phase 1** (`tick`) | `deadline` rows via a single `UPDATE ... WHERE id IN (SELECT ... ORDER BY due_at LIMIT 50 FOR UPDATE SKIP LOCKED)` committed immediately | **No** (`SKIP LOCKED` never waits) | **No** |
| **Poller Phase 2** (`tick`) | Invokes `apply_command(TIMEOUT)` per claimed deadline in a fresh transaction | Same as `apply_command()` | **No** |
| **Outbox Relay** | `outbox` rows via a single `UPDATE ... WHERE id IN (SELECT ... ORDER BY id LIMIT 20 FOR UPDATE SKIP LOCKED)` committed immediately | **No** (`SKIP LOCKED` never waits) | **No** |
| **Monitor & Witness** | `REPEATABLE READ READ ONLY` snapshot (plus single-row `heartbeat` upsert) | **No** | **No** |

### 2.2 Mandatory `rhp.locked_referral` Session GUC (`I14`)
The database trigger `rhp_require_lock()` rejects any `INSERT` or `UPDATE` on contract tables (`referral`, `offer`, `deadline`, `event`, `payload_grant`, `outbox`) unless the transaction has first locked the parent `referral` row and set the transaction-local GUC:
```sql
SELECT * FROM referral WHERE id = $1 FOR UPDATE;
SELECT set_config('rhp.locked_referral', $1::text, true);
```
**Exemptions built into `rhp_require_lock()`:**
1. **Poller Phase 1 claim:** `UPDATE deadline SET claimed_until = ...` where `(NEW.status, NEW.due_at) IS NOT DISTINCT FROM (OLD.status, OLD.due_at)` is exempt because it mutates only delivery-claim bookkeeping (`claimed_until`), not contract state.
2. **Outbox Relay update:** `UPDATE outbox SET visible_after = ..., attempts = ..., status = ...` is exempt because `INSERT INTO outbox` happens under the referral lock, while `UPDATE outbox` is delivery bookkeeping.

---

## 3. Complete 24-Table Schema Inventory (`F4`)

All 24 tables in `db/schema.sql` are locked. Never drop, rename, or weaken any table, column, domain, index, or constraint:

| # | Table Name | Primary Key | Key Constraints, Indexes & Invariants Enforced |
|---|---|---|---|
| 1 | `facility` | `id uuid` | `code UNIQUE`, `tier IN ('PHC','CHC','FRU','DH','MC','DISPATCH')`, integer `lat_e5, lon_e5` |
| 2 | `roster` | `id uuid` | `facility_id FK`, `role_slot IN ('NURSE','CMO','CONSULTANT','CLINICIAN','EMT','DISPATCHER','ADMIN','JUDGE_DESK')`, `UNIQUE(facility_id, role_slot, slot_no, valid_from)` |
| 3 | `facility_capability` | `(facility_id, capability)` | `capability cap_t`, `attested_at`, `expires_at` |
| 4 | `need_class_requirement` | `(need_class, capability)` | Maps `need_class_t` to required `cap_t` (`OT`, `BLOOD`, `ANAESTHETIST`, `PAEDIATRICIAN`, `NICU`) |
| 5 | `catchment_chain` | `(origin_facility_id, need_class, position)` | `position BETWEEN 1 AND 8`, `UNIQUE(origin_facility_id, need_class, target_facility_id)`, `CHECK (origin_facility_id <> target_facility_id)` |
| 6 | `device` | `id uuid` | `roster_id FK`, `CHECK (octet_length(pubkey)=32)`, `revoked_at` |
| 7 | `enrollment_ticket` | `id uuid` | `token_hash bytea UNIQUE`, single-use (`used_at`, `device_id FK`) |
| 8 | `session` | `id uuid` | `token_hash bytea UNIQUE`, `call_sid text UNIQUE`, `pin_failed`, `pin_locked_until`, `CHECK (device_id IS NOT NULL OR call_sid IS NOT NULL)` (`F7`) |
| 9 | `referral` | `id uuid` | `version`, `hs_state`, `tr_state`, `mode`, `chain uuid[] CHECK (cardinality(chain) BETWEEN 0 AND 8)`, `lease_offer_id DEFERRABLE FK`, `lease_epoch`, `open_offers CHECK (BETWEEN 0 AND 2)` (`I12`), `mgso4_status` (`D1`), `paper_code UNIQUE`, `head_seq`, `head_hash`, `head_ts`, `outcome`, terminal outcome `CHECK` (`I5`) |
| 10 | `offer` | `id uuid` | `UNIQUE(referral_id, facility_id)` (`I9`), `CREATE UNIQUE INDEX one_lease ON offer(referral_id) WHERE status = 'ACCEPTED'` (`I2`), `counter_round BETWEEN 0 AND 2`, `offer_chain_guard` trigger (`I7`) |
| 11 | `offer_resource_confirmation` | `(offer_id, capability)` | `confirmed_by FK`, `CHECK (expires_at > confirmed_at)` (`I15`) |
| 12 | `deadline` | `id uuid` | `kind IN ('ACK','DECISION','COUNTER_CONFIRM','NOTICE_VOICE','NOTICE_PROXY','HANDOVER','DISPATCH_ACTION','CLOSURE')`, `status IN ('PENDING','DONE','CANCELLED')`, `claimed_until`, partial indexes `deadline_due` and `deadline_ref` |
| 13 | `event` | `(referral_id, seq)` | `seq >= 1`, `event_id uuid UNIQUE` (`I4`), 28 allowed `type` values, `CHECK (rhp_detail_ok(type, detail))` (`I11`), `prev_hash` & `hash` 32 bytes (`I5`), `event_ao` & `event_guard` triggers (`I16`) |
| 14 | `key_version` | `id uuid` | `referral_id FK`, `kek_epoch`, `wrapped_dek`, `status IN ('ACTIVE','SHREDDED')`, `CHECK ((status='SHREDDED') = (wrapped_dek IS NULL))` |
| 15 | `event_secret` | `(referral_id, seq)` | `FOREIGN KEY (referral_id, seq) REFERENCES event`, `key_id FK`, `nonce`, `ciphertext` |
| 16 | `clinical_payload` | `referral_id uuid` | `key_id FK`, `nonce`, `ciphertext`, `schema_ver`, `expires_at` |
| 17 | `payload_grant` | `id uuid` | `CREATE UNIQUE INDEX one_active_grant ON payload_grant(referral_id, facility_id) WHERE revoked_at IS NULL` (`I10`) |
| 18 | `telemetry` | `id bigserial` | `event_id uuid UNIQUE`, `kind IN ('GPS','OBS')`, integer `lat_e5, lon_e5, acc_m, obs_val` |
| 19 | `idempotency` | `(actor_id, key)` | `CHECK (length(key) BETWEEN 8 AND 80)`, `request_hash bytea`, `status IN ('IN_FLIGHT','DONE')`, `http_status`, `response jsonb`, `expires_at` (`F14`, `I4`) |
| 20 | `inbox` | `id bigserial` | `UNIQUE(source, external_id)` for webhook deduplication |
| 21 | `outbox` | `id bigserial` | `FOREIGN KEY (referral_id, event_seq) REFERENCES event`, `channel IN ('SSE','FCM','VOICE','SMS','PROXY_PAGE')`, `status IN ('PENDING','SENT','DEAD')`, `attempts`, `visible_after` |
| 22 | `rejected_command` | `id bigserial` | `http_status IN (401,403,409,412,422,429)`, `reason_code`, append-only trigger `rejected_ao` (`I8`) |
| 23 | `checkpoint` | `id bigserial` | `kind IN ('REGULAR','RESTORE')`, `tree_size`, `root_hash`, `signature`, `CHECK ((kind='RESTORE') = (cold_signature IS NOT NULL AND restore_from IS NOT NULL))` (`F8`), append-only trigger `checkpoint_ao` |
| 24 | `heartbeat` | `(subject_kind, subject_id)` | `subject_kind IN ('POLLER','RELAY','MONITOR','WITNESS','DEVICE')`, `last_seen`, `ntp_offset_ms` (`F11`) |

---

## 4. Mandatory Triggers & SQL Functions (`db/schema.sql`)

Every deployment of the schema **MUST** include these exact trigger functions:
1. **`rhp_no_mutate()`**: Blocks `BEFORE UPDATE OR DELETE` on `event`, `checkpoint`, and `rejected_command` (`RAISE EXCEPTION 'APPEND_ONLY %', TG_TABLE_NAME`).
2. **`rhp_event_guard()`**: Runs `BEFORE INSERT ON event`. Enforces `NEW.seq = r.head_seq + 1`, `NEW.prev_hash = r.head_hash`, and `NEW.server_ts >= r.head_ts` (`RAISE EXCEPTION 'CHAIN_BREAK seq=%', NEW.seq`).
3. **`rhp_require_lock()`**: Runs `BEFORE INSERT OR UPDATE` on `referral`, `offer`, `deadline`, `event`, `payload_grant`, and `outbox`. Verifies `current_setting('rhp.locked_referral', true) IS NOT DISTINCT FROM rid` (`RAISE EXCEPTION 'I14_LOCK_NOT_HELD'`).
4. **`rhp_i1()`**: `CONSTRAINT TRIGGER i1_pending_deadline AFTER INSERT OR UPDATE ON referral DEFERRABLE INITIALLY DEFERRED`. Verifies that if `NEW.hs_state NOT IN ('CLOSED','CANCELLED')`, at least one `deadline` row exists with `referral_id = NEW.id AND status = 'PENDING'` (`RAISE EXCEPTION 'I1_NO_PENDING_DEADLINE'`).
5. **`rhp_chain_guard()`**: Runs `BEFORE INSERT ON offer`. Enforces that when `NEW.source = 'CHAIN'`, `NEW.facility_id = ANY(referral.chain)` (`RAISE EXCEPTION 'I7_NOT_IN_CHAIN'`).
6. **`rhp_allowed(t text)` & `rhp_detail_ok(t text, d jsonb)`**: Enforces `I11` (`F9`) on `event.detail` so only allowlisted keys per event type and only booleans, $\le 12$-digit integers, uppercase enum tokens (`^[A-Z0-9_]{1,40}$`), or lowercase UUIDs are stored.

---

## 5. Stateless Poller & Outbox Relay SQL Patterns

### 5.1 Two-Phase Poller Claim (`api/poller.py`)
Never hold a `deadline` row lock while calling `apply_command()`. Phase 1 is a standalone committed `UPDATE`:
```sql
UPDATE deadline
   SET claimed_until = clock_timestamp() + interval '5 seconds'
 WHERE id IN (
   SELECT id FROM deadline
    WHERE status = 'PENDING'
      AND due_at <= clock_timestamp()
      AND (claimed_until IS NULL OR claimed_until < clock_timestamp())
    ORDER BY due_at
    LIMIT 50
    FOR UPDATE SKIP LOCKED
 )
 RETURNING id, referral_id, kind, step, epoch;
```
Phase 2 iterates over the returned rows and invokes `apply_command(conn, TimeoutCmd(...), SYSTEM_SESSION, idem_key=f"timeout:{d.id}")` in a separate transaction per row. Inside `apply_command(TIMEOUT)`, the deadline is re-read under the referral lock (`WHERE id = $1 AND status = 'PENDING'`); if already `DONE` or `CANCELLED`, it returns `200` no-op.

### 5.2 Outbox Relay Claim (`api/relay.py`)
```sql
UPDATE outbox
   SET visible_after = clock_timestamp() + interval '30 seconds',
       attempts = attempts + 1
 WHERE id IN (
   SELECT id FROM outbox
    WHERE status = 'PENDING'
      AND visible_after <= clock_timestamp()
    ORDER BY id
    LIMIT 20
    FOR UPDATE SKIP LOCKED
 )
 RETURNING *;
```
After external adapter delivery succeeds, execute `UPDATE outbox SET status = 'SENT' WHERE id = $1`. If `attempts > 8`, set `status = 'DEAD'` and emit a dispatcher alert.

---

## 6. Database Roles & `BROKEN_BUILD` Isolation (`F20`)

| Role | Permitted Operations | Explicitly Prohibited |
|---|---|---|
| `rhp_app` | `SELECT, INSERT, UPDATE` on public tables; `DELETE` **only** on `event_secret, clinical_payload, idempotency, telemetry` (for crypto-shredding and TTL purge) | `UPDATE` or `DELETE` on `event, checkpoint, rejected_command`; DDL changes; superuser bypass |
| `rhp_monitor` | `SELECT` on `event, referral, offer, deadline, checkpoint, heartbeat, outbox, rejected_command`; `INSERT, UPDATE` on `heartbeat` | Any access to `clinical_payload`, `event_secret`, `key_version`, `session`, `roster`; any mutation of contract tables |
| `rhp_witness` | `SELECT` on `event, referral, checkpoint`; `INSERT` on `checkpoint`; `INSERT, UPDATE` on `heartbeat` | Any access to clinical tables or mutation of `referral`/`event` |
| `rhp_scratch` | Used **only** when `BROKEN_BUILD=1` against database `rhp_scratch_broken` (which omits `one_lease`) | Cannot authenticate to main database (`pg_hba.conf` + distinct password); aborts boot (exit `78`) if `REAL_DATA=1` |

---

## 7. DO / DO NOT Database Checklist
- **DO** resolve the circular foreign key between `referral.lease_offer_id` and `offer.id` using `ALTER TABLE referral ADD CONSTRAINT referral_lease_fk FOREIGN KEY (lease_offer_id) REFERENCES offer(id) DEFERRABLE INITIALLY DEFERRED`.
- **DO** order multi-row locks on `offer` and `deadline` by `ORDER BY id ASC`.
- **DO NOT** use `SERIALIZABLE` isolation instead of `READ COMMITTED` + `SELECT ... FOR UPDATE` (to avoid spurious serialization-failure storms under 200-way contention while preserving exact per-referral arbitration).
- **DO NOT** add `FLOAT`, `REAL`, or `DOUBLE PRECISION` columns to any table.