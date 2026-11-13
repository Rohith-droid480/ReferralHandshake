---
trigger: always_on
scope: "**/*"
authority: ReferralHandshake_FINAL_LOCKED_Architecture.md
sections: "§8, §9, §10, §11, §12"
invariants: "I5, I6, I8, I10, I11"
---

# `.agents/rules/security-standards.md` — Security, Cryptography, Privacy & Regulatory Posture

Every authentication check, session token, PIN verification, encryption routine, SSE stream, and log entry in **ReferralHandshake (Protocol RHP-1)** is governed by this security specification.

---

## 1. Identity, Device Enrollment & Session Lifecycle (`F7`, `I6`)

1. **Roster-Bound Authority (`I6`):**
   - Offers are addressed to a facility's **duty role slot** (`NURSE`, `CMO`, `CONSULTANT`), never an ad-hoc unrostered individual.
   - Every `ACCEPT`, `COUNTER`, `DECLINE`, and `RESOURCE_CONFIRM` requires an active `roster` row (`valid_from <= server_ts` and `(valid_to IS NULL OR valid_to > server_ts)`), a registered `device` (or verified Exotel `call_sid` on the rostered `phone_e164`), and a verified PIN—unless executed by a rostered `DISPATCHER` with `proxy=true`, `proxy_for=<roster_id>`, and a structured reason code.
2. **Single-Use Device Enrollment (`F7`):**
   - An `ADMIN` issues a single-use `enrollment_ticket` (15-minute expiry; only `SHA-256(token)` is stored in `enrollment_ticket.token_hash`).
   - The client generates an Ed25519 keypair (`32-byte` public key) and redeems the ticket once (`used_at` stamped, `device` row created).
   - Authenticated sessions use high-entropy opaque random tokens where only `SHA-256(session_token)` is stored in `session.token_hash`.
   - Voice IVR sessions set `session.call_sid` (`device_id IS NULL`), satisfying `CHECK (device_id IS NOT NULL OR call_sid IS NOT NULL)`.

---

## 2. Server-Verified PIN & Autonomous Lockout Scoping (`D12`, `F7`)

1. **Argon2id Verification:**
   - All PIN hashes in `roster.pin_hash` use Argon2id tuned to $\approx 100\text{ ms}$ verification latency on the target host.
   - PIN verification happens on the server in Step 3 of `apply_command()`. Client-side PIN checks are forbidden.
2. **Per-Session / Per-Call Lockout Scope (Anti-DoS `F7`):**
   - `pin_failed` and `pin_locked_until` live on the `session` table (scoped to `session.id` or `session.call_sid`), **NOT** on the `roster` or `facility` row. This prevents an attacker or rival desk from locking out a hospital's entire duty role.
   - **Autonomous Transaction Rule:** When `argon2_verify` fails, `session.pin_failed` and `session.pin_locked_until` **MUST** be updated and committed on a **separate autonomous database connection** before `apply_command()` returns `403 PIN_INVALID`. Rolling back the command transaction must never roll back the failed-attempt counter.
   - **Backoff Schedule:** Strike 1 = $0\text{ s}$, Strike 2 = $5\text{ s}$, Strike 3 = $30\text{ s}$ lock + `PIN_LOCKED` event + dispatcher page; subsequent strikes lock the session for $120\text{ s}$. Repeated lockouts across multiple sessions on the same roster slot flag the slot for admin review.

---

## 3. Envelope Encryption, Crypto-Shredding & PHI Zero-Leakage (`D9`, `F9`, `F10`, `I10`, `I11`)

### 3.1 Per-Referral Envelope Encryption (`D9`, §10)
- **Data Encryption Key (DEK):** Each referral gets a unique 256-bit AES-GCM DEK at `CREATE`.
- **Key Encryption Key (KEK):** Each DEK is wrapped via AES-KW (`wrapped_dek` in `key_version`) under a monthly `kek_epoch` key.
- **Authenticated Additional Data (AAD):**
  - `clinical_payload` ciphertext AAD: `referral_id || key_id || schema_ver`
  - `event_secret` ciphertext AAD: `referral_id || seq || key_id`
- **Hash-Chain Binding:** `event.secret_hash = SHA256(nonce || ciphertext)` is included in the JCS `core` of `event`. This binds the encrypted clinical content into the hash chain so that deleting the ciphertext during crypto-shredding **never** invalidates the SHA-256 event hash chain.

### 3.2 Four-Step Crypto-Shredding Walk-Through (`P5`)
When `clinical_payload.expires_at` is reached (or upon retention expiry after `CLOSED`):
1. `DELETE FROM clinical_payload WHERE referral_id = $1` and `DELETE FROM event_secret WHERE referral_id = $1`.
2. `UPDATE key_version SET wrapped_dek = NULL, status = 'SHREDDED', shredded_at = clock_timestamp() WHERE referral_id = $1` (enforced by `CHECK ((status='SHREDDED') = (wrapped_dek IS NULL))`).
3. When all referrals belonging to a monthly `kek_epoch` have expired, destroy the `kek_epoch` master key so that any historical `wrapped_dek` copies inside PostgreSQL WAL archives or logical backups become permanently unrecoverable.
4. Decrypted payloads exist only in transient API process memory; every response returning clinical data **MUST** include `Cache-Control: no-store`.

### 3.3 Zero PHI in Metadata, Push, SMS, Voice, and Revoked Streams
- **`event.detail` Allowlist (`F9`, `I11`):** Enforced by both Pydantic `Literal` schemas (`extra='forbid'`) and the PostgreSQL `rhp_detail_ok(type, detail)` `CHECK` constraint. Free-text strings, patient names, phone numbers, and ABHA IDs are physically rejected by the database in `event.detail`.
- **Empty-Payload FCM (`P3`):** Android push notifications carry **zero payload** (wake ping only); the app fetches details over authenticated HTTPS.
- **Static DLT SMS (`P2`):** SMS carries only `"RHP alert: new referral. Open {#var#}"` where `{#var#}` is $\le 30$ characters on a whitelisted static domain. Zero clinical text is sent via SMS.
- **De-Identified Voice IVR:** Speaks only originating facility name, structured reason code, and ETA. Patient names are never spoken.
- **Stream Grant Revocation (`F10`, `I10`):** SSE checks `payload_grant.revoked_at IS NULL` on every frame emit and every $15\text{ s}$ heartbeat. When a facility declines, times out, is superseded, or rejects on arrival, its `payload_grant` is revoked in the same transaction and a `GRANT_REVOKED` control frame wipes the client DOM.
- **Aggregate Export K-Anonymity (`F9`):** Shared/public exports and XES logs bucket timestamps to **4-hour windows** and suppress any cell with fewer than $k = 5$ referrals.

---

## 4. Tamper Evidence, Independent Witnesses & Cold-Key Restore (`D10`, `F8`, `I5`)

1. **Separate-OS-User Signer (`witness/`):**
   - Runs as dedicated OS user `rhp-sign` (`user: "1002"` in Docker), with Ed25519 private key file mode `0400`, connecting to PostgreSQL as `rhp_witness`.
   - Every $5\text{ s}$, takes a `REPEATABLE READ READ ONLY` snapshot of all referrals ordered by `id` and constructs a binary Merkle tree:
     - **Leaf:** $\text{SHA256}(\texttt{0x00} \parallel \text{referral\_id}_{16\text{B}} \parallel \text{head\_seq}_{8\text{B BE}} \parallel \text{head\_hash}_{32\text{B}})$
     - **Internal Node:** $\text{SHA256}(\texttt{0x01} \parallel \text{left}_{32\text{B}} \parallel \text{right}_{32\text{B}})$ (odd node promoted unchanged)
   - Signs C2SP-format note (`rhp1/<deployment>\n<tree_size>\n<root_b64>\n`) and inserts into `checkpoint`.
   - Published to independent witnesses: Big Screen, judges' phones (`/checkpoints/latest` with `Cache-Control: no-store`), and an off-box append-only witness log.
2. **Pure-JS Browser Verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`):**
   - Step 1: Verify checkpoint Ed25519 signature against QR-pinned public key $\rightarrow$ else `CHECKPOINT_SIG`.
   - Step 2: Recompute event chain from genesis `0x00 * 32` $\rightarrow$ on mismatch output `BROKEN referral=<id> seq=<n> kind=PREV|HASH expected=<h1> got=<h2>`; on missing `seq` output `SEQ_GAP`.
   - Step 3: Fold $O(\log N)$ Merkle inclusion proof path $\rightarrow$ on mismatch output `ROOT_MISMATCH`.
   - Step 4: If live `head_seq` is less than checkpointed `head_seq` without a valid cold-key signed `RESTORE` checkpoint and per-referral `RESTORE` event $\rightarrow$ output `TRUNCATED at seq=<k>`.

---

## 5. Judge Admission, LAN Mode & `BROKEN_BUILD` Safety Guards (`D11`, `F20`)

1. **Rotating QR + Turnstile (`D11`):**
   - Judge QR carries single-use `jti` valid for $20\text{ s}$ (rotates every $15\text{ s}$).
   - Requires Cloudflare Turnstile challenge completion before minting a `JUDGE_DESK` session.
   - Hard admission cap of **20 concurrent judge desks**.
2. **Fail-Closed LAN Mode:**
   - When venue internet fails, LAN mode serves over the local hotspot with cap $20$, enforces `REAL_DATA=0` (refuses boot if `REAL_DATA=1`), and disables PIN entry over plain HTTP.
3. **`BROKEN_BUILD=1` Hard Isolation (`F20`):**
   - Must abort process startup with **exit code `78`** if `REAL_DATA=1`, if the database name in DSN is not `rhp_scratch_broken`, or if the scratch DB role can connect to the primary database.
   - Big screen and desks must display a flashing red banner: `BROKEN BUILD — SCRATCH DB`.

---

## 6. STRIDE Controls & Regulatory Compliance Matrix (§9, §10)

| Threat / Regulation | Mandatory Engineering Control in RHP-1 | Posture / Status |
|---|---|---|
| **Spoofing / BOLA / Mass Assignment** | Roster + device/number + Argon2id PIN; object-level `facility_id` check on every route; Pydantic `extra='forbid'`; server-owned state | `CLOSED` (`T-I6`, `T-I6b`) |
| **DPDP Act 2023 / Rules 2025** | Synthetic data only (`REAL_DATA=0`); handover record vs medical record separation; per-referral DEK crypto-shredding; s.7(i) staff telemetry notice & HR siloing | Designed to comply (`OPEN` legal review on s.8(7) vs NMC 3-yr retention `[GAP]`) |
| **BSA 2023 s.63** | Export bundle produces RFC 8785 JCS event file, per-file SHA-256, bundle SHA-256, and Part A / Part B certificate templates | `BOUNDED` (never claim "BSA certified") |
| **CERT-In 2022 Directions** | Chrony slew-only NTP to NIC/NPL (`heartbeat.ntp_offset_ms` alarm at $> 2\text{ s}$); 180-day rolling log structure; 6-h incident runbook | `BOUNDED` |
| **TRAI TCCCPR / DLT** | Static template, variable $\le 30\text{ chars}$, whitelisted domain, zero clinical text in SMS; sandbox/whitelisted numbers for voice | `CLOSED` by design |