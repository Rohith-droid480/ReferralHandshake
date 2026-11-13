# ARCHITECTURE_AND_INVARIANTS_GUARDRAILS.md — Technical Guardrails & Invariants Reference

**Rule:** Every line of code you write must conform to these exact architectural mechanisms from `ReferralHandshake_FINAL_LOCKED_Architecture.md`.

---

## 1. Locked Stack vs. Banned Technologies

| Category | Locked Choice (MUST USE) | Banned Technologies (NEVER USE OR INSTALL) |
|---|---|---|
| **Database** | PostgreSQL 16 (single primary, `synchronous_commit=on`, `READ COMMITTED` + explicit `SELECT ... FOR UPDATE`) | SQLite for contract state, Redis, Kafka, Debezium, MongoDB, Blockchain |
| **Backend API** | Python 3.12, FastAPI, `psycopg` (v3), Pydantic v2 (`extra='forbid'`), Argon2id (`argon2-cffi`) | Django, SQLAlchemy ORM magic that hides lock order, floating-point numbers in hashed JSON |
| **Web / Crypto** | React PWA, SSE (`Last-Event-ID`, 15s heartbeat), `@noble/curves/ed25519`, `@noble/hashes/sha256`, RFC 8785 JCS | WebSockets, browser `crypto.subtle` for Ed25519 (breaks on iOS Safari & LAN HTTP), CRDTs for contract state |
| **Infra / Reach** | Docker Compose, Toxiproxy, Cloudflare Tunnel + LAN fallback, Exotel Outbound IVR, DLT static SMS | Kubernetes, WhatsApp APIs, on-device LLMs, unverified third-party push carrying PHI |

---

## 2. Global Lock Order Discipline (Fixes F1, Enforces I14)

Deadlocks are prevented by enforcing a strict global lock hierarchy across the entire codebase:
$$\text{referral} \longrightarrow \text{offer (ORDER BY id)} \longrightarrow \text{deadline (ORDER BY id)} \longrightarrow \text{outbox}$$

1. **Inside `apply_command()`:**
   - First acquire the non-blocking idempotency advisory lock: `pg_try_advisory_xact_lock`.
   - Next lock the `referral` row (`SELECT * FROM referral WHERE id=%s FOR UPDATE`).
   - Immediately stamp the transaction-local GUC: `SELECT set_config('rhp.locked_referral', %s, true)` so the PostgreSQL trigger `rhp_require_lock()` permits writes to `referral`, `offer`, `deadline`, `event`, `payload_grant`, and `outbox`.
   - Lock `offer` rows (`ORDER BY id FOR UPDATE`) and `deadline` rows (`ORDER BY id FOR UPDATE`) only *after* holding the `referral` lock.
2. **Inside the Two-Phase Poller (`rhp.poller`):**
   - **Phase 1:** Execute a single standalone `UPDATE deadline SET claimed_until = ... WHERE id IN (SELECT ... FOR UPDATE SKIP LOCKED) RETURNING ...` and **COMMIT immediately** without touching `referral`.
   - **Phase 2:** For each claimed deadline, invoke `apply_command(TimeoutCmd(...))`, which locks `referral` first and re-verifies `WHERE id=$1 AND status='PENDING'`.
3. **Inside the Outbox Relay (`rhp.relay`):**
   - Claim pending rows with a single `UPDATE outbox SET visible_after = ... FOR UPDATE SKIP LOCKED` statement and commit immediately.
4. **Inside the Monitor & Witness:**
   - Connect as `rhp_monitor` or `rhp_witness` using `REPEATABLE READ READ ONLY`. Never acquire row locks.

---

## 3. The 10-Step `apply_command()` Pipeline (Exact Order Required)

Every state-changing command (`CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `COUNTER`, `CONFIRM_COUNTER`, `DECLINE`, `TIMEOUT`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`, `TR_UPDATE`, `CANCEL`, `CLOSE`, `REVOKE_GRANT`) MUST flow through `apply_command()` in these exact 10 steps:

1. **Idempotency (Pre-Lock):** Hash canonical request body (`SHA-256(JCS(body))`). Acquire `pg_try_advisory_xact_lock(hashtextextended(f"{actor_id}:{idem_key}", 0))`; if false, return `409 DUPLICATE_IN_FLIGHT`. Check `idempotency` table: if `request_hash` mismatches, return `422 KEY_REUSED_DIFFERENT_PAYLOAD`; if `DONE`, replay stored `http_status` and `response` (including stored `409`/`412`/`422`). Otherwise upsert `status='IN_FLIGHT'`.
2. **Session Check:** Load session by opaque token hash (`session.token_hash`). Verify not expired or revoked (`401 SESSION_INVALID`).
3. **PIN Verification (Mutating Commands):** Verify PIN with Argon2id. If invalid, increment `session.pin_failed` on a **separate autonomous database connection** (so rolling back the main transaction never erases failed PIN attempts!), lock session for `120s` on strike 3 (`PIN_LOCKED` + page dispatcher), and return `403 PIN_INVALID` (or `429 PIN_LOCKED`).
4. **Lock Referral & Monotone Clock:** `SELECT * FROM referral WHERE id=%s FOR UPDATE`. Set `rhp.locked_referral` GUC. Compute authoritative monotone timestamp: `ts = GREATEST(clock_timestamp(), r.head_ts)`. Open `SAVEPOINT sp_cmd`.
5. **Authority & Fencing:** Verify active roster slot, facility match, and grant. Check `expected_version` and `expected_epoch`; if stale, raise `Reject(412, "STALE_PRECONDITION")`.
6. **Transition Guard:** Lock offers (`ORDER BY id`) and lookup `(cmd.type, r.hs_state, offer.status)` in `transitions.yaml`.
7. **Staleness & Confirmation Check (I15):** On `ACCEPT` or `CONFIRM_COUNTER(true)`, verify all required capabilities in `need_class_requirement` are confirmed in `offer_resource_confirmation` with `expires_at > ts`. If expired, raise `Reject(409, "STALE_CONFIRMATION_RECONFIRM_REQUIRED")`. If offer was superseded or late-accept window closed, raise `Reject(409, "LEASE_HELD" | "LATE_ACCEPT_REJECTED")`.
8. **Apply State Effects:** Update `offer`, increment `referral.lease_epoch` (on lease grant/revoke), maintain `open_offers` (`0..2`), update `payload_grant`, mark satisfied `deadline` rows `DONE`/`CANCELLED`, and insert new `deadline` rows (ensuring `I1` at least 1 `PENDING` deadline if non-terminal).
9. **Append Hash-Chained Event & Outbox:**
   - Increment `seq = r.head_seq + 1`.
   - Build `core` dict using **only ASCII keys, strings, booleans, and integers** (`client_ts_ms`, `server_ts_us`—floats are strictly forbidden by RFC 8785 JCS rule).
   - Compute `hash = SHA256(r.head_hash || JCS(core))`.
   - Insert into `event` (validated by `rhp_detail_ok(type, detail)` and `rhp_event_guard()`), write encrypted `event_secret` / `clinical_payload` if applicable, update `referral.head_seq`, `head_hash`, `head_ts`, `version = version + 1`, and insert `outbox` rows last.
10. **Finalize & Commit (or Savepoint Rollback on Domain Reject):**
    - On success: update `idempotency` to `DONE` with HTTP `200` and response JSON; `COMMIT`.
    - On deterministic `Reject(code, reason)`: `ROLLBACK TO SAVEPOINT sp_cmd` (keeping the referral lock), insert audit row into `rejected_command`, update `idempotency` to `DONE` with `code` and `reason`, and `COMMIT`.

---

## 4. The 16 Invariants (`I1–I16`) Quick-Check Table

Before completing any step, verify your code does not violate any of these invariants:

| ID | Invariant Summary | DB / Code Enforcement Mechanism |
|---|---|---|
| **I1** | Every non-terminal referral has $\ge 1$ `PENDING` deadline; overdue acted on within $\tau$ | Deferred constraint trigger `i1_pending_deadline` at `COMMIT` |
| **I2** | At most 1 active lease per referral; `lease_epoch` strictly increases | Partial unique index `one_lease ON offer(referral_id) WHERE status='ACCEPTED'` + referral row lock |
| **I3** | Transport updates (`TR_UPDATE`) are accepted in every non-terminal `hs_state` | Transport handler never gates on `hs_state`; geofence only emits `ARRIVAL_SUGGESTED` |
| **I4** | Every `event_id` appears once; per-referral `seq` is gap-free (`1..N`) | `idempotency` PK, `event.event_id UNIQUE`, `PRIMARY KEY(referral_id, seq)`, `rhp_event_guard` trigger |
| **I5** | Hash chain & checkpoint signatures verify; `CLOSED`/`CANCELLED` require `outcome` | Append-only triggers `event_ao`/`checkpoint_ao`; `referral` CHECK constraint |
| **I6** | Every response comes from a rostered role, registered device/number, verified PIN, or proxy | Steps 2, 3, and 5 of `apply_command()` |
| **I7** | System-chosen offer targets $\in$ `referral.chain`; dispatcher offers carry `source='DISPATCHER'` | Trigger `offer_chain_guard` |
| **I8** | Stale `expected_version` / `expected_epoch` is never applied and always logged | Step 5 raises `412` -> logged in `rejected_command` |
| **I9** | A facility is an offer target at most once per referral (no $A \to B \to A$ loops) | `UNIQUE (referral_id, facility_id)` on `offer` |
| **I10** | Clinical payload frames go only to subscribers with an active `payload_grant` | Per-event SSE grant check + immediate `GRANT_REVOKED` control frame on revoke |
| **I11** | `event.detail` contains ONLY allowlisted keys and primitive enum/int/bool/UUID values (no PHI) | Pydantic `Literal` schemas + PostgreSQL `CHECK (rhp_detail_ok(type, detail))` |
| **I12** | At most 2 open offers (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) at any instant | `referral.open_offers CHECK (open_offers BETWEEN 0 AND 2)` updated under lock |
| **I13** | Configured worst-case escalation time satisfies $T_{\max} = F \cdot (A + D + \varepsilon) \le B$ | Startup validator refuses boot if violated or if demo profile used with `REAL_DATA=1` |
| **I14** | No contract-state table write occurs without holding the `referral` row lock | Trigger `rhp_require_lock` checks session GUC `rhp.locked_referral` |
| **I15** | No lease is granted from a resource confirmation expired at `server_ts` | Step 7 checks `expires_at > ts`; returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` |
| **I16** | `server_ts` is monotonically non-decreasing per referral | `ts = GREATEST(clock_timestamp(), r.head_ts)` + `rhp_event_guard` trigger |

---

## 5. Clinical Safety & Claims Register Guardrails

1. **Never Block Care on Missing Drug History (Fixes D1):** `mgso4_status` (`GIVEN | NONE_GIVEN | UNKNOWN`) is *answer-required*, never *knowledge-required*. `UNKNOWN` is valid, never blocks `CREATE` or ambulance dispatch, and renders a high-visibility red banner (`"Pre-referral MgSO4 dose unknown — verify before dosing"`) on the receiving desk.
2. **Anti-Goodhart UI Rules:** Receiving desks must display a prioritized queue **without countdown clocks** (which distort clinical triage). APOT-style `ARRIVED -> HANDED_OVER` time must be tracked separately from `OFFERED -> ACCEPTED` time.
3. **Forbidden Wording in UI, Copy, Comments & Slides:** Never write `"lives saved"`, `"deaths prevented"`, `"eliminates ping-pong"`, `"ABDM compliant"`, `"mathematically proven system"`, `"immutable log"`, `"BSA certified"`, `"zero loopholes"`, or `"first/only"`. Use only authorized wording from `FINAL_LOCKED_Architecture.md` §19.