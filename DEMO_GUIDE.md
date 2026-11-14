# ReferralHandshake (Protocol RHP-1) — Presenter Demo Guide & Pitch Playbook

> **Written for:** Presenters pitching to judges and healthcare evaluators at Colossus 3.0.  
> **Rule:** Plain language first. No technical jargon without a one-line plain English explanation.

---

## 1. Thirty-Second Elevator Pitch & One-Line Impact Statement

### The 30-Second Elevator Pitch
*"In India today, when a pregnant woman in a rural clinic suffers severe eclampsia, the referral is an uncoordinated phone call or an unread WhatsApp message. Ambluances wander between hospitals—a phenomenon documented as the 'Referral Ping-Pong'—while receiving doctors have no verified record of what medications were given. ReferralHandshake transforms that broken communication into a verifiable state contract. We guarantee that exactly one hospital holds the admission lease, that ambulances are never blocked by negotiation delays, that life-saving drug dosages are verified before arrival, and that the entire handover is provable in any browser without trusting our server."*

### The One-Line Impact Statement
**"ReferralHandshake eliminates unannounced emergency arrivals and the dangerous referral ping-pong by turning inter-facility hospital handovers into mathematically bounded, verifiable contracts."**

---

## 2. How Each Feature Works (Plain Language Breakdown)

### 1. The Pre-Referral $\text{MgSO}_4$ Drug Safety Lock
- **What it does:** Forces the referring clinic to answer whether Magnesium Sulfate (the eclampsia anticonvulsant) was given, none was given, or status is unknown.
- **Why it matters:** Doctors at receiving hospitals frequently have no idea if a loading dose was given; overdosing causes respiratory arrest, while underdosing causes fatal seizures. Selecting `UNKNOWN` never blocks the ambulance, but triggers an unmistakable red warning banner on the hospital's screen.
- **How it is implemented:** Stored as an enum `mgso4_status_t` (`GIVEN`, `NONE_GIVEN`, `UNKNOWN`) checked during referral creation.
- **Where the code is:** `pwa/src/views/ClinicianCard.tsx`, `pwa/src/views/ReceivingDesk.tsx`, and `api/rhp/schemas.py`.

### 2. The Single-Leaseholder Guarantee
- **What it does:** Ensures that across competing hospitals, exactly **one** facility holds the confirmed admission lease on a patient.
- **Why it matters:** Eliminates double-bookings, chaotic admissions, and competing claim rejections at the hospital gate.
- **How it is implemented:** Enforced at the database engine level via a PostgreSQL partial unique index (`one_lease ON offer(referral_id) WHERE status = 'ACCEPTED'`), validated under 200 concurrent threads.
- **Where the code is:** `db/01_schema.sql`, `tests/test_race200.py`, and `pwa/src/views/ArenaBigScreen.tsx`.

### 3. Decoupled Transport & Care Tracks
- **What it does:** Runs the clinical handshake negotiation (`hs_state`) and the ambulance transit (`tr_state`) on parallel, independent tracks.
- **Why it matters:** An ambulance driver must never be told to sit and wait outside a rural clinic while hospital doctors negotiate bed availability.
- **How it is implemented:** Separate state machines in PostgreSQL. Transport commands (`TR_UPDATE`) never read or block on clinical handshake states.
- **Where the code is:** `spec/transitions.yaml` (Invariant `I3`) and `pwa/src/views/AmbulancePwa.tsx`.

### 4. Anti-Goodhart Receiving Desk (No Countdown Clocks)
- **What it does:** Displays incoming emergency cases sorted strictly by clinical urgency, with zero ticking countdown timers.
- **Why it matters:** When hospital staff see a clock ticking down to zero, they game the system by waiting out the final seconds to let the case time out to someone else.
- **How it is implemented:** Acuity priority queue rendered without countdown timers, reporting arrival latency separately from decision latency.
- **Where the code is:** `pwa/src/views/ReceivingDesk.tsx` and Architecture §4.8.

### 5. Multi-Channel Notice Ladder & Silence Escalation
- **What it does:** If a hospital does not respond, the system automatically rings an outbound voice IVR call, pages the 108 Dispatcher, and steps to the next hospital on the approved catchment chain.
- **Why it matters:** Silence is never indefinite. A rural patient is never stranded because a doctor stepped away from their desk.
- **How it is implemented:** A 2-phase stateless deadline poller (`api/rhp/poller.py`) and transactional outbox relay (`api/rhp/relay.py`) claiming due timers via `SKIP LOCKED`.
- **Where the code is:** `api/rhp/poller.py`, `api/rhp/relay.py`, and `api/rhp/reach/exotel_ivr.py`.

### 6. Offline Paper Handover Slip (Crockford Base32 + Mod 37)
- **What it does:** Generates a 9-character alphanumeric code (e.g., `XKV68JK68`) printed directly on the referral card.
- **Why it matters:** Works even when rural cell towers completely fail. The receiving hospital types in the 9 characters to pull up or reconstruct the case.
- **How it is implemented:** 40-bit integer encoded in Crockford Base32 with a modulo-37 check character that instantly catches typos.
- **Where the code is:** `api/rhp/reach/paper_code.py` and `tests/test_paper_code.py`.

### 7. Pure-JS Browser Verifier & Tamper Detection
- **What it does:** Proves directly in the judge's web browser that no medical event or database record was altered or forged.
- **Why it matters:** Proves contract integrity without requiring judges or patients to trust our central server or database administrator.
- **How it is implemented:** Every state change appends an RFC 8785 canonical JSON hash. A standalone witness signs Merkle roots with Ed25519 every 5 seconds. The browser verifies the cryptographic signature using pure JavaScript (`@noble/curves`).
- **Where the code is:** `witness/signer.py`, `pwa/src/crypto/verifier.ts`, and `pwa/src/views/ArenaBigScreen.tsx`.

---

## 3. The 3-Minute Live Pitch & Demo Script

| Elapsed | Action / Screen | What to Say (Verbatim) | What the Judge Sees |
|---|---|---|---|
| **00:00–00:40** | Open at `/clinician` | *"Judges, in rural India, emergency obstetric referrals are a black box. Over 90% arrive unannounced. A mother with eclampsia is put in an ambulance, but receiving doctors don't know if life-saving Magnesium Sulfate was administered at the clinic. Let's fix that."* | Clinician Card with rural Karnataka NH-275 catchment preset. |
| **00:40–01:10** | Click **S1: MgSO4 UNKNOWN** | *"I'm Dr. Asha at PHC Channapatna. Our patient has severe pre-eclampsia. We don't have records of prior dosing, so we select UNKNOWN MgSO4. Notice: this NEVER blocks referral or ambulance dispatch. It creates the referral and prints an offline 9-character Crockford paper slip."* | Referral created instantly (`200 OK`). Slip prints with paper code. |
| **01:10–01:45** | Switch to `/receiving-desk` | *"Now we are at CHC Ramanagara. Look at the receiving desk: first, there are NO countdown clocks—stopping staff from running down the timer. Second, an unmistakable RED warning flashes: 'PRE-REFERRAL MgSO4 DOSE UNKNOWN'. The doctor knows immediately to verify before dosing. The doctor enters PIN 1234 and accepts."* | Flashing red warning banner. Capability checklist. Clean PIN modal and lease granted. |
| **01:45–02:20** | Open `/arena` | *"Now look at the Guarantee Arena. What happens if two hospitals try to accept simultaneously? Our database enforces Invariant I2 via a partial unique index. Exactly one hospital holds the admission lease. The competing hospital immediately receives 409 Conflict. No double-bookings ever."* | Arena showing active leaseholder and zero invariant violations. |
| **02:20–03:00** | Click **S6: Tamper Test** | *"Finally, how do you know the database wasn't secretly manipulated? Every state mutation is hash-chained and signed every 5 seconds. Watch: I'll inject a simulated database tampering. Instantly, our pure-JS browser verifier flags RED: TAMPER DETECTED. Zero trust in the server. Complete tamper-evident auditability."* | Browser verifier flashes RED: TAMPER DETECTED. Demonstrates cold-key repair. |

---

## 4. The 5-Minute Deep-Dive Presentation Script

*Extends the 3-minute script with two crucial real-world operational workflows:*

- **Minute 03:00–04:00 | Ambulance Highway Telemetry & Human Arrival Gate (`/ambulance`):**
  - *"Let's look at the ambulance crew on Karnataka NH-275. Notice that transit and handshake negotiation run on independent tracks. The ambulance streams GPS telemetry. When the ambulance crosses the 200-meter hospital geofence, the system emits an arrival suggestion. But notice: it NEVER auto-admits the patient. A human EMT or triage nurse must tap 'Confirm Arrival'. Technology assists; human clinicians remain accountable."*
- **Minute 04:00–05:00 | 108 Central Dispatcher Time-Scrubber & Legal Exporters (`/dispatcher`, `/command-centre`):**
  - *"If hospitals fail to respond, the notice ladder escalates the case to the 108 Dispatcher. The dispatcher can scrub backwards along our event timeline to see exactly which facility timed out. From our Command Centre, administrators can export HL7 FHIR R4 bundles, IEEE 1849 process mining logs, or 1-click DPDP 2023 cryptographic shredding that permanently destroys patient clinical data while preserving the tamper-evident hash chain."*

---

## 5. Live Demo Failure Fallback Plan

| Failure Scenario | Immediate Action | Backup Path |
|---|---|---|
| **Backend or Uvicorn down** | Run `.\run_demo.ps1` (or `./run_demo.sh`) in terminal. Restarts stack and re-seeds data in 3 seconds. | Open static pre-built production bundle at `http://localhost:8000/app/`. |
| **Wi-Fi or Network Drops** | Switch to localhost: `http://localhost:8080/`. The platform runs 100% offline-first. | Show the offline paper slip handover (Scenario S4) to demonstrate offline resilience! |
| **Browser Verifier reports stale** | Click **"Reset State"** on the Demo Scenarios Bar or run `python scripts/seed_demo_scenarios.py`. | Refer to the pre-rendered offline script at `docs/OFFLINE_DEMO_SCRIPT.md`. |
| **Screen sharing freezes** | Open `docs/screenshots/` and present the high-resolution step-by-step screenshots. | Follow the 60–90s script in `docs/OFFLINE_DEMO_SCRIPT.md`. |

