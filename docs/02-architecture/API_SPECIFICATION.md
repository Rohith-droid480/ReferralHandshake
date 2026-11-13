# ReferralHandshake (Protocol RHP-1) — API Specification

**Framework:** Python 3.12 + FastAPI + Pydantic v2 (`extra='forbid'`)  
**Base URL:** `/v1`  
**Content-Type:** `application/json; charset=utf-8` (except Exotel form/query webhooks and `text/event-stream` SSE)  
**Response Caching:** Every endpoint returns `Cache-Control: no-store`

---

## 1. Serialization, Canonical JSON (RFC 8785 JCS) & Global Headers

### 1.1 RFC 8785 JCS Canonicalization Rules
All request payload fingerprints (`idempotency.request_hash`) and event chain hashes (`event.hash`) use RFC 8785 JSON Canonicalization Scheme (JCS) restricted to the locked deterministic subset:
- **Allowed JSON Types:** ASCII strings, signed 64-bit integers (`-999999999999` to `999999999999`), booleans (`true`, `false`), arrays, and objects with lexicographically sorted ASCII keys.
- **Strictly Prohibited:** IEEE 754 floating-point numbers are banned across all API schemas. Coordinates use integer micro-degrees/10 (`lat_e5`, `lon_e5`, e.g., $12.97160^\circ \rightarrow 1297160$), durations use integer milliseconds, and timestamps use integer milliseconds (`client_ts_ms`) or microseconds (`server_ts_us`) since the Unix epoch.

### 1.2 Required HTTP Headers on Mutating Endpoints
| Header | Requirement | Format & Validation |
|---|---|---|
| `Idempotency-Key` | **Mandatory** on all `POST` command endpoints | ASCII string, $8 \le \text{length} \le 80$ (typically UUIDv7 or `<cmd>-<uuid>`). Missing or invalid length returns `422 MISSING_IDEMPOTENCY_KEY`. |
| `Authorization` or `Cookie` | **Mandatory** (except `/v1/auth/*` and `/v1/webhooks/exotel/*`) | `Bearer <opaque_session_token>` (Android/API) or `Cookie: rhp_sid=<opaque_session_token>` (`HttpOnly; Secure; SameSite=Strict` for PWA desks). |

---

## 2. Authentication, Device Enrollment & Judge QR Admission (`F7`, `D11`, `D12`)

### 2.1 `POST /v1/auth/tickets` — Issue Single-Use Enrollment Ticket (`ADMIN` only)
Creates a 15-minute single-use `enrollment_ticket` for binding a ward tablet or clinician phone to a `roster` slot.
- **Request Body:**
  ```json
  {
    "roster_id": "018f4a90-1111-7000-8000-000000000001",
    "ttl_seconds": 900
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "ticket_id": "018f4a90-2222-7000-8000-000000000002",
    "enrollment_token": "enr_9f8e7d6c5b4a32109f8e7d6c5b4a3210",
    "expires_at_ms": 1794615300000
  }
  ```

### 2.2 `POST /v1/auth/enroll` — Redeem Ticket & Register Device Public Key
Redeems the single-use `enrollment_token` (`SHA-256` matched against `enrollment_ticket.token_hash`), registers the device's 32-byte Ed25519 public key in `device`, and mints an opaque session token in `session`.
- **Request Body:**
  ```json
  {
    "enrollment_token": "enr_9f8e7d6c5b4a32109f8e7d6c5b4a3210",
    "pubkey_hex": "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
    "platform": "PWA"
  }
  ```
- **Response (`200 OK`):** Sets `Set-Cookie: rhp_sid=<token>; HttpOnly; Secure; SameSite=Strict; Path=/` and returns:
  ```json
  {
    "session_id": "018f4a90-3333-7000-8000-000000000003",
    "device_id": "018f4a90-4444-7000-8000-000000000004",
    "roster_id": "018f4a90-1111-7000-8000-000000000001",
    "facility_id": "018f4a90-0000-7000-8000-000000000010",
    "role_slot": "CMO",
    "session_token": "ses_4a5b6c7d8e9f01234a5b6c7d8e9f0123"
  }
  ```

### 2.3 `POST /v1/auth/qr-join` — Judge Arena Rotating-QR Admission (`D11`)
Validates a rotating QR token (`jti` valid for $20\text{ s}$, rotated every $15\text{ s}$ on the Big Screen) plus a Cloudflare Turnstile token (or LAN mode flag when `LAN_FALLBACK=1` and `REAL_DATA=0`), enforces the $20$-desk admission cap, and issues a synthetic hospital desk session.
- **Request Body:**
  ```json
  {
    "qr_jti": "qr_018f4a90-5555-7000-8000-000000000005",
    "turnstile_token": "0.cf_turnstile_response_token",
    "pubkey_hex": "3b6a27bcceb6a42d62a3a8d02a6f0d73653215771de243a63ac048a18b59da29"
  }
  ```
- **Errors:** `403 QR_EXPIRED_OR_USED`, `403 TURNSTILE_FAILED`, `429 JUDGE_CAP_REACHED` (when active `JUDGE_DESK` sessions $\ge 20$).

---

## 3. Idempotency & Optimistic/Epoch Fencing Matrix (`F14`, `D7`)

### 3.1 Complete Idempotency Edge-Case Matrix (`F14`)

| Case # | Client Request Condition | Server Action in Step 1 of `apply_command()` | HTTP Status & Reason Code |
|---|---|---|---|
| **1** | Same `(actor_id, key)`, identical JCS payload hash, prior status `DONE` (`200`) | Returns stored `http_status` (`200`) and stored `response` JSON without acquiring referral lock | `200 OK` (exact replay) |
| **2** | Same `(actor_id, key)`, identical JCS payload hash, prior status `DONE` (`409`/`412`/`422`) | Returns stored domain rejection HTTP status and stored error JSON | `409` / `412` / `422` (exact replay) |
| **3** | Same `(actor_id, key)`, **different** JCS payload hash | Rejects immediately in Step 1 | `422 KEY_REUSED_DIFFERENT_PAYLOAD` |
| **4** | Concurrent duplicate request while first request holds `pg_try_advisory_xact_lock` | Non-blocking advisory lock returns `false`; rejects immediately so client backs off | `409 DUPLICATE_IN_FLIGHT` |
| **5** | Server/DB crash before transaction commit | Entire transaction rolls back; `idempotency` row is absent; client retry executes cleanly | `200 OK` (on retry) |
| **6** | Key older than $48\text{ h}$ (purged from `idempotency`), same `event_id` | Step 1 inserts new `idempotency` row; `event.event_id UNIQUE` catches duplicate and returns original event | `409 DUPLICATE_EVENT_ID` |
| **7** | Mutating request missing `Idempotency-Key` header (or length $< 8$ or $> 80$) | Rejects before DB transaction | `422 MISSING_IDEMPOTENCY_KEY` |
| **8** | Different `Idempotency-Key`, but reused `event_id` from an earlier committed event | Caught by `event.event_id UNIQUE` check before insert; rolls back to `sp_cmd` and logs rejection | `409 DUPLICATE_EVENT_ID` |

### 3.2 Version vs. Lease Epoch Fencing (`D7`, `I8`)
- **`expected_version` (`referral.version`):** Optimistic concurrency check on the referral row. If the client supplies `expected_version` and `expected_version != referral.version`, Step 5 raises `412 STALE_VERSION` (unless the command is a race-evaluated `ACCEPT`/`CONFIRM_COUNTER`, which evaluates lease state first so concurrent hospital desks receive a semantic `409 LEASE_HELD` rather than a generic `412`).
- **`expected_epoch` (`referral.lease_epoch`):** Monotonic fencing token that increments on every ownership grant or revocation. Any command carrying `expected_epoch != referral.lease_epoch` is rejected in Step 5 with `412 STALE_EPOCH` and logged in `rejected_command` (`I8`).

---

## 4. Contract Command Endpoints (`apply_command()` Routes)

All 14 contract commands execute through the single `apply_command()` pipeline (`SYSTEM_DESIGN.md` Section 5.2). Every request model enforces `model_config = ConfigDict(extra='forbid')`.

### 4.1 `POST /v1/referrals` — Command: `CREATE`
Creates a referral, envelope-encrypts the clinical payload under a fresh per-referral DEK, snapshots the catchment chain (truncated to $F$ facilities for the active profile), creates initial offer(s) and notice/ACK deadlines, and grants payload access to the origin and offered facilities.
- **Request Body:**
  ```json
  {
    "referral_id": "018f4a90-7777-7000-8000-000000000100",
    "event_id": "018f4a90-7777-7000-8000-000000000101",
    "mode": "SEQUENTIAL",
    "need_class": "OBSTETRIC_EMERGENCY",
    "mgso4_status": "GIVEN",
    "chain": [
      "018f4a90-0000-7000-8000-000000000010",
      "018f4a90-0000-7000-8000-000000000020",
      "018f4a90-0000-7000-8000-000000000030"
    ],
    "profile_id": "PILOT_OB_CRITICAL",
    "pin": "4829",
    "client_ts_ms": 1794614400000,
    "clinical_isbar": {
      "schema_ver": 1,
      "identify_code": "SYNTH-OB-042",
      "situation": "SEVERE_PREECLAMPSIA_34W",
      "background": "G2P1_BP_170_115_PROTEINURIA_3PLUS",
      "assessment": "NEEDS_CEmONC_OT_AND_NICU",
      "recommendation": "IMMEDIATE_TRANSFER",
      "mgso4_loading_dose_g": 14,
      "mgso4_given_at_ms": 1794613800000,
      "oxytocin_status": "NONE_GIVEN"
    }
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "referral_id": "018f4a90-7777-7000-8000-000000000100",
    "version": 1,
    "hs_state": "OFFERED",
    "tr_state": "REQUESTED",
    "lease_epoch": 0,
    "open_offers": 1,
    "paper_code": "48K9M2P7W",
    "head_seq": 2,
    "head_hash_hex": "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
    "server_ts_us": 1794614400125000
  }
  ```

### 4.2 `POST /v1/referrals/{referral_id}/offers/{offer_id}/ack` — Command: `ACK`
Records human acknowledgement on a receiving desk (`PWA`) or voice IVR (`VOICE`), marks `ACK`, `NOTICE_VOICE`, and `NOTICE_PROXY` deadlines `DONE`, schedules the `DECISION` deadline at $\text{ts} + D$, and transitions any prior `SOFT_OPEN` offer on the referral to `TIMED_OUT`.
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000102",
    "expected_epoch": 0,
    "client_ts_ms": 1794614405000
  }
  ```

### 4.3 `POST /v1/referrals/{referral_id}/offers/{offer_id}/confirm-resource` — Command: `RESOURCE_CONFIRM`
Live-only command confirming a single required capability (`OT`, `BLOOD`, `ANAESTHETIST`, `PAEDIATRICIAN`, `NICU`) with `expires_at = server_ts + confirm_ttl`.
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000103",
    "capability": "OT",
    "pin": "7391",
    "expected_epoch": 0,
    "client_ts_ms": 1794614410000
  }
  ```

### 4.4 `POST /v1/referrals/{referral_id}/offers/{offer_id}/accept` — Command: `ACCEPT`
Verifies PIN, verifies no lease is currently held (`409 LEASE_HELD`), verifies the offer is in `OPEN`, `ACKED`, or `SOFT_OPEN` (`409 LATE_ACCEPT_REJECTED`), verifies every capability in `need_class_requirement` has an unexpired row in `offer_resource_confirmation` (`409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`, `I15`), grants the lease (`status='ACCEPTED'`, `lease_epoch + 1`), transitions other open offers to `SUPERSEDED` and revokes their `payload_grant`s, cancels decision deadlines, and schedules the `HANDOVER` deadline.
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000104",
    "pin": "7391",
    "expected_version": 3,
    "expected_epoch": 0,
    "client_ts_ms": 1794614412000
  }
  ```
- **Response (`200 OK`):** Returns updated state with `hs_state: "ACCEPTED"`, `lease_facility_id`, and `lease_epoch: 1`.
- **Domain Rejection Responses:**
  - `409 {"error": "LEASE_HELD", "winning_facility_id": "...", "lease_epoch": 1}`
  - `409 {"error": "LATE_ACCEPT_REJECTED", "offer_status": "TIMED_OUT"}`
  - `409 {"error": "STALE_CONFIRMATION_RECONFIRM_REQUIRED", "expired_capabilities": ["OT", "NICU"]}`
  - `412 {"error": "STALE_EPOCH", "current_epoch": 1}`

### 4.5 `POST /v1/referrals/{referral_id}/offers/{offer_id}/counter` — Command: `COUNTER`
Submits a structured counter-offer (`counter_round < 2`) with a bitmask of conditional capabilities (`1=WITHOUT_NICU`, `2=ANAESTHETIST_IN_20M`, `4=BLOOD_ON_REQUEST`, `8=OT_IN_30M`) and sets `COUNTER_CONFIRM` deadline to $\text{ts} + \min(C, \text{remaining } D)$.
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000105",
    "counter_mask": 2,
    "pin": "7391",
    "expected_epoch": 0,
    "client_ts_ms": 1794614415000
  }
  ```

### 4.6 `POST /v1/referrals/{referral_id}/offers/{offer_id}/confirm-counter` — Command: `CONFIRM_COUNTER`
Executed by the referring clinician (`CLINICIAN`) or dispatcher proxy to accept (`confirmed: true`) or reject (`confirmed: false`) a `COUNTERED` offer. When `confirmed: true`, re-verifies `I15` confirmation freshness and executes the `ACCEPT` lease-grant path.
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000106",
    "confirmed": true,
    "pin": "4829",
    "expected_epoch": 0,
    "client_ts_ms": 1794614420000
  }
  ```

### 4.7 `POST /v1/referrals/{referral_id}/offers/{offer_id}/decline` — Command: `DECLINE`
Records a documented decline for a structured missing-resource reason, revokes the declining facility's `payload_grant` (`GRANT_REVOKED`), and calls `advance()` to offer the next target in `referral.chain` (or transition to `ESCALATED_TO_DISPATCHER` if exhausted).
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000107",
    "decline_reason": "NO_NICU_VENTILATOR",
    "suggested_facility_id": "018f4a90-0000-7000-8000-000000000030",
    "pin": "7391",
    "expected_epoch": 0,
    "client_ts_ms": 1794614415000
  }
  ```
  *(Allowed `decline_reason` tokens: `NO_OT_AVAILABLE`, `NO_NICU_VENTILATOR`, `NO_ANAESTHETIST`, `NO_BLOOD_STOCK`, `NO_PAEDIATRICIAN`, `AT_CAPACITY`.)*

### 4.8 `POST /v1/referrals/{referral_id}/arrival-rejected` — Command: `ARRIVAL_REJECTED`
Records a broken commitment when an `ACCEPTED` facility cannot admit the patient upon arrival, increments `lease_epoch`, clears `lease_offer_id`/`lease_facility_id`, revokes the `payload_grant`, and calls `advance()`.
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000108",
    "reason": "OT_OCCUPIED_UNEXPECTED_CASE",
    "pin": "7391",
    "expected_epoch": 1,
    "client_ts_ms": 1794616000000
  }
  ```

### 4.9 `POST /v1/referrals/{referral_id}/dispatcher-assign` — Command: `DISPATCHER_ASSIGN`
Human dispatcher assignment when `hs_state == 'ESCALATED_TO_DISPATCHER'` (or administrative override with mandatory reason enum). Creates an offer with `source='DISPATCHER'` and `status='ACCEPTED'`, increments `lease_epoch`, and marks `proxy=true`.
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000109",
    "target_facility_id": "018f4a90-0000-7000-8000-000000000040",
    "reason": "PHONE_CONFIRMED_WITH_DUTY_CMO",
    "override_existing": false,
    "pin": "9012",
    "expected_epoch": 1,
    "client_ts_ms": 1794616100000
  }
  ```

### 4.10 `POST /v1/referrals/{referral_id}/transport` — Command: `TR_UPDATE` (`I3`)
Advances or updates the independent transport track (`DISPATCHED`, `EN_ROUTE`, `ARRIVED`, `HANDED_OVER`, `TR_CANCELLED`, or `TR_DESTINATION_CHANGE`). Never reads or blocks on `hs_state` (`I3`). Transitioning to `ARRIVED` requires a human actor (`EMT`, `NURSE`, `CMO`, `DISPATCHER`); automated geofence hits submit `suggestion_only: true` which emits `ARRIVAL_SUGGESTED` without changing `tr_state`.
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000110",
    "tr_state": "ARRIVED",
    "tr_facility_id": "018f4a90-0000-7000-8000-000000000010",
    "reason": "CREW_CONFIRMED_AT_CASUALTY_DOOR",
    "suggestion_only": false,
    "dwell_s": 45,
    "proxy": false,
    "client_ts_ms": 1794615800000
  }
  ```

### 4.11 `POST /v1/referrals/{referral_id}/cancel` — Command: `CANCEL`
Cancels a non-terminal referral (`PATIENT_REFUSED`, `DELIVERED_AT_ORIGIN`, `STABILISED_NO_TRANSFER_NEEDED`, `DUPLICATE_ERRONEOUS`), transitions open/accepted offers to `WITHDRAWN`, revokes all non-origin `payload_grant`s, and cancels all `PENDING` deadlines.
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000111",
    "outcome": "PATIENT_REFUSED",
    "reason": "FAMILY_DECLINED_TRANSFER_SIGNED",
    "pin": "4829",
    "expected_epoch": 0,
    "client_ts_ms": 1794614900000
  }
  ```

### 4.12 `POST /v1/referrals/{referral_id}/close` — Command: `CLOSE`
Closes an `ACCEPTED` or `ESCALATED_TO_DISPATCHER` referral with a mandatory outcome from the 9-value outcome taxonomy, revokes active `payload_grant`s, cancels remaining deadlines, and sets `clinical_payload.expires_at` for retention-based crypto-shredding.
- **Request Body:**
  ```json
  {
    "event_id": "018f4a90-7777-7000-8000-000000000112",
    "outcome": "ADMITTED_STABLE",
    "reason": "HANDOVER_COMPLETE_IN_LABOR_WARD",
    "pin": "7391",
    "expected_epoch": 1,
    "client_ts_ms": 1794616400000
  }
  ```

### 4.13 `POST /v1/referrals/{referral_id}/grants/{grant_id}/revoke` — Command: `REVOKE_GRANT`
Explicitly revokes a facility's `payload_grant` (`ADMIN` or `DISPATCHER`) and triggers an immediate `GRANT_REVOKED` SSE control frame.

### 4.14 `POST /v1/referrals/paper-link` — Link or Reconcile by 9-Character Paper Code
Allows a receiving desk to look up a referral using the 9-character Crockford Base32 + mod-37 check code (`paper_code`) printed on the physical referral slip (rate-limited to $10\text{ attempts/min}$ per session). If valid and the caller's facility is in `referral.chain` or is the arriving destination, grants read access or initiates Case `(b)`/`(c)` arrival handling.
- **Request Body:**
  ```json
  {
    "paper_code": "48K9M2P7W",
    "pin": "7391"
  }
  ```

### 4.15 `POST /v1/referrals/{referral_id}/telemetry` — Append-Only GPS & Vitals Batch (`I4`)
Ingests batched offline/online GPS coordinates (`lat_e5`, `lon_e5`, `acc_m`) and vitals observations (`SYSTOLIC_BP`, `DIASTOLIC_BP`, `HEART_RATE`, `SPO2`, `FETAL_HR`). Deduplicates via `telemetry.event_id UNIQUE` (`ON CONFLICT (event_id) DO NOTHING`) for set-union offline merge.
- **Request Body:**
  ```json
  {
    "items": [
      {
        "event_id": "018f4a90-8888-7000-8000-000000000201",
        "kind": "GPS",
        "lat_e5": 1297160,
        "lon_e5": 7759460,
        "acc_m": 9,
        "client_ts_ms": 1794615000000
      },
      {
        "event_id": "018f4a90-8888-7000-8000-000000000202",
        "kind": "OBS",
        "obs_code": "SYSTOLIC_BP",
        "obs_val": 168,
        "client_ts_ms": 1794615005000
      }
    ]
  }
  ```

### 4.16 `POST /v1/intake/ai-draft` — AI Intake Accelerator with Cognitive Forcing Function (`T3_EXTRAS`)
Enforces the think-first Cognitive Forcing Function (`A2`): if `anchor_need_class` or `anchor_mgso4_status` is absent, immediately returns **`423 ANCHOR_REQUIRED`** without returning any draft fields. Never includes confidence scores or explanations (`R08`).

---

## 5. Server-Sent Events (SSE) Stream & Grant Revocation (`F10`, `I10`)

### 5.1 `GET /v1/events/stream`
Establishes a persistent HTTP/2 SSE stream authenticated via the `rhp_sid` cookie. Supports `Last-Event-ID: <outbox_id>` header for gapless resume.
- **Per-Event Authorization Filter (`I10`):** Before emitting any event frame (and on every $15\text{ s}$ `: heartbeat` comment), the server checks whether the subscriber's `(facility_id, role_slot)` holds an active row in `payload_grant WHERE referral_id = $1 AND facility_id = $2 AND revoked_at IS NULL`.
- **Clinical Payload Stripping & `GRANT_REVOKED` Frame:**
  - If an active grant exists, the frame includes decrypted `clinical_isbar`.
  - When a grant is revoked (upon `DECLINE`, `SUPERSEDED`, `ARRIVAL_REJECTED`, `CANCELLED`, or `CLOSED`), the outbox relay immediately emits:
    ```text
    id: 4092
    event: GRANT_REVOKED
    data: {"referral_id":"018f4a90-7777-7000-8000-000000000100","facility_id":"018f4a90-0000-7000-8000-000000000010","reason":"SUPERSEDED"}
    ```
  - Upon receiving `GRANT_REVOKED`, the React PWA immediately purges the referral's clinical payload from memory and DOM state.

---

## 6. Read-Only Projection, Verification & Health Endpoints

| Endpoint | Role Access | Description & Response Payload |
|---|---|---|
| `GET /v1/referrals/{id}` | Rostered roles + `JUDGE_DESK` | Returns current `referral` state, `offers[]`, `deadlines[]`, and (only if caller holds active `payload_grant`) decrypted `clinical_isbar`. |
| `GET /v1/referrals/{id}/events` | Rostered roles + `JUDGE_DESK` | Returns ordered array of committed `event` rows (`seq = 1..head_seq`) with `prev_hash_hex`, `hash_hex`, and canonical `core` fields for pure-JS browser verification. |
| `GET /v1/checkpoints/latest` | Public / Witness / `JUDGE_DESK` | Returns the latest signed C2SP Merkle checkpoint (`checkpoint_id`, `tree_size`, `root_b64`, `note_text`, `signature_b64`, `signer_key_id`). |
| `GET /v1/referrals/{id}/proof` | Public / Witness / `JUDGE_DESK` | Returns the $O(\log N)$ binary Merkle inclusion proof (`leaf_index`, `tree_size`, `path: [{"side": "L"\|"R", "hash": "b64"}]`, `checkpoint_id`). |
| `GET /v1/metrics` | Public / Big Screen | Returns live-measured `I1`–`I16` monitor violation counts, p50/p95 command latency, deadline lateness, `heartbeats[]`, and APOT-split handover KPIs. |
| `GET /v1/mode` | Public / Big Screen | Returns `{"broken_build": false, "real_data": false, "profile_id": "DEMO_FAST", "lan_mode": false}`. |
| `GET /healthz` | Public / Load Balancer | Re-runs `validate(profile, REAL_DATA)` (`I13`) and checks `heartbeat` freshness ($< 15\text{ s}$). Returns `200 OK` or `503 SERVICE_UNAVAILABLE`. |