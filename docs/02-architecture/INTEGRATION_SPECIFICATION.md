# ReferralHandshake (Protocol RHP-1) — Integration Specification

**Architectural Principle:** Every external channel or adapter (Exotel Voice IVR, DLT SMS, Paper Code, Android Foreground Location Service, Mapbox ETA Matrix, Pure-JS Browser Verifier, FHIR R4, IEEE 1849 XES, and Toxiproxy) is a stateless interface that **produces or consumes contract events** or **projects the committed event log**. Adapters hold zero authoritative state and zero business logic.

---

## 1. Unified Notice Ladder & Channel Matrix (`F2`, Section 8)

### 1.1 Role-to-Channel Matrix

| Actor / Role | Primary Interface | Deterministic Fallback Chain |
|---|---|---|
| **Referring Clinician** | React PWA Card / Android App | Dispatcher phone-assisted proxy (`proxy=true`, `channel='DISPATCHER_PROXY'`) |
| **Receiving Duty Role (`NURSE`, `CMO`, `CONSULTANT`)** | React PWA Desk (SSE + Audio Alert) | **Rung 0:** SSE + empty-payload FCM wake $\rightarrow$ **Rung $A/4$:** Outbound Exotel Voice IVR (`Press 1` + PIN) + DLT Static SMS Link $\rightarrow$ **Rung $3A/4$:** Dispatcher phone-assisted proxy $\rightarrow$ **At Door:** 9-char Paper Code entry |
| **Ambulance Crew (`EMT`)** | Native Android App (`T3`) / PWA GPS (`T1`) | EMT or Dispatcher proxy status update; $200\text{ m}$ geofence hint confirmed at receiving desk |
| **Dispatcher (`DISPATCHER`)** | Dispatcher Console (PWA) | Direct phone outreach recorded as proxy |
| **District Officer (`ADMIN`)** | Command Centre Read-Only View | Weekly FHIR R4 / IEEE 1849 XES / BSA s.63 export bundle |

### 1.2 Concurrent Roster Slot Notification & Stagger Math
When an offer opens (`status='OPEN'`) at time $t_0$:
1. **Rung $0$ ($t = t_0$):** Outbox rows (`channel='SSE'`, `channel='FCM'`, `channel='SMS'`) are inserted for all $S$ active rostered duty slots (`NURSE` slot 1, `CMO` slot 2, `CONSULTANT` slot 3) concurrently.
2. **Rung $A/4$ ($t = t_0 + A/4 + i \cdot \delta$):** When the `NOTICE_VOICE` deadline fires at $t_0 + A/4$, the outbox relay initiates outbound Exotel voice calls to slot $i \in \{0, \dots, S-1\}$ staggered by $\delta\text{ ms}$.
3. **Ladder Termination:** The instant any rostered slot commits `ACK` (via PWA or Voice `Press 1`), all remaining `NOTICE_VOICE` and `NOTICE_PROXY` deadlines for that offer are marked `CANCELLED`.
4. **Pre-Warm Advisory (`ADVISORY_PREWARM`):** If facility $k$ has committed `ACK` but has not yet decided at $t_0 + A$, the poller emits `ADVISORY_PREWARM` to facility $k+1$ (carries no deadline, cannot `ACCEPT`, and does not count toward `open_offers`).

---

## 2. Exotel Outbound IVR & Voice Webhook Integration (`F7`, `T2_REACH`)

### 2.1 Sandbox Constraints & Outbound Call Initiation
- **Trial Whitelist:** Exotel trial accounts permit outbound calls only to $\le 10$ pre-verified E.164 phone numbers (`[V]`). These numbers are seeded in `roster.phone_e164` for the team's feature phone and test handsets.
- **No Inbound Number Required:** The platform initiates outbound calls exclusively via `POST https://api.exotel.com/v1/Accounts/{sid}/Calls/connect.json` connecting the target `phone_e164` to the Exotel Passthru / Gather applet URL.
- **Zero Spoken PHI:** Audio prompts use pre-recorded native-speaker wave files (Kannada, Hindi, English) for fixed clinical phrases (`"Emergency obstetric referral"`, `"Severe pre-eclampsia"`, `"Requires CEmONC OT and NICU"`), combined with dynamic synthesis only for facility code and integer ETA minutes. Patient names or identifiers are never spoken.

### 2.2 Call Flow, AMD Gate & Webhook Budget ($\le 2\text{ s}$)
Exotel webhooks time out at $5\text{ s}$ (`[V]`). ReferralHandshake enforces a strict **$2.0\text{ s}$ total webhook budget** ($1.5\text{ s}$ database execution budget):

```
[Exotel Outbound Dial]
       |
       v
1. POST /v1/webhooks/exotel/connect
   - Checks CallSid in inbox(source='EXOTEL', external_id=CallSid:connect).
   - Evaluates Answering Machine Detection (AMDStatus). If 'machine' -> hangup (UNANSWERED).
   - Plays Gate Prompt: "Emergency referral alert. Press 1 to acknowledge and hear details." (8s Gather timeout).
       |
       v (Caller presses '1')
2. GET/POST /v1/webhooks/exotel/ack?CallSid=...&digits=1
   - Deduplicates in inbox(source='EXOTEL', external_id=CallSid:ack).
   - Runs apply_command(ACK, channel='VOICE') with 1.5s timeout.
   - COMMIT-BEFORE-CONFIRM RULE: Only after PostgreSQL commits the ACK does the webhook return
     the applet response playing the de-identified clinical summary + Menu:
     "Press 1 to Accept all required resources, Press 2 to Counter with conditions,
      Press 3 to Decline, or Press 9 to repeat."
       |
       v (Caller presses '1', '2', or '3')
3. GET/POST /v1/webhooks/exotel/menu?CallSid=...&digits=1
   - If '1' (Accept): prompts "Enter your 4-digit duty PIN followed by hash."
   - If '2' (Counter): prompts "Press 1 for no NICU, 2 for Anaesthetist in 20 minutes, 4 for Blood on request, then PIN and hash."
   - If '3' (Decline): prompts "Press 1 for no OT, 2 for no NICU, 3 for no Anaesthetist, 4 for no Blood, 6 for At Capacity, then PIN and hash."
       |
       v (Caller enters PIN + '#', delivered by Exotel as URL-encoded '%23')
4. GET/POST /v1/webhooks/exotel/decision?CallSid=...&digits=7391%23
   - Strips trailing '#' / '%23'.
   - Runs apply_command(ACCEPT | COUNTER | DECLINE) within 1.5s budget.
   - If DB commits within 1.5s: plays "Confirmed. Ownership lease granted [or response recorded]."
   - If DB exceeds 1.5s budget: plays "Please hold while we confirm" and redirects to /v1/webhooks/exotel/poll?CallSid=...
     which reads the committed idempotency record on the next callback.
```

### 2.3 Per-Call Lockout (`F7`)
Voice sessions are stored in `session` keyed by `call_sid` (`device_id IS NULL`). Three invalid PIN entries on a call leg lock that `call_sid`, play `"PIN locked. Transferring to dispatcher"`, hang up, and emit `PIN_LOCKED` + `PROXY_PAGE` to the dispatcher console without locking out the hospital's web desk sessions.

---

## 3. TRAI TCCCPR / DLT Static SMS Adapter (`P2`, `T2_REACH`)

- **Regulatory Constraint:** Under TRAI TCCCPR 2018 / DLT rules, variable fields `{#var#}` are capped at $30$ characters, URLs must match pre-whitelisted static domains, and clinical text triggers silent carrier drops (`[V]`).
- **Locked Static Template:**
  ```text
  RHP alert: new referral. Open {#var#}
  ```
  where `{#var#}` is strictly `<short_domain>/r/<9_char_paper_code>` (e.g., `rhp.in/r/48K9M2P7W`, $18$ characters $\le 30$). Zero clinical data or patient identifiers ever traverse SMS.

---

## 4. Crockford Base32 + Mod-37 Paper Code Specification (`T2_REACH`)

Every referral generates a unique 9-character `paper_code` printed at the top of the referral card (which serves as the physical Dakshata referral slip, eliminating double entry):
- **Payload ($8$ characters):** 40-bit random integer $N \in [0, 2^{40}-1]$ encoded as $8$ Crockford Base32 symbols (`0123456789ABCDEFGHJKMNPQRSTVWXYZ`).
- **Check Symbol ($1$ character):** $c = N \bmod 37$ mapped onto the 37-character Crockford check alphabet:
  `0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U`
- **Mathematical Error Detection Guarantee:** Because $37$ is a prime greater than $32$, $\gcd(32^i, 37) = 1$ for all positions $i \in \{0, \dots, 7\}$.
  - Any single-character substitution error $\Delta \not\equiv 0 \pmod{37}$ changes $N$ by $\Delta \cdot 32^i \not\equiv 0 \pmod{37}$ ($100\%$ detected).
  - Any adjacent transposition of distinct values $a \ne b$ changes $N$ by $(a - b) \cdot 31 \cdot 32^i \not\equiv 0 \pmod{37}$ ($100\%$ detected).

```python
CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CHECK_ALPHABET = CROCKFORD_ALPHABET + "*~$=U"
CONFUSABLES = str.maketrans({"O": "0", "o": "0", "I": "1", "i": "1", "L": "1", "l": "1"})

def encode_paper_code(n_40bit: int) -> str:
    assert 0 <= n_40bit < (1 << 40)
    chars = []
    val = n_40bit
    for _ in range(8):
        chars.append(CROCKFORD_ALPHABET[val & 0x1F])
        val >>= 5
    body = "".join(reversed(chars))
    check = CHECK_ALPHABET[n_40bit % 37]
    return body + check

def verify_paper_code(raw: str) -> bool:
    s = raw.strip().upper().translate(CONFUSABLES)
    if len(s) != 9:
        return False
    body, check_ch = s[:8], s[8]
    if check_ch not in CHECK_ALPHABET:
        return False
    n = 0
    for ch in body:
        idx = CROCKFORD_ALPHABET.find(ch)
        if idx < 0:
            return False
        n = (n << 5) | idx
    return CHECK_ALPHABET[n % 37] == check_ch
```

---

## 5. Android Native Client (`T3`) & PWA Ambulance Fallback (`T1`)

### 5.1 Android Foreground Location Service & Geofence Hint (`D2`, `F5`)
- **Service Declaration:** `android:foregroundServiceType="location"` with `ACCESS_FINE_LOCATION` and persistent notification `"ReferralHandshake Active Transport Tracking"`.
- **Sampling Cadence:** `FusedLocationProviderClient` with `PRIORITY_HIGH_ACCURACY`, interval $5,000\text{ ms}$, fastest interval $2,000\text{ ms}$.
- **200 m Geofence Hint:** When horizontal accuracy $\text{acc\_m} \le 50\text{ m}$ and Haversine distance to `tr_facility_id` is $\le 200\text{ m}$ for a continuous dwell $\ge 30\text{ s}$ at speed $< 3\text{ m/s}$, the client submits `POST /v1/referrals/{id}/transport` with `suggestion_only: true`, emitting `ARRIVAL_SUGGESTED`. A human EMT or receiving desk role must tap **Confirm Arrival** to transition `tr_state` to `ARRIVED`.

### 5.2 Offline Room Outbox & Stale Confirmation Re-Confirm Flow (`F12`, `I15`)
- **Telemetry Set-Union Merge:** GPS and vitals rows are queued in local SQLite/Room with client-generated UUIDv7 `event_id`s and flushed in batches to `/v1/referrals/{id}/telemetry` on reconnect.
- **Offline `ACCEPT` Handling:** If a receiving desk clicks **Accept** while offline, the UI displays an amber badge: `"ACCEPT PENDING — NOT CONFIRMED BY SERVER"`. When connectivity returns and the outbox flushes:
  - If the offer timed out and a successor ACKed (`409 LATE_ACCEPT_REJECTED`), the UI displays a modal alert explaining ownership moved.
  - If required resource confirmations expired while offline (`409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`), the UI opens a **Live Re-Confirmation Modal** that issues fresh `RESOURCE_CONFIRM` requests for each required capability followed by a new `ACCEPT` command with a new `Idempotency-Key`.

### 5.3 Zero-Payload FCM Wake Ping (`D13`, `P3`)
Push notifications sent via Firebase Cloud Messaging contain **zero clinical fields**:
```json
{
  "message": {
    "token": "<device_fcm_token>",
    "data": {
      "kind": "WAKE_SYNC",
      "outbox_id": "4091"
    },
    "android": { "priority": "high" }
  }
}
```
Upon receiving `WAKE_SYNC`, the Android app wakes and fetches the referral state over authenticated TLS (`GET /v1/referrals/{id}`).

---

## 6. Mapbox Directions & Matrix ETA Integration (`D14`, Section 9)

- **Server-Side Proxy & Caching:** Clients never call Mapbox directly with API keys. The backend computes road ETAs only for the active referral's top candidate facilities in `referral.chain` ($\le 8$ facilities) using:
  - `mapbox/driving` Matrix API (up to 25 coordinates, 60 requests/min `[V]`), or
  - `mapbox/driving-traffic` Matrix API (up to 10 coordinates, 30 requests/min `[V]`).
- **Cache TTL & Fallback:** Matrix responses are cached in-process for $120\text{ s}$ keyed by `( quantized_ambulance_lat_lon_e3, chain_hash )`. If the cache is older than $120\text{ s}$ or Mapbox is unreachable, the UI displays the last cached value labelled `"ETA stale"` or falls back to Haversine straight-line distance at $35\text{ km/h}$ labelled `"Estimated (offline)"`.
- **Map Tiles:** Map views use the Mapbox GL JS SDK (or self-hosted PMTiles on LAN fallback) to respect OpenStreetMap tile-server bulk-download policies (`R07`).

---

## 7. Pure-JS Browser Verifier & Interoperability Exporters

### 7.1 Pure-JS Browser Verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`)
Because iOS Safari lacks WebCrypto Ed25519 support (`[V]`) and `window.crypto.subtle` is disabled on plain HTTP LAN fallback origins (`[V]`), the React PWA bundles `@noble/curves/ed25519` and `@noble/hashes/sha256` directly:

```javascript
import { ed25519 } from "@noble/curves/ed25519";
import { sha256 } from "@noble/hashes/sha256";
import { bytesToHex, hexToBytes, utf8ToBytes } from "@noble/hashes/utils";

export function jcsBytes(obj) {
  const keys = Object.keys(obj).sort();
  const parts = keys.map((k) => {
    const v = obj[k];
    const valStr = v !== null && typeof v === "object" && !Array.isArray(v)
      ? new TextDecoder().decode(jcsBytes(v))
      : JSON.stringify(v);
    return `${JSON.stringify(k)}:${valStr}`;
  });
  return utf8ToBytes(`{${parts.join(",")}}`);
}

export function verifyReferralChainAndProof(events, checkpoint, proof, pinnedPubKeyHex) {
  // 1. Verify Ed25519 signature over C2SP checkpoint note text
  const sigOk = ed25519.verify(
    hexToBytes(checkpoint.signature_hex),
    utf8ToBytes(checkpoint.note_text),
    hexToBytes(pinnedPubKeyHex)
  );
  if (!sigOk) return { ok: false, error: "CHECKPOINT_SIG" };

  // 2. Recompute per-referral SHA-256 chain from genesis (32 zero bytes)
  let expectedPrev = new Uint8Array(32);
  let expectedSeq = 1;
  for (const ev of events) {
    if (ev.seq !== expectedSeq) {
      return { ok: false, error: `SEQ_GAP expected=${expectedSeq} got=${ev.seq}` };
    }
    if (bytesToHex(expectedPrev) !== ev.prev_hash_hex) {
      return { ok: false, error: `BROKEN referral=${ev.referral_id} seq=${ev.seq} kind=PREV expected=${bytesToHex(expectedPrev)} got=${ev.prev_hash_hex}` };
    }
    const coreBytes = jcsBytes(ev.core);
    const combined = new Uint8Array(expectedPrev.length + coreBytes.length);
    combined.set(expectedPrev, 0);
    combined.set(coreBytes, expectedPrev.length);
    const computedHash = bytesToHex(sha256(combined));
    if (computedHash !== ev.hash_hex) {
      return { ok: false, error: `BROKEN referral=${ev.referral_id} seq=${ev.seq} kind=HASH expected=${computedHash} got=${ev.hash_hex}` };
    }
    expectedPrev = hexToBytes(computedHash);
    expectedSeq += 1;
  }

  // 3. Check truncation against checkpointed head_seq
  const lastSeq = events.length ? events[events.length - 1].seq : 0;
  if (lastSeq < proof.head_seq && !proof.has_valid_restore) {
    return { ok: false, error: `TRUNCATED at seq=${lastSeq} (checkpoint head_seq=${proof.head_seq})` };
  }

  // 4. Fold Merkle inclusion path
  let node = hexToBytes(proof.leaf_hash_hex);
  for (const step of proof.path) {
    const sib = hexToBytes(step.hash_hex);
    const buf = new Uint8Array(1 + 32 + 32);
    buf[0] = 0x01;
    if (step.side === "R") {
      buf.set(node, 1);
      buf.set(sib, 33);
    } else {
      buf.set(sib, 1);
      buf.set(node, 33);
    }
    node = sha256(buf);
  }
  if (bytesToHex(node) !== checkpoint.root_hash_hex) {
    return { ok: false, error: "ROOT_MISMATCH" };
  }
  return { ok: true, head_seq: lastSeq, head_hash_hex: bytesToHex(expectedPrev) };
}
```

### 7.2 NRCeS-Aligned FHIR R4 Bundle Exporter (`T3_EXTRAS`, Section 15)
`GET /v1/exports/fhir/{referral_id}` projects the referral into a FHIR R4 `Bundle` (`type="collection"`) containing:
1. **`ServiceRequest`**: `status="active"|"completed"|"revoked"`, `intent="order"`, `category=OBSTETRIC_EMERGENCY`, `requester=origin_facility_id`, `performer=lease_facility_id`.
2. **`Task`**:
   - `Task.status` mapping: `CREATED`/`OFFERED` $\rightarrow$ `requested`; `ACKNOWLEDGED` $\rightarrow$ `received`; `ACCEPTED` $\rightarrow$ `accepted`; `COUNTERED`/`ESCALATED_TO_DISPATCHER` $\rightarrow$ `on-hold`; `CANCELLED` $\rightarrow$ `cancelled`; `CLOSED` $\rightarrow$ `completed`.
   - `Task.businessStatus.coding[0].code` = exact `referral.hs_state`.
3. **`Encounter`**: Generated from `TR_UPDATED` events (`status="in-progress"` at `EN_ROUTE`, `"arrived"` at `ARRIVED`, `"finished"` at `HANDED_OVER`).
4. **`Communication`**: Generated for each `OFFER_COUNTERED` and `OFFER_DECLINED` event with structured reason codes.

### 7.3 IEEE 1849 XES Process-Mining Exporter & BSA 2023 s.63 Evidence Bundle
- **IEEE 1849 XES (`GET /v1/exports/xes`):** Exports `<trace>` elements per `referral_id` and `<event>` elements per committed `event.type`. For shared/aggregate exports, timestamps are bucketed to $4\text{-hour}$ intervals and any `(origin_facility, target_facility, need_class)` cell with $< 5$ referrals is suppressed ($k \ge 5$, `F9`).
- **BSA 2023 Section 63 Export Bundle (`GET /v1/exports/bsa63/{referral_id}`):** Produces a ZIP archive containing:
  1. `events.jcs.jsonl` (canonical event log + Merkle proof),
  2. `MANIFEST.sha256` (per-file and bundle SHA-256 digests),
  3. `Part_A_Custodian_Certificate_Template.md` and `Part_B_Expert_Certificate_Template.md` pre-populated with the SHA-256 hash and Ed25519 public key (explicitly labelled `"Template for human signature — not pre-certified"` per `L3`).

---

## 8. Toxiproxy Chaos & Fault-Injection Harness (`T0` Gate)

The `docker-compose.yml` topology routes API-to-PostgreSQL (`pg_proxy:5433 -> pg:5432`) and Phone/Client-to-API (`api_proxy:8001 -> api:8000`) through Shopify **Toxiproxy** to execute the 8-toxic verification suite:

| Toxic # | Toxic Type & Direction | Injected Parameters | Automated Verification Assertion |
|---|---|---|---|
| **1** | `latency` (upstream `pg_proxy`) | `latency=400ms, jitter=100ms` | p95 command latency increases; zero duplicate events (`I4`); zero deadlocks (`I14`) |
| **2** | `latency` (downstream `api_proxy`) | `latency=1500ms` | Client retries replay stored `idempotency` response (`F14` Case 1/2) |
| **3** | `bandwidth` (downstream `api_proxy`) | `rate=5KB/s` | SSE stream reconnects and resumes without missing events via `Last-Event-ID` |
| **4** | `slow_close` (`pg_proxy`) | `delay=2000ms` | Connection pool recovers cleanly; zero leaked `IN_FLIGHT` idempotency rows |
| **5** | `timeout` (`api_proxy`) | `timeout=1000ms` | Client retry with same `Idempotency-Key` yields exact single event |
| **6** | `reset_peer` (`pg_proxy` mid-txn) | `timeout=200ms` | Uncommitted transaction aborts; `idempotency` row rolls back; retry executes cleanly (`F14` Case 5) |
| **7** | `slicer` (`api_proxy`) | `average_size=64, size_variation=32, delay=10ms` | Chunked JSON request bodies reassemble identically; JCS SHA-256 hash matches |
| **8** | `limit_data` / Proxy Disable | `enabled=false` for $10\text{ s}$ then `true` | Outbox relay redelivers after visibility timeout ($30\text{ s}$); Independent Monitor stays green (`0` violations) |