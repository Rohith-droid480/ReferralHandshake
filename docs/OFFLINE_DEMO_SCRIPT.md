# 60–90s Offline Emergency Presentation Script & Video Walkthrough

> **Purpose:** Use this exact script if internet connectivity fails or during backup slide presentation. Every step links to a recorded screen state in `docs/screenshots/`.

---

## 00:00–00:15 | The Crisis & MgSO4 Safety Lock (Referring Clinician)
- **Screen:** `ClinicianCard.tsx` (`/clinician`)
- **Visual:** Clinician enters an obstetric emergency (Severe Eclampsia) at PHC Channapatna. Selects `mgso4_status='UNKNOWN'`.
- **Script:** *"In rural India, mothers with eclampsia die on the road because tertiary centers don't know what was given at the primary clinic. In ReferralHandshake, selecting UNKNOWN MgSO4 never blocks ambulance dispatch, but arms a life-critical verification alert for the receiving doctor."*
- **Judge Takeaway:** Solves Defect D1 (Pre-referral drug safety lock).

---

## 00:15–00:35 | Anti-Goodhart Triage & Single-Lease Guarantee (Receiving Desk)
- **Screen:** `ReceivingDesk.tsx` (`/receiving-desk`) & `ArenaBigScreen.tsx` (`/arena`)
- **Visual:** CHC Ramanagara sees the case with a flashing red warning banner: `PRE-REFERRAL MgSO4 DOSE UNKNOWN`. Desk shows strictly zero ticking countdown clocks. Doctor enters PIN 1234 to accept. Competing hospital immediately sees `Already accepted by CHC Ramanagara`.
- **Script:** *"Notice there are zero ticking countdown clocks. That stops hospital staff from running down the timer to dump critical patients. When Ramanagara accepts with their clinician PIN, our partial unique index guarantees that exactly one hospital holds the case. No double bookings. Ever."*
- **Judge Takeaway:** Solves Defect D18 (Anti-Goodhart queue) and Invariant I2 (Single Lease).

---

## 00:35–00:55 | Highway Telemetry & Independent Transport (Ambulance Desk)
- **Screen:** `AmbulancePwa.tsx` (`/ambulance`)
- **Visual:** Ambulance streams live GPS coordinates along NH-275. Crosses 200m geofence: system emits `ARRIVAL_SUGGESTED`, requiring EMT human touch to confirm arrival.
- **Script:** *"Handshake negotiation and ambulance transit run on completely decoupled tracks. Even if negotiation stalls, the ambulance is already moving. Geofences suggest arrival, but care handover strictly requires human confirmation."*
- **Judge Takeaway:** Invariant I3 (Two Independent Tracks) & Closure F5 (Human-in-the-loop arrival).

---

## 00:55–01:15 | Dispatcher Safety Net & Deterministic Time-Scrubber
- **Screen:** `DispatcherConsole.tsx` (`/dispatcher`)
- **Visual:** Dispatcher drags the time-scrubber slider backwards through historical events to audit response times.
- **Script:** *"If all hospitals stay silent, the mathematically bounded notice ladder automatically escalates the case to the 108 Dispatcher. The dispatcher scrubs the exact timeline to see which hospital failed to respond."*
- **Judge Takeaway:** Invariant I13 (Escalation bound $T_{\max} \le B$) and Closure F3.

---

## 01:15–01:30 | Cryptographic Proof & Browser Verifier
- **Screen:** `ArenaBigScreen.tsx` (`/arena`) & `CommandCentre.tsx` (`/command-centre`)
- **Visual:** Pure-JS `@noble` browser verifier confirms Ed25519 Merkle checkpoints. Clicking "Inject Tamper" immediately flags `TAMPER DETECTED` in red.
- **Script:** *"Finally, every state change is hash-chained and signed every 5 seconds. The browser verifier validates the proof with zero trust in the server. If an administrative record is altered in SQL, the browser instantly catches the drift."*
- **Judge Takeaway:** Invariant I5 (Tamper-evident audit) & Section 63 BSA compliance.

