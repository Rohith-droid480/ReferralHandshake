# ReferralHandshake (Protocol RHP-1) — Master Build Plan & Real-Time Priority Build Modules

**System:** Referral Handshake Protocol (RHP-1) & Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru, 24-hour build, 2 students) `[V]`  
**Data Posture:** Synthetic data only (`REAL_DATA=0`)  
**First Clinical Pathway:** Emergency obstetric referral through Karnataka-style tiers (`PHC` $\rightarrow$ `CHC` $\rightarrow$ `FRU` $\rightarrow$ `DH` $\rightarrow$ `MC`); generic data model (`OBSTETRIC_EMERGENCY`, `NEONATAL`, `TRAUMA`, `CARDIAC`, `STROKE`)  
**Input Precedence:** `ReferralHandshake_LOCKED_Problem_Statement_v7.md` $>$ Research tagged `[V]` $>$ `ReferralHandshake_v8_LOCKED_Solution.md` $>$ `ReferralHandshake_FINAL_LOCKED_Architecture.md` $>$ `ReferralHandshake_3Gem_Antigravity_Workflow.md`

---

## 0. Master Build Sequence, Tier Cut Order & Governance

### 0.1 Execution Model & Dependency Graph
Every module and sub-segment (`1.1` through `12.3`) in this build plan is ordered by **strict dependency and criticality**:
$$\text{Spec-First Spine} \rightarrow \text{Immediate Proof} \rightarrow \text{Vertical Slice Integration } (\texttt{T0} \rightarrow \texttt{T1\_TRANSPORT} \rightarrow \texttt{T2\_REACH} \rightarrow \texttt{T3\_EXTRAS})$$
Do not skip ahead. A segment `X.Y` counts as complete only when its **Verification Gate** passes with raw command output pasted into the Build Report.

```text
[MODULE 1] Spec-First Spine, Cryptographic Primitives & Production Database (T0)
     |
     v
[MODULE 2] Identity, PIN Lockout Scope & 10-Step Transactional Command Pipeline (T0)
     |
     v
[MODULE 3] Core Handshake Commands, Single-Owner Lease & Escalation Engine (T0)
     |
     v
[MODULE 4] Independent Runtime Monitor, 200-Way Race & Safe BROKEN_BUILD (T0 Proof Gate)
     |
     v
[MODULE 5] Stateless Poller, Outbox Relay, Notice Ladder & Authorized SSE Hub (T0 Liveness)
     |
     v
[MODULE 6] Cryptographic Witness Signer, Merkle Checkpoints & Pure-JS Verifier (T0 Integrity)
     |
     v
[MODULE 7] Core PWA Desks, Rotating QR Admission & Guarantee Arena Big Screen (T0 Complete)
     |
     +--> [MODULE 8] Parallel Transport Track, Mapbox ETAs, Dispatcher Console & Replay (T1_TRANSPORT)
     |
     +--> [MODULE 9] Multi-Channel Reach: Exotel Voice IVR, DLT SMS & Paper Code (T2_REACH)
     |
     +--> [MODULE 10] Envelope Encryption, Crypto-Shredding & Command Centre Analytics (T3_EXTRAS A)
     |
     +--> [MODULE 11] Cognitive-Forcing AI Intake, FHIR/XES/BSA Exports & Kotlin App (T3_EXTRAS B)
     |
     +--> [MODULE 12] Toxiproxy Chaos Matrix, Self-Audit CI Scripts (ST-1..ST-5) & Final Gate Suite
```

### 0.2 Feature Flags & Tier Cut Order (Closure F16)

| Tier | Feature Flag | Scope & Deliverables | Cut Order |
|---|---|---|---|
| **T0** | Always On | FastAPI core, PostgreSQL 16 (`synchronous_commit=on`), 2-phase Poller, Outbox Relay, PWA desks with rotating QR admission, Independent Python Runtime Monitor, Witness Signer + Browser Verifier, `BROKEN_BUILD` scratch DB | **Never cut** |
| **T1** | `T1_TRANSPORT` | Parallel Transport Track, PWA Ambulance (foreground GPS), Mapbox Matrix ETA cache, Dispatcher Console + Proxy entry, Deterministic Replay Scrubber | Cut 3rd |
| **T2** | `T2_REACH` | Outbound Exotel Voice IVR (AMD + Press-1 human gate + DTMF PIN), TRAI DLT-compliant static SMS stub/sandbox, 9-char Crockford Base32 + mod-37 Paper Code | Cut 2nd |
| **T3** | `T3_EXTRAS` | Envelope encryption & crypto-shredder, Command Centre analytics, Cognitive-Forcing AI Intake (`423 ANCHOR_REQUIRED`), FHIR R4 / XES / BSA s.63 exports, Native Kotlin Android EMT app | Cut 1st |

### 0.3 Two-Lane Parallel Ownership & Common-Mode Independence (Closure F17)
- **Lane A (Person A — Backend & Formal Spec):** Owns `spec/transitions.yaml`, `spec/rhp1.qnt`, `db/01_schema.sql`, `api/`, `witness/`, and backend concurrency/chaos tests.
- **Lane B (Person B — Independent Monitor, Clients & Reach):** Owns `monitor/monitor.py`, `pwa/`, `spec/profiles.json`, Exotel/SMS/Paper adapters, and demo operations.
- **Strict Non-Interference Rule (F17):** `monitor/monitor.py` is built by Person B in a separate workspace from §3 invariant prose alone. It connects to PostgreSQL using the read-only `rhp_monitor` role and **imports zero code from `api/`**. `CODEOWNERS` protects `spec/`, `db/01_schema.sql`, `vectors/`, and `monitor/`.

### 0.4 Target Monorepo File Tree

```text
rhp/
├─ docker-compose.yml
├─ Makefile
├─ .env.example
├─ CODEOWNERS
├─ AGENTS.md
├─ db/
│  ├─ 01_schema.sql
│  ├─ 02_roles.sql
│  ├─ 03_seed.sql
│  └─ make_scratch.sh
├─ spec/                              # FROZEN (CODEOWNERS, SHA-256 pinned)
│  ├─ transitions.yaml
│  ├─ profiles.json
│  ├─ rhp1.qnt
│  └─ parity_vectors.json
├─ vectors/                           # FROZEN Conformance Vectors (V-01 .. V-28)
├─ api/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ rhp/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ db.py
│     ├─ crypto.py
│     ├─ profiles.py
│     ├─ transitions.py
│     ├─ auth.py
│     ├─ schemas.py
│     ├─ pipeline.py
│     ├─ commands/
│     │  ├─ create.py
│     │  ├─ ack_confirm.py
│     │  ├─ accept.py
│     │  ├─ decline_advance.py
│     │  ├─ counter.py
│     │  ├─ timeout.py
│     │  ├─ lifecycle.py
│     │  ├─ judge_join.py
│     │  └─ transport.py
│     ├─ poller.py
│     ├─ relay.py
│     ├─ sse.py
│     ├─ reach/
│     │  ├─ exotel_ivr.py
│     │  ├─ audio_manifest.json
│     │  ├─ dlt_sms.py
│     │  └─ paper_code.py
│     ├─ extras/
│     │  ├─ envelope_crypto.py
│     │  ├─ shredder.py
│     │  ├─ mapbox_eta.py
│     │  ├─ analytics.py
│     │  ├─ ai_intake.py
│     │  └─ exporters.py
│     └─ main.py
├─ monitor/                           # Independent Process (Imports NOTHING from api/)
│  ├─ Dockerfile
│  └─ monitor.py
├─ witness/                           # Separate OS User (uid 1002, key mode 0400)
│  ├─ Dockerfile
│  └─ signer.py
├─ scripts/
│  ├─ toggle_broken_build.sh
│  ├─ tamper.sh
│  ├─ witness_pull_sync.py
│  ├─ cold_sign_restore.py
│  └─ preflight.sh
├─ pwa/
│  ├─ Dockerfile
│  ├─ package.json
│  └─ src/
│     ├─ vendor/                      # Bundled @noble/curves & @noble/hashes
│     ├─ crypto/verifier.ts
│     ├─ store/sseClient.ts
│     ├─ store/outbox.ts
│     ├─ components/ModeBanner.tsx
│     ├─ views/JudgeJoin.tsx
│     ├─ views/ClinicianCard.tsx
│     ├─ views/ReceivingDesk.tsx
│     ├─ views/JudgeDesk.tsx
│     ├─ views/ArenaBigScreen.tsx
│     ├─ views/DispatcherConsole.tsx
│     ├─ views/AmbulancePwa.tsx
│     └─ views/CommandCentre.tsx
├─ android/                           # Native Kotlin EMT App (T3_EXTRAS)
│  └─ app/src/main/
│     ├─ AndroidManifest.xml
│     └─ java/in/rhp/emt/
│        ├─ LocationForegroundService.kt
│        ├─ outbox/OutboxDao.kt
│        └─ fcm/ZeroPayloadMessagingService.kt
└─ tests/
   ├─ explore_transitions.py
   ├─ test_boot_guards.py
   ├─ test_ddl_constraints.py         # ST-3 / T-F4
   ├─ test_lock_order.py              # ST-1 / T-F1
   ├─ test_tmax_profiles.py           # ST-2 / T-F2 / T-F3
   ├─ test_jcs_parity.py
   ├─ test_transitions_table.py       # T-F19
   ├─ test_auth_sessions.py
   ├─ test_pin_lockout_scope.py       # T-F7
   ├─ test_authz_matrix.py            # T-I6 / T-I6b / T-F9
   ├─ test_pipeline_core.py           # T-I8 / T-I14 / T-I16
   ├─ test_cmd_create.py              # T-I1 / T-I7
   ├─ test_cmd_ack_confirm.py
   ├─ test_cmd_accept.py              # T-C3 / T-F12 / T-I15
   ├─ test_cmd_decline_advance.py     # T-F13 / T-I9
   ├─ test_cmd_counter.py             # T-C4
   ├─ test_cmd_lifecycle.py
   ├─ test_monitor_fold.py
   ├─ test_race200.py                 # T-C1
   ├─ test_idempotency_matrix.py      # ST-4 / T-F14
   ├─ test_broken_build.py            # T-F20
   ├─ test_mutations.py               # T-F17 (M1..M6)
   ├─ test_conformance_vectors.py
   ├─ test_poller_liveness.py         # T-C2 / T-C6 / T-T1 / T-T4
   ├─ test_notice_ladder_and_closure.py
   ├─ test_sse_revoke.py              # T-F10 / T-N3
   ├─ test_clock_and_heartbeats.py    # T-F11
   ├─ test_witness_merkle.py
   ├─ test_tamper_vs_restore.py       # T-F8 / T-S2
   ├─ test_transport_and_arrivals.py  # T-F5 / T-I3
   ├─ test_dlt_sms_lint.py            # T-P2
   ├─ test_paper_code_mod37.py
   ├─ test_envelope_crypto.py         # T-P5
   ├─ test_analytics_recompute.py
   ├─ test_ai_seeded_errors.py        # T-A1 / T-A2
   ├─ test_claims_lexicon.py          # ST-5 / T-F15 / T-L3
   ├─ test_stateful_hypothesis.py
   └─ test_toxiproxy_chaos.py
```

---

## MODULE 1: Spec-First Spine, Cryptographic Primitives & Production Database (`T0` — Priority 1)

### 1.1 Monorepo Workspace, Docker Compose Topology & Environment Guard
* **Objective:** Initialize the repository structure, multi-container orchestration, and boot-level safety guards (`REAL_DATA=0`, `BROKEN_BUILD` isolation, and feature flags).
* **Files to Create:**
  * `docker-compose.yml`
  * `.env.example`
  * `Makefile`
  * `CODEOWNERS`
  * `api/rhp/config.py`
* **Implementation Specifications:**
  1. Configure `docker-compose.yml` with 9 services:
     * `pg`: `postgres:16` with command `["postgres", "-c", "synchronous_commit=on", "-c", "log_lock_waits=on"]`.
     * `api`: FastAPI server on port `8000`, dependent on `pg`, environment `PROFILE=DEMO_FAST`, `REAL_DATA=0`.
     * `poller`: runs `python -m rhp.poller`.
     * `relay`: runs `python -m rhp.relay`.
     * `monitor`: runs `python -m monitor` under UID `1001` with `RHP_MONITOR_DSN`.
     * `witness`: runs `python -m signer` under UID `1002` with `RHP_WITNESS_DSN` and read-only `0400` signing key mount.
     * `toxiproxy`: `ghcr.io/shopify/toxiproxy` exposing proxy ports for `pg` and `api`.
     * `pwa`: React production/dev server on port `3000`.
     * `tunnel`: `cloudflare/cloudflared` (optional profile).
  2. Implement `api/rhp/config.py` using Pydantic `BaseSettings`:
     * Environment variables: `PROFILE` (`DEMO_FAST`, `DEMO_VOICE`, `PILOT_OB_CRITICAL`, `PILOT_STANDARD`), `REAL_DATA` (`0` or `1`), `BROKEN_BUILD` (`0` or `1`), `LAN_MODE` (`0` or `1`), `T1_TRANSPORT` (`0` or `1`), `T2_REACH` (`0` or `1`), `T3_EXTRAS` (`0` or `1`), `APP_DSN`, `AUTONOMOUS_DSN`, `COLD_PUBKEY_HEX`, `WITNESS_PUBKEY_HEX`.
     * **Hard Boot Refusals (exit code `78`):**
       * If `REAL_DATA == 1` and `PROFILE in ("DEMO_FAST", "DEMO_VOICE")` $\rightarrow$ abort boot (`sys.exit(78)`).
       * If `REAL_DATA == 1` and `LAN_MODE == 1` $\rightarrow$ abort boot (`sys.exit(78)`).
       * If `BROKEN_BUILD == 1` and (`REAL_DATA == 1` or `"rhp_scratch_broken"` not in `APP_DSN`) $\rightarrow$ abort boot (`sys.exit(78)`).
* **Verification Gate (`T-F2`, `T-F20`):**
  * Run `docker compose up -d pg` and `pytest tests/test_boot_guards.py` verifying exit code `78` when `BROKEN_BUILD=1` is paired with the main database DSN or `REAL_DATA=1`.

### 1.2 PostgreSQL 16 24-Table DDL, Append-Only Triggers, Lock Guards & Role Grants
* **Objective:** Deploy the complete 24-table relational schema, custom domains, JSONB allowlist checks, append-only triggers, deferred constraint triggers, and least-privilege database roles (Closure F4).
* **Files to Create:**
  * `db/01_schema.sql`
  * `db/02_roles.sql`
  * `db/make_scratch.sh`
* **Implementation Specifications:**
  1. Write all 24 tables in `db/01_schema.sql` in exact dependency order:
     * `facility`, `roster`, `facility_capability`, `need_class_requirement`, `catchment_chain`, `device`, `enrollment_ticket`, `session`, `referral`, `offer`, `offer_resource_confirmation`, `deadline`, `event`, `key_version`, `event_secret`, `clinical_payload`, `payload_grant`, `telemetry`, `idempotency`, `inbox`, `outbox`, `rejected_command`, `checkpoint`, `heartbeat`.
     * Include partial unique index `CREATE UNIQUE INDEX one_lease ON offer (referral_id) WHERE status = 'ACCEPTED';` (Invariant I2) and `CREATE UNIQUE INDEX one_active_grant ON payload_grant (referral_id, facility_id) WHERE revoked_at IS NULL;`.
     * Include deferred circular foreign key `ALTER TABLE referral ADD CONSTRAINT referral_lease_fk FOREIGN KEY (lease_offer_id) REFERENCES offer(id) DEFERRABLE INITIALLY DEFERRED;`.
  2. **Pre-Applied Schema Refinements (Mandatory):**
     * In `rhp_allowed(t text)`:
       * Ensure `WHEN t='OFFER_DECLINED' THEN ARRAY['reason','facility']` so optional redirect suggestions (facility UUIDs) pass `rhp_detail_ok`.
       * Ensure `WHEN t='OFFER_SOFT_EXPIRED' THEN ARRAY['step','facility']`.
     * In `rhp_require_lock()`:
       * Support `CREATE` by requiring the caller to set `set_config('rhp.locked_referral', new_referral_id::text, true)` in the transaction prior to `INSERT INTO referral`.
       * Exempt delivery bookkeeping updates (`deadline` where `(NEW.status, NEW.due_at) IS NOT DISTINCT FROM (OLD.status, OLD.due_at)`, and `outbox` `UPDATE` for `status/attempts/visible_after`) as specified in §3 and §7.
     * In `db/02_roles.sql`:
       * Create roles `rhp_app`, `rhp_monitor`, and `rhp_witness` idempotently with login passwords.
       * Grant `SELECT ON event, referral, offer, deadline, checkpoint, heartbeat, outbox, rejected_command, offer_resource_confirmation, need_class_requirement TO rhp_monitor;` and `SELECT (id, facility_id, role_slot, slot_no, valid_from, valid_to) ON roster TO rhp_monitor;` so the independent monitor can verify Invariants I1–I16 without accessing `phone_e164` or `pin_hash`.
       * Revoke `UPDATE, DELETE` on `event`, `checkpoint`, `rejected_command` from `rhp_app`.
       * Grant `DELETE ON event_secret, clinical_payload, idempotency, telemetry TO rhp_app;` for crypto-shredding and TTL purges.
  3. Write `db/make_scratch.sh` to create database `rhp_scratch_broken` and role `rhp_scratch_app` with `01_schema.sql` loaded **except** `DROP INDEX one_lease;`, ensuring `rhp_scratch_app` cannot authenticate to the main database in `pg_hba.conf`.
* **Verification Gate (`ST-3` / `T-F4`):**
  * Load `01_schema.sql` and `02_roles.sql` into PostgreSQL 16. Query `information_schema.tables` to assert exactly 24 tables exist, scan `pg_constraint` and `pg_trigger` for all triggers (`event_ao`, `checkpoint_ao`, `rejected_ao`, `event_guard`, `lk_referral`, `lk_offer`, `lk_deadline`, `lk_event`, `lk_grant`, `lk_outbox`, `i1_pending_deadline`, `offer_chain_guard`), and assert that `UPDATE event` as `rhp_app` raises `APPEND_ONLY`.

### 1.3 Synthetic District Seed Data & Cold-Key Signed Timing Profiles
* **Objective:** Seed a realistic synthetic Karnataka obstetric referral network and lock the 4 cryptographically signed timing profiles with startup $T_{\max}$ validation (Closures F2, F3, Invariant I13).
* **Files to Create:**
  * `db/03_seed.sql`
  * `spec/profiles.json`
  * `api/rhp/profiles.py`
* **Implementation Specifications:**
  1. In `db/03_seed.sql`, insert clearly labeled synthetic facilities across tiers:
     * `PHC_CHANNAPATNA` (`PHC`), `CHC_RAMANAGARA` (`CHC`), `FRU_KANAKAPURA` (`FRU`), `DH_MANDYA` (`DH`), `MC_BENGALURU_OB` (`MC`), and `DISPATCH_108_CENTRAL` (`DISPATCH`).
     * Populate `need_class_requirement` for `OBSTETRIC_EMERGENCY` (`OT`, `BLOOD`, `ANAESTHETIST`, `NICU`).
     * Populate `facility_capability` with current timestamps and 24h `expires_at`.
     * Populate `catchment_chain` for `PHC_CHANNAPATNA` $\rightarrow$ `[CHC_RAMANAGARA, DH_MANDYA, MC_BENGALURU_OB]`.
     * Populate `roster` slots (`NURSE`, `CMO`, `CONSULTANT`, `CLINICIAN`, `EMT`, `DISPATCHER`, `ADMIN`, plus 20 `JUDGE_DESK` slots) and pre-registered `device` rows for local testing.
  2. In `spec/profiles.json`, encode the 4 profiles (`PILOT_OB_CRITICAL`, `PILOT_STANDARD`, `DEMO_FAST`, `DEMO_VOICE`) with exact millisecond values:
     * `PILOT_OB_CRITICAL`: $A=60000, D=180000, \text{rungs}=[0, 15000, 45000], S=3, \delta=5000, V=20000, F=3, \varepsilon=3000, C=90000, \text{confirm\_ttl}=120000, H=7200000, \text{dispatch\_action}=300000, \text{closure}=86400000, B=900000, \text{demo}=\text{false}$.
     * `PILOT_STANDARD`: $A=120000, D=300000, \text{rungs}=[0, 30000, 90000], S=3, \delta=10000, V=20000, F=3, \varepsilon=3000, C=150000, \text{confirm\_ttl}=180000, H=7200000, \text{dispatch\_action}=300000, \text{closure}=86400000, B=1500000, \text{demo}=\text{false}$.
     * `DEMO_FAST`: $A=3000, D=4000, \text{rungs}=[0, 750, 2250], S=3, \delta=0, \text{voice}=\text{false}, F=3, \varepsilon=1000, C=2000, \text{confirm\_ttl}=10000, H=30000, \text{dispatch\_action}=5000, \text{closure}=20000, B=25000, \text{demo}=\text{true}$.
     * `DEMO_VOICE`: $A=45000, D=20000, \text{rungs}=[0, 11250, 33750], S=1, \delta=0, V=20000, F=2, \varepsilon=1000, C=10000, \text{confirm\_ttl}=60000, H=60000, \text{dispatch\_action}=10000, \text{closure}=60000, B=150000, \text{demo}=\text{true}$.
     * Sign each canonical profile JSON with the offline Ed25519 cold key and embed `sig` and `profile_hash`.
  3. In `api/rhp/profiles.py`, implement `validate_profile(p, real_data)` enforcing:
     * Invariant I13: $T_{\max} = F \cdot (A + D + \varepsilon) \le B$.
     * Voice budget: if `p.voice`, $A/4 + (S - 1)\delta + V \le 3A/4$.
     * Rung tuple: $\text{rungs} == (0, A/4, 3A/4)$.
     * Real data guard: `not (p.demo and real_data)`.
     * Ed25519 signature verification against `COLD_PUBKEY_HEX`.
* **Verification Gate (`ST-2` / `T-F2` / `T-F3`):**
  * Run `pytest tests/test_tmax_profiles.py` confirming $729\text{ s} \le 900\text{ s}$, $1269\text{ s} \le 1500\text{ s}$, $24\text{ s} \le 25\text{ s}$, $132\text{ s} \le 150\text{ s}$, voice stagger $15000 + 2 \cdot 5000 + 20000 = 45000 \le 45000$, and confirming that tampering with 1 byte of `profiles.json` aborts startup.

### 1.4 RFC 8785 Canonical JSON (JCS), SHA-256 Chain Hasher, Integer Microsecond Clock & Cross-Language Parity Vectors
* **Objective:** Guarantee bit-for-bit identical canonical JSON serialization and SHA-256 hash chaining across the Python server, the Python monitor, and the JavaScript browser verifier.
* **Files to Create:**
  * `api/rhp/crypto.py`
  * `spec/parity_vectors.json`
* **Implementation Specifications:**
  1. Implement `jcs(obj: dict) -> bytes`:
     * Reject any `float` value immediately (`TypeError("Floats prohibited in RHP-1 JCS")`).
     * Permit only `int`, `str`, `bool`, `None` (`null`), `list`, and `dict` with ASCII keys.
     * Serialize with `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")`.
  2. Define the exact `event_core` dictionary layout used for hashing:
     * Keys: `referral_id` (`str`), `seq` (`int`), `event_id` (`str`), `type` (`str`), `epoch` (`int`), `actor_roster_id` (`str | None`), `facility_id` (`str | None`), `channel` (`str`), `proxy` (`bool`), `detail` (`dict`), `secret_hash` (`str | None`, lowercase hex), `client_ts_ms` (`int | None`), `server_ts_us` (`int`).
     * Compute `server_ts_us` in SQL via `(extract(epoch from server_ts)*1000000)::bigint` so Python and PostgreSQL never diverge by 1 microsecond.
     * Compute `hash = hashlib.sha256(prev_hash_bytes + jcs(event_core)).digest()`, where genesis `prev_hash_bytes = b"\x00" * 32`.
  3. Generate `spec/parity_vectors.json` containing 10 chained events (including `None` fields, nested `detail` allowlist keys, and genesis transitions) with expected JCS strings and SHA-256 hex digests.
* **Verification Gate:**
  * Run `pytest tests/test_jcs_parity.py` asserting that `api/rhp/crypto.py` matches all 10 vectors in `spec/parity_vectors.json` and raises `TypeError` on any float input.

### 1.5 Frozen State Machine Table (`transitions.yaml`) & Schema Loader
* **Objective:** Encode the complete RHP-1 state machine as a declarative, human-owned, hash-pinned YAML specification loaded by the server at startup (Closure F19).
* **Files to Create:**
  * `spec/transitions.yaml`
  * `api/rhp/transitions.py`
* **Implementation Specifications:**
  1. Author `spec/transitions.yaml` containing:
     * Handshake states (`CREATED`, `OFFERED`, `ACKNOWLEDGED`, `ACCEPTED`, `COUNTERED`, `ESCALATED_TO_DISPATCHER`, `CANCELLED`, `CLOSED`).
     * Offer statuses (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`, `ACCEPTED`, `DECLINED`, `TIMED_OUT`, `SUPERSEDED`, `ARRIVAL_REJECTED`, `WITHDRAWN`) and open-set definition `{OPEN, ACKED, COUNTERED, SOFT_OPEN}` with max cap `2` (Invariant I12).
     * Transport states (`REQUESTED`, `DISPATCHED`, `EN_ROUTE`, `ARRIVED`, `HANDED_OVER`, `TR_CANCELLED`).
     * All 15 commands (`CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `COUNTER`, `CONFIRM_COUNTER`, `DECLINE`, `TIMEOUT`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`, `TR_UPDATE`, `TR_DESTINATION_CHANGE`, `CANCEL`, `CLOSE`, `REVOKE_GRANT`) with allowed actor roles, required pre-states, state transitions, deadline mutations, and domain error codes (`409 INVALID_TRANSITION`, `409 LEASE_HELD`, `409 LATE_ACCEPT_REJECTED`, `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`, `409 INVALID_TR`).
  2. Implement `api/rhp/transitions.py` to load `spec/transitions.yaml`, verify its SHA-256 against the pinned constant, and expose `TRANSITIONS.lookup(cmd_type, referral, offer)`.
* **Verification Gate (`T-F19`):**
  * Run `pytest tests/test_transitions_table.py` to verify all valid and invalid `(command, hs_state, offer_status)` combinations and confirm the 12-state v7-to-RHP-1 mapping table.

### 1.6 Quint Formal Control-Plane Specification (`rhp1.qnt`), Vacuity Checks & Explicit-State Explorer
* **Objective:** Model-check the control-plane invariants at bounds $F=3, \text{MAXE}=4$ and generate conformance traces before writing command handlers (Closure F6).
* **Files to Create:**
  * `spec/rhp1.qnt`
  * `tests/explore_transitions.py`
  * `vectors/V_01_happy_path.json` ... `vectors/V_28_unclosed_referral.json`
* **Implementation Specifications:**
  1. Save the Quint module in `spec/rhp1.qnt` checking `safety = I2 and I12 and I1m and IDisp and I13` and `transportNeverGated`.
  2. Write `tests/explore_transitions.py` as a deterministic Python breadth-first state explorer over `spec/transitions.yaml` that enumerates all reachable states up to depth $d=12$, verifies Reachability & Exit (`T-F6`: every reachable non-terminal state has a deterministic path to `CLOSED` or `CANCELLED`), and exports the 28 scenario conformance vectors into `vectors/`.
* **Verification Gate (`T-F6`):**
  * Execute `quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000` (passes with 0 violations), run the 4 vacuity checks (`ACCEPTED`, `DISPATCH`, `CLOSED`, `SOFT` reachability must each fail `--invariant "not (...)"` with a witness trace), and run `python tests/explore_transitions.py` confirming 100% exit reachability.

---

## MODULE 2: Identity, PIN Lockout Scope & 10-Step Transactional Command Pipeline (`T0` — Priority 2)

### 2.1 Dual Connection Pools & Advisory Lock Helpers
* **Objective:** Provide dead-simple, deadlock-free database connection management separating main command transactions from autonomous security audit writes.
* **Files to Create:**
  * `api/rhp/db.py`
* **Implementation Specifications:**
  1. Initialize two `psycopg_pool.ConnectionPool` instances in `api/rhp/db.py`:
     * `main_pool`: sized for high concurrency (`min_size=10, max_size=220` to handle 200-way barrier bursts without pool starvation), `READ COMMITTED`.
     * `autonomous_pool`: dedicated pool (`min_size=2, max_size=20`, `autocommit=True`) used exclusively for recording PIN failure increments so outer transaction rollbacks never erase brute-force counters.
  2. Implement helpers:
     * `try_advisory_idem_lock(conn, roster_id: UUID, key: str) -> bool` using `SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))`.
     * `lock_referral_first(conn, referral_id: UUID)` which executes `SELECT * FROM referral WHERE id = %s FOR UPDATE` and immediately calls `SELECT set_config('rhp.locked_referral', %s, true)`.
     * `get_monotone_ts(conn, head_ts)` executing `SELECT GREATEST(clock_timestamp(), %s)`.
* **Verification Gate:**
  * Run a unit test proving that an increment written via `autonomous_pool` persists when an active transaction on `main_pool` rolls back.

### 2.2 Device Enrollment Tickets, Opaque Cookie Sessions & Voice `call_sid` Sessions
* **Objective:** Authenticate web desks, mobile devices, and outbound voice calls without exposing bearer tokens to XSS or allowing unrevoked access (Closure F7).
* **Files to Create:**
  * `api/rhp/auth.py`
* **Implementation Specifications:**
  1. **Enrollment Ticket Flow (`POST /v1/auth/enroll`):**
     * Admin issues a single-use `enrollment_ticket` (random 32-byte token; only `SHA-256(token)` is stored in `enrollment_ticket.token_hash`, valid for 15 minutes).
     * Client redeems ticket with its 32-byte Ed25519 `pubkey` and `platform`; server marks `used_at`, creates a `device` row, and mints an opaque session token.
  2. **Session Management:**
     * Store only `SHA-256(session_token)` in `session.token_hash`.
     * Set `HttpOnly; Secure; SameSite=Strict` cookie (`rhp_session`) for browser/PWA clients (relaxing `Secure` only when `LAN_MODE=1` and `REAL_DATA=0`).
     * For Exotel IVR calls, create a voice session bound to `call_sid` (`device_id IS NULL, call_sid = %s`).
     * Implement `load_session(conn, token_or_call_sid)` checking `revoked_at IS NULL AND expires_at > clock_timestamp()`.
* **Verification Gate:**
  * Run `pytest tests/test_auth_sessions.py` verifying ticket single-use enforcement, expired/revoked session rejection (`401 SESSION_INVALID`), and `call_sid` session binding.

### 2.3 Argon2id PIN Verifier, Autonomous Failure Counter & Per-Session Lockout Scope
* **Objective:** Enforce step-up PIN verification on mutating clinical actions while preventing a rival or attacker from locking out an entire hospital's duty role (Closure F7, Invariant I6).
* **Files to Create:**
  * Update `api/rhp/auth.py`
* **Implementation Specifications:**
  1. Use `argon2-cffi` (`PasswordHasher`) to verify `roster.pin_hash`.
     * Seed production/clinical roles with Argon2id parameters tuned to $\approx 100\text{ ms}$, and seed synthetic `JUDGE_DESK` roles in demo profiles with fast parameters ($t=1, m=8192$) so 200 concurrent judge accepts do not bottleneck on CPU hashing. Also disable PIN entry over plain HTTP when `LAN_MODE=1`.
  2. **Per-Session Lockout Scope (`session.id` or `session.call_sid`):**
     * Before checking the PIN, check `if session.pin_locked_until and session.pin_locked_until > now: raise Reject(429, "PIN_LOCKED")`.
     * On PIN mismatch, use `autonomous_pool` to increment `session.pin_failed`:
       * Failure 1: backoff $0\text{ s}$.
       * Failure 2: `pin_locked_until = clock_timestamp() + interval '5 seconds'`.
       * Failure 3: `pin_locked_until = clock_timestamp() + interval '120 seconds'`, and emit a `PIN_LOCKED` event + dispatcher page on the target referral.
     * Because lockout is scoped to `session.id`, a legitimate clinician on another registered device at the same facility is never locked out by an attacker's session.
* **Verification Gate (`T-F7`):**
  * Run `pytest tests/test_pin_lockout_scope.py`: fail PIN 3 times on Session A (assert `429 PIN_LOCKED` and `pin_failed == 3` persisted despite command rollback), then submit a valid PIN on Session B for the same facility/role and assert `200 OK`.

### 2.4 Role-Command Authorization Matrix, Roster Validity Check & Strict Pydantic Schemas
* **Objective:** Enforce object-level authorization (BOLA prevention), role-slot permissions, and strict input validation (`extra='forbid'`, Closure F9, Invariant I11).
* **Files to Create:**
  * `api/rhp/schemas.py`
* **Implementation Specifications:**
  1. Define Pydantic request models with `model_config = ConfigDict(extra='forbid')` for all commands and a closed `Literal` / enum validator for every `event.detail` payload matching `rhp_allowed(type)` (Invariant I11).
  2. Implement `authorize(conn, referral, offer, session, cmd, ts)`:
     * Verify the actor's `roster` row has `valid_from <= ts AND (valid_to IS NULL OR valid_to > ts)` (Invariant I6).
     * Enforce the Role $\times$ Command matrix:
       * `CREATE`, `CONFIRM_COUNTER`: `CLINICIAN` at `origin_facility_id` (or `DISPATCHER` with `proxy=True`).
       * `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `COUNTER`, `DECLINE`: `NURSE`, `CMO`, `CONSULTANT`, or `JUDGE_DESK` whose `facility_id == offer.facility_id` (or `DISPATCHER` with `proxy=True`).
       * `DISPATCHER_ASSIGN`: `DISPATCHER`.
       * `ARRIVAL_REJECTED`, `TR_UPDATE(ARRIVED|HANDED_OVER)`: receiving role at `lease_facility_id` or `EMT` / `DISPATCHER`.
       * `CLOSE`: receiving role at `lease_facility_id` or `DISPATCHER` or `SYSTEM`.
* **Verification Gate (`T-I6`, `T-I6b`, `T-F9`):**
  * Run `pytest tests/test_authz_matrix.py` verifying that cross-facility accepts return `403`, extra JSON fields return `422`, and fuzzing `event.detail` with free-text patient names is blocked by both Pydantic and PostgreSQL `rhp_detail_ok`.

### 2.5 The 10-Step `apply_command()` Transactional Pipeline
* **Objective:** Implement the single serialized command execution pipeline enforcing total lock order (`referral` $\rightarrow$ `offer` $\rightarrow$ `deadline` $\rightarrow$ `outbox`), idempotency replay, optimistic fencing, savepoint rejection logging, and hash-chained event writing (Closures F1, F11, F14).
* **Files to Create:**
  * `api/rhp/pipeline.py`
* **Implementation Specifications:**
  1. Implement `apply_command(conn, cmd, session_token, idem_key)` following the exact 10-step contract:
     * **Step 1 (Idempotency before referral lock):** Require `idem_key` (`8..80` chars, else `422 MISSING_IDEMPOTENCY_KEY`). Compute `req_hash = sha256(jcs(cmd.body_for_hash()))`. Acquire `try_advisory_idem_lock(conn, actor_id, idem_key)` (if false $\rightarrow$ `409 DUPLICATE_IN_FLIGHT`). Check `idempotency` table:
       * If row exists and `expires_at > clock_timestamp()`:
         * If `request_hash != req_hash` $\rightarrow$ `422 KEY_REUSED_DIFFERENT_PAYLOAD`.
         * If `status == 'DONE'` $\rightarrow$ return stored `(http_status, response)` immediately (replaying both `200` and deterministic `409`/`412`/`422` rejections).
       * Upsert `idempotency` with `status = 'IN_FLIGHT', expires_at = clock_timestamp() + interval '48 hours'`.
       * Check if `cmd.event_id` already exists in `event` under a different key $\rightarrow$ `409 DUPLICATE_EVENT_ID`.
     * **Step 2 (Session):** Validate session via `load_session`.
     * **Step 3 (PIN):** If `cmd.needs_pin`, verify PIN via `verify_pin_or_lockout`.
     * **Step 4 (Lock Referral First + Monotone Clock):**
       * For `CREATE`, pre-generate `referral_id`, call `set_config('rhp.locked_referral', str(referral_id), true)`, and set `ts = clock_timestamp()`.
       * For all other commands, `SELECT * FROM referral WHERE id = %s FOR UPDATE`, call `set_config('rhp.locked_referral', str(r.id), true)`, and set `ts = GREATEST(clock_timestamp(), r.head_ts)` (Invariant I16).
       * Execute `SAVEPOINT sp_cmd`.
     * **Step 5 (Authority & Fencing):** Run `authorize(...)` and check `cmd.expected_version == r.version` and (if present) `cmd.expected_epoch == r.lease_epoch`; on mismatch raise `Reject(412, "STALE_PRECONDITION")` (Invariant I8).
     * **Step 6 (Transition Guard & Forward Lock Order):** Lock offers (`SELECT * FROM offer WHERE referral_id = %s ORDER BY id FOR UPDATE`) and deadlines (`SELECT * FROM deadline WHERE referral_id = %s ORDER BY id FOR UPDATE`). Lookup transition in `TRANSITIONS`.
     * **Step 7 (Staleness Check):** Verify confirmation TTLs (Invariant I15) and offer soft-open validity.
     * **Step 8 (Apply State & Deadlines):** Mutate `referral`, `offer`, `payload_grant`, and `deadline` rows.
     * **Step 9 (Event Hash Chain & Outbox):** Compute `seq = r.head_seq + 1`, `hash = sha256(r.head_hash + jcs(core))`, `INSERT INTO event`, update `referral.head_seq / head_hash / head_ts / version`, and `INSERT INTO outbox` last.
     * **Step 10 (Finalize):** Update `idempotency` to `status = 'DONE'`, store `http_status` and `response`, and commit.
     * **Savepoint Rejection Handler:** On `Reject(code, reason)`, execute `ROLLBACK TO SAVEPOINT sp_cmd` (keeping the referral lock and Step 1 idempotency row), `INSERT INTO rejected_command`, mark `idempotency` as `DONE` with `(code, reason)`, and commit.
* **Verification Gate (`T-I8`, `T-I14`, `T-I16`):**
  * Run `pytest tests/test_pipeline_core.py` verifying that direct table writes without `rhp.locked_referral` raise `I14_LOCK_NOT_HELD`, stale `expected_version` returns `412` and logs to `rejected_command`, and replaying the same `Idempotency-Key` returns the exact stored `412` response.

---

## MODULE 3: Core Handshake Commands, Single-Owner Lease & Escalation Engine (`T0` — Priority 3)

### 3.1 `CREATE` Command: Chain Snapshot, Mode Selection, Initial Offers, Grants & Deadlines
* **Objective:** Atomically create a referral, snapshot its approved catchment chain, open initial offer(s), grant payload access, and arm ACK and notice deadlines so no referral is ever silent (Invariants I1, I7).
* **Files to Create:**
  * `api/rhp/commands/create.py`
* **Implementation Specifications:**
  1. Load the approved `catchment_chain` for `(origin_facility_id, need_class)`. Allow the clinician to reorder or skip targets from that approved set, but reject any target not in `catchment_chain` (`I7_NOT_IN_CHAIN`). Truncate chain to profile max $F$.
  2. Require `mgso4_status` in `('GIVEN', 'NONE_GIVEN', 'UNKNOWN')`. Never reject or delay `CREATE` when `mgso4_status == 'UNKNOWN'` (Fix D1).
  3. Generate unique 9-character Crockford Base32 + mod-37 `paper_code`.
  4. If `chain` is non-empty:
     * Set `hs_state = 'OFFERED'`, `tr_state = 'REQUESTED'`.
     * In `SEQUENTIAL` mode, open 1 offer (`chain[0]`, `step=1`, `status='OPEN'`, `open_offers=1`).
     * In `PARALLEL2` mode, open up to 2 offers (`chain[0]` and `chain[1]`, `open_offers=2`).
     * Insert `payload_grant` rows for `origin_facility_id` and each offered facility.
     * Insert `deadline` rows for each open offer: `ACK` (due at `ts + A`), `NOTICE_VOICE` (due at `ts + A/4`), and `NOTICE_PROXY` (due at `ts + 3A/4`).
     * Emit `REFERRAL_CREATED` and `OFFER_CREATED` events + `outbox` rows (`SSE`, `FCM`).
  5. If `chain` is empty:
     * Set `hs_state = 'ESCALATED_TO_DISPATCHER'`, `open_offers = 0`, insert `DISPATCH_ACTION` deadline (`ts + dispatch_action_ms`), and emit `REFERRAL_CREATED` + `ESCALATED_TO_DISPATCHER`.
* **Verification Gate (`T-I1`, `T-I7`):**
  * Run `pytest tests/test_cmd_create.py` verifying `SEQUENTIAL`, `PARALLEL2`, and empty-chain creation, confirming that the deferred `i1_pending_deadline` trigger passes at `COMMIT`, and confirming that an unapproved target facility raises `I7_NOT_IN_CHAIN`.

### 3.2 `ACK` & `RESOURCE_CONFIRM` Commands: Live Capability Confirmation TTL & Soft-Open Expiry
* **Objective:** Record human acknowledgement of an offer, transition deadlines from `ACK` to `DECISION`, expire any prior `SOFT_OPEN` offer, and record time-bounded capability confirmations.
* **Files to Create:**
  * `api/rhp/commands/ack_confirm.py`
* **Implementation Specifications:**
  1. **`ACK` Command:**
     * Require target offer `status == 'OPEN'`.
     * Set offer `status = 'ACKED'`, `acked_at = ts`, `acked_by = session.roster_id`.
     * Mark the offer's `ACK`, `NOTICE_VOICE`, and `NOTICE_PROXY` deadlines as `'DONE'`.
     * Insert a `DECISION` deadline due at `ts + D`.
     * **Soft-Open Closure Rule (F13):** If offer at `step - 1` is currently `'SOFT_OPEN'`, transition that prior offer to `'TIMED_OUT'`, decrement `referral.open_offers`, revoke its `payload_grant`, and emit `OFFER_SOFT_EXPIRED` + `GRANT_REVOKED`.
     * Update `referral.hs_state` to reflect the lead offer (`ACKNOWLEDGED` if no higher-priority state exists) and emit `OFFER_ACKED`.
  2. **`RESOURCE_CONFIRM` Command:**
     * Require offer `status in ('OPEN', 'ACKED', 'SOFT_OPEN')` and `capability` in `need_class_requirement` for `referral.need_class`.
     * Upsert `offer_resource_confirmation(offer_id, capability, confirmed_by, confirmed_at=ts, expires_at=ts + profile.confirm_ttl)`.
     * Emit `RESOURCE_CONFIRMED` with `detail={"capability": cap}`.
* **Verification Gate:**
  * Run `pytest tests/test_cmd_ack_confirm.py` verifying that `ACK` cancels pending notice rungs, arms `DECISION`, and closes a predecessor `SOFT_OPEN` offer.

### 3.3 `ACCEPT` Command: Single-Owner Lease Arbitration, Fencing Epoch & I15 Staleness Check
* **Objective:** Grant an exclusive single-owner lease to exactly one facility when all required capabilities are confirmed and unexpired, fencing out all competing or late accepts (Invariants I2, I8, I15, Closure F12).
* **Files to Create:**
  * `api/rhp/commands/accept.py`
* **Implementation Specifications:**
  1. Check lease availability:
     * If `referral.lease_offer_id IS NOT NULL` $\rightarrow$ raise `Reject(409, "LEASE_HELD")`.
     * If `offer.status in ('TIMED_OUT', 'SUPERSEDED')` $\rightarrow$ raise `Reject(409, "LATE_ACCEPT_REJECTED")`.
     * Require `offer.status in ('OPEN', 'ACKED', 'SOFT_OPEN')`.
  2. **Invariant I15 (Resource Confirmation Staleness Check):**
     * Query required capabilities from `need_class_requirement WHERE need_class = referral.need_class`.
     * Query `offer_resource_confirmation WHERE offer_id = offer.id`.
     * If any required capability is missing or has `expires_at <= ts` $\rightarrow$ raise `Reject(409, "STALE_CONFIRMATION_RECONFIRM_REQUIRED")`.
  3. **Grant Lease:**
     * Update winning `offer.status = 'ACCEPTED'`, `decided_at = ts` (protected by `one_lease` unique index).
     * Increment `referral.lease_epoch += 1`, set `referral.lease_offer_id = offer.id`, `referral.lease_facility_id = offer.facility_id`, `referral.tr_facility_id = offer.facility_id`, `referral.hs_state = 'ACCEPTED'`, `referral.open_offers = 0`.
     * For every other offer on this referral in `('OPEN', 'ACKED', 'COUNTERED', 'SOFT_OPEN')`: set `status = 'SUPERSEDED'`, revoke its `payload_grant`, and emit `GRANT_REVOKED`.
     * Cancel all pending `ACK`, `DECISION`, `COUNTER_CONFIRM`, and `NOTICE_*` deadlines; insert a `HANDOVER` deadline due at `ts + profile.H`.
     * Emit `OFFER_ACCEPTED` and `LEASE_GRANTED` (`detail={"facility": str(offer.facility_id), "epoch": referral.lease_epoch}`).
* **Verification Gate (`T-C3`, `T-F12`, `T-I15`):**
  * Run `pytest tests/test_cmd_accept.py` verifying single-lease grant, `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` when `ts >= expires_at`, and `409 LATE_ACCEPT_REJECTED` when accepting after a successor facility has ACKed.

### 3.4 `DECLINE` Command & Deterministic `advance()` Escalation Engine
* **Objective:** Record structured declines with optional redirect suggestions and deterministically advance along the catchment chain without loops or $>2$ open offers (Invariants I7, I9, I12, Closure F13).
* **Files to Create:**
  * `api/rhp/commands/decline_advance.py`
* **Implementation Specifications:**
  1. **`DECLINE` Command:**
     * Require `offer.status in ('OPEN', 'ACKED', 'SOFT_OPEN', 'COUNTERED')`.
     * Validate `decline_reason` (`NO_OT`, `NO_NICU`, `NO_ANAESTHETIST`, `NO_BLOOD`, `NO_PAEDIATRICIAN`, `AT_CAPACITY`).
     * Set `offer.status = 'DECLINED'`, `offer.decline_reason = reason`, `offer.decided_at = ts`, decrement `referral.open_offers`, cancel the offer's pending deadlines, revoke its `payload_grant`, and emit `OFFER_DECLINED` (with optional redirect `facility` UUID in `detail`, displayed as an advisory and never auto-followed) + `GRANT_REVOKED`.
     * Invoke `advance(conn, referral, offers, ts, mode_reason="DECLINE")`.
  2. **`advance()` Escalation Function:**
     * Find the next facility in `referral.chain` that has no row in `offer` for this referral (enforcing Invariant I9 `UNIQUE(referral_id, facility_id)`).
     * If a next facility exists:
       * If `referral.open_offers == 2` because an older offer `k-1` is `SOFT_OPEN`, transition `k-1` to `TIMED_OUT` first (`open_offers` becomes `1`, revoke grant) so opening the new offer keeps `open_offers <= 2` (Invariant I12).
       * Insert new `offer` (`status='OPEN'`, `step = ladder_cursor + 1`, `source='CHAIN'`), increment `ladder_cursor` and `open_offers`, grant payload access, arm `ACK` + `NOTICE_VOICE` + `NOTICE_PROXY` deadlines, update `referral.hs_state` to the lead offer state, and emit `OFFER_CREATED`.
     * If no unused facility remains in `referral.chain` and `referral.open_offers == 0`:
       * Transition `referral.hs_state = 'ESCALATED_TO_DISPATCHER'`, arm `DISPATCH_ACTION` deadline, and emit `ESCALATED_TO_DISPATCHER`.
* **Verification Gate (`T-F13`, `T-I9`):**
  * Run `pytest tests/test_cmd_decline_advance.py` walking a 3-facility chain through declines to `ESCALATED_TO_DISPATCHER` and asserting `open_offers` never exceeds 2.

### 3.5 `COUNTER` & `CONFIRM_COUNTER` Commands: Bounded 2-Round Negotiation
* **Objective:** Support conditional counter-offers (up to 2 rounds) inside the facility's decision window $D$ without blocking parallel offers (Closure F13).
* **Files to Create:**
  * `api/rhp/commands/counter.py`
* **Implementation Specifications:**
  1. **`COUNTER` Command:**
     * Require `offer.status in ('OPEN', 'ACKED')` and `offer.counter_round < 2`.
     * Set `offer.status = 'COUNTERED'`, `offer.counter_round += 1`, `offer.counter_mask = cmd.mask`.
     * Cancel pending `ACK`/`DECISION` deadlines for this offer and insert a `COUNTER_CONFIRM` deadline due at `min(ts + profile.C, decision_deadline_due_at)` so counters never extend the facility's decision window $D$.
     * Update `referral.hs_state` (lead offer rule) and emit `OFFER_COUNTERED`.
  2. **`CONFIRM_COUNTER` Command (by referring `CLINICIAN`):**
     * Require `offer.status == 'COUNTERED'`.
     * If `cmd.confirmed == True`: execute the `ACCEPT` lease-grant path (including the Invariant I15 resource confirmation expiry check and competing-offer check; if another offer already won the lease, raise `409 LEASE_HELD`).
     * If `cmd.confirmed == False`: set `offer.status = 'DECLINED'`, decrement `open_offers`, revoke grant, emit `COUNTER_RESOLVED(confirmed=False)`, and call `advance()`.
* **Verification Gate (`T-C4`, `V-COUNTER-LOOP`):**
  * Run `pytest tests/test_cmd_counter.py` verifying that a 3rd counter attempt returns `409`, and that when Offer 1 is `COUNTERED` and Offer 2 is `OPEN`, whichever of `CONFIRM_COUNTER(True)` or Offer 2 `ACCEPT` locks the referral first wins the lease while the loser gets `409 LEASE_HELD`.

### 3.6 `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`, `CANCEL`, `CLOSE` & `REVOKE_GRANT` Commands
* **Objective:** Complete all lifecycle, exception, and terminal closure commands with the 9-outcome taxonomy (Closure F6).
* **Files to Create:**
  * `api/rhp/commands/lifecycle.py`
* **Implementation Specifications:**
  1. **`ARRIVAL_REJECTED`:** Require `referral.hs_state == 'ACCEPTED'`. Mark lease offer `status = 'ARRIVAL_REJECTED'`, increment `referral.lease_epoch += 1`, clear `lease_offer_id` and `lease_facility_id`, revoke grant, cancel `HANDOVER` deadline, emit `ARRIVAL_REJECTED` + `LEASE_REVOKED`, and call `advance()` to escalate to the next unused facility or dispatcher.
  2. **`DISPATCHER_ASSIGN`:** Allowed when `hs_state == 'ESCALATED_TO_DISPATCHER'` (or live override with mandatory `reason` enum). Creates or updates an offer for the target facility with `source = 'DISPATCHER'`, `status = 'ACCEPTED'`, increments `lease_epoch += 1`, sets `proxy = True`, supersedes any open offers, arms `HANDOVER` deadline, and emits `DISPATCHER_ASSIGNED` + `LEASE_GRANTED`.
  3. **`CANCEL`:** Allowed in any non-terminal `hs_state`. Requires `outcome` in `('PATIENT_REFUSED', 'TRANSPORT_CANCELLED', 'DELIVERED_EN_ROUTE', 'DETERIORATED_OR_DIED_PRE_HANDOVER')`. Marks open/accepted offers `WITHDRAWN`, cancels all pending deadlines, revokes grants, sets `hs_state = 'CANCELLED'`, `closed_at = ts`, and emits `CANCELLED`.
  4. **`CLOSE`:** Allowed in `ACCEPTED` or `ESCALATED_TO_DISPATCHER`. Validates `outcome` in the 9-outcome taxonomy (`ADMITTED_STABLE`, `ADMITTED_CRITICAL`, `DELIVERED_AT_RECEIVER`, `DELIVERED_EN_ROUTE`, `PATIENT_REFUSED`, `TRANSPORT_CANCELLED`, `DETERIORATED_OR_DIED_PRE_HANDOVER`, `REDIRECTED_ON_ARRIVAL`, `UNKNOWN_COUNTER_REFERRAL`, requiring `tr_state == 'HANDED_OVER'` for `ADMITTED_STABLE`, `ADMITTED_CRITICAL`, or `DELIVERED_AT_RECEIVER`, else `422 OUTCOME_REQUIRED`). Cancels pending deadlines, revokes active grants, schedules payload expiry, sets `hs_state = 'CLOSED'`, `closed_at = ts`, and emits `CLOSED`.
* **Verification Gate:**
  * Run `pytest tests/test_cmd_lifecycle.py` covering `ARRIVAL_REJECTED` re-escalation, dispatcher assignment, and terminal outcome constraints.

---

## MODULE 4: Independent Runtime Monitor, 200-Way Race & Safe `BROKEN_BUILD` (`T0` Proof Gate — Priority 4)

### 4.1 Independent Runtime Monitor (`monitor/`)
* **Objective:** Continuously re-derive every referral's state from the raw event log using an independent implementation by Person B and check Invariants I1–I16 against the database (Closure F17).
* **Files to Create:**
  * `monitor/monitor.py`
  * `monitor/Dockerfile`
* **Implementation Specifications:**
  1. `monitor/monitor.py` must import **zero modules** from `api/`. It connects to PostgreSQL as `rhp_monitor` in `REPEATABLE READ READ ONLY` isolation using a server-side cursor (`with c.cursor(name="snap") as cur:`).
  2. Implement `fold_events(events, roster_map, referral_row, offers_rows)` checking:
     * **I1:** No non-terminal referral lacks a `PENDING` deadline, and no `PENDING` deadline has `clock_timestamp() - due_at > tau_ms` ($\tau = 2 \cdot \text{poll\_interval} + 2000\text{ ms}$).
     * **I2:** Count of `ACCEPTED` offers per referral $\le 1$; `LEASE_GRANTED` never occurs while a lease is already active; `epoch` strictly increases on every `LEASE_GRANTED` / `LEASE_REVOKED`.
     * **I3:** `rejected_command` contains no `TR_UPDATE` rejection caused by `hs_state` (only invalid `tr_state` transitions or terminal referrals).
     * **I4:** `seq` starts at 1 and increments by 1 with no gaps; `event_id` is globally unique.
     * **I5:** Recompute `SHA-256(prev_hash || jcs(core))` for every event from genesis `0x00*32`; verify terminal referrals have `outcome IS NOT NULL`.
     * **I6:** Every `OFFER_ACCEPTED`, `OFFER_COUNTERED`, `OFFER_DECLINED` event has an `actor_roster_id` valid at `server_ts` in `roster` or has `proxy == True`.
     * **I7:** Every offer with `source == 'CHAIN'` has `facility_id` inside `referral.chain`.
     * **I8:** No applied event has `epoch < referral_epoch_at_step`.
     * **I9:** No `facility_id` appears more than once in `offer` for the same `referral_id`.
     * **I11:** Every `event.detail` key and value matches the closed allowlist.
     * **I12:** Count of offers in `('OPEN', 'ACKED', 'COUNTERED', 'SOFT_OPEN')` $\le 2$ at every fold step and in `referral.open_offers`.
     * **I15:** Every `OFFER_ACCEPTED` event had unexpired `offer_resource_confirmation` rows at `server_ts`.
     * **I16:** `server_ts_us` is monotonically non-decreasing across `seq`.
     * **Differential Check:** Derived `(head_seq, head_hash, lease_epoch, lease_facility)` from the event fold must equal the stored columns on `referral` (`DIFF_HEAD`, `DIFF_EPOCH`, `DIFF_LEASE`).
  3. Expose HTTP `/metrics` and `/status` on port `8001` returning invariant counters, violation list, and monitor heartbeat updates every 1 second.
* **Verification Gate:**
  * Start `monitor` against seeded referrals and run `pytest tests/test_monitor_fold.py` confirming 0 violations on valid flows.

### 4.2 The 200-Way Concurrency Barrier (`race200`) & Idempotency Edge-Case Suite
* **Objective:** Prove under real concurrent load that 200 simultaneous `ACCEPT` requests across competing hospital desks yield exactly 1 lease, 0 deadlocks, and gap-free event sequences (Closures F1, F14).
* **Files to Create:**
  * `tests/test_race200.py`
  * `tests/test_idempotency_matrix.py`
* **Implementation Specifications:**
  1. In `tests/test_race200.py`:
     * Create a `PARALLEL2` referral with 2 open offers (`OFFER[0]`, `OFFER[1]`), pre-confirm required capabilities, and spin up 200 `httpx.AsyncClient` coroutines synchronized on an `asyncio.Barrier(200)`.
     * Fire all 200 `POST /v1/offers/{OFFER[i % 2]}/accept` requests simultaneously.
     * Assert:
       * `sum(r.status_code == 200 for r in rs) == 1`
       * `all(r.status_code in (200, 409, 412, 422, 429) for r in rs)`
       * `SELECT count(*) FROM offer WHERE referral_id = %s AND status = 'ACCEPTED'` equals `1`
       * `SELECT max(seq) - count(*) FROM event WHERE referral_id = %s` equals `0`
       * PostgreSQL `pg_stat_database.deadlocks` delta equals `0`
       * Independent Runtime Monitor reports `0` violations.
  2. In `tests/test_idempotency_matrix.py`, test all 8 rows of the F14 Idempotency Matrix (success replay, domain rejection replay, key reuse with different payload $\rightarrow 422$, concurrent in-flight duplicate $\rightarrow 409$, crash before commit $\rightarrow$ clean re-execution, expired key $>48\text{ h}$ with same `event_id` $\rightarrow 409$, missing key $\rightarrow 422$, same `event_id` with new key $\rightarrow 409`).
* **Verification Gate (`T-C1`, `T-F1`, `T-F14`):**
  * Execute `pytest tests/test_race200.py tests/test_idempotency_matrix.py` 5 consecutive times with 100% pass rate.

### 4.3 Safe `BROKEN_BUILD` Isolation (`rhp_scratch_broken` DB & Double-Lease Fault Injection)
* **Objective:** Provide a live, isolated demonstration proving the Independent Runtime Monitor catches a double-lease bug within 2 seconds without ever risking the main database (Closure F20).
* **Files to Create:**
  * `scripts/toggle_broken_build.sh`
  * Update `api/rhp/commands/accept.py` (guarded by `config.BROKEN_BUILD == 1`)
* **Implementation Specifications:**
  1. When `BROKEN_BUILD == 1` (which `config.py` guarantees can only boot when connected to `rhp_scratch_broken` with `REAL_DATA == 0`):
     * In `accept.py`, skip the `SELECT ... FOR UPDATE` referral lock wait and skip the `if referral.lease_offer_id is not None` check (while `rhp_scratch_broken` also lacks the `one_lease` unique index).
     * `/mode` endpoint returns `{"broken_build": true, "banner": "BROKEN BUILD — SCRATCH DB"}`.
  2. When two competing desks press Accept in `BROKEN_BUILD=1`, both offers become `ACCEPTED`, and `monitor/monitor.py` immediately flags `I2: DOUBLE_LEASE_VIOLATION`.
* **Verification Gate (`T-F20`):**
  * Run `pytest tests/test_broken_build.py` verifying that switching to `BROKEN_BUILD=1` on `rhp_scratch_broken` causes a 2-way race to grant 2 leases and turns the monitor red within $\le 2\text{ s}$, and switching back to `BROKEN_BUILD=0` restores green status.

### 4.4 Six-Part Mutation Test Suite (`M1`–`M6`) & Conformance Vector Runner
* **Objective:** Prove there are no common-mode blind spots between the specification, the server, and the independent monitor (Closure F17).
* **Files to Create:**
  * `tests/test_mutations.py`
  * `tests/test_conformance_vectors.py`
* **Implementation Specifications:**
  1. Implement `tests/test_mutations.py` exercising all 6 mutations via monkeypatch/scratch toggles and asserting the named detector trips:
     * **M1:** Disable `expected_epoch` fencing $\rightarrow$ tripped by vector `V-STALE-EPOCH` + Monitor `I8`.
     * **M2:** Disable `FOR UPDATE` + drop `one_lease` on scratch DB $\rightarrow$ tripped by `race200` + Monitor `I2`.
     * **M3:** Make poller hold `deadline` row lock while calling `apply_command` $\rightarrow$ tripped by `T-F1` deadlock detector + `I14`.
     * **M4:** Remove `nxt` cap guard in Quint spec $\rightarrow$ tripped by `quint run` `I12` counterexample.
     * **M5:** Write `prev_hash` as all zeros on event append $\rightarrow$ tripped by Monitor `I5` + Browser Verifier `kind=PREV`.
     * **M6:** Ignore `expires_at` on `offer_resource_confirmation` during `ACCEPT` $\rightarrow$ tripped by vector `V-STALE-CONFIRM` + Monitor `I15`.
  2. Implement `tests/test_conformance_vectors.py` replaying all 28 scenario vectors in `vectors/` against the live FastAPI + PostgreSQL stack.
* **Verification Gate (`T-F17`):**
  * Run `pytest tests/test_mutations.py tests/test_conformance_vectors.py` with 100% pass rate.

---

## MODULE 5: Stateless Poller, Outbox Relay, Notice Ladder & Authorized SSE Hub (`T0` Liveness — Priority 5)

### 5.1 Two-Phase Stateless Deadline Poller (`SKIP LOCKED` Claim + `TIMEOUT` Command Execution)
* **Objective:** Execute overdue deadlines without holding locks across transactions or deadlocking against live user commands (Closure F1).
* **Files to Create:**
  * `api/rhp/commands/timeout.py`
  * `api/rhp/poller.py`
* **Implementation Specifications:**
  1. **Poller Phase 1 (Single Committed Claim Statement in `poller.py`):**
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
     RETURNING id, referral_id, offer_id, kind, step, epoch;
     ```
     Commit Phase 1 immediately. Zero referral locks are held during Phase 1.
  2. **Poller Phase 2 (`apply_command(TimeoutCmd)` in `timeout.py`):**
     * For each claimed row, invoke `apply_command` with `SYSTEM_SESSION` and `idem_key = f"timeout:{d.id}"`.
     * Under the Step 4 referral lock, re-read the `deadline` row: if `status != 'PENDING'` or `epoch != d.epoch`, mark/leave it and return `200 no-op` (making double-firing 100% idempotent).
     * Handle `TIMEOUT` by `deadline.kind`:
       * `ACK` expiry:
         * If offer is still `'OPEN'` (silent): in `SEQUENTIAL` mode, transition offer to `'SOFT_OPEN'` and call `advance()` to open `step + 1` (keeping `open_offers <= 2`); in `PARALLEL2` mode, transition offer to `'TIMED_OUT'`, revoke grant, and call `advance()`.
         * If offer is `'ACKED'` (human saw it, deciding): emit `ADVISORY_PREWARM` to the next facility in `referral.chain` (not an offer, carries no deadline, does not increment `open_offers`).
       * `DECISION` or `COUNTER_CONFIRM` expiry:
         * In `SEQUENTIAL` mode, transition offer to `'SOFT_OPEN'` and call `advance()`; in `PARALLEL2` mode or if last target in chain, transition offer to `'TIMED_OUT'`, revoke grant, and call `advance()`.
  3. Set poll interval to `250ms` in `DEMO_FAST` (so 750ms notice rungs and the 24s $T_{\max}$ bound execute with sub-second precision) and `1000ms` in pilot profiles.
* **Verification Gate (`T-C2`, `T-C6`, `T-T1`, `T-T4`):**
  * Run `pytest tests/test_poller_liveness.py`: verify that in `DEMO_FAST` a completely silent 3-facility referral escalates through all 3 facilities to `ESCALATED_TO_DISPATCHER` in $\le 25\text{ s}$, and that running `race200` simultaneously with an active poller produces `0` deadlocks.

### 5.2 Unified Intra-Facility Notice Ladder ($0, A/4, 3A/4$ Rungs) & Overdue Re-Arming
* **Objective:** Escalate inside the receiving facility (Duty Nurse $\rightarrow$ CMO $\rightarrow$ Consultant/Dispatcher Proxy) within the ACK window $A$ and handle overdue handovers and closures (Closures F2, F6).
* **Files to Create:**
  * Update `api/rhp/commands/timeout.py`
* **Implementation Specifications:**
  1. When `TIMEOUT` processes `kind == 'NOTICE_VOICE'` (due at $A/4$):
     * If the offer is still `'OPEN'`, mark the deadline `'DONE'`, emit `NOTICE_SENT(channel='VOICE', rung=1, slot=i)`, and insert `outbox` rows (`channel='VOICE'`) for the facility's rostered duty slots (staggered by $\delta$).
  2. When `TIMEOUT` processes `kind == 'NOTICE_PROXY'` (due at $3A/4$):
     * If the offer is still `'OPEN'`, mark the deadline `'DONE'`, emit `NOTICE_SENT(channel='DISPATCHER_PROXY', rung=2, slot=1)`, and insert an `outbox` row (`channel='PROXY_PAGE'`) paging the dispatcher to phone-assist.
  3. When `TIMEOUT` processes `HANDOVER` or `DISPATCH_ACTION`:
     * Emit `HANDOVER_OVERDUE` (or re-page dispatcher) and insert a new re-armed deadline row so Invariant I1 (`i1_pending_deadline`) remains satisfied.
  4. **Two-Stage `CLOSURE` Timeout (Closure F6):**
     * When `TR_UPDATE(HANDED_OVER)` commits, arm a `CLOSURE` deadline.
     * On first `CLOSURE` expiry: emit `CLOSURE_OVERDUE` to the dispatcher/district view and re-arm `CLOSURE` once (`step = 2`).
     * On second `CLOSURE` expiry (`step == 2`): automatically execute `CLOSE` with `outcome = 'UNKNOWN_COUNTER_REFERRAL'`, `proxy = True`, `actor = SYSTEM`.
* **Verification Gate:**
  * Run `pytest tests/test_notice_ladder_and_closure.py` verifying that an early `ACK` cancels `NOTICE_VOICE` and `NOTICE_PROXY`, and that an unclosed handed-over referral auto-closes with `UNKNOWN_COUNTER_REFERRAL` after the 2nd `CLOSURE` expiry.

### 5.3 Visibility-Timeout Outbox Relay & Pluggable Channel Adapters
* **Objective:** Deliver events from the `outbox` table with at-least-once guarantees and automatic crash recovery (30s visibility timeout).
* **Files to Create:**
  * `api/rhp/relay.py`
* **Implementation Specifications:**
  1. Claim ready outbox rows in a single statement:
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
  2. Dispatch each claimed row to its channel adapter (`SSE`, `FCM`, `VOICE`, `SMS`, `PROXY_PAGE`).
  3. On success, `UPDATE outbox SET status = 'SENT' WHERE id = %s`.
  4. If `attempts > 8`, `UPDATE outbox SET status = 'DEAD' WHERE id = %s` and insert a dispatcher alert.
* **Verification Gate (`T-F3b`):**
  * Simulate an adapter crash mid-flight, verify the row becomes eligible again after `visible_after`, and verify `attempts > 8` transitions the row to `DEAD`.

### 5.4 Per-Frame Authorized SSE Hub (`Last-Event-ID` Resume & `GRANT_REVOKED` Stream Stripping)
* **Objective:** Push real-time state updates to web desks over HTTP/2 SSE while dynamically stripping clinical payloads the instant a facility's `payload_grant` is revoked (Closure F10, Invariant I10).
* **Files to Create:**
  * `api/rhp/sse.py`
* **Implementation Specifications:**
  1. Authenticate `GET /v1/stream` via the `rhp_session` cookie. Support `Last-Event-ID` header (`outbox.id`) to replay any missed frames on reconnect.
  2. Emit a `: heartbeat\n\n` frame every 15 seconds and re-verify session validity on every heartbeat.
  3. **Per-Frame Grant Evaluation (Invariant I10):**
     * Before serializing any SSE frame for a subscriber `(facility_id, role_slot)`, query whether an active `payload_grant` (`revoked_at IS NULL`) exists for `(referral_id, facility_id)`.
     * If no active grant exists, strip all clinical payload fields before sending.
     * When `GRANT_REVOKED` is emitted for a facility, immediately push a `event: GRANT_REVOKED\ndata: {"referral_id": ...}\n\n` control frame so the receiving browser wipes its DOM state.
* **Verification Gate (`T-F10`, `T-N3`):**
  * Run `pytest tests/test_sse_revoke.py`: subscribe as Hospital B, receive an offer with clinical payload, decline the offer, and assert that Hospital B immediately receives `GRANT_REVOKED` and zero clinical fields on subsequent events for that referral.

### 5.5 Component Heartbeats, Chrony Slew-Only NTP Offset Monitor & Clock-Step Guard
* **Objective:** Track liveness of all background workers and bound clock drift (Closure F11, Invariant I16).
* **Files to Create:**
  * Update `api/rhp/poller.py`, `api/rhp/relay.py`, `monitor/monitor.py`, `witness/signer.py`
* **Implementation Specifications:**
  1. Every 5 seconds, `POLLER`, `RELAY`, `MONITOR`, and `WITNESS` upsert their row in `heartbeat(subject_kind, subject_id, last_seen=clock_timestamp(), ntp_offset_ms=...)`.
  2. Expose heartbeat freshness in `/healthz` and `/metrics`: if any component's `clock_timestamp() - last_seen > interval '15 seconds'` or `abs(ntp_offset_ms) > 2000`, set `liveness_status = "AMBER"` and emit an operator page.
* **Verification Gate (`T-F11`):**
  * Run `pytest tests/test_clock_and_heartbeats.py` verifying that `GREATEST(clock_timestamp(), head_ts)` keeps `server_ts` strictly non-decreasing during a simulated backward clock step and triggers the $>2\text{ s}$ offset alarm.

---

## MODULE 6: Cryptographic Witness Signer, Merkle Checkpoints & Pure-JS Verifier (`T0` Integrity — Priority 6)

### 6.1 Separate-OS-User Witness Signer (`witness/`): 5-Second Binary Merkle Tree & C2SP Signed Notes
* **Objective:** Produce signed, tamper-evident Merkle checkpoints over all referrals every 5 seconds using an isolated OS user and database role (Closure F8, Invariant I5).
* **Files to Create:**
  * `witness/signer.py`
  * `witness/Dockerfile`
* **Implementation Specifications:**
  1. Run `witness/signer.py` as UID `1002` (`rhp-sign`) with its Ed25519 private key mounted at `0400` permissions, connecting via `rhp_witness`.
  2. Every 5 seconds, open a `REPEATABLE READ READ ONLY` transaction and query `SELECT id, head_seq, head_hash FROM referral ORDER BY id ASC`.
  3. Build a binary Merkle tree:
     * **Leaf:** $\text{leaf}_i = \text{SHA-256}(\texttt{0x00} \parallel \text{referral\_id\_bytes}_{16} \parallel \text{head\_seq\_be}_{8} \parallel \text{head\_hash}_{32})$.
     * **Internal Node:** $\text{node} = \text{SHA-256}(\texttt{0x01} \parallel \text{left}_{32} \parallel \text{right}_{32})$; promote an odd trailing node unchanged.
     * For an empty tree (`tree_size == 0`), `root_hash = b"\x00" * 32`.
  4. Format the C2SP-style note: `f"rhp1/{deployment}\n{tree_size}\n{b64encode(root_hash)}\n"`, sign with Ed25519, and `INSERT INTO checkpoint(taken_at, kind, tree_size, root_hash, signature, signer_key_id) VALUES (clock_timestamp(), 'REGULAR', ...)`.
  5. Expose `GET /v1/checkpoints/latest` (`Cache-Control: no-store`) and `GET /v1/referrals/{id}/proof?checkpoint_id=...` returning the $O(\log N)$ Merkle inclusion proof `{"referral_id", "head_seq", "head_hash", "leaf_index", "tree_size", "path": [{"side": "L"|"R", "hash": "b64"}], "checkpoint_id", "note", "signature"}`.
* **Verification Gate:**
  * Run `pytest tests/test_witness_merkle.py` across tree sizes $0, 1, 2, 3, 7, 16$ and verify every leaf's inclusion proof folds to the signed `root_hash`.

### 6.2 Off-Box Witness Sync, Cold-Key Signed `RESTORE` Protocol & Truncation Detection
* **Objective:** Distinguish legitimate disaster-recovery database restores from malicious history truncation or split-view attacks (Closure F8).
* **Files to Create:**
  * `scripts/witness_pull_sync.py`
  * `scripts/cold_sign_restore.py`
* **Implementation Specifications:**
  1. `scripts/witness_pull_sync.py` runs on a second witness client (or judge phone storage), polling `/v1/checkpoints/latest`, verifying the Ed25519 signature, appending to an append-only local log, and raising `SPLIT_VIEW_OR_ROLLBACK_DETECTED` if a newly fetched checkpoint has a lower `id` or if any referral's `head_seq` regresses without a valid `RESTORE` checkpoint.
  2. `scripts/cold_sign_restore.py` uses the offline cold Ed25519 key to sign `{restore_from_checkpoint_id, restored_at, head_map_hash}`, inserts a `checkpoint(kind='RESTORE', restore_from=..., cold_signature=...)` row, and appends a `RESTORE` event (`prev_hash = restored_head_hash`, `seq = head_seq + 1`) to each restored referral.
* **Verification Gate (`T-F8`, `T-S2`):**
  * Run `pytest tests/test_tamper_vs_restore.py` proving that truncating the `event` table without a cold-key `RESTORE` checkpoint triggers `TRUNCATED at seq=<k>`, while a cold-key-signed `RESTORE` validates cleanly.

### 6.3 Pure-JS Browser Verifier (`@noble`) & Superuser SQL Tamper Demo Script (`tamper.sh`)
* **Objective:** Enable every judge's phone browser (including iOS Safari over plain-HTTP LAN where WebCrypto `crypto.subtle` is disabled) to independently verify event hash chains, Merkle inclusion proofs, and checkpoint signatures in pure JavaScript.
* **Files to Create:**
  * `pwa/src/crypto/verifier.ts`
  * `scripts/tamper.sh`
* **Implementation Specifications:**
  1. Bundle pinned `@noble/curves/ed25519` and `@noble/hashes/sha256` locally in `pwa/src/vendor/`.
  2. In `pwa/src/crypto/verifier.ts`, implement `verifyReferralIntegrity(checkpoint, proof, events, pinnedWitnessPubKey, pinnedColdPubKey)`:
     * Step 1: Verify `checkpoint.signature` over `checkpoint.note` using `ed25519.verify`. On failure return `{ok: false, error: "CHECKPOINT_SIG"}`.
     * Step 2: Walk `events` from `seq = 1` (`prev_hash = 0x00 * 32`). Check `e.seq === expectedSeq` (else `SEQ_GAP`), check `e.prev_hash === prevHash` (else `BROKEN referral=${id} seq=${e.seq} kind=PREV`), serialize `core` using deterministic key-sorted JCS, and check `sha256(prev_hash || jcs(core)) === e.hash` (else `BROKEN referral=${id} seq=${e.seq} kind=HASH expected=${computed} got=${e.hash}`).
     * Step 3: Compute leaf hash `sha256(0x00 || uuidBytes || seqBe8 || headHash)` and fold `proof.path` to verify equality with `checkpoint.root_hash` (else `ROOT_MISMATCH`).
     * Step 4: Verify `events[events.length - 1].seq >= proof.head_seq` unless a valid cold-signed `RESTORE` event is present (else `TRUNCATED at seq=${proof.head_seq}`).
  3. Write `scripts/tamper.sh` to connect as PostgreSQL superuser (`postgres`), temporarily disable `event_ao` trigger (`SET session_replication_role = replica;`), modify `detail` on a target referral's event row, and restore `session_replication_role = origin;`.
* **Verification Gate (`T-I5`, `T-D1`):**
  * Run Vitest/Node test verifying `verifier.ts` against `spec/parity_vectors.json`, execute `scripts/tamper.sh`, and assert `verifier.ts` outputs `BROKEN referral=... seq=... kind=HASH`.

---

## MODULE 7: Core PWA Desks, Rotating QR Admission & Guarantee Arena Big Screen (`T0` Complete — Priority 7)

### 7.1 React PWA Shell, SSE State Store, IndexedDB Offline Outbox & Mode/Liveness Banners
* **Objective:** Build the responsive frontend foundation with real-time SSE synchronization, offline command queuing, and prominent safety/mode banners.
* **Files to Create:**
  * `pwa/src/store/sseClient.ts`
  * `pwa/src/store/outbox.ts`
  * `pwa/src/components/ModeBanner.tsx`
* **Implementation Specifications:**
  1. `sseClient.ts`: connects to `/v1/stream`, tracks `lastEventId`, updates the reactive referral store on incoming events, and immediately clears clinical payload fields from memory/DOM upon receiving a `GRANT_REVOKED` frame.
  2. `outbox.ts`: stores mutating commands in IndexedDB when offline with a generated UUIDv7 `event_id` and `Idempotency-Key`. Displays queued items as **"Pending — Not Confirmed"**. On reconnect (or foreground focus on iOS), flushes the queue in order; if the server returns `409` or `412`, replaces local optimistic state with authoritative server state and displays a clear explanation banner.
  3. `ModeBanner.tsx`: polls `/mode` and `/healthz`, rendering:
     * Flashing Red Banner when `BROKEN_BUILD == 1` (`"BROKEN BUILD — SCRATCH DB (LEASE GUARD DISABLED)"`).
     * Amber Banner when `LAN_MODE == 1` or any worker heartbeat is $>15\text{ s}$ stale.
     * Persistent badge: `"SYNTHETIC DATA ONLY (REAL_DATA=0)"`.
* **Verification Gate:**
  * Verify in browser dev tools that toggling network offline queues commands as `"Pending — Not Confirmed"` and reconnecting flushes them with the identical `Idempotency-Key`.

### 7.2 Rotating Single-Use Judge QR Admission, Cloudflare Turnstile Gate, 20-Desk Cap & LAN Mode
* **Objective:** Let judges join live from their phones as competing hospital desks in under 4 seconds while preventing bot floods.
* **Files to Create:**
  * `api/rhp/commands/judge_join.py`
  * `pwa/src/views/JudgeJoin.tsx`
* **Implementation Specifications:**
  1. Backend `GET /v1/judge/qr-token` mints a signed, rotating QR payload containing a single-use `jti` (valid for 20s, rotated every 15s on the Big Screen) plus pinned `WITNESS_PUBKEY_HEX` and `COLD_PUBKEY_HEX`.
  2. When a judge scans the QR (`POST /v1/judge/join`):
     * Verify `jti` is unexpired and unused.
     * In tunnel mode, verify the Cloudflare Turnstile token; in `LAN_MODE=1`, bypass cloud Turnstile and enforce strict single-use `jti` + IP rate limit.
     * Enforce a hard cap of `20` active `JUDGE_DESK` sessions (`429 ADMISSION_CAP_REACHED` on desk 21).
     * Assign the judge to one of the competing receiving facilities (`CHC_RAMANAGARA` or `DH_MANDYA`) and set the `rhp_session` cookie.
* **Verification Gate:**
  * Test joining 20 sessions via QR tokens (succeeds), test reusing a consumed `jti` (`403`), and test a 21st join (`429`).

### 7.3 Referring Clinician Card Creator (ISBAR + Answer-Required `mgso4_status` + Printable Slip)
* **Objective:** Allow a clinician to author and dispatch an emergency obstetric referral in $\le 20\text{ s}$ with zero double-entry.
* **Files to Create:**
  * `pwa/src/views/ClinicianCard.tsx`
* **Implementation Specifications:**
  1. Structured ISBAR form with curated preset codes, `need_class` (`OBSTETRIC_EMERGENCY` default), mode toggle (`SEQUENTIAL` default, `PARALLEL2` for critical/race demo), and pre-filled approved catchment chain (1-tap confirm or reorder/skip).
  2. **Answer-Required Drug Safety Block:** Radio selector for `mgso4_status`: `GIVEN` (with dose/time inputs), `NONE_GIVEN`, or `UNKNOWN`. Selecting `UNKNOWN` is valid and never blocks dispatch.
  3. **Card-as-Slip Print View:** Renders a printable handover slip displaying the 9-character Crockford `paper_code` and QR code so the clinician never writes a separate paper slip.
* **Verification Gate:**
  * Create a referral with `mgso4_status = 'UNKNOWN'` in the UI and verify it transitions immediately to `OFFERED` in under 1 second.

### 7.4 Receiving Duty Desk (Anti-Goodhart Priority Queue, Red `mgso4_status=UNKNOWN` Banner & Live Reconfirm)
* **Objective:** Provide the hospital casualty desk interface that prevents Goodhart gaming, surfaces clinical unknowns, and handles race losses and expired confirmations gracefully.
* **Files to Create:**
  * `pwa/src/views/ReceivingDesk.tsx`
* **Implementation Specifications:**
  1. **Anti-Goodhart Queue:** Display incoming offers ordered by clinical priority without countdown timers on the clinician-facing queue.
  2. **Clinical Safety Banner:** When `referral.mgso4_status == 'UNKNOWN'`, display a high-contrast red banner: `"PRE-REFERRAL MgSO4 DOSE UNKNOWN — VERIFY WITH PATIENT/ESCORT BEFORE DOSING"`.
  3. **Handshake Controls:**
     * Opening the card automatically sends `ACK`.
     * Interactive capability checklist (`OT`, `BLOOD`, `ANAESTHETIST`, `NICU`) where each toggle sends `RESOURCE_CONFIRM`.
     * Action buttons: **Accept** (prompts for 4-digit PIN), **Counter** (structured condition checkboxes), **Decline** (structured reason dropdown + optional redirect facility selector).
  4. **Stale Confirmation Reconfirm Modal (Invariant I15):** If `ACCEPT` returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`, open a 1-click **"Capabilities Expired — Reconfirm Live Now"** modal that re-submits `RESOURCE_CONFIRM` for each required capability and immediately sends a fresh `ACCEPT`.
* **Verification Gate:**
  * Open an offer on `ReceivingDesk`, let `confirm_ttl` expire, click Accept, verify `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` triggers the reconfirm modal, and complete the accept.

### 7.5 Judge Race Desk & Integrated Pure-JS Tamper Verifier Drawer
* **Objective:** Give judges a frictionless smartphone screen to participate in the live concurrency race and verify cryptographic integrity in their own browser.
* **Files to Create:**
  * `pwa/src/views/JudgeDesk.tsx`
* **Implementation Specifications:**
  1. Displays the judge's assigned hospital desk name, live offer state, pre-confirmed capability badges, and a large **ACCEPT REFERRAL (GRANT LEASE)** button.
  2. On click, submits `ACCEPT` and clearly renders either:
     * **Green Winner Card:** `"LEASE GRANTED — YOU OWN THIS HANDOVER (Epoch #1)"`, or
     * **Amber Loser Card:** `"409 LEASE_HELD — Another facility locked the lease milliseconds ahead of you."`
  3. Includes an **"Inspect & Verify Cryptographic Proof"** drawer that runs `verifier.ts` in the judge's browser against `/v1/checkpoints/latest` and prints either `"VALID: Merkle Root & Ed25519 Signature Verified"` or the exact broken link (`BROKEN referral=... seq=... kind=HASH`).
* **Verification Gate:**
  * Open two browser windows as Judge Desk 1 and Judge Desk 2, click Accept simultaneously, verify one shows Green Winner and one shows Amber `409 LEASE_HELD`, then run `scripts/tamper.sh` and click Verify in the drawer to confirm `BROKEN ... kind=HASH` appears on the phone screen.

### 7.6 Guarantee Arena Big Screen & 30-Second Live Proof Loop Controller
* **Objective:** Build the centerpiece projection dashboard showing the Independent Runtime Monitor's I1–I16 counters, live escalation ladders, witness checkpoints, and operator chaos controls (Closure F16).
* **Files to Create:**
  * `pwa/src/views/ArenaBigScreen.tsx`
* **Implementation Specifications:**
  1. **Top Bar:** Mode/Safety Banner (`GREEN: ALL 16 INVARIANTS HOLDING` or flashing `RED: INVARIANT VIOLATION DETECTED`), active profile badge, live measured p50/p95 commit latency, and worker heartbeat indicators.
  2. **Left Column (Invariant Matrix I1–I16):** 16 live tiles driven directly by `monitor` `/status`, showing evaluation count and violation count.
  3. **Center Column (Live Contract Track & Escalation Ladder):** Real-time visual state machine showing both the **Handshake Track** (`OFFERED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `ACCEPTED` / `SOFT_OPEN` $\rightarrow$ `ESCALATED_TO_DISPATCHER`) and the independent **Transport Track**, plus the rotating Judge Join QR code.
  4. **Right Column (Witness & Operator Chaos Drawer):** Latest signed Merkle checkpoint root, witness count, and 1-click operator buttons for the 30-second proof loop:
     * `[1] Spawn PARALLEL2 Race Referral`
     * `[2] Toggle BROKEN_BUILD (Scratch DB)`
     * `[3] Inject SQL Row Tamper (Scratch DB)`
     * `[4] Trigger Toxiproxy Network Partition`
     * `[5] Show 30s Proof Loop Recap Overlay`
* **Verification Gate (`T-F16` — Completes Tier 0):**
  * Execute the entire 30-second live proof loop end-to-end on the Big Screen (`0–4s` QR join $\rightarrow$ `4–7s` PARALLEL2 create $\rightarrow$ `7–12s` simultaneous accept $\rightarrow$ `12–18s` `BROKEN_BUILD=1` turns Monitor I2 RED $\rightarrow$ `18–21s` flip back GREEN $\rightarrow$ `21–27s` SQL tamper caught by Judge phone verifier $\rightarrow$ `27–30s` live measured recap).

---

## MODULE 8: Parallel Transport Track, Mapbox ETAs, Dispatcher Console & Replay (`T1_TRANSPORT` — Priority 8)

### 8.1 Parallel Transport Track API (`TR_UPDATE`, `TR_DESTINATION_CHANGE`), 6 Arrival Cases & Telemetry Ingest
* **Objective:** Run ambulance transport tracking completely independently of handshake state (Invariant I3), handle all 6 real-world arrival scenarios (Closure F5), and ingest offline-tolerant GPS/vitals telemetry.
* **Files to Create:**
  * `api/rhp/commands/transport.py`
* **Implementation Specifications:**
  1. **`TR_UPDATE` Command:**
     * Advances `referral.tr_state`: `REQUESTED` $\rightarrow$ `DISPATCHED` $\rightarrow$ `EN_ROUTE` $\rightarrow$ `ARRIVED` $\rightarrow$ `HANDED_OVER` (or `TR_CANCELLED` prior to `ARRIVED`).
     * **Invariant I3 Enforcement:** Never read or gate on `referral.hs_state` (except rejecting if `hs_state in ('CLOSED', 'CANCELLED')`).
     * Require a human actor (`EMT`, receiving desk role, or `DISPATCHER`) for `ARRIVED` and `HANDED_OVER`.
  2. **Six Arrival Cases (Closure F5):**
     * **Case (a) Arrival at lease holder:** Geofence emits `ARRIVAL_SUGGESTED`; EMT or desk confirms `TR_UPDATE(ARRIVED)`.
     * **Case (b) Arrival at facility with `OPEN`/`ACKED`/`SOFT_OPEN` offer:** Desk can execute `ACCEPT` immediately (subject to I15 resource confirmations) and confirm `ARRIVED`.
     * **Case (c) Unannounced arrival at facility with no offer:** Emit `ARRIVAL_AT_NON_OWNER` urgent alert + dispatcher page; never block care; dispatcher can `DISPATCHER_ASSIGN`.
     * **Case (d) En-route destination change:** Crew or dispatcher sends `TR_DESTINATION_CHANGE(facility_id, reason, accepted=True)`.
     * **Case (e) Crew refuses redirect advisory:** Crew sends `TR_DESTINATION_CHANGE(facility_id, reason, accepted=False)`; logged, lease unchanged, dispatcher paged.
     * **Case (f) Ambulance past highway turn-off:** System provides detour ETA advisory; crew decides; if continuing to original facility without lease, handled via Case (c) on arrival.
  3. **Telemetry Batch Ingest (`POST /v1/telemetry`):**
     * Inserts `GPS` (`lat_e5, lon_e5, acc_m`) and `OBS` (`obs_code, obs_val`) records with `ON CONFLICT (event_id) DO NOTHING` (idempotent set-union merge for offline batches).
* **Verification Gate (`T-F5`, `T-I3`):**
  * Run `pytest tests/test_transport_and_arrivals.py` verifying `TR_UPDATE` succeeds in every non-terminal `hs_state` and testing all 6 arrival cases `(a)` through `(f)`.

### 8.2 Geofence Arrival Hint (`ARRIVAL_SUGGESTED`) & Server-Side Mapbox Matrix ETA Service
* **Objective:** Provide 200m geofence arrival hints without auto-transitioning `ARRIVED` and compute cached road ETAs for top candidate facilities.
* **Files to Create:**
  * `api/rhp/extras/mapbox_eta.py`
* **Implementation Specifications:**
  1. When `POST /v1/telemetry` ingests a `GPS` point within $200\text{ m}$ of `tr_facility_id` (Haversine distance) with dwell $\ge 20\text{ s}$, emit `ARRIVAL_SUGGESTED` via `SYSTEM_SESSION`. Never auto-mutate `tr_state` to `ARRIVED`.
  2. Implement `get_candidate_etas(referral_id)` calling Mapbox Matrix API (`mapbox/driving`, max 25 coords, 60 req/min) for the active referral's chain candidates, caching results in memory/DB for $120\text{ s}$. If the cache is $>120\text{ s}$ old or offline, return the cached value flagged with `stale: true`.
* **Verification Gate:**
  * Submit synthetic GPS points approaching `CHC_RAMANAGARA` and verify `ARRIVAL_SUGGESTED` is emitted while `tr_state` remains `EN_ROUTE` until human confirmation.

### 8.3 PWA Ambulance Client (Foreground `watchPosition`, Offline Queue & Redirect Advisory)
* **Objective:** Provide EMT crews with a mobile web interface for live GPS streaming, offline vitals logging, redirect advisories, and 1-tap arrival/handover confirmation.
* **Files to Create:**
  * `pwa/src/views/AmbulancePwa.tsx`
* **Implementation Specifications:**
  1. Streams foreground geolocation (`navigator.geolocation.watchPosition`) plus a manual **"Update Position / Log Vitals"** button and displays `"Last confirmed: Ns ago"`.
  2. Displays a high-visibility **Redirect Advisory Modal** whenever `referral.lease_facility_id` changes while `tr_state == 'EN_ROUTE'`, showing the new lease holder, detour ETA, and two buttons: **Accept Redirect** (`TR_DESTINATION_CHANGE(accepted=True)`) or **Continue to Current Destination** (`TR_DESTINATION_CHANGE(accepted=False)`).
  3. Renders the **"Geofence Hint: Within 200m — Confirm Arrival?"** prompt when `ARRIVAL_SUGGESTED` fires.
* **Verification Gate:**
  * Simulate a lease change while an ambulance is `EN_ROUTE` and verify the Redirect Advisory Modal appears without automatically changing the ambulance's destination.

### 8.4 Dispatcher Console (Escalated Queue, Phone-Assisted Proxy Entry & Deterministic Replay Scrubber)
* **Objective:** Empower the 108/district dispatcher to resolve `ESCALATED_TO_DISPATCHER` referrals, enter phone-assisted proxy responses, and scrub backward/forward through any referral's event history.
* **Files to Create:**
  * `pwa/src/views/DispatcherConsole.tsx`
* **Implementation Specifications:**
  1. **Escalated Action Queue:** Highlights referrals in `ESCALATED_TO_DISPATCHER`, `ARRIVAL_AT_NON_OWNER`, `HANDOVER_OVERDUE`, and `CLOSURE_OVERDUE`.
  2. **Proxy Action Panel:** Allows the dispatcher to execute `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `DECLINE`, `DISPATCHER_ASSIGN`, or `TR_UPDATE` on behalf of a clinician, receiving role, or EMT crew, automatically tagging `proxy = True`, `proxy_for = target_roster_id`, and requiring a structured reason code.
  3. **Deterministic Time-Scrubber Replay:** Slider from `seq = 1` to `head_seq` that folds the referral's event log client-side and renders the exact historical state of all offers, leases, and transport positions at each sequence number.
* **Verification Gate (`T1` Acceptance Gate):**
  * Run 20 paired trials comparing direct API actions vs. dispatcher proxy actions (assert identical resulting states and event sequences) and verify the replay scrubber reproduces `referral` state at `seq = head_seq`.

---

## MODULE 9: Multi-Channel Reach: Exotel Voice IVR, DLT SMS & Paper Code (`T2_REACH` — Priority 9)

### 9.1 Outbound Exotel IVR Adapter, `inbox` Webhook Deduplication & 2-Second Commit Budget
* **Objective:** Reach duty clinicians on basic feature phones via outbound automated calls with strict webhook idempotency and sub-2-second response times.
* **Files to Create:**
  * `api/rhp/reach/exotel_ivr.py`
* **Implementation Specifications:**
  1. Outbox relay `VOICE` adapter initiates an outbound Exotel call to `roster.phone_e164` (whitelisted numbers in trial mode) and creates a voice `session` bound to `CallSid`.
  2. Every incoming Exotel webhook (`POST /v1/webhooks/exotel/*`) first executes:
     ```sql
     INSERT INTO inbox(source, external_id, payload_sha256)
     VALUES ('EXOTEL', %s, %s)
     ON CONFLICT (source, external_id) DO NOTHING
     RETURNING id;
     ```
     If no row is returned, replay `200 OK` immediately.
  3. Enforce a `1.5s` execution timeout on `apply_command()` inside the webhook handler so the HTTP response always returns within `2.0s` (well inside Exotel's 5s limit `[V]`); if lock contention exceeds `1.5s`, return the `"please_hold"` applet response and poll the committed result on the next callback.
* **Verification Gate (`T-N5`, `T-N6`):**
  * Replay 20 duplicate Exotel webhook requests and assert `inbox` deduplicates 100% of them with p95 latency $\le 2\text{ s}$.

### 9.2 Answering-Machine Detection (AMD), Mandatory Press-1 Human Gate & Native Audio Prompts
* **Objective:** Prevent voicemail boxes or auto-attendants from ever generating a false `ACK` (Closure F7, Invariant I6).
* **Files to Create:**
  * Update `api/rhp/reach/exotel_ivr.py`
  * `api/rhp/reach/audio_manifest.json`
* **Implementation Specifications:**
  1. On call connect, inspect AMD status and play the pre-recorded native prompt (Kannada / Hindi / English): *"Emergency referral call. Press 1 to hear the referral."* (8s timeout).
  2. If AMD reports `MACHINE`, or the callee hangs up, or no `1` is pressed within 8s $\rightarrow$ record zero `ACK` events and mark the call `UNANSWERED`.
  3. Only when DTMF `1` is received: invoke `apply_command(ACK, channel='VOICE')` and, **only after the transaction commits**, play the de-identified summary (origin facility, need class, ETA — **never a patient name**).
* **Verification Gate (`T2` Voicemail Gate):**
  * Run 5 simulated voicemail/AMD-machine trials (assert `0` ACKs recorded) and 20 human press-1 trials (assert 20/20 `ACK` events committed before summary playback).

### 9.3 DTMF Response Menu (Accept / Counter / Decline) & Per-Call PIN Verification
* **Objective:** Allow a feature-phone receiver to accept, counter, or decline with a PIN using only their keypad.
* **Files to Create:**
  * Update `api/rhp/reach/exotel_ivr.py`
* **Implementation Specifications:**
  1. Keypad Menu:
     * `1`: Confirm all required capabilities and request **Accept**.
     * `2`: Request **Counter** (sub-menu: `1` Without NICU, `2` Anaesthetist in 20m, `3` Blood on request).
     * `3`: Request **Decline** (sub-menu: `1` `NO_OT`, `2` `NO_NICU`, `3` `NO_ANAESTHETIST`, `4` `AT_CAPACITY`).
     * `9`: Repeat summary.
  2. Prompt for 4-digit PIN followed by `#` (URL-decoded from `%23`).
  3. Execute `apply_command` with Step 3 Argon2id PIN verification scoped to `call_sid`. Play `"Your response is recorded"` **only after database commit**. On 3 wrong PINs, lock the `call_sid` session, play lockout notice, hang up, and page the dispatcher.
* **Verification Gate:**
  * Complete a full `ACK` $\rightarrow$ `ACCEPT` + PIN `#` flow via simulated Exotel DTMF webhooks and verify `LEASE_GRANTED` commits with `channel='VOICE'`.

### 9.4 TRAI DLT-Compliant Static SMS Alert Adapter
* **Objective:** Deliver SMS alerts without ever transmitting PHI or violating TRAI DLT variable-length rules (Closure P2).
* **Files to Create:**
  * `api/rhp/reach/dlt_sms.py`
* **Implementation Specifications:**
  1. Enforce a strict static template: `"RHP alert: new referral. Open {#var#}"` where `{#var#}` is strictly $\le 30$ characters (`^[A-Za-z0-9/_.-]{1,30}$`, containing only the whitelisted domain path / short paper code).
  2. Raise a hard error if any caller attempts to pass clinical text or patient identifiers to the SMS adapter.
* **Verification Gate (`T-P2`):**
  * Run `pytest tests/test_dlt_sms_lint.py` verifying that variables $>30$ chars or strings outside the token regex are rejected.

### 9.5 9-Character Crockford Base32 + Mod-37 Checksum Paper Code Codec & Paper-First Linking UI
* **Objective:** Guarantee 100% detection of single-character typos and adjacent transpositions when casualty staff link a paper slip at the door.
* **Files to Create:**
  * `api/rhp/reach/paper_code.py`
  * Update `pwa/src/views/ReceivingDesk.tsx`
* **Implementation Specifications:**
  1. **Encoding:** Generate 40 random bits ($N \in [0, 2^{40}-1]$), encode as 8 Crockford Base32 characters (`0123456789ABCDEFGHJKMNPQRSTVWXYZ`), compute $c = N \pmod{37}$, and append the 9th check character from the 37-character Crockford checksum alphabet (`0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U`). Because $37$ is prime and $32^i$ is invertible $\pmod{37}$, any single-symbol error changes $N$ by $\Delta \cdot 32^i \not\equiv 0 \pmod{37}$, and any adjacent transposition of distinct symbols changes $N$ by $(a - b) \cdot 32^i \cdot 31 \not\equiv 0 \pmod{37}$.
  2. **Decoding & Verification:** Normalize input (uppercase, map `I`/`L` $\rightarrow$ `1`, `O` $\rightarrow$ `0` on the first 8 chars; preserve `U` on the 9th check char), recompute $N \pmod{37}$, and reject mismatches with `422 INVALID_PAPER_CODE_CHECKSUM`.
  3. Rate-limit `POST /v1/paper-code/resolve` to 10 attempts/minute per session. Allow a receiving desk to link an existing digital referral or create a paper-first record if the origin clinic was completely offline.
* **Verification Gate (`T2` Paper Code Gate):**
  * Run `pytest tests/test_paper_code_mod37.py` mutating 1,000 random valid paper codes with single-symbol errors and adjacent transpositions, asserting 100% rejection.

---

## MODULE 10: Envelope Encryption, Crypto-Shredding & Command Centre Analytics (`T3_EXTRAS` Part A — Priority 10)

### 10.1 Per-Referral AES-256-GCM Envelope Encryption, Monthly KEK Wrapping & `event_secret` Binding
* **Objective:** Encrypt all clinical payloads and sensitive event notes with per-referral Data Encryption Keys (DEKs) so deleting the DEK permanently crypto-shreds PHI without breaking the event hash chain (Closures D9, P5).
* **Files to Create:**
  * `api/rhp/extras/envelope_crypto.py`
* **Implementation Specifications:**
  1. For each referral at `CREATE`:
     * Generate a random 256-bit DEK (`os.urandom(32)`).
     * Wrap the DEK using AES Key Wrap (`cryptography.hazmat.primitives.keywrap.aes_key_wrap`) with the current monthly `KEK` (`kek_epoch = "2026-11"`), and store in `key_version(id, referral_id, kek_epoch, wrapped_dek, status='ACTIVE')`.
  2. Encrypt the ISBAR + Dakshata payload using `AESGCM(dek).encrypt(nonce_12b, plaintext_bytes, aad)` where `aad = f"{referral_id}:{key_id}:{schema_ver}".encode()`, and store in `clinical_payload`.
  3. If an event includes sensitive notes, encrypt in `event_secret` with `aad = f"{referral_id}:{seq}:{key_id}".encode()` and store `SHA-256(nonce || ciphertext)` in `event.secret_hash`.
* **Verification Gate:**
  * Run `pytest tests/test_envelope_crypto.py` verifying round-trip encryption/decryption and AAD tamper rejection.

### 10.2 Automated Crypto-Shredding Worker (DEK Zeroing & Ciphertext Purge)
* **Objective:** Execute verifiable crypto-shredding on expired handover records while keeping the pseudonymous `event` hash chain 100% intact and verifiable.
* **Files to Create:**
  * `api/rhp/extras/shredder.py`
* **Implementation Specifications:**
  1. Implement `shred_referral(conn, referral_id)`:
     * `DELETE FROM clinical_payload WHERE referral_id = %s;`
     * `DELETE FROM event_secret WHERE referral_id = %s;`
     * `UPDATE key_version SET wrapped_dek = NULL, status = 'SHREDDED', shredded_at = clock_timestamp() WHERE referral_id = %s;`
  2. Expose an operator endpoint `POST /v1/admin/referrals/{id}/shred` for live demonstration and run a scheduled sweep for rows where `clinical_payload.expires_at <= clock_timestamp()`.
* **Verification Gate (`T-P5`):**
  * Create a referral, run `shred_referral`, verify `clinical_payload` and `wrapped_dek` are `NULL`/deleted, and run the Independent Runtime Monitor and Browser Verifier confirming `I5` hash chain verification still passes 100%.

### 10.3 District Command Centre: Live Map, Timestamped Capability Attestations & APOT-Separated KPIs
* **Objective:** Provide district health officers with read-only bottleneck intelligence derived strictly from the event log, separating acceptance latency from physical handover latency to expose gaming.
* **Files to Create:**
  * `api/rhp/extras/analytics.py`
  * `pwa/src/views/CommandCentre.tsx`
* **Implementation Specifications:**
  1. **Capability Attestations with Age:** Display each facility's attested capabilities (`OT`, `BLOOD`, `ANAESTHETIST`, `PAEDIATRICIAN`, `NICU`) with `"Attested Xh Ym ago"` and hide expired capabilities (`expires_at <= now`). Never display the phrase `"live beds"`.
  2. **Log-Derived KPIs (Anti-Goodhart):**
     * Compute from `event` rows: Median/p95 Time-to-ACK, Unanswered Offer Rate, Intra/Inter-Facility Escalation Count, `ARRIVAL_REJECTED` Broken-Commitment Rate, and **APOT-Style Arrival-to-Handover Time** (`TR_UPDATED(ARRIVED)` $\rightarrow$ `TR_UPDATED(HANDED_OVER)`) reported alongside Acceptance Rate so facilities that accept quickly but delay handover at the door are immediately visible.
* **Verification Gate:**
  * Run `pytest tests/test_analytics_recompute.py` asserting that Command Centre KPI endpoints match a fresh full-log recomputation bit-for-bit.

### 10.4 Referral Network Graph (`networkx`) & 4-Hour Bucketed $k \ge 5$ Privacy-Preserving Aggregations
* **Objective:** Visualize district referral bottlenecks and suppress small-cell re-identification risk on shared exports (Closure F9).
* **Files to Create:**
  * Update `api/rhp/extras/analytics.py`
* **Implementation Specifications:**
  1. Build a directed weighted `networkx.DiGraph` from `origin_facility_id` $\rightarrow$ `lease_facility_id` (and declined/timed-out hops), computing betweenness centrality and labeling the output `"Descriptive Network Graph (Not Causal)"`.
  2. Implement `bucket_and_suppress(rows, k=5)` which truncates timestamps to 4-hour windows (`00:00`, `04:00`, `08:00`, `12:00`, `16:00`, `20:00`) and masks any `(facility, need_class, bucket)` cell with $< 5$ referrals.
* **Verification Gate:**
  * Verify in `pytest` that a bucket with 4 referrals is suppressed (`count = "<5"`) while a bucket with 5 referrals is emitted.

---

## MODULE 11: Cognitive-Forcing AI Intake, Interoperability Exports & Kotlin App (`T3_EXTRAS` Part B — Priority 11)

### 11.1 AI Intake Accelerator: `423 ANCHOR_REQUIRED` Cognitive Forcing Function & 20-Slip Seeded-Error Gate
* **Objective:** Accelerate referral card drafting from photos/dictation while preventing clinician automation bias via a server-enforced Cognitive Forcing Function (Closures A1, A2).
* **Files to Create:**
  * `api/rhp/extras/ai_intake.py`
  * Update `pwa/src/views/ClinicianCard.tsx`
* **Implementation Specifications:**
  1. **Think-First Anchor Gate (`423 ANCHOR_REQUIRED`):**
     * `POST /v1/ai/draft/{draft_id}/reveal` refuses to return the AI-extracted draft (`HTTP 423 ANCHOR_REQUIRED`) until the clinician first submits their own independent commitment for `need_class` and `mgso4_status`.
  2. **Quarantined UI & Mandatory Re-Entry:**
     * Render AI draft fields as unverified placeholders; require active manual re-entry/confirmation on critical dosage and vital fields; never display confidence percentages or persuasive explanations.
  3. Include a 20-slip synthetic benchmark harness (`tests/test_ai_seeded_errors.py`) with 30% seeded fatal errors verifying the forcing-function gate (targets: critical-error rubber-stamp $\le 5\%$, silent omission $\le 1\%$).
* **Verification Gate (`T-A1`, `T-A2`):**
  * Assert `GET/POST` to retrieve an AI draft without anchor commitments returns `423 ANCHOR_REQUIRED`, and assert the system operates 100% normally when `T3_EXTRAS=0`.

### 11.2 NRCeS/ABDM-Aligned FHIR R4 Bundle Exporter (`ServiceRequest`, `Task`, `Encounter`, `Communication`)
* **Objective:** Export any referral's lifecycle as a valid, curated FHIR R4 Bundle without requiring a heavy external terminology server.
* **Files to Create:**
  * `api/rhp/extras/exporters.py`
* **Implementation Specifications:**
  1. `GET /v1/referrals/{id}/export/fhir` constructs a FHIR R4 `Bundle` (`type="collection"`) containing:
     * `ServiceRequest`: `intent="order"`, `status`, `code` (curated obstetric/trauma code subset), `requester` (`origin_facility_id`), `performer` (`lease_facility_id`).
     * `Task`: `status` mapped deterministically (`CREATED`/`OFFERED` $\rightarrow$ `requested`, `ACKNOWLEDGED` $\rightarrow$ `received`, `ACCEPTED` $\rightarrow$ `accepted`, `COUNTERED`/`ESCALATED_TO_DISPATCHER` $\rightarrow$ `on-hold`, `CANCELLED` $\rightarrow$ `cancelled`, `CLOSED` $\rightarrow$ `completed`), `businessStatus.text = referral.hs_state`.
     * `Encounter`: generated from `TR_UPDATED` (`ARRIVED` / `HANDED_OVER`) events.
     * `Communication`: generated for each `OFFER_COUNTERED` and `OFFER_DECLINED` event with structured reason codes.
* **Verification Gate:**
  * Validate the JSON output of `/v1/referrals/{id}/export/fhir` against the FHIR R4 JSON schema validator.

### 11.3 IEEE 1849 XES Process-Mining Exporter & BSA 2023 s.63 Hash-Bearing Evidence Bundle Generator
* **Objective:** Export 4-hour bucketed XES event logs for process mining and generate a hash-bearing evidence package with Part A (Custodian) and Part B (Expert) certificate templates under Bharatiya Sakshya Adhiniyam (BSA) 2023 s.63.
* **Files to Create:**
  * Update `api/rhp/extras/exporters.py`
* **Implementation Specifications:**
  1. `GET /v1/export/xes`: generates standard IEEE 1849 XML (`<log>`, `<trace>`, `<event>`) with `concept:name = event.type`, `org:resource = actor_facility_id`, and 4-hour bucketed `time:timestamp`.
  2. `GET /v1/referrals/{id}/export/bsa63`: produces a deterministic ZIP/JSON bundle containing:
     * Canonical JCS event log (`events.jcs.json`) and Merkle inclusion proof (`merkle_proof.json`).
     * SHA-256 manifest (`manifest.sha256`).
     * Pre-populated **Part A (Custodian)** and **Part B (Expert)** BSA s.63 certificate templates pre-filled with the exact SHA-256 hex digest, system description, and an explicit header: `"BSA s.63-Ready Export Bundle — Requires Authorized Signatory Execution (Not Pre-Certified)"`.
* **Verification Gate (`T-L3`):**
  * Verify the BSA export bundle recomputes the exact SHA-256 digest and passes the `ST-5` claims lexicon scan.

### 11.4 Native Kotlin Android EMT Client (`FOREGROUND_SERVICE_TYPE_LOCATION`, Room Outbox & Empty-Payload FCM)
* **Objective:** Provide the production native Android ambulance application specification and module for continuous background location tracking and offline Room persistence.
* **Files to Create:**
  * `android/app/src/main/AndroidManifest.xml`
  * `android/app/src/main/java/in/rhp/emt/LocationForegroundService.kt`
  * `android/app/src/main/java/in/rhp/emt/outbox/OutboxDao.kt`
  * `android/app/src/main/java/in/rhp/emt/fcm/ZeroPayloadMessagingService.kt`
* **Implementation Specifications:**
  1. Declare `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_LOCATION`, and `ACCESS_FINE_LOCATION` permissions in `AndroidManifest.xml`.
  2. Implement `LocationForegroundService.kt` using `ServiceCompat.startForeground(..., FOREGROUND_SERVICE_TYPE_LOCATION)` and `FusedLocationProviderClient` (5-second interval), writing coordinates to a local Room `TelemetryEntity` table.
  3. Implement `OutboxWorker` (`CoroutineWorker`) that flushes pending Room commands and telemetry batches to `/v1/telemetry` and `/v1/referrals/{id}/tr-update` with `Idempotency-Key` headers.
  4. Implement `ZeroPayloadMessagingService.kt` which receives empty-payload FCM wake pings (`data = {"wake": "1"}`) and performs an authenticated HTTPS fetch to `/v1/referrals` so zero PHI ever traverses third-party push servers (Closure P3).
* **Verification Gate (`T-P3`):**
  * Run unit tests verifying the FCM adapter payload contains zero clinical keys (`{"wake": "1"}` only) and the Room outbox retries with the identical `Idempotency-Key`.

---

## MODULE 12: Toxiproxy Chaos Matrix, Self-Audit CI Scripts (`ST-1`..`ST-5`) & Final Gate Suite (Priority 12)

### 12.1 Eight-Scenario Toxiproxy Fault-Injection Matrix & Container Kill Recovery
* **Objective:** Prove the platform survives network partitions, TCP resets, packet slicing, bandwidth throttling, and sudden API container crashes with zero lost or duplicated events.
* **Files to Create:**
  * `tests/test_toxiproxy_chaos.py`
* **Implementation Specifications:**
  1. Programmatically drive the `toxiproxy` REST API (`http://localhost:8474`) across all 8 required fault scenarios between the client, `api`, and `pg`:
     * **Toxic 1 (`latency` upstream):** Add $1500\text{ ms}$ jitter $\rightarrow$ assert p95 latency rises, 0 duplicate events.
     * **Toxic 2 (`latency` downstream):** Drop response after commit, trigger client retry $\rightarrow$ assert Step 1 idempotency replays stored `200 OK`, single event in DB.
     * **Toxic 3 (`bandwidth`):** Throttle to $5\text{ KB/s}$ $\rightarrow$ assert SSE reconnects cleanly with `Last-Event-ID`.
     * **Toxic 4 (`slow_close`):** Delay socket close $\rightarrow$ assert no leaked `IN_FLIGHT` idempotency locks block retries.
     * **Toxic 5 (`timeout`):** Blackhole connection for $3\text{ s}$ then restore $\rightarrow$ assert retry converges to exact same state.
     * **Toxic 6 (`reset_peer`):** Inject TCP RST mid-transaction before commit $\rightarrow$ assert transaction aborts cleanly, idempotency row rolls back, and client retry succeeds.
     * **Toxic 7 (`slicer`):** Slice TCP frames into 16-byte chunks $\rightarrow$ assert JSON payloads and SHA-256 hashes remain intact.
     * **Toxic 8 (`limit_data` / proxy disable):** Cut network completely during offer creation $\rightarrow$ assert `outbox` relay redelivers within $\le 30\text{ s}$ of restoration and Monitor remains green.
* **Verification Gate:**
  * Run `pytest tests/test_toxiproxy_chaos.py` and verify all 8 toxics pass with `0` monitor violations.

### 12.2 Automated Self-Audit CI Scripts (`ST-1`..`ST-5`)
* **Objective:** Automate all five architectural self-audits so every commit is verified against lock ordering, $T_{\max}$ math, foreign-key integrity, idempotency, and claims discipline.
* **Files to Create:**
  * `tests/test_lock_order.py` (`ST-1`)
  * `tests/test_tmax_profiles.py` (`ST-2`)
  * `tests/test_ddl_constraints.py` (`ST-3`)
  * `tests/test_idempotency_matrix.py` (`ST-4`)
  * `tests/test_claims_lexicon.py` (`ST-5`, plus `T-F15` residual lint)
* **Implementation Specifications:**
  1. `ST-1`: Static + runtime check verifying that every database transaction in `api/` acquires locks strictly in the order `referral` $\rightarrow$ `offer` $\rightarrow$ `deadline` $\rightarrow$ `outbox` and that `rhp_require_lock` triggers are active on all 6 contract tables.
  2. `ST-2`: Verifies $T_{\max} = F \cdot (A + D + \varepsilon) \le B$ and voice stagger $A/4 + (S - 1)\delta + V \le 3A/4$ across all profiles.
  3. `ST-3`: Verifies all 24 tables, primary keys, foreign keys, `one_lease` partial unique index, and append-only triggers in `pg_constraint` and `pg_trigger`.
  4. `ST-4`: Executes all 8 idempotency edge cases.
  5. `ST-5`: Scans all UI templates, markdown docs, and code comments (excluding the forbidden-claims reference table itself) to ensure zero occurrences of forbidden overclaims (`"bullet-proof"`, `"airtight"`, `"zero loopholes"`, `"immutable log"`, `"ABDM compliant"`, `"production ready"`, `"eliminates ping-pong"`, `"lives saved"`, `"deaths prevented"`, `"mathematically proven system"`, `"BSA certified"`).
* **Verification Gate:**
  * Run `pytest tests/test_lock_order.py tests/test_tmax_profiles.py tests/test_ddl_constraints.py tests/test_idempotency_matrix.py tests/test_claims_lexicon.py` with 100% pass rate.

### 12.3 Master Tier Acceptance Gate Runner (`Makefile`)
* **Objective:** Provide single-command verification gates (`make gate-t0`, `make gate-t1`, `make gate-t2`, `make gate-t3`, `make gate-all`) measuring every acceptance criterion in the Definition of Done.
* **Files to Create:**
  * Update `Makefile`
  * `scripts/preflight.sh`
* **Implementation Specifications:**
  1. **`make gate-t0`:**
     * Runs `ST-1`..`ST-5`, `quint run spec/rhp1.qnt --invariant safety` ($\ge 20,000$ samples) + 4 vacuity checks, `race200` (asserting 1 winner out of 200, gap-free `seq`, 0 deadlocks), `M1`–`M6` mutation suite, `BROKEN_BUILD` red/green switch ($\le 2\text{ s}$), tampered-row detection in the pure-JS verifier, `DEMO_FAST` silence-to-dispatcher escalation ($\le 25\text{ s}$), and a 10-minute stateful Hypothesis + chaos run with `0` monitor violations.
  2. **`make gate-t1`:**
     * Runs 20 paired proxy-vs-direct equivalence runs, dispatcher assignment after `ESCALATED_TO_DISPATCHER`, and full state replay verification.
  3. **`make gate-t2`:**
     * Runs 20/20 voice ACKs post-commit, 5/5 voicemail 0-ACK trials, webhook p95 $\le 2\text{ s}$, and 1,000 mutated Crockford mod-37 paper codes (100% error rejection).
  4. **`make gate-t3`:**
     * Runs envelope encryption + crypto-shredding verification, `423 ANCHOR_REQUIRED` AI forcing-function gate, 20-slip seeded-error test, Android 2-hour GPS soak check, and FHIR R4 / XES / BSA s.63 bundle validation.
* **Verification Gate:**
  * Execute `make gate-all` and `scripts/preflight.sh` and confirm all 4 tier gates exit `0`.

---

## 13. Pre-Event (`Phase P`) & 24-Hour Hackathon (`Phase E`) Schedule

### 13.1 Phase P — Pre-Event Spec Artifacts Only (Verify Against Event Rules `[verify]`)

| Step ID | Lane | Artifact / Task | Modules Covered | Spec Ref | Risk | Loop Type |
|---|---|---|---|---|---|---|
| **P1** | Lane A | `spec/transitions.yaml` + conformance vectors (`V-01`..`V-28`) from §4 transition table | Module 1.5, 1.6 | §4, §5 | HIGH | FULL |
| **P2** | Lane A | `db/01_schema.sql` + `db/02_roles.sql`; load into PG16 and run FK/constraint scan (`ST-3`) | Module 1.2 | §7 | HIGH | FULL |
| **P3** | Lane A | `spec/rhp1.qnt` Quint spec; `quint run safety` ($\ge 20,000$ samples); vacuity checks | Module 1.6 | §12 | HIGH | FULL |
| **P4** | Lane B | `spec/profiles.json` signed profile file + $T_{\max}$ validator (`I13`, `ST-2`) | Module 1.3 | §6 | MED | FAST (FULL on guard) |
| **P5** | Lane B | `db/03_seed.sql` synthetic Karnataka obstetric network (`REAL_DATA=0`) | Module 1.3 | §2, §10 | LOW | FAST |
| **P6** | Lane B | Run §21 pre-event verification checklist (Exotel trial, iOS Safari noble JS, LAN QR) | Pre-Flight | §21 | LOW | FAST |

### 13.2 Phase E — 24-Hour At-Event Execution Plan

| Step ID | Hours | Lane A (Person A — Backend / Proof) | Lane B (Person B — Monitor / Clients / Reach) | Modules | Risk | Gate |
|---|---|---|---|---|---|---|
| **E0** | `H00–H02` | Repo init, `docker-compose.yml`, DDL load, seed, `transitions.yaml` loader, JCS parity | PWA shell, `ModeBanner`, rotating-QR judge admission (`JudgeJoin.tsx`) | Mod 1.1–1.5, 7.1–7.2 | MED | — |
| **E1** | `H02–H06` | `apply_command()` steps 1–10: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `DECLINE` | `ClinicianCard.tsx`, `ReceivingDesk.tsx`, `JudgeDesk.tsx`, SSE with per-event authz | Mod 2.1–3.4, 5.4, 7.3–7.5 | HIGH | — |
| **E2** | `H06–H09` | Two-phase `poller.py`, visibility-timeout `relay.py`, `TIMEOUT`, notice ladder ($0, A/4, 3A/4$) | `ArenaBigScreen.tsx`; Independent Python `monitor/monitor.py` (separate workspace) | Mod 4.1, 5.1–5.3, 5.5, 7.6 | HIGH | — |
| **E3** | `H09–H12` | Hash chain, `witness/signer.py` (UID 1002), 5s Merkle checkpoints, inclusion proofs | Pure-JS browser verifier (`verifier.ts` with `@noble`), `tamper.sh`, `cold_sign_restore.py` | Mod 6.1–6.3 | HIGH | — |
| **E4** | `H12–H14` | `test_race200.py`, mutation suite `M1`–`M6`, conformance vector runner | `BROKEN_BUILD` scratch DB (`make_scratch.sh`) + flashing red banner | Mod 4.2–4.4 | HIGH | **G0 = T0 Pass** |
| **E5** | `H14–H17` | `COUNTER`/`CONFIRM_COUNTER`, 6 arrival cases, `CLOSE` taxonomy, `transport.py`, Mapbox ETA | `DispatcherConsole.tsx` (proxy entry + replay scrubber), `AmbulancePwa.tsx` (GPS + advisories) | Mod 3.5–3.6, 8.1–8.4 | HIGH | **G1 = T1 Pass** |
| **E6** | `H17–H20` | Full F14 idempotency matrix, stale epoch/version fencing tests, Toxiproxy chaos suite | `exotel_ivr.py` (AMD + Press-1 gate + PIN), `dlt_sms.py`, `paper_code.py` (mod-37) | Mod 9.1–9.5, 12.1 | HIGH | **G2 = T2 Pass** |
| **E7** | `H20–H22` | T3 extras (if G0–G2 green) or test-driven bug fixes; run `ST-1`..`ST-5` | Record MP4 fallback clips (Clips A, B, C, D); run 30s proof loop rehearsal $\times 3$ | Mod 10, 11, 12.2–12.3 | MED | **G3 = Rehearsal** |
| **E8** | `H22–H24` | **Hard Code Freeze at H22:** config-only adjustments, `preflight.sh` | Final pitch & device choreography rehearsal, backup laptop + phone hotspot ready | All | LOW | **FREEZE** |

---

## 14. 30-Second Live Proof Loop & Reconciled 6-Month Pilot Cost

### 14.1 Second-by-Second 30s Live Proof Loop (`DEMO_FAST`, Closure F16)

| Window | Operator / Judge Action | Visible System & Monitor Result | Pre-Recorded Fallback |
|---|---|---|---|
| `0–4 s` | Judges scan rotating QR on Big Screen; two become hospital desks `D1`, `D2` | Two judge desks join live (admission cap $\le 20$) | `clip_A_qr_race.mp4` |
| `4–7 s` | Lane B creates a `PARALLEL2` referral | Both `D1` and `D2` receive live SSE offer simultaneously | `clip_A_qr_race.mp4` |
| `7–12 s` | Both judges press **Accept** simultaneously | Exactly one receives `200 OK` (lease granted, `epoch=1`); the other receives `409 LEASE_HELD`; Monitor stays **GREEN** | `clip_B_single_lease.mp4` |
| `12–18 s` | Operator flips `BROKEN_BUILD=1` (flashing red banner: `BROKEN BUILD — SCRATCH DB`), spawns referral, both press Accept | Both receive `200 OK` (double lease); Independent Monitor turns **RED (`I2`)** within $\le 2\text{ s}$ | `clip_C_broken_build.mp4` |
| `18–21 s` | Operator flips back to `BROKEN_BUILD=0`, spawns fresh referral | Monitor returns **GREEN** | `clip_C_broken_build.mp4` |
| `21–27 s` | Operator runs `scripts/tamper.sh` (`psql` edits one event row in scratch DB as superuser) | Judge-phone pure-JS verifier prints `BROKEN referral=... seq=... kind=HASH` | `clip_D_tamper_recap.mp4` |
| `27–30 s` | Operator opens Recap Overlay | Shows live-measured `I1`–`I16` evaluation counters and live-measured p50/p95 commit latency (zero pre-claimed numbers) | `clip_D_tamper_recap.mp4` |

### 14.2 Reconciled 6-Month Pilot Cloud Cost (`AWS ap-south-1`, Closure F18 `[verify]`)

| Infrastructure / Service Component | Monthly Cost (USD) | 6-Month Cost (USD) | Reconciliation Note |
|---|---|---|---|
| Managed PostgreSQL 16 Multi-AZ (`db.t4g.medium`) | $\$95.00$ | $\$570.00$ | Synchronous standby for contract durability |
| Storage ($2 \times 100\text{ GB gp3}$) | $\$23.00$ | $\$138.00$ | Primary + standby volumes |
| Application Load Balancer (ALB) | $\$22.00$ | $\$132.00$ | TLS termination & SSE routing |
| **Base Database & Edge Subtotal** | **$\$140.00$** | **$\$840.00$** | Matches Report 3's $\$810$ within $\$30$ ALB/LCU rounding |
| $2 \times$ Small Application VMs (API, Poller, Relay, Monitor, Witness) | $\$26.00$ | $\$156.00$ | No Kubernetes overhead |
| Backups & S3 Object Lock (Witness Archive) | $\$8.00$ | $\$48.00$ | Nightly logical backup + WAL archive |
| Logs & Monitoring (180-day CERT-In retention) | $\$10.00$ | $\$60.00$ | In-India log retention |
| Data Transfer | $\$6.00$ | $\$36.00$ | Outbound SSE / API traffic |
| **Subtotal with Application Tier** | **$\$190.00$** | **$\$1,140.00$** | Aligns with lean app-tier estimates |
| Telephony & DLT SMS Sandbox/Pilot Allowance | $\$25.00$ | $\$150.00$ | Outbound IVR + static SMS alerts |
| $10\%$ Operational Contingency (on $\$215.00/\text{mo}$) | $\$21.50$ | $\$129.00$ | Buffer for traffic spikes |
| **Locked Planning Total** | **$\$236.50/\text{mo}$** | **$\$1,419.00$ ($\approx \$1,420$)** | Reconciles all prior figures into range $\$1,140\text{–}\$1,500$ |

---

## 15. Definition of Done & Tier Acceptance Gates (§24)

| Tier | Measured Acceptance Criteria (All Must Pass with Raw Command Output) |
|---|---|
| **T0** | `race200` passes: exactly 1 of 200 concurrent requests returns `200`, DB shows 1 `ACCEPTED` offer, `seq` is gap-free, deadlock delta $= 0$; `M1`–`M6` each trip their named checker; Independent Runtime Monitor shows `0` violations over a 10-minute randomised Hypothesis + chaos run; `quint run safety` passes ($\ge 20,000$ samples) and all 4 vacuity checks fail as required; Browser Verifier names the exact edited `seq` on a tampered row; `BROKEN_BUILD=1` turns Monitor red in $\le 2\text{ s}$ and green after switch-back; `DEMO_FAST` silence-to-dispatcher escalation measured $\le 25\text{ s}$. |
| **T1** | Proxy entry and direct API entry yield identical state and event sequence in 20 paired runs; Dispatcher Console assigns after `ESCALATED_TO_DISPATCHER`; client-side replay scrubber reproduces the exact final state from the event log. |
| **T2** | $20/20$ voice ACKs are recorded only after database commit; voicemail/AMD-machine call yields $0$ ACKs across 5 trials; Exotel webhook p95 latency $\le 2\text{ s}$; paper-code single-symbol errors and adjacent transpositions are rejected $100\%$ across $1,000$ mutated codes. |
| **T3** | Android client keeps GPS active $\ge 2\text{ h}$ with screen off on the demo device; AI draft is withheld (`423 ANCHOR_REQUIRED`) until clinician commits anchors (API test); 20-slip seeded-error gate achieves critical-error rubber-stamp $\le 5\%$ and silent omission $\le 1\%$; FHIR R4 bundle passes schema validator. |