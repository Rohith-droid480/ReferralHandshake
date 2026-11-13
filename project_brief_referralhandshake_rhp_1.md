# Project Brief — ReferralHandshake (Protocol RHP-1)

**Project Title:** ReferralHandshake — The Verifiable Emergency Referral Contract (Protocol RHP-1)  
**Team:** MAHA YODHAS (2 Students: Person A / Lane A & Person B / Lane B)  
**Track & Event:** HealthTech Track, Colossus 3.0 (13–14 Nov 2026, Bengaluru; 24-hour hackathon build)  
**Pitch Format:** 5-minute live presentation including a mandatory $\ge 30\text{ s}$ live interactive proof loop (`[V]`)  
**Core Tagline:** *"Today a referral is shouted across a street. ReferralHandshake makes it a signed-for handover, and proves the signature holds, live."*  
**Long-Term Vision:** *"No emergency referral without a receipt."*

---

## 0. Locked Problem Statement, USP & MVP

### 0.1 The Locked Problem Statement (v7 §4)
> **How can an emergency referral stop being a message and become a verifiable contract: one that is offered, answered, negotiated, owned by exactly one destination, escalated automatically when nobody responds, never delays care, works from a feature phone to a command centre, survives failures, and closes with an outcome back to the referrer, with its guarantees provable rather than promised?**

### 0.2 The Three-Part USP (All Three Required)
1. **Deterministic Contract Semantics:** Structured offer, explicit acknowledgement (`ACK`), structured response vocabulary (`ACCEPT` with per-resource confirmation, `COUNTER` with up to 2 rounds, `DECLINE` with missing-resource reason), single-owner lease with monotonic fencing epoch (`lease_epoch`), two-level escalation ladder (intra-facility concurrent slots + voice stagger $\rightarrow$ next catchment facility $\rightarrow$ human dispatcher), and mandatory closing outcome.
2. **Reach Without Dependency:** Operates seamlessly across React PWA hospital desks, native Kotlin Android ambulance apps, outbound Exotel voice IVR with keypad + PIN on a feature phone, static DLT SMS alerts, 9-character Crockford Base32 paper codes on printed slips, and dispatcher phone-assisted proxy entry.
3. **Live Provability Under Attack:** A frozen Quint control-plane specification (`rhp1.qnt`), conformance test vectors, a 200-way concurrent barrier test, an **independent Python runtime monitor** (written by the teammate who did not write the server) that re-derives every referral's state from the hash-chained event log, Ed25519 Merkle checkpoints broadcast to independent witnesses, and a live **Guarantee Arena** where judges attack the system on stage.

### 0.3 Minimum Viable Product (MVP) Definition
One emergency obstetric referral running end-to-end across four roles (**Referring Clinician**, **Receiving Duty Role**, **Ambulance Crew**, **Dispatcher**):
- `CREATE` structured referral card $\rightarrow$ `OFFER` to receiving facility's duty role $\rightarrow$ `ACK` $\rightarrow$ `ACCEPT` / `COUNTER` / `DECLINE` $\rightarrow$ single-owner lease (`one_lease`) $\rightarrow$ durable timer escalation (notice rungs inside the facility, then next approved catchment facility, then `ESCALATED_TO_DISPATCHER`) $\rightarrow$ parallel `tr_state` transport track $\rightarrow$ human-confirmed `ARRIVED` $\rightarrow$ `HANDED_OVER` $\rightarrow$ `CLOSED` with outcome, backed by an append-only SHA-256 hash-chained log, an offline outbox, a `BROKEN_BUILD` chaos switch, and the live runtime monitor.
- **Done Means:** The conformance suite passes, `race200` grants exactly 1 lease with 0 deadlocks, mutation tests `M1–M6` trip their checkers, the monitor shows 0 invariant violations under attack, and the core demo runs even with optional layers (`T1–T3`) switched off.

---

## 1. Ideation & Concept Selection Summary

### 1.1 Root-Cause Decomposition (F1–F8)

| ID | Root Failure Mode | Empirical Basis (`[V]`) | RHP-1 Contract Mechanism |
|---|---|---|---|
| **F1** | **Silence** (referral is an unacknowledged message) | $53\%$ no phone contact (Maharashtra); $90.6\%$ unannounced arrivals (Safdarjung) | Enforced `ACK` window $A$ and `DECISION` window $D$; notice rungs at $0, A/4, 3A/4$ |
| **F2** | **Ownerless or doubly-owned patient** ("ping-pong") | $47.3\%$ visited $\ge 2$ hospitals first (Safdarjung) | Per-referral `FOR UPDATE` lock + `one_lease` partial unique index + `lease_epoch` |
| **F3** | **Capability mismatch** | $19\%$ resource-driven (no OT $47\%$, no NICU $45\%$, no anaesthetist $24\%$) | `need_class_requirement` + live `RESOURCE_CONFIRM` (`expires_at` TTL) + `COUNTER` |
| **F4** | **Information loss** | $50\%$ incomplete slips (Safdarjung); $40\%$ untraceable (Maharashtra) | ISBAR + Dakshata card (`mgso4_status`) + printable slip with Base32 paper code |
| **F5** | **Reach & connectivity gaps** | $70\%$ no escort (Safdarjung); dead zones; feature-phone desks | Outbound Exotel IVR (`Press 1` + PIN), DLT SMS, offline outbox, dispatcher proxy |
| **F6** | **No evidence or loop closure** | Counter-referrals rarely returned to originating PHC | SHA-256 hash chain + Merkle witnesses + two-stage `CLOSURE` deadline |
| **F7** | **Adoption & Goodhart gaming** | Countdown clocks distort triage; accept-without-bed delays handover | Priority queue (no countdowns), APOT arrival-to-handover metric, capacity framing |
| **F8** | **Systemic blindness** | District officers cannot see where referrals stall | Read-only command centre projections, network graph, IEEE 1849 XES export |

### 1.2 Weighted Evaluation of 13 Candidate Concepts (v8 §1.3)
Weights: **Impact** ($20$), **Real-World Operability** ($15$), **Safety & Legal Defensibility** ($15$), **Technical Soundness/Provability** ($15$), **Hackathon Wow** ($15$), **2-Person Build Feasibility** ($10$), **Scope/Upside** ($10$). Ranking is invariant to $\pm 5$ weight shifts.

| Concept | Imp (20) | Oper (15) | Safe (15) | Tech (15) | Wow (15) | Feas (10) | Scope (10) | **Weighted Total (10)** |
|---|---|---|---|---|---|---|---|---|
| **C1** Gemini spec as originally written | 6 | 4 | 4 | 6 | 7 | 7 | 5 | **5.6** |
| **C2** Locked v7, all layers built at once | 8 | 9 | 8 | 8 | 9 | 4 | 8 | **7.9** |
| **C3 v8 + Final Architecture (Gated & Cut-Lined Fusion)** | **9** | **9** | **9** | **9** | **10** | **7** | **10** | **9.1 (LOCKED WINNER)** |
| **C4** Blockchain referral ledger | 4 | 3 | 4 | 4 | 6 | 5 | 4 | **4.3** |
| **C5** AI triage + auto-routing optimiser | 6 | 5 | 2 | 4 | 8 | 5 | 7 | **5.3** |
| **C6** Voice/IVR-only referral bridge | 7 | 9 | 7 | 5 | 6 | 8 | 5 | **6.8** |
| **C7** Dispatcher command-centre dashboard only | 6 | 6 | 7 | 5 | 6 | 7 | 6 | **6.1** |
| **C8** FHIR/ABDM e-referral integration only | 5 | 4 | 6 | 6 | 3 | 5 | 7 | **5.1** |
| **C9** District digital-twin simulation as headline | 5 | 3 | 3 | 4 | 8 | 3 | 6 | **4.6** |
| **C10** WhatsApp referral bot | 6 | 7 | 1 | 4 | 5 | 9 | 4 | **5.1** |
| **C11** Open protocol + conformance suite only | 7 | 4 | 8 | 8 | 5 | 6 | 9 | **6.7** |
| **C12** Offline mesh / LoRa network | 5 | 5 | 5 | 5 | 7 | 2 | 4 | **4.9** |
| **C13** Live bed-availability marketplace | 7 | 4 | 5 | 5 | 6 | 6 | 7 | **5.7** |

---

## 2. Scope Tiers (T0–T3), Feature Flags & Cut Order

### 2.1 Locked Build Tiers (Architecture §2)

| Tier | Feature Flag | Exact Deliverables Included | Cut Order Under Time Pressure |
|---|---|---|---|
| **T0 (Core & Proof)** | Always ON | FastAPI `apply_command()` (10 steps), PostgreSQL 16 (24 tables), 2-phase Poller, Outbox Relay, React PWA receiving/referring desks with rotating QR admission, Independent Python Runtime Monitor, Ed25519 Witness/Signer, Pure-JS Browser Verifier, `BROKEN_BUILD` isolated scratch DB (`rhp_scratch_broken`), `race200` & `M1–M6` mutation suite | **NEVER CUT** |
| **T1 (Transport & Console)** | `T1_TRANSPORT=1` | PWA ambulance client (foreground GPS + manual update), parallel `tr_state` updates, 6 arrival cases (`ARRIVAL_SUGGESTED` $\rightarrow$ human `ARRIVED`), Dispatcher console with proxy entry & override, time-scrubber replay | **Cut 3rd** (keep after T2/T3 cuts) |
| **T2 (Reach Adapters)** | `T2_REACH=1` | Outbound Exotel voice IVR (AMD + `Press 1` gate + Kannada/Hindi/English prompts + DTMF PIN), DLT-compliant static SMS stub/sandbox, 9-char Crockford Base32 (`mod 37`) printable paper code | **Cut 2nd** (fallback to pre-recorded call clip if telecom fails) |
| **T3 (Extras)** | `T3_EXTRAS=1` | Native Kotlin Android foreground location app, AI Intake Accelerator with Cognitive Forcing Function (`423 ANCHOR_REQUIRED` + 20-slip seeded-error gate), NRCeS-aligned FHIR R4 bundle exporter & IEEE 1849 XES exporter | **Cut 1st** (build only after T0–T2 gates are green) |

### 2.2 Pre-Event vs. At-Event Work Boundary (`[verify]`)
- **Pre-Event Preparation (Specification & Static Artifacts Only — No Product Code):** Locked specification documents, `transitions.yaml`, Quint formal spec (`rhp1.qnt`), PostgreSQL 16 `db/schema.sql` DDL, conformance test vectors, cold-key signed profile JSON (`profiles.json`), Exotel trial account & $\le 10$ whitelisted numbers, bundled pure-JS `@noble` libraries, synthetic seed dataset (`REAL_DATA=0`), and MP4 fallback recording plan.
- **At-Event Execution (24-Hour Window):** All application code (`api/`, `monitor/`, `witness/`, `pwa/`, `tests/`) built against the frozen specifications and verified at each tier gate.

---

## 3. Team Topology, 24-Hour Build Plan & Multi-Agent Governance

### 3.1 Two-Person Common-Mode Separation (F17)
- **Person A (Lane A — Protocol, Backend & Formal Spec):** Owns `db/schema.sql`, `spec/transitions.yaml`, `spec/rhp1.qnt`, FastAPI `apply_command()`, 2-phase Poller, Outbox Relay, Ed25519 Witness/Signer, and the concurrency/mutation test harness (`race200`, `M1–M6`, Toxiproxy).
- **Person B (Lane B — Independent Monitor, Clients, Reach & Demo Ops):**
  1. Writes `monitor/monitor.py` **in a separate workspace from §3 prose alone**, importing zero server code and connecting via read-only DB role `rhp_monitor`.
  2. Owns React PWA desks, pure-JS browser verifier, Dispatcher console, Exotel IVR webhooks, Paper code UI, `BROKEN_BUILD` banner, and MP4 fallback recordings.

### 3.2 Hour-by-Hour 24-Hour Build Schedule & Step Catalogue

| Step ID | Hours | Lane A (Person A — Backend & Proof) | Lane B (Person B — Monitor, Clients & Reach) | Risk | Loop Type | Gate |
|---|---|---|---|---|---|---|
| **P1–P6** | Pre-Event | `transitions.yaml`, DDL FK scan (`ST-3`), `rhp1.qnt` verification + vacuity checks | Signed profiles + $T_{max}$ validator (`I13`), synthetic seed data, §21 pre-event checklist | HIGH | FULL / FAST | Spec Freeze |
| **E0** | H00–H02 | Repo init, `docker-compose.yml`, load 24-table DDL, seed, `transitions.yaml` loader | React PWA shell, rotating QR admission (`jti`), Turnstile / LAN mode | MED | FAST | — |
| **E1** | H02–H06 | `apply_command()` steps 1–10: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `DECLINE` | Receiving/referring desk UI, SSE stream with per-event `payload_grant` filter (`I10`) | HIGH | FULL | — |
| **E2** | H06–H09 | Stateless 2-phase Poller, Outbox Relay, `TIMEOUT`, unified notice ladder ($0, A/4, 3A/4$) | Guarantee Arena big screen UI; **Independent Python Monitor** (separate workspace) | HIGH | FULL | — |
| **E3** | H09–H12 | RFC 8785 JCS SHA-256 hash chain, `rhp-sign` witness process, $5\text{ s}$ Merkle checkpoints | Pure-JS browser verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`, O(log N) proof) | HIGH | FULL | — |
| **E4** | H12–H14 | 200-way `asyncio.Barrier` test (`race200`), mutation suite `M1–M6`, Toxiproxy suite | `BROKEN_BUILD=1` isolated `rhp_scratch_broken` DB + flashing red banner (`F20`) | HIGH | FULL | **G0 (T0 Pass)** |
| **E5** | H14–H17 | `COUNTER`, `CONFIRM_COUNTER`, 6 arrival cases (`F5`), two-stage `CLOSURE` (`F6`) | Dispatcher console (`DISPATCHER_ASSIGN`, proxy entry), PWA foreground GPS + replay scrubber | HIGH | FULL | **G1 (T1 Pass)** |
| **E6** | H17–H20 | Full idempotency matrix (`F14`), stale confirmation check (`F12`/`I15`), fencing tests | Outbound Exotel IVR (`Press 1` gate + PIN + $2\text{ s}$ budget), Base32 `mod 37` paper code | HIGH | FULL | **G2 (T2 Pass)** |
| **E7** | H20–H22 | Defect closures from Gem 2 Milestone Validation; final self-audit `ST-1..ST-5` | Record MP4 fallback clips A–D; execute full 5-minute + 30-second rehearsal $\times 3$ | MED | FULL | **G3 (Rehearsal)** |
| **E8** | H22–H24 | **HARD CODE FREEZE AT H22:** configuration-only adjustments | Final stage rehearsal, hotspot + LAN QR verification, backup laptop warm standby | LOW | FAST | **FREEZE** |

### 3.3 2-Gem Milestone Validation Multi-Agent Governance Workflow
```
G1 (CONDUCTOR) ──① AG-PROMPT──▶ GOOGLE ANTIGRAVITY (Builder) ──② BUILD REPORT + AUDIT-REQUEST──▶ G2 (AUDITOR)
      ▲                                                                                                │
      └────────────④ DECISION PACKET (Attacks as runnable tests)──────── G3 (ADVERSARY) ◀──③ RED-TEAM──┘
```
- **Rule 1 (Evidence Mandate):** Antigravity must paste raw terminal test output and full code/diff of `HIGH`-risk files in every `BUILD REPORT`. "Tests pass" without raw output is an automatic `FAIL`.
- **Rule 2 (Executable Red-Teaming):** Every attack identified by Gem 2 (`MILESTONE VALIDATOR`) is written as a concrete runnable test specification that Gem 1 (`CONDUCTOR`) injects into the next `AG-PROMPT`.
- **Rule 3 (Protected Files):** `spec/`, `db/schema.sql`, and `monitor/` are protected by `CODEOWNERS`. Antigravity may never modify the spec or weaken a test to make a build pass.
- **Rule 4 (Max 2 Fix Loops):** If a step fails 2 fix loops, Gem 1 cuts scope according to the locked tier order (`T3 -> T2 -> T1`; `T0` never) or escalates a `SPEC-QUESTION` to the human team.

---

## 4. Pitch Choreography & The 30-Second Live Proof Loop

### 4.1 The Mandatory 30-Second Live Proof Loop (`DEMO_FAST` Profile, F16)

| Time Window | On-Stage Action | Live Visible System Behaviour | Pre-Recorded Fallback |
|---|---|---|---|
| **$0\text{--}4\text{ s}$** | Judges scan rotating single-use QR (`jti`, $20\text{ s}$ TTL); two judges join as competing hospital desks `D1` and `D2` | Two read-only/synthetic `JUDGE_DESK` sessions active on big screen (admission cap $\le 20$) | `Clip A` (LAN QR fallback if venue Wi-Fi drops) |
| **$4\text{--}7\text{ s}$** | Person B creates a `PARALLEL2` obstetric emergency referral (`mgso4_status=UNKNOWN` red banner shown) | Both `D1` and `D2` receive real-time SSE offer frames simultaneously (`open_offers = 2`) | `Clip A` |
| **$7\text{--}12\text{ s}$** | Both judges press **Accept** at the exact same moment | Exactly one desk receives `HTTP 200` (`ACCEPTED`, `lease_epoch = 1`); the other receives `HTTP 409 LEASE_HELD` (`SUPERSEDED`); Monitor stays **GREEN** | `Clip B` |
| **$12\text{--}18\text{ s}$** | Person B flips `BROKEN_BUILD=1` (routes to isolated `rhp_scratch_broken` DB without `one_lease`; flashing red banner appears); new referral; both press **Accept** | Both desks win a lease; Independent Python Monitor turns **RED** (`I2 DOUBLE_LEASE_VIOLATION`) within $\le 2\text{ s}$ | `Clip C` |
| **$18\text{--}21\text{ s}$** | Person B switches back to `BROKEN_BUILD=0` (primary DB); fresh referral created | Monitor returns to **GREEN** (`0` violations on primary contract DB) | `Clip C` |
| **$21\text{--}27\text{ s}$** | Person A runs a superuser `UPDATE` in `psql` altering one historical `event` row on the scratch log | Pure-JS verifier on judges' phones immediately prints `BROKEN referral=<id> seq=<n> kind=HASH expected=<h1> got=<h2>` | `Clip D` |
| **$27\text{--}30\text{ s}$** | Big screen displays live invariant scoreboard (`I1–I16`) and live-measured `p50/p95` command latency | Every number shown on screen is measured live during the run; zero pre-claimed metrics | `Clip D` |

### 4.2 Full Presentational Arc (Adaptable to 5-Minute Colossus 3.0 Slot or 7-Minute Extended Slot)

| Segment (5m / 7m) | Scene | Enacted Flow & Key Evidence Cited | Fallback |
|---|---|---|---|
| **1 ($0:00\text{--}0:50$ / $1:00$)** | **The Phone Rings** | Composite persona (PHC Medical Officer, explicitly labelled composite). Create referral in $\approx 20\text{ s}$. A feature phone held by a judge rings via Exotel: `Press 1` gate $\rightarrow$ de-identified prompt $\rightarrow$ press `1` + PIN $\rightarrow$ `ACK` & lease granted $\rightarrow$ ambulance dot moves on `tr_state`. Cite Das et al. ($53\%$ no phone call) & Safdarjung ($90.6\%$ unannounced) `[V]`. | Pre-recorded call clip |
| **2 ($0:50\text{--}2:30$ / $3:15$)** | **30s Proof Loop + Silence Ladder** | Run the **30-Second Live Proof Loop** (Race, Broken Build, Tamper Verifier). Then ignore an offer on `DEMO_FAST`: watch notice rungs ($0, A/4, 3A/4$), `SOFT_OPEN` handoff to Facility 2, and `ESCALATED_TO_DISPATCHER` fire deterministically in $\le 24\text{ s}$ ($B = 25\text{ s}$). | LAN QR + Replay scrubber |
| **3 ($2:30\text{--}3:45$ / $5:45$)** | **Network Partition & Crash Recovery** | Trigger Toxiproxy partition + `docker kill` on API container mid-referral; restart container; client retries with same `Idempotency-Key`; zero lost or duplicate events; display **live-measured** recovery time. | `Clip C/D` |
| **4 ($3:45\text{--}4:30$ / $6:30$)** | **Degraded World (Offline + Paper)** | Ambulance phone goes offline: UI shows `"Pending, not confirmed"`; on reconnect, authoritative server state wins and explains any `409`. Desk links referral via 9-char Crockford Base32 (`mod 37`) paper code. | Cut first if behind clock |
| **5 ($4:30\text{--}5:00$ / $7:00$)** | **Loop Closure & Honest Limits** | Receiver records outcome (`ADMITTED_STABLE`); counter-referral returns to originating PHC; show read-only process map and the **What We Do Not Claim** slide (§19). | Static summary slide |

---

## 5. Reconciled 6-Month Pilot Budget, Validation Roadmap & Acceptance Gates

### 5.1 Reconciled 6-Month Pilot Cloud Budget (AWS `ap-south-1` Mumbai Multi-AZ, F18)
*Note: Figures are planning estimates to be confirmed with the AWS Pricing Calculator `[verify]`; resolves earlier document variations ($810 vs $900–$1,000 vs $1,000–$1,500).*

| Infrastructure Component | Monthly Cost (USD) | 6-Month Cost (USD) | Reconciliation Note |
|---|---|---|---|
| Managed PostgreSQL 16 Multi-AZ (`db.t4g.medium`) | $\$95.00$ | $\$570.00$ | Synchronous standby for durable contract locks |
| Provisioned Storage ($2 \times 100\text{ GB gp3}$) | $\$23.00$ | $\$138.00$ | Primary + standby storage |
| Application Load Balancer (ALB) | $\$22.00$ | $\$132.00$ | HTTPS termination & SSE routing |
| **Base Database + Entry Subtotal** | **$\$140.00$** | **$\$840.00$** | **Matches Report 3's $\$810$ base figure ($\$30$ delta = ALB LCU rounding)** |
| $2 \times$ Small Application VMs (API, Poller, Relay, Monitor, Witness) | $\$26.00$ | $\$156.00$ | Stateless workers + isolated OS user `rhp-sign` |
| Automated Backups & S3 Object Lock Witness Archive | $\$8.00$ | $\$48.00$ | Nightly logical dumps + WAL archive |
| CloudWatch Logs & Metrics ($180\text{ d}$ CERT-In retention) | $\$10.00$ | $\$60.00$ | Kept in-region (`ap-south-1`) |
| Outbound Data Transfer | $\$6.00$ | $\$36.00$ | SSE streams + API responses |
| **Subtotal with Full Application Tier** | **$\$190.00$** | **$\$1,140.00$** | **Aligns with the upper boundary of v4's $\$900\text{--}\$1,000$ lean estimate** |
| Exotel Voice IVR & DLT SMS Pilot Allowance | $\$25.00$ | $\$150.00$ | Outbound duty-role alerts & fallbacks |
| $10\%$ Operational Contingency (on $\$215.00/\text{mo}$) | $\$21.50$ | $\$129.00$ | Traffic spikes & restore drills |
| **LOCKED TOTAL PILOT BUDGET** | **$\$236.50/\text{mo}$** | **$\$1,419.00$ ($\approx \$1,420$)** | **Sits cleanly inside v8's $\$1,000\text{--}\$1,500$ range (no Kubernetes)** |

### 5.2 Pre-Event Verification Checklist (Architecture §21)

| # | Verification Item | Time Box | Exact Test Procedure | Pre-Decided Fallback |
|---|---|---|---|---|
| 1 | Event rules on pre-built work & AI coding | $1.0\text{ h}$ | Read official Colossus 3.0 rulebook; confirm with organisers | Spec-only pre-work (`Phase P`); write all code during `Phase E` |
| 2 | Exotel call concurrency, DTMF `%23`, AMD | $1.5\text{ h}$ | Place $5$ concurrent outbound calls to team phones + voicemail box | Sequential call stagger ($\delta$); PWA desks for judges |
| 3 | Exotel webhook $\le 5\text{ s}$ limit under load | $30\text{ min}$ | Replay $20$ signed webhook callbacks against local tunnel | Spoken `"Please hold"` path if DB commit exceeds $1.5\text{ s}$ |
| 4 | LAN HTTP + iOS Camera QR scan | $30\text{ min}$ | Scan `http://192.168.x.x` QR from iPhone Safari | Cloudflare tunnel domain or pre-installed local root CA |
| 5 | Pure-JS Ed25519 on iPhone Safari | $30\text{ min}$ | Verify sample C2SP Merkle checkpoint using `@noble/curves/ed25519` | Server-side verification endpoint explicitly labelled as fallback |
| 6 | Quint / Apalache verification at $F=3, E=4$ | $1.0\text{ h}$ | Run `quint verify rhp1.qnt --invariant safety` | Python explicit-state explorer over `transitions.yaml` |
| 7 | Mapbox Matrix API rate limits & key | $30\text{ min}$ | Execute $1$ Matrix request ($25$ coordinates, `mapbox/driving`) | Cached synthetic ETAs labelled `"ETA cached/simulated"` |
| 8 | Android foreground location soak | $2.0\text{ h}$ | Log GPS with screen off for $2\text{ h}$ on demo phone | PWA foreground `watchPosition` + manual `"Update Location"` button |
| 9 | DPDP Rules commencement date conflict | $1.0\text{ h}$ | Inspect official Gazette notification text (13 vs 14 Nov 2025) | Cite both dates or use 14 Nov 2025 conservatively |
| 10 | DPDP s.7(f) vs s.7(d) emergency clause | $30\text{ min}$ | Inspect official Gazette Act text | Cite as *"DPDP Act Section 7 emergency processing provision"* |
| 11 | Das et al. (2023) denominator check | $30\text{ min}$ | Inspect published tables ($25,253$ vs $28,020$) | Quote verified percentages ($47\%, 37\%, 60\%$) only |
| 12 | Chrony slew-only clock step test | $30\text{ min}$ | Step host clock by $3\text{ s}$ against running monitor | Demonstrate `heartbeat.ntp_offset_ms > 2000` alarm path |

### 5.3 Definition of Done & Tier Acceptance Gates (Architecture §24)

| Tier Gate | Measured Pass Criteria (Raw Terminal Output Required in Build Report) |
|---|---|
| **G0 (Tier T0)** | 1. `race200` passes: exactly $1$ of $200$ concurrent requests returns `HTTP 200`, PostgreSQL shows $1$ `ACCEPTED` offer, `event.seq` gap-free (`max(seq) - count(*) == 0`), `pg_stat_database.deadlocks` delta $= 0$.<br>2. Mutation tests `M1–M6` each trip their designated detector.<br>3. Independent Python monitor reports $0$ invariant violations over a $10\text{-minute}$ randomised Hypothesis + Toxiproxy run.<br>4. `quint run rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000` passes and vacuity checks fail as required.<br>5. Browser verifier pinpoints the exact `seq` and `kind=HASH\|PREV` on a tampered row.<br>6. `BROKEN_BUILD=1` turns the monitor red within $\le 2\text{ s}$ and green upon switch-back.<br>7. `DEMO_FAST` silence-to-dispatcher escalation completes in $\le 25\text{ s}$ ($T_{max} = 24\text{ s}$). |
| **G1 (Tier T1)** | 1. Dispatcher proxy entry and direct clinician/desk API entry produce identical `referral` state and `event` sequences across $20$ paired runs.<br>2. Dispatcher console successfully assigns a facility (`source='DISPATCHER'`) after `ESCALATED_TO_DISPATCHER`.<br>3. Time-scrubber replay deterministically reconstructs final state from the event log. |
| **G2 (Tier T2)** | 1. $20/20$ voice `ACK`s are spoken as confirmed only *after* PostgreSQL commit.<br>2. Voicemail/AMD trials yield $0$ false `ACK`s across $5$ trials.<br>3. Exotel webhook `p95` latency $\le 2.0\text{ s}$.<br>4. Crockford Base32 `mod 37` paper-code validator rejects $100\%$ of single-symbol errors and adjacent transpositions across $1,000$ mutated codes. |
| **G3 (Tier T3)** | 1. Android foreground service maintains GPS logging for $\ge 2\text{ h}$ with screen off.<br>2. AI draft endpoint returns `HTTP 423 ANCHOR_REQUIRED` until `need_class` and `mgso4_status` anchors are committed.<br>3. 20-slip seeded-error usability gate achieves $\le 5\%$ critical-error rubber-stamp rate and $\le 1\%$ silent-omission rate.<br>4. Exported FHIR R4 bundle passes structural validation. |