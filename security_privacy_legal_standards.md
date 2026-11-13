# ReferralHandshake (Protocol RHP-1) — Security, Privacy & Legal Standards

**Security Posture:** Defense-in-Depth, Zero PHI in Metadata/Push/SMS, Per-Referral Envelope Encryption, Independent Witness Checkpoints  
**Data Mode:** Synthetic Data Only (`REAL_DATA=0`) in Prototype & Hackathon Demo

---

## 1. Identity, Device Enrollment & Anti-DoS PIN Architecture [F7, D12]

### 1.1 Single-Use Ticket Enrollment & Session Binding
1. **Roster Slot Authority:** Authority belongs to a facility's **duty role slot** (`NURSE`, `CMO`, `CONSULTANT`, `CLINICIAN`, `EMT`, `DISPATCHER`, `ADMIN`), never an unverified personal account.
2. **Device Enrollment:** An `ADMIN` issues a single-use `enrollment_ticket` (random 256-bit token, stored only as `SHA-256(token)` in `enrollment_ticket.token_hash`, valid for $15\text{ minutes}$). The ward tablet or phone generates an Ed25519 keypair, redeems the ticket by submitting its 32-byte public key, and receives a registered `device` record and an opaque 256-bit session token (stored as `SHA-256(token)` in `session.token_hash`).
3. **Voice Session Binding:** Outbound Exotel IVR calls create an ephemeral `session` bound to `call_sid` (`device_id IS NULL, call_sid IS NOT NULL`) scoped to the dialed `roster_id`.

### 1.2 Server-Verified Argon2id PIN & Per-Session Lockout Isolation [F7]
On shared ward tablets and feature phones, "device present" does not equal "user verified" (`D12`). Every mutating clinical decision (`RESOURCE_CONFIRM`, `ACCEPT`, `COUNTER`, `CONFIRM_COUNTER`, `DECLINE`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`, `CANCEL`) requires explicit PIN verification:
- **Argon2id Hashing:** `roster.pin_hash` uses Argon2id (`time_cost=2, memory_cost=65536, parallelism=2`, tuned to $\approx 100\text{ ms}$).
- **Autonomous Failure Counter:** When PIN verification fails in Step 3 of `apply_command()`, the failure increment executes on a **separate autonomous database connection** that commits immediately before `apply_command()` returns `403 PIN_INVALID`. A transaction rollback never erases a failed PIN attempt.
- **Per-Session / Per-Call Lockout Scope (`F7`):** Progressive backoff is $0\text{ s}$ (fail 1), $5\text{ s}$ (fail 2), and $120\text{ s}$ lockout (`pin_locked_until = clock_timestamp() + interval '120 seconds'`) on fail 3, scoped strictly to `session.id` (or `call_sid`). **Why:** An attacker on a stolen session or competing call cannot lock out the facility's legitimate ward tablet session (`I3` in Security Matrix).
- **3rd-Strike Alert & Slot Suspension:** The 3rd consecutive failure appends a `PIN_LOCKED` event and pages the dispatcher. Repeated lockouts ($\ge 3$ locked sessions within $30\text{ minutes}$) suspend the `roster` slot pending admin review.

---

## 2. Edge Protection, Rotating QR Admission & LAN Fallback [D11]

1. **Rotating Single-Use Judge QR:** The big screen displays a QR code whose signed payload carries a unique `jti` and expires in $20\text{ s}$ (rotated every $15\text{ s}$).
2. **Cloudflare Turnstile Gate (`D11`):** Scanning the QR loads a challenge page requiring a valid Cloudflare Turnstile proof before the server mints a `JUDGE_DESK` session.
3. **Admission Cap & Rate Limits:** Simultaneous active `JUDGE_DESK` sessions are hard-capped at $20$. Per-IP minting is rate-limited with NAT allowance, and each minted session is rate-limited to $5\text{ req/s}$.
4. **Fail-Closed LAN Mode:** If venue internet fails, the local hotspot LAN mode engages with `JUDGE_DESK` cap $\le 20$, synthetic mode forced, **hard boot refusal if `REAL_DATA=1`**, and PIN entry disabled over plain HTTP (demo desks use pre-bound synthetic role buttons). Because iOS Safari disables `window.crypto.subtle` on insecure HTTP LAN origins `[V]`, the browser verifier uses bundled pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256`.

---

## 3. Envelope Encryption, Crypto-Shredding & PHI-Free Metadata [D9, F9]

### 3.1 Per-Referral Envelope Encryption & Crypto-Shredding Walkthrough
ReferralHandshake stores a temporary **handover record**, never a permanent longitudinal EHR:
1. **Key Hierarchy:** Each referral generates a fresh 256-bit AES-GCM Data Encryption Key (**DEK**). The DEK is wrapped using AES Key Wrap (`AES-KW`, RFC 3394) under a monthly Master Key Encryption Key (**KEK**, identified by `key_version.kek_epoch`) and stored in `key_version.wrapped_dek`.
2. **Authenticated Encryption (AAD):**
   - `clinical_payload.ciphertext`: AES-256-GCM with $96\text{-bit}$ random `nonce` and $\text{AAD} = \text{referral\_id} \parallel \text{key\_id} \parallel \text{schema\_ver}$.
   - `event_secret.ciphertext`: AES-256-GCM with $96\text{-bit}$ `nonce` and $\text{AAD} = \text{referral\_id} \parallel \text{seq} \parallel \text{key\_id}$.
   - `event.secret_hash`: Stores `SHA-256(nonce || ciphertext)` inside the immutable event hash chain so deleting `event_secret` never invalidates the SHA-256 event chain (`I5`).
3. **4-Step Crypto-Shredding Procedure (`D9`):**
   - **Step A:** When `clinical_payload.expires_at` passes (or on administrative purge after closure), `DELETE FROM clinical_payload WHERE referral_id = $1` and `DELETE FROM event_secret WHERE referral_id = $1`.
   - **Step B:** `UPDATE key_version SET wrapped_dek = NULL, status = 'SHREDDED', shredded_at = clock_timestamp() WHERE referral_id = $1`.
   - **Step C (WAL & Backup Shredding):** Because PostgreSQL WAL segments and physical backups retain historical ciphertext and wrapped DEKs, once every referral belonging to a `kek_epoch` has expired, the external `kek_epoch` master key is destroyed, rendering all historical WAL and backup copies cryptographically unrecoverable.
   - **Step D (Memory & Cache Hygiene):** Decryption occurs only in Python process memory; all clinical HTTP responses set `Cache-Control: no-store, no-cache, must-revalidate`; no Redis or shared cache layer exists.

### 3.2 PHI-Free Metadata & Re-Identification Bounds [F9, I11]
- **Database & API Allowlist:** `event.detail` is restricted by Pydantic `Literal` types and the PostgreSQL `rhp_detail_ok(type, detail)` constraint to allowlisted keys (`rhp_allowed(type)`), booleans, $\le 12$-digit integers, UUIDs, and uppercase enum tokens `^[A-Z0-9_]{1,40}$`. Free-text clinical strings are structurally impossible in `event.detail`.
- **Zero-Payload Push & Static SMS:** FCM push notifications carry an empty wake ping (`{}`); the Android app fetches clinical details over an authenticated TLS session (`P3`). SMS messages use a static DLT template containing only a short link code (`P2`).
- **Aggregate Export Anonymization:** Shared XES and analytics exports bucket timestamps into $4\text{-hour}$ intervals and suppress any `(origin, destination, need_class)` cell with fewer than $5$ referrals ($k \ge 5$).

---

## 4. Tamper-Evident Log, Binary Merkle Proofs & Independent Witnesses [F8, D10]

### 4.1 Per-Referral Hash Chain
For every event $e_k$ ($k \ge 1$) on a referral:

$$\text{hash}_k = \text{SHA-256}\left(\text{prev\_hash}_k \parallel \text{JCS}(\text{core}_k)\right)$$

where $\text{prev\_hash}_1 = \text{0x00}^{32}$ (32 zero bytes) and $\text{core}_k$ contains `{referral_id, seq, event_id, type, epoch, actor_roster_id, facility_id, channel, proxy, detail, secret_hash, client_ts_ms, server_ts_us}`.

### 4.2 Separate-OS-User Signer & Binary Merkle Checkpoints
Every $5\text{ seconds}$, the isolated witness process (running as OS user `rhp-sign`, UID `1002`, reading an Ed25519 private key with file permissions `0400`, connected to PostgreSQL as `rhp_witness` in `REPEATABLE READ READ ONLY` mode) snapshots all referrals ordered by `referral.id`:
- **Leaf Hash:** $L_i = \text{SHA-256}(\text{0x00} \parallel \text{referral\_id}_{16\text{B}} \parallel \text{head\_seq}_{8\text{B BE}} \parallel \text{head\_hash}_{32\text{B}})$.
- **Interior Node Hash:** $N = \text{SHA-256}(\text{0x01} \parallel \text{left}_{32\text{B}} \parallel \text{right}_{32\text{B}})$ (odd trailing node promoted unchanged).
- **C2SP Signed Note Format:**
  ```text
  rhp1/colossus-demo
  40
  <base64_root_hash>

  — rhp-sign <key_id_hex> <base64_ed25519_signature>
  ```
- **Independent Witnesses:** Checkpoints are pushed every $5\text{ s}$ to (1) the Guarantee Arena big screen, (2) judges' phones via `/checkpoints/latest`, and (3) an off-box append-only log on a second laptop (preventing split-view history rewriting by a single operator, `D10`).

### 4.3 Pure-JS Browser Verifier Algorithm
```javascript
import { ed25519 } from '@noble/curves/ed25519';
import { sha256 } from '@noble/hashes/sha256';
import { utf8ToBytes, hexToBytes, bytesToHex, concatBytes } from '@noble/hashes/utils';

export function jcsBytes(obj) {
  const keys = Object.keys(obj).sort();
  const parts = keys.map((k) => `${JSON.stringify(k)}:${
    obj[k] !== null && typeof obj[k] === 'object' && !Array.isArray(obj[k])
      ? new TextDecoder().decode(jcsBytes(obj[k]))
      : JSON.stringify(obj[k])
  }`);
  return utf8ToBytes(`{${parts.join(',')}}`);
}

export function verifyReferralChainAndProof(events, proof, checkpointNote, pinnedPubKeyHex, coldPubKeyHex) {
  // 1. Verify Ed25519 signature on checkpoint note
  const [body, sigLine] = checkpointNote.split('\n\n');
  const sigBytes = Uint8Array.from(atob(sigLine.split(' ')[3]), c => c.charCodeAt(0));
  if (!ed25519.verify(sigBytes, utf8ToBytes(body + '\n'), hexToBytes(pinnedPubKeyHex))) {
    return { ok: false, code: 'CHECKPOINT_SIG' };
  }
  // 2. Recompute per-referral SHA-256 hash chain from genesis
  let expectedSeq = 1;
  let prevHash = new Uint8Array(32); // 32 zero bytes
  for (const ev of events) {
    if (ev.seq !== expectedSeq) {
      return { ok: false, code: `SEQ_GAP referral=${ev.referral_id} expected=${expectedSeq} got=${ev.seq}` };
    }
    if (bytesToHex(prevHash) !== ev.prev_hash_hex) {
      return { ok: false, code: `BROKEN referral=${ev.referral_id} seq=${ev.seq} kind=PREV expected=${bytesToHex(prevHash)} got=${ev.prev_hash_hex}` };
    }
    const recomputed = bytesToHex(sha256(concatBytes(prevHash, jcsBytes(ev.core))));
    if (recomputed !== ev.hash_hex) {
      return { ok: false, code: `BROKEN referral=${ev.referral_id} seq=${ev.seq} kind=HASH expected=${recomputed} got=${ev.hash_hex}` };
    }
    prevHash = hexToBytes(ev.hash_hex);
    expectedSeq += 1;
  }
  // 3. Check for uncertified truncation below checkpointed head_seq
  const lastSeq = events.length ? events[events.length - 1].seq : 0;
  if (lastSeq < proof.head_seq && !proof.valid_cold_restore) {
    return { ok: false, code: `TRUNCATED at seq=${lastSeq} checkpoint_seq=${proof.head_seq}` };
  }
  // 4. Fold binary Merkle inclusion path to signed root
  let node = sha256(concatBytes(new Uint8Array([0x00]), hexToBytes(proof.referral_id_hex), proof.head_seq_be8, prevHash));
  for (const step of proof.path) {
    const sib = hexToBytes(step.hash_hex);
    node = step.side === 'R'
      ? sha256(concatBytes(new Uint8Array([0x01]), node, sib))
      : sha256(concatBytes(new Uint8Array([0x01]), sib, node));
  }
  if (bytesToHex(node) !== proof.root_hash_hex) {
    return { ok: false, code: 'ROOT_MISMATCH' };
  }
  return { ok: true, code: 'VERIFIED' };
}
```

---

## 5. STRIDE Threat Matrix & Indian Legal Posture

### 5.1 STRIDE Threat Matrix

| STRIDE Category | Specific Threat Vector | Enforced Architectural Control | Verification Test |
|---|---|---|---|
| **Spoofing** | Unauthorized person clicks Accept on shared ward tablet; SIM swap; voicemail auto-answer triggers ACK. | Roster slot check + device key binding + server-verified Argon2id PIN (`D12`); AMD + press-1 gate (`F7`); slot suspension on repeated lockouts. | `T-I6`, `T-F7` |
| **Tampering** | Sysadmin edits/deletes `event` row in `psql`; attacker injects `hs_state` in JSON body. | `event_ao` trigger + per-referral SHA-256 chain + 5 s Ed25519 Merkle checkpoints on witnesses (`F8`, `D10`); Pydantic `extra='forbid'` + server-owned state. | `T-F8`, `T-I6b` |
| **Repudiation** | Receiving hospital claims "we never accepted" or "we didn't know NICU was needed". | Device-signed/PIN-verified `OFFER_ACCEPTED` and `RESOURCE_CONFIRMED` events chained into signed Merkle checkpoints. | `T-I5`, `T-I15` |
| **Information Disclosure** | PHI leaked in FCM push, DLT SMS, `event.detail` logs, or SSE stream after decline/supersede. | Empty-payload FCM wake ping (`P3`), static DLT SMS (`P2`), `rhp_detail_ok` CHECK (`F9`), per-event `payload_grant` check + `GRANT_REVOKED` frame (`F10`), DEK crypto-shredding (`D9`). | `T-F9`, `T-F10`, `T-P2`, `T-P3`, `T-P5` |
| **Denial of Service** | Rival hospital locks out duty PIN; bot floods QR join; flaky network retry storm. | Per-session/per-`call_sid` lockout scope (`F7`), Turnstile challenge + 20-desk cap (`D11`), advisory lock + idempotent replay (`F14`). | `T-F7`, `T-F14`, `T-N8` |
| **Elevation of Privilege** | BOLA (Hospital A acts on Hospital B's offer); AI agent modifies `spec/` to pass CI. | Step 5 object-level `actor_facility_id == offer.facility_id` check; CODEOWNERS hash-pinning on `spec/`, `db/schema.sql`, and `monitor/`. | `T-I6b`, `T-F17` |

### 5.2 Indian Regulatory & Legal Posture ("Designed to Comply", `REAL_DATA=0`)

| Statute / Guideline | Architectural Posture & Parameterization | Residual Status |
|---|---|---|
| **DPDP Act 2023 & DPDP Rules 2025** | Rules commencement cited as 13 Nov 2025 vs Gazette 14 Nov 2025 `[CONFLICT]`; core obligations apply May 2027 `[V]`. Emergency processing under s.7(f) (some texts cite s.7(d) `[CONFLICT]`) logged narrowly; staff telemetry under s.7(i) requires prior written notice, minimisation, HR siloing, and erasure. Safeguards ceiling ₹250 Cr (s.8(5)); breach notification ceiling ₹200 Cr / 72 h DPBI report (s.8(6)). Interplay between s.8(7) erasure and 3-year clinical retention is parameterized `[GAP]`. | `OPEN` (requires formal legal opinion before real data) |
| **Bharatiya Sakshya Adhiniyam (BSA) 2023 s.63** | System generates a BSA s.63-ready export bundle (RFC 8785 JCS event file, per-file SHA-256, bundle SHA-256, and pre-filled Part A Custodian + Part B Expert certificate templates citing the hash). Never claimed as "BSA certified" `[V*]`. | `BOUNDED` |
| **CERT-In Directions 2022** | 6-hour incident reporting runbook; 180-day rolling logs retained in India; chrony slew-only NTP synchronized to NIC/NPL strata `[V]`. | `BOUNDED` |
| **TRAI TCCCPR / DLT** | SMS uses static pre-registered template `"RHP alert: new referral. Open {#var#}"` with variable $\le 30$ chars and whitelisted domain; zero clinical text over SMS `[V]`. Voice legality for de-identified clinical prompts is unsettled `[GAP]`; prototype uses sandbox + $\le 10$ whitelisted team numbers. | SMS: `CLOSED`; Voice: `OPEN` |
| **ABDM / NRCeS FHIR R4** | No M3 longitudinal health record fetch (unconscious patient cannot consent `[GAP]`). Summary is clinician-authored at origin; exports validated FHIR R4 `ServiceRequest` + `Task` bundles. | `BOUNDED` |
| **ICMR 2017 & 2023 Ethics Guidelines** | Any shadow-mode district pilot requires Institutional Ethics Committee (IEC) approval (full committee review if pregnant women's identifiable data are used or clinical decisions are influenced). Mandatory human-in-the-loop override for AI (`T3_EXTRAS`). | `OPEN` (for pilot stage) |