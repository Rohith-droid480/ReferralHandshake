---
trigger: glob
globs: ["api/**", "pwa/**", "android/**", "spec/**", "**/*.py", "**/*.ts", "**/*.tsx"]
authority: ReferralHandshake_FINAL_LOCKED_Architecture.md
sections: "§4, §5, §8, §9, §11, §15, §16"
invariants: "I1–I16"
---

# `.agents/rules/api-contracts.md` — Command Pipeline, State Transitions & Channel Contracts

Every HTTP endpoint, SSE stream, webhook handler, and client command in **ReferralHandshake (Protocol RHP-1)** must conform strictly to this specification.

---

## 1. The 10-Step `apply_command()` Pipeline (§5)

All state-mutating operations **MUST** execute through `apply_command(conn, cmd, sess, idem_key)` in this exact 10-step order:

1. **Step 1 — Idempotency (Before Referral Lock):**
   - Compute `h = sha256(jcs(cmd.body_for_hash()))`.
   - Acquire non-blocking transaction-scoped advisory lock: `SELECT pg_try_advisory_xact_lock(hashtextextended($1, 0))` on `f"{sess.roster_id}:{idem_key}"`. If `false`, return `409 DUPLICATE_IN_FLIGHT`.
   - Query `idempotency WHERE actor_id = $1 AND key = $2`. If found:
     - If `row.request_hash != h`, return `422 KEY_REUSED_DIFFERENT_PAYLOAD`.
     - If `row.status == 'DONE'`, replay `http(row.http_status, row.response)` (including stored `409`, `412`, `422` domain rejections).
   - Upsert `idempotency(..., status='IN_FLIGHT', expires_at=clock_timestamp() + interval '48 hours')`.
2. **Step 2 — Session Validation:**
   - Load `session`, `device`, and `roster` rows (read-only). Verify session is active, not expired, and `revoked_at IS NULL`; else return `401 SESSION_INVALID`.
3. **Step 3 — PIN Verification (Autonomous Failure Counter):**
   - If `cmd.needs_pin`: check `session.pin_locked_until > clock_timestamp()` $\rightarrow$ return `429 PIN_LOCKED`.
   - Verify PIN with Argon2id against `roster.pin_hash`. On mismatch, increment `session.pin_failed` and set `pin_locked_until` (backoff $0\text{ s}, 5\text{ s}, 30\text{ s}$, then $120\text{ s}$ lock on 3rd strike + emit `PIN_LOCKED` / page dispatcher) on a **separate autonomous database connection** so rolling back the main transaction never erases the failure count. Return `403 PIN_INVALID`.
4. **Step 4 — Lock Referral First, Set GUC & Monotone Timestamp:**
   - `SELECT * FROM referral WHERE id = $1 FOR UPDATE`.
   - `SELECT set_config('rhp.locked_referral', $1::text, true)`.
   - `SELECT GREATEST(clock_timestamp(), r.head_ts)` $\rightarrow$ `ts`.
   - Establish `SAVEPOINT sp_cmd`.
5. **Step 5 — Authority & Fencing (`I6`, `I8`):**
   - Verify actor's `roster.role_slot`, `facility_id`, and active validity window `[valid_from, valid_to)` match the command's required authority; else raise `Reject(403, "FORBIDDEN_ROLE_OR_FACILITY")`.
   - Check `expected_version == r.version` (and `expected_epoch == r.lease_epoch` where provided); on mismatch, raise `Reject(412, "STALE_PRECONDITION")`.
6. **Step 6 — Transition Guard (`transitions.yaml`):**
   - Lock offers (`SELECT * FROM offer WHERE referral_id = $1 ORDER BY id FOR UPDATE`) and deadlines (`ORDER BY id FOR UPDATE`).
   - Lookup transition in `transitions.yaml`. If invalid pre-state, raise `Reject(409, "INVALID_TRANSITION")` (or `409 LEASE_HELD` if an active lease already exists).
7. **Step 7 — Staleness & Resource Confirmation Checks (`F12`, `I15`):**
   - For `ACCEPT` or `CONFIRM_COUNTER(true)`: verify offer is in `{'OPEN', 'ACKED', 'SOFT_OPEN'}` (or `'COUNTERED'`). If offer moved to `'TIMED_OUT'` after successor ACKed, raise `Reject(409, "LATE_ACCEPT_REJECTED")`.
   - Verify every capability required by `need_class_requirement` for `r.need_class` has a row in `offer_resource_confirmation` for this offer with `expires_at > ts`. If any confirmation is missing or `expires_at <= ts`, raise `Reject(409, "STALE_CONFIRMATION_RECONFIRM_REQUIRED")`.
8. **Step 8 — Apply State Mutations:**
   - Update `offer` statuses, `referral.hs_state` / `tr_state`, `lease_offer_id`, `lease_facility_id`, `lease_epoch = r.lease_epoch + 1` (on lease grant/revoke), `open_offers`, `payload_grant` rows (`granted_at` / `revoked_at`), and `deadline` rows (`WHERE id = $1 AND status = 'PENDING'`).
9. **Step 9 — Append Hash-Chained Event & Outbox Rows:**
   - Increment `seq = r.head_seq + 1`, compute RFC 8785 JCS `core`, compute `hash = SHA256(r.head_hash || JCS(core))`, insert `event` (and `event_secret` / `clinical_payload` if applicable), insert `outbox` rows, and update `referral(version = r.version + 1, head_seq = seq, head_hash = hash, head_ts = ts)`.
10. **Step 10 — Finalize Idempotency & Commit (or Catch Domain `Reject`):**
    - On success: update `idempotency SET status='DONE', http_status=200, response=ev.view()` and `COMMIT`.
    - On `except Reject as e`: execute `ROLLBACK TO SAVEPOINT sp_cmd` (preserving the referral lock and Step 1 idempotency row), `INSERT INTO rejected_command(...)`, update `idempotency SET status='DONE', http_status=e.code, response=e.body`, and `COMMIT`.
    - On any unexpected database/system exception: abort the entire transaction so the `idempotency` row rolls back and the client can safely retry.

---

## 2. Complete Command & State Transition Matrix (§4)

| Command | Authorized Actor | Required Pre-State | State & Side-Effect Mutations | Deterministic Error Codes |
|---|---|---|---|---|
| `CREATE` | Rostered `CLINICIAN` (or `DISPATCHER` proxy) | None (new `referral_id`) | Insert `referral` (`epoch=0`, `tr_state='REQUESTED'`, truncate `chain` to $\le F$); if `chain` non-empty: `hs_state='OFFERED'`, open offer(s) to `chain[0]` (`SEQUENTIAL`) or `chain[0..1]` (`PARALLEL2`), grant payload to origin + offered facilities, arm `ACK`, `NOTICE_VOICE` ($A/4$), `NOTICE_PROXY` ($3A/4$) deadlines; if `chain` empty: `hs_state='ESCALATED_TO_DISPATCHER'` + `DISPATCH_ACTION` deadline | `422 SCHEMA_INVALID`, `403 FORBIDDEN` |
| `ACK` | Receiving duty role (`PWA` / `VOICE`) | Offer `OPEN` | Offer $\rightarrow$ `ACKED`; `ACK`, `NOTICE_VOICE`, `NOTICE_PROXY` deadlines $\rightarrow$ `DONE`/`CANCELLED`; arm `DECISION` deadline due at `ts + D`; any prior `SOFT_OPEN` offer on this referral $\rightarrow$ `TIMED_OUT` (decrement `open_offers`); `hs_state` $\rightarrow$ `ACKNOWLEDGED` (if lead) | `409 INVALID_TRANSITION` |
| `RESOURCE_CONFIRM` | PIN-verified receiving role | Offer in `OPEN`, `ACKED`, `SOFT_OPEN` | Live online command only: upsert `offer_resource_confirmation(offer_id, capability, confirmed_by, confirmed_at=ts, expires_at=ts + confirm_ttl)` | `409 INVALID_TRANSITION`, `422 INVALID_CAPABILITY` |
| `ACCEPT` | PIN-verified receiving role | Offer in `OPEN`, `ACKED`, `SOFT_OPEN`; `lease_offer_id IS NULL`; all required capabilities confirmed & `expires_at > ts` | Offer $\rightarrow$ `ACCEPTED`; `lease_offer_id=offer.id`, `lease_facility_id=offer.facility_id`, `lease_epoch = lease_epoch + 1`, `open_offers = 0`; other open offers $\rightarrow$ `SUPERSEDED` + their `payload_grant` revoked; pending offer deadlines $\rightarrow$ `CANCELLED`; arm `HANDOVER` deadline (`ts + H`); `hs_state` $\rightarrow$ `ACCEPTED`; emit `OFFER_ACCEPTED` + `LEASE_GRANTED` | `409 LEASE_HELD`, `409 LATE_ACCEPT_REJECTED`, `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`, `412 STALE_PRECONDITION` |
| `COUNTER` | PIN-verified receiving role | Offer in `OPEN`, `ACKED`; `counter_round < 2` | Offer $\rightarrow$ `COUNTERED`, `counter_round += 1`, `counter_mask` set; replace `DECISION` with `COUNTER_CONFIRM` due at `ts + min(C, remaining_D)`; `hs_state` $\rightarrow$ `COUNTERED` (if lead) | `409 MAX_COUNTERS_EXCEEDED`, `422` |
| `CONFIRM_COUNTER` | Referring `CLINICIAN` (or `DISPATCHER` proxy) | Offer `COUNTERED` | If `confirmed=true`: execute `ACCEPT` path (re-verifying `I15` confirmation TTLs and no competing lease); if `confirmed=false`: offer $\rightarrow$ `DECLINED`, revoke grant, run `advance()` | `409 LEASE_HELD`, `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` |
| `DECLINE` | PIN-verified receiving role | Offer in `OPEN`, `ACKED`, `SOFT_OPEN`, `COUNTERED` | Offer $\rightarrow$ `DECLINED` with structured `decline_reason`; revoke facility's `payload_grant`; cancel offer deadlines; run `advance()` | `409 INVALID_TRANSITION`, `422 REASON_REQUIRED` |
| `TIMEOUT` | `SYSTEM` (poller Phase 2) | `deadline.status == 'PENDING'` matching offer step/epoch | - `ACK` expiry on silent `OPEN` offer: in `SEQUENTIAL`, offer $\rightarrow$ `SOFT_OPEN` (if `open_offers == 2`, prior `SOFT_OPEN` $k-1 \rightarrow$ `TIMED_OUT` first) and open next in `chain`; in `PARALLEL2` or last target, offer $\rightarrow$ `TIMED_OUT` and run `advance()`.<br>- `ACK` expiry on `ACKED` offer: emit `ADVISORY_PREWARM` to next target in `chain` (not an offer).<br>- `DECISION` / `COUNTER_CONFIRM` expiry: in `SEQUENTIAL` with next target available, offer $\rightarrow$ `SOFT_OPEN` + open next; otherwise offer $\rightarrow$ `TIMED_OUT` + `advance()`.<br>- `HANDOVER` / `DISPATCH_ACTION` expiry: emit overdue event, re-page, re-arm.<br>- `CLOSURE` expiry: 1st expiry emits `CLOSURE_OVERDUE` and re-arms once; 2nd expiry executes `CLOSE(outcome='UNKNOWN_COUNTER_REFERRAL', proxy=true, actor=system)`. | `200` no-op if deadline is no longer `PENDING` |
| `ARRIVAL_REJECTED` | Receiving desk or `EMT` | `hs_state == 'ACCEPTED'` | Offer $\rightarrow$ `ARRIVAL_REJECTED`; `lease_offer_id = NULL`, `lease_facility_id = NULL`, `lease_epoch += 1`; revoke grant; emit `ARRIVAL_REJECTED` + `LEASE_REVOKED`; run `advance()` | `409 INVALID_TRANSITION` |
| `DISPATCHER_ASSIGN` | `DISPATCHER` | `hs_state == 'ESCALATED_TO_DISPATCHER'` (or live override with reason enum) | Create/update offer with `source='DISPATCHER'`, `status='ACCEPTED'`, `proxy=true`, `lease_epoch += 1`; supersede any open offers; `hs_state` $\rightarrow$ `ACCEPTED`; arm `HANDOVER` deadline | `409 LEASE_HELD`, `422 REASON_REQUIRED` |
| `TR_UPDATE` | `EMT`, `DISPATCHER`, or geofence hint | Any non-terminal `hs_state` (`I3`) | Advance `tr_state` (`REQUESTED -> DISPATCHED -> EN_ROUTE -> ARRIVED -> HANDED_OVER` or `TR_CANCELLED`). Geofence emits `ARRIVAL_SUGGESTED` only; transition to `ARRIVED` requires human actor (`F5`). At `HANDED_OVER`, arm `CLOSURE` deadline. | `409 INVALID_TR_TRANSITION` |
| `TR_DESTINATION_CHANGE` | `EMT` or `DISPATCHER` | `tr_state` prior to `ARRIVED` | Update `tr_facility_id` and emit `TR_DESTINATION_CHANGE(facility, reason, accepted)`; never modifies `hs_state` or lease | `409 ALREADY_ARRIVED` |
| `CANCEL` | `CLINICIAN` or `DISPATCHER` | Any non-terminal `hs_state` | `hs_state` $\rightarrow$ `CANCELLED` with outcome in taxonomy; open/accepted offers $\rightarrow$ `WITHDRAWN`; `lease_offer_id = NULL`; all active grants revoked; all pending deadlines $\rightarrow$ `CANCELLED` | `409 TERMINAL_STATE` |
| `CLOSE` | Receiving role, `DISPATCHER`, or `SYSTEM` (post-2x `CLOSURE`) | `hs_state` in `ACCEPTED`, `ESCALATED_TO_DISPATCHER` | Validate outcome against `tr_state` (`ADMITTED_*` and `DELIVERED_AT_RECEIVER` require `tr_state == 'HANDED_OVER'`); `hs_state` $\rightarrow$ `CLOSED`, `closed_at = ts`; revoke active grants; cancel pending deadlines; schedule `clinical_payload` crypto-shred | `422 OUTCOME_REQUIRED`, `409 HANDOVER_REQUIRED_FOR_OUTCOME` |
| `REVOKE_GRANT` | `ADMIN`, `DISPATCHER`, or `SYSTEM` | Active `payload_grant` (`revoked_at IS NULL`) | Set `revoked_at = ts`, `revoke_reason`; emit `GRANT_REVOKED` + outbox control frame (`F10`) | `409 GRANT_NOT_ACTIVE` |

---

## 3. Idempotency Edge-Case Matrix (`F14`, `I4`)

Every mutating HTTP request (`POST`, `PUT`, `PATCH`, `DELETE`) **MUST** carry an `Idempotency-Key` header ($8$ to $80$ ASCII characters):

| Scenario | Server Behavior | HTTP Status |
|---|---|---|
| Missing `Idempotency-Key` header on mutating endpoint | Reject before DB lock | `422 MISSING_IDEMPOTENCY_KEY` |
| Same `(actor_id, key)`, identical JCS payload hash, prior `200` | Replay stored `response` JSON without re-executing | `200 OK` (stored) |
| Same `(actor_id, key)`, identical JCS payload hash, prior domain rejection | Replay stored rejection (`409`, `412`, `422`) and `reason_code` | `409` / `412` / `422` (stored) |
| Same `(actor_id, key)`, different JCS payload hash | Reject immediately at Step 1 | `422 KEY_REUSED_DIFFERENT_PAYLOAD` |
| Concurrent duplicate request while first is still executing | `pg_try_advisory_xact_lock` returns `false` | `409 DUPLICATE_IN_FLIGHT` |
| Crash or connection reset before transaction commit | Entire transaction rolls back; `idempotency` row absent; retry executes cleanly | `200` (on retry) |
| Key replayed after $48\text{ h}$ TTL purge, carrying same `event_id` | Caught by `event.event_id UNIQUE` constraint; returns original event | `409 DUPLICATE_EVENT_ID` |
| Fresh `Idempotency-Key`, but reused `event_id` | Caught by `event.event_id UNIQUE` constraint | `409 DUPLICATE_EVENT_ID` |

---

## 4. RFC 8785 JCS Event Hashing Contract (`I5`, `I11`)

Every row inserted into `event` computes its SHA-256 hash over the previous event's 32-byte binary hash concatenated with the UTF-8 bytes of the RFC 8785 JCS canonical JSON of `core`:
```python
core = {
    "referral_id": str(referral_id),          # lowercase UUID string
    "seq": int(seq),                          # integer >= 1
    "event_id": str(event_id),                # lowercase UUID string
    "type": str(event_type),                  # uppercase enum string
    "epoch": int(epoch),                      # integer >= 0
    "actor_roster_id": str(actor_id) if actor_id else None,
    "facility_id": str(facility_id) if facility_id else None,
    "channel": str(channel),                  # PWA|ANDROID|VOICE|SMS_LINK|PAPER|DISPATCHER_PROXY|SYSTEM
    "proxy": bool(proxy),
    "detail": detail_dict,                    # must pass rhp_detail_ok(type, detail)
    "secret_hash": secret_hash_hex_or_none,   # lowercase hex string or null
    "client_ts_ms": int(client_ts_ms) if client_ts_ms is not None else None,
    "server_ts_us": int(server_ts_us),        # integer microseconds since epoch
}
jcs_bytes = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
event_hash = hashlib.sha256(prev_hash_bytes + jcs_bytes).digest()
```
- For `seq == 1` (`REFERRAL_CREATED`), `prev_hash_bytes = b"\x00" * 32`.
- **Strict Type Rule:** `core` and `detail` **MUST NEVER** contain floating-point numbers (`float`).

---

## 5. Channel-Specific Interface Contracts (§8, §15, §16)

1. **SSE Stream (`GET /v1/stream`):**
   - Authenticates via `HttpOnly; Secure; SameSite=Strict` session cookie.
   - Supports `Last-Event-ID` header to replay missed events from `event` table.
   - Emits a `: heartbeat\n\n` comment frame every $15\text{ s}$.
   - **Per-Event Grant Filter (`F10`, `I10`):** Before emitting any event frame or heartbeat, verify `(subscriber.facility_id, subscriber.role_slot)` holds an active `payload_grant` (`revoked_at IS NULL`). When a grant is revoked, push a `GRANT_REVOKED` control frame on the next relay cycle so the PWA immediately wipes clinical DOM state.
2. **Exotel Outbound IVR Webhook (`POST /v1/webhooks/exotel`):**
   - Deduplicate every callback via `INSERT INTO inbox(source, external_id, payload_sha256) VALUES ('EXOTEL', $1, $2) ON CONFLICT DO NOTHING`.
   - **AMD + Press-1 Gate (`F7`):** Answering machine detection (`AMD`) or silence never triggers `ACK`. The callee must press `1` within $8\text{ s}$ ("Press 1 to hear a referral") to commit `apply_command(ACK, channel='VOICE')`.
   - **PIN + `#` Gate:** Decisions (`1` accept, `2` conditions, `3` decline) require entering the roster PIN followed by `#` (URL-decoded from `%23`).
   - **Webhook Timing Budget:** Complete `apply_command()` within $\le 1.5\text{ s}$ (total HTTP response $\le 2\text{ s}$, well inside Exotel's $5\text{ s}$ timeout `[V]`). Play spoken "recorded" confirmation **only after** transaction commit; if $> 1.5\text{ s}$, play "please hold" and read committed status on the next callback.
3. **Crockford Base32 + Mod-37 Paper Code (`POST /v1/paper-code/resolve`):**
   - Format: $8$ Crockford Base32 payload characters ($40\text{ bits}$, integer $N$) + $1$ check character $= N \bmod 37$ using alphabet `0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U`.
   - Rejects $100\%$ of single-character substitutions and adjacent transpositions before hitting the database. Rate-limited to $10\text{ attempts/min}$ per session.
4. **Optional AI Intake Accelerator (`POST /v1/intake/draft`, `T3_EXTRAS`):**
   - **Cognitive Forcing Function:** Returns `423 ANCHOR_REQUIRED` unless the request includes clinician-committed `need_class` and `mgso4_status`.
   - Never returns confidence scores or natural-language explanations.