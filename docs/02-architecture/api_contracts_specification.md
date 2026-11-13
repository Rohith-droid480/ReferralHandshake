# ReferralHandshake (Protocol RHP-1) — API Contracts & Channel Protocols

**API Framework:** FastAPI (Python 3.12), Pydantic v2 (`extra='forbid'`)  
**Serialization:** RFC 8785 Canonical JSON Subset (ASCII keys, integer/string/boolean values only; **floats prohibited**)  
**Authentication:** `HttpOnly; Secure; SameSite=Strict` Session Cookie (`rhp_sid`) or Bearer Token + PIN on mutating clinical actions

---

## 1. Global HTTP & Idempotency Contract [F14]

Every state-changing `POST` request must supply an `Idempotency-Key` HTTP header ($8 \le \text{length} \le 80$ ASCII characters) and a client-generated UUIDv7 `event_id` in the JSON body.

### 1.1 Idempotency Edge-Case Matrix [F14]

| # | Scenario | Server Behaviour | HTTP Status & Reason Code |
|---|---|---|---|
| 1 | Same `(actor_id, key)`, identical payload hash, prior status `DONE` (`200`) | Returns stored JSON response without acquiring referral lock. | `200 OK` (stored body) |
| 2 | Same `(actor_id, key)`, identical payload hash, prior deterministic rejection | Returns stored rejection status and body from `idempotency.response`. | Stored `403` / `409` / `412` / `422` / `429` |
| 3 | Same `(actor_id, key)`, different `request_hash` | Rejects immediately in Step 1. | `422 Unprocessable Entity` (`KEY_REUSED_DIFFERENT_PAYLOAD`) |
| 4 | Concurrent duplicate request while first is `IN_FLIGHT` | `pg_try_advisory_xact_lock` returns `false` in Step 1. | `409 Conflict` (`DUPLICATE_IN_FLIGHT`) |
| 5 | Server crash / `reset_peer` before transaction commit | Transaction rolls back (`idempotency` row vanishes); client retry executes cleanly. | `200 OK` (on retry) |
| 6 | Replay after $48\text{-hour}$ `idempotency` TTL expiry | `idempotency` row expired, but `event.event_id UNIQUE` catches duplicate `event_id`. | `409 Conflict` (`DUPLICATE_EVENT_ID`, includes original event view) |
| 7 | Missing or malformed `Idempotency-Key` header | Rejected before DB transaction. | `422 Unprocessable Entity` (`MISSING_IDEMPOTENCY_KEY`) |
| 8 | New `Idempotency-Key` but reused `event_id` | Caught by `event.event_id UNIQUE` constraint inside `apply_command()`. | `409 Conflict` (`DUPLICATE_EVENT_ID`) |

### 1.2 Standard Error Envelope & Fencing Codes (`D7`)

Optimistic concurrency (`expected_version`, `expected_epoch`) is strictly separated from race-outcome conflicts:
- **`412 Precondition Failed` (`STALE_VERSION_OR_EPOCH`):** Client's `expected_version != referral.version` or `expected_epoch != referral.lease_epoch`. Logged to `rejected_command` (`I8`).
- **`409 Conflict`:** Valid precondition or concurrent race loser:
  - `LEASE_HELD`: Another facility won the ownership lease (`I2`).
  - `LATE_ACCEPT_REJECTED`: Offer left `OPEN`/`ACKED`/`SOFT_OPEN` (e.g., successor facility already `ACKED`) (`F12`, `F13`).
  - `STALE_CONFIRMATION_RECONFIRM_REQUIRED`: One or more `offer_resource_confirmation` rows have `expires_at <= server_ts` (`I15`, `F12`).
  - `INVALID_TRANSITION` / `INVALID_TR`: Transition disallowed by `transitions.yaml`.
  - `AT_CAPACITY`: Target facility open-offer load guard reached.

```json
{
  "error": "CONFLICT",
  "reason_code": "STALE_CONFIRMATION_RECONFIRM_REQUIRED",
  "referral_id": "01931f8e-7c00-7000-8000-000000000001",
  "current_version": 4,
  "current_lease_epoch": 0,
  "stale_capabilities": ["OT", "BLOOD"],
  "server_ts_us": 1763035200123456
}
```

---

## 2. Complete Command Transition Contract (`transitions.yaml` Specification)

All 14 commands execute through `apply_command()`:

| Command | Endpoint | Allowed Roles | Pre-State Guards | State Mutations & Side Effects | Possible Rejections |
|---|---|---|---|---|---|
| `CREATE` | `POST /v1/referrals` | `CLINICIAN`, `DISPATCHER` (proxy) | None | Inserts `referral` (`version=1`, `lease_epoch=0`, `tr_state='REQUESTED'`), encrypts `clinical_payload` with new DEK (`key_version`), snapshots `chain` ($\le F$), creates `OPEN` offer(s) (`chain[0]` in `SEQUENTIAL`, `chain[0..1]` in `PARALLEL2`), grants `payload_grant` to origin + offered facilities, arms `ACK`, `NOTICE_VOICE`, `NOTICE_PROXY` deadlines. If `chain` is empty, sets `hs_state='ESCALATED_TO_DISPATCHER'` + `DISPATCH_ACTION` deadline. | `401`, `403`, `422 SCHEMA`, `423 ANCHOR_REQUIRED` |
| `ACK` | `POST /v1/offers/{offer_id}/ack` | `NURSE`, `CMO`, `CONSULTANT`, `DISPATCHER` (proxy) | `offer.status == 'OPEN'` | Sets `offer.status='ACKED'`, `acked_at=ts`, `acked_by=roster_id`; marks `ACK`, `NOTICE_VOICE`, `NOTICE_PROXY` deadlines `DONE`; inserts `DECISION` deadline (`due_at = ts + D`); transitions any prior `SOFT_OPEN` offer on this referral to `TIMED_OUT` (decrementing `open_offers`); sets `hs_state='ACKNOWLEDGED'`. | `401`, `403`, `409 INVALID_TRANSITION`, `412` |
| `RESOURCE_CONFIRM` | `POST /v1/offers/{offer_id}/resource-confirm` | `NURSE`, `CMO`, `CONSULTANT` (PIN required) | `offer.status IN ('OPEN','ACKED','SOFT_OPEN')` | Upserts `offer_resource_confirmation(offer_id, capability, confirmed_by, confirmed_at=ts, expires_at=ts+confirm_ttl)`. Online-only command. | `401`, `403 PIN_INVALID`, `409`, `422`, `429 PIN_LOCKED` |
| `ACCEPT` | `POST /v1/offers/{offer_id}/accept` | `NURSE`, `CMO`, `CONSULTANT`, `DISPATCHER` (proxy) (PIN required) | `offer.status IN ('OPEN','ACKED','SOFT_OPEN')` AND `referral.lease_offer_id IS NULL` AND all required capabilities for `need_class` confirmed with `expires_at > ts` (`I15`) | Sets `offer.status='ACCEPTED'`, `decided_at=ts`; sets `referral.lease_offer_id=offer.id`, `lease_facility_id=offer.facility_id`, `lease_epoch = lease_epoch + 1`, `hs_state='ACCEPTED'`, `open_offers=0`; transitions all other open offers to `SUPERSEDED` and revokes their `payload_grant`s; cancels offer deadlines and arms `HANDOVER` deadline (`due_at = ts + H`). Appends `OFFER_ACCEPTED` and `LEASE_GRANTED`. | `403`, `409 LEASE_HELD`, `409 LATE_ACCEPT_REJECTED`, `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`, `412`, `429` |
| `COUNTER` | `POST /v1/offers/{offer_id}/counter` | `NURSE`, `CMO`, `CONSULTANT`, `DISPATCHER` (proxy) (PIN required) | `offer.status IN ('OPEN','ACKED')` AND `offer.counter_round < 2` | Sets `offer.status='COUNTERED'`, `counter_round = counter_round + 1`, `counter_mask = cmd.mask`; replaces `DECISION` deadline with `COUNTER_CONFIRM` (`due_at = min(ts + C, decision_due_at)`); sets `hs_state='COUNTERED'`. | `403`, `409 INVALID_TRANSITION`, `412`, `422`, `429` |
| `CONFIRM_COUNTER` | `POST /v1/offers/{offer_id}/confirm-counter` | `CLINICIAN`, `DISPATCHER` (proxy) (PIN required) | `offer.status == 'COUNTERED'` | If `confirmed == true`: re-verifies `I15` confirmations (`expires_at > ts`) and executes `ACCEPT` lease grant path. If `confirmed == false`: sets `offer.status='DECLINED'`, revokes `payload_grant`, decrements `open_offers`, and invokes `advance()`. | `403`, `409 LEASE_HELD`, `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`, `412`, `429` |
| `DECLINE` | `POST /v1/offers/{offer_id}/decline` | `NURSE`, `CMO`, `CONSULTANT`, `DISPATCHER` (proxy) (PIN required) | `offer.status IN ('OPEN','ACKED','SOFT_OPEN','COUNTERED')` | Sets `offer.status='DECLINED'`, `decline_reason=cmd.reason`, `decided_at=ts`; revokes facility's `payload_grant` (`GRANT_REVOKED`); cancels offer deadlines; decrements `open_offers`; invokes `advance()`. | `403`, `409 INVALID_TRANSITION`, `412`, `422`, `429` |
| `TIMEOUT` | Internal (`poller` Phase 2) | `SYSTEM` | `deadline.status == 'PENDING'` AND `deadline.epoch == referral.lease_epoch` | Marks `deadline.status='DONE'`. For `NOTICE_VOICE` / `NOTICE_PROXY`: enqueues outbox rows. For `ACK` expiry on `OPEN` offer: in `SEQUENTIAL`, sets offer to `SOFT_OPEN` and opens next chain target (expiring any older `SOFT_OPEN` offer so `open_offers <= 2`); if offer already `ACKED`, emits `ADVISORY_PREWARM` to next facility. For `DECISION` / `COUNTER_CONFIRM` expiry: in `SEQUENTIAL` sets `SOFT_OPEN` + opens next; in `PARALLEL2` sets `TIMED_OUT` + opens next. For `HANDOVER` / `CLOSURE` / `DISPATCH_ACTION`: emits overdue event and re-arms deadline (or auto-closes with `UNKNOWN_COUNTER_REFERRAL` on 2nd `CLOSURE` expiry). | `200 OK` (no-op if deadline already `DONE`/`CANCELLED`) |
| `ARRIVAL_REJECTED` | `POST /v1/referrals/{id}/arrival-rejected` | `NURSE`, `CMO`, `CONSULTANT`, `EMT`, `DISPATCHER` (PIN required) | `referral.hs_state == 'ACCEPTED'` | Sets lease offer `status='ARRIVAL_REJECTED'`; increments `lease_epoch = lease_epoch + 1`; clears `lease_offer_id` and `lease_facility_id`; revokes `payload_grant`; cancels `HANDOVER` deadline; appends `ARRIVAL_REJECTED` and `LEASE_REVOKED`; invokes `advance()`. | `403`, `409 INVALID_TRANSITION`, `412`, `429` |
| `DISPATCHER_ASSIGN` | `POST /v1/referrals/{id}/dispatcher-assign` | `DISPATCHER` (PIN required) | `referral.hs_state == 'ESCALATED_TO_DISPATCHER'` (or live override with reason) | Creates or updates offer for target facility with `source='DISPATCHER'`, `status='ACCEPTED'`, `proxy=true`; increments `lease_epoch = lease_epoch + 1`; supersedes any open offers; grants `payload_grant`; sets `hs_state='ACCEPTED'`; arms `HANDOVER` deadline. | `403`, `409 LEASE_HELD`, `412`, `422`, `429` |
| `TR_UPDATE` | `POST /v1/referrals/{id}/transport` | `EMT`, `NURSE`, `CMO`, `DISPATCHER`, `SYSTEM` (suggestion only) | `referral.hs_state NOT IN ('CLOSED','CANCELLED')` (`I3`) | Never reads `hs_state` for gating (`I3`). Advances `tr_state` (`REQUESTED -> DISPATCHED -> EN_ROUTE -> ARRIVED -> HANDED_OVER` or `TR_CANCELLED`) or records `TR_DESTINATION_CHANGE`. `ARRIVED` requires a human actor (`SYSTEM` geofence emits `ARRIVAL_SUGGESTED` only). At `HANDED_OVER`, cancels `HANDOVER` deadline and arms `CLOSURE` deadline. | `401`, `403`, `409 INVALID_TR` |
| `CANCEL` | `POST /v1/referrals/{id}/cancel` | `CLINICIAN`, `DISPATCHER` (PIN required) | `referral.hs_state NOT IN ('CLOSED','CANCELLED')` | Sets `hs_state='CANCELLED'`, `outcome=cmd.outcome`, `closed_at=ts`, `lease_offer_id=NULL`, `lease_facility_id=NULL`, `open_offers=0`; sets all active/accepted offers to `WITHDRAWN`; revokes all `payload_grant`s; cancels all `PENDING` deadlines. | `403`, `409 INVALID_TRANSITION`, `412`, `422`, `429` |
| `CLOSE` | `POST /v1/referrals/{id}/close` | `NURSE`, `CMO`, `CONSULTANT`, `DISPATCHER`, `SYSTEM` (2nd `CLOSURE` expiry) | `referral.hs_state IN ('ACCEPTED','ESCALATED_TO_DISPATCHER')` | Validates `outcome` (`ADMITTED_STABLE`, `ADMITTED_CRITICAL`, `DELIVERED_AT_RECEIVER` require `tr_state == 'HANDED_OVER'`). Sets `hs_state='CLOSED'`, `outcome=cmd.outcome`, `closed_at=ts`; cancels `PENDING` deadlines; revokes `payload_grant`s; schedules `clinical_payload` crypto-shredding. | `403`, `409 INVALID_TRANSITION`, `412`, `422 OUTCOME_REQUIRED` |
| `REVOKE_GRANT` | `POST /v1/grants/{grant_id}/revoke` | `ADMIN`, `DISPATCHER` (PIN required) | `payload_grant.revoked_at IS NULL` | Sets `revoked_at=ts`, `revoke_reason=cmd.reason`; appends `GRANT_REVOKED` event and outbox SSE control frame. | `403`, `409`, `429` |

---

## 3. REST Request & Response Schemas

### 3.1 `POST /v1/referrals` (`CREATE`)

**Request Body:**
```json
{
  "event_id": "01931f8e-7b10-7000-8000-000000000101",
  "mode": "SEQUENTIAL",
  "need_class": "OBSTETRIC_EMERGENCY",
  "origin_facility_id": "11111111-1111-4111-8111-111111111101",
  "chain": [
    "22222222-2222-4222-8222-222222222201",
    "33333333-3333-4333-8333-333333333301"
  ],
  "mgso4_status": "GIVEN",
  "profile_id": "PILOT_OB_CRITICAL",
  "client_ts_ms": 1763035200000,
  "pin": "4829",
  "clinical_card": {
    "identify_code": "SYNTH-OB-0042",
    "situation": "SEVERE_PREECLAMPSIA_34W",
    "background": "PRIMIGRAVIDA_BP_170_115",
    "assessment": "NEEDS_CEmONC_NICU_ANAESTHESIA",
    "recommendation": "IMMEDIATE_TRANSFER",
    "mgso4_loading_dose_g": 14,
    "mgso4_given_at_ms": 1763034600000,
    "oxytocin_status": "NONE_GIVEN",
    "vitals_systolic": 170,
    "vitals_diastolic": 115,
    "vitals_hr": 104,
    "vitals_spo2": 96
  }
}
```
*Note on `mgso4_status` (`D1`, `I3`):* Must be one of `"GIVEN"`, `"NONE_GIVEN"`, or `"UNKNOWN"`. If `"UNKNOWN"`, `mgso4_loading_dose_g` and `mgso4_given_at_ms` are omitted, the referral is created and dispatched without delay, and receiving desks render a prominent red banner: `"PRE-REFERRAL MgSO4 DOSE UNKNOWN — VERIFY BEFORE DOSING"`.

### 3.2 `POST /v1/offers/{offer_id}/accept` (`ACCEPT`)

**Request Body:**
```json
{
  "event_id": "01931f8e-9a20-7000-8000-000000000205",
  "expected_version": 2,
  "expected_epoch": 0,
  "pin": "7391",
  "client_ts_ms": 1763035215000
}
```

**Response Body (`200 OK`):**
```json
{
  "referral_id": "01931f8e-7c00-7000-8000-000000000001",
  "version": 3,
  "hs_state": "ACCEPTED",
  "tr_state": "EN_ROUTE",
  "lease_offer_id": "01931f8e-7c01-7000-8000-000000000002",
  "lease_facility_id": "22222222-2222-4222-8222-222222222201",
  "lease_epoch": 1,
  "open_offers": 0,
  "head_seq": 4,
  "head_hash_hex": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "server_ts_us": 1763035215104821
}
```

---

## 4. Real-Time SSE Stream, Outbound Exotel IVR & Paper Code Protocols

### 4.1 Server-Sent Events (`GET /v1/stream`) [F10, I10]
- **Headers:** Supports `Last-Event-ID: <referral_id>:<seq>` for gapless replay upon reconnect.
- **Heartbeat:** Server emits `: heartbeat <unix_ms>\n\n` every $15\text{ s}$ and re-evaluates session validity and `payload_grant` status.
- **Per-Event Authorization (`I10`):** Before pushing any event frame to a connected subscriber, the SSE hub checks `EXISTS (SELECT 1 FROM payload_grant WHERE referral_id = $1 AND facility_id = $2 AND revoked_at IS NULL)`.
- **Grant Revocation Frame (`F10`):** When a facility's offer transitions to `DECLINED`, `SUPERSEDED`, `TIMED_OUT` (final), `ARRIVAL_REJECTED`, or `WITHDRAWN`, its `payload_grant` is revoked and the outbox relay immediately emits:
  ```text
  event: GRANT_REVOKED
  id: 01931f8e-7c00-7000-8000-000000000001:5
  data: {"referral_id":"01931f8e-7c00-7000-8000-000000000001","facility_id":"22222222-2222-4222-8222-222222222201","reason":"SUPERSEDED"}
  ```
  Upon receiving `GRANT_REVOKED`, the React PWA immediately purges the decrypted clinical card from browser memory and DOM state.

### 4.2 Outbound Exotel IVR Webhook (`POST /v1/webhooks/exotel`) [F7]
1. **Outbound-Only Call Initiation:** Triggered at notice rung $A/4$ to pre-registered duty numbers (`roster.phone_e164`).
2. **Deduplication & Latency Budget:** Every webhook callback inserts `inbox(source='EXOTEL', external_id=CallSid || ':' || step, payload_sha256)` (`ON CONFLICT DO NOTHING`). Internal processing budget is capped at $1.5\text{ s}$ ($\le 2\text{ s}$ total HTTP response vs Exotel's $5\text{ s}$ limit `[V]`). If a database lock wait exceeds $1.5\text{ s}$, the endpoint returns a `200 OK` TwiML/Exotel XML `"Please hold"` loop and re-polls on the next callback.
3. **Voicemail / AMD + Press-1 Gate (`F7`):** Answering Machine Detection (`AnsweredBy`) plus an explicit $8\text{-second}$ prompt (`"Emergency referral alert. Press 1 to hear referral details"`). Voicemail, silence, or hangup records zero `ACK`. Only pressing `1` commits `apply_command(ACK, channel='VOICE')` and plays the pre-recorded (Kannada/Hindi/English) de-identified clinical summary (origin facility, `need_class`, required capabilities, ETA — **never** patient name).
4. **Decision & PIN Entry:** Keypad `1` (`ACCEPT`), `2` (`COUNTER` conditions menu), `3` (`DECLINE` reason menu), `9` (repeat), followed by 4-digit PIN terminated by `#` (URL-encoded as `%23`). The spoken `"Response recorded"` audio plays **only after** `apply_command()` commits `200 OK`.

### 4.3 Crockford Base32 + Mod-37 Paper Code Contract
- **Format:** 8 Crockford Base32 symbols (`0123456789ABCDEFGHJKMNPQRSTVWXYZ`, encoding a 40-bit integer $N$) followed by 1 check symbol (`N mod 37`) mapped onto the 37-symbol Crockford check alphabet (`0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U`), formatted as `XXXX-XXXX-C` (e.g., `7K4M-9P2W-*`).
- **Error Detection Math:** Because $37$ is prime and $\gcd(32^i, 37) = 1$, every single-character substitution alters $N \text{ by } \Delta \cdot 32^i \not\equiv 0 \pmod{37}$ ($100\%$ detection), and every adjacent transposition of distinct symbols $a, b$ alters $N \text{ by } (a - b) \cdot 31 \cdot 32^i \not\equiv 0 \pmod{37}$ ($100\%$ detection).
- **Endpoint:** `POST /v1/paper-code/resolve` (rate-limited to $10\text{ attempts/min}$ per session).

### 4.4 Proof, Monitor & Interoperability Endpoints
- `GET /checkpoints/latest`: Returns latest C2SP-style signed checkpoint note (`Cache-Control: no-store`).
- `GET /v1/referrals/{id}/proof?checkpoint_id={cid}`: Returns binary Merkle inclusion proof (`leaf_index`, `tree_size`, `path[]`) and full canonical `event` array for pure-JS browser verification.
- `GET /mode`: Returns `{"broken_build": false, "real_data": false, "profile_id": "DEMO_FAST", "db_name": "rhp_main"}`.
- `GET /v1/referrals/{id}/fhir`: Exports FHIR R4 Bundle (`ServiceRequest`, `Task`, `Encounter`, `Communication`) using the curated NRCeS-aligned code subset.
- `GET /v1/exports/xes`: Exports IEEE 1849 XES event log with timestamps bucketed to $4\text{-hour}$ windows and cells with $< 5$ referrals suppressed ($k \ge 5$, `F9`).