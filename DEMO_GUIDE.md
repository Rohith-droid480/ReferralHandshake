# ReferralHandshake (Protocol RHP-1) — Master Live Demo & Judge Walkthrough Guide
**Team MAHA YODHAS** | **Colossus 3.0 (HealthTech Track) — Bengaluru**

---

## 0. Executive Pitch Opening (30 Seconds)

> *"In India today, up to 70% of emergency obstetric transfers arrive at apex hospitals unannounced, and ambulances bounce between an average of 2.4 facilities before finding an open bed. When a mother arrives in eclamptic convulsions, doctors have no verified record of whether life-saving Magnesium Sulfate ($\text{MgSO}_4$) was administered at the rural clinic. Giving another dose risks fatal respiratory arrest; withholding it risks fatal seizures.*
> 
> *ReferralHandshake replaces chaotic WhatsApp messages and phone calls with **Protocol RHP-1**—a mathematically verified state machine contract enforced by database invariants, cryptographic non-repudiation, and human-in-the-loop telephony. Today, we will prove that at most ONE hospital can ever hold an admission lease, an ambulance is never delayed by phone tag, and every second of medical history is backed by court-admissible Ed25519 Merkle proofs."*

---

## 1. Quick Access & Credentials

| Role / View | Web URL | Mobile Wi-Fi URL | Credentials |
|---|---|---|---|
| **Guarantee Arena (Big Screen)** | `http://localhost:8080/` | `http://<LAN_IP>:8080/` | Public View |
| **Referring Clinician Desk** | `http://localhost:8080/clinician` | `http://<LAN_IP>:8080/clinician` | Role: `CLINICIAN` (PHC Channapatna) |
| **Receiving Hospital Desk** | `http://localhost:8080/receiving-desk` | `http://<LAN_IP>:8080/receiving-desk` | Role: `CMO` (CHC Ramanagara) \| **PIN: 1234** |
| **108 Ambulance PWA** | `http://localhost:8080/ambulance` | `http://<LAN_IP>:8080/ambulance` | Role: `EMT` (108 Ambulance) |
| **108 Dispatcher Console** | `http://localhost:8080/dispatcher` | `http://<LAN_IP>:8080/dispatcher` | Role: `DISPATCHER` (108 Central Hub) |
| **Command Centre & Exporters** | `http://localhost:8080/command-centre` | `http://<LAN_IP>:8080/command-centre` | Role: `ADMIN` / District Health Officer |
| **Judge Admission (QR Gate)** | `http://localhost:8080/judge-join` | `http://<LAN_IP>:8080/judge-join` | Auto-allocated desk |
| **Core API Docs & OpenAPI** | `http://localhost:8000/docs` | `http://<LAN_IP>:8000/docs` | Public API |
| **Independent Runtime Monitor** | `http://localhost:8001/status` | `http://<LAN_IP>:8001/status` | Read-Only Monitor |
| **Standalone Android APK** | `http://localhost:8000/v1/download/apk` | `http://<LAN_IP>:8000/v1/download/apk` | Direct Install |

> **Universal Demo PIN:** `1234` for all clinician, CMO, and EMT authorization actions.

---

## 2. The 30-Second Live Proof Loop (Architecture §17)

Follow this rapid 5-step sequence to demonstrate the entire lifecycle of an emergency referral in under 60 seconds:

```text
[Step 1: PHC Clinician] -> [Step 2: CHC Receiving Desk] -> [Step 3: Arena Concurrency] -> [Step 4: 108 Ambulance] -> [Step 5: Verifier]
```

### Step 1: Create Referral with Drug Safety Lock (`/clinician`)
1. Open **Clinician Card** (`http://localhost:8080/clinician`).
2. Click the **"1. Severe Eclampsia"** preset card at the top.
3. Observe that $\text{MgSO}_4$ status defaults to `UNKNOWN`.
4. Click **"Sign & Dispatch Referral"**.
5. **Immediate Evidence:**
   - Contract is committed into the hash chain (`seq = 1`, `prev_hash = 32x00`).
   - A 9-character Crockford Base32 paper slip is generated (e.g., `XKV68JK68`) for offline continuity.

### Step 2: Receiving Hospital Triage & Acuity Queue (`/receiving-desk`)
1. Switch to **Receiving Desk** (`http://localhost:8080/receiving-desk`).
2. Ensure active role is `CHC Ramanagara` (via top role switcher).
3. **Immediate Clinical Evidence:**
   - A persistent, high-contrast **RED VERIFICATION BANNER** appears:
     `"Pre-referral MgSO4 dose unknown — verify before dosing (Defect D1 Closure)"`.
   - The desk displays an ordered priority queue with strictly **zero countdown timers** (Closure `D18`, Anti-Goodhart protection).
4. Verify required capabilities: Check **"Operating Theatre Active"** and **"Blood Storage Available"**.
5. Enter PIN `1234` and click **"Sign & Commit Acceptance"**.
6. **Result:** The admission lease is granted (`Epoch #1`, status `ACCEPTED`).

### Step 3: Concurrency Race & Single-Lease Proof (`/arena`)
1. Open the **Guarantee Arena** (`http://localhost:8080/arena`).
2. Observe the state machine visualization:
   - `CHC Ramanagara` holds the active lease (`ACCEPTED`).
   - Competing facility `DH Mandya` was automatically updated to `SUPERSEDED` (Invariant `I2`).
   - Open offers count is strictly bounded (`0 <= open_offers <= 2`).

### Step 4: 108 Ambulance Highway Transit & Geofence (`/ambulance`)
1. Open **Ambulance PWA** (`http://localhost:8080/ambulance`).
2. Click **"Start Highway Simulation"** along Karnataka NH-275.
3. Watch the ambulance coordinates move from Channapatna toward Ramanagara.
4. When the ambulance reaches within 200 meters of the hospital, the system emits `ARRIVAL_SUGGESTED`.
5. **Anti-Goodhart Rule (`D2`, `F5`):** The geofence alone does NOT mark the patient arrived. Click the green button **"Confirm Physical Handover (EMT)"** to commit `TR_UPDATE(ARRIVED)`.

### Step 5: Pure-JS `@noble` Browser Verification (`/judge-desk` or `/arena`)
1. Open the **Browser Verifier Drawer** on the Judge Desk or Guarantee Arena.
2. Click **"Verify Merkle Inclusion & Ed25519 Signature"**.
3. **Cryptographic Proof:**
   - The browser imports `@noble/curves/ed25519` and verifies the witness note signature against the pinned cold public key.
   - The browser recomputes the SHA-256 binary Merkle path from the referral leaf up to the signed root.
   - A glowing green badge confirms: **`ZERO HASH DRIFT — 100% MATHEMATICALLY VERIFIED`**.

---

## 3. Deep-Dive Feature Demonstrations

### Feature A: Feature-Phone Outbound Voice IVR with Kannada Prompts
1. On any view, click **"Feature-Phone IVR"** in the top navigation or role switcher.
2. An interactive feature-phone handset simulator appears.
3. Select Language: **Kannada**, **Hindi**, or **English**.
4. Click **"Simulate Outbound Emergency Call"**:
   - The IVR speaks the synthesized prompt in real-time.
   - **Automated Machine Detection (AMD):** If machine silence or voicemail is simulated, the call is rejected.
   - **Mandatory Press-1 Human Gate (`F7`):** The listener must press DTMF key `1` to commit the acknowledgement.

### Feature B: 108 Dispatcher Time-Scrubber Replay (`/dispatcher`)
1. Open **108 Dispatcher Console** (`http://localhost:8080/dispatcher`).
2. Select the escalated eclampsia case (`Referral #3`).
3. Drag the **Deterministic Time-Scrubber** slider from $t=0$ to the right:
   - Watch the state reconstruct event-by-event: `OFFER_CREATED` -> `NOTICE_VOICE` -> `TIMEOUT` -> `ESCALATED_TO_DISPATCHER`.
4. Click **"Direct Placement to Apex College"** to override the network ladder with complete cryptographic attribution.

### Feature C: Legal Exporters & 1-Click DPDP 2023 Crypto-Shredding (`/command-centre`)
1. Open **Command Centre** (`http://localhost:8080/command-centre`).
2. In the **Verifiable Legal Exporters** section:
   - Click **"FHIR R4 Bundle"** to inspect standardized HL7 JSON.
   - Click **"IEEE 1849 XES"** to export XML process mining logs.
   - Click **"BSA 2023 s.63 Bundle"** to preview the court-admissible electronic record certificate.
3. Click **"1-Click DPDP Crypto-Shred"**:
   - The per-referral Data Encryption Key (DEK) is zeroed out (`wrapped_dek = NULL`).
   - Clinical ciphertexts are permanently destroyed under Section 9 of the DPDP Act 2023.
   - The SHA-256 hash chain remains 100% intact and verifiable!

### Feature D: Mobile Phone Wi-Fi Testing (Any Smartphone)
1. Ensure your laptop and phone are on the same Wi-Fi network.
2. Note the LAN IP printed by `run_demo.ps1` (e.g. `http://192.168.1.15:8080`).
3. Open that URL on your phone's Safari or Chrome browser.
4. Tap **"Add to Home Screen"** — the application runs full-screen with offline service worker support!
5. On the laptop's `/arena`, scan the rotating QR code with your phone camera to join the live concurrency race as a competing hospital triage desk!

---

## 4. Troubleshooting & Verification Commands

If you ever need to verify backend health from the terminal:

```powershell
# 1. Healthcheck & Active Alarms (expect status: GREEN, 0 alarms)
curl http://localhost:8000/healthz

# 2. Run Backend Pytest Suite (234 tests in ~6 seconds)
pytest tests/ -q

# 3. Run PWA Vitest Suite (20 tests in ~2 seconds)
npm --prefix pwa test -- --run

# 4. Check Lane B Independent Monitor (ZERO imports from api/)
python -c "import ast; tree = ast.parse(open('monitor/monitor.py').read()); imports = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]; assert not any('api' in i or 'rhp' in i for i in imports); print('Lane B Isolation Verified!')"
```

---
*ReferralHandshake (Protocol RHP-1) — Team MAHA YODHAS — Colossus 3.0*
