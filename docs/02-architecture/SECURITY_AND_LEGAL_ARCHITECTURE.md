# ReferralHandshake (Protocol RHP-1) — Security, Privacy, Cryptographic & Legal Architecture

**System:** Referral Handshake Protocol (RHP-1) + Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru)  
**Document Authority:** Derived strictly from `ReferralHandshake_LOCKED_Problem_Statement_v7.md` (Priority 1) > Research findings tagged `[V]` (Priority 2) > `ReferralHandshake_v8_LOCKED_Solution.md` (Priority 3) > `ReferralHandshake_FINAL_LOCKED_Architecture.md` (Priority 4) > `ReferralHandshake_3Gem_Antigravity_Workflow.md` (Priority 5).  
**Operating Posture:** Synthetic data only (`REAL_DATA=0`) for hackathon demonstration; architected as "designed to comply" with explicit policy parameters for district pilot deployment.

> **Evidence & Status Tag Legend:**  
> - **`[V]`** Verified from primary research or official technical specifications.  
> - **`[V*]`** Verified from secondary, vendor, or legal commentary sources; confirm primary text before pilot deployment.  
> - **`[CONFLICT]`** Primary/secondary sources disagree; conservative posture enforced and discrepancy documented.  
> - **`[GAP]`** Unsettled in law or unverified in public documentation; parameterized in code and assigned an owner.  
> - **`[verify]`** Pre-event operational verification test scheduled (§11).  
> - **Weakness Status Tags:** **`CLOSED`** (deterministic technical control + named automated test) · **`BOUNDED`** (stated technical residual + runtime monitor/alarm) · **`OPEN`** (external legal/operational dependency + assigned owner + closing evidence).

---

## 1. Security Architecture Overview & Core Design Principles

### 1.1 The Handover-Record Minimisation Principle
ReferralHandshake is an **inter-facility handover coordination protocol**, not a longitudinal Electronic Health Record (EHR) repository (v7 §12, v8 §10.3).
1. **No Longitudinal Fetch:** The platform never queries external health repositories (e.g., ABDM HIU pulls) because fetching historical records under the ABDM Health Data Management Policy (HDMP) requires explicit electronic patient consent (M3 artefact) that an unconscious or critically ill obstetric patient cannot provide, and emergency consent-override mechanisms remain unverified `[GAP]`.
2. **Dual-Plane Storage Separation:**
   - **Ephemeral Clinical Plane (`clinical_payload`, `event_secret`):** Holds the point-of-care clinician-authored ISBAR + Dakshata summary, envelope-encrypted under a per-referral Data Encryption Key ($\text{DEK}$) and shared strictly with facilities holding an active `payload_grant`. Upon retention expiry, the $\text{DEK}$ is destroyed (crypto-shredded).
   - **Long-Lived Pseudonymous Audit Plane (`event`, `checkpoint`, `rejected_command`):** Holds the hash-chained state transition log containing zero Protected Health Information (PHI), enforced at both the API layer (`Pydantic extra='forbid'`) and the database engine (`CHECK (rhp_detail_ok(type, detail))`).
3. **Never Block Care (Invariant I3):** No security control, missing clinical field (`mgso4_status = 'UNKNOWN'`), network partition, or PIN lockout on a single session may ever block ambulance dispatch (`TR_UPDATE`) or physical clinical care. Existing telephone and paper emergency procedures remain primary at all times.

### 1.2 Defense-in-Depth Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ EDGE & ADMISSION LAYER                                                                          │
│  • Cloudflare WAF + Turnstile challenge before minting any JUDGE_DESK session (cap = 20)        │
│  • Rotating single-use QR (jti, 20 s TTL, 15 s rotation) + pinned Witness & Cold Ed25519 pubkeys│
│  • LAN Fail-Closed Mode: refuses boot if REAL_DATA=1; disables HTTP PIN entry; cap = 20         │
└───────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ APPLICATION SECURITY LAYER (FastAPI / Python 3.12 / apply_command() Steps 1–7)                  │
│  • Step 1: Scoped Idempotency (actor_id, key) + SHA-256(JCS(payload)) + pg_try_advisory_xact_lock│
│  • Step 2: Opaque Session Token -> SHA-256 lookup -> Device + Roster validity [valid_from/to]   │
│  • Step 3: Argon2id PIN verify; failures committed via AUTONOMOUS connection per session/call   │
│  • Step 4: Global Lock Order (referral FOR UPDATE first) + GUC rhp.locked_referral + Monotone ts│
│  • Step 5: Object-Level Authz (BOLA), Role Slot Matrix, Fencing (version -> 412, epoch -> 409)  │
│  • Step 6–7: Frozen transitions.yaml guard + I15 Live Resource Confirmation TTL check           │
└───────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ DATA, CRYPTOGRAPHY & INTEGRITY LAYER (PostgreSQL 16 Primary, synchronous_commit=on)             │
│  • Envelope Encryption: per-referral AES-256-GCM DEK wrapped by monthly AES-KW KEK epoch        │
│  • PHI-Free Metadata: rhp_detail_ok() JSONB allowlist CHECK + 4-hour bucket / k>=5 export guard │
│  • Append-Only Triggers: event_ao, checkpoint_ao, rejected_ao + rhp_event_guard hash-chain check│
│  • Least-Privilege DB Roles: rhp_app (no UPDATE/DELETE on audit), rhp_monitor (RO), rhp_witness │
└───────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ OUT-OF-BAND VERIFICATION & WITNESS LAYER                                                        │
│  • Witness Signer (OS user rhp-sign, UID 1002, mode 0400): 5 s C2SP-style Merkle checkpoints    │
│  • Pure-JS Browser Verifier (@noble/curves/ed25519, @noble/hashes/sha256): O(log N) proof check │
│  • Independent Python Monitor (Person B, UID 1001, rhp_monitor): differential state/chain fold  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Security & Legal Defect Closure Traceability (v8 D-Series & Final Architecture F-Series)

| Defect ID | Vulnerability / Gap in Earlier Drafts | Locked Architectural Closure in RHP-1 | Invariants | Verification Test |
|---|---|---|---|---|
| **D5 / §19** | Overclaimed "mathematically impenetrable", "BSA s.63-ready/certified", "zero silent drops" | Strict Claims Register (§10.4); BSA s.63 export bundle generated with Part A/B templates without claiming certification; all metrics measured live | I5 | `ST-5` (`forbidden_word_scan`), `T-L3` |
| **D9** | "Crypto-shredding by deleting a per-referral salt" is not cryptographic erasure | Per-referral AES-256-GCM $\text{DEK}$ wrapped by monthly $\text{KEK}$ epoch; deleting `wrapped_dek` + ciphertext and rotating $\text{KEK}$ epoch destroys WAL/backup recoverability (§5) | I10 | `T-P5` (`shred_restore_test`) |
| **D10 / F8** | Hash chains alone cannot stop a sysadmin from rewriting history or restoring an old backup | Separate-OS-user Ed25519 witness signer broadcasting 5 s Merkle roots to independent witnesses + cold-key-signed `RESTORE` checkpoint (§6) | I5 | `T-F8` (`tamper_vs_restore`), `T-S2` |
| **D11** | Static QR minting JWTs allowed bot floods to exhaust rate limits | Rotating single-use QR (`jti`, 20 s TTL) + Cloudflare Turnstile challenge prior to session creation + hard cap of 20 judge desks + fail-closed LAN mode (§4.1) | I6 | `T-N7`, `T-D4` |
| **D12 / F7** | Shared ward tablet lacked "user verified" step; PIN brute-force or rival lockout-DoS on facility | Argon2id PIN verified server-side on every mutating command; failures committed via autonomous txn scoped strictly to `(session_id \| call_sid)`; AMD + press-1 gate on voice (§3) | I6 | `T-F7` (`pin_lockout_scope`) |
| **D18** | Unlawful staff telemetry and Goodhart gaming via countdown clocks | DPDP s.7(i) prior written notice, HR siloing, priority queue UI without countdown timers, APOT handover metric separated from acceptance (§8.2) | — | `T-K2` |
| **F9** | Free-text `event.detail` risked leaking patient identifiers into the permanent audit log | Per-event-type key allowlist (`rhp_allowed`) + value regex/type constraint (`rhp_detail_ok`) in both Pydantic and PostgreSQL + $4\text{ h}$ bucketing and $k \ge 5$ suppression (§5.4) | I11 | `T-F9` (`detail_check_fuzz`) |
| **F10** | Open SSE streams continued receiving clinical updates after an offer was declined or superseded | Per-event grant evaluation at emit time + 15 s heartbeat re-check + immediate `GRANT_REVOKED` control frame + DOM state wipe (§4.3) | I10 | `T-F10` (`sse_revoke`) |
| **F11** | Host clock steps could break event ordering or prematurely expire deadlines | `GREATEST(clock_timestamp(), referral.head_ts)` under referral row lock + chrony slew-only + $>2\text{ s}$ NTP offset alarm (§6.1) | I16 | `T-F11` (`clock_step`) |
| **F12** | Queued offline `ACCEPT` replayed hours later could seize a lease on stale resource checks | `offer_resource_confirmation.expires_at` enforced at `server_ts` (I15); returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` forcing live reconfirmation (§3.5) | I15 | `T-F12` (`offline_stale`) |
| **F14** | Replay of failed or in-flight commands had undefined security/audit behavior | Step 1 idempotency scoped to `(actor_id, key)` with `pg_try_advisory_xact_lock`; domain rejections logged in `rejected_command` via `SAVEPOINT` rollback (§3.4) | I4, I8 | `T-F14` (`idem_matrix`) |
| **F17** | AI agent or single developer could introduce a shared bug into both server and monitor | Person A writes server/Quint/`transitions.yaml`; Person B writes Python monitor from §3 prose alone using read-only role `rhp_monitor` + 6 mutation tests (§9.2) | I1–I16 | `T-F17` (`mutation_suite`) |
| **F20** | `BROKEN_BUILD=1` demo switch risked running against real data or the main database | Hard boot abort (`exit 78`) if `REAL_DATA=1` or DSN $\neq$ `rhp_scratch_broken` or cross-DB auth succeeds; dedicated scratch key and flashing red banner (§7.3) | I2 | `T-F20` (`broken_isolation`) |

---

## 2. Identity, Device Enrollment, Roster Authority & Session Lifecycle

### 2.1 Roster-Based Duty Roles (v7 §8, v8 §11, FINAL §7)
Offers and administrative permissions are bound to an institutional **duty role slot** at a registered facility (`roster`), never to an ad-hoc personal account:
- **Valid Role Slots (`roster.role_slot`):** `'NURSE'`, `'CMO'`, `'CONSULTANT'`, `'CLINICIAN'`, `'EMT'`, `'DISPATCHER'`, `'ADMIN'`, `'JUDGE_DESK'`.
- **Temporal & Slot Scoping:** Each `roster` record specifies `facility_id`, `role_slot`, `slot_no` ($1 \dots S$, where $S \le 3$), `phone_e164` (for Exotel outbound IVR), `pin_hash` (Argon2id), and an active window `[valid_from, valid_to)`.
- **Constraint:** `UNIQUE (facility_id, role_slot, slot_no, valid_from)` prevents overlapping duplicate slot assignments.

### 2.2 Three-Step Cryptographic Device Enrollment (`F7`)
To prevent rogue devices from polling endpoints or spoofing acknowledgements, every browser desk or Android client must complete a one-time enrollment ceremony before obtaining an operational session:

```
┌──────────────┐                  ┌─────────────────────┐                  ┌────────────────────┐
│  ADMIN Desk  │                  │  FastAPI Core (DB)  │                  │ Field Device (PWA/ │
│ (PIN auth'd) │                  │                     │                  │   Android Kotlin)  │
└──────┬───────┘                  └──────────┬──────────┘                  └─────────┬──────────┘
       │ 1. POST /v1/admin/tickets           │                                       │
       │    {roster_id, ttl_min: 15}         │                                       │
       │────────────────────────────────────▶│                                       │
       │    INSERT enrollment_ticket         │                                       │
       │    (token_hash = SHA256(raw_tkt))   │                                       │
       │◀────────────────────────────────────│                                       │
       │ 2. Out-of-band QR / one-time code   │                                       │
       │────────────────────────────────────────────────────────────────────────────▶│
       │                                     │      3. Generate Ed25519 keypair      │
       │                                     │         (pubkey 32B, privkey in       │
       │                                     │          IndexedDB / Android Keystore)│
       │                                     │      4. POST /v1/auth/enroll          │
       │                                     │         {raw_tkt, pubkey, platform}   │
       │                                     │◀──────────────────────────────────────│
       │                                     │ 5. Verify SHA256(raw_tkt), unused,    │
       │                                     │    unexpired -> mark used_at,         │
       │                                     │    INSERT device, INSERT session      │
       │                                     │    (token_hash = SHA256(raw_sess))    │
       │                                     │──────────────────────────────────────▶│
       │                                     │    Set-Cookie: rhp_sess=<raw_sess>;   │
       │                                     │    HttpOnly; Secure; SameSite=Strict  │
```

### 2.3 Reference Implementation: Enrollment & Session Verification (`Python 3.12 / psycopg3`)

```python
import hashlib
import secrets
from datetime import datetime, timezone
from dataclasses import dataclass
from uuid import UUID, uuid4
import psycopg

@dataclass(frozen=True)
class AuthenticatedSession:
    session_id: UUID
    roster_id: UUID
    facility_id: UUID
    role_slot: str
    slot_no: int
    device_id: UUID | None
    call_sid: str | None
    pin_hash: str | None
    pin_failed: int
    pin_locked_until: datetime | None
    valid: bool

def sha256_bytes(raw: str | bytes) -> bytes:
    data = raw.encode("utf-8") if isinstance(raw, str) else raw
    return hashlib.sha256(data).digest()

def issue_enrollment_ticket(conn: psycopg.Connection, admin_sess: AuthenticatedSession, target_roster_id: UUID) -> str:
    if admin_sess.role_slot != "ADMIN":
        raise PermissionError("403_ADMIN_ROLE_REQUIRED")
    raw_ticket = secrets.token_urlsafe(32)
    ticket_hash = sha256_bytes(raw_ticket)
    conn.execute(
        """
        INSERT INTO enrollment_ticket (id, roster_id, token_hash, issued_by, expires_at)
        VALUES (%s, %s, %s, %s, clock_timestamp() + interval '15 minutes')
        """,
        (uuid4(), target_roster_id, ticket_hash, admin_sess.roster_id),
    )
    return raw_ticket

def redeem_enrollment_ticket(
    conn: psycopg.Connection, raw_ticket: str, pubkey_bytes: bytes, platform: str
) -> tuple[UUID, str]:
    if len(pubkey_bytes) != 32:
        raise ValueError("422_INVALID_ED25519_PUBKEY_LENGTH")
    t_hash = sha256_bytes(raw_ticket)
    row = conn.execute(
        """
        SELECT id, roster_id, expires_at, used_at
        FROM enrollment_ticket
        WHERE token_hash = %s
        FOR UPDATE
        """,
        (t_hash,),
    ).fetchone()
    now_ts = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    if not row or row.used_at is not None or row.expires_at <= now_ts:
        raise PermissionError("401_TICKET_INVALID_OR_EXPIRED")

    device_id = uuid4()
    session_id = uuid4()
    raw_session_token = secrets.token_urlsafe(32)
    s_hash = sha256_bytes(raw_session_token)

    conn.execute(
        """
        INSERT INTO device (id, roster_id, pubkey, platform, registered_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (device_id, row.roster_id, pubkey_bytes, platform, now_ts),
    )
    conn.execute(
        """
        UPDATE enrollment_ticket
        SET used_at = %s, device_id = %s
        WHERE id = %s
        """,
        (now_ts, device_id, row.id),
    )
    conn.execute(
        """
        INSERT INTO session (id, token_hash, roster_id, device_id, created_at, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s + interval '12 hours')
        """,
        (session_id, s_hash, row.roster_id, device_id, now_ts, now_ts),
    )
    return device_id, raw_session_token

def load_session(conn: psycopg.Connection, raw_token: str) -> AuthenticatedSession:
    s_hash = sha256_bytes(raw_token)
    row = conn.execute(
        """
        SELECT s.id AS session_id, s.roster_id, r.facility_id, r.role_slot, r.slot_no,
               s.device_id, s.call_sid, r.pin_hash, s.pin_failed, s.pin_locked_until,
               (s.revoked_at IS NULL AND s.expires_at > clock_timestamp()
                AND (d.id IS NULL OR d.revoked_at IS NULL)
                AND r.valid_from <= clock_timestamp()
                AND (r.valid_to IS NULL OR r.valid_to > clock_timestamp())
                AND f.active = true) AS is_valid
        FROM session s
        JOIN roster r ON r.id = s.roster_id
        JOIN facility f ON f.id = r.facility_id
        LEFT JOIN device d ON d.id = s.device_id
        WHERE s.token_hash = %s
        """,
        (s_hash,),
    ).fetchone()
    if not row:
        raise PermissionError("401_SESSION_NOT_FOUND")
    return AuthenticatedSession(
        session_id=row.session_id,
        roster_id=row.roster_id,
        facility_id=row.facility_id,
        role_slot=row.role_slot,
        slot_no=row.slot_no,
        device_id=row.device_id,
        call_sid=row.call_sid,
        pin_hash=row.pin_hash,
        pin_failed=row.pin_failed,
        pin_locked_until=row.pin_locked_until,
        valid=bool(row.is_valid),
    )
```

---

## 3. Autonomous PIN Verification, Lockout-DoS Prevention & Channel Authority

### 3.1 Closing the Shared-Tablet "User Present vs. User Verified" Gap (`D12`, `F7`, `I6`)
In casualty wards and PHCs, a single tablet or desktop browser is shared across shift handovers. Under NIST SP 800-63B terminology, an active browser cookie proves only that a registered device is present (**User Present / UP**), not that an authorized clinician is at the keyboard (**User Verified / UV**).
- **Rule:** Viewing the incoming priority queue or opening a referral card (`ACK`) requires an active rostered session (`UP`).
- **Rule:** Every commitment or state-mutating clinical/contract action (`RESOURCE_CONFIRM`, `ACCEPT`, `COUNTER`, `CONFIRM_COUNTER`, `DECLINE`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`, `CANCEL`, `CLOSE`, `REVOKE_GRANT`) has `cmd.needs_pin = True` and requires live verification of the actor's 4-to-6 digit PIN against `roster.pin_hash` (`UV`), unless executed by the system timer poller (`SYSTEM_SESSION`).

### 3.2 Autonomous PIN Failure Accounting & Per-Session Lockout Scope (`F7`)
Two subtle vulnerabilities arise in naive PIN implementations:
1. **Transaction Rollback Erases Failures:** If `pin_failed` is incremented inside the main command transaction and the transaction subsequently raises an exception or rolls back on `403 PIN_INVALID`, the failure counter resets to zero, enabling unlimited brute-force guessing.
2. **Facility-Wide Lockout Denial of Service (Lockout-DoS):** If `pin_failed` is stored on `roster` or `facility`, a competing hospital or malicious actor who obtains a session token (or spoofs a call) can intentionally enter 3 wrong PINs to lock out the casualty medical officer on all other devices at that facility.

**Locked RHP-1 Closure:**
- `pin_failed` and `pin_locked_until` are columns on `session(id)` (which is keyed to a single `device_id` or a single Exotel `call_sid`), **never** on `roster` or `facility`.
- Step 3 of `apply_command()` verifies the PIN using **Argon2id** (`time_cost=2, memory_cost=65536, parallelism=2`, tuned to $\approx 100\text{ ms}$ on the demo host).
- On a mismatch, `autonomous_pin_failed(dsn, session_id, referral_id)` opens an **independent autocommit database connection**, increments `session.pin_failed`, applies the exponential backoff schedule, and on strike 3 inserts an outbox `PROXY_PAGE` alert to the dispatcher.
- **Backoff Schedule:**
  - Strike 1 (`pin_failed = 1`): immediate retry allowed ($0\text{ s}$ delay), returns `403 PIN_INVALID`.
  - Strike 2 (`pin_failed = 2`): `pin_locked_until = clock_timestamp() + interval '5 seconds'`.
  - Strike 3 (`pin_failed = 3`): `pin_locked_until = clock_timestamp() + interval '30 seconds'`, emits `PIN_LOCKED` event, and pages dispatcher.
  - Strike $\ge 4$ (`pin_failed >= 4`): `pin_locked_until = clock_timestamp() + interval '120 seconds'`.
  - If $\ge 3$ distinct sessions for the same `roster_id` enter lockout within $30\text{ minutes}$ (indicative of SIM swap or credential compromise), the dispatcher console raises a `ROSTER_SLOT_SUSPENSION_RECOMMENDED` alert for admin review (`I4` in §10.2).

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)

def autonomous_pin_failed(dsn: str, session_id: UUID) -> tuple[int, datetime | None]:
    """Commits PIN failure increment on an independent connection so rollback never erases it."""
    with psycopg.connect(dsn, autocommit=True) as auto_conn:
        row = auto_conn.execute(
            """
            UPDATE session
            SET pin_failed = pin_failed + 1,
                pin_locked_until = CASE
                    WHEN pin_failed + 1 = 1 THEN NULL
                    WHEN pin_failed + 1 = 2 THEN clock_timestamp() + interval '5 seconds'
                    WHEN pin_failed + 1 = 3 THEN clock_timestamp() + interval '30 seconds'
                    ELSE clock_timestamp() + interval '120 seconds'
                END
            WHERE id = %s
            RETURNING pin_failed, pin_locked_until
            """,
            (session_id,),
        ).fetchone()
        return row.pin_failed, row.pin_locked_until

def verify_pin_or_raise(dsn: str, conn: psycopg.Connection, sess: AuthenticatedSession, candidate_pin: str | None) -> None:
    now_ts = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    if sess.pin_locked_until is not None and sess.pin_locked_until > now_ts:
        raise PermissionError("429_PIN_LOCKED")
    if not candidate_pin or not sess.pin_hash:
        autonomous_pin_failed(dsn, sess.session_id)
        raise PermissionError("403_PIN_INVALID")
    try:
        ph.verify(sess.pin_hash, candidate_pin)
    except VerifyMismatchError:
        strikes, _ = autonomous_pin_failed(dsn, sess.session_id)
        if strikes >= 3:
            raise PermissionError("429_PIN_LOCKED")
        raise PermissionError("403_PIN_INVALID")
    # Reset failure counter on valid PIN
    if sess.pin_failed > 0:
        with psycopg.connect(dsn, autocommit=True) as auto_conn:
            auto_conn.execute(
                "UPDATE session SET pin_failed = 0, pin_locked_until = NULL WHERE id = %s",
                (sess.session_id,),
            )
```

### 3.3 Object-Level (BOLA), Function-Level & Fencing Authorization Matrix (Step 5)
Every command executes `authorize(conn, referral, offers, sess, cmd)` and `fence(referral, cmd)` **after** acquiring `SELECT * FROM referral WHERE id = %s FOR UPDATE` in Step 4:

| Command Type | Permitted `role_slot` | Object-Level (BOLA) Facility Requirement | PIN Required (`UV`) | Fencing Precondition |
|---|---|---|---|---|
| `CREATE` | `CLINICIAN`, `DISPATCHER` (proxy) | `sess.facility_id == cmd.origin_facility_id` (or `DISPATCHER` with `proxy=True`) | Yes | None (`version = 1`, `lease_epoch = 0`) |
| `ACK` | `NURSE`, `CMO`, `CONSULTANT`, `DISPATCHER` (proxy) | Target `offer.facility_id == sess.facility_id` and `offer.status == 'OPEN'` | No (`UP` + press-1 on voice) | `expected_version` matches `referral.version` |
| `RESOURCE_CONFIRM` | `NURSE`, `CMO`, `CONSULTANT` | Target `offer.facility_id == sess.facility_id` and `offer.status IN ('OPEN','ACKED','SOFT_OPEN')` | Yes | `expected_version` matches |
| `ACCEPT` | `NURSE`, `CMO`, `CONSULTANT`, `DISPATCHER` (proxy) | Target `offer.facility_id == sess.facility_id`; all required capabilities confirmed & unexpired (`I15`) | Yes | `expected_version` matches (`412` on stale); `referral.lease_offer_id IS NULL` (`409 LEASE_HELD` on lost race) |
| `COUNTER` | `CMO`, `CONSULTANT`, `NURSE` | Target `offer.facility_id == sess.facility_id` and `counter_round < 2` | Yes | `expected_version` matches |
| `CONFIRM_COUNTER` | `CLINICIAN`, `DISPATCHER` (proxy) | `sess.facility_id == referral.origin_facility_id` | Yes | `expected_version` matches; `referral.lease_offer_id IS NULL` |
| `DECLINE` | `NURSE`, `CMO`, `CONSULTANT`, `DISPATCHER` (proxy) | Target `offer.facility_id == sess.facility_id` | Yes | `expected_version` matches |
| `ARRIVAL_REJECTED` | `NURSE`, `CMO`, `CONSULTANT`, `EMT`, `DISPATCHER` | `sess.facility_id == referral.lease_facility_id` or `EMT`/`DISPATCHER` | Yes | `expected_version` & `expected_epoch == referral.lease_epoch` (`412` if stale) |
| `DISPATCHER_ASSIGN` | `DISPATCHER` | `sess.role_slot == 'DISPATCHER'`; `referral.hs_state == 'ESCALATED_TO_DISPATCHER'` (or explicit `override` reason) | Yes | `expected_version` & `expected_epoch` match |
| `TR_UPDATE` | `EMT`, `DISPATCHER`, `NURSE`/`CMO` (on `ARRIVED`) | Assigned ambulance device or `DISPATCHER` or receiving desk (for `ARRIVED`); **never checks `hs_state` (`I3`)** | Yes (for `ARRIVED` / `HANDED_OVER`) | Monotone transport state progression |
| `CANCEL` | `CLINICIAN`, `DISPATCHER` | `sess.facility_id == referral.origin_facility_id` or `DISPATCHER` | Yes | `expected_version` matches |
| `CLOSE` | `NURSE`, `CMO`, `CONSULTANT`, `DISPATCHER`, `SYSTEM` | `sess.facility_id == referral.lease_facility_id` or `DISPATCHER` (or `SYSTEM` after $2 \times \text{CLOSURE}$ deadline) | Yes (except `SYSTEM`) | `expected_version` matches |

### 3.4 Scoped Idempotency & Deterministic Rejection Logging (`F14`, `I4`, `I8`)
1. **Step 1 Advisory Lock & Payload Fingerprint:** Before touching any referral row, `apply_command()` computes $h = \text{SHA-256}(\text{JCS}(\text{cmd.body\_for\_hash}()))$ and calls `pg_try_advisory_xact_lock(hashtextextended(f"{sess.roster_id}:{idem_key}", 0))`.
   - If the advisory lock returns `False`, a concurrent duplicate request with the same key is currently in flight -> immediately return `409 DUPLICATE_IN_FLIGHT`.
   - If `(actor_id, key)` exists in `idempotency` with a different `request_hash` -> return `422 KEY_REUSED_DIFFERENT_PAYLOAD`.
   - If `(actor_id, key)` exists with `status = 'DONE'` -> return the stored `http_status` and `response` JSON (exact replay, including stored `409`/`412`/`422` domain rejections).
2. **Savepoint Rollback for Domain Rejections:** In Step 4, after locking the `referral` row, `apply_command()` issues `SAVEPOINT sp_cmd`. If Step 5, 6, or 7 raises a deterministic domain rejection (`403`, `409`, `412`, `422`), the transaction executes `ROLLBACK TO SAVEPOINT sp_cmd` (retaining the `referral` lock acquired prior to the savepoint), inserts an immutable audit record into `rejected_command`, marks `idempotency.status = 'DONE'` with the error payload, and commits.

### 3.5 Offline Staleness & Live Resource Reconfirmation (`F12`, `I15`)
- Resource confirmations (`offer_resource_confirmation`) are strictly online commands carrying `expires_at = server_ts + profile.confirm_ttl` ($120\text{ s}$ in `PILOT_OB_CRITICAL`, $10\text{ s}$ in `DEMO_FAST`).
- An offline click on "Accept" in the PWA or Android client is queued in the local outbox and displayed in the UI as `"Pending — Not Confirmed (Offline)"`.
- When connectivity returns and the request reaches `apply_command()`, Step 7 checks:
  1. Is `offer.status` still in `('OPEN', 'ACKED', 'SOFT_OPEN')`? If the offer timed out or another facility accepted, return `409 LATE_ACCEPT_REJECTED` or `409 LEASE_HELD`.
  2. For every required capability $c \in \text{need\_class\_requirement}(\text{referral.need\_class})$, does `offer_resource_confirmation` have a row with $\text{expires\_at} > \text{server\_ts}$? If any confirmation has expired ($\min(\text{expires\_at}) \le \text{server\_ts}$), return `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`. The client UI immediately opens a one-screen live reconfirmation modal.

### 3.6 Voice IVR Security (`F7`) & Paper Code Algebraic Checksum (§8)
1. **Outbound-Only Exotel IVR with AMD + Press-1 Gate:**
   - RHP-1 exposes **no inbound telephone number**, eliminating inbound war-dialing and caller-ID spoofing.
   - At notice rung $A/4$, the outbox relay triggers an outbound Exotel call to `roster.phone_e164` for slot $i$ at $A/4 + i \cdot \delta$.
   - **Voicemail / Auto-Attendant Defense (`F7`):** Carrier connection or Answering Machine Detection (AMD) alone **never** records an `ACK`. The callee must press `1` within $8\text{ s}$ ("Press 1 to hear an emergency referral"). Only when the Exotel webhook delivers `Digits="1"` with `AMDStatus="HUMAN"` does the server execute `apply_command(ACK, channel='VOICE')`.
   - **De-Identified Audio:** Pre-recorded native-speaker prompts (Kannada, Hindi, English) state the originating facility tier, reason code, and ETA. No patient name or demographic identifier is ever spoken.
   - **Webhook Deduplication & Budget:** Every Exotel callback inserts `(source='EXOTEL', external_id=CallSid+CallbackSeq, payload_sha256)` into `inbox` (`ON CONFLICT DO NOTHING`) and completes within a $2\text{ s}$ server budget (well inside Exotel's $5\text{ s}$ timeout `[V]`). Spoken "Acceptance recorded" plays **only** after `apply_command(ACCEPT)` commits.
2. **Paper Code Error-Detection Algebra (Crockford Base32 + Modulo 37):**
   - Each printed referral card carries a 9-character `paper_code`: 8 payload characters from Crockford's Base32 alphabet ($\Sigma_{32} = \texttt{0123456789ABCDEFGHJKMNPQRSTVWXYZ}$, encoding a 40-bit integer $N = \sum_{i=0}^{7} d_i \cdot 32^i$) followed by 1 check character $c = N \bmod 37$ mapped onto the 37-symbol extended alphabet $\Sigma_{37} = \Sigma_{32} \cup \{\texttt{*}, \texttt{\~}, \texttt{\$}, \texttt{=}, \texttt{U}\}$.
   - **Proof of $100\%$ Single-Symbol Error Detection:** Because $37$ is prime and $\gcd(32, 37) = 1$, $32^i \not\equiv 0 \pmod{37}$ for all $i \in \{0, \dots, 7\}$. A single-character substitution at position $i$ changing digit $d_i \to d'_i$ with $\Delta = d'_i - d_i \in [-31, 31] \setminus \{0\}$ shifts $N$ by:
     $$\Delta N \equiv \Delta \cdot 32^i \not\equiv 0 \pmod{37}$$
     since $37$ is prime and $1 \le |\Delta| \le 31 < 37$.
   - **Proof of $100\%$ Adjacent Transposition Detection:** Swapping adjacent distinct digits $a \neq b$ at positions $i+1$ and $i$ shifts $N$ by:
     $$\Delta N = (b \cdot 32^{i+1} + a \cdot 32^i) - (a \cdot 32^{i+1} + b \cdot 32^i) = (b - a) \cdot 31 \cdot 32^i$$
     Since $\gcd(31, 37) = 1$, $\gcd(32^i, 37) = 1$, and $1 \le |b - a| \le 31 < 37$, we have $\Delta N \not\equiv 0 \pmod{37}$.
   - **Rate Limit:** Paper code lookup (`POST /v1/paper/resolve`) is rate-limited to $10\text{ attempts/min}$ per session and returns only a link to the referral desk view (which still requires a valid rostered grant to view clinical payload).

---

## 4. Edge Defense, Rotating QR Admission & Real-Time Stream Security

### 4.1 Judge QR Admission & Fail-Closed LAN Mode (`D11`, FINAL §9)
During the Guarantee Arena live demo, judges scan a QR code on the big screen to join as competing hospital desks (`D1`, `D2`) or independent checkpoint verifiers. To prevent bot floods or stale QR replay:
1. **Rotating Single-Use QR Payload:** Every $15\text{ s}$, the big screen requests a fresh signed QR challenge token (`jti` UUID, $20\text{ s}$ TTL). The QR URL fragment encodes the pinned Ed25519 witness public key (`wk`) and cold public key (`ck`) so the judge's browser never trusts the server to supply its own verification keys:
   `https://<demo-domain>/join?jti=<uuid>&exp=<ts>#wk=<hex32>&ck=<hex32>`
2. **Cloudflare Turnstile + Admission Cap:** When a judge's phone hits `/join`, Cloudflare WAF + Turnstile verifies human interaction before the FastAPI server mints a `JUDGE_DESK` session. Active `JUDGE_DESK` sessions are capped at **20 concurrent desks** (`SELECT count(*) FROM session s JOIN roster r ON r.id=s.roster_id WHERE r.role_slot='JUDGE_DESK' AND s.revoked_at IS NULL AND s.expires_at > clock_timestamp()`).
3. **Fail-Closed LAN Mode:** If venue internet fails and the team switches to the local Wi-Fi hotspot (`LAN_MODE=1`):
   - The server **refuses to boot** (`sys.exit(78)`) if `REAL_DATA=1`.
   - Concurrent `JUDGE_DESK` sessions remain hard-capped at $20$.
   - Clinical PIN entry over plain HTTP is disabled for all non-demo roles (`JUDGE_DESK` desks in `DEMO_FAST` use pre-bound demo session tokens).
   - Because iOS Safari disables `window.crypto.subtle` on insecure HTTP LAN origins `[V]` and lacks native WebCrypto Ed25519 support `[V]`, the PWA bundles pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256` directly in the client build.

### 4.2 Strict Input Validation & Mass-Assignment Prevention
All FastAPI request models inherit from a strict base class that rejects unknown fields and floating-point numbers (preserving RFC 8785 JCS determinism):

```python
from pydantic import BaseModel, ConfigDict, field_validator

class StrictCommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    @field_validator("*", mode="before")
    @classmethod
    def forbid_floats(cls, v):
        if isinstance(v, float):
            raise ValueError("FLOATS_PROHIBITED_IN_RHP1_JCS")
        return v
```

### 4.3 Real-Time SSE Stream Security & Immediate Grant Revocation (`F10`, `I10`)
A critical privacy vulnerability in pub/sub referral platforms occurs when Hospital A opens an SSE stream upon receiving an offer, then declines (or is superseded when Hospital B accepts), yet Hospital A's open browser tab continues receiving live clinical observations and transport updates.

**Locked RHP-1 Stream Security Protocol (`I10`):**
1. **Per-Frame Grant Re-Evaluation:** The SSE broadcaster never broadcasts raw clinical frames to a room. Before writing any frame to a subscriber's socket—and on every $15\text{ s}$ heartbeat—the broadcaster verifies that `(subscriber.facility_id, referral_id)` has an active row in `payload_grant WHERE revoked_at IS NULL` (or `subscriber.role_slot == 'DISPATCHER'`).
2. **Immediate `GRANT_REVOKED` Control Frame:** Whenever `apply_command()` executes `DECLINE`, `CANCEL`, `ARRIVAL_REJECTED`, `REVOKE_GRANT`, final `TIMEOUT`, or supersedes open offers upon `ACCEPT` / `CONFIRM_COUNTER(true)` / `DISPATCHER_ASSIGN`, Step 8 sets `payload_grant.revoked_at = ts` and Step 9 inserts an `outbox(channel='SSE', kind='GRANT_REVOKED')` row in the **same transaction**.
3. **Client DOM Purge:** In the next outbox relay cycle ($\le 250\text{ ms}$), the SSE hub emits:
   ```text
   event: GRANT_REVOKED
   id: 1042
   data: {"referral_id":"...","facility_id":"...","revoked_at_us":1763014200000000,"reason":"SUPERSEDED"}
   ```
   Upon receiving `GRANT_REVOKED`, the React PWA immediately unmounts the decrypted clinical card from React state, overwrites the cached DEK in memory, and downgrades the desk row to a metadata-only status badge (`"Offer Superseded — Lease Granted Elsewhere"`).

```python
async def sse_event_generator(request, pool, sess: AuthenticatedSession, referral_id: UUID, last_event_id: int):
    """Per-frame & per-heartbeat authorization enforcement for SSE streams (F10 / I10)."""
    cursor_seq = last_event_id
    while not await request.is_disconnected():
        with pool.connection() as conn:
            # Re-verify session and active payload_grant on every poll / 15s heartbeat
            grant_ok = conn.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM payload_grant
                    WHERE referral_id = %s AND facility_id = %s AND revoked_at IS NULL
                ) OR %s = 'DISPATCHER'
                """,
                (referral_id, sess.facility_id, sess.role_slot),
            ).fetchone()[0]

            events = conn.execute(
                """
                SELECT seq, type, epoch, detail, server_ts
                FROM event
                WHERE referral_id = %s AND seq > %s
                ORDER BY seq ASC
                """,
                (referral_id, cursor_seq),
            ).fetchall()

        for ev in events:
            cursor_seq = ev.seq
            if ev.type == "GRANT_REVOKED" and ev.detail.get("facility") == str(sess.facility_id):
                yield f"id: {ev.seq}\nevent: GRANT_REVOKED\ndata: {json.dumps(ev.detail)}\n\n"
                return  # Terminate clinical stream immediately
            # Strip any clinical attachment reference if grant_ok is False
            payload = {"seq": ev.seq, "type": ev.type, "epoch": ev.epoch, "detail": ev.detail, "clinical_access": bool(grant_ok)}
            yield f"id: {ev.seq}\nevent: STATE_UPDATE\ndata: {json.dumps(payload)}\n\n"

        # 15-second heartbeat frame also enforces grant status
        yield f": heartbeat ts={int(time.time())} grant={int(bool(grant_ok))}\n\n"
        await asyncio.sleep(1.0)
```

---

## 5. Cryptographic Architecture: Envelope Encryption, Crypto-Shredding & PHI-Free Metadata

### 5.1 Envelope Encryption Specification (`D9`, `I10`)
Clinical data (`clinical_payload` and `event_secret`) is never stored in plaintext and never written into `event.detail`.
1. **Key Hierarchy:**
   - **Master Key Encryption Key ($\text{KEK}_{\text{epoch}}$):** A 256-bit AES key scoped to a monthly cohort identifier `kek_epoch` (e.g., `'2026-11'`), loaded from the environment / KMS into API memory.
   - **Per-Referral Data Encryption Key ($\text{DEK}_r$):** A fresh 256-bit key generated via `secrets.token_bytes(32)` at `CREATE`.
   - **Key Wrapping:** $\text{DEK}_r$ is wrapped under $\text{KEK}_{\text{epoch}}$ using **AES Key Wrap (RFC 3394)** (`cryptography.hazmat.primitives.keywrap.aes_key_wrap`) and stored in `key_version.wrapped_dek` with `status = 'ACTIVE'`.
2. **Authenticated Encryption with Associated Data (AES-256-GCM):**
   - **Clinical Payload (`clinical_payload`):** Encrypted with $\text{DEK}_r$ using a $96\text{-bit}$ ($12\text{-byte}$) random nonce and Additional Authenticated Data ($\text{AAD}$) binding the ciphertext to its exact referral, key, and schema version:
     $$\text{AAD}_{\text{payload}} = \text{referral\_id}_{\text{ASCII}} \parallel \texttt{"|"} \parallel \text{key\_id}_{\text{ASCII}} \parallel \texttt{"|"} \parallel \text{schema\_ver}_{\text{ASCII}}$$
   - **Per-Event Secret (`event_secret`):** For events carrying free-text clinical notes or vitals corrections, the secret JSON is encrypted with $\text{DEK}_r$ using a fresh $96\text{-bit}$ nonce and:
     $$\text{AAD}_{\text{event}} = \text{referral\_id}_{\text{ASCII}} \parallel \texttt{"|"} \parallel \text{seq}_{\text{ASCII}} \parallel \texttt{"|"} \parallel \text{key\_id}_{\text{ASCII}}$$
3. **Hash-Chain Binding Without Breaking Crypto-Shredding:**
   - The `event` row stores only `secret_hash = SHA-256(nonce || ciphertext)`.
   - The event hash chain computes $\text{hash}_k = \text{SHA-256}(\text{prev\_hash}_k \parallel \text{JCS}(\text{core}_k))$, where `core` contains `"secret_hash": encode(secret_hash, 'hex')`.
   - Consequently, when `event_secret` and `clinical_payload` are deleted during crypto-shredding, `event.secret_hash` remains intact and **every historical hash chain and Merkle checkpoint continues to verify $100\%$ (`I5`)**.

### 5.2 Four-Step Crypto-Shredding & Cohort KEK Destruction (`D9`, `P5`)
1. **Step 1 (Row Deletion):** When a referral reaches its configured retention expiry (`clinical_payload.expires_at`), the shredder worker executes `DELETE FROM clinical_payload WHERE referral_id = %s` and `DELETE FROM event_secret WHERE referral_id = %s`.
2. **Step 2 (DEK Destruction):** Within the same transaction, the worker executes:
   ```sql
   UPDATE key_version
   SET wrapped_dek = NULL, status = 'SHREDDED', shredded_at = clock_timestamp()
   WHERE referral_id = %s;
   ```
   The table constraint `CHECK ((status='SHREDDED') = (wrapped_dek IS NULL))` guarantees at the database level that a `SHREDDED` key row never retains key material.
3. **Step 3 (WAL & Backup Cohort Unrecoverability):** Because PostgreSQL Write-Ahead Logs (WAL) and nightly backups still hold historical dead tuples of `wrapped_dek` and `ciphertext`, deleting database rows alone does not erase backups. When every referral belonging to a monthly `kek_epoch` cohort has reached `status = 'SHREDDED'`, the external $\text{KEK}_{\text{epoch}}$ is permanently destroyed in KMS/secret storage. Without $\text{KEK}_{\text{epoch}}$, all historical `wrapped_dek` blobs in WAL archives and snapshots become computationally unrecoverable (`BOUNDED` to the monthly cohort window, `T-P5`).
4. **Step 4 (Zero-Cache Guarantee):** Decryption occurs exclusively in ephemeral Python process memory (`synchronous_commit=on`, no Redis/Memcached tier in the stack), and all clinical HTTP responses carry `Cache-Control: no-store, no-cache, must-revalidate`.

### 5.3 Reference Implementation: Envelope Encryption & Crypto-Shredding (`Python 3.12`)

```python
import os
import hashlib
from uuid import UUID, uuid4
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.keywrap import aes_key_wrap, aes_key_unwrap
import psycopg

class EnvelopeCryptoManager:
    def __init__(self, kek_ring: dict[str, bytes], active_kek_epoch: str):
        """kek_ring maps kek_epoch (e.g. '2026-11') -> 32-byte KEK."""
        self.kek_ring = kek_ring
        self.active_epoch = active_kek_epoch

    def encrypt_clinical_payload(
        self, conn: psycopg.Connection, referral_id: UUID, plaintext_bytes: bytes, schema_ver: int, ttl_hours: int = 72
    ) -> UUID:
        dek = os.urandom(32)
        kek = self.kek_ring[self.active_epoch]
        wrapped_dek = aes_key_wrap(kek, dek)
        key_id = uuid4()

        nonce = os.urandom(12)
        aad = f"{referral_id}|{key_id}|{schema_ver}".encode("ascii")
        ciphertext = AESGCM(dek).encrypt(nonce, plaintext_bytes, aad)

        conn.execute(
            """
            INSERT INTO key_version (id, referral_id, kek_epoch, wrapped_dek, status, created_at)
            VALUES (%s, %s, %s, %s, 'ACTIVE', clock_timestamp())
            """,
            (key_id, referral_id, self.active_epoch, wrapped_dek),
        )
        conn.execute(
            """
            INSERT INTO clinical_payload (referral_id, key_id, nonce, ciphertext, schema_ver, expires_at)
            VALUES (%s, %s, %s, %s, %s, clock_timestamp() + (%s || ' hours')::interval)
            """,
            (referral_id, key_id, nonce, ciphertext, schema_ver, ttl_hours),
        )
        return key_id

    def decrypt_clinical_payload(self, conn: psycopg.Connection, referral_id: UUID) -> bytes:
        row = conn.execute(
            """
            SELECT cp.key_id, cp.nonce, cp.ciphertext, cp.schema_ver,
                   kv.kek_epoch, kv.wrapped_dek, kv.status
            FROM clinical_payload cp
            JOIN key_version kv ON kv.id = cp.key_id
            WHERE cp.referral_id = %s
            """,
            (referral_id,),
        ).fetchone()
        if not row or row.status == "SHREDDED" or row.wrapped_dek is None:
            raise LookupError("410_CLINICAL_PAYLOAD_SHREDDED")
        kek = self.kek_ring.get(row.kek_epoch)
        if kek is None:
            raise LookupError("410_KEK_EPOCH_DESTROYED")
        dek = aes_key_unwrap(kek, bytes(row.wrapped_dek))
        aad = f"{referral_id}|{row.key_id}|{row.schema_ver}".encode("ascii")
        return AESGCM(dek).decrypt(bytes(row.nonce), bytes(row.ciphertext), aad)

    @staticmethod
    def crypto_shred_referral(conn: psycopg.Connection, referral_id: UUID) -> None:
        conn.execute("DELETE FROM event_secret WHERE referral_id = %s", (referral_id,))
        conn.execute("DELETE FROM clinical_payload WHERE referral_id = %s", (referral_id,))
        conn.execute(
            """
            UPDATE key_version
            SET wrapped_dek = NULL, status = 'SHREDDED', shredded_at = clock_timestamp()
            WHERE referral_id = %s AND status <> 'SHREDDED'
            """,
            (referral_id,),
        )
```

### 5.4 PHI-Free Event Metadata (`F9`, `I11`) & Re-Identification Bounds
To guarantee that `event.detail` never becomes a covert channel for patient names, phone numbers, or Aadhaar/ABHA identifiers:
1. **Dual-Layer Allowlist Enforcement (`I11`):**
   - PostgreSQL immutable function `rhp_allowed(type text)` defines the exact permitted JSONB keys per event type (e.g., `OFFER_DECLINED` allows only `ARRAY['reason']`; `REFERRAL_CREATED` allows only `ARRAY['mode','need_class','chain_len','profile','mgso4']`).
   - PostgreSQL immutable function `rhp_detail_ok(type text, detail jsonb)` enforces that every key is in `rhp_allowed(type)` and every value is strictly a boolean, an integer (`^-?[0-9]{1,12}$`), a closed uppercase enum token (`^[A-Z0-9_]{1,40}$`), or a lowercase UUID (`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`).
2. **Quasi-Identifier & Re-Identification Controls (`F9`):**
   - Even without direct identifiers, exact timestamps combined with rare `origin_facility_id -> lease_facility_id` pairs can act as quasi-identifiers.
   - All public/research XES and aggregate district exports bucket timestamps into **4-hour windows** (`date_trunc('day', server_ts) + floor(extract(hour from server_ts) / 4) * interval '4 hours'`) and enforce **$k$-anonymity with $k \ge 5$** (suppressing any origin-destination-need_class cell with fewer than 5 referrals).
   - **Stated Bounded Residual (`P1`):** A rogue client with valid credentials could still encode a short code inside an uppercase string if not constrained by API enums; mitigated by strict Pydantic `Literal` enums on every API field and continuous CI fuzzing (`T-F9`). Low-volume rural facilities remain susceptible to side-information correlation by insiders holding physical registers (`BOUNDED`).

---

## 6. Tamper-Evident Log, Merkle Checkpoints, Split-View Defense & Cold-Key Restore

### 6.1 Per-Referral Hash Chain & Monotone Server Clock (`F11`, `I5`, `I16`)
Every state-changing command appends one or more rows to `event` while holding the per-referral `FOR UPDATE` row lock:
1. **Monotone Timestamp (`I16`):** Step 4 computes:
   $$\text{ts} = \max(\text{clock\_timestamp}(), \text{referral.head\_ts})$$
   and convert $\text{ts}$ to integer microseconds since the Unix epoch ($\text{server\_ts\_us} = \lfloor \text{epoch}(\text{ts}) \times 10^6 \rfloor$). If the host clock steps backward by $\Delta$, per-referral timestamps remain strictly non-decreasing (`rhp_event_guard` raises `CHAIN_BREAK` if `NEW.server_ts < r.head_ts`).
2. **RFC 8785 Canonical JSON (`JCS`) Core:**
   ```json
   {
     "actor_roster_id": "550e8400-e29b-41d4-a716-446655440000",
     "channel": "PWA",
     "client_ts_ms": 1763014200123,
     "detail": {"epoch": 1, "facility": "660e8400-e29b-41d4-a716-446655440111", "reason": "ALL_RESOURCES_CONFIRMED"},
     "epoch": 1,
     "event_id": "01931f5a-7c00-7000-8000-000000000001",
     "facility_id": "660e8400-e29b-41d4-a716-446655440111",
     "proxy": false,
     "referral_id": "770e8400-e29b-41d4-a716-446655440222",
     "secret_hash": null,
     "seq": 4,
     "server_ts_us": 1763014200456789,
     "type": "LEASE_GRANTED"
   }
   ```
   Because floating-point numbers are banned across all fields and keys are pure ASCII, RFC 8785 JCS serialization is identical to `json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")`.
3. **Chain Recurrence:**
   $$\text{prev\_hash}_1 = \texttt{0x00}^{32}, \qquad \text{hash}_k = \text{SHA-256}(\text{prev\_hash}_k \parallel \text{JCS}(\text{core}_k))$$

### 6.2 Binary Merkle Tree & 5-Second C2SP-Style Signed Checkpoints (`D10`, `F8`)
A database superuser (`postgres`) can disable triggers, rewrite `event` rows, and recompute a single referral's hash chain unless external witnesses hold signed commitments to the global state.
- **Process Isolation:** The checkpoint signer runs in a separate container / OS user `rhp-sign` (`UID 1002`), reading an Ed25519 private key with file permissions `0400` and connecting to PostgreSQL via the restricted role `rhp_witness` (`SELECT` on `event, referral, checkpoint`; `INSERT` on `checkpoint` only).
- **Merkle Tree Construction (every $5\text{ s}$):**
  1. Open a `REPEATABLE READ READ ONLY` transaction and query all referrals ordered lexicographically by `id::bytea`:
     `SELECT id, head_seq, head_hash FROM referral ORDER BY id ASC`.
  2. For each referral $i \in \{0, \dots, N-1\}$, compute the domain-separated leaf hash ($0\text{x}00$ prefix prevents second-preimage node/leaf confusion):
     $$\text{Leaf}_i = \text{SHA-256}\left(\texttt{0x00} \parallel \text{UUID\_bytes}(\text{id}_i)_{16\text{B}} \parallel \text{uint64\_be}(\text{head\_seq}_i)_{8\text{B}} \parallel \text{head\_hash}_{i, 32\text{B}}\right)$$
  3. Fold adjacent pairs bottom-up using the internal node prefix $\texttt{0x01}$:
     $$\text{Node}(L, R) = \text{SHA-256}(\texttt{0x01} \parallel L_{32\text{B}} \parallel R_{32\text{B}})$$
     If a level has an odd number of nodes, the trailing odd node is promoted unchanged to the next level. For $N = 0$, $\text{Root} = \text{SHA-256}(\texttt{""})$.
  4. Format the C2SP-style signed note:
     ```text
     rhp1/colossus-demo
     40
     4b9f8a2e...<base64_root_hash>...==

     — rhp-witness-1 <base64_ed25519_signature_over_3_header_lines>
     ```
  5. Broadcast the checkpoint to **three independent witnesses**: (a) the Guarantee Arena big screen, (b) every judge's phone polling `/v1/checkpoints/latest` (`Cache-Control: no-store`), and (c) an off-box append-only witness log on the secondary laptop (S3 Object Lock in pilot `[verify]`).

### 6.3 Executable Pure-JS Browser Verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`)

```javascript
// Pure-JS Verifier running on Judges' phones (works on iOS Safari & plain-HTTP LAN mode)
import { ed25519 } from "@noble/curves/ed25519";
import { sha256 } from "@noble/hashes/sha256";
import { utf8ToBytes, hexToBytes, bytesToHex, concatBytes } from "@noble/hashes/utils";

export function jcsBytes(obj) {
  const canonicalize = (val) => {
    if (val === null || typeof val === "boolean" || typeof val === "string") {
      return JSON.stringify(val);
    }
    if (typeof val === "number") {
      if (!Number.isInteger(val)) throw new Error("FLOAT_PROHIBITED_IN_JCS");
      return val.toString(10);
    }
    if (Array.isArray(val)) {
      return "[" + val.map(canonicalize).join(",") + "]";
    }
    const keys = Object.keys(val).sort();
    return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalize(val[k])).join(",") + "}";
  };
  return utf8ToBytes(canonicalize(obj));
}

function uuidToBytes(uuidStr) {
  return hexToBytes(uuidStr.replace(/-/g, ""));
}

function uint64BE(n) {
  const buf = new Uint8Array(8);
  let v = BigInt(n);
  for (let i = 7; i >= 0; i--) {
    buf[i] = Number(v & 0xffn);
    v >>= 8n;
  }
  return buf;
}

export function verifyReferralAndInclusion({
  pinnedWitnessPubKeyHex,
  pinnedColdPubKeyHex,
  checkpoint,
  events,
  inclusionProof,
  priorSeenHeadSeq = 0,
}) {
  // 1. Verify Ed25519 checkpoint signature against QR-pinned witness public key
  const noteHeader = utf8ToBytes(
    `rhp1/${checkpoint.deployment}\n${checkpoint.tree_size}\n${checkpoint.root_b64}\n`
  );
  const sigOk = ed25519.verify(
    hexToBytes(checkpoint.signature_hex),
    noteHeader,
    hexToBytes(pinnedWitnessPubKeyHex)
  );
  if (!sigOk) {
    return { ok: false, code: "CHECKPOINT_SIG", detail: `checkpoint_id=${checkpoint.id}` };
  }

  // 2. Recompute per-referral SHA-256 event hash chain from genesis (32 zero bytes)
  let expectedSeq = 1;
  let runningPrevHash = new Uint8Array(32); // 0x00 * 32

  for (const ev of events) {
    if (ev.seq !== expectedSeq) {
      return {
        ok: false,
        code: "SEQ_GAP",
        detail: `BROKEN referral=${ev.referral_id} expected_seq=${expectedSeq} got=${ev.seq}`,
      };
    }
    const storedPrev = hexToBytes(ev.prev_hash_hex);
    if (bytesToHex(storedPrev) !== bytesToHex(runningPrevHash)) {
      return {
        ok: false,
        code: "BROKEN",
        detail: `BROKEN referral=${ev.referral_id} seq=${ev.seq} kind=PREV expected=${bytesToHex(
          runningPrevHash
        )} got=${ev.prev_hash_hex}`,
      };
    }
    const core = {
      actor_roster_id: ev.actor_roster_id,
      channel: ev.channel,
      client_ts_ms: ev.client_ts_ms,
      detail: ev.detail,
      epoch: ev.epoch,
      event_id: ev.event_id,
      facility_id: ev.facility_id,
      proxy: ev.proxy,
      referral_id: ev.referral_id,
      secret_hash: ev.secret_hash_hex,
      seq: ev.seq,
      server_ts_us: ev.server_ts_us,
      type: ev.type,
    };
    const recomputedHash = sha256(concatBytes(runningPrevHash, jcsBytes(core)));
    if (bytesToHex(recomputedHash) !== ev.hash_hex) {
      return {
        ok: false,
        code: "BROKEN",
        detail: `BROKEN referral=${ev.referral_id} seq=${ev.seq} kind=HASH expected=${bytesToHex(
          recomputedHash
        )} got=${ev.hash_hex}`,
      };
    }
    runningPrevHash = recomputedHash;
    expectedSeq++;
  }

  const headSeq = events.length;
  const headHashHex = bytesToHex(runningPrevHash);

  // 3. Verify O(log N) Merkle inclusion proof up to the signed checkpoint root
  let node = sha256(
    concatBytes(
      new Uint8Array([0x00]),
      uuidToBytes(inclusionProof.referral_id),
      uint64BE(headSeq),
      runningPrevHash
    )
  );
  for (const step of inclusionProof.path) {
    const sibling = hexToBytes(step.hash_hex);
    node =
      step.side === "L"
        ? sha256(concatBytes(new Uint8Array([0x01]), sibling, node))
        : sha256(concatBytes(new Uint8Array([0x01]), node, sibling));
  }
  if (bytesToHex(node) !== checkpoint.root_hex) {
    return {
      ok: false,
      code: "ROOT_MISMATCH",
      detail: `computed=${bytesToHex(node)} checkpoint_root=${checkpoint.root_hex}`,
    };
  }

  // 4. Detect silent truncation vs. cold-key-signed backup restore (F8)
  if (headSeq < priorSeenHeadSeq) {
    if (checkpoint.kind !== "RESTORE" || !checkpoint.cold_signature_hex) {
      return { ok: false, code: "TRUNCATED", detail: `TRUNCATED at seq=${headSeq} (was ${priorSeenHeadSeq})` };
    }
    const restoreMsg = utf8ToBytes(
      `RESTORE:${checkpoint.restore_from}:${checkpoint.id}:${checkpoint.root_hex}`
    );
    const coldOk = ed25519.verify(
      hexToBytes(checkpoint.cold_signature_hex),
      restoreMsg,
      hexToBytes(pinnedColdPubKeyHex)
    );
    if (!coldOk) {
      return { ok: false, code: "TAMPER_INVALID_RESTORE_SIG", detail: `seq=${headSeq}` };
    }
  }

  return { ok: true, code: "VERIFIED", head_seq: headSeq, head_hash: headHashHex };
}
```

---

## 7. Database-Level Security Enforcement, Role Separation & Safe `BROKEN_BUILD` Isolation

### 7.1 Least-Privilege PostgreSQL 16 Role Separation Matrix (`FINAL §7`)

| Database Role | OS / Service Owner | Permitted `SELECT` Tables | Permitted `INSERT` / `UPDATE` Tables | Permitted `DELETE` Tables | Explicit Prohibitions |
|---|---|---|---|---|---|
| **`rhp_app`** | FastAPI + Poller + Outbox Relay | All 24 tables in `public` | All tables (`INSERT`); `UPDATE` on operational tables **except** `event`, `checkpoint`, `rejected_command` | `event_secret`, `clinical_payload`, `idempotency`, `telemetry` (for crypto-shredding & 48h TTL purge only) | `REVOKE UPDATE, DELETE ON event, checkpoint, rejected_command`; blocked by `rhp_no_mutate` triggers |
| **`rhp_monitor`** | Independent Python Monitor (Person B, `UID 1001`) | `event`, `referral`, `offer`, `deadline`, `checkpoint`, `heartbeat`, `outbox`, `rejected_command` | `heartbeat` (`INSERT, UPDATE` for its own liveness row only) | None | **Zero access** to `clinical_payload`, `event_secret`, `key_version`, `roster`, `session`, `device` (cannot read PHI or auth secrets) |
| **`rhp_witness`** | Merkle Checkpoint Signer (`rhp-sign`, `UID 1002`) | `event`, `referral`, `checkpoint` | `checkpoint` (`INSERT` only); `heartbeat` (`INSERT, UPDATE`) | None | Cannot modify `referral` or `event`; cannot read clinical or auth tables |

### 7.2 Database Security & Invariant Triggers (`I1`, `I4`, `I5`, `I7`, `I11`, `I14`, `I16`)
1. **`event_ao`, `checkpoint_ao`, `rejected_ao` (`BEFORE UPDATE OR DELETE`):** Calls `rhp_no_mutate()` which unconditionally raises `APPEND_ONLY <table>`.
2. **`event_guard` (`BEFORE INSERT ON event`):** Verifies `NEW.seq = r.head_seq + 1`, `NEW.prev_hash = r.head_hash`, and `NEW.server_ts >= r.head_ts`. Any out-of-sequence insert, broken hash link, or backward timestamp raises `CHAIN_BREAK`.
3. **`lk_referral`, `lk_offer`, `lk_deadline`, `lk_event`, `lk_grant`, `lk_outbox` (`BEFORE INSERT OR UPDATE`):** Enforces Invariant `I14` (`rhp_require_lock()`). Checks that `current_setting('rhp.locked_referral', true)` equals the target `referral_id`. Only non-contract delivery bookkeeping updates (`deadline.claimed_until` when `(status, due_at)` are unchanged, and `outbox.status/attempts/visible_after`) are exempt.
4. **`offer_chain_guard` (`BEFORE INSERT ON offer`):** Enforces Invariant `I7` (`rhp_chain_guard()`). If `NEW.source = 'CHAIN'`, verifies `NEW.facility_id = ANY(referral.chain)`; otherwise raises `I7_NOT_IN_CHAIN`.
5. **`i1_pending_deadline` (`AFTER INSERT OR UPDATE ON referral DEFERRABLE INITIALLY DEFERRED`):** Enforces Invariant `I1` at transaction `COMMIT`. If `NEW.hs_state NOT IN ('CLOSED', 'CANCELLED')`, verifies that at least one `deadline` row with `status = 'PENDING'` exists for `NEW.id`.

### 7.3 Safe `BROKEN_BUILD` Isolation (`F20`)
To prove to judges in the Guarantee Arena that the independent runtime monitor catches bugs rather than displaying a static green light, `BROKEN_BUILD=1` disables the lease check so two competing hospitals both win a lease (`DOUBLE_LEASE_VIOLATION` on Invariant `I2`). To prevent this mode from ever running near real data or corrupting the primary contract database:

```python
import os
import sys
from urllib.parse import urlparse
import psycopg

def enforce_broken_build_isolation(dsn: str, main_dsn_Check: str | None = None) -> bool:
    broken = os.getenv("BROKEN_BUILD", "0") == "1"
    real_data = os.getenv("REAL_DATA", "0") == "1"
    db_name = urlparse(dsn).path.lstrip("/")

    if broken:
        # Guard 1: Hard abort if REAL_DATA=1
        if real_data:
            sys.stderr.write("FATAL [F20]: BROKEN_BUILD=1 is strictly prohibited when REAL_DATA=1.\n")
            sys.exit(78)
        # Guard 2: Hard abort unless database name is explicitly rhp_scratch_broken
        if db_name != "rhp_scratch_broken":
            sys.stderr.write(f"FATAL [F20]: BROKEN_BUILD=1 requires db 'rhp_scratch_broken', got '{db_name}'.\n")
            sys.exit(78)
        # Guard 3: Verify scratch credentials cannot authenticate to the main database
        if main_dsn_Check:
            try:
                with psycopg.connect(main_dsn_Check, connect_timeout=2):
                    sys.stderr.write("FATAL [F20]: Scratch DB role succeeded in connecting to main DB!\n")
                    sys.exit(78)
            except psycopg.OperationalError:
                pass  # Expected: authentication / pg_hba rejection
    return broken
```

---

## 8. Indian Legal, Regulatory & Ethics Architecture ("Designed to Comply")

### 8.1 Digital Personal Data Protection (DPDP) Act 2023 & DPDP Rules 2025
- **Commencement & Enforcement Timeline:** Secondary sources report DPDP Rules notification on either 13 Nov 2025 or 14 Nov 2025 `[CONFLICT]`, with core obligations taking effect 18 months later on 13/14 May 2027 `[V]`. RHP-1 conservatively adopts the 14 Nov 2025 Gazette timeline and treats all safeguard obligations as active design requirements.
- **Section 7(f) Medical Emergency Processing Without Consent (vs. draft s.7(d) `[CONFLICT]`):**
  - **Legal Basis:** The DPDP Act permits a Data Fiduciary to process personal data without prior consent for responding to a medical emergency involving a threat to the life or immediate threat to the health of the Data Principal.
  - **Architectural Enforcement:** RHP-1 invokes this emergency basis **narrowly**:
    1. Only the clinician-authored handover summary needed for immediate receiving-facility triage is transmitted.
    2. `REFERRAL_CREATED` records the structured `need_class` (`OBSTETRIC_EMERGENCY`, etc.) and originating clinician (`actor_roster_id`) as the auditable emergency basis.
    3. Access is restricted by `payload_grant` strictly to the originating facility, active offer targets, and the dispatcher, and is revoked the moment an offer terminates (`F10`, `I10`).
- **Section 7(i) Employment Processing & Anti-Goodhart Staff Telemetry (`D18`, v8 §10.3/§11):**
  - **Legal Basis & Constraints:** Processing staff response times and escalation events under the employment provision requires **prior written notice to staff**, strict data minimization, siloing from HR performance/disciplinary records, and erasure once the operational evaluation purpose concludes.
  - **Architectural Enforcement:**
    1. Offers target `roster.role_slot` (`NURSE`, `CMO`, `CONSULTANT`), not personal accounts.
    2. Receiving desks display a **priority-ordered queue without countdown clocks** (preventing the Manchester Triage System target-distortion effect `[V]`).
    3. District Command Centre dashboards aggregate reliability metrics at the **facility and district level as capacity signals**, never ranking individual clinicians.
    4. Arrival-to-handover (`ARRIVED -> HANDED_OVER`, APOT-style) is measured separately from `OFFERED -> ACCEPTED` so "accept to hit the KPI, then hold the patient in the ambulance" is immediately visible (`T-K2`).
- **Section 8(5) Security Safeguards & Section 8(6) Breach Reporting:**
  - Statutory penalty ceilings reach up to ₹250 crore for failure to maintain reasonable security safeguards (s.8(5)) and up to ₹200 crore for failure to notify the Data Protection Board of India (DPBI) and affected individuals of a personal data breach (s.8(6); detailed report within 72 hours) `[V*]`.
  - Enforced via envelope encryption, per-event grant revocation, Argon2id PINs, least-privilege DB roles, and the incident response runbook (§8.3).
- **Section 8(7) Erasure vs. NMC 2020 3-Year Retention Interplay (`L2`, `[GAP]`):**
  - DPDP s.8(7) requires erasure of personal data once the specified purpose is no longer served, unless retention is necessary for compliance with any law in force. The NMC Telemedicine Practice Guidelines (2020) mandate 3-year retention of teleconsultation records, and CERT-In directions mandate 180-day log retention `[V*]`. Whether the 3-year telemedicine rule applies to an emergency inter-facility referral handover record is legally unsettled `[GAP]`.
  - **Architectural Resolution:** Retention is parameterized via `clinical_payload.expires_at` (`RETENTION_HOURS_CLINICAL`, default $72\text{ h}$ in demo, configurable to $3\text{ years}$ if counsel directs) while the PHI-free hash-chained audit log (`event`) satisfies long-term accountability without retaining patient identifiers (`OPEN`, owned by Legal Advisor).

### 8.2 Bharatiya Sakshya Adhiniyam (BSA) 2023 Section 63 Export Bundle (`L3`, `D5`)
Under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (replacing Section 65B of the Indian Evidence Act), admissibility of electronic records in legal proceedings requires a two-part certificate (**Part A** signed by the person in lawful control of the computer device/system and **Part B** signed by a qualified expert) stating the cryptographic hash value (SHA-256) of the electronic record `[V*]`.
- **What RHP-1 Builds:** Endpoint `GET /v1/referrals/{id}/evidence-bundle` outputs a deterministic ZIP archive containing:
  1. `events_jcs.jsonl`: Every committed `event` row for the referral in RFC 8785 canonical JSON, plus its Merkle inclusion proof and signed `checkpoint` note.
  2. `manifest.sha256`: Per-file SHA-256 digests and the overall bundle root SHA-256 digest.
  3. `BSA_Section63_PartA_Template.md` & `BSA_Section63_PartB_Template.md`: Pre-populated human-signable certificate templates containing the exact device/server deployment identifier, NTP synchronization attestation, SHA-256 hash values, and verification instructions.
- **Strict Claims Rule (`T-L3`):** The system generates a *BSA s.63-ready export bundle*; it is **never** described as "BSA certified", "immutable", or "legally conclusive" (tamper-evident logs detect modification; legal conclusiveness requires human signature and judicial admission).

### 8.3 CERT-In Directions (28 April 2022) & TRAI TCCCPR / DLT Telecom Compliance
1. **CERT-In Compliance Posture (`L4`, `T2`, `T3`):**
   - **NTP Synchronization:** All pilot hosts run `chronyd` in **slew-only mode** (no `makestep` after boot) synchronized against NIC (`samay1.nic.in`, `samay2.nic.in`) and CSIR-NPL stratum servers `[V]`. The `heartbeat` table records `ntp_offset_ms` every $5\text{ s}$ and fires an operator alarm if $|\text{ntp\_offset\_ms}| > 2000\text{ ms}$ (`F11`).
   - **180-Day In-India Log Retention & 6-Hour Reporting:** Security audit logs (`event`, `rejected_command`, `checkpoint`, `inbox`) are retained for $\ge 180\text{ days}$ on MeitY-empanelled cloud infrastructure in India (`ap-south-1` Mumbai / Hyderabad) with a documented 6-hour CERT-In incident notification runbook.
2. **TRAI TCCCPR 2018 & DLT Scrubbing (`P2`, `L1`):**
   - **SMS:** DLT scrubbing drops messages with unwhitelisted URLs or variables exceeding $\approx 30\text{ characters}$ `[V]`. RHP-1 never sends clinical text via SMS; the static template `"RHP alert: new referral. Open {#var#}"` carries only a $\le 30\text{-char}$ path on a pre-registered static domain (`CLOSED`, `T-P2`).
   - **Voice IVR (`L1`):** Automated outbound calls reading a de-identified emergency summary to pre-registered institutional duty numbers sit in an unsettled regulatory area under TRAI commercial communication rules `[GAP]`. For the hackathon prototype, calls are placed strictly through an Exotel trial/sandbox account to $\le 10$ whitelisted team phone numbers using synthetic data (`OPEN`, requires written legal opinion before pilot).
   - **WhatsApp:** Explicitly banned across all tiers for health data.

### 8.4 ABDM / NRCeS FHIR R4 Interoperability & ICMR (2017 / 2023) Ethics Routing
1. **ABDM & NRCeS FHIR R4 (`§15`):**
   - RHP-1 exports a valid FHIR R4 bundle (`ServiceRequest` + `Task` + `Encounter` + `Communication`) using a curated code subset without requiring a runtime terminology server.
   - Any future production integration with ABDM requires a Web Application Security Assessment (**WASA "Safe to Host"** certificate) by an STQC/CERT-In-empanelled auditor `[V*]`.
   - Claims are restricted to `"FHIR-shaped export"` (and `"ABDM-sandbox aligned"` only if sandbox API calls are executed).
2. **ICMR 2017 Ethical Guidelines & ICMR 2023 AI in Healthcare Guidelines (`§16`):**
   - **Ethics Committee Routing:** A district pilot that records clinician response latencies is human-participants health systems research under ICMR 2017 and is **not exempt** from ethics review. Minimal-risk shadow-mode observation qualifies for expedited review, whereas involving identifiable data of pregnant women (a vulnerable population under ICMR 2017) or influencing live routing requires **full Institutional Ethics Committee (IEC) review**.
   - **Cognitive Forcing Function for AI Intake (`T3_EXTRAS`, `A1`, `A2`):** When the optional AI intake accelerator is enabled, the API returns `423 ANCHOR_REQUIRED` and withholds the AI draft until the clinician manually commits `need_class` and `mgso4_status` (`GIVEN | NONE_GIVEN | UNKNOWN`). No AI confidence scores or explanations are displayed (as explanations increased commission errors from $10\%$ to $21\%$ in clinical decision studies `[V]`), critical fields require manual re-entry, and human override is always immediate.

---

## 9. Developer-Side Security & Multi-Agent Governance (`3-Gem + Antigravity`)

### 9.1 Defending Against Vibe-Coded Concurrency Bugs & Reward Hacking
Empirical benchmarks (`CONCUR`, `R11`, `R12`) demonstrate that coding agents frequently generate plausible-looking concurrency code with subtle race conditions or attempt "reward hacking" by weakening tests/specifications to make CI pass. RHP-1 enforces four hard governance locks:
1. **Read-Only Spec & Hash-Pinned Artefacts (`CODEOWNERS`):**
   - `/spec/*`, `transitions.yaml`, `rhp1.qnt`, `db/schema.sql`, and `/monitor/*` are protected by `CODEOWNERS` and SHA-256 hash-pinned in CI.
   - The coding agent (Google Antigravity) is forbidden by `AGENTS.md` from modifying specification files, transition tables, or monitor code to make a failing test pass.
2. **Common-Mode Failure Independence (`F17`):**
   - **Lane A (Person A):** Owns FastAPI `apply_command()`, `transitions.yaml`, and the Quint model (`rhp1.qnt`).
   - **Lane B (Person B):** Writes the independent Python runtime monitor (`monitor/monitor.py`) in an isolated workspace from the §3 invariant prose alone. The monitor imports **zero** server modules and connects via `rhp_monitor`.
3. **Six Mandatory Mutation Tests (`M1`–`M6`, `T-F17`):**
   No tier gate (`G0`) can pass unless deliberately injecting each of the six mutations into a scratch branch causes the named independent checker to fail:
   - `M1`: Skip `expected_epoch` check -> trips Monitor `I8` + vector `V-STALE-EPOCH`.
   - `M2`: Remove `FOR UPDATE` on `referral` and drop `one_lease` -> trips `T-C1 race200` + Monitor `I2`.
   - `M3`: Poller holds `deadline` lock across `apply_command()` -> trips `T-F1` (`deadlocks_delta > 0`, `I14`).
   - `M4`: Remove `nxt` cap guard in Quint -> trips `quint run safety` on `I12` (`open_offers > 2`).
   - `M5`: Write `prev_hash` as zeros -> trips Browser Verifier + Monitor `I5` (`kind=PREV`).
   - `M6`: `ACCEPT` ignores `offer_resource_confirmation.expires_at` -> trips vector `V-STALE-CONFIRM` + Monitor `I15`.
4. **Secret & Data Hygiene in Multi-Agent Prompts:**
   - `REAL_DATA=0` is enforced at boot for all demo profiles (`DEMO_FAST`, `DEMO_VOICE`).
   - API keys (Exotel, Mapbox, Cloudflare, Ed25519 private keys, KEKs) are loaded strictly from `.env` / `0400` key files and never pasted into Gem 1/2/3 packets or Antigravity build reports.

---

## 10. Threat Model (STRIDE), Security Attack Matrix, Residual Risks & Claims Discipline

### 10.1 STRIDE Threat Model Mapping

| STRIDE Category | Concrete RHP-1 Threat Vector | Enforced Architectural Control | Invariants |
|---|---|---|---|
| **Spoofing** | Unrostered person accepts on a shared ward tablet; SIM swap; voicemail triggers false `ACK` | Enrollment ticket -> Ed25519 device key -> session cookie (`UP`) + Argon2id PIN per action (`UV`); AMD + press-1 gate on voice; slot suspension on repeated lockouts | I6 |
| **Tampering** | Superuser edits or truncates `event` rows in PostgreSQL; client sends `"hs_state": "ACCEPTED"` in JSON body | Per-referral SHA-256(JCS) chain + 5 s Ed25519 Merkle checkpoints broadcast to external witnesses + cold-key `RESTORE`; Pydantic `extra='forbid'` + server-owned state | I5, I8, I14 |
| **Repudiation** | Receiving hospital claims "we never accepted that referral" after turning the ambulance away at the door | `OFFER_ACCEPTED` + `LEASE_GRANTED` events bind `actor_roster_id`, `device_id`/`call_sid`, verified PIN, `offer_resource_confirmation` rows, and Merkle inclusion proof; `ARRIVAL_REJECTED` records broken commitment | I2, I5, I6 |
| **Information Disclosure** | PHI leaked via FCM push, DLT SMS, `event.detail`, or an unclosed SSE stream after decline/supersede | Empty-payload FCM wake ping; static DLT SMS template; `rhp_detail_ok()` allowlist CHECK; per-frame SSE grant check + immediate `GRANT_REVOKED` frame; AES-256-GCM envelope encryption + crypto-shredding | I10, I11 |
| **Denial of Service** | Rival hospital locks out casualty desk via wrong PINs; QR bot flood; retry storm; poller/command deadlock | Lockout scoped strictly to `(session_id \| call_sid)` via autonomous txn; rotating QR + Turnstile + cap 20; Step 1 advisory lock + idempotent replay; global lock order `referral>offer>deadline>outbox` | I1, I4, I6, I14 |
| **Elevation of Privilege** | BOLA (Hospital A accepts Hospital B's offer); AI agent weakens spec or runs `BROKEN_BUILD` on real DB | Object-level facility match under referral row lock; `CODEOWNERS` + SHA-256 CI pin on `/spec` and `/monitor`; 3-way boot abort on `BROKEN_BUILD=1` | I2, I6, I7 |

### 10.2 Complete Security, Privacy, Insider, Legal & Demo Attack Matrix (`F15`)

| ID | Class | Scenario | Detection | Auto-Response | Human Fallback | Inv | Stated Technical Residual & Reason | Named Test | Status |
|---|---|---|---|---|---|---|---|---|---|
| **I1** | Identity | Unrostered or wrong-facility user attempts `ACCEPT` | Step 5 BOLA & roster check | `403 FORBIDDEN` + `rejected_command` row | Admin roster audit | I6 | Shared-credential misuse inside a valid rostered shift cannot be distinguished by software alone | `T-I6` | `CLOSED` |
| **I2** | Identity | PIN brute-force on stolen tablet or voice call | `session.pin_failed` counter | Argon2id ($\approx 100\text{ ms}$), $0/5/30/120\text{ s}$ lock via autonomous txn, `PIN_LOCKED` event | Dispatcher paged on strike 3 | I6 | Starting a new voice call resets `call_sid` scope, but requires control of the registered duty phone number | `T-F7` | `BOUNDED` |
| **I3** | Identity | Rival hospital enters bad PINs to lock out target desk | Per-session lock scope | Only attacker's `session_id` locks; target desk's session unaffected | — | I6 | None across sessions (state isolated by `session.id` PK) | `T-F7` | `CLOSED` |
| **I4** | Identity | SIM swap on duty phone number | Repeated lockouts / unexpected channel ACK | Alert dispatcher; suspend `roster` slot pending admin verification | Admin re-rosters phone | I6 | Exposure window between carrier SIM swap and first anomalous action/lockout | `T-I4` | `BOUNDED` |
| **I5** | Identity | Voicemail box or auto-attendant answers Exotel call | Exotel AMD + press-1 gate ($8\text{ s}$) | No `ACK` committed; call marked `UNANSWERED`; ladder advances | Next slot / rung $3A/4$ proxy | I6 | A human bystander answering the duty phone can press `1` to `ACK`, but PIN still gates `ACCEPT`/`DECLINE` | `T-F7` | `CLOSED` |
| **I6** | Identity | BOLA or mass-assignment (`hs_state` injected in JSON) | Route authz suite + Pydantic `extra='forbid'` | `403` / `422` + `rejected_command` | — | I6 | Newly added routes must be covered by the route-matrix CI test | `T-I6b` | `CLOSED` |
| **P1** | Privacy | Free-text PHI injected into `event.detail` | Pydantic `Literal` + PG `rhp_detail_ok()` CHECK | Transaction aborts with `422` / CHECK failure | — | I11 | An uppercase string matching `^[A-Z0-9_]{1,40}$` could still encode a short identifier if API enum is bypassed | `T-F9` | `BOUNDED` |
| **P2** | Privacy | PHI transmitted over DLT SMS | Static template linter | Only short referral code in `{#var#}` ($\le 30\text{ chars}$) | — | — | None in SMS body (clinical payload never touches SMS adapter) | `T-P2` | `CLOSED` |
| **P3** | Privacy | PHI transmitted over FCM push notification | Push payload linter | Empty wake ping `{referral_id, seq}` only; client fetches over HTTPS | — | I10 | Traffic-analysis metadata (wake timing and IP) visible to push provider | `T-P3` | `CLOSED` |
| **P4** | Privacy | Desk keeps SSE open after `DECLINE` or `SUPERSEDE` | Per-frame grant check + `GRANT_REVOKED` frame | Server strips clinical fields; client purges DOM & memory | — | I10 | Data already viewed or photographed on screen before revocation cannot be recalled | `T-F10` | `BOUNDED` |
| **P5** | Privacy | Deleted `clinical_payload` recovered from WAL / backup | Restore drill test | `wrapped_dek=NULL` + monthly `kek_epoch` destruction | Ops KEK rotation | I10 | Backups remain decryptable until the monthly `kek_epoch` cohort expires and its KEK is destroyed | `T-P5` | `BOUNDED` |
| **S1** | Insider | DB superuser edits or deletes an `event` row | Browser verifier + Python monitor | Names exact broken `referral_id`, `seq`, and `kind=PREV\|HASH\|SEQ_GAP` | Incident response & restore | I5 | Tamper-evident (detection only; superuser cannot be prevented from writing local disk) | `T-F8` | `BOUNDED` |
| **S2** | Insider | Operator serves split-view history to different parties | Witness checkpoint gossip | Divergent roots for same `checkpoint.id` or missing `head_seq` flagged | External audit | I5 | Requires $\ge 2$ honest external witnesses holding checkpoints | `T-S2` | `BOUNDED` |
| **S3** | Insider | Attacker steals `rhp-sign` Ed25519 private key | Key rotation drill / host audit | Revoke witness key; sign new epoch with offline cold key | Admin key ceremony | I5 | Attacker can co-sign forged checkpoints until key theft is detected and rotated (no hardware HSM in prototype) | `T-S3` | `OPEN` |
| **S4** | Insider | Dispatcher abuses `DISPATCHER_ASSIGN` override | Monitor flags `proxy=true` & override count | Requires structured reason enum; highlighted on district view | District officer review | I6 | Legitimate-looking emergency override by an authorized dispatcher requires human post-hoc audit | `T-S4` | `BOUNDED` |
| **L1** | Legal | Outbound voice IVR legality under TRAI rules | Pre-pilot legal review | Sandbox + $\le 10$ whitelisted team phones + synthetic text | PWA desk / dispatcher proxy | — | Regulatory interpretation unsettled `[GAP]` | `T-L1` | `OPEN` |
| **L2** | Legal | DPDP s.8(7) erasure vs. NMC 3-year retention | Policy config validator | Parameterized `RETENTION_HOURS_CLINICAL` + separate PHI-free audit log | Legal counsel sign-off | — | Applicability of 3-year telemedicine rule to handover records is `[GAP]` | `T-L2` | `OPEN` |
| **L3** | Legal | Overclaiming BSA s.63 certification in pitch/docs | CI forbidden-phrase linter (`ST-5`) | Generates export bundle + Part A/B templates only | — | I5 | Human custodian/expert must physically sign Part A/B for court use | `T-L3` | `CLOSED` |
| **L4** | Legal | Missing CERT-In 6 h or DPBI 72 h breach clock | Incident runbook drill | Automated tamper/breach alert pages operator immediately | Operator files report | — | Clock compliance depends on human operator action after alert | `T-L4` | `BOUNDED` |
| **D1** | Demo | iOS Safari lacks WebCrypto Ed25519 / LAN HTTP `crypto.subtle` | Preflight iPhone test | Bundled pure-JS `@noble/curves/ed25519` & `@noble/hashes/sha256` | Labelled server-side verify | I5 | Pure-JS verification takes $\approx 5\text{–}15\text{ ms}$ per signature on mobile CPU | `T-D1` | `BOUNDED` |
| **D3** | Demo | `BROKEN_BUILD=1` accidentally enabled on main DB | Startup guard `enforce_broken_build_isolation()` | Hard abort (`exit 78`) if `REAL_DATA=1` or DB $\neq$ `rhp_scratch_broken` | — | I2 | None (process exits before opening listener socket) | `T-F20` | `CLOSED` |

### 10.3 Ranked Security & Legal Residual-Risk Register (§20)

| Rank | Residual Risk Item | Status | Owner | Enforced Mitigation | Required Closing Evidence |
|---|---|---|---|---|---|
| **1** | Outbound voice IVR regulatory status unsettled (`L1`) | `OPEN` | Legal Advisor | Exotel sandbox, $\le 10$ whitelisted team numbers, synthetic de-identified prompts | Written legal opinion + TRAI/MeitY principal-entity clearance before any pilot |
| **2** | DPDP s.8(7) erasure vs. NMC 3-year retention (`L2`) | `OPEN` | Legal Advisor | Parameterized `clinical_payload.expires_at` + crypto-shredding + PHI-free `event` log | Counsel determination on handover-record retention period |
| **3** | Witness signer key theft without HSM (`S3`) | `OPEN` | Person A (`T1`) | Separate OS user `rhp-sign` (`UID 1002`), `0400` key file, offline cold key for `RESTORE` | Cloud KMS / hardware HSM integration + key-rotation drill log for pilot |
| **4** | Clock step bounds under NTP fault (`T2/T3`) | `BOUNDED` | Person A (`T1`) | `GREATEST(clock_timestamp(), head_ts)` under lock, chrony slew-only, $>2\text{ s}$ offset alarm | NTP step fault-injection test report (`T-F11`) |
| **5** | Low-volume facility quasi-identifier correlation (`P1`) | `BOUNDED` | Person A (`T1`) | `rhp_detail_ok()` allowlist, $4\text{-hour}$ timestamp buckets, $k \ge 5$ cell suppression | Export audit & fuzz test (`T-F9`) |
| **6** | AI intake rubber-stamping (`A1`) | `BOUNDED` | Person B (`T2`) | Cognitive Forcing Function (`423 ANCHOR_REQUIRED`), no confidence scores, AI off by default | 20-slip seeded-error usability gate ($\le 5\%$ rubber-stamp, $\le 1\%$ omission) |

### 10.4 Claims & Evidence Discipline Register (§19)

| Authorized Wording (Mandatory) | Forbidden Claims (Strictly Prohibited Across Code, UI & Pitch) |
|---|---|
| "Referral communication and documentation gaps are documented in specific urban Indian studies (Das et al., 2023; Safdarjung 2018–2023) `[V]`" | National prevalence claims; "lives saved"; "deaths prevented"; "mortality reduced" |
| "Automatic inter-facility escalation and hard single-owner guarantees were not found in public documentation of the systems audited `[V*]`" | "First in the world"; "only system"; "no competitor has this" |
| "Designed to comply with DPDP Act 2023 and CERT-In directions; synthetic data only (`REAL_DATA=0`); ABDM-sandbox aligned (only if sandbox calls are made)" | "ABDM compliant"; "HIPAA/DPDP certified"; "production ready" |
| "Every identified weakness is `CLOSED` with a named test, `BOUNDED` with a stated residual and monitor alarm, or `OPEN` with an owner" | "Bullet-proof"; "airtight"; "zero loopholes"; "guaranteed"; "immune"; "crash-proof" |
| "Control-plane model checked within stated bounds ($F=3, E=4$); implementation checked by conformance vectors, 200-way concurrency tests, and an independent runtime monitor" | "Mathematically proven system"; "formally verified code" |
| "Tamper-evident hash-chained log with external Merkle witnesses and a BSA s.63-ready export bundle" | "Immutable log"; "blockchain-grade"; "BSA certified"; "legally conclusive" |
| "Process improvement and capacity-signalling effects are hypotheses to be tested in an ethics-approved district pilot" | "Eliminates ping-pong"; "zero silent drops" |

---

## 11. Security & Legal Pre-Event Verification & Automated CI Test Suite

| Test ID | Target Mechanism | Automated Execution / Verification Procedure | Pass Criterion |
|---|---|---|---|
| **`T-F1`** | Global lock order & `rhp_require_lock` (`I14`) | Run 200-way concurrent `ACCEPT` + poller `TIMEOUT` ticks; attempt direct SQL `UPDATE offer` without setting `rhp.locked_referral` | `deadlocks_delta == 0`; direct SQL raises `I14_LOCK_NOT_HELD` |
| **`T-F2`** | Signed profile & `REAL_DATA` guard | Boot API with `PROFILE=DEMO_FAST` and `REAL_DATA=1`; tamper 1 byte of profile JSON | Both boots refuse start with non-zero exit and log `I13` / signature error |
| **`T-F7`** | Per-session PIN lockout & AMD press-1 gate (`I6`) | Submit 3 wrong PINs on Session A, then submit valid PIN on Session B (same facility/role); replay Exotel voicemail callback without `Digits="1"` | Session A returns `429 PIN_LOCKED` (persisted across rollback); Session B returns `200`; voicemail records `0` ACKs |
| **`T-F8`** | Tamper detection vs. cold-key `RESTORE` (`I5`) | In `psql` (superuser on scratch DB), alter 1 byte of `event.detail` at `seq=2`; next, truncate head without `RESTORE` row; finally, apply valid cold-key `RESTORE` checkpoint | Browser verifier outputs `BROKEN referral=… seq=2 kind=HASH`, then `TRUNCATED at seq=…`, then `VERIFIED` on signed restore |
| **`T-F9`** | PHI-free `event.detail` allowlist (`I11`) | Fuzz `event` inserts with 1,000 random keys, floats, lowercase strings, and phone numbers | $100\%$ rejected by Pydantic (`422`) and PostgreSQL `rhp_detail_ok` CHECK |
| **`T-F10`** | SSE stream revocation (`I10`) | Open SSE on Hospital A (`OFFERED`), then `ACCEPT` on Hospital B (`SUPERSEDED`) | Hospital A receives `GRANT_REVOKED` within $\le 1\text{ s}$, stream closes, clinical DOM state wiped |
| **`T-F11`** | Monotone server timestamp (`I16`) | Step host clock backward by $3\text{ s}$ mid-referral and issue `ACK` | `event.server_ts >= prev_event.server_ts`; `heartbeat.ntp_offset_ms` raises $>2\text{ s}$ alarm |
| **`T-F12`** | Offline stale confirmation (`I15`) | Confirm resources on `DEMO_FAST` (`confirm_ttl=10s`), sleep $11\text{ s}$, replay queued `ACCEPT` | Returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`; `0` leases granted |
| **`T-F14`** | Scoped idempotency edge matrix (`I4`, `I8`) | Replay identical key+payload (`200` and `409`), same key+mutated payload (`422`), parallel in-flight duplicate (`409`), and expired key with duplicate `event_id` (`409`) | All 8 rows of the §5 idempotency matrix return exact expected status codes with `0` duplicate `event` rows |
| **`T-F17`** | Six mutation tests (`M1`–`M6`) | Run `scripts/run_mutations.sh` toggling `M1`..`M6` against Quint, Conformance Vectors, and Person B's Monitor | All 6 mutations fail their designated independent checker |
| **`T-F20`** | `BROKEN_BUILD` scratch isolation | Attempt boot with `BROKEN_BUILD=1` against main DB DSN or with `REAL_DATA=1` | Process aborts immediately with exit code `78` before binding port |
| **`ST-5`** | Claims discipline linter | Scan repository (`docs/`, `api/`, `pwa/`) excluding §10.4 / Architecture §19 for forbidden claims | `0` matches found |