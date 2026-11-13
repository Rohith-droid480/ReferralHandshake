---
name: frontend-development
description: Build ReferralHandshake (RHP-1) React PWA desks, pure-JS Ed25519/SHA-256 Merkle browser verifier, SSE client with Last-Event-ID and GRANT_REVOKED DOM wipe, Anti-Goodhart receiving queue, printable Crockford paper slip, and Android Kotlin foreground location client.
owner_lane: Lane B (Clients, Reach UI & Guarantee Arena)
tier_scope: T0, T1, T2, T3
spec_anchors:
  - ReferralHandshake_FINAL_LOCKED_Architecture.md (§0, §4, §8, §9, §11, §13, §15, §16, §17)
  - ReferralHandshake_v8_LOCKED_Solution.md (§6, §7, §8, §11, §14)
  - ReferralHandshake_LOCKED_Problem_Statement_v7.md (§6, §8, §10, §11)
invariants_enforced:
  - I3
  - I5
  - I10
  - I15
codeowners_restricted:
  - spec/
  - db/schema.sql
  - monitor/
---

# RHP-1 Frontend & Mobile Development Skill (`frontend-development`)

## 1. Mission & Client Inventory
You build the user-facing and judge-facing clients for **ReferralHandshake (Protocol RHP-1)**. Under the **Coherence Rule**, every client view is strictly an adapter that produces commands (`POST /v1/...` with `Idempotency-Key`) or renders read-only projections of the event stream (`SSE` / `/v1/...`). Never embed authoritative state transitions in client code.

### Locked Client Surfaces by Tier
| Surface | Tier | Target Role | Core Responsibilities |
|---|---|---|---|
| **Receiving Hospital Desk (PWA)** | T0 | `NURSE`, `CMO`, `CONSULTANT` | Priority queue (no countdown clocks), red `mgso4_status=UNKNOWN` banner, one-by-one resource confirmation, `ACCEPT` / `COUNTER` / `DECLINE` with PIN, live reconfirmation modal on `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`. |
| **Referring Clinician Card & Printable Slip (PWA)** | T0 | `CLINICIAN` | Structured ISBAR + Dakshata entry (`mgso4_status`: `GIVEN \| NONE_GIVEN \| UNKNOWN`), one-tap approved catchment chain, printable slip with 9-char Crockford Base32 + mod-37 paper code & QR (card = slip, zero double-entry). |
| **Judge QR Web Desk & Browser Verifier (PWA)** | T0 | `JUDGE_DESK` | Rotating QR join + Turnstile, competing hospital race button (`PARALLEL2`), pure-JS Ed25519 checkpoint + SHA-256 Merkle inclusion proof + event hash chain verifier. |
| **Guarantee Arena Big Screen (PWA)** | T0 | Public / Judges | Live I1–I16 invariant counters from independent monitor, measured p50/p95 latency, deadline lateness, `BROKEN BUILD — SCRATCH DB` flashing red banner when `/mode` reports `BROKEN_BUILD=1`. |
| **Ambulance Client (PWA Fallback / Kotlin Native)** | T1 / T3 | `EMT` | Parallel transport track (`DISPATCHED -> EN_ROUTE -> ARRIVED -> HANDED_OVER`), 200m geofence `ARRIVAL_SUGGESTED` prompt (human confirms `ARRIVED`), redirect advisory banner, offline outbox queue showing `"pending, not confirmed"`. |
| **Dispatcher Console (PWA)** | T1 | `DISPATCHER` | Handles `ESCALATED_TO_DISPATCHER`, phone-assisted proxy entry (`proxy=true`, `proxy_for`, mandatory reason enum), replay time-scrubber. |
| **AI Intake Accelerator UI (PWA)** | T3 | `CLINICIAN` | Cognitive Forcing Function (think-first anchor commit before unblocking `423 ANCHOR_REQUIRED` draft), critical field re-entry, zero confidence scores or explanations. |

---

## 2. Pure-JS Cryptography & Browser Verifier (F8 / D1 / N7 / §11)

> **CRITICAL PLATFORM CONSTRAINT (`[V]`):** iOS Safari WebCrypto does not reliably support Ed25519 across target versions, and `window.crypto.subtle` is completely disabled by browsers over plain LAN HTTP (`http://192.168.x.x`) during the venue internet-down LAN fallback (`N7`). Therefore, you **must** bundle pure-JavaScript `@noble/curves/ed25519` and `@noble/hashes/sha256` and **never** call `crypto.subtle` for checkpoint or hash-chain verification.

### 2.1 Pure-JS Verifier Implementation (`verifier.ts`)
```typescript
import { ed25519 } from "@noble/curves/ed25519";
import { sha256 } from "@noble/hashes/sha256";
import { bytesToHex, hexToBytes, utf8ToBytes } from "@noble/hashes/utils";

export function jcsCanonical(obj: Record<string, unknown>): Uint8Array {
  const validate = (v: unknown): void => {
    if (typeof v === "number" && !Number.isInteger(v)) {
      throw new Error("FLOATS_PROHIBITED_IN_JCS");
    }
    if (v && typeof v === "object") {
      if (Array.isArray(v)) v.forEach(validate);
      else {
        for (const [k, val] of Object.entries(v)) {
          if (!/^[\x00-\x7F]+$/.test(k)) throw new Error("NON_ASCII_KEY");
          validate(val);
        }
      }
    }
  };
  validate(obj);
  const sortObj = (val: unknown): unknown => {
    if (Array.isArray(val)) return val.map(sortObj);
    if (val !== null && typeof val === "object") {
      return Object.keys(val as Record<string, unknown>)
        .sort()
        .reduce((acc: Record<string, unknown>, key) => {
          acc[key] = sortObj((val as Record<string, unknown>)[key]);
          return acc;
        }, {});
    }
    return val;
  };
  return utf8ToBytes(JSON.stringify(sortObj(obj)));
}

export function verifyReferralChainAndProof(
  events: Array<{
    referral_id: string;
    seq: number;
    event_id: string;
    type: string;
    epoch: number;
    actor_roster_id: string | null;
    facility_id: string | null;
    channel: string;
    proxy: boolean;
    detail: Record<string, unknown>;
    secret_hash: string | null;
    client_ts_ms: number | null;
    server_ts_us: number;
    prev_hash_hex: string;
    hash_hex: string;
  }>,
  checkpoint: {
    note_body: string; // "rhp1/<deployment>\n<tree_size>\n<root_hex>\n"
    signature_hex: string;
    root_hex: string;
    head_seq: number;
    kind: "REGULAR" | "RESTORE";
    cold_signature_hex?: string;
  },
  proofPath: Array<{ side: "L" | "R"; hash_hex: string }>,
  pinnedSignerPubKeyHex: string,
  pinnedColdPubKeyHex: string
): { ok: boolean; status: string } {
  // 1. Verify Ed25519 checkpoint signature with pinned key
  const sigOk = ed25519.verify(
    hexToBytes(checkpoint.signature_hex),
    utf8ToBytes(checkpoint.note_body),
    hexToBytes(pinnedSignerPubKeyHex)
  );
  if (!sigOk) return { ok: false, status: "CHECKPOINT_SIG" };

  // 2. Recompute per-referral SHA-256 chain from genesis (32 zero bytes)
  let expectedPrev = new Uint8Array(32);
  let expectedSeq = 1;
  for (const ev of events) {
    if (ev.seq !== expectedSeq) {
      return { ok: false, status: `SEQ_GAP referral=${ev.referral_id} expected=${expectedSeq} got=${ev.seq}` };
    }
    if (bytesToHex(expectedPrev) !== ev.prev_hash_hex.toLowerCase()) {
      return {
        ok: false,
        status: `BROKEN referral=${ev.referral_id} seq=${ev.seq} kind=PREV expected=${bytesToHex(expectedPrev)} got=${ev.prev_hash_hex}`,
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
      secret_hash: ev.secret_hash,
      seq: ev.seq,
      server_ts_us: ev.server_ts_us,
      type: ev.type,
    };
    const payload = new Uint8Array(expectedPrev.length + jcsCanonical(core).length);
    payload.set(expectedPrev, 0);
    payload.set(jcsCanonical(core), expectedPrev.length);
    const computedHash = bytesToHex(sha256(payload));
    if (computedHash !== ev.hash_hex.toLowerCase()) {
      return {
        ok: false,
        status: `BROKEN referral=${ev.referral_id} seq=${ev.seq} kind=HASH expected=${computedHash} got=${ev.hash_hex}`,
      };
    }
    expectedPrev = hexToBytes(computedHash);
    expectedSeq += 1;
  }

  // 3. Check for illegal truncation below checkpointed head_seq
  const liveHeadSeq = events.length > 0 ? events[events.length - 1].seq : 0;
  if (liveHeadSeq < checkpoint.head_seq && checkpoint.kind !== "RESTORE") {
    return { ok: false, status: `TRUNCATED at seq=${liveHeadSeq}` };
  }

  // 4. Verify Merkle inclusion proof path up to signed root_hash
  const lastEv = events[events.length - 1];
  const uuidBytes = hexToBytes(lastEv.referral_id.replace(/-/g, ""));
  const seqBuf = new Uint8Array(8);
  new DataView(seqBuf.buffer).setBigUint64(0, BigInt(lastEv.seq), false);
  const headHashBytes = hexToBytes(lastEv.hash_hex);

  const leafInput = new Uint8Array(1 + 16 + 8 + 32);
  leafInput[0] = 0x00;
  leafInput.set(uuidBytes, 1);
  leafInput.set(seqBuf, 17);
  leafInput.set(headHashBytes, 25);
  let curHash = sha256(leafInput);

  for (const step of proofPath) {
    const sibling = hexToBytes(step.hash_hex);
    const nodeInput = new Uint8Array(1 + 32 + 32);
    nodeInput[0] = 0x01;
    if (step.side === "L") {
      nodeInput.set(sibling, 1);
      nodeInput.set(curHash, 33);
    } else {
      nodeInput.set(curHash, 1);
      nodeInput.set(sibling, 33);
    }
    curHash = sha256(nodeInput);
  }

  if (bytesToHex(curHash) !== checkpoint.root_hex.toLowerCase()) {
    return { ok: false, status: "ROOT_MISMATCH" };
  }

  return { ok: true, status: "VERIFIED" };
}
```

---

## 3. SSE Stream Lifecycle & `GRANT_REVOKED` DOM Wipe (F10 / I10)

1. **Authentication & Reconnection:** Connect to `/v1/stream` using `EventSource(..., { withCredentials: true })` (authenticated via `HttpOnly; Secure; SameSite=Strict` session cookie). Track the last seen event ID so reconnects automatically pass `Last-Event-ID`.
2. **15-Second Heartbeat Monitor:** If no SSE event or `:heartbeat` comment arrives within 18 seconds (`15s` heartbeat + `3s` grace), mark the connection indicator as `"Stale — Reconnecting"` and display `"Last confirmed Ns ago"` on all cards.
3. **Immediate Clinical Wipe on `GRANT_REVOKED` (I10):** When the SSE stream emits an event of type `GRANT_REVOKED` for `referral_id`:
   * Immediately purge `clinical_payload` from React state, memory caches, and `IndexedDB` for that `referral_id`.
   * Replace the card view with a non-clinical summary (`referral_id`, `status: SUPERSEDED | DECLINED | WITHDRAWN`).

---

## 4. Clinical Safety & Anti-Goodhart UI Rules (§8, §11, §15, §16)

1. **No Countdown Clocks on Receiving Desks (`[V]`, R09):** Receiving hospital desks (`NURSE`, `CMO`, `CONSULTANT`) must display offers as a priority-ordered list without ticking countdown timers (countdowns distort clinical triage). Only the Guarantee Arena big screen may show timer metrics for judges.
2. **Red $\text{MgSO}_4$ Banner (D1 / K1):** Whenever `referral.mgso4_status === 'UNKNOWN'`, render a persistent high-contrast red banner at the top of the receiving desk card:
   `"PRE-REFERRAL MgSO4 DOSE UNKNOWN — VERIFY WITH PATIENT/ESCORT BEFORE DOSING"`.
3. **Live Resource Reconfirmation Modal (F12 / I15):**
   * Offline `ACCEPT` clicks are queued in the local outbox and badged `"Pending — Not Confirmed"`.
   * If flushing an `ACCEPT` returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`, open a modal requiring the rostered user to re-toggle each required capability (`OT`, `BLOOD`, `ANAESTHETIST`, `PAEDIATRICIAN`, `NICU`), fire live `POST /v1/offers/{id}/confirm-resource` calls, and then submit a fresh `ACCEPT` with a new `Idempotency-Key`.
4. **Cognitive Forcing Function for AI Drafts (T3 / §16):**
   * Before calling `GET /v1/referrals/{id}/ai-draft`, the clinician UI must require manual selection and commitment of `need_class` and `mgso4_status` (otherwise the server returns `423 ANCHOR_REQUIRED`).
   * Never render AI confidence percentages, colour-coded confidence bars, or LLM rationales (`[V]`, explanations increased commission errors from 10% to 21%).
5. **Android Ambulance Foreground Service (T3) & PWA GPS Fallback (T1):**
   * Native Android app uses `FOREGROUND_SERVICE_TYPE_LOCATION` with `FusedLocationProviderClient`, Room outbox (`WorkManager`), and zero-payload FCM wake pushes (followed by authenticated HTTPS fetch).
   * PWA fallback uses `navigator.geolocation.watchPosition` plus a manual `"Update Location"` button and a `"Confirm Arrival"` button when the 200m geofence triggers `ARRIVAL_SUGGESTED`.

---

## 5. Verification Gates (Must Pass on Every Frontend Task)

1. **Gate FE-1 (`T-D1` / `T-F8` Verifier Test):** Feed a valid event chain + Merkle proof and a 1-byte mutated event chain into `verifyReferralChainAndProof()`. Verify the mutated chain returns `BROKEN referral=... seq=... kind=HASH` with zero calls to `window.crypto.subtle`.
2. **Gate FE-2 (`T-F10 sse_revoke`):** Simulate an active receiving desk viewing a referral card, emit a `GRANT_REVOKED` SSE frame, and assert that zero clinical fields remain in the DOM (`document.body.innerText`) within 100ms.
3. **Gate FE-3 (`T-F12 offline_stale`):** Queue an `ACCEPT` while offline, advance server time past `confirm_ttl`, reconnect, and verify the UI handles `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` by displaying the live reconfirmation prompt.
4. **Gate FE-4 (`T-F20 broken_isolation` Banner):** When `/mode` returns `{"broken_build": true, "db": "rhp_scratch_broken"}`, verify the Guarantee Arena and all desks display the flashing red banner `BROKEN BUILD — SCRATCH DB`.

---

## 6. Explicit DO / DO NOT Guardrails

### DO
* **DO** generate a fresh UUIDv7 `event_id` and `Idempotency-Key` per user intent and reuse that exact `Idempotency-Key` across network retries of the same intent.
* **DO** label every pre-computed or synthetic demo metric accurately and display only live-measured latency/recovery numbers on the Guarantee Arena screen.
* **DO** disable PIN entry if the client detects plain HTTP (`window.location.protocol === 'http:'` in LAN fallback mode for judge read-only desks).

### DO NOT
* **DO NOT** use WebSockets, Firebase Realtime Database, or third-party push payloads containing clinical text.
* **DO NOT** display countdown clocks on the receiving clinician/nurse desk UI.
* **DO NOT** auto-reroute the ambulance on the map when a lease changes; always render a `"Redirect Advisory"` banner requiring crew/dispatcher confirmation.