# ReferralHandshake (Protocol RHP-1) — Live Stage Demo & Guarantee Arena Runbook

**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru)
**System:** Referral Handshake Protocol (`RHP-1`) + Reference Platform + Independent Runtime Monitor
**Data Mode:** `REAL_DATA=0` (100% synthetic data; demo profiles refuse boot if `REAL_DATA=1`)
**Authority Precedence:** `Problem_Statement_v7.md` > `[V]` Research > `v8_LOCKED_Solution.md` > `FINAL_LOCKED_Architecture.md`

---

## 0. Executive Summary of Demo Strategy

Judges form their core impression within the first 30 to 60 seconds (`v8 §14`). Therefore, **ReferralHandshake does not open with a slide deck**. It opens with a live, adversarial demonstration of **trust under attack** inside the **Guarantee Arena**, followed by the end-to-end clinical and degraded-network journey.

This document contains two synchronized runbooks:
1. **Runbook A — The 5-Minute Colossus 3.0 Official Stage Script (with the Mandatory 30-Second Live Proof Loop, `F16`):** Designed for the strict 5-minute hackathon pitch clock (`FINAL_LOCKED_Architecture.md §0, §17`).
2. **Runbook B — The 7-Minute Guarantee Arena Deep-Dive Script (8 Scenes, `v8 §14`):** Designed for technical judging booths, extended Q&A walkthroughs, and full-system verification across all tiers (`T0` through `T3`).

Every metric shown on stage (event latency $p_{50}/p_{95}$, recovery time, invariant counters, deadline lateness) is **measured live from the running PostgreSQL 16 log and runtime monitor**—never pre-claimed or hardcoded (`v8 Defect D5`, `FINAL §2`).

---

## 1. Pre-Flight Checklist & H22 Code Freeze Protocol

### 1.1 Hard Code Freeze Rule (`H22` Gate)
- **T-Minus 4 Hours (or Hour 22 of the 24-hour build):** Absolute code freeze (`v8 §13.2`, `FINAL §17, §18 D5`).
- `CODEOWNERS` locks `spec/`, `db/schema.sql`, `transitions.yaml`, and `monitor/`.
- Only configuration toggles (`.env` flags `T1_TRANSPORT`, `T2_REACH`, `T3_EXTRAS`, `PROFILE`) and rehearsed fallback switches are permitted after freeze.

### 1.2 Hardware, Network & Dual-Uplink Topology
| Component | Primary Configuration | Fail-Closed Fallback | Verification Command / Check |
|---|---|---|---|
| **Presentation Laptop (Primary)** | Docker Compose stack (`pg`, `api`, `poller`, `relay`, `monitor`, `witness`, `toxiproxy`, `pwa`, `tunnel`) | Pre-warmed Identical Backup Laptop on local hotspot | `docker compose ps` (all 9 services healthy) |
| **Network Uplink** | Dedicated 5G Mobile Hotspot (Primary) + Venue Wi-Fi (Secondary) | **LAN Mode** on local hotspot (`192.168.x.x`), fails closed: cap 20 desks, synthetic only, PIN entry disabled over plain HTTP (`FINAL §9`) | `curl -s http://localhost:8000/healthz \| jq .` |
| **Judge QR Admission** | Rotating single-use QR (`jti` valid $20\text{ s}$, rotates every $15\text{ s}$) + Cloudflare Turnstile challenge | Local LAN QR (`JUDGE_DESK` read-only/synthetic role, cap 20) | Scan QR on iPhone Safari (tests pure-JS `@noble` bundle) |
| **Telephony / Voice (`T2`)** | Exotel trial account with $\le 10$ pre-verified, whitelisted team numbers (`[V]`) | Pre-recorded real-call capture `clip_voice.mp4` + live PWA receiving desk | Place 1 test call; verify webhook HTTP 200 in $\le 2\text{ s}$ |
| **Feature Phone** | Charged basic keypad phone on loud speaker (whitelisted in Exotel) | Secondary whitelisted dumbphone on standby | Battery $> 80\%$, ringer volume max |
| **Ambulance GPS Device (`T1`/`T3`)** | Teammate Android phone running foreground location service / PWA GPS | Manual `TR_UPDATE` + replay scrubber on Dispatcher Console | `heartbeat` table shows `DEVICE` seen $< 5\text{ s}$ ago |

### 1.3 Database, Scratch Isolation & Crypto Pre-Flight (`T-Minus 15 Minutes`)
Run the pre-flight verification script in Terminal 1 before walking to the stage:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[1/7] Verifying PostgreSQL 16 synchronous_commit and lock_waits..."
psql "$DATABASE_URL" -Atc "SHOW synchronous_commit;" | grep -qx "on"
psql "$DATABASE_URL" -Atc "SHOW log_lock_waits;" | grep -qx "on"

echo "[2/7] Verifying active profile signature and T_max <= B (I13)..."
python3 -m rhp.profile_validator --profile DEMO_FAST --real-data 0
python3 -m rhp.profile_validator --profile DEMO_VOICE --real-data 0

echo "[3/7] Verifying Scratch DB isolation for BROKEN_BUILD (F20 / T-F20)..."
./scripts/make_scratch.sh
python3 -m rhp.broken_guard_check --verify-isolation

echo "[4/7] Verifying Independent Monitor (Person B, role rhp_monitor, UID 1001)..."
curl -sf http://localhost:8001/metrics | jq -e '.violations_total == 0'

echo "[5/7] Verifying Witness Signer (OS user rhp-sign, UID 1002, role rhp_witness)..."
curl -sf http://localhost:8002/checkpoints/latest | jq -e '.tree_size >= 0 and (.signature | length > 0)'

echo "[6/7] Verifying Heartbeats (POLLER, RELAY, MONITOR, WITNESS <= 5s)..."
psql "$DATABASE_URL" -Atc "
  SELECT count(*) FROM heartbeat
  WHERE subject_kind IN ('POLLER','RELAY','MONITOR','WITNESS')
    AND last_seen > clock_timestamp() - interval '5 seconds';
" | grep -qx "4"

echo "[7/7] Arming MP4 Fallback Clips (clip_A.mp4 .. clip_G.mp4)..."
ls -la ./demo_fallbacks/clip_{A,B,C,D,E,F,G}.mp4
echo "PRE-FLIGHT GREEN. READY FOR STAGE."
```

---

## 2. Stage Layout, Screen Split & Team Choreography

### 2.1 Big Screen 3-Pane Layout ("The Guarantee Arena")
```
+---------------------------------------------------------------------------------------------------+
| TOP BANNER: MODE = PRODUCTION PRIMARY (REAL_DATA=0 | PROFILE=DEMO_FAST | T_max=24s <= B=25s)      |
| (Flashes RED: "BROKEN BUILD — SCRATCH DB (rhp_scratch_broken)" when BROKEN_BUILD=1 is active)     |
+-----------------------------------+-----------------------------------+---------------------------+
| PANE 1 (LEFT 35%):                | PANE 2 (CENTER 40%):              | PANE 3 (RIGHT 25%):       |
| INDEPENDENT RUNTIME MONITOR       | CLINICAL & DISPATCH WORKSPACES    | ADVERSARIAL CONSOLE       |
| (Person B Code | Role: rhp_monitor)|                                   | (Person A Terminal)       |
|                                   | - Top: Rotating Judge QR +        |                           |
| - Invariants I1..I16 Green Badges |   Competing Hospital Desks (D1,D2)| - Live psql shell         |
| - Violations Counter: 0           | - Mid: Clinician ISBAR+Dakshata   | - Toxiproxy CLI controls  |
| - Differential Check:             |   Card (mgso4_status banner)      | - BROKEN_BUILD toggle     |
|   fold(event) == referral row     | - Bot: Parallel Transport Track   | - Pure-JS Merkle Verifier |
| - Live Measured p50 / p95 (ms)    |   Map + Dispatcher Proxy Console  |   Output Log              |
| - C2SP Checkpoint Root (every 5s) |                                   |                           |
+-----------------------------------+-----------------------------------+---------------------------+
```

### 2.2 Role Division on Stage
- **Person A (`T1` — Presenter & Adversary):** Holds the microphone, delivers the narrative, states evidence with exact study attributions, and executes live terminal attacks in Pane 3 (`BROKEN_BUILD=1`, `psql` superuser tamper, Toxiproxy fault injection, container kill).
- **Person B (`T2` — Operator & Clinical Driver):** Drives Pane 2 (creates the referral card, triggers the feature phone call, operates the receiving desks and dispatcher console, and keeps one finger on the `F1`–`F7` hotkeys for instant MP4 fallback playback if venue hardware hiccups).

### 2.3 Pre-Recorded MP4 Fallback Hotkey Map (`v8 §13.2`, `FINAL §17`)
If any external dependency (venue Wi-Fi, projector EDID, cellular carrier) lags by $> 2\text{ s}$, Person B presses the mapped hotkey to seamlessly switch the active pane to the timestamped recording while **explicitly disclosing on screen** (`D4: FALLBACK CLIP ACTIVE`):
- `Hotkey F1` $\rightarrow$ `clip_A.mp4`: Rotating QR scan + `PARALLEL2` referral creation ($0\text{–}7\text{ s}$).
- `Hotkey F2` $\rightarrow$ `clip_B.mp4`: Simultaneous Accept race $\rightarrow$ one `200 OK` (`lease_epoch=1`), one `409 LEASE_HELD` ($7\text{–}12\text{ s}$).
- `Hotkey F3` $\rightarrow$ `clip_C.mp4`: `BROKEN_BUILD=1` scratch DB double-lease $\rightarrow$ Monitor turns RED (`I2`) in $\le 2\text{ s}$ $\rightarrow$ switch back green ($12\text{–}21\text{ s}$).
- `Hotkey F4` $\rightarrow$ `clip_D.mp4`: `psql` superuser row tamper $\rightarrow$ Pure-JS browser verifier names exact broken link `seq=n kind=HASH` ($21\text{–}30\text{ s}$).
- `Hotkey F5` $\rightarrow$ `clip_E.mp4`: Exotel outbound IVR ringing feature phone $\rightarrow$ Press-1 AMD gate $\rightarrow$ Kannada/English prompt $\rightarrow$ DTMF PIN accept.
- `Hotkey F6` $\rightarrow$ `clip_F.mp4`: `DEMO_FAST` silence escalation across 3 facilities to `ESCALATED_TO_DISPATCHER` in $\le 24\text{ s}$.
- `Hotkey F7` $\rightarrow$ `clip_G.mp4`: Toxiproxy `reset_peer` + API kill/restart + offline stale confirmation `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`.

---

## 3. Runbook A: The 5-Minute Colossus 3.0 Official Stage Script (with Mandatory 30s Live Proof Loop)

> **Total Clock:** `5:00` (`300 seconds`)
> **Mandatory Live Demo Minimum:** $\ge 30\text{ s}$ (`FINAL §0, §17`). In this script, **4 minutes and 15 seconds** are live interaction on the running stack.

---

### Segment 1: The Referral Black Box & Pitch Hook (`0:00 – 0:45`)

**Visual on Screen:**
- Pane 2 displays a single stark evidence overlay card alongside the live Clinician Referral Card ready to fire.

**Person A (Spoken):**
> "When a mother in labour needs an emergency C-section that a Primary Health Centre cannot perform, a referring doctor, an ambulance crew, and a receiving hospital must act as one.
>
> Today, that handover is shouted across a street. In a study of 199,888 deliveries in urban Maharashtra by Das et al. (2023) `[V]`, referring facilities phoned the receiving hospital in only **47% of referrals**—**53% had no phone contact at all**, only **37% of referral slips were fully documented**, and **40% of referred women could not be tracked** at the higher facility. In a 2018–2023 audit of 3,220 inter-facility obstetric referrals at Safdarjung Hospital, Delhi `[V]`, **90.6% of critically ill patients arrived with no prior communication**, and **47.3% had visited two or more hospitals first**—hospital ping-pong.
>
> We built **ReferralHandshake (`Protocol RHP-1`)**. It turns an unconfirmed referral message into a **Verifiable Referral Contract**: offered, answered, negotiated, owned by at most one destination under a fenced lease, escalated automatically on silence, never blocking transport, working from a feature phone to a command centre, and checked continuously by an independent runtime monitor.
>
> Don't take our word for it. Help us try to break it live in the next 30 seconds."

---

### Segment 2: The Mandatory 30-Second Live Proof Loop (`0:45 – 1:15`, `F16`, Profile `DEMO_FAST`)

> **Clock Reference:** `t = 0s .. 30s` inside the proof loop (`0:45` to `1:15` wall clock).

| Loop $t\text{ (s)}$ | Wall Clock | Actor & Exact Action | Visible System & Monitor Result | Fallback |
|---|---|---|---|---|
| **$0\text{–}4\text{ s}$** | `0:45–0:49` | **Person A:** "Two judges, please scan the rotating QR on screen or hold the two pre-joined tablet desks `D1` (District Hospital A) and `D2` (District Hospital B)." | Single-use `jti` QR validates; `D1` and `D2` appear on Pane 2 (`JUDGE_DESK`, cap 20). Pane 1 Monitor shows `I1–I16: GREEN`, `Violations: 0`. | `clip_A.mp4` |
| **$4\text{–}7\text{ s}$** | `0:49–0:52` | **Person B:** Clicks **Send Emergency Obstetric Referral (`PARALLEL2`)** on Clinician Card (`need_class=OBSTETRIC_EMERGENCY`, `mgso4_status=UNKNOWN`). | Atomic `CREATE` transaction commits. Both `D1` and `D2` flash `OFFERED` (`open_offers = 2`). Red banner displays: *"Pre-referral $\text{MgSO}_4$ dose UNKNOWN — verify before dosing"* without blocking dispatch (`D1`, `I3`). | `clip_A.mp4` |
| **$7\text{–}12\text{ s}$** | `0:52–0:57` | **Person A:** "On three, both hospitals press **Confirm Resources & Accept** at the exact same instant—one, two, three!" Both desks tap Accept (or Person A fires `./scripts/fire_race200.sh` alongside the two desks). | PostgreSQL row lock (`SELECT ... FOR UPDATE` on `referral`) + partial unique index `one_lease` serialises the race. Desk `D1` gets `200 OK` (`ACCEPTED`, `lease_epoch = 1`). Desk `D2` immediately receives `409 LEASE_HELD` (`SUPERSEDED`). Monitor stays **GREEN** (`I2`, `I12`). | `clip_B.mp4` |
| **$12\text{–}18\text{ s}$** | `0:57–1:03` | **Person A:** "How do you know our monitor isn't just a static green PNG? Let's switch to a deliberately broken build (`BROKEN_BUILD=1`) on our isolated scratch database where the lease guard is removed." Runs `make broken-on` in Pane 3. Both desks press Accept on a new referral. | Top banner flashes red: **`BROKEN BUILD — SCRATCH DB (rhp_scratch_broken)`**. Both `D1` and `D2` receive `200 OK` (two leases granted!). Within **$\le 2\text{ s}$**, Person B's independent Python monitor turns bright **RED**: `VIOLATION I2 (DOUBLE_LEASE) & DIFF_EPOCH`. | `clip_C.mp4` |
| **$18\text{–}21\text{ s}$** | `1:03–1:06` | **Person A:** Runs `make broken-off` in Pane 3; Person B triggers a clean referral. | System returns to production primary DB; red banner clears; Monitor returns to **GREEN** (`0 violations`). | `clip_C.mp4` |
| **$21\text{–}27\text{ s}$** | `1:06–1:12` | **Person A:** "Now suppose a rogue sysadmin with database superuser access silently edits an event row in `psql` to hide a rejected handover." Executes `./scripts/tamper_row.sh` in Pane 3. | The pure-JS verifier running directly in the judges' browsers (`@noble/curves/ed25519` + `@noble/hashes/sha256` + RFC 8785 JCS) compares the event stream against the signed C2SP Merkle checkpoint and prints: `BROKEN referral=<id> seq=3 kind=HASH expected=9f8a... got=4c12...`. | `clip_D.mp4` |
| **$27\text{–}30\text{ s}$** | `1:12–1:15` | **Person B:** Triggers the 30-second Proof Overlay on Pane 1. | Overlay displays live-measured counters: `I1–I16 Checked`, `200-Way Race Winner = 1`, `Deadlock Delta = 0`, live-measured $p_{50} / p_{95}$ command latency, and `Tamper Link Named = seq 3`. | `clip_D.mp4` |

---

### Segment 3: Reach Without Dependency — Feature Phone IVR & Paper Code (`1:15 – 2:30`)

**Visual on Screen:**
- Switch profile selector on new referral to `DEMO_VOICE` ($A = 45000\text{ ms}$, rung $A/4 = 11250\text{ ms}$).
- Person B holds up the physical **feature phone** next to the microphone.

**Person A (Spoken):**
> "What if the receiving Community Health Centre has no smartphone, no app installed, or no Wi-Fi? RHP-1 reaches every party where they are.
>
> Under our unified ACK window $A$ (`F2`), rung 0 pushes SSE and an empty-payload FCM wake ping (zero PHI over third-party push, `I10`). When nobody opens the card by $A/4$, the stateless poller fires `NOTICE_VOICE` via Exotel outbound IVR to the facility's rostered duty number."

**Live Action (`1:35 – 2:10`):**
1. The feature phone on stage rings out loud.
2. **Person A:** "Notice that if this went to voicemail, it would never count as an acknowledgement. Our AMD + mandatory press-1 gate (`F7`) requires a human keypress before `ACK` is committed."
3. **Person B** answers on speakerphone and presses `1`.
4. **Speakerphone Audio (Pre-recorded native voice + synthesized facility code, zero patient name):**
   *"Emergency obstetric referral from PHC-Kanakapura. Need class: Obstetric Emergency. ETA 18 minutes. Press 1 to Accept all required resources, 2 to Counter with conditions, 3 to Decline, 9 to repeat, followed by your 4-digit duty PIN and hash."*
5. **Person B** dials `2` (Counter: *"Can take patient, anaesthetist arriving in 20 minutes"*), enters PIN `4821#` (transmitted as `%23`).
6. Within $< 1.5\text{ s}$ (inside the $2\text{ s}$ webhook budget, well below Exotel's $5\text{ s}$ ceiling `[V]`), `apply_command(COUNTER)` commits in PostgreSQL. Only **after** commit does the voice call speak *"Counter-offer recorded"* and Pane 2 updates live to `COUNTERED` (`counter_round = 1`).
7. **Person B** taps **Confirm Counter-Offer** on the referring clinician's screen $\rightarrow$ state transitions `COUNTERED` $\rightarrow$ `ACCEPTED` (`lease_epoch` increments).
8. **Person A points to the printed Referral Card:** "And if the network is completely dead, the printed Referral Card *is* the Dakshata referral slip—zero double entry for nurses (`v8 D18`). It carries a 9-character Crockford Base32 paper code with a prime $\bmod 37$ check symbol that catches 100% of single-character typos and adjacent transpositions when typed at the receiving desk."

---

### Segment 4: Two Independent Tracks, Silence Escalation & Deadlock-Free Poller (`2:30 – 3:45`)

**Visual on Screen:**
- Pane 2 shows the **Transport Track** map (`REQUESTED` $\rightarrow$ `DISPATCHED` $\rightarrow$ `EN_ROUTE`) moving independently alongside a new `DEMO_FAST` referral where all receiving desks stay completely silent.

**Person A (Spoken):**
> "In emergency obstetrics, software must **never block care** (`Invariant I3`). Look at the bottom of Pane 2: the ambulance is already `EN_ROUTE` on the Transport Track while the Handshake Track is still negotiating ownership. Our transport handler never even reads `hs_state`.
>
> Now watch what happens on Referral #4 when every hospital stays silent."

**Live Action (`2:55 – 3:25`):**
1. Person B creates Referral #4 under `DEMO_FAST` ($A = 3\text{ s}$, $D = 4\text{ s}$, $\epsilon = 1\text{ s}$, $F = 3$ facilities in the administratively approved catchment chain, bound $B = 25\text{ s}$).
2. **Facility 1 stays silent:** At $t = 3\text{ s}$, the two-phase poller claims the due `ACK` deadline using a single committed `UPDATE ... FOR UPDATE SKIP LOCKED` statement (Phase 1) and invokes `apply_command(TIMEOUT)` (Phase 2), acquiring locks in our strict global order: `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox` (`F1`, `I14`).
3. Facility 1's offer moves to `SOFT_OPEN` (preserving the late-accept window until Facility 2 ACKs, keeping `open_offers <= 2`, `I12`), and Facility 2 opens (`OFFERED`).
4. **Facility 2 ACKs at $t = 5\text{ s}$** (which immediately closes Facility 1's `SOFT_OPEN` offer to `TIMED_OUT`), then stays silent through its decision window $D = 4\text{ s}$.
5. **Facility 3 stays silent:** Before $T_{max} = F \cdot (A + D + \epsilon) = 3 \cdot (3 + 4 + 1) = 24\text{ s} \le B = 25\text{ s}$ (`F3`, `I13`), the pre-approved chain is exhausted.
6. The referral deterministically enters `ESCALATED_TO_DISPATCHER` (`I7`: the system never invents an unapproved destination). The Dispatcher Console pages red, and Person B assigns a destination via phone-assisted proxy (`source = 'DISPATCHER'`, `proxy = true`).

**Live Action (`3:25 – 3:45` — Network Partition & Stale Offline Reconfirmation):**
1. **Person A** runs `./scripts/inject_reset_peer.sh` (Toxiproxy injects TCP `reset_peer` between API and DB) while Person B clicks `TR_UPDATE(ARRIVED)` on the ambulance PWA.
2. The client retries with the same `Idempotency-Key` and `UUIDv7` `event_id`. Once Toxiproxy clears, the command applies **exactly once** (`I4`: gap-free `seq`, zero duplicates).
3. **Person A:** "And if an offline hospital desk confirmed OT and Blood 15 minutes ago and their tablet flushes an offline `ACCEPT` after reconnecting, Step 7 checks `offer_resource_confirmation.expires_at` (`F12`, `I15`), rejects the stale confirmation with `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`, and prompts a live 1-tap reconfirmation so a patient never rolls into an OT that was taken 10 minutes ago."

---

### Segment 5: Loop Closure, Anti-Goodhart Analytics & Honest Claims Close (`3:45 – 5:00`)

**Visual on Screen:**
- Pane 2 transitions `ARRIVED` $\rightarrow$ `HANDED_OVER` $\rightarrow$ `CLOSED(outcome = DELIVERED_AT_RECEIVER)`.
- District Command Centre projection opens showing the referral network graph and APOT separation chart, followed by the **Claims & Honest Limits** summary card.

**Person A (Spoken):**
> "When the patient is handed over, the contract cannot silently vanish. To reach `CLOSED`, the receiver records a structured outcome—or if nobody closes it after two `CLOSURE` deadlines, the protocol closes it as `UNKNOWN_COUNTER_REFERRAL` with `proxy=true` (`F6`), surfacing the gap to district officers while scheduling per-referral DEK envelope crypto-shredding of the clinical payload (`§10`).
>
> On the District Command Centre, notice how we prevent Goodhart's Law (`v8 §11`, `FINAL §15`): receiving desks see a priority queue with **zero countdown clocks** so triage isn't distorted, and district dashboards measure **Arrival-to-Handover (APOT)** separately from **Acceptance**, so 'accepting on the screen while holding the patient in the ambulance' is immediately visible.
>
> Finally, our **Claims Discipline (`§19`)**:
> - We **do not** claim ReferralHandshake creates hospital beds or saves lives—it surfaces refusals before the ambulance reaches a locked door and gives administrators bottleneck evidence.
> - Our Quint model (`rhp1.qnt`) checks the control-plane specification within stated bounds ($F=3, E=4$); our production Python code is checked by conformance vectors, a 200-way barrier suite, and Person B's zero-shared-code runtime monitor (`F17`).
> - Our log is **tamper-evident** via C2SP Merkle witnesses and exports a BSA Section 63-ready hash bundle—never claimed as 'immutable' or 'legally certified'.
>
> **No emergency referral without a receipt—and every guarantee shown holding under attack, live.** We are MAHA YODHAS, and we are ready for your questions."

---

## 4. Runbook B: Extended 7-Minute Guarantee Arena Script (8 Scenes, `v8 §14`)

Use this extended 8-scene runbook during booth judging, deep-dive technical audits, or if the pitch format grants 7 minutes.

| Time | Scene | T1 (Person A) & T2 (Person B) Actions | Invariants & Closures Demonstrated | Fallback |
|---|---|---|---|---|
| **0:00–1:00** | **1. The Phone Rings** | T1 introduces a 1-line **composite persona** (explicitly labelled composite: a PHC Medical Officer in rural Karnataka) and cites Das et al. (2023) `[V]` (53% no phone contact) & Safdarjung (2018–23) `[V]` (90.6% unannounced). T2 creates an obstetric referral in $\approx 20\text{ s}$ (1-tap pre-approved chain, `mgso4_status=UNKNOWN` red banner). A judge holds the whitelisted **feature phone**: Exotel outbound call rings at rung $A/4$, passes the press-1 AMD gate, reads the de-identified prompt, judge presses `1` + PIN + `#`. Screen shows `OFFER_ACKED` $\rightarrow$ `OFFER_ACCEPTED` (`lease_epoch=1`) while ambulance dot moves on the parallel Transport Track. | `D1` ($\text{MgSO}_4$ answer-required, never blocks), `I3` (parallel transport), `I6` (rostered PIN auth), `F2` (unified ladder), `F7` (AMD + press-1 gate, $2\text{ s}$ webhook budget). | `clip_E.mp4` |
| **1:00–2:15** | **2. The Race** | Judges scan rotating single-use QR (Turnstile challenge, cap 20), become competing hospital desks (`PARALLEL2` mode), and press Accept simultaneously alongside `./scripts/fire_race200.sh` (200 concurrent coroutines). Exactly one `200 OK` wins the lease; 199 receive deterministic `409 LEASE_HELD`. Monitor stays green (`deadlocks_delta = 0`). | `I2` (`one_lease` partial unique index + row lock), `I8` (`version` 412 vs `lease_epoch` 409), `I12` (`open_offers <= 2`), `F1 / I14` (global lock order). | `clip_B.mp4` or LAN QR |
| **2:15–3:15** | **3. The Silence** | Under `DEMO_FAST`, T2 sends a sequential referral where Facility 1 ignores ACK ($3\text{ s}$ $\rightarrow$ `SOFT_OPEN`), Facility 2 ACKs (closing Facility 1's soft-open window) then ignores Decision ($4\text{ s}$), and Facility 3 ignores all rungs. Within $24\text{ s} \le B=25\text{ s}$, state transitions to `ESCALATED_TO_DISPATCHER`. T2 assigns via Dispatcher Proxy (`source='DISPATCHER'`, `proxy=true`). | `I1` (deferred constraint trigger `i1_pending_deadline`), `I7` (`offer_chain_guard`), `I9` (no facility loops), `F3 / I13` ($T_{max} = F(A+D+\epsilon) \le B$), `F13` (`SOFT_OPEN` late-accept rule). | `clip_F.mp4` |
| **3:15–4:15** | **4. The Failure** | T1 activates Toxiproxy (`reset_peer` and `latency` between API and DB), then runs `docker compose kill api && docker compose start api` mid-referral while T2 submits `CONFIRM_COUNTER` and `TR_UPDATE`. Client retries with `Idempotency-Key`; step 1 `pg_try_advisory_xact_lock` and `idempotency` table replay the exact result with zero duplicate events. **Live-measured recovery time** is displayed on Pane 1. | `I4` (gap-free `seq`, `event_id UNIQUE`), `F14` (10-step `apply_command`, `SAVEPOINT sp_cmd` storing domain rejections in `rejected_command`), `F11 / I16` (`GREATEST(clock_timestamp(), head_ts)`). | `clip_G.mp4` |
| **4:15–5:00** | **5. The Forgery** | T1 connects to `psql` as superuser on scratch DB and alters an `event` row. The pure-JS verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`, RFC 8785 JCS) on the judges' phones compares the chain against the 5-second C2SP signed Merkle checkpoint already held on their phones and names the exact broken link (`BROKEN referral=... seq=3 kind=HASH`). T1 contrasts this with a legitimate cold-key signed `RESTORE` checkpoint (`F8`). | `I5` (SHA-256 JCS chain + Ed25519 Merkle checkpoints), `I11 / F9` (`rhp_detail_ok` allowlist), `F8` (separate OS user `rhp-sign`, $O(\log N)$ inclusion proof, cold-key `RESTORE`). | `clip_D.mp4` |
| **5:00–5:45** | **6. The Broken Build** | T1 flips `BROKEN_BUILD=1` (hard-routed to `rhp_scratch_broken` minus `one_lease`; red banner flashes). Two desks press Accept $\rightarrow$ both win $\rightarrow$ Person B's independent monitor turns **RED** (`I2` + `DIFF_EPOCH`) in $\le 2\text{ s}$. T1 flips back to production primary $\rightarrow$ Monitor green. | `F17` (Common-mode independence: Person A server/Quint vs Person B monitor; mutation suite `M1–M6`), `F20` (scratch DB hard isolation, exit 78 on `REAL_DATA=1`). | `clip_C.mp4` |
| **5:45–6:30** | **7. Degraded World & AI Forcing** | Ambulance phone goes offline: queued GPS/observations show *"pending, not confirmed"* and merge via set-union on reconnect; a stale offline `ACCEPT` is rejected with `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` (`I15`). T2 demonstrates `GRANT_REVOKED` wiping clinical DOM state on an open SSE stream (`F10 / I10`), types a 9-char Crockford Base32 paper code, and shows the optional AI Intake Accelerator withholding its draft (`423 ANCHOR_REQUIRED`) until the clinician commits `need_class` and `mgso4_status` (`§16`). | `F12 / I15` (confirmation TTL), `F10 / I10` (per-event SSE authz + `GRANT_REVOKED`), `F5` (6 arrival cases, geofence 200m hint only), `§16` (Cognitive Forcing Function, system works with AI off). | Cut first if short on clock |
| **6:30–7:00** | **8. Close & District View** | T2 completes handover (`HANDED_OVER` $\rightarrow$ `CLOSED` with structured outcome, returning receipt to origin PHC). T1 shows the read-only District Command Centre (in-app process map, APOT arrival-to-handover vs acceptance separation, FHIR R4 `ServiceRequest` + `Task` export) and closes on the **Claims Register & Honest Limits** slide. | `F6` (9-outcome taxonomy + 2-stage `CLOSURE` deadline), `§10` (per-referral DEK crypto-shredding), `§15` (anti-Goodhart analytics), `§19` (Claims Register). | — |

---

## 5. Exact Terminal Commands for Stage Execution (Pane 3 Copy-Paste Sheet)

Keep these five helper commands ready in Pane 3 (`tmux` session `arena`):

### 5.1 Fire the 200-Way Concurrent Accept Barrier (`T-C1 / race200`)
```bash
python3 -m tests.concurrency.race200 \
  --api-url http://localhost:8000 \
  --referral-id "$ACTIVE_REFERRAL_ID" \
  --concurrency 200
```
**Expected Output on Stage:**
```text
[race200] Launching 200 concurrent coroutines behind asyncio.Barrier(200)...
[race200] HTTP 200 (Lease Granted): 1
[race200] HTTP 409 (LEASE_HELD):    199
[race200] DB offer status='ACCEPTED' count: 1
[race200] Event seq gap check (max(seq) - count(*)): 0
[race200] pg_stat_database deadlocks delta: 0
[race200] PASS (I2, I4, I14 verified live)
```

### 5.2 Toggle `BROKEN_BUILD=1` on Isolated Scratch Database (`F20`)
```bash
# Switch ON (routes exclusively to rhp_scratch_broken; aborts with exit 78 if REAL_DATA=1)
export BROKEN_BUILD=1 DATABASE_URL="postgresql://rhp_scratch@localhost:5432/rhp_scratch_broken"
docker compose up -d api monitor

# Switch OFF (restore production primary)
export BROKEN_BUILD=0 DATABASE_URL="postgresql://rhp_app@localhost:5432/rhp_primary"
docker compose up -d api monitor
```

### 5.3 Execute Superuser Row Tamper & Run Pure-JS Verifier (`F8 / I5`)
```bash
# In scratch DB as superuser, bypass trigger temporarily to simulate insider disk/DB tamper:
psql "postgresql://postgres@localhost:5432/rhp_scratch_broken" << 'EOF'
SET session_replication_role = replica;
UPDATE event SET detail = '{"facility":"TAMPERED_FACILITY","epoch":99}'::jsonb
 WHERE referral_id = (SELECT id FROM referral ORDER BY created_at DESC LIMIT 1)
   AND seq = 3;
SET session_replication_role = origin;
EOF

# Trigger CLI mirror of the browser @noble/curves + @noble/hashes verifier:
node ./pwa/scripts/verify_checkpoint.mjs --api http://localhost:8000 --witness http://localhost:8002
```
**Expected Output on Stage & Judge Phones:**
```text
[Verifier] Checkpoint #381 Ed25519 signature VALID (signer_key_id: rhp-sign-2026-11)
[Verifier] Recomputing RFC 8785 JCS SHA-256 chain from genesis (32x0x00)...
[Verifier] BROKEN referral=01931f4a-7c20-7b12-9a11-08d4e1209c01 seq=3 kind=HASH
           expected=9f8a4d2c11e08b773c91a04f62d8e51109ab34c721f08e12d45a67b890c12345
           got     =4c1289ab0012f4e89123c45d67e89f0123456789abcdef0123456789abcdef01
```

### 5.4 Inject & Clear Toxiproxy Network Faults (`§12 / Scene 4`)
```bash
# Inject TCP reset_peer + 600ms latency on pg_proxy
toxiproxy-cli toxic add -t reset_peer -n pg_reset -a timeout=500 pg_proxy
toxiproxy-cli toxic add -t latency -n pg_lat -a latency=600 -a jitter=200 pg_proxy

# Clear toxics and measure recovery
toxiproxy-cli toxic remove -n pg_reset pg_proxy
toxiproxy-cli toxic remove -n pg_lat pg_proxy
```

---

## 6. Stage Discipline: Words Never Spoken vs. Authorized Phrasing (`§19`)

Both presenters must enforce these exact linguistic guardrails during the pitch and Q&A:

| Topic | NEVER Say on Stage (Forbidden) | ALWAYS Say on Stage (Authorized) |
|---|---|---|
| **Clinical Impact** | "Saves lives", "prevents maternal deaths", "eliminates hospital ping-pong" | "Surfaces refusal before the ambulance reaches a locked door; process improvement is a hypothesis to be tested in an ethics-approved pilot." |
| **Epidemiology** | "Across India, 53% of referrals fail" or "90% of Indian patients arrive unannounced" | "In Das et al. (2023) in urban Maharashtra `[V]`, 53% had no phone contact; in a single tertiary obstetric ICU audit at Safdarjung Hospital, Delhi (2018–23) `[V]`, 90.6% arrived without prior communication." |
| **Formal Methods** | "Mathematically proven system", "bullet-proof", "airtight", "zero loopholes", "crash-proof" | "Our Quint model checks the control-plane specification within stated bounds ($F=3, E=4$); our code is checked by conformance vectors, a 200-way barrier test, and an independent runtime monitor. Every identified weakness is `CLOSED`, `BOUNDED` with a stated residual, or `OPEN` with an owner." |
| **Competitors** | "We are the first or only system with single-owner leases" | "Automatic inter-facility escalation and hard single-owner leases were not found in public documentation of the systems audited (`[V*]`)." |
| **Audit Log & Legal** | "Immutable blockchain log", "BSA Section 63 certified", "ABDM compliant" | "Tamper-evident hash-chained log with independent C2SP Merkle witnesses; exports a BSA s.63-ready hash bundle; FHIR-shaped export (`ServiceRequest` + `Task`), synthetic data only (`REAL_DATA=0`)." |
| **Metrics** | Pre-quoting "MTTR is 3 seconds" or "Latency is 12ms" from a slide | "Let's read the live-measured recovery time and $p_{50}/p_{95}$ latency directly off the monitor screen from the run we just executed." |