---
trigger: always_on
agent_mode: browser_verification_and_developer_testing
project: ReferralHandshake (RHP-1)
---

# .agents/agent.md — Live Physical Browser Execution & Interactive Feature Testing Protocol

**Core Mandate:** Whenever you (the Google Antigravity Agent) complete or modify any feature, endpoint, background worker, or UI component, **running unit tests in the terminal is NOT enough**. You MUST physically run the live project in a browser using your built-in Browser tool / Playwright runner, interact with the real UI/API, verify the live DOM, SSE stream, and database state, and then write a clear, step-by-step **"How to Test This Feature Yourself"** guide for the developer.

---

## 1. Mandatory 5-Step Physical Browser Execution Protocol (Run on Every Feature Completion)

Before declaring any step complete or emitting your `BUILD REPORT`, execute these 5 steps in order:

### Step 1 — Ensure the Live Stack is Running & Healthy
1. Start or verify the local stack (`docker compose up -d` or local `uvicorn` + `vite` + `poller` + `relay` + `monitor` + `witness` processes).
2. Query `http://localhost:8000/healthz` and verify HTTP `200 OK`, `REAL_DATA=0`, active profile signature valid, and $T_{\max} \le B$ (`I13`).

### Step 2 — Physically Open the Real Browser
Launch your Browser Subagent / browser session and navigate to the live application endpoints corresponding to the feature just built:
- **PWA Desks & Role Switcher:** `http://localhost:5173`
- **Guarantee Arena (Big Screen Monitor):** `http://localhost:5173/arena`
- **Judge Rotating QR Desk & Browser Verifier:** `http://localhost:5173/judge`
- **FastAPI OpenAPI / Swagger UI (for backend-only steps):** `http://localhost:8000/docs`
- **Monitor & Witness Telemetry JSON:** `http://localhost:8000/metrics` and `http://localhost:8000/checkpoints/latest`

### Step 3 — Perform Multi-Role Physical Interactions in the Browser
ReferralHandshake is a multi-party coordination protocol. Test the feature by opening separate tabs/contexts for the interacting roles and physically clicking through the workflow:
- **Tab 1 (Referring PHC Clinician):** Fill out the structured referral card (ISBAR + Dakshata `mgso4_status`) and click **Create & Offer**.
- **Tab 2 (Receiving Facility 1 Duty Desk — e.g., FRU/District Hospital):** Observe the offer arrive live via SSE without refreshing the page. Click **Acknowledge**, confirm required capabilities (`OT`, `BLOOD`, `ANAESTHETIST`, `NICU`), enter the roster PIN, and click **Accept** / **Counter** / **Decline**.
- **Tab 3 (Competing Receiving Facility 2 Desk — for `PARALLEL2` race):** Click **Accept** concurrently with Tab 2 to verify that one desk receives the green ownership lease (`200 OK`) and the other receives a clear `409 LEASE_HELD` reason banner.
- **Tab 4 (Guarantee Arena Big Screen):** Watch the live `I1`–`I16` invariant counters, event hash chain, and `lease_epoch` update in real time.

### Step 4 — Inspect Browser DevTools (Console, Network, SSE & DOM)
While the browser is open, explicitly check and record:
1. **Console Errors:** Assert `0` uncaught JavaScript exceptions or React rendering errors.
2. **Network & Headers:** Verify mutating `POST` requests carry the `Idempotency-Key` header and `expected_version`/`expected_epoch`, and verify SSE (`text/event-stream`) connections include `Last-Event-ID` and receive 15 s heartbeats.
3. **Safety & Anti-Goodhart DOM Checks:**
   - When `mgso4_status = "UNKNOWN"`, assert the high-visibility red warning banner (`"Pre-referral MgSO4 dose unknown — verify before dosing"`) is rendered on the receiving desk (`D1`).
   - Assert the receiving desk displays an ordered priority queue **with zero countdown timer clocks** (`D18`).
   - When an offer is declined or superseded (`GRANT_REVOKED`), assert the clinical payload fields are immediately wiped from that desk's DOM (`F10`, `I10`).

### Step 5 — Capture Proof for the Build Report
Log the exact URLs visited, DOM elements verified, HTTP status codes observed, and screenshots/snapshots captured into Section 2 of your `BUILD REPORT`.

---

## 2. Step-by-Step Browser Verification Playbooks (By Build Step)

Use the playbook matching the current step in the Build Plan:

| Build Step | What the Agent Must Physically Execute in the Browser |
|---|---|
| **P1–P5 (Pre-Event)** | If web UI is not yet built, spin up a local static preview or FastAPI `/docs` swagger page in the browser, execute the schema/profile/seed verification endpoints, and show the rendered JSON/table output. |
| **E0 (PWA Shell & QR Join)** | Open `http://localhost:5173/arena`, verify the rotating QR code refreshes every 15 s (`jti` TTL 20 s), open the QR link in a second browser tab, complete admission, and verify the 20-desk cap indicator increments. |
| **E1 (Core Handshake & SSE Grant Filter)** | Open Clinician Desk + Receiving Desk side-by-side. Create a referral with `mgso4_status=UNKNOWN`. Verify live SSE arrival and red MgSO4 banner on the Receiving Desk. Test `ACK -> RESOURCE_CONFIRM -> ACCEPT` (with PIN), then test `DECLINE` on a second referral and verify `GRANT_REVOKED` immediately clears the clinical card from the declining desk's DOM. |
| **E2 (Poller, Notice Ladder & Monitor)** | Open `http://localhost:5173/arena` under `DEMO_FAST`. Create a referral and **do not click anything** on the receiving desks. Watch the browser UI automatically step through Rung $0 \to A/4 \to 3A/4 \to \text{Facility 2} \to \text{Facility 3} \to \text{ESCALATED\_TO\_DISPATCHER}$ in $\le 25\text{ s}$ while the Independent Monitor stays **GREEN** (`0` violations). |
| **E3 (Hash Chain, Witness & JS Verifier)** | Open `http://localhost:5173/judge`. Click **Verify Live Checkpoints & Chain** (running `@noble/curves/ed25519` and `@noble/hashes/sha256` in the browser) and confirm `VALID`. Then run a `psql` tamper update on `event` seq 2, click **Verify** again in the browser, and confirm the UI highlights `BROKEN referral=<id> seq=2 kind=HASH`. Restore the row before finishing. |
| **E4 (Gate G0: Race & `BROKEN_BUILD`)** | Open `http://localhost:5173/arena` and two Hospital Desk tabs. Trigger the 2-desk concurrent Accept race (Monitor stays GREEN). Then click/toggle `BROKEN_BUILD=1` (routes to `rhp_scratch_broken`), verify the flashing red banner `BROKEN BUILD — SCRATCH DB` appears across the top of the browser, trigger concurrent Accept on a scratch referral, and verify the Monitor turns **RED (`I2 DOUBLE_LEASE_VIOLATION`)** within $\le 2\text{ s}$. Toggle back to normal and verify **GREEN**. |
| **E5 (Gate G1: Counter, GPS, Proxy & Replay)** | In the browser: (1) Send a `COUNTER` offer from Receiving Desk and confirm it on Clinician Desk; (2) Move the PWA Ambulance GPS slider/coordinates inside the 200 m radius and verify `ARRIVAL_SUGGESTED` appears (requiring a human click to confirm `ARRIVED`); (3) Use Dispatcher Console to enter a proxy action (`proxy=true`); (4) Drag the **Time-Scrubber Replay** slider from `seq=1` to `head_seq` and verify every historical state renders accurately. |
| **E6 (Gate G2: Offline Staleness, Voice & Paper Code)** | In the browser: (1) Toggle the Receiving Desk's "Simulate Offline" switch, click Accept (verify UI shows `"Pending, not confirmed"`), wait past `confirm_ttl`, toggle Online, and verify the `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` modal prompts live reconfirmation; (2) Open the Printable Slip view, copy the 9-char Crockford Base32 + mod-37 Paper Code, type it into a blank Receiving Desk to link the record, and test a 1-character typo to see the instant checksum rejection banner. |

---

## 3. Mandatory "How to Test This Feature Yourself" Guide (Output in Every Build Report)

Every time you finish a step, you MUST include this exact user-facing testing guide inside Section 2 of your `BUILD REPORT` so the human developer can test and understand the feature in under 60 seconds:

```text
=== HOW TO TEST THIS FEATURE YOURSELF (60-SECOND DEVELOPER GUIDE) ===

1. START / OPEN THE APP:
   - Command (if not already running): `<exact docker compose or uvicorn/vite command>`
   - Open in your browser:
     * Tab 1 (Role: <e.g., Referring Clinician>): http://localhost:5173/<path>
     * Tab 2 (Role: <e.g., Receiving CMO Desk>): http://localhost:5173/<path>
     * Tab 3 (Guarantee Arena Monitor): http://localhost:5173/arena
   - Test Credentials / PIN to use: Facility `<code/name>`, Role `<slot>`, PIN `<4-digit PIN>`

2. CLICK-BY-CLICK WALKTHROUGH (HAPPY PATH):
   - Step A: In Tab 1, click `<button/field>` and enter `<sample synthetic input>`.
   - Step B: Watch Tab 2 — within `<N>` ms, you will see `<exact visual UI change via SSE>`.
   - Step C: In Tab 2, check `<resource checkboxes>`, enter PIN `<PIN>`, and click `<button>`.

3. WHAT YOU SHOULD SEE (VISUAL & PROTOCOL PROOF):
   - In Tab 2: `<exact badge/state, e.g., LEASE GRANTED — Epoch 1, green border>`
   - In Tab 3 (Guarantee Arena): `<Monitor status = GREEN, head_seq increments to N, 0 invariant violations>`
   - In Browser DevTools Network Tab: `<POST /v1/... returns 200 OK with Idempotency-Key header>`

4. TRY TO BREAK IT (RED-TEAM SPOT CHECK YOU CAN DO RIGHT NOW):
   - Try this attack: `<e.g., Click Accept in two tabs at the same time / Enter wrong PIN 3 times / Mutate 1 character of the Paper Code>`
   - Why it fails safely: `<explain the exact HTTP 409/412/403/422 code and which invariant I1-I16 or trigger blocked it>`

5. ONE-LINE DATABASE & LOG VERIFICATION COMMAND:
   - Run this in your terminal to inspect the committed database state:
     `psql "$DATABASE_URL" -c "<exact SELECT query on referral, offer, event, or deadline>"`
```