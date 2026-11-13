---
name: security-audit
description: Audit ReferralHandshake (RHP-1) security controls, enrollment tickets, Argon2id per-session PIN lockout, SSE per-event grant revocation, AES-256-GCM envelope encryption and crypto-shredding, separate-OS-user witness signing, DPDP/BSA/TRAI/CERT-In legal posture, and Claims Register compliance.
owner_lane: Gem 2 (Auditor), Gem 3 (Adversary), Lane A & Lane B Security Enforcement
tier_scope: T0, T1, T2, T3
spec_anchors:
  - ReferralHandshake_FINAL_LOCKED_Architecture.md (§1, §8, §9, §10, §11, §18, §19, §20)
  - ReferralHandshake_v8_LOCKED_Solution.md (§10, §15, §16)
  - ReferralHandshake_LOCKED_Problem_Statement_v7.md (§1, §12, Appendix A, Appendix B)
invariants_enforced:
  - I5
  - I6
  - I8
  - I10
  - I11
  - I13
  - I14
codeowners_restricted:
  - spec/
  - db/schema.sql
  - monitor/
---

# RHP-1 Security, Privacy & Claims Audit Skill (`security-audit`)

## 1. Mission & Threat Model Scope
You enforce the security, cryptographic privacy, tamper-evidence, regulatory posture, and strict evidence/claims discipline of **ReferralHandshake (Protocol RHP-1)**. Every weakness identified in the system must be classified as:
* **`CLOSED`:** Prevented by a deterministic mechanism in the architecture and verified by a named automated test (`T-...`).
* **`BOUNDED`:** Mitigated with an explicit, quantified technical residual and a live runtime monitor alarm (never write a bare `"none"` in any residual risk column—enforced by `T-F15`).
* **`OPEN`:** Assigned to a named owner with the exact closing evidence required before real-world use.

---

## 2. Identity, Device Enrollment & Per-Session PIN Lockout (F7 / I6 / §9)

### 2.1 Single-Use Ticket Enrollment & Opaque Sessions
1. **Enrollment Flow:** An `ADMIN` issues a single-use `enrollment_ticket` (valid 15 minutes; only `SHA-256(token)` is stored in `enrollment_ticket.token_hash`). The field device generates an Ed25519 keypair, redeems the ticket with its 32-byte `pubkey`, and creates a `device` row (`octet_length(pubkey) = 32`).
2. **Session Tokens:** Authenticated sessions use high-entropy opaque random tokens stored only as `SHA-256` hashes in `session.token_hash` (delivered to PWAs as `HttpOnly; Secure; SameSite=Strict` cookies). No self-minted or stateless unrevocable JWTs are permitted (`D11`).
3. **Voice Call Sessions:** Outbound Exotel IVR calls authenticate by matching the pre-registered `roster.phone_e164` and binding the session to `session.call_sid` (`device_id IS NULL, call_sid IS NOT NULL`), gated by AMD + press-1 (`"Press 1 to hear a referral"`) before `ACK` and server-verified PIN before `ACCEPT` / `COUNTER` / `DECLINE`.

### 2.2 Anti-DoS Per-Session PIN Lockout (`T-F7 pin_lockout_scope`)
* **Argon2id Verification:** Every state-mutating command (`RESOURCE_CONFIRM`, `ACCEPT`, `COUNTER`, `DECLINE`) requires the rostered role's PIN, verified on the server via memory-hard **Argon2id** ($\approx 100\text{ ms}$ on the demo host).
* **Autonomous Failure Counter:** When PIN verification fails in Step 3 of `apply_command()`, increment `session.pin_failed` on a **separate autonomous database connection** that commits immediately, so rolling back the main command transaction cannot reset the failure counter.
* **Lockout Scope (Prevents Rival Lockout-DoS):** Backoff delays (`0s`, `5s`, `30s`, then lock for `120s` at 3 strikes) are scoped strictly to the individual `(session_id OR call_sid)`, **never** globally to the facility or `roster_id`. Thus, a malicious caller or rival desk cannot lock out a hospital's legitimate logged-in web desk session.
* **Escalation on Abuse:** The 3rd failed strike on a session emits a `PIN_LOCKED` event and pages the dispatcher; repeated lockouts across multiple sessions on the same roster slot suspend that slot pending admin review.

### 2.3 Judge QR Admission & Fail-Closed LAN Mode (§9 / D11)
* **Rotating QR:** The big-screen join QR encodes a single-use `jti` valid for 20 seconds and rotates every 15 seconds, plus the pinned Ed25519 public keys (`signer_pub`, `cold_pub`).
* **Bot & Crowd Control:** Require a Cloudflare Turnstile challenge before minting any `JUDGE_DESK` session, enforce an admission cap of **20 concurrent judge desks**, and restrict `JUDGE_DESK` to synthetic referrals (`REAL_DATA=0`).
* **Fail-Closed LAN Fallback (`N7`):** If venue internet fails, LAN mode caps admission at 20 desks, serves synthetic data only, **refuses boot (`exit 78`) if `REAL_DATA=1`**, and disables PIN entry over plain HTTP.

---

## 3. Cryptographic Privacy, Envelope Encryption & PHI-Free Metadata (§10)

### 3.1 AES-256-GCM Envelope Encryption & 4-Step Crypto-Shredding (D9)
* **Per-Referral DEK:** Each referral generates a unique 256-bit Data Encryption Key (DEK).
* **KEK Wrapping:** The DEK is wrapped with AES Key Wrap (`AES-KW`) under a monthly Key Encryption Key (`kek_epoch`) and stored in `key_version.wrapped_dek`.
* **Authenticated Additional Data (AAD):**
  * `clinical_payload` AES-256-GCM ciphertext binds $\text{AAD} = \text{referral\_id} \parallel \text{key\_id} \parallel \text{schema\_ver}$.
  * `event_secret` AES-256-GCM ciphertext binds $\text{AAD} = \text{referral\_id} \parallel \text{seq} \parallel \text{key\_id}$.
* **Chain Binding Without PHI:** `event.secret_hash` stores `SHA-256(ciphertext)`. When `clinical_payload` and `event_secret` are deleted and `key_version.wrapped_dek` is set to `NULL` (`status = 'SHREDDED'`), the per-referral hash chain in `event` remains 100% verifiable.
* **Backup & Cache Hygiene:** All decrypted clinical responses must carry `Cache-Control: no-store`. Once all referrals in a `kek_epoch` expire, destroy the KEK epoch key so historical WAL segments and backups cannot decrypt shredded payloads (`T-P5`).

### 3.2 Zero PHI in Metadata, Push, SMS & Revoked Streams (F9 / F10 / I10 / I11)
1. **`event.detail` Strict Allowlist (I11 / F9):** Enforced by both Pydantic `Literal` schemas and PostgreSQL `CHECK (rhp_detail_ok(type, detail))`. Only allowlisted keys per `event.type` with booleans, $\le 12$-digit integers, UUIDs, or uppercase enum tokens (`^[A-Z0-9_]{1,40}$`) are permitted.
2. **Aggregate Export Anonymity:** Public/aggregate exports bucket timestamps into **4-hour windows** and suppress any cell with fewer than **5 referrals ($k \ge 5$)**.
3. **Zero-Payload Push & Static DLT SMS (`T-P2`, `T-P3`):**
   * FCM push notifications carry an empty wake payload (`{}`); the Android app performs an authenticated HTTPS fetch to retrieve clinical details.
   * SMS uses a static DLT-compliant template (`"RHP alert: new referral. Open {#var#}"` where `{#var#}` is $\le 30$ chars on a whitelisted static domain) with zero clinical text (`[V]`).
   * Exotel voice prompts speak only de-identified metadata (origin facility, reason code, ETA) using native pre-recorded Kannada/Hindi/English audio phrases—never the patient's name.

---

## 4. Separate-OS-User Witness Signer & Tamper vs Restore Audit (F8 / §11)

1. **Process & Privilege Isolation:** The checkpoint signer runs as dedicated OS user `rhp-sign` (`uid 1002`), reads its Ed25519 private key from a `0400` file unreadable by `rhp_app`, and connects to PostgreSQL as `rhp_witness`.
2. **5-Second Binary Merkle Checkpoints:** Every 5 seconds, `rhp-sign` reads a `REPEATABLE READ READ ONLY` snapshot of `(referral_id, head_seq, head_hash)` ordered by `referral_id`, computes the binary Merkle root:
   * $\text{Leaf} = \text{SHA-256}(\texttt{0x00} \parallel \text{referral\_id}_{16\text{B}} \parallel \text{head\_seq}_{8\text{B BE}} \parallel \text{head\_hash}_{32\text{B}})$
   * $\text{Node} = \text{SHA-256}(\texttt{0x01} \parallel \text{left}_{32\text{B}} \parallel \text{right}_{32\text{B}})$ (odd node promoted unchanged)
   and signs a C2SP-style note distributed to independent witnesses (Guarantee Arena screen, judges' phones via `/checkpoints/latest`, and an off-box log).
3. **Distinguishing Legitimate Restore from Malicious Truncation (`T-F8`):** Any decrease in `head_seq` compared to a witnessed checkpoint is flagged as `TRUNCATED` / `TAMPER` **unless** accompanied by a `checkpoint(kind='RESTORE')` carrying a valid offline `cold_signature` and per-referral `RESTORE` events linking the restored head hash.

---

## 5. Indian Legal & Regulatory Audit Checklist (§10, §19)

| Framework | Mandatory Architectural & Presentation Posture | Audit Status |
|---|---|---|
| **DPDP Act 2023 & Rules 2025** | Prototype uses synthetic data only (`REAL_DATA=0`). Note commencement date conflict (`13 Nov 2025` vs Gazette `14 Nov 2025` `[CONFLICT]`; core obligations `13/14 May 2027` `[V]`). Cite emergency processing narrowly (`s.7(f)` vs `s.7(d)` `[CONFLICT]`). Staff telemetry (`s.7(i)`) requires prior written notice, minimisation, siloing from HR records, and erasure. Retention interplay (`s.8(7)` erasure vs 3-year NMC telemedicine retention `[GAP]`) is parameterised. | `OPEN` (Legal review before pilot) |
| **BSA 2023 s.63** | Export bundle produces RFC 8785 JCS event log, per-file SHA-256, bundle SHA-256, and unexecuted Part A (Custodian) & Part B (Expert) certificate templates. **Never** claim the system is "BSA certified" or produces "legally conclusive immutable evidence". | `BOUNDED` |
| **CERT-In Directions 2022** | 6-hour incident reporting runbook, 180-day rolling logs in India, chrony slew-only NTP traceable to NIC/NPL (`[V]`). | `BOUNDED` |
| **TRAI TCCCPR / DLT** | Static template, variables $\le 30$ chars, whitelisted domain, Exotel sandbox/trial with $\le 10$ pre-verified numbers (`[V]`). Never circumvent telecom controls; exclude WhatsApp completely. | `CLOSED` by design |
| **ABDM & FHIR R4** | No longitudinal record fetch (unconscious patient cannot give M3 consent `[GAP]`). Clinician-authored point-of-care summary; curated FHIR R4 export (`ServiceRequest`, `Task`, `Encounter`, `Communication`). Claim `"ABDM-sandbox aligned"` **only** if sandbox calls are made; never `"ABDM compliant"`. | `BOUNDED` |
| **ICMR 2017 / 2023** | Shadow-mode district pilot requires Institutional Ethics Committee review (full review if identifiable data of pregnant women or decision influence is involved); human-in-the-loop override is mandatory for AI. | `OPEN` |

---

## 6. Claims Discipline & Evidence Register Audit (§19 / Problem v7)

Every slide, UI label, README, API doc, and pitch script must pass this exact filter (`ST-5`):

| Authorized Wording (Permitted) | Forbidden Wording (Immediate S1 Audit Failure) |
|---|---|
| "Referral communication and documentation gaps are documented in specific urban Indian studies (Das et al. 2023: 47% phoned, 53% no phone contact, 37% slips complete, 60% tracked — quote percentages only due to 25,253 vs 28,020 denominator `[CONFLICT]`; Safdarjung 2018–2023: 90.6% no prior communication, 70% no escort, 47.3% visited $\ge 2$ hospitals `[V]`)." | National prevalence claims, "deaths prevented", "lives saved", "maternal mortality reduced", or quoting Ethiopia's "47% refused referral". |
| "Automatic inter-facility escalation and hard single-owner guarantees were not found in public documentation of the systems audited `[V*]`." | "First in the world", "only system", "no competitor has this". |
| "Control-plane model checked within stated bounds ($F=3, E=4$); implementation checked by conformance vectors, 200-way barrier tests, and an independent runtime monitor." | "Mathematically proven system", "mathematically impenetrable", "100% bug-free". |
| "Every identified weakness is `CLOSED`, `BOUNDED` with a stated residual and alarm, or `OPEN` with a named owner." | "Bullet-proof", "airtight", "zero loopholes", "zero silent drops", "crash-proof", "immune". |
| "Tamper-evident hash-chained log with independent witnesses and BSA s.63-ready export templates." | "Immutable log", "blockchain-grade immutability", "BSA certified". |
| "Designed to comply; FHIR-shaped export; process improvement is a hypothesis to test in an ethics-approved pilot." | "ABDM compliant", "production-ready", "eliminates ping-pong". |

---

## 7. Explicit DO / DO NOT Guardrails

### DO
* **DO** audit every request route for Object-Level Authorization (BOLA), verifying that the caller's `session.roster_id` and `facility_id` have an active relationship (`origin_facility_id`, open/accepted `offer`, or `DISPATCHER`) to the target `referral_id` (`T-I6b`).
* **DO** verify that `REAL_DATA=0` is enforced in `.env` and that no API keys, Exotel credentials, or private signing keys appear in git commits or agent reports.
* **DO** challenge any audit report where Gem 2 marks a security control `PASS` without raw test output (`T-F7`, `T-F8`, `T-F9`, `T-F10`, `T-F20`).

### DO NOT
* **DO NOT** permit PIN lockout counters to be stored on `roster` or `facility` where an attacker can trigger a facility-wide Denial of Service (`D12` / `F7`).
* **DO NOT** allow `BROKEN_BUILD=1` to connect to the primary database or share database credentials with `rhp_app` (`F20`).
* **DO NOT** allow any UI component, log message, or pitch artifact to use any phrase from the Forbidden Wording column of §19.