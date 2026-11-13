# EDGE_CASE_CATALOG.md — ReferralHandshake (Protocol RHP-1)

**System:** Referral Handshake Protocol (RHP-1) & Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru)  
**Data Mode:** Synthetic Only (`REAL_DATA=0`)  
**Precedence Hierarchy:** `ReferralHandshake_LOCKED_Problem_Statement_v7.md` $>$ Research findings tagged `[V]` $>$ `ReferralHandshake_v8_LOCKED_Solution.md` $>$ `ReferralHandshake_FINAL_LOCKED_Architecture.md` $>$ `ReferralHandshake_3Gem_Antigravity_Workflow.md`

> **Evidence & Weakness Status Tags:**  
> - **`[V]`** Verified primary source · **`[V*]`** Secondary/vendor source · **`[CONFLICT]`** Sources disagree · **`[GAP]`** No reliable source found; parameterised · **`[verify]`** Pre-event verification test required.  
> - **`CLOSED`** Deterministic mechanism enforced in code/DDL + named automated test.  
> - **`BOUNDED`** Stated technical residual + explicit quantitative bound + live monitor/operator alarm.  
> - **`OPEN`** Named owner + interim operational mitigation + required closing evidence.

---

## 0. Architectural Guardrails & Non-Negotiable Locks

Every edge-case handler in this catalog obeys the following locked rules:
1. **Coherence Rule:** Every component is strictly (a) a state/event in the contract, (b) an interface producing or consuming those events, or (c) a read-only projection of the committed event log.
2. **Global Lock Order (`F1`, `I14`):** Multi-table transactions acquire row locks strictly in the order `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`. The database trigger `rhp_require_lock` rejects any contract-state write unless the transaction has set the session GUC `rhp.locked_referral` to the target `referral.id`.
3. **Two Independent Tracks (`I3`, `D1`, `D2`):** The Handshake track (`CREATED`, `OFFERED`, `ACKNOWLEDGED`, `ACCEPTED`, `COUNTERED`, `ESCALATED_TO_DISPATCHER`, `CANCELLED`, `CLOSED`) and the Transport track (`REQUESTED`, `DISPATCHED`, `EN_ROUTE`, `ARRIVED`, `HANDED_OVER`, `TR_CANCELLED`) execute in parallel. Transport commands (`TR_UPDATE`, `TR_DESTINATION_CHANGE`) never read `hs_state` and never block care. Pre-referral intervention status (`mgso4_status` $\in \{\text{\texttt{GIVEN}}, \text{\texttt{NONE\_GIVEN}}, \text{\texttt{UNKNOWN}}\}$) is answer-required, never knowledge-required, and never blocks dispatch.
4. **Fencing vs. Race Separation (`D7`, `I2`, `I8`):** Optimistic row concurrency (`expected_version`) and ownership fencing (`expected_epoch`) are separate from race resolution. Stale preconditions return `HTTP 412 Precondition Failed` and log to `rejected_command`; lost concurrent races or expired resource confirmations return `HTTP 409 Conflict` (`LEASE_HELD`, `LATE_ACCEPT_REJECTED`, `STALE_CONFIRMATION_RECONFIRM_REQUIRED`) and log to `rejected_command`.
5. **Offer Cap (`F13`, `I12`):** At most $2$ offers per referral may be in the open set $\{\text{\texttt{OPEN}}, \text{\texttt{ACKED}}, \text{\texttt{COUNTERED}}, \text{\texttt{SOFT\_OPEN}}\}$ at any instant (`CHECK (open_offers BETWEEN 0 AND 2)`).
6. **Monotone Authoritative Server Time (`F11`, `I16`):** All deadline and confirmation calculations use `ts = GREATEST(clock_timestamp(), referral.head_ts)` evaluated under the `referral` row lock. Client timestamps (`client_ts_ms`) are recorded for audit only and never govern state transitions or expiries.
7. **Canonical JSON (`F8`, `I5`):** RFC 8785 JCS canonicalization permits only ASCII keys, strings, booleans, and integers (`^-?[0-9]{1,12}$`). Floating-point numbers are strictly prohibited across all hashed payloads and `event.detail` objects.

---

## 1. Master Failure-Mode & Attack Matrix (52 Architectural Cases)

Every row in this matrix is enforced by the production pipeline (`apply_command()`, poller, relay, witness, or client adapters) and verified by the named test in the conformance suite. No row claims an unbounded or unexamined "none" residual (`F15`).

| ID | Class | Scenario | Detection Mechanism | Automated System Response | Human Fallback | Inv | Bounded Technical Residual & Reason | Test ID | Status |
|---|---|---|---|---|---|---|---|---|---|
| **C1** | Concurrency | $200$ simultaneous `ACCEPT` requests on the same referral (single offer or across `PARALLEL2` offers) | PostgreSQL row-lock wait queue on `referral` + `one_lease` partial unique index | First holder of `SELECT * FROM referral WHERE id=%s FOR UPDATE` commits `status='ACCEPTED'` and increments `lease_epoch`; remaining $199$ receive `409 LEASE_HELD` (recorded in `rejected_command`) | Losing desks see explicit `LEASE_HELD` reason and winning facility code | `I2` | Relies on PostgreSQL 16 single-primary row-lock and partial unique index correctness | `T-C1` (`race200`) | `CLOSED` |
| **C2** | Concurrency | `ACCEPT` command arrives concurrently with Poller Phase 2 `TIMEOUT` command | Per-referral `FOR UPDATE` serialization | Whichever transaction acquires the `referral` lock first commits: if `ACCEPT` wins, deadline becomes `CANCELLED` and `TIMEOUT` returns `200 no-op`; if `TIMEOUT` wins (`SEQUENTIAL`), offer transitions to `SOFT_OPEN` and `ACCEPT` still succeeds under the late-accept rule if successor has not ACKed | None required; both orderings produce legal, audited contract states | `I2` | Either serialization order is possible within the millisecond race window; both are deterministic and logged | `T-C2` | `CLOSED` |
| **C3** | Concurrency | Late `ACCEPT` from step $k$ arrives after step $k+1$ has already committed `ACK` | Offer status check in `apply_command()` Step 6/7 (`offer.status == 'TIMED_OUT'`) | When step $k+1$ commits `ACK`, step $k$'s `SOFT_OPEN` offer is atomically transitioned to `TIMED_OUT`; step $k$'s subsequent `ACCEPT` is rejected with `409 LATE_ACCEPT_REJECTED` | Receiving desk at step $k$ sees rejection notice; may contact dispatcher if capacity reopened | `I2` | Step $k$'s offline client sees the rejection only upon next network sync | `T-C3` | `CLOSED` |
| **C4** | Concurrency | Facility 1 submits `CONFIRM_COUNTER(true)` concurrently with Facility 2 submitting `ACCEPT` in `PARALLEL2` mode | Per-referral `FOR UPDATE` lock | First transaction to lock `referral` grants the lease (`lease_epoch + 1`) and marks the other open offer `SUPERSEDED` (revoking its `payload_grant`); second transaction rolls back to `SAVEPOINT sp_cmd`, logs `rejected_command`, and returns `409 LEASE_HELD` | Referrer and losing facility see exact winner on UI | `I2`, `I12` | Decided deterministically under a single row lock | `T-C4` | `CLOSED` |
| **C5** | Concurrency | Poller deadline claim vs. live API command lock-ordering conflict | PostgreSQL `log_lock_waits=on` + `pg_stat_database.deadlocks` delta check | Poller Phase 1 claims deadlines via a single committed `UPDATE ... FOR UPDATE SKIP LOCKED` without holding `referral`; Phase 2 calls `apply_command(TIMEOUT)` which locks `referral -> offer -> deadline -> outbox` in strict global order | None required | `I14` | Assumes PostgreSQL internal lock manager correctness; deadlock counter delta is verified to be $0$ | `T-F1` (`lock_order_200way`) | `CLOSED` |
| **C6** | Concurrency | Duplicate timer firing (two poller instances claim the same deadline after a 5 s claim lapse) | Re-read of `deadline.status` under the `referral` lock + deterministic idempotency key `timeout:<deadline_id>` | First `TIMEOUT` marks `deadline.status = 'DONE'`; second `TIMEOUT` either hits the idempotency cache (`200`) or sees `status != 'PENDING'` under the referral lock and returns `200 no-op` | None required | `I1`, `I4` | Status check under `referral` lock guarantees zero duplicate state transitions | `T-C6` | `CLOSED` |
| **C7** | Concurrency | Stale writer submits command with outdated `expected_version` or `expected_epoch` | Step 5 `fence(r, cmd)` check inside `apply_command()` | Rolls back to `SAVEPOINT sp_cmd`, inserts row into `rejected_command(http_status=412, reason_code='STALE_VERSION'|'STALE_EPOCH')`, finalizes idempotency record, returns `412 Precondition Failed` | Client refetches latest referral snapshot and prompts user if state changed | `I8` | Deterministic rejection under `referral` row lock | `T-I8` | `CLOSED` |
| **C8** | Concurrency | Command or escalation logic attempts to open a 3rd concurrent offer | Step 6 transition guard + PostgreSQL `CHECK (open_offers BETWEEN 0 AND 2)` + soft-open eviction rule | Before opening offer $k+1$ in `SEQUENTIAL` mode, any still-`SOFT_OPEN` offer at $k-1$ is transitioned to `TIMED_OUT`; any direct violation raises constraint error and aborts | Escalates to dispatcher when chain slots are exhausted | `I12` | Enforced both in transition code and by database `CHECK` constraint | `T-F13` (`open_cap`) | `CLOSED` |
| **T1** | Timer | Poller process crashes mid-batch after Phase 1 claim | `heartbeat` table (`subject_kind='POLLER'`) staleness $> 15\text{ s}$ | `deadline.claimed_until` expires after $5\text{ s}$; surviving or restarted poller instance re-claims the row on the next $1\text{ s}$ tick | Operator alerted if poller heartbeat exceeds $15\text{ s}$ | `I1` | Deadline execution delayed by at most $\le 5\text{ s}$ (claim lease) $+ 1\text{ s}$ (poll interval) $= 6\text{ s}$ | `T-T1` | `BOUNDED` |
| **T2** | Timer | Host system clock steps forward by $\Delta$ | `heartbeat.ntp_offset_ms` monitor check every $5\text{ s}$ (alarm at $> 2000\text{ ms}$) | Deadlines due within $\Delta$ fire early, causing premature escalation only; `one_lease` and row locks still prevent double leases; `SOFT_OPEN` preserves prior target's ability to accept; poller batch limit caps fan-out to $50\text{ claims/tick}$ | Operator investigates NTP daemon (`chronyd` configured slew-only) | `I2`, `I16` | Extra escalations bounded by step size $\Delta$; zero safety invariant violations | `T-F11` (`clock_step`) | `BOUNDED` |
| **T3** | Timer | Host system clock steps backward by $\Delta$ | `heartbeat.ntp_offset_ms` $> 2000\text{ ms}$ alarm | `ts = GREATEST(clock_timestamp(), referral.head_ts)` preserves non-decreasing `server_ts` per referral (`I16`); pending deadlines fire up to $\Delta$ late | Operator investigates host clock | `I16` | Deadline firing delayed by at most $\Delta$ ($\le 2\text{ s}$ before monitor alarm trips) | `T-F11` (`clock_step`) | `BOUNDED` |
| **T4** | Timer | Deadline backlog storm after a database or poller outage ($n$ overdue deadlines) | Monitor query on `deadline WHERE status='PENDING' AND due_at < now() - tau` | Poller claims $50$ rows per $1\text{ s}$ tick ordered by `due_at ASC` (`ORDER BY due_at LIMIT 50 FOR UPDATE SKIP LOCKED`), draining oldest deadlines first | Dispatcher paged on backlog alarm | `I1` | Backlog of $n$ rows drains in $\lceil n / 50 \rceil$ ticks | `T-T4` | `BOUNDED` |
| **T5** | Timer | PostgreSQL primary fails over to synchronous standby mid-timer | Connection reset in API/poller + health check | Managed Multi-AZ promotes synchronous standby (`synchronous_commit=on` guarantees zero committed data loss); poller and API reconnect and resume from durable `deadline` rows | Operator monitors failover completion | `I1` | Failover window is typically $60\text{–}120\text{ s}$ `[V*]`; deadlines due during failover fire immediately upon reconnect | `T-T5` | `BOUNDED` |
| **T6** | Timer | Unauthorized edit or corruption of timing profile file (`A`, `D`, `F`, `B`) | Startup validator `validate(profile, REAL_DATA)` checks Ed25519 signature against `COLD_PUB`, verifies $F \cdot (A + D + \epsilon) \le B$, and blocks demo profiles when `REAL_DATA=1` | Application refuses to boot (non-zero exit before binding socket) | Admin restores cold-key signed profile file | `I13` | Offline cold-key compromise is out of band (tracked under `S3`) | `T-F2`, `T-F3` | `CLOSED` |
| **N1** | Network | Receiving desk clicks `ACCEPT` while offline, reconnects minutes later | Step 7 staleness check in `apply_command()` | Offline UI displays `"pending, not confirmed"`; on reconnect, if offer left `OPEN`/`ACKED`/`SOFT_OPEN` returns `409 LATE_ACCEPT_REJECTED`; if any required `offer_resource_confirmation.expires_at <= server_ts` returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` | PWA opens live reconfirmation modal to re-run `RESOURCE_CONFIRM` then fresh `ACCEPT` | `I15` | Deterministic server-side rejection of stale confirmations | `T-F12` (`offline_stale`) | `CLOSED` |
| **N2** | Network | HTTP response lost in transit after server commits transaction; client retries | Step 1 idempotency check (`PRIMARY KEY (actor_id, key)`) | Server matches `(actor_id, key)` and `request_hash`, sees `status='DONE'`, and replays the exact stored `http_status` and `response` JSON without touching `referral` | None required | `I4` | Idempotency keys retained $48\text{ h}$; beyond $48\text{ h}$, `event.event_id UNIQUE` still blocks duplicate events (`409 DUPLICATE_EVENT_ID`) | `T-F14` (`idem_matrix`) | `CLOSED` |
| **N3** | Network | SSE connection drops silently on hospital Wi-Fi or cellular link | $15\text{ s}$ SSE heartbeat timer on client and server | Client `EventSource` reconnects with `Last-Event-ID: <seq>`; server replays missed events for that referral (filtered by current `payload_grant`) | User can also click manual refresh | `I4` | UI view can be stale for at most $\le 15\text{ s}$ before reconnect triggers | `T-N3` | `BOUNDED` |
| **N4** | Network | Ambulance enters cellular dead zone during transport | Device heartbeat age $> 30\text{ s}$ in `heartbeat` / `telemetry` | Android Room outbox / PWA queue buffers `GPS` and `OBS` rows with UUIDv7 `event_id`; command centre displays `"last confirmed Ns ago"`; reconnect merges via idempotent `ON CONFLICT (event_id) DO NOTHING` set-union | Crew communicates via voice/radio to dispatcher; dispatcher can enter proxy `TR_UPDATE` | `I3` | Live map position is stale for the duration of the physical RF outage | `T-N4` | `BOUNDED` |
| **N5** | Network | Exotel retries IVR webhook callback due to network jitter | `inbox` table `UNIQUE (source, external_id)` check | `INSERT INTO inbox ... ON CONFLICT DO NOTHING` deduplicates the webhook retry and returns the cached TwiML/Exotel XML response within the $2\text{ s}$ budget | None required | `I4` | Exact deduplication by external callback ID | `T-N5` | `CLOSED` |
| **N6** | Network | Database lock contention delays Exotel webhook execution past $1.5\text{ s}$ | Webhook handler internal $1.5\text{ s}$ timeout guard (Exotel hard limit is $5\text{ s}$ `[V]`) | Handler returns HTTP 200 with `<Say>Please hold</Say>` + `<Redirect>` polling callback; background command finishes commit; next callback reads committed state and speaks `"Recorded"` | If call drops before redirect, ladder advances to next slot or `NOTICE_PROXY` at $3A/4$ | `I1` | Caller waits at most one extra IVR redirect cycle ($\approx 2\text{ s}$) | `T-N6` | `BOUNDED` |
| **N7** | Network | Venue internet / Cloudflare tunnel fails during live demo | Preflight / continuous uplink probe | Switch to local hotspot `LAN_MODE=1` QR desk; pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256` execute without `crypto.subtle` (which browsers disable on plain HTTP `[V]`) | Switch to pre-recorded MP4 clip if Wi-Fi spectrum is completely jammed | `I5` | LAN HTTP disables PIN entry for non-synthetic roles and refuses boot if `REAL_DATA=1` | `T-N7` | `BOUNDED` |
| **N8** | Network | Flaky mobile network triggers aggressive client retry storm | Per-session / per-IP token-bucket rate limiter + Step 1 `pg_try_advisory_xact_lock` | Concurrent duplicate requests receive `409 DUPLICATE_IN_FLIGHT`; excessive rate receives `429 Too Many Requests` with `Retry-After`; completed requests replay idempotently | None required | `I4` | Burst of requests within the $\le 1\text{ s}$ rate-limiter window reaches Step 1 advisory lock | `T-N8` | `BOUNDED` |
| **I1** | Identity | Unrostered user or wrong facility role attempts `ACCEPT` / `COUNTER` / `DECLINE` | Step 2 session validation + Step 5 `authorize(conn, r, s, cmd)` check against `roster` (`valid_from <= ts <= valid_to`) and `offer.facility_id` | Rolls back to `SAVEPOINT sp_cmd`, records `rejected_command(http_status=403, reason_code='ROLE_OR_FACILITY_UNAUTHORIZED')`, returns `403 Forbidden` | Admin reviews `rejected_command` audit log | `I6` | Shared-PIN misuse by a colleague physically sharing the same rostered device is indistinguishable from the rostered user | `T-I6` | `CLOSED` |
| **I2** | Identity | Attacker attempts brute-force guessing of 4-digit PIN | Step 3 Argon2id verification ($\approx 100\text{ ms}$) + autonomous transaction incrementing `session.pin_failed` | Backoff delays of $0\text{ s}$, $5\text{ s}$, $30\text{ s}$; on 3rd failure, sets `pin_locked_until = now() + 120s`, emits `PIN_LOCKED` event, and pages dispatcher | Legitimate user waits $120\text{ s}$ or uses dispatcher proxy | `I6` | Opening a new voice `call_sid` resets the per-call counter, but requires calling from a pre-registered `roster.phone_e164` number; repeated lockouts on a slot suspend the slot | `T-F7` (`pin_lockout_scope`) | `BOUNDED` |
| **I3** | Identity | Rival hospital or attacker intentionally enters wrong PINs to lock out a receiving facility's duty role | Lockout state (`pin_failed`, `pin_locked_until`) is stored on `session(id)` (scoped to a single enrolled `device_id` or single `call_sid`), not on `roster` or `facility` | Attacker only locks their own session/call; legitimate duty nurse on the ward tablet's enrolled device session is completely unaffected | Admin revokes compromised session if needed | `I6` | Isolated per authenticated session/call | `T-F7` (`pin_lockout_scope`) | `CLOSED` |
| **I4** | Identity | SIM swap or physical theft of a rostered duty phone | Repeated `PIN_LOCKED` events or anomalous off-shift activity on a `roster` slot | Automated alert to `ADMIN` + slot suspension (`valid_to = now()`) after repeated lockouts; PIN still required in addition to phone possession | Admin revokes `device` / updates `roster.phone_e164` | `I6` | Window of exposure between theft and detection if attacker also knows the PIN | `T-I4` | `BOUNDED` |
| **I5** | Identity | Outbound Exotel voice call is answered by voicemail or an automated PBX | Exotel AMD (`AnsweredBy`) check + mandatory human keypress gate (`"Press 1 to hear a referral"` within $8\text{ s}$) | `apply_command(ACK)` is **never** called on call pick-up; it executes only when DTMF `1` is received. Silence or machine verdict marks call `UNANSWERED` and advances to next slot | Escalates to `NOTICE_PROXY` at $3A/4$ | `I6` | A human bystander answering the duty phone can press `1` to hear the de-identified summary, but cannot `ACCEPT`/`COUNTER`/`DECLINE` without the PIN | `T-F7` | `CLOSED` |
| **I6** | Identity | BOLA (accessing another facility's referral) or mass-assignment of `hs_state` / `lease_epoch` in JSON body | Pydantic `extra='forbid'` on command schemas + object-level `facility_id` / `payload_grant` checks on every route | Extra JSON fields fail validation with `422 Unprocessable Entity`; unauthorized facility access fails with `403 Forbidden` | None required | `I6`, `I10` | Any future route added must include the `require_grant` dependency (enforced by CI route-matrix test) | `T-I6b` | `CLOSED` |
| **P1** | Privacy | Developer or client attempts to smuggle free-text PHI into `event.detail` | Pydantic `Literal` allowlist + PostgreSQL `CHECK (rhp_detail_ok(type, detail))` | Transaction aborts with `422` (API) or `CHECK` violation (DB); only allowlisted keys per `event.type` and `boolean`, $\le 12$-digit `int`, UUID, or uppercase token `^[A-Z0-9_]{1,40}$` values are permitted | Use encrypted `clinical_payload` or `event_secret` for clinical data | `I11` | A $40$-char uppercase string token could theoretically encode a short identifier if API enum validation were bypassed; blocked by closed Pydantic `Literal` enums + CI fuzzing | `T-F9` (`detail_check_fuzz`) | `BOUNDED` |
| **P2** | Privacy | Clinical text or patient name sent over DLT SMS | Static SMS template linter in CI and adapter code | SMS adapter formats only `"RHP alert: new referral. Open {#var#}"` where `{#var#}` is $\le 30\text{ chars}$ (referral short code/link); takes zero clinical fields as arguments | Recipient opens authenticated link or waits for voice call | — | Zero clinical fields passed to SMS adapter | `T-P2` | `CLOSED` |
| **P3** | Privacy | PHI leaked through Google FCM push notification payload | FCM adapter payload schema (`{"type":"WAKE","referral_id":"<uuid>"}`) | Sends zero-clinical-payload wake ping; Android app wakes and performs authenticated HTTPS fetch using device session | None required | `I10` | Third-party push provider sees only device token and wake timestamp | `T-P3` | `CLOSED` |
| **P4** | Privacy | Rejected, declined, or superseded facility keeps SSE stream open to read subsequent clinical updates | Per-frame `payload_grant` check in SSE emitter + `GRANT_REVOKED` control frame on revoke | Revoking a grant (`revoked_at = ts`) immediately causes the SSE hub to strip clinical fields for that subscriber and emit `event: GRANT_REVOKED`, which triggers a client DOM wipe | None required | `I10` | Data already rendered on screen or photographed by a user before `revoked_at` cannot be physically recalled | `T-F10` (`sse_revoke`) | `BOUNDED` |
| **P5** | Privacy | Crypto-shredded `clinical_payload` still recoverable from older PostgreSQL WAL segments or nightly backups | Monthly `kek_epoch` key hierarchy (`key_version.kek_epoch`) | At `clinical_payload.expires_at`, ciphertext rows are deleted and `key_version.wrapped_dek` is set to `NULL` (`status='SHREDDED'`); when all referrals in a `kek_epoch` expire, the master KEK for that epoch is destroyed, rendering WAL/backup copies permanently undecipherable | Admin verifies monthly KEK destruction log | — | Backups remain decryptable by the KEK until the cohort's `kek_epoch` is destroyed | `T-P5` | `BOUNDED` |
| **A1** | AI Safety | Clinician rubber-stamps an AI intake draft containing a hallucinated dosage or condition | Cognitive Forcing Function (CFF) + mandatory re-entry of critical fields + fast-approve speed bump | Server withholds draft until anchor fields are committed; shows zero confidence scores or explanations (`[V]`); requires manual re-entry of critical fields; logs verification dwell time | Clinician uses primary structured manual form (AI is optional behind `T3_EXTRAS`) | — | Internal 20-slip seeded-error usability gate targets $\le 5\%$ critical rubber-stamp rate and $\le 1\%$ silent omission rate (not $0\%$) | `T-A1` | `BOUNDED` |
| **A2** | AI Safety | Client attempts to fetch AI draft before clinician commits anchor values (`need_class`, `mgso4_status`) | Server endpoint guard on `/v1/referrals/{id}/ai-draft` | Server returns `423 Locked` (`ANCHOR_REQUIRED`) until anchor fields are persisted | Clinician selects anchors first | — | Enforced server-side before ciphertext is returned | `T-A2` | `CLOSED` |
| **A3** | AI Safety | Indic ASR misrecognizes rural Kannada dialect during voice dictation (WER $> 20\%$ `[V]`) | CFF quarantine + no direct-to-contract path from ASR | Dictation outputs only an unverified draft subject to `A1`/`A2` gates; never triggers a state transition or populates unverified fields | Clinician switches `T3_EXTRAS` AI off and taps structured checkboxes | — | High dialect WER (`>20%` `[V]`) is bounded by keeping ASR strictly off the critical path | `T-A3` | `BOUNDED` |
| **K1** | Clinical | Referring clinician does not know whether pre-referral $\text{MgSO}_4$ was given before patient arrived at PHC | Mandatory 3-state enum `mgso4_status` (`GIVEN | NONE_GIVEN | UNKNOWN`) | Selecting `UNKNOWN` is accepted without blocking `CREATE` or ambulance dispatch (`D1`, `I3`); receiving desk UI renders a persistent red banner: `"PRE-REFERRAL MgSO4 DOSE UNKNOWN — VERIFY BEFORE DOSING"` | Receiving clinician performs clinical assessment before administering loading/maintenance dose | `I3` | Prevents care delay while alerting receiver; relies on receiving clinician reading the prominent warning banner | `T-K1` | `BOUNDED` |
| **K2** | Clinical | Receiving hospital clicks `ACCEPT` to look responsive on district metrics, then leaves patient waiting on ambulance trolley without a bed (Goodhart gaming) | Separate tracking of `OFFER_ACCEPTED` vs. `TR_UPDATED(ARRIVED)` vs. `TR_UPDATED(HANDED_OVER)` (APOT-style metric) + `HANDOVER` deadline $H$ | If `ARRIVED` does not progress to `HANDED_OVER` within $H$, emits `HANDOVER_OVERDUE` and flags `"arrival-without-handover"`; if turned away at door, EMT/desk triggers `ARRIVAL_REJECTED` (revoking lease and logging broken commitment) | District officer reviews aggregated APOT handover gap and `ARRIVAL_REJECTED` counts | `I2` | Software cannot physically create hospital beds; it surfaces and records the bottleneck | `T-K2` | `BOUNDED` |
| **K3** | Clinical | Every PHC referral skips CHCs/FRUs and funnels straight to the tertiary Medical College | Administratively approved `catchment_chain` (`I7`) + sequential-by-default offers + per-facility open-offer load guard | Offers follow the tier-ordered `catchment_chain` sequentially by default; if a facility hits its configured open-offer cap, it auto-returns structured `AT_CAPACITY` decline and advances | Clinician can explicitly reorder/skip with a logged reason; dispatcher handles chain exhaustion | `I7` | Chain ordering and load caps depend on district administrative configuration | `T-K3` | `BOUNDED` |
| **K4** | Clinical | Lease changes (redirect) after the moving ambulance has already passed the highway turn-off to the new facility | Server computes detour ETA from cached Mapbox Matrix and emits redirect advisory to ambulance and dispatcher | System **never** auto-reroutes a moving ambulance; crew sees detour ETA advisory and either confirms `TR_DESTINATION_CHANGE(accepted=true)` or declines `TR_DESTINATION_CHANGE(accepted=false)` | If crew continues to original facility, Case `(c)` (`ARRIVAL_AT_NON_OWNER`) triggers on arrival and dispatcher coordinates | `I3` | Crew may be in a dead zone or unable to safely divert on a highway | `T-F5` (`arrival_cases`) | `BOUNDED` |
| **S1** | Insider | Malicious DBA or root user with `psql` superuser access bypasses triggers and edits or deletes an `event` row | Independent Python monitor (`fold()`) + pure-JS browser verifier + off-box witness checkpoints | Recomputed `SHA256(prev_hash || JCS(core))` fails to match stored `hash`, or `head_seq` falls below signed checkpoint `tree_size`; verifier outputs exact broken link: `BROKEN referral=<id> seq=<n> kind=PREV|HASH` or `TRUNCATED at seq=<k>` | Incident response + restore from verified backup using cold-key `RESTORE` protocol | `I5` | Hash chains and witnesses *detect* tampering within $\le 5\text{ s}$; they do not physically prevent root disk writes | `T-F8` (`tamper_vs_restore`) | `BOUNDED` |
| **S2** | Insider | Malicious operator attempts a split-view attack (showing one history to the district and another to a hospital) | C2SP-style signed checkpoints broadcast every $5\text{ s}$ to independent witnesses (big screen, judge phones via QR, off-box append-only log) | Witnesses compare Ed25519-signed `(checkpoint_id, tree_size, root_hash)` notes; any divergence for the same checkpoint ID proves equivocation | Audit against off-box witness log | `I5` | Requires at least $\ge 2$ independent honest witnesses holding checkpoints | `T-S2` | `BOUNDED` |
| **S3** | Insider | Compromise of the `rhp-sign` OS user's online Ed25519 checkpoint signing key | Key rotation drill + separation between online `rhp-sign` key and offline `COLD_PUB` key (which signs profiles and `RESTORE` checkpoints) | Revoke online `signer_key_id`, rotate key, verify history against pre-compromise off-box witness logs | Move signer key to HSM / cloud KMS before any pilot | `I5` | Attacker with both DB superuser and `rhp-sign` key could sign forged checkpoints until key rotation; no HSM in 24h hackathon build | `T-S3` | `OPEN` |
| **S4** | Insider | Dispatcher abuses `DISPATCHER_ASSIGN` override to favour or avoid specific hospitals | Mandatory structured `reason` enum + `proxy=true` flag + monitor counter for dispatcher overrides | Every override is immutably logged in `event` with `actor_roster_id` and surfaced in district audit views | District Nodal Officer reviews override frequency and reasons | `I6` | Legitimate-looking overrides with valid reason enums require human audit | `T-S4` | `BOUNDED` |
| **F1** | Infra | FastAPI container is killed (`SIGKILL`) mid-request | Docker healthcheck / supervisor + client timeout | Uncommitted PostgreSQL transaction aborts automatically (releasing row locks and removing `IN_FLIGHT` idempotency row); restarted container processes client's retry cleanly | None required | `I4` | In-flight requests experience latency equal to container restart + retry backoff ($\approx 2\text{–}5\text{ s}$) | `T-F1b` | `BOUNDED` |
| **F2** | Infra | PostgreSQL primary node suffers hardware/VM failure in pilot | Multi-AZ health monitor | Synchronous standby (`synchronous_commit=on`) is promoted with zero committed transaction loss; application connection pool reconnects | Operator verifies standby promotion | `I1`, `I4` | Write availability pause of $60\text{–}120\text{ s}$ during Multi-AZ promotion `[V*]` | `T-F2b` | `BOUNDED` |
| **F3** | Infra | Outbox relay process crashes after delivering notification but before marking `outbox.status='SENT'` | `outbox.visible_after` visibility timeout ($30\text{ s}$) | After $30\text{ s}$, unclaimed `PENDING` row becomes visible again (`attempts = attempts + 1`); downstream consumers deduplicate by `outbox.id` / `Last-Event-ID`; if `attempts > 8`, marks `DEAD` and pages dispatcher | Dispatcher handles `DEAD` channel via phone proxy | `I4` | At-least-once delivery after a relay crash can produce a duplicate push/SMS alert within $30\text{ s}$ | `T-F3b` | `BOUNDED` |
| **F4** | Infra | Aggressive OEM Android battery-saver (e.g., MIUI, ColorOS) kills background location service `[GAP]` | Device heartbeat monitor (`heartbeat` table `subject_kind='DEVICE'`) | When device heartbeat exceeds $30\text{ s}$, UI switches indicator to `"last confirmed Ns ago"`; PWA / app provides manual `"Update Location"` tap and dispatcher proxy fallback | Crew plugs phone into ambulance 12V charger and follows onboarding battery-whitelist checklist | `I3` | GPS trace has a gap for the duration the OS suspends the app | `T-F4b` | `BOUNDED` |
| **L1** | Legal | Regulatory uncertainty around automated voice calls carrying de-identified clinical referral prompts `[GAP]` | Pre-deployment legal review gate | Prototype uses Exotel trial sandbox with $\le 10$ pre-verified team phone numbers, `REAL_DATA=0`, and zero patient names spoken | Dispatcher human phone call remains primary in any jurisdiction where automated voice is restricted | — | Telecom/voice legality for clinical alerts is unsettled `[GAP]` | `T-L1` | `OPEN` |
| **L2** | Legal | Tension between DPDP Act s.8(7) erasure upon purpose completion and NMC 3-year record-keeping duties `[GAP]` | Configurable `clinical_payload.expires_at` and `kek_epoch` retention parameters | System separates short-lived encrypted handover payload (`clinical_payload`) from long-lived PHI-free audit metadata (`event`); retention durations are config parameters | Legal counsel sets retention parameters prior to any real-data pilot | — | Legal applicability of 3-year telemedicine retention to emergency handover records is unverified `[GAP]` | `T-L2` | `OPEN` |
| **L3** | Legal | Risk of overclaiming BSA 2023 Section 63 electronic-evidence certification | Automated forbidden-claim linter (`ST-5`) + export bundle generator | System generates a hash-bearing export bundle (RFC 8785 JCS events, SHA-256 manifest, pre-filled Part A custodian and Part B expert certificate templates) without claiming legal certification | Human custodian and examiner sign Part A / Part B certificates when producing evidence | `I5` | Legal admissibility requires human signature on Part A/B certificates per BSA s.63 `[V*]` | `T-L3` | `CLOSED` |
| **L4** | Legal | Delayed detection of a security breach against CERT-In ($6\text{ h}$) and DPBI ($72\text{ h}$) reporting clocks `[V*]` | Monitor alerts on `TAMPER`, anomalous `PIN_LOCKED` spikes, and `rejected_command` floods + incident runbook | Generates pre-formatted incident timeline from `event`, `rejected_command`, and `checkpoint` tables for rapid filing | Security officer submits report within $6\text{ h}$ (CERT-In) / $72\text{ h}$ (DPBI) | — | Reporting timeliness depends on human operator response after monitor alert fires | `T-L4` | `BOUNDED` |
| **D1** | Demo | iOS Safari lacks WebCrypto Ed25519 support `[V]` and disables `crypto.subtle` on LAN HTTP `[V]` | Browser capability check / unconditional bundling of pure-JS primitives | PWA bundles `@noble/curves/ed25519` and `@noble/hashes/sha256` directly, executing Merkle and hash-chain verification in pure JS on every browser | Labelled server-side verify endpoint available if an ancient browser fails JS execution | `I5` | Pure-JS verification adds $\approx 15\text{ KB}$ gzipped to PWA bundle and takes $\approx 5\text{–}20\text{ ms}$ per referral chain | `T-D1` | `BOUNDED` |
| **D2** | Demo | Exotel trial account restricts outbound calls to $\le 10$ whitelisted numbers `[V]` | Preflight script verifies whitelisted numbers and account balance | Voice IVR demo calls the team's pre-verified feature phone held by a judge; all other judges join via rotating QR PWA web desks (cap $20$) | Pre-recorded MP4 clip of feature-phone voice call if cellular carrier drops call inside venue | — | Judge personal phone numbers cannot receive live outbound IVR calls on a trial account | `T-D2` | `BOUNDED` |
| **D3** | Demo | `BROKEN_BUILD=1` accidentally enabled against the main database or with `REAL_DATA=1` | Startup guard in `api`, `poller`, `monitor`, and `witness` | Process immediately aborts with exit code `78` if `REAL_DATA=1`, if DSN database name $\neq \text{\texttt{rhp\_scratch\_broken}}$, or if the scratch DB role can connect to the main DB | Operator uses isolated scratch environment with flashing red banner | `I2` | Enforced by deterministic startup assertions and PostgreSQL role separation | `T-F20` (`broken_isolation`) | `CLOSED` |
| **D4** | Demo | Complete failure of both mobile hotspot and venue Wi-Fi during the 5-minute pitch | Preflight dual-uplink check + local loopback stack | Laptop runs entire Docker stack locally (`pg`, `api`, `poller`, `relay`, `monitor`, `witness`, `pwa`); fallback switches to local loopback + pre-recorded MP4 clips (Clips A–D) | Presenter discloses whenever a fallback clip is shown | — | Pre-recorded fallback clips are not live judge interaction and must be transparently labelled | `T-D4` | `BOUNDED` |
| **D5** | Demo | Last-minute "vibe-coded" change at hour 23 breaks a passing invariant gate | `CODEOWNERS` protection on `/spec`, `db/schema.sql`, and `/monitor` + hard code freeze at `H22` | CI blocks any PR modifying frozen spec/monitor files without human sign-off; after `H22`, only `.env` / profile config switches are permitted | Roll back to last good git tag `step-<ID>-loop<n>` | — | Process control enforced by git tags and CI branch rules | `T-D5` | `BOUNDED` |

---

## 2. The 28 Real-World Operational Scenarios & Conformance Vectors (`SC-01` to `SC-28`)

Every scenario from `ReferralHandshake_v8_LOCKED_Solution.md` §4.8 is mapped below to its exact RHP-1 command sequence, state transitions, database assertions, and conformance vector ID.

| Vector ID | Scenario Name | Initial State & Setup | Exact Command / Event Sequence | Expected `referral` & `offer` Post-State | HTTP Status & Invariants Verified |
|---|---|---|---|---|---|
| **`VEC-SC01`** | Receiver has no smartphone | `OFFERED` to Facility $F_1$ (`step=1`), `offer.status='OPEN'`, profile `DEMO_VOICE` | 1. At $t = A/4$, poller fires `TIMEOUT(NOTICE_VOICE)` $\rightarrow$ outbox enqueues `VOICE` to $F_1$ slot 1.<br>2. Exotel connects; receiver presses `1` $\rightarrow$ webhook calls `apply_command(ACK, channel='VOICE')`.<br>3. Receiver presses `1` (Accept) + 4-digit PIN + `#` $\rightarrow$ webhook auto-confirms required capabilities and calls `apply_command(ACCEPT, channel='VOICE')`.<br>*(Alt)* If unanswered by $3A/4$, `TIMEOUT(NOTICE_PROXY)` pages dispatcher, who submits `ACCEPT` with `channel='DISPATCHER_PROXY', proxy=true`. | `hs_state='ACCEPTED'`, `lease_facility_id=F_1`, `lease_epoch=1`, `offer.status='ACCEPTED'`, `event.channel IN ('VOICE','DISPATCHER_PROXY')` | `200 OK` · `I1`, `I2`, `I6` |
| **`VEC-SC02`** | Receiver cannot take patient, suggests redirect | `OFFERED` or `ACKNOWLEDGED` at $F_1$, chain $[F_1, F_2]$ | 1. $F_1$ submits `DECLINE(reason='NO_NICU', suggested_facility_id=F_3)` with valid PIN.<br>2. System marks $F_1$ offer `DECLINED`, revokes $F_1$'s `payload_grant`, logs suggestion in `event.detail` (advisory only—never auto-followed), and calls `advance()` to open offer to $F_2$ (`chain[1]`). | `hs_state='OFFERED'`, `ladder_cursor=2`, $F_1$ `offer.status='DECLINED'`, $F_2$ `offer.status='OPEN'`, $F_1$ `payload_grant.revoked_at IS NOT NULL` | `200 OK` · `I1`, `I7`, `I9`, `I10` |
| **`VEC-SC03`** | Receiver can take patient only partly (Counter-offer) | `ACKNOWLEDGED` at $F_1$, `counter_round=0` | 1. $F_1$ submits `COUNTER(counter_mask=2)` (e.g., `"ANAESTHETIST_IN_20_MIN"`) with PIN.<br>2. Offer becomes `COUNTERED`, `counter_round=1`, `DECISION` deadline replaced by `COUNTER_CONFIRM` due at $\min(C, \text{remaining } D)$.<br>3. Referrer submits `CONFIRM_COUNTER(confirmed=true)` (re-checking `I15` resource confirmations). | `hs_state='ACCEPTED'`, `lease_facility_id=F_1`, `lease_epoch=1`, `offer.status='ACCEPTED'`, `offer.counter_round=1` | `200 OK` · `I1`, `I2`, `I15` |
| **`VEC-SC04`** | Duty nurse is busy (Intra-facility notice ladder) | `OFFERED` to $F_1$ with $S=3$ rostered slots (`NURSE`, `CMO`, `CONSULTANT`) | 1. At $t=0$, SSE + FCM sent to all 3 slots.<br>2. No ACK by $t=A/4$: `NOTICE_VOICE` calls Slot 1 (`NURSE`) at $A/4$, Slot 2 (`CMO`) at $A/4 + \delta$, Slot 3 (`CONSULTANT`) at $A/4 + 2\delta$.<br>3. Slot 2 (`CMO`) answers and presses `1` $\rightarrow$ `ACK` committed; remaining voice rungs for $F_1$ cancelled. | `hs_state='ACKNOWLEDGED'`, `offer.status='ACKED'`, `offer.acked_by = <CMO_roster_id>`, `DECISION` deadline active at $t_{\text{ack}} + D$ | `200 OK` · `I1`, `I6`, `I13` |
| **`VEC-SC05`** | Two facilities accept at once (`PARALLEL2` mode) | `OFFERED` in `PARALLEL2` mode; $F_1$ (`step=1`) and $F_2$ (`step=2`) both `OPEN`; `open_offers=2` | 1. Both $F_1$ and $F_2$ confirm resources.<br>2. $F_1$ and $F_2$ send `ACCEPT` simultaneously.<br>3. $F_1$ acquires `referral` lock first: $F_1$ becomes `ACCEPTED` (`lease_epoch=1`), $F_2$ becomes `SUPERSEDED` (`payload_grant` revoked).<br>4. $F_2$'s transaction acquires lock second, sees `hs_state='ACCEPTED'`, rolls back to `SAVEPOINT sp_cmd`, logs `rejected_command`, returns `409 LEASE_HELD`. | `hs_state='ACCEPTED'`, `lease_facility_id=F_1`, `lease_epoch=1`, `open_offers=0`, $F_1$ `ACCEPTED`, $F_2$ `SUPERSEDED` | Winner: `200 OK`<br>Loser: `409 Conflict (LEASE_HELD)` · `I2`, `I10`, `I12` |
| **`VEC-SC06`** | Late accept after escalation (`SOFT_OPEN` window) | `SEQUENTIAL` mode; $F_1$ timed out on `ACK`, so $F_1$ is `SOFT_OPEN` and $F_2$ is `OPEN` (`open_offers=2`) | **Subcase 6a ($F_1$ wins before $F_2$ ACKs):** $F_1$ confirms resources and submits `ACCEPT` while $F_2$ is still `OPEN`. $F_1$ gets `ACCEPTED`, $F_2$ becomes `SUPERSEDED`.<br>**Subcase 6b ($F_2$ ACKs first):** $F_2$ submits `ACK` $\rightarrow$ $F_1$ transitions from `SOFT_OPEN` to `TIMED_OUT`. $F_1$ then submits `ACCEPT` $\rightarrow$ rejected with `409 LATE_ACCEPT_REJECTED`. | **6a:** `lease_facility_id=F_1`, $F_2$ `SUPERSEDED`.<br>**6b:** `hs_state='ACKNOWLEDGED'` at $F_2$, $F_1$ `TIMED_OUT`, `rejected_command` logged for $F_1$. | **6a:** `200 OK`<br>**6b:** `409 Conflict (LATE_ACCEPT_REJECTED)` · `I2`, `I12` |
| **`VEC-SC07`** | Receiver accepts, then rejects patient on arrival | `hs_state='ACCEPTED'` at $F_1$ (`lease_epoch=1`), `tr_state='ARRIVED'`, chain $[F_1, F_2]$ | 1. EMT or $F_1$ desk submits `ARRIVAL_REJECTED(reason='OT_UNAVAILABLE_EMERGENCY')`.<br>2. $F_1$ offer becomes `ARRIVAL_REJECTED`, `lease_epoch` increments to $2$, lease cleared (`lease_offer_id=NULL`), $F_1$ `payload_grant` revoked, `advance()` opens offer to $F_2$ (`step=2`). | `hs_state='OFFERED'`, `lease_offer_id=NULL`, `lease_epoch=2`, $F_1$ `ARRIVAL_REJECTED`, $F_2$ `OPEN`, `tr_state='ARRIVED'` | `200 OK` · `I1`, `I2`, `I9`, `I10` |
| **`VEC-SC08`** | All approved facilities in chain fail | `OFFERED` at last facility $F_3$ (`step=3`), chain $[F_1, F_2, F_3]$ | 1. $F_3$ submits `DECLINE(reason='AT_CAPACITY')` (or its `DECISION` deadline expires in `PARALLEL2` / after soft-open eviction).<br>2. `advance()` finds no remaining unused targets in `referral.chain` and `open_offers == 0`.<br>3. Referral transitions to `ESCALATED_TO_DISPATCHER` with a `DISPATCH_ACTION` deadline. | `hs_state='ESCALATED_TO_DISPATCHER'`, `open_offers=0`, `deadline(kind='DISPATCH_ACTION', status='PENDING')` exists | `200 OK` · `I1`, `I7`, `I12` |
| **`VEC-SC09`** | Ambulance in cellular dead zone | `hs_state='ACCEPTED'`, `tr_state='EN_ROUTE'` | 1. Ambulance phone loses connectivity for $10\text{ min}$; queues $20$ `telemetry(kind='GPS')` and $2$ `telemetry(kind='OBS')` items locally with UUIDv7 `event_id`s.<br>2. Command centre displays `"last confirmed 600s ago"`.<br>3. Reconnect flushes batch (and retries batch twice); server inserts via `ON CONFLICT (event_id) DO NOTHING`. | Exactly $22$ `telemetry` rows stored with original `client_ts_ms` and authoritative `server_ts`; zero duplicates | `200 OK` · `I3`, `I4` |
| **`VEC-SC10`** | Server or internet down at origin PHC | Origin clinician has no internet; patient needs immediate transfer | 1. Clinician initiates transfer by phone/paper slip carrying pre-printed or locally generated Crockford Base32 paper code; ambulance departs immediately.<br>2. When connectivity returns (or at receiving desk via paper code), outbox flushes `CREATE` and `TR_UPDATE` commands with `Idempotency-Key`. | Referral created and linked via `paper_code`; transport and handshake states reconcile without blocking patient care | `200 OK` · `I3`, `I4` |
| **`VEC-SC11`** | Wrong person attempts to accept | `OFFERED` to $F_1$ | 1. User authenticated as `EMT` (or a `NURSE` rostered at $F_2$, or with an invalid PIN) calls `POST /v1/offers/{id}/accept`.<br>2. Step 3 (PIN) or Step 5 (authority) rejects the command, rolls back to `SAVEPOINT sp_cmd`, and logs `rejected_command`. | `referral` and `offer` unchanged; `rejected_command` row persisted; `session.pin_failed` incremented if PIN failed | `403 Forbidden` · `I6` |
| **`VEC-SC12`** | Crew cannot use app (Proxy entry) | `hs_state='OFFERED'`, `tr_state='REQUESTED'` | 1. Crew calls dispatcher by radio/phone.<br>2. Dispatcher submits `TR_UPDATE(tr_state='DISPATCHED', channel='DISPATCHER_PROXY', proxy=true, proxy_for=<emt_roster_id>)` and later `TR_UPDATE(tr_state='EN_ROUTE')`. | `tr_state='EN_ROUTE'`, `event.proxy=true`, `event.proxy_for=<emt_roster_id>`, `hs_state` unaffected | `200 OK` · `I3`, `I6` |
| **`VEC-SC13`** | Paper slip arrives without digital record (or desk looks up by paper code) | Ambulance arrives with paper slip bearing code `8F3K9M2P-Z` | 1. Receiving desk enters `8F3K9M2P-Z` into PWA.<br>2. Client & server validate `mod 37` check symbol (`Z`).<br>3. Server resolves existing referral by `referral.paper_code` (or creates a paper-first record if origin was completely offline) and displays status. | Referral linked; any corrupted single-char mistype (e.g., `8F3K9M2Q-Z`) rejected with `422 INVALID_PAPER_CODE_CHECKSUM` before DB query | `200 OK` (or `422` on typo) · `I4`, `I5` |
| **`VEC-SC14`** | iPhone Safari with restricted background execution | Clinician or desk user on iOS Safari | 1. User opens desk or ambulance PWA on iPhone; background tab is suspended by iOS.<br>2. On foregrounding (`visibilitychange` event), PWA flushes queued outbox commands and reconnects SSE with `Last-Event-ID`; pure-JS `@noble/curves/ed25519` verifies latest checkpoint. | Outbox flushed idempotently; missed SSE frames replayed; checkpoint verified without WebCrypto `Ed25519` | `200 OK` · `I4`, `I5` |
| **`VEC-SC15`** | AI intake draft contains seeded error | Clinician uploads synthetic referral slip photo (`T3_EXTRAS=1`) | 1. `GET /ai-draft` before anchors returns `423 ANCHOR_REQUIRED`.<br>2. Clinician commits `need_class='OBSTETRIC_EMERGENCY'` and `mgso4_status='GIVEN'`.<br>3. Draft loads with a seeded error; clinician must manually re-enter critical fields and pass speed-bump check before `CREATE`.<br>4. Turning `T3_EXTRAS=0` disables `/ai-draft` while manual `CREATE` works identically. | `CREATE` commits only clinician-verified structured fields; system operates identically with AI disabled | `423 Locked` $\rightarrow$ `200 OK` · `I3` |
| **`VEC-SC16`** | Patient delivers or stabilises before departure | `hs_state='OFFERED'` (or `ACCEPTED`), `tr_state='REQUESTED'` | 1. Referring clinician submits `CANCEL(outcome='DELIVERED_EN_ROUTE' | 'TRANSPORT_CANCELLED', reason='STABILISED_AT_ORIGIN')`.<br>2. All open/accepted offers transition to `WITHDRAWN`, active `payload_grant` rows are revoked, pending deadlines become `CANCELLED`, `tr_state` becomes `TR_CANCELLED`. | `hs_state='CANCELLED'`, `tr_state='TR_CANCELLED'`, `open_offers=0`, `lease_offer_id=NULL`, `closed_at IS NOT NULL`, `outcome IS NOT NULL` | `200 OK` · `I1`, `I5`, `I10` |
| **`VEC-SC17`** | Patient or family refuses transfer | `hs_state='ACCEPTED'`, `tr_state='DISPATCHED'` | 1. Referring clinician submits `CANCEL(outcome='PATIENT_REFUSED', reason='AMA_SIGNED')`.<br>2. Lease offer becomes `WITHDRAWN`, `payload_grant` revoked, deadlines cancelled, receiving desk notified via SSE `GRANT_REVOKED`. | `hs_state='CANCELLED'`, `outcome='PATIENT_REFUSED'`, `closed_at IS NOT NULL`, `open_offers=0` | `200 OK` · `I1`, `I5`, `I10` |
| **`VEC-SC18`** | Ambulance breaks down en route | `hs_state='ACCEPTED'` at $F_1$, `tr_state='EN_ROUTE'` | 1. Dispatcher reassigns replacement vehicle and logs `TR_UPDATE(tr_state='EN_ROUTE', detail={'source':'REASSIGNED'})`.<br>2. Handshake state (`hs_state='ACCEPTED'`, `lease_facility_id=F_1`, `lease_epoch=1`) remains untouched. | `hs_state='ACCEPTED'`, `lease_epoch=1` unchanged; new `TR_UPDATED` event appended to log | `200 OK` · `I2`, `I3` |
| **`VEC-SC19`** | Receiver roster stale (duty phone number unreachable) | `OFFERED` to $F_1$; Slot 1 phone fails carrier delivery | 1. At $t=A/4$, Exotel call to Slot 1 returns `failed`/`busy` webhook.<br>2. Adapter logs `NOTICE_SENT` failure and immediately triggers Slot 2 (`CMO`) call without waiting for full call budget $V$; if all slots fail, `NOTICE_PROXY` at $3A/4$ pages dispatcher. | Escalation proceeds within window $A$; no silent stall | `200 OK` · `I1`, `I13` |
| **`VEC-SC20`** | Counter-offer loop between receiver and referrer | `ACKNOWLEDGED` at $F_1$, `counter_round=2` (after two counter rounds) | 1. $F_1$ attempts a 3rd `COUNTER` command.<br>2. Step 6 transition guard (`offer.counter_round < 2`) and DB `CHECK (counter_round BETWEEN 0 AND 2)` reject the command with `409 MAX_COUNTER_ROUNDS_EXCEEDED`.<br>3. $F_1$ must `ACCEPT`, `DECLINE`, or let `DECISION` expire to escalate. | `offer.counter_round` remains $2$; `rejected_command` logged; facility window bounded by $D$ | `409 Conflict` · `I1`, `I13` |
| **`VEC-SC21`** | Duplicate referral created for the same patient | Clinician or desk creates a second referral while first is active | 1. Entering an already-used `paper_code` returns `409 DUPLICATE_PAPER_CODE` with the existing `referral_id` so the UI prompts to link/open the existing referral.<br>2. System never silently auto-merges two distinct `referral_id` streams. | Existing referral preserved; zero unapproved state merges | `409 Conflict` · `I4`, `I5` |
| **`VEC-SC22`** | Client device clock is wrong by $+3\text{ hours}$ or $-2\text{ days}$ | Android phone with misconfigured local clock submits `CREATE` or `ACCEPT` | 1. Client sends `client_ts_ms` skewed by hours.<br>2. Server records `client_ts_ms` in `event`, computes `server_ts = GREATEST(clock_timestamp(), referral.head_ts)`, and sets all `deadline.due_at` and `offer_resource_confirmation.expires_at` strictly from `server_ts`. | Deadlines and confirmations unaffected by client skew; `I16` holds | `200 OK` · `I1`, `I15`, `I16` |
| **`VEC-SC23`** | SIM theft / PIN brute-force attack on voice or web | Attacker submits 3 wrong PINs on session $S_a$ | 1. Calls 1, 2, 3 with bad PIN commit `pin_failed = 1, 2, 3` via autonomous connection and return `403 PIN_INVALID`.<br>2. On 3rd failure, `pin_locked_until = now() + 120s`, `PIN_LOCKED` event appended, dispatcher paged.<br>3. Call 4 within $120\text{ s}$ on $S_a$ returns `429 PIN_LOCKED`.<br>4. Legitimate user on session $S_b$ submits valid PIN $\rightarrow$ `200 OK`. | $S_a$ locked for $120\text{ s}$; $S_b$ succeeds (`I2`, `I6`) | `403` $\rightarrow$ `429` on $S_a$; `200 OK` on $S_b$ · `I6` |
| **`VEC-SC24`** | Admin / Dispatcher override assignment | `hs_state='ESCALATED_TO_DISPATCHER'` (or live referral requiring emergency override) | 1. Dispatcher submits `DISPATCHER_ASSIGN(facility_id=F_4, reason='DIRECT_CMO_PHONE_CONFIRMATION')` with dispatcher PIN.<br>2. Creates offer for $F_4$ with `source='DISPATCHER'`, `status='ACCEPTED'`, increments `lease_epoch`, sets `event.proxy=true`, arms `HANDOVER` deadline. | `hs_state='ACCEPTED'`, `lease_facility_id=F_4`, `offer.source='DISPATCHER'`, `event.proxy=true`, `I7` satisfied (`source='DISPATCHER'` exempt from `chain` membership) | `200 OK` · `I1`, `I2`, `I6`, `I7` |
| **`VEC-SC25`** | Receiver accepts but has no bed (Handover delay) | `hs_state='ACCEPTED'`, `tr_state='ARRIVED'`, `HANDOVER` deadline $H$ active | 1. Patient arrives (`ARRIVED`), but receiver delays `HANDED_OVER` past $H$.<br>2. Poller fires `TIMEOUT(HANDOVER)` $\rightarrow$ emits `HANDOVER_OVERDUE`, flags referral on command centre, and re-arms `HANDOVER` deadline. | `event(type='HANDOVER_OVERDUE')` appended; new `PENDING` `HANDOVER` deadline armed (`I1`); APOT metric records delay | `200 OK` · `I1`, `I2` |
| **`VEC-SC26`** | Tertiary facility overload (`AT_CAPACITY`) | Tertiary facility $F_3$ has reached its configured open-offer cap | 1. Escalation or `CREATE` reaches $F_3$ (or $F_3$ desk clicks `AT_CAPACITY`).<br>2. $F_3$ offer is recorded and immediately declined with `decline_reason='AT_CAPACITY'`, advancing to the next target or `ESCALATED_TO_DISPATCHER`. | $F_3$ `offer.status='DECLINED'`, `decline_reason='AT_CAPACITY'`, referral advances without waiting $A+D$ at $F_3$ | `200 OK` · `I1`, `I9`, `I12` |
| **`VEC-SC27`** | Network retry storm from flaky connection | Client fires $50$ concurrent retries with the same `(actor_id, Idempotency-Key)` and payload | 1. First request acquires `pg_try_advisory_xact_lock`, executes `apply_command()`, commits `event` (`seq=k`), marks `idempotency.status='DONE'`.<br>2. Requests arriving while #1 is in flight fail `pg_try_advisory_xact_lock` and receive `409 DUPLICATE_IN_FLIGHT`.<br>3. Requests arriving after #1 commits read `idempotency.status='DONE'` and receive the exact cached `200 OK` response. | Exactly $1$ `event` row (`seq=k`) written; zero gaps in `seq` | $1 \times \text{\texttt{200 OK}}$ (exec) + $m \times \text{\texttt{409}}$ (in-flight) + $k \times \text{\texttt{200 OK}}$ (replay) · `I4` |
| **`VEC-SC28`** | Referral never closed by receiving facility | `hs_state='ACCEPTED'`, `tr_state='HANDED_OVER'`; `CLOSURE` deadline armed at $t_{\text{handover}} + C_{\text{close}}$ | 1. At 1st `CLOSURE` expiry, poller fires `TIMEOUT(CLOSURE)` $\rightarrow$ emits `CLOSURE_OVERDUE`, alerts dispatcher/district view, and re-arms a 2nd `CLOSURE` deadline.<br>2. At 2nd `CLOSURE` expiry, poller fires `TIMEOUT(CLOSURE)` $\rightarrow$ system issues `CLOSE(outcome='UNKNOWN_COUNTER_REFERRAL', proxy=true, channel='SYSTEM')`. | `hs_state='CLOSED'`, `outcome='UNKNOWN_COUNTER_REFERRAL'`, `closed_at IS NOT NULL`, zero pending deadlines, `payload_grant` revoked | `200 OK` · `I1`, `I5`, `I10` |

---

## 3. Control-Plane State Machine, Offer Cap & Track-Interaction Edge Cases

### 3.1 Soft-Open, `PARALLEL2`, and `COUNTER` Cap Arithmetic (`F13`, `I2`, `I12`)

Invariant `I12` mandates that the number of offers in `OPEN_SET = {'OPEN', 'ACKED', 'COUNTERED', 'SOFT_OPEN'}` for any referral satisfies:
$$0 \le \text{\texttt{open\_offers}} \le 2$$

```
SEQUENTIAL STEADY STATE (open_offers = 1):
  [Offer k: OPEN]

SEQUENTIAL FIRST TIMEOUT -> OVERLAP STATE (open_offers = 2):
  [Offer k: SOFT_OPEN]  +  [Offer k+1: OPEN]

SEQUENTIAL SECOND TIMEOUT -> EVICTION RULE (open_offers = 2, NOT 3):
  [Offer k: TIMED_OUT]  +  [Offer k+1: SOFT_OPEN]  +  [Offer k+2: OPEN]

SEQUENTIAL SUCCESSOR ACK -> LATE-ACCEPT WINDOW CLOSES (open_offers = 1):
  [Offer k: TIMED_OUT]  +  [Offer k+1: ACKED]
```

Exact transition edge rules enforced inside `apply_command()` under the `referral` row lock:
1. **Soft-Open Eviction on Next Hop (`SEQUENTIAL`):** When offer $k$ times out (`ACK` or `DECISION` expiry) and `advance()` opens offer $k+1$, if offer $k-1$ is still in `SOFT_OPEN`, offer $k-1$ is atomically transitioned to `TIMED_OUT` (and its `payload_grant` is revoked) in the **same transaction** before offer $k$ becomes `SOFT_OPEN` and offer $k+1$ becomes `OPEN`. Thus `open_offers` transitions $2 \rightarrow 2$ and never reaches $3$.
2. **Soft-Open Termination on Chain Exhaustion:** If offer $k$ is the last facility in `referral.chain` (no $k+1$ exists) and offer $k$ times out, offer $k$ does **not** enter `SOFT_OPEN`; it transitions directly to `TIMED_OUT` ( along with any $k-1$ in `SOFT_OPEN`), `open_offers` becomes $0$, and `referral.hs_state` transitions to `ESCALATED_TO_DISPATCHER`.
3. **Late-Accept Deterministic Resolution:**
   - While offer $k$ is `SOFT_OPEN` and offer $k+1$ is `OPEN` (not yet `ACKED`), if $k$ submits a valid `ACCEPT` (with unexpired `offer_resource_confirmation` rows per `I15`), $k$ transitions to `ACCEPTED`, `lease_epoch` increments, and $k+1$ transitions to `SUPERSEDED` (with `GRANT_REVOKED` emitted to $k+1$).
   - The instant $k+1$ commits `ACK` (or `ACCEPT` or `COUNTER`), $k$ is atomically transitioned from `SOFT_OPEN` to `TIMED_OUT` and $k$'s `payload_grant` is revoked. Any subsequent `ACCEPT` from $k$ sees `offer.status == 'TIMED_OUT'` and returns `409 Conflict` with `reason_code = 'LATE_ACCEPT_REJECTED'`.
4. **`PARALLEL2` Timeout Rule:** In `PARALLEL2` mode, two offers ($F_1, F_2$) start `OPEN` (`open_offers = 2`). Because `open_offers` is already at the cap of $2$, a timed-out offer in `PARALLEL2` mode **never** enters `SOFT_OPEN`; it transitions directly to `TIMED_OUT`, freeing one slot so `advance()` can open $F_3$ (`open_offers` stays $\le 2$).
5. **`COUNTER` Co-Existence & Deadline Clamping:**
   - When offer $k$ submits `COUNTER`, `offer.status` becomes `COUNTERED` (which remains in `OPEN_SET`). It does **not** supersede a second open offer (whether $k-1$ is `SOFT_OPEN` in `SEQUENTIAL` mode or another facility is `OPEN`/`ACKED` in `PARALLEL2` mode).
   - Whichever of $\{\text{other offer's \texttt{ACCEPT}}, \text{referrer's \texttt{CONFIRM\_COUNTER(true)} for } k\}$ acquires the `referral` lock first wins the lease (`lease_epoch + 1`) and marks the other offer `SUPERSEDED`.
   - `COUNTER` replaces the offer's `DECISION` deadline with a `COUNTER_CONFIRM` deadline whose `due_at` is strictly clamped to:
     $$\text{\texttt{due\_at}} = \text{\texttt{ts}} + \min\left(C,\ \max\left(0,\ \text{\texttt{decision\_due\_at}} - \text{\texttt{ts}}\right)\right)$$
     This guarantees that up to $2$ counter-offer rounds can never extend a facility's total decision window beyond $D$ (`F3`, `I13`).

### 3.2 Six Arrival Ambiguity Edge Cases (`F5`, `I3`)

Geofence evaluation ($200\text{ m}$ radius $+$ $60\text{ s}$ dwell at speed $< 2\text{ m/s}$) is strictly a hint that emits `ARRIVAL_SUGGESTED`. Only a human actor (`EMT`, receiving desk role, or `DISPATCHER` proxy) can transition `referral.tr_state` to `ARRIVED`.

| Case | Handshake State at Arrival | Facility Where Ambulance Arrives | Exact System Behaviour & State Transitions |
|---|---|---|---|
| **Case (a)** | `hs_state = 'ACCEPTED'`, `lease_facility_id = F_1` | Lease holder $F_1$ | 1. Geofence emits `ARRIVAL_SUGGESTED(facility=F_1)`.<br>2. EMT or $F_1$ desk submits `TR_UPDATE(tr_state='ARRIVED', facility_id=F_1)` $\rightarrow$ `tr_state='ARRIVED'`, `tr_facility_id=F_1`.<br>3. `HANDOVER` deadline $H$ is already active (or re-anchored to $t_{\text{arrived}} + H$ if configured). |
| **Case (b)** | `hs_state IN ('OFFERED','ACKNOWLEDGED')` | Facility $F_k$ holding an `OPEN`, `ACKED`, or `SOFT_OPEN` offer | 1. `TR_UPDATE(tr_state='ARRIVED', facility_id=F_k)` succeeds immediately (`I3`).<br>2. $F_k$'s desk UI highlights physical arrival; $F_k$ may immediately submit `RESOURCE_CONFIRM` + `ACCEPT` (subject to `I15` TTL check and `I2` single-lease check) followed by `TR_UPDATE(tr_state='HANDED_OVER')`. |
| **Case (c)** | Any non-terminal `hs_state` | Facility $F_x$ with **no** open or accepted offer (or a `DECLINED`/`TIMED_OUT` offer) | 1. `TR_UPDATE(tr_state='ARRIVED', facility_id=F_x)` **still succeeds** (`I3`: never block care).<br>2. Server emits `ARRIVAL_AT_NON_OWNER(facility=F_x)` urgent alert and pages the dispatcher (`OUTBOX` channel `PROXY_PAGE`).<br>3. If $F_x$ clinically stabilizes/admits the patient, the dispatcher executes `DISPATCHER_ASSIGN(facility_id=F_x, reason='UNANNOUNCED_ARRIVAL_ACCEPTED')` (`source='DISPATCHER'`) to transfer the lease (`lease_epoch + 1`) and supersede any other open offers. |
| **Case (d)** | Any non-terminal `hs_state`; `tr_state` before `ARRIVED` | En-route destination change | 1. EMT or dispatcher submits `TR_DESTINATION_CHANGE(facility_id=F_new, reason='CLINICAL_DIVERSION'|'LEASE_REDIRECT', accepted=true)`.<br>2. Updates `referral.tr_facility_id = F_new` and appends `TR_DESTINATION_CHANGE` event.<br>3. The server **never** mutates `tr_facility_id` automatically when `lease_facility_id` changes; it only pushes a redirect advisory. |
| **Case (e)** | Lease moves to $F_2$, while `tr_facility_id = F_1` | Crew refuses redirect advisory | 1. Crew taps `"Continue to current destination"` $\rightarrow$ submits `TR_DESTINATION_CHANGE(facility_id=F_1, reason='CREW_DECLINED_REDIRECT', accepted=false)`.<br>2. `lease_facility_id` remains $F_2$; `tr_facility_id` remains $F_1$; dispatcher is paged immediately to coordinate with $F_1$ and $F_2$. |
| **Case (f)** | Lease moves to $F_2$ after ambulance passed highway turn-off | En-route past turn-off | 1. Server queries cached Mapbox Matrix for current ambulance `(lat_e5, lon_e5)` $\rightarrow F_2$ and displays detour ETA on the redirect advisory.<br>2. Crew decides whether to divert (Case `(d)`) or continue to $F_1$ (Case `(e)` $\rightarrow$ Case `(c)` upon arrival at $F_1$). |

### 3.3 Reachability, Empty Catchment Chain & Two-Stage Closure (`F6`, `I1`, `I5`)

1. **Empty Catchment Chain at `CREATE`:** If `catchment_chain` has $0$ active targets for `(origin_facility_id, need_class)` (or the clinician's approved `chain` array is empty `{}`), `CREATE` atomically transitions `referral.hs_state` directly from `CREATED` to `ESCALATED_TO_DISPATCHER` inside the `CREATE` transaction and inserts a `PENDING` `deadline(kind='DISPATCH_ACTION')`. `referral.hs_state = 'CREATED'` is never committed as a resting state without a pending deadline (`I1`).
2. **Outcome Taxonomy Guards:**
   - The $9$ legal outcomes are: `ADMITTED_STABLE`, `ADMITTED_CRITICAL`, `DELIVERED_AT_RECEIVER`, `DELIVERED_EN_ROUTE`, `PATIENT_REFUSED`, `TRANSPORT_CANCELLED`, `DETERIORATED_OR_DIED_PRE_HANDOVER`, `REDIRECTED_ON_ARRIVAL`, `UNKNOWN_COUNTER_REFERRAL`.
   - `CLOSE` with `outcome IN ('ADMITTED_STABLE', 'ADMITTED_CRITICAL', 'DELIVERED_AT_RECEIVER')` is rejected with `409 Conflict (HANDOVER_REQUIRED_FOR_OUTCOME)` unless `referral.tr_state == 'HANDED_OVER'`.
3. **Two-Stage Unclosed Referral Resolution:**
   - When `TR_UPDATE(tr_state='HANDED_OVER')` commits, the server creates `deadline(kind='CLOSURE', step=1, due_at = ts + CLOSURE_TTL)`.
   - **Stage 1 Expiry:** If the receiver has not called `CLOSE` by `step=1` expiry, the poller's `TIMEOUT` command appends `event(type='CLOSURE_OVERDUE', detail={'kind':'CLOSURE','step':1})`, pages the receiving desk and dispatcher, and inserts `deadline(kind='CLOSURE', step=2, due_at = ts + CLOSURE_TTL)`.
   - **Stage 2 Expiry:** If still unclosed at `step=2` expiry, the poller's `TIMEOUT` command transitions `referral.hs_state = 'CLOSED'`, `outcome = 'UNKNOWN_COUNTER_REFERRAL'`, `closed_at = ts`, `channel = 'SYSTEM'`, `proxy = true`, revokes all active `payload_grant` rows, and schedules `clinical_payload` expiry. The system never fabricates a clinical outcome.

---

## 4. Command Pipeline, Idempotency & Worker Lock-Order Edge Cases

### 4.1 Complete Idempotency Edge-Case Matrix (`F14`, `I4`)

Every mutating HTTP endpoint (`POST /v1/referrals`, `POST /v1/offers/{id}/ack`, `accept`, `counter`, `decline`, `confirm-counter`, `arrival-rejected`, `dispatcher-assign`, `tr-update`, `cancel`, `close`, `revoke-grant`) requires the `Idempotency-Key` header ($8\text{–}80$ ASCII chars).

```python
# Exact canonical request hash computed in Step 1 BEFORE acquiring any referral lock:
def compute_request_hash(cmd_type: str, path_params: dict, body_dict: dict) -> bytes:
    canonical_envelope = {
        "cmd": cmd_type,
        "params": path_params,
        "body": body_dict,  # Pydantic model_dump(mode="json"), floats prohibited
    }
    return hashlib.sha256(jcs_serialize(canonical_envelope)).digest()
```

| Case # | Condition at Step 1 (`apply_command`) | Advisory Lock `pg_try_advisory_xact_lock` | `idempotency` Row State | `event.event_id` State | Exact Server Action & HTTP Response |
|---|---|---|---|---|---|
| **IDEM-1** | First time `(actor_id, key)` is seen | Acquired (`true`) | Absent | Absent | Inserts `idempotency(status='IN_FLIGHT')`, executes Steps 2–9, updates `idempotency(status='DONE', http_status=200, response=...)`, commits, returns `200 OK`. |
| **IDEM-2** | Retry of `(actor_id, key)` with **identical** `request_hash` after prior `200 OK` | Acquired (`true`) | `status = 'DONE'`, `http_status = 200` | Present | Returns stored `200 OK` and cached `response` JSON immediately in Step 1 **without** locking `referral` or writing to `event`. |
| **IDEM-3** | Retry of `(actor_id, key)` with **identical** `request_hash` after prior deterministic domain rejection (`403`, `409`, `412`, `422`, `429`) | Acquired (`true`) | `status = 'DONE'`, `http_status IN (403,409,412,422,429)` | Absent (rolled back to `SAVEPOINT sp_cmd`, logged in `rejected_command`) | Returns the exact stored error `http_status` and cached `response` JSON immediately in Step 1. |
| **IDEM-4** | Reuse of `(actor_id, key)` with **different** `request_hash` (`row.request_hash != h`) | Acquired (`true`) | Any (`IN_FLIGHT` or `DONE`) | Any | Rejects immediately in Step 1 with `422 Unprocessable Entity` (`reason_code = 'KEY_REUSED_DIFFERENT_PAYLOAD'`). |
| **IDEM-5** | Concurrent duplicate request arrives while original `(actor_id, key)` transaction is still executing | Fails (`false`) | `status = 'IN_FLIGHT'` (uncommitted in first txn) | Uncommitted | Rejects immediately in Step 1 with `409 Conflict` (`reason_code = 'DUPLICATE_IN_FLIGHT'`). Client backs off and retries, hitting **IDEM-2** or **IDEM-3**. |
| **IDEM-6** | Server process or DB crashes mid-transaction before `COMMIT` | Released by PG on txn abort | Absent (rolled back with aborted txn) | Absent (rolled back with aborted txn) | Next client retry with `(actor_id, key)` sees clean state and executes as **IDEM-1** (zero partial effects). |
| **IDEM-7** | Client retries after $> 48\text{ h}$ (`idempotency` row purged) using the same client-generated UUIDv7 `event_id` | Acquired (`true`) | Absent (purged after `expires_at`) | Present in `event(event_id UNIQUE)` | Guard checks `SELECT * FROM event WHERE event_id = %s` before Step 8; finds existing event, caches and returns `409 Conflict` (`reason_code = 'DUPLICATE_EVENT_ID'`) containing the original committed event view. |
| **IDEM-8** | Client omits `Idempotency-Key` header (or length $< 8$ or $> 80$) on any mutating route | Not called | Not queried | Not queried | FastAPI middleware rejects with `422 Unprocessable Entity` (`reason_code = 'MISSING_IDEMPOTENCY_KEY'`). |

### 4.2 Savepoint Rollback for Domain Rejections & Autonomous PIN Counter (`F1`, `F7`, `I8`)

A critical subtle bug in naive single-transaction pipelines is that rolling back a transaction on a `403`/`409`/`412` error also rolls back the audit log (`rejected_command`), the idempotency record (`idempotency`), and the failed PIN counter (`session.pin_failed`). RHP-1 closes both failure modes explicitly:
1. **Autonomous PIN Failure Connection (Step 3):** When `argon2_verify(s.pin_hash, cmd.pin)` returns `False`, `autonomous_pin_failed(s.id)` opens a **separate short-lived database connection** outside the main transaction, increments `session.pin_failed`, sets `pin_locked_until = clock_timestamp() + interval '120 seconds'` if `pin_failed >= 3`, and commits immediately. The main transaction then records the `403 PIN_INVALID` response in `idempotency` and commits.
2. **Savepoint `sp_cmd` After Locking Referral (Step 4–10):**
   - Step 4 acquires `SELECT * FROM referral WHERE id = %s FOR UPDATE`, sets `set_config('rhp.locked_referral', str(r.id), true)`, and then issues `SAVEPOINT sp_cmd`.
   - If Steps 5–9 raise a deterministic `Reject(code, reason)` (e.g., `412 STALE_VERSION`, `409 LEASE_HELD`, `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`), the handler executes `ROLLBACK TO SAVEPOINT sp_cmd`.
   - Because the `referral` row lock and the Step 1 `idempotency` insert occurred **before** `SAVEPOINT sp_cmd`, both remain held and intact!
   - The handler then inserts the audit row into `rejected_command`, updates `idempotency` to `status='DONE'` with the error status/body, and issues `COMMIT`.

### 4.3 Offline Staleness & Live Resource Reconfirmation (`F12`, `I15`)

```
RECEIVING DESK                           API / POSTGRESQL 16
      |                                           |
      |--- 1. POST /offers/{id}/confirm (OT) ---->|expires_at = server_ts + confirm_ttl
      |<-- 200 OK (expires_at = T0 + 120s) -------|
      |                                           |
  [Network drops for 180s; user clicks ACCEPT]    |
  [UI shows: "Pending, not confirmed"]            |
      |                                           |
  [Network recovers at T0 + 185s]                 |
      |--- 2. POST /offers/{id}/accept ---------->|Step 7: min(expires_at) <= server_ts
      |<-- 409 STALE_CONFIRMATION_RECONFIRM_REQ --|(logged in rejected_command)
      |                                           |
  [PWA opens Live Reconfirmation Modal]           |
      |--- 3. POST /offers/{id}/confirm (OT) ---->|expires_at = (T0+186s) + 120s
      |--- 4. POST /offers/{id}/accept (new key)->|Step 7 passes -> LEASE_GRANTED
      |<-- 200 OK (lease_epoch = 1) --------------|
```

Exact rules enforced in Step 7 (`check_confirmations(conn, r, cmd, ts)`):
1. `RESOURCE_CONFIRM` cannot be queued offline: its payload requires `client_mode = 'LIVE'`, and the PWA disables the resource-confirmation checkboxes while `navigator.onLine == false` or SSE is disconnected.
2. On `ACCEPT` (and `CONFIRM_COUNTER(true)`), the server queries:
   ```sql
   SELECT ncr.capability, orc.expires_at
     FROM need_class_requirement ncr
     LEFT JOIN offer_resource_confirmation orc
       ON orc.offer_id = %s AND orc.capability = ncr.capability
    WHERE ncr.need_class = %s;
   ```
3. If any required capability row has `orc.expires_at IS NULL`, `ACCEPT` fails with `422 MISSING_RESOURCE_CONFIRMATION`.
4. If any required capability row has `orc.expires_at <= ts` (where `ts = GREATEST(clock_timestamp(), r.head_ts)`), `ACCEPT` fails with `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` (`I15`).

---

## 5. Timing, Clock Skew & Unified Notice Ladder Edge Cases

### 5.1 Unified ACK Window & Notice Ladder Ordering (`F2`, `F3`, `I13`)

When an offer is created at time $t_0$ (`status = 'OPEN'`), three `deadline` rows are inserted in the same transaction:
1. `kind = 'NOTICE_VOICE'`, `due_at = t_0 + A/4`
2. `kind = 'NOTICE_PROXY'`, `due_at = t_0 + 3A/4`
3. `kind = 'ACK'`, `due_at = t_0 + A`

**Edge Case — Notice Rung Fires After Offer Already ACKed or Closed:**
- When `apply_command(ACK)` (or `ACCEPT`, `COUNTER`, `DECLINE`, `CANCEL`) executes at any time $t < t_0 + A$, it updates all pending `NOTICE_VOICE`, `NOTICE_PROXY`, and `ACK` deadlines for that `offer_id` to `status = 'CANCELLED'`.
- If the poller claimed `NOTICE_VOICE` in Phase 1 just milliseconds before `ACK` committed, the poller's Phase 2 `apply_command(TIMEOUT)` acquires the `referral` lock after `ACK`, sees `deadline.status == 'CANCELLED'` (and `offer.status == 'ACKED'`), and returns `200 no-op` without placing a voice call.

**Edge Case — Facility ACKed Within $A$, But Undecided at $t_0 + A$ (`ADVISORY_PREWARM`):**
- When `ACK` commits at $t_{\text{ack}} < t_0 + A$, the `ACK` deadline is marked `DONE`, and a `DECISION` deadline is inserted with `due_at = t_ack + D`.
- Additionally, if a next facility $k+1$ exists in `referral.chain` and `mode == 'SEQUENTIAL'`, the server may emit an `ADVISORY_PREWARM` event to $k+1$ if $k$ remains undecided.
- **Crucial Guard:** `ADVISORY_PREWARM` does **not** create an `offer` row, does **not** grant a `payload_grant` for clinical ciphertext (`I10`), carries **no** deadline, cannot be `ACK`ed or `ACCEPT`ed, and does **not** increment `open_offers` (`I12`). It only displays a de-identified incoming-readiness heads-up on $k+1$'s desk.

### 5.2 $T_{\max}$ Bound & Catchment Chain Truncation (`F3`, `I13`)

For any profile with parameters $(A, D, F, \epsilon, B, S, \delta, V)$:
$$T_{\max} = F \cdot (A + D + \epsilon) \le B$$
$$\frac{A}{4} + (S - 1) \cdot \delta + V \le \frac{3A}{4} \quad (\text{when voice enabled})$$

**Edge Case — Clinician or Catchment Table Supplies $> F$ Facilities:**
- Although the `referral.chain` column allows `cardinality(chain) BETWEEN 0 AND 8` across profiles, at `CREATE` time the server truncates `referral.chain` to at most $F$ entries (`chain = input_chain[:profile.F]`) for the active profile.
- This guarantees that even if a district `catchment_chain` lists $5$ hospitals and the active profile has $F = 3$, the automated ladder will never execute more than $F = 3$ hops before transitioning to `ESCALATED_TO_DISPATCHER` within $T_{\max} \le B$ (`I13`).

### 5.3 Host Clock Step vs. Slew Edge Cases (`F11`, `I16`)

Let $t_{\text{wall}} = \text{\texttt{clock\_timestamp()}}$ and $t_{\text{head}} = \text{\texttt{referral.head\_ts}}$. Every command computes:
$$t_s = \max\left(t_{\text{wall}},\ t_{\text{head}}\right)$$
and if a referral already has $t_{\text{wall}} == t_{\text{head}}$ within the same microsecond, the server adds $+1\ \mu\text{s}$ (`r.head_ts + interval '1 microsecond'`) if strict microsecond uniqueness is needed, satisfying `NEW.server_ts >= r.head_ts` in trigger `rhp_event_guard` (`I16`).

- **Backward Clock Jump ($t_{\text{wall}} < t_{\text{head}}$ by $\Delta$):**
  - `server_ts` remains pinned at $t_{\text{head}}$ for all new events on that referral (`I16` never violates).
  - New deadlines created during the backward jump have `due_at = t_head + window`, while the poller compares `due_at <= clock_timestamp()`. Thus, deadline firing is delayed by $\Delta$ until the wall clock catches up.
  - Because `chronyd` is configured for slew-only after boot (`makestep` disabled) and the monitor checks `heartbeat.ntp_offset_ms` every $5\text{ s}$, any step $> 2000\text{ ms}$ triggers an immediate `CLOCK_OFFSET_ALARM` on the Guarantee Arena screen.

---

## 6. Identity, Reach Channels, Stream Revocation & Privacy Edge Cases

### 6.1 Exotel Outbound IVR Edge Cases (`F7`, `I4`, `I6`)

1. **Voicemail / PBX Auto-Attendant Pick-up:**
   - Exotel initiates the outbound call to `roster.phone_e164`.
   - Even if the carrier signals `HTTP 200` call-answered immediately when a voicemail box picks up, **no `ACK` event is generated**.
   - The initial Exotel applet plays: *"Emergency referral alert. Press 1 to hear the referral."* (`Gather` timeout $= 8\text{ s}$, `numDigits = 1`).
   - Only if Exotel posts `Digits=1` (and `AnsweredBy != 'machine'`) does the webhook execute `apply_command(ACK, channel='VOICE')`.
2. **DTMF `#` URL-Encoding & Partial PIN Entry:**
   - Exotel encodes the `#` terminator as `%23` or strips it depending on applet configuration; the webhook parser normalizes `digits.rstrip('#')` and validates `^[0-9]{4}$`.
   - If the user enters fewer than $4$ digits before timeout, the IVR prompts *"PIN requires 4 digits, please re-enter"* without incrementing `pin_failed` (up to $2$ input timeouts before hanging up).
3. **Call Drops After PIN Entered Before Audio Confirmation Plays:**
   - The database transaction commits **before** the HTTP response returning the `"Confirmed, referral accepted"` audio applet is sent.
   - If the phone line drops while the audio is playing, the lease is already committed in PostgreSQL, and the server pushes an SMS link confirmation (`outbox` channel `SMS`) to the same `roster.phone_e164` so the clinician has a written receipt on their feature phone.

### 6.2 Crockford Base32 + Mod-37 Paper Code Edge Cases (`F7`, §8)

The paper code format is `CCCCCCCC-K`, where:
- `CCCCCCCC` is $8$ symbols from Crockford's Base32 alphabet (`0123456789ABCDEFGHJKMNPQRSTVWXYZ`, representing a $40$-bit integer $N \in [0, 2^{40}-1]$).
- `K` is $1$ check symbol from the $37$-symbol Crockford check alphabet (`0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U`), equal to $N \bmod 37$.

```python
CROCKFORD_32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CROCKFORD_37 = CROCKFORD_32 + "*~$=U"
CONFUSABLES = str.maketrans({"O": "0", "o": "0", "I": "1", "i": "1", "L": "1", "l": "1"})

def normalize_and_verify_paper_code(raw: str) -> str:
    cleaned = raw.strip().upper().translate(CONFUSABLES).replace("-", "").replace(" ", "")
    if len(cleaned) != 9:
        raise ValueError("INVALID_LENGTH")
    body, check_char = cleaned[:8], cleaned[8]
    if any(ch not in CROCKFORD_32 for ch in body) or check_char not in CROCKFORD_37:
        raise ValueError("INVALID_ALPHABET")
    n = 0
    for ch in body:
        n = (n << 5) | CROCKFORD_32.index(ch)
    if CROCKFORD_37[n % 37] != check_char:
        raise ValueError("INVALID_PAPER_CODE_CHECKSUM")
    return f"{body}-{check_char}"
```

- **Human Confusable Normalization:** Handwritten `O`/`o` is mapped to `0`; `I`/`i`/`L`/`l` is mapped to `1`; hyphens and spaces are stripped before checksum verification.
- **Single-Symbol Substitution Proof:** Because $37$ is prime and $\gcd(32^i, 37) = 1$ for all $i \in \{0, \dots, 7\}$, changing any single symbol by $\Delta \in \{1, \dots, 31\}$ changes $N$ by $\Delta \cdot 32^i \not\equiv 0 \pmod{37}$, which is detected $100\%$ of the time.
- **Adjacent Transposition Proof:** Swapping adjacent distinct symbols $a \neq b$ at positions $i+1$ and $i$ changes $N$ by $(a - b)(32^{i+1} - 32^i) = (a - b) \cdot 31 \cdot 32^i \not\equiv 0 \pmod{37}$ because $\gcd(31, 37) = 1$, detecting $100\%$ of adjacent transpositions of distinct characters.

### 6.3 SSE Stream Authorization & Revocation Edge Cases (`F10`, `I10`)

```python
async def sse_event_generator(session, referral_id: UUID, last_event_id: int):
    # Re-evaluated on EVERY event frame and EVERY 15s heartbeat:
    while True:
        if not is_session_valid(session.id):
            yield ServerSentEvent(event="SESSION_REVOKED", data="{}")
            return
        grant_active = has_active_payload_grant(referral_id, session.facility_id)
        for ev in fetch_events_since(referral_id, last_event_id):
            last_event_id = ev.seq
            if ev.type == "GRANT_REVOKED" and ev.detail.get("facility") == str(session.facility_id):
                yield ServerSentEvent(id=str(ev.seq), event="GRANT_REVOKED", data='{"wipe_dom":true}')
                grant_active = False
                continue
            payload = ev.to_public_metadata_dict()
            if grant_active and session.role_slot != "JUDGE_DESK":
                payload["clinical_summary"] = decrypt_clinical_view(referral_id)
            yield ServerSentEvent(id=str(ev.seq), event=ev.type, data=jcs_str(payload))
        await asyncio.sleep(0.5)  # with 15s ": heartbeat\n\n" comment + re-auth check
```

- **`JUDGE_DESK` Role Restriction:** Even if a judge scans a QR code for a facility desk, `role_slot == 'JUDGE_DESK'` is restricted to synthetic/metadata views in real-data mode and capped at $20$ concurrent sessions.
- **Reconnect After Grant Revocation (`Last-Event-ID`):** If a superseded or declined hospital reconnects with `Last-Event-ID: 1` after its grant was revoked at `seq = 5`, `has_active_payload_grant()` evaluates at reconnect time (`False`), so even historical events `seq = 2..4` are replayed **without** clinical fields (`I10`).

---

## 7. Integrity Verification, Cold-Key Restore, Mutation Suite & `BROKEN_BUILD` Isolation

### 7.1 Browser & Monitor Verification Edge Cases (`F8`, `I5`)

The pure-JS browser verifier (`@noble/curves/ed25519` + `@noble/hashes/sha256`) and the witness auditor handle five distinct failure signatures:

| Verifier Error Code | Triggering Condition | Exact Diagnostic Output Format |
|---|---|---|
| **`CHECKPOINT_SIG`** | Ed25519 signature over `rhp1/<deployment>\n<tree_size>\n<root_b64>\n` fails verification against pinned `SIGNER_PUB` | `CHECKPOINT_SIG checkpoint_id=<id> signer=<key_id>` |
| **`SEQ_GAP`** | Event stream for `referral_id` does not start at `seq=1` or has `events[i].seq != events[i-1].seq + 1` | `SEQ_GAP referral=<id> expected_seq=<n> got_seq=<m>` |
| **`BROKEN` (`PREV`)** | `events[0].prev_hash != 0x00*32` or `events[i].prev_hash != events[i-1].hash` | `BROKEN referral=<id> seq=<n> kind=PREV expected=<hex> got=<hex>` |
| **`BROKEN` (`HASH`)** | `SHA256(events[i].prev_hash || JCS(events[i].core)) != events[i].hash` (e.g., someone edited `detail` or `epoch` in `psql`) | `BROKEN referral=<id> seq=<n> kind=HASH expected=<hex> got=<hex>` |
| **`ROOT_MISMATCH`** | Folding `SHA256(0x00 || id_16B || head_seq_8B_BE || head_hash_32B)` along the Merkle inclusion `path` does not equal `checkpoint.root_hash` | `ROOT_MISMATCH referral=<id> checkpoint_id=<id> computed=<b64> signed=<b64>` |
| **`TRUNCATED`** | Witness holds a prior signed checkpoint where `referral_id` had `head_seq = k`, live DB returns `head_seq < k`, and **no** cold-key signed `RESTORE` checkpoint covers the regression | `TRUNCATED referral=<id> at seq=<k> live_seq=<m>` |

### 7.2 Distinguishing Legitimate Backup Restore from Malicious Truncation (`F8`)

If a catastrophic storage failure requires restoring the database from a backup taken at `checkpoint_id = C_0`:
1. Any events committed after $C_0$ but lost before replication are absent, causing live `head_seq` values to be lower than checkpoints $C_1, C_2$ already held by witnesses.
2. Without a formal restore record, every witness would report `TRUNCATED` (`TAMPER`).
3. To execute a legitimate restore:
   - An operator holding the offline cold Ed25519 private key (`COLD_PRIV`, corresponding to `COLD_PUB` pinned in the client bundle) signs the canonical restore statement:
     $$\text{\texttt{restore\_note}} = \text{\texttt{"rhp1-restore\textbackslash n"}} \parallel \text{\texttt{restore\_from\_checkpoint\_id}} \parallel \text{\texttt{"\textbackslash n"}} \parallel \text{\texttt{restored\_at\_us}} \parallel \text{\texttt{"\textbackslash n"}} \parallel \text{\texttt{head\_map\_sha256\_b64}}$$
   - The operator inserts a `checkpoint(kind='RESTORE', restore_from=C_0, cold_signature=sig)` row and appends a `RESTORE` event (`detail={'checkpoint_id': C_0}`, `prev_hash = restored_head_hash`, `seq = restored_head_seq + 1`) to each active referral.
   - The browser verifier verifies `cold_signature` against `COLD_PUB`, confirms `prev_hash` matches the $C_0$ leaf, and displays an amber `VERIFIED_RESTORE from checkpoint=<C_0>` notice instead of `TAMPER`.

### 7.3 The 6+2 Common-Mode Independence Mutation Suite (`F17`)

To prove that the specification (Quint, Person A), the server (`apply_command`, Person A), and the independent runtime monitor (Python, Person B) do not share common-mode blind spots, the CI gate `T-F17` (`mutation_suite`) injects each of the following $8$ mutations one by one and asserts that the target detector trips with a non-zero violation count within $\le 1$ cycle:

| Mutation ID | Target Artifact | Exact Injected Fault | Required Detector That MUST Fail / Trip | Expected Violation Code |
|---|---|---|---|---|
| **`M1`** | Server (`apply_command` Step 5) | Comment out `if cmd.expected_epoch != r.lease_epoch: raise Reject(412, "STALE_EPOCH")` and apply an event carrying a stale `epoch < r.lease_epoch` | Independent Python Monitor (`fold()`) + Conformance Vector `V-STALE-EPOCH` | `I8` (`epoch < st["epoch"]`) |
| **`M2`** | Scratch Server + Scratch DB | Remove `FOR UPDATE` from `SELECT * FROM referral` and drop unique index `one_lease`, then run $200$-way barrier `ACCEPT` race | `T-C1` (`race200`) + Independent Python Monitor (`fold()`) | `I2` (`DOUBLE_LEASE_VIOLATION`: two `LEASE_GRANTED` events without an intervening revoke) |
| **`M3`** | Server Poller (`poller.py`) | Hold `SELECT ... FROM deadline FOR UPDATE` open across Phase 2 while calling `apply_command()` concurrently with live `ACCEPT` calls | `T-F1` (`lock_order_200way`) checking `pg_stat_database.deadlocks` and `rhp_require_lock` | `I14` (`deadlocks_delta > 0` or `I14_LOCK_NOT_HELD`) |
| **`M4`** | Quint Spec (`rhp1.qnt`) | In `action timeout(f)`, remove `else if (off.get(g) == "SOFT") "TIMEOUT"` so the prior `SOFT` offer is not evicted when $f+1$ opens | `quint run rhp1.qnt --invariant safety` | `I12` counterexample trace where `nOpen(off) == 3` |
| **`M5`** | Server (`append_event` Step 9) | Write `prev_hash = b"\x00" * 32` on `seq = 2` instead of `r.head_hash` (with trigger `event_guard` disabled in scratch test) | Pure-JS Browser Verifier + Independent Python Monitor (`fold()`) | `I5` (`BROKEN seq=2 kind=PREV`) |
| **`M6`** | Server (`check_confirmations` Step 7) | Change `if orc.expires_at <= ts:` to `if False:` so an expired `offer_resource_confirmation` is accepted | Conformance Vector `V-STALE-CONFIRM` + Independent Python Monitor | `I15` (ACCEPT committed with `min(expires_at) <= server_ts`) |
| **`M7`** | `transitions.yaml` | Add guard `hs_state: [OFFERED, ACCEPTED]` to `TR_UPDATE`, blocking `TR_UPDATE` when `hs_state == 'ESCALATED_TO_DISPATCHER'` | Conformance Vector `V-TR-INDEPENDENT` + Independent Python Monitor | `I3` (transport update rejected in a non-terminal handshake state) |
| **`M8`** | Quint Spec (`rhp1.qnt`) | Add guard `hs != "DISPATCH"` to `action trStep` | `quint run rhp1.qnt` (`transportNeverGated` / dispatch-transport reachability test) | `I3` trace failure |

### 7.4 Safe `BROKEN_BUILD` Isolation Guards (`F20`)

When demonstrating the Guarantee Arena's ability to catch a double-lease bug on stage (`BROKEN_BUILD=1`), the following $4$ hard boot assertions run before FastAPI binds a port:
```python
def assert_broken_build_isolation(env: dict, dsn: str):
    if env.get("BROKEN_BUILD") != "1":
        return
    if env.get("REAL_DATA") == "1":
        sys.exit(78)  # EX_CONFIG: never run broken build when REAL_DATA=1
    parsed = psycopg.conninfo.conninfo_to_dict(dsn)
    if parsed.get("dbname") != "rhp_scratch_broken":
        sys.exit(78)  # Must connect exclusively to scratch DB
    if parsed.get("user") != "rhp_scratch_app":
        sys.exit(78)  # Must use dedicated scratch DB role
    # Verify pg_hba / role isolation: scratch role MUST fail to connect to main DB 'rhp'
    try:
        main_dsn = psycopg.conninfo.make_conninfo(**{**parsed, "dbname": "rhp"})
        with psycopg.connect(main_dsn, connect_timeout=2):
            sys.exit(78)  # Abort if scratch credentials can access main DB!
    except psycopg.OperationalError:
        pass  # Expected: access denied to main DB
```

---

## 8. Complete 40-Item Loophole Ledger & D1–D20 / F1–F20 Traceability

### 8.1 The 40-Item Loophole Ledger (`LH-01` to `LH-40`, v8 §16)

| # | Loophole | Architectural Closure / Bounded Residual | Inv / Fix | Test ID | Status |
|---|---|---|---|---|---|
| **LH-01** | Blocking care through mandatory clinical fields ($\text{MgSO}_4$ dose/time) | `mgso4_status` (`GIVEN \| NONE_GIVEN \| UNKNOWN`) is answer-required, never knowledge-required; `UNKNOWN` sets red receiver banner, never blocks `CREATE` or dispatch | `D1`, `I3` | `T-K1` | `CLOSED` |
| **LH-02** | Ambulance held at origin until handshake completes | Independent Transport track (`REQUESTED -> DISPATCHED -> EN_ROUTE -> ARRIVED -> HANDED_OVER`); transport commands never read `hs_state` | `D2`, `I3` | `T-I3` | `CLOSED` |
| **LH-03** | Double ownership lease granted on concurrent clicks | Per-referral `SELECT ... FOR UPDATE` on primary + `one_lease` partial unique index + `lease_epoch` increment + `SOFT_OPEN` late-accept rule | `D7`, `I2` | `T-C1` | `CLOSED` |
| **LH-04** | Zombie write from delayed offline device overwrites newer state | Every mutating command checks `expected_version` and `expected_epoch` in Step 5; stale writes get `412` and log to `rejected_command` | `D7`, `I8` | `T-I8` | `CLOSED` |
| **LH-05** | Lost HTTP response followed by client retry duplicates event | Step 1 `Idempotency-Key` (`PRIMARY KEY (actor_id, key)`) + `request_hash` + `event.event_id UNIQUE` replays stored response | `I4`, `F14` | `T-F14` | `CLOSED` |
| **LH-06** | In-memory timer lost on server restart | Timers are durable rows in `deadline` table (`status='PENDING'`); stateless 2-phase poller claims overdue rows across restarts | `D8`, `I1` | `T-T1` | `CLOSED` |
| **LH-07** | Client clock skew alters deadline durations or breaks event order | Deadlines and confirmations computed strictly from `GREATEST(clock_timestamp(), referral.head_ts)` under `referral` lock; client skew logged only | `F11`, `I16` | `T-F11` | `CLOSED` |
| **LH-08** | Silent receiving hospital stalls referral indefinitely | Unified ACK window $A$ (rungs at $0$, $A/4$, $3A/4$) + decision window $D$ + automatic escalation across `referral.chain` to `ESCALATED_TO_DISPATCHER` within $T_{\max} \le B$ | `F2`, `F3`, `I1`, `I13` | `T-F3` | `CLOSED` |
| **LH-09** | Escalation chain exhausted with no destination left | Transitions to `ESCALATED_TO_DISPATCHER` with `DISPATCH_ACTION` deadline; system never invents an unapproved destination | `I1`, `I7` | `T-I7`, `VEC-SC08` | `CLOSED` |
| **LH-10** | Tertiary medical college overload from parallel broadcasting | `SEQUENTIAL` mode is default; `PARALLEL2` is restricted to dispatcher/demo; per-facility open-offer cap triggers `AT_CAPACITY` decline | `F13`, `I12` | `T-K3` | `BOUNDED` |
| **LH-11** | Referral ping-pong loop ($A \rightarrow B \rightarrow A$) | `UNIQUE (referral_id, facility_id)` on `offer` (`I9`) + `CHECK (origin_facility_id <> target_facility_id)` on `catchment_chain` | `D3`, `I9` | `T-I9` | `CLOSED` |
| **LH-12** | Hospital accepts to game KPI, then delays bed handover at door | Separate `ARRIVED -> HANDED_OVER` APOT metric + `HANDOVER` deadline $H$ emitting `HANDOVER_OVERDUE` + `ARRIVAL_REJECTED` revoking lease and logging broken commitment | `D18`, `I2` | `T-K2` | `BOUNDED` |
| **LH-13** | Shared ward tablet spoofing ("user present" vs "user verified") | Every mutating action (`ACCEPT`, `COUNTER`, `DECLINE`) requires server-verified Argon2id PIN in Step 3 (`NIST UV`), plus enrolled `device_id` and active `roster` slot | `D12`, `F7`, `I6` | `T-F7` | `CLOSED` |
| **LH-14** | BOLA, mass-assignment of `hs_state`, or function-level role abuse | Pydantic `extra='forbid'`, server-owned state transitions from `transitions.yaml`, object-level `facility_id` / `payload_grant` checks on every route | `I6`, `I10` | `T-I6b` | `CLOSED` |
| **LH-15** | Sysadmin or DBA tampers with `event` rows in PostgreSQL | `REVOKE UPDATE, DELETE` from `rhp_app` + `event_ao` trigger + per-referral SHA-256 hash chain + 5s Ed25519 Merkle checkpoints to witnesses (detects tampering within $\le 5\text{ s}$) | `D10`, `F8`, `I5` | `T-F8` | `BOUNDED` |
| **LH-16** | Operator presents split-view history to different parties | Signed checkpoints broadcast every $5\text{ s}$ to big screen, judge QR phones, and off-box witness log; witnesses compare root hashes | `D10`, `F8`, `I5` | `T-S2` | `BOUNDED` |
| **LH-17** | Bot farm mints thousands of QR judge tokens to DoS the demo | Rotating single-use QR (`jti`, valid $20\text{ s}$, rotates every $15\text{ s}$) + Cloudflare Turnstile challenge before session mint + admission cap of $20$ desks + LAN fallback | `D11`, §9 | `T-N7` | `CLOSED` |
| **LH-18** | PHI leaked through third-party push notification servers (FCM) | FCM carries zero clinical payload (wake ping only); Android app fetches clinical payload over authenticated HTTPS | `I10` | `T-P3` | `CLOSED` |
| **LH-19** | PHI leaked or silently dropped in DLT SMS messages | SMS carries static template alert + short code/link ($\le 30\text{ chars}$ variable); zero clinical text ever passed to SMS adapter | `I10` | `T-P2` | `CLOSED` |
| **LH-20** | Fake crypto-shredding ("deleting a salt") leaves PHI intact | Envelope encryption: AES-256-GCM per-referral DEK wrapped by monthly `kek_epoch` KEK; shredding deletes ciphertext, nulls `wrapped_dek`, and destroys expired KEK epochs | `D9`, §10 | `T-P5` | `BOUNDED` |
| **LH-21** | Conflict between DPDP s.8(7) erasure and 3-year clinical retention | Handover record (`clinical_payload`) separated from PHI-free metadata log (`event`); retention window is a configurable policy parameter pending legal review `[GAP]` | `D9`, `L2` | `T-L2` | `OPEN` |
| **LH-22** | AI intake hallucination enters the clinical handover record | AI is optional (`T3_EXTRAS`), quarantined behind Cognitive Forcing Function (`423` until anchors committed), requires manual re-entry of critical fields | `D1`, `A1`, `A2` | `T-A1`, `T-A2` | `BOUNDED` |
| **LH-23** | AI confidence scores or explanations induce automation bias | UI and API strip all LLM confidence scores and explanations (explanations raised commission errors $10\% \rightarrow 21\%$ `[V]`) | `A1`, §16 | `T-A1` | `CLOSED` |
| **LH-24** | Countdown timers on receiving desk distort clinical triage (Goodhart) | Receiving desk displays a priority-ordered queue with **no countdown clocks** (`[V]`); district dashboards show aggregated capacity signals, never individual blame | `D18`, §15 | `T-K2` | `CLOSED` |
| **LH-25** | Unlawful staff performance surveillance via telemetry | DPDP s.7(i) posture: prior written notice, minimal collection (`event.detail` allowlist), siloed from HR records, 4h timestamp bucketing and $k \ge 5$ suppression on exports | `D18`, `F9`, §10 | `T-F9` | `BOUNDED` |
| **LH-26** | Double-entry burden on busy PHC clinicians (paper slip + app) | The ReferralHandshake card **is** the printable Dakshata/ISBAR referral slip with embedded Crockford Base32 paper code and QR | `D18`, §8 | `VEC-SC13` | `CLOSED` |
| **LH-27** | Overclaiming clinical outcomes or unmeasured metrics on stage | Strict Claims Register (§19) + automated forbidden-word lint (`ST-5`) + every latency/recovery number shown live is measured live from the running log | `D5`, §19 | `ST-5` | `CLOSED` |
| **LH-28** | Spec/code drift or coding agent "fixing" the test/spec to pass | `/spec`, `db/schema.sql`, `transitions.yaml`, and `/monitor` are protected by `CODEOWNERS` and hash-pinned in CI; agents cannot modify them | `D6`, `F17` | `T-F17` | `CLOSED` |
| **LH-29** | Model-checker false atomicity hides database race conditions | Quint verifies control-plane logic; real row-lock races are tested directly against PostgreSQL 16 via $200$-way `asyncio.Barrier` (`T-C1`) and Toxiproxy faults | `D6`, §12 | `T-C1`, `T-F1` | `CLOSED` |
| **LH-30** | Runtime monitor and server share the same transition bug | Person A writes server, `transitions.yaml`, and Quint spec; Person B writes the Python monitor from §3 prose alone (`rhp_monitor` read-only role, zero server imports), verified by mutations `M1–M8` | `D19`, `F17` | `T-F17` | `CLOSED` |
| **LH-31** | Venue Wi-Fi or cloud failure crashes the live hackathon demo | Local-first Docker stack on laptop + dual uplink (phone hotspot + venue Wi-Fi) + LAN-QR fallback + 4 pre-recorded MP4 clips (Clips A–D) + `H22` code freeze | `D17`, `F16` | `T-D4`, `T-F16` | `BOUNDED` |
| **LH-32** | Urban canyon / ionospheric GPS error ($7\text{–}50\text{ m}$ `[V]`) mis-triggers arrival | $200\text{ m}$ geofence + dwell emits `ARRIVAL_SUGGESTED` only; a human (`EMT`, desk, or dispatcher) must confirm `ARRIVED` | `D2`, `F5` | `T-F5` | `CLOSED` |
| **LH-33** | Missing OSM capability tags ($0.08\%$ bed tags `[V]`) or OSM tile-policy ban | Curated Karnataka facility registry with IPHS/CEmONC capability tags + commercial Mapbox SDK / self-hosted PMTiles (never bulk-scraping OSM tiles) | `D14`, `D15`, §9 | `T-K3` | `CLOSED` |
| **LH-34** | Stale self-reported facility capability treated as "live beds" | `facility_capability` rows carry `attested_at` and `expires_at`; UI displays attestation age and hides expired capabilities; never labelled "live beds" | `D15`, §14 | `T-K3` | `CLOSED` |
| **LH-35** | Outdated duty roster phone number blocks offer notification | Concurrent SSE/FCM push at $t=0$ to all slots + staggered voice calls across slots $0..S-1$ at $A/4 + i\cdot\delta$ + dispatcher proxy page at $3A/4$ | `F2`, §8 | `VEC-SC19` | `CLOSED` |
| **LH-36** | Rival locks out receiving hospital's PIN, or SIM swap compromises slot | PIN lockout is scoped per `session_id` / `call_sid` (not per facility/role) so rivals cannot DoS the desk; repeated lockouts alert admin and suspend slot | `D12`, `F7` | `T-F7` | `CLOSED` |
| **LH-37** | Unsafe hardcoded timers or unbounded escalation chains | 4 cold-key signed profiles with startup validator enforcing $T_{\max} = F \cdot (A + D + \epsilon) \le B$ (`I13`) and blocking demo profiles when `REAL_DATA=1` | `F2`, `F3`, `I13` | `T-F2`, `T-F3` | `CLOSED` |
| **LH-38** | Single SQLite file corruption or single-node DB loss in pilot | PostgreSQL 16 primary with `synchronous_commit=on` (Docker in demo; Multi-AZ synchronous standby + WAL archive in pilot) | `D8`, §7 | `T-F2b` | `BOUNDED` |
| **LH-39** | LLM-generated concurrency defects in `apply_command()` or poller | Spec-first workflow, total lock order enforced by trigger `rhp_require_lock` (`I14`), $200$-way concurrency barrier, and 8 mutation tests | `F1`, `F17`, `I14` | `T-F1`, `T-F17` | `CLOSED` |
| **LH-40** | Unsettled telecom regulation for automated clinical voice calls | Prototype uses Exotel trial sandbox with $\le 10$ whitelisted team numbers, `REAL_DATA=0`, press-1 human gate, and de-identified prompts; legal review required before pilot `[GAP]` | `F7`, `L1` | `T-L1` | `OPEN` |

### 8.2 Cross-Reference Index: `F1–F20` Closures $\leftrightarrow$ `I1–I16` Invariants $\leftrightarrow$ Self-Audit Tests (`ST-1..ST-5`)

| Fix ID | Summary of Architectural Closure | Enforced Invariants | Verification Gate / CI Test |
|---|---|---|---|
| **F1** | Global lock order `referral -> offer -> deadline -> outbox`; 2-phase poller; trigger `rhp_require_lock` | `I1`, `I14` | `T-F1` (`lock_order_200way`), `ST-1` |
| **F2** | Unified ACK window $A$ with notice rungs at $0$, $A/4$, $3A/4$; 4 signed profiles; demo guard on `REAL_DATA=1` | `I1`, `I13` | `T-F2` (`profile_guard`) |
| **F3** | Concurrent slot notification; $T_{\max} = F \cdot (A + D + \epsilon) \le B$; chain truncated to $F$ at `CREATE` | `I13` | `T-F3` (`tmax_validator`), `ST-2` |
| **F4** | Complete 24-table PostgreSQL 16 DDL, `one_lease`, deferred `referral_lease_fk`, append-only triggers | `I1–I16` | `T-F4` (`ddl_load_fk_scan`), `ST-3` |
| **F5** | Six explicit arrival cases `(a)–(f)`; geofence emits `ARRIVAL_SUGGESTED` only; human confirms `ARRIVED` | `I2`, `I3` | `T-F5` (`arrival_cases`) |
| **F6** | Reachability & Exit table; 9-outcome taxonomy; two-stage `CLOSURE` deadline $\rightarrow$ `UNKNOWN_COUNTER_REFERRAL` | `I1`, `I5` | `T-F6` (`reachability_bfs`), `VEC-SC28` |
| **F7** | Single-use enrollment ticket; autonomous-txn Argon2id PIN counter; per-session/call lockout; AMD + press-1 gate | `I6` | `T-F7` (`pin_lockout_scope`) |
| **F8** | Separate-OS-user `rhp-sign` Ed25519 checkpoint signer; $O(\log N)$ Merkle inclusion proofs; cold-key `RESTORE` | `I5` | `T-F8` (`tamper_vs_restore`) |
| **F9** | Per-type `event.detail` key allowlist (`rhp_detail_ok`), integer/enum/bool/UUID only, 4h buckets, $k \ge 5$ | `I11` | `T-F9` (`detail_check_fuzz`) |
| **F10** | Per-event SSE `payload_grant` authorization check + `GRANT_REVOKED` control frame + client DOM wipe | `I10` | `T-F10` (`sse_revoke`) |
| **F11** | `GREATEST(clock_timestamp(), referral.head_ts)` under referral lock; chrony slew-only; $>2\text{ s}$ offset alarm | `I16` | `T-F11` (`clock_step`) |
| **F12** | `expires_at` on `offer_resource_confirmation`; `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`; live reconfirm modal | `I15` | `T-F12` (`offline_stale`) |
| **F13** | `open_offers` `CHECK (0..2)`; soft-open eviction on next hop; `PARALLEL2` and `COUNTER` deadline clamping | `I2`, `I12` | `T-F13` (`open_cap`) |
| **F14** | Step 1 idempotency with `pg_try_advisory_xact_lock`, `(actor_id, key)` + `request_hash`, `SAVEPOINT sp_cmd` | `I4`, `I8` | `T-F14` (`idem_matrix`), `ST-4` |
| **F15** | Every failure-mode row states a quantitative technical bound and reason (zero bare "none" claims) | All | `T-F15` (`residual_lint`), `ST-5` |
| **F16** | Feature flags `T0–T3` with strict cut order (`T3 -> T2 -> T1`; `T0` never cut) + 30s live proof loop | `I1–I16` | `T-F16` (`loop_rehearsal`) |
| **F17** | Common-mode independence: Person A writes server/Quint/YAML; Person B writes Python monitor from §3 prose; 8 mutations | `I1–I16` | `T-F17` (`mutation_suite`) |
| **F18** | Reconciled 6-month AWS `ap-south-1` Multi-AZ pilot budget ($\approx \$1,419 / 6\text{ mo}$, `[verify]`) | — | `T-F18` (`cost_recompute`) |
| **F19** | Explicit 12-state v7 $\rightarrow$ RHP-1 `referral.hs_state` / `offer.status` / `event.type` mapping | `I1–I5` | `T-F19` (`v7_map`) |
| **F20** | `BROKEN_BUILD=1` isolated to `rhp_scratch_broken` DB with exit-78 hard aborts if `REAL_DATA=1` or main DB reachable | `I2` | `T-F20` (`broken_isolation`) |