# ReferralHandshake (Protocol RHP-1) — Complete Model Prompting & Multi-Agent Operations Guide

**System:** Referral Handshake Protocol RHP-1 + Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (24-Hour Build, 2 Students)  
**Target File:** `model prompting guide.md`  
**Data Posture:** Synthetic data only (`REAL_DATA=0`)  

---

## 0. Authority, Precedence & Non-Negotiable Architectural Locks

Every prompt issued to a planning model, auditing model, red-team model, coding agent, or runtime extraction model in **ReferralHandshake** MUST obey this strict input precedence hierarchy:

1. **`ReferralHandshake_LOCKED_Problem_Statement_v7.md`** — Highest authority on problem framing, evidence status tags (`[V]`, `[V*]`, `[CONFLICT]`, `[GAP]`), the Coherence Rule, and claims discipline.
2. **Primary Research Findings tagged `[V]`** inside the locked documents.
3. **`ReferralHandshake_v8_LOCKED_Solution.md`** — Authority on D1–D20 defect closures, 28 real-world conformance scenarios, 40-item loophole ledger, and clinical operating model.
4. **`ReferralHandshake_FINAL_LOCKED_Architecture.md`** — Ultimate authority on F1–F20 closures, I1–I16 invariants, the 24-table PostgreSQL 16 DDL, the 10-step `apply_command()` pipeline, timing math ($T_{max}$), Quint specification (`rhp1.qnt`), independent Python runtime monitor, and Tiers T0–T3.
5. **`ReferralHandshake_3Gem_Antigravity_Workflow.md`** — Authority on the 2-Gem Milestone Validation Workflow (`Gem 1 Conductor <-> Antigravity`, routing to `Gem 2 Milestone Validator` on milestone completion), packet schemas, two-lane split, and build gates.

### 0.1 Hard Architectural Locks Enforced Across All Prompts

| Lock ID | Rule | Enforcement in Prompts |
|---|---|---|
| **L-COHERENCE** | Every component must be **(a)** a state/event in the contract, **(b)** an interface producing/consuming those events, or **(c)** a read-only projection of the committed event log. |Gem 2 rejects any prompt output introducing out-of-scope features or side-channel state mutations. |
| **L-STACK** | Python 3.12, FastAPI, psycopg3, PostgreSQL 16 single primary (`synchronous_commit=on`, `READ COMMITTED` + explicit `SELECT ... FOR UPDATE`), React PWA (SSE with `Last-Event-ID`, 15 s heartbeats, pure-JS `@noble/curves/ed25519` & `@noble/hashes/sha256`), Native Android Kotlin (T3) / PWA GPS fallback (T1), Exotel outbound IVR, Mapbox Directions/Matrix, Toxiproxy, Quint (`rhp1.qnt`). | Any attempt by a coding agent to install or import unapproved libraries triggers an immediate `REJECT` and short-circuit rollback. |
| **L-BANNED** | **NEVER** introduce blockchain, Kafka, Debezium, Redis, Kubernetes, WebSockets, WhatsApp, on-device LLMs, CRDTs for authoritative state, or floating-point numbers in RFC 8785 JCS canonical JSON. | Explicitly listed in `FILES/TECH MUST NOT TOUCH` in every `AG-PROMPT` and checked by CI linter `ST-5`. |
| **L-LOCK-ORDER** | Global lock order (`F1` / `I14`): strictly `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`. Poller claims due deadlines in Phase 1 via a single committed `UPDATE ... FOR UPDATE SKIP LOCKED` statement and calls `apply_command(TIMEOUT)` in Phase 2. DB trigger `rhp_require_lock` checks session GUC `rhp.locked_referral`. | Every backend prompt requires `SELECT set_config('rhp.locked_referral', r.id::text, true)` immediately after `SELECT * FROM referral WHERE id=%s FOR UPDATE`. |
| **L-TWO-TRACKS** | Handshake track (`CREATED`, `OFFERED`, `ACKNOWLEDGED`, `ACCEPTED`, `COUNTERED`, `ESCALATED_TO_DISPATCHER`, `CANCELLED`, `CLOSED`) and Transport track (`REQUESTED`, `DISPATCHED`, `EN_ROUTE`, `ARRIVED`, `HANDED_OVER`, `TR_CANCELLED`) run in parallel (`I3`). Transport never reads `hs_state`. `mgso4_status` (`GIVEN \| NONE_GIVEN \| UNKNOWN`) is answer-required, never knowledge-required (`D1`), and never blocks dispatch. | Prompts touching transport or intake explicitly forbid gating on `hs_state` or `mgso4_status = 'UNKNOWN'`. |
| **L-LEASE-CAP** | Separate `version` (`412` on stale) and `lease_epoch` (`409` on lost race). Partial unique index `one_lease` on `offer(referral_id) WHERE status = 'ACCEPTED'` (`I2`). `open_offers` (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) $\le 2$ always (`I12`, `F13`). | Concurrency prompts require running `race200` (`T-C1`) and `open_cap` (`T-F13`). |
| **L-TIMING** | Unified ACK window $A$ with notice rungs at $0$ (SSE/FCM), $A/4$ (Exotel voice with AMD + press-1 gate), and $3A/4$ (dispatcher proxy page). $T_{max} = F \cdot (A + D + \epsilon) \le B$ (`F2`, `F3`, `I13`). Monotone server timestamp via `ts = GREATEST(clock_timestamp(), referral.head_ts)` (`F11`, `I16`). | Boot validator refuses startup if $F \cdot (A + D + \epsilon) > B$ or if a demo profile is loaded with `REAL_DATA=1`. |
| **L-INDEPENDENCE** | **Person A (Lane A)** owns backend, `transitions.yaml`, and Quint spec (`rhp1.qnt`). **Person B (Lane B)** writes the independent Python runtime monitor from §3 prose alone (`F17`), importing zero server code and connecting via read-only DB role `rhp_monitor`. | Separate Antigravity workspaces and separate Gem chat threads (`G1-A/B`, `G2-A/B`, `G3-A/B`). |

---

## 1. Multi-Agent Prompting Topology (The 2-Gem Milestone Validation Workflow)

To eliminate single-model blind spots and copy-paste overhead during the 24-hour build, development is partitioned across two reviewing Gem personas, one implementation agent, and two human-operated lanes:

```
                        ┌──────────────────────────────────────────────────────┐
                        │        HUMAN COURIER (Lane A or Lane B Operator)     │
                        │   Approves SPEC-DEVIATIONs · Enforces H22 Freeze     │
                        └──────────────────────────────────────────────────────┘

  ┌──────────────┐  ① AG-PROMPT   ┌──────────────────┐  ② ONLY WHEN FEATURE/MILESTONE DONE  ┌──────────────┐
  │    GEM 1     │───────────────▶│   ANTIGRAVITY    │─────────────────────────────────────▶│    GEM 2     │
  │  CONDUCTOR   │                │ (Only Code Writer)│   (BUILD REPORT + VALIDATION-REQ)    │  VALIDATOR   │
  └──────────────┘                └──────────────────┘                                      │(Audit+Advers)│
         ▲                                 │                                                └──────────────┘
         │                                 │ (2a) Sub-step only (feature not yet done):            │
         │                                 │      FAST-ADVANCE PACKET (skip Gem 2)                 │
         │                                 ▼                                                       │
         └─────────────────────────────────┴───────────────────────────────────────────────────────┘
                                   ③ PROMPT FOR GEM 1 (DECISION PACKET:
                                     Verdict + Fix List + Attacks + Ledger Delta)
```

### 1.1 Two-Lane Isolation Matrix (`F17` Common-Mode Defence)

| Attribute | Lane A (Person A — Backend & Formal Spec) | Lane B (Person B — Monitor, Clients & Reach) |
|---|---|---|
| **Gem Threads** | `G1-A`, `G2-A` | `G1-B`, `G2-B` |
| **Antigravity Workspace** | `workspace-lane-a` (Branch `lane-a/*`) | `workspace-lane-b-monitor` (isolated) & `workspace-lane-b-clients` |
| **Owned Artifacts** | `db/schema.sql`, `spec/transitions.yaml`, `spec/rhp1.qnt`, `api/`, `witness/`, `scripts/make_scratch.sh` | `monitor/monitor.py`, `pwa/`, `verifier/`, `reach/exotel_ivr.py`, `spec/profiles.json`, `db/seed.sql` |
| **Strict Information Barrier** | Never edits `monitor/monitor.py`. | The `workspace-lane-b-monitor` session is **NEVER** shown `api/`, `spec/transitions.yaml`, or `spec/rhp1.qnt`. It receives only Architecture §3 (Invariants `I1`–`I16` prose) and §7 (`event`, `referral`, `offer`, `deadline` read-only schema). |

---

## 2. Exact System Prompts for All Models (Copy-Paste Ready)

### 2.1 Knowledge Base Upload Checklist (Both Gems)

Before sending any prompt, upload these locked files into the **Knowledge** slot of **Gem 1** and **Gem 2**:
1. `ReferralHandshake_LOCKED_Problem_Statement_v7.md`
2. `ReferralHandshake_v8_LOCKED_Solution.md`
3. `ReferralHandshake_FINAL_LOCKED_Architecture.md`
4. `ReferralHandshake_3Gem_Antigravity_Workflow.md` (updated to 2-Gem Milestone Workflow)
5. `AGENTS.md` and `GEMINI.md`
6. `Master Verification & Test Plan.md`

---

### 2.2 Gem 1 — CONDUCTOR System Instructions

Paste the following block verbatim into **Gem 1's System Instructions**:

```text
You are GEM 1 — CONDUCTOR for ReferralHandshake (Protocol RHP-1, Team MAHA YODHAS, Colossus 3.0 HealthTech Track, 24-hour build, 2 students).
Your uploaded Knowledge files are the LOCKED specification.
Strict Precedence: Problem Statement v7 > Research tagged [V] > Solution v8 > FINAL_LOCKED_Architecture.
Never contradict them. If a behaviour is not specified in the Knowledge files, state "NOT IN SPEC" and ask the user; never invent states, tables, endpoints, or semantics.

YOUR ROLE:
You own the build sequence, step sizing, tier gates (T0 -> T1 -> T2 -> T3), scope cuts, the STATE LEDGER, and every prompt sent to Google Antigravity (the ONLY agent allowed to write product code). You NEVER write product code yourself.

NON-NEGOTIABLE ARCHITECTURAL LOCKS TO ENFORCE IN EVERY PROMPT:
1. Coherence Rule: every component is (a) a contract state/event, (b) an event producer/consumer interface, or (c) a read-only log projection.
2. Locked Stack: Python 3.12, FastAPI, psycopg3, PostgreSQL 16 primary (synchronous_commit=on, READ COMMITTED + explicit SELECT ... FOR UPDATE), React PWA (SSE + Last-Event-ID, 15s heartbeats, pure-JS @noble/curves/ed25519 & @noble/hashes/sha256), Exotel IVR, Mapbox, Toxiproxy, Quint.
3. Banned Tech: NO blockchain, Kafka, Debezium, Redis, Kubernetes, WebSockets, WhatsApp, on-device LLMs, CRDTs for authoritative state, or floats in RFC 8785 JCS JSON.
4. Global Lock Order (F1/I14): referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox. Poller Phase 1 is a single committed UPDATE ... FOR UPDATE SKIP LOCKED; Phase 2 calls apply_command(TIMEOUT). Trigger rhp_require_lock checks GUC rhp.locked_referral.
5. Two Independent Tracks (I3): Handshake and Transport run in parallel. Transport never reads hs_state. mgso4_status (GIVEN|NONE_GIVEN|UNKNOWN) never blocks dispatch.
6. Lease & Cap (I2, I12, F13): version (412) != lease_epoch (409). Partial unique index one_lease. open_offers <= 2 always.
7. Timing Bound (F2, F3, I13): Rungs at 0, A/4, 3A/4. T_max = F * (A + D + eps) <= B. Monotone server_ts = GREATEST(clock_timestamp(), referral.head_ts) (I16).
8. Common-Mode Independence (F17): Lane B monitor prompts must forbid reading server code or transitions.yaml.

EVERY REPLY YOU GENERATE MUST CONTAIN ONLY THESE 3 SECTIONS IN ORDER:
1. Updated === STATE LEDGER v<n> ===
2. Exactly ONE === AG-PROMPT | STEP <id> | LANE <A|B> | LOOP <FULL|FAST> #<n> | RISK <LOW|MED|HIGH> ===
3. One routing instruction line telling the user where to paste the output (e.g., "Paste AG-PROMPT into Antigravity -> then paste its output into Gem 2 on milestone completion, or direct to Gem 1 on sub-step").

AG-PROMPT MANDATORY FIELDS:
- Header: STEP id, LANE A/B, LOOP FULL/FAST, RISK level, loop count #<n>
- GOAL: 1 concise sentence
- SPEC ANCHORS: exact § numbers, Invariant IDs (I1-I16), Closure IDs (F1-F20 / D1-D20), and Test IDs (T-xx)
- INPUT STATE: git branch, last good tag, existing verified modules
- TASKS: numbered, atomic implementation instructions
- ATTACK TESTS FROM LAST RED-TEAM: runnable test specs from Gem 2 (or "None")
- FILES YOU MAY TOUCH: explicit file paths
- FILES YOU MUST NOT TOUCH: explicit protected paths (always protect /spec, and protect /api when prompting Lane B monitor)
- TESTS TO WRITE AND RUN: exact pytest / quint / psql commands
- ACCEPTANCE CRITERIA: measurable numbers/assertions
- STOP CONDITIONS: if spec is ambiguous, a test fails, or a forbidden file needs edits, STOP immediately and report
- REQUIRED OUTPUT FORMAT: (1) BUILD REPORT with raw terminal outputs and full text of HIGH-risk files, followed by (2) Mandatory routing banner (Case A for sub-step, Case B for completed feature/milestone)

DECISION RULES ON RECEIVING A PACKET FROM GEM 2 (OR FAST-ADVANCE FROM ANTIGRAVITY):
- Advance to the next step ONLY if zero S1 defects remain open and all MUST-FIX items have raw terminal proof.
- Convert every Gem 2 ATTACK (A-n) into a mandatory runnable test task in the next AG-PROMPT.
- Maximum 2 fix loops per step. On loop #3 failure, either cut scope in strict order (T3 first, then T2, then T1; T0 is NEVER cut) or output a SPEC-QUESTION for user decision.
- Enforce Code Freeze at Hour 22 (H22): after H22, issue only configuration, rehearsal, and MP4 fallback prompts.
- Keep REAL_DATA=0 always. Never request or emit API keys/secrets. Be terse. Zero conversational filler or praise.
```

---

### 2.3 Gem 2 — MILESTONE VALIDATOR (Merged Spec Auditor & Red-Team Adversary) System Instructions

Paste the following block verbatim into **Gem 2's System Instructions**:

```text
You are GEM 2 — MILESTONE VALIDATOR (Combined Spec Auditor & Red-Team Adversary) for ReferralHandshake (Team MAHA YODHAS, Colossus 3.0, 24-hour build, 2 students). Knowledge files are the LOCKED spec (Problem v7 > Solution v8 > Architecture FINAL). You audit and attack ONLY what is pasted/attached; anything not shown to you is UNVERIFIED, never assumed OK. You NEVER write product code or fixes.

WHEN INVOKED: You are used ONLY when a feature or milestone/gate is completed. You perform both Spec Conformance Auditing and Red-Team Adversarial Validation in a single pass, and output a ready-to-paste DECISION PACKET prompt for Gem 1 (Conductor).

INPUT: a BUILD REPORT + VALIDATION-REQUEST (or AUDIT-REQUEST) from Antigravity covering a completed feature or milestone.

DO, in order:
1. EVIDENCE CHECK: raw test output present? commands shown? any "passes" with no output = FAIL. List what is UNVERIFIED.
2. SPEC CONFORMANCE: for every anchor in the AG-PROMPT, a row: anchor | requirement | what code does (file:line) | MATCH / PARTIAL / MISSING / DEVIATES.
3. INVARIANT SWEEP: for every invariant I1-I16 the feature/milestone touches, name the enforcement mechanism in the code (index, trigger, lock, check) or flag it ABSENT.
4. CODE & ARCHITECTURE REVIEW: lock order (referral > offer > deadline > outbox), apply_command() single write path, transaction boundaries, idempotency position, error paths, REAL_DATA=0, no hard-coded secrets, no banned tech (blockchain, Kafka, Redis, Kubernetes, WhatsApp, on-device LLM, CRDT for authoritative state), Lane B monitor independence (F17: never imports server code), test non-vacuity.
5. TARGETED RED-TEAM & CLAIMS INTEGRITY:
   - Identify the top 3-5 high-impact attack scenarios for this milestone (or FULL sweep at Gates G0-G3): concurrency/races (race200, double timeout, outbox redelivery), crash mid-tx, partition/replay, clock steps, stale/offline commands, PIN/session/SSE authz abuse, PHI leaks, tamper/broken-build isolation.
   - Format each attack: A-n | scenario | targets I#/§ | expected per spec | BREAKS / HOLDS / UNKNOWN + exact mechanism | runnable test spec (inputs, steps, pass condition).
   - Claims & Demo Integrity: flag any simulated/pre-computed metric or violation of "every number shown live is measured live".
6. DEFECT LIST: id D-n, severity S1 blocker (breaks invariant or demo) / S2 major / S3 minor / S4 note, spec reference, expected behavior, evidence required to close.

OUTPUT:
Part A: Concise Milestone Validation Audit (Steps 1-6).
Part B: A single copy-pasteable block titled "=== PROMPT FOR GEM 1 (COPY AND PASTE THIS ENTIRE BLOCK INTO GEM 1) ===" containing the exact "=== DECISION PACKET ===" (VERDICT: ADVANCE / FIX-THEN-ADVANCE / REDO / SPEC-QUESTION, ATTACKS, AUDITOR SELF-CHECK, CLAIMS/DEMO INTEGRITY, FIX LIST [MUST-FIX S1 / SHOULD-FIX S2-S3 / LOG S4], RISK-ACCEPT CANDIDATES, LEDGER DELTA, and explicit instructions for Gem 1's next AG-PROMPT).
```

*(Note: Gem 3 is retired; all adversarial red-teaming, attack test generation, and claims integrity auditing are merged into Gem 2 and executed at milestone/gate boundaries).*

---

### 2.5 Google Antigravity Workspace Rules (`AGENTS.md`)

Place this file at `/AGENTS.md` in the repository root and configure it as the global workspace rule in Google Antigravity:

```markdown
# AGENTS.md — ReferralHandshake (RHP-1) Builder Governance Rules

You are the implementation agent for **ReferralHandshake (Protocol RHP-1)**. You receive instructions exclusively via `=== AG-PROMPT ===` blocks issued by **Gem 1 (CONDUCTOR)**.

## 1. Immutable Authority & File Ownership (`CODEOWNERS` Protection)
1. Specification files in `/spec/` (`ReferralHandshake_LOCKED_Problem_Statement_v7.md`, `ReferralHandshake_v8_LOCKED_Solution.md`, `ReferralHandshake_FINAL_LOCKED_Architecture.md`, `transitions.yaml`, `rhp1.qnt`, `profiles.json`, `conformance_vectors.json`) are **READ-ONLY** unless the current `AG-PROMPT` explicitly lists them under `FILES YOU MAY TOUCH`.
2. **Anti-Reward-Hacking Rule:** You must NEVER weaken a test assertion, modify a conformance vector, drop a database constraint in `db/schema.sql` (outside the isolated `scripts/make_scratch.sh` script for `rhp_scratch_broken`), or edit `monitor/monitor.py` to make a failing test pass.
3. **Common-Mode Isolation (`F17`):**
   - When operating in **Lane A (Server/Spec)**, you must NEVER read or edit `monitor/monitor.py`.
   - When operating in **Lane B (Monitor)**, you must NEVER import, read, or inspect any file inside `api/`, `spec/transitions.yaml`, or `spec/rhp1.qnt`. The monitor is built solely from Architecture §3 prose and the read-only PostgreSQL schema.

## 2. Hard Technical Constraints
1. **Locked Stack:** Python 3.12, FastAPI, psycopg3 (synchronous/connection-pool or async with explicit transactions), PostgreSQL 16 (`synchronous_commit=on`, `READ COMMITTED` isolation + explicit `SELECT ... FOR UPDATE`), Pydantic v2 (`model_config = ConfigDict(extra='forbid')`), React 18 PWA, pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256`.
2. **Banned Technologies:** NEVER use or install blockchain libraries, Kafka, Debezium, Redis, Kubernetes manifests, WebSockets (`ws://` / `socket.io`), WhatsApp SDKs, on-device LLMs, CRDT libraries for contract state, or floating-point numbers inside RFC 8785 JCS canonical JSON payloads.
3. **Single State-Mutation Entrypoint:** Every authoritative contract write (`referral`, `offer`, `offer_resource_confirmation`, `deadline` status/due_at, `event`, `payload_grant`, and `outbox` insert) MUST execute inside `apply_command()` while holding the `referral` row lock and after setting `SELECT set_config('rhp.locked_referral', str(referral_id), true)`.
4. **Global Lock Order (`F1` / `I14`):** Always acquire locks in the strict order:
   `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`.
5. **Synthetic Data & Secrets Posture:** Keep `REAL_DATA=0` in all default environments. Never hardcode API keys, Exotel credentials, or private keys in source files or print them in build reports.

## 3. Execution & Git Tagging Protocol
1. Execute ONLY the numbered tasks in the active `AG-PROMPT`. Touch ONLY the files listed in `FILES YOU MAY TOUCH`.
2. If you encounter a specification ambiguity, an unresolvable test failure, or a requirement to edit a file in `FILES YOU MUST NOT TOUCH`, **STOP IMMEDIATELY** and output a blocker report. Do not improvise workarounds.
3. At the conclusion of every step where tests execute, commit your work on the lane branch and create an annotated git tag: `step-<STEP_ID>-loop<N>` (e.g., `step-E1-loop1`).

## 4. Mandatory Output Format (`BUILD REPORT` + `AUDIT-REQUEST`)
Every response you produce after executing an `AG-PROMPT` MUST end with these two blocks in exact order. Never summarize terminal output—paste the raw stdout/stderr verbatim.

```text
=== BUILD REPORT | STEP <id> | LANE <A|B> | LOOP #<n> ===
1. GIT STATUS & COMMIT: <branch name> | <commit hash> | <tag name>
2. FILES CHANGED (`git diff --stat`):
   <paste raw git diff --stat>
3. HIGH-RISK FILE CONTENTS:
   <paste full file content of every touched file marked HIGH risk, or full unified diff if >300 lines>
4. COMMANDS RUN & RAW TERMINAL OUTPUT:
   <paste exact commands and verbatim stdout/stderr; zero truncation>
5. TEST MATRIX SUMMARY:
   | Test ID / Name | Command | Status (PASS/FAIL) | Measured Latency / Value |
6. NOT DONE / SKIPPED ITEMS: <"None" or explicit list>
7. DEVIATIONS FROM SPEC: <"None" or explicit list>
8. ASSUMPTIONS MADE: <"None" or explicit list>
9. SELF-RATED RISK & TOP 3 FRAGILE POINTS: <1-3 technical areas Gem 2 should scrutinize>

=== AUDIT-REQUEST FOR GEM 2 ===
Step: <id> | Lane: <A|B> | Loop: <FULL|FAST> #<n>
Spec Anchors to Audit Against: <copy from AG-PROMPT>
Measurable Acceptance Criteria: <copy from AG-PROMPT>
Please audit the BUILD REPORT above against every Spec Anchor and Invariant (I1-I16) using your 6-point audit protocol.
```
```

---

## 3. Loop Routing Rules & Risk Classification Matrix

Gem 1 selects the loop path for every step based on the architectural surface touched:

| Loop Type | Routing Path | Target Duration | When to Use |
|---|---|---|---|
| **MILESTONE VALIDATION** | Gem 1 -> Antigravity -> Gem 2 -> Gem 1 | \\text{--}20\\text{ min}$ | Used **ONLY** when a complete Feature or Milestone/Gate (P1–P6, E0–E8, G0–G3) is completed, or when validating an S1 fix. Gem 2 runs combined spec audit and adversarial red-teaming. |
| **SUB-STEP FAST-ADVANCE** | Gem 1 <-> Antigravity | \\text{--}10\\text{ min}$ | Sub-steps within a feature (e.g. drafting schema, scaffolding tests, UI layout, iterative code). Skips Gem 2 entirely until the entire feature/milestone is ready. |
| **SHORT-CIRCUIT** | `Gem 1 -> Antigravity -> Gem 2 -> Gem 1` (Immediate abort) | $5\text{ min}$ | Gem 2 returns `VERDICT: REJECT` because code fails to boot/compile, raw outputs are missing, or forbidden files were touched. |

### 3.1 Surface Risk Classification Table

| Risk Level | Architectural Surfaces & Files | Required Verification |
|---|---|---|
| **HIGH** | `db/schema.sql`, `spec/transitions.yaml`, `spec/rhp1.qnt`, `api/command.py` (`apply_command`), `api/poller.py`, `api/relay.py`, `api/auth.py` (Argon2id/PIN/Session), `api/sse.py` (per-event grant filter), `witness/signer.py`, `verifier/verify.js`, `monitor/monitor.py`, `reach/exotel_ivr.py`, `scripts/make_scratch.sh` (`BROKEN_BUILD` isolation). | **Milestone Validation Loop** at feature completion + full file text in Build Report + Gem 2 red-team attack tests. |
| **MED** | `spec/profiles.json` + $T_{max}$ validator (`api/config.py`), `pwa/` interactive desk/dispatcher components, paper code generator/validator (`api/paper.py`), Mapbox ETA caching adapter (`api/eta.py`), FHIR/XES read-only exporters (`api/export.py`). | **FAST Loop** (upgrade to **FULL** if Gem 2 finds any `S1`/`S2` defect). |
| **LOW** | `db/seed.sql` (`REAL_DATA=0`), `docker-compose.yml` wiring, static styling, MP4 fallback switcher UI, README/documentation files. | **FAST Loop**. |

---

## 4. Canonical Handoff Packet Schemas

### 4.1 The `STATE LEDGER` (Maintained by Gem 1 in Every Turn)

Whenever a Gem chat thread grows long or drifts, start a fresh chat and paste ONLY the latest `STATE LEDGER` plus the active packet:

```text
=== STATE LEDGER v<n> ===
Clock: H<hh.mm> of 24.00 (or Phase P) | Active Lane: <A|B>
Lane A Position: Step <id> (Last good tag: <tag>)
Lane B Position: Step <id> (Last good tag: <tag>)
Tier Gates: G0(T0)[ ]  G1(T1)[ ]  G2(T2)[ ]  G3(Rehearsal)[ ]  H22-FREEZE[ ]
Completed Steps: <comma-separated step IDs + git tags>
Open Defects: <D-id [S1|S2|S3] short description (or "None")>
Pending Attack Tests: <A-id short description (or "None")>
User-Accepted Bounded Risks: <R-id + bound (or "None")>
Approved Spec Deviations: <SD-id (or "None")>
Scope Cuts Executed: <"None" or cut tier items>
Next 3 Queued Steps: <id1, id2, id3>
```

### 4.2 Spec-Deviation Proposal Packet (`Gem 1 -> User`)

If Gem 2 raises `VERDICT: SPEC-QUESTION` or a step fails 3 loops due to an external platform constraint:

```text
=== SPEC-DEVIATION PROPOSAL | SD-<n> | STEP <id> ===
1. TRIGGER: <Exact technical blocker or Gem 2 SPEC-QUESTION>
2. AFFECTED ANCHORS: <Document name, §, Invariant I#, Closure F#>
3. PROPOSED MINIMAL CHANGE: <Exact delta>
4. INVARIANT IMPACT ANALYSIS: <Proof that I1-I16 and Coherence Rule still hold>
5. FALLBACK IF REJECTED: <Cut tier item per T3 -> T2 -> T1 order>
USER ACTION REQUIRED: Reply "APPROVE SD-<n>" or "REJECT SD-<n> (CUT)".
```

---

## 5. Phase P (Pre-Event Spec Artifacts) — Complete Prompt Catalogue

> **Event Rule Guard (`§2`, `§21`):** Confirm with Colossus 3.0 organisers whether pre-event spec files (`P1`–`P6`) are permitted. These steps produce specification data, schemas, formal models, and verification scripts—zero application server or UI code.

---

### 5.1 Step `P1` (Lane A) — `spec/transitions.yaml` & Conformance Vectors

```text
=== AG-PROMPT | STEP P1 | LANE A | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Author the frozen machine-readable state transition table (`spec/transitions.yaml`) and exhaustive conformance test vectors (`spec/conformance_vectors.json`) covering all 14 commands and all 28 real-world scenarios.
SPEC ANCHORS: Architecture §3 (I1-I16), §4 (State Model, Complete Transition Table, v7->RHP-1 mapping F19, Reachability & Exit F6, Arrival Semantics F5, Soft-Open/PAR2/Counter F13), Solution v8 §4.8 (28 Scenarios).
INPUT STATE: branch `lane-a/spec`, clean repository root.
TASKS:
 1. Create `spec/transitions.yaml` defining:
    - `hs_states`: [CREATED, OFFERED, ACKNOWLEDGED, ACCEPTED, COUNTERED, ESCALATED_TO_DISPATCHER, CANCELLED, CLOSED]
    - `offer_states`: [OPEN, ACKED, COUNTERED, SOFT_OPEN, ACCEPTED, DECLINED, TIMED_OUT, SUPERSEDED, ARRIVAL_REJECTED, WITHDRAWN]
    - `open_offer_set`: [OPEN, ACKED, COUNTERED, SOFT_OPEN] (cap <= 2 per I12)
    - `tr_states`: [REQUESTED, DISPATCHED, EN_ROUTE, ARRIVED, HANDED_OVER, TR_CANCELLED]
    - `outcomes`: [ADMITTED_STABLE, ADMITTED_CRITICAL, DELIVERED_AT_RECEIVER, DELIVERED_EN_ROUTE, PATIENT_REFUSED, TRANSPORT_CANCELLED, DETERIORATED_OR_DIED_PRE_HANDOVER, REDIRECTED_ON_ARRIVAL, UNKNOWN_COUNTER_REFERRAL]
    - Exact guard predicates, pre-states, post-states, deadline mutations, lease_epoch increments, grant mutations, and HTTP error codes (403, 409 LEASE_HELD, 409 LATE_ACCEPT_REJECTED, 409 STALE_CONFIRMATION_RECONFIRM_REQUIRED, 409 INVALID_TRANSITION, 409 INVALID_TR, 412 STALE_VERSION_OR_EPOCH, 422 SCHEMA/OUTCOME_REQUIRED) for all 14 commands:
      CREATE, ACK, RESOURCE_CONFIRM, ACCEPT, COUNTER, CONFIRM_COUNTER, DECLINE, TIMEOUT, ARRIVAL_REJECTED, DISPATCHER_ASSIGN, TR_UPDATE, TR_DESTINATION_CHANGE, CANCEL, CLOSE, REVOKE_GRANT.
    - Explicit rule that `TR_UPDATE` and `TR_DESTINATION_CHANGE` NEVER read `hs_state` (I3).
 2. Create `spec/conformance_vectors.json` containing deterministic input->expected-state/event vectors for all 28 scenarios in v8 §4.8 plus `V-STALE-EPOCH` (M1), `V-STALE-CONFIRM` (M6), `V-SOFT-OPEN-WIN`, `V-SOFT-OPEN-LATE-REJECT`, `V-OVERLAP-CAP-2`, and `V-CLOSURE-2X-TIMEOUT`.
 3. Create `scripts/verify_transitions.py` that performs a Breadth-First Search (BFS) over `spec/transitions.yaml` to verify `T-F6` (`reachability_bfs`: every non-terminal state is reachable from CREATED and has a deterministic exit path to CLOSED or CANCELLED) and `T-F19` (`v7_map`: all 12 v7 states map cleanly).
ATTACK TESTS FROM LAST RED-TEAM: None.
FILES YOU MAY TOUCH: `spec/transitions.yaml`, `spec/conformance_vectors.json`, `scripts/verify_transitions.py`.
FILES YOU MUST NOT TOUCH: Any other file.
TESTS TO WRITE AND RUN: `python3 scripts/verify_transitions.py`
ACCEPTANCE (measurable):
 - `verify_transitions.py` exits 0, confirming 8/8 `hs_states` reachable, 8/8 have deterministic terminal exits, `open_offers <= 2` across all reachable states, and all 34 conformance vectors validate against the YAML guards.
STOP IF: Any transition in Architecture §4 is ambiguous.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `spec/transitions.yaml`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

### 5.2 Step `P2` (Lane A) — 24-Table PostgreSQL 16 DDL & Constraint Scan (`ST-3`)

```text
=== AG-PROMPT | STEP P2 | LANE A | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Create the complete 24-table PostgreSQL 16 schema (`db/schema.sql`) and automated constraint/trigger verification script (`scripts/test_ddl.py`) enforcing F1, F4, F9, I1, I2, I4, I5, I7, I9, I11, I12, I14, and I16.
SPEC ANCHORS: Architecture §1 (F1, F4, F9), §3 (I1-I16), §7 (Complete PostgreSQL 16 DDL — all 24 tables, functions, triggers, and 3 DB roles), §23 (ST-3).
INPUT STATE: branch `lane-a/spec`, last good tag `step-P1-loop1`.
TASKS:
 1. Create `db/schema.sql` containing the exact 24 tables from Architecture §7:
    `facility`, `roster`, `facility_capability`, `need_class_requirement`, `catchment_chain`, `device`, `enrollment_ticket`, `session`, `referral`, `offer`, `offer_resource_confirmation`, `deadline`, `event`, `key_version`, `event_secret`, `clinical_payload`, `payload_grant`, `telemetry`, `idempotency`, `inbox`, `outbox`, `rejected_command`, `checkpoint`, `heartbeat`.
 2. Include all partial unique indexes (`one_lease`, `one_active_grant`), deferred FK (`referral_lease_fk`), functions (`rhp_allowed`, `rhp_detail_ok`, `rhp_no_mutate`, `rhp_event_guard`, `rhp_require_lock`, `rhp_i1`, `rhp_chain_guard`), triggers (`event_ao`, `checkpoint_ao`, `rejected_ao`, `event_guard`, `lk_referral`, `lk_offer`, `lk_deadline`, `lk_event`, `lk_grant`, `lk_outbox`, `i1_pending_deadline`, `offer_chain_guard`), and roles (`rhp_app`, `rhp_monitor`, `rhp_witness`) with exact GRANT/REVOKE permissions.
 3. Write `scripts/test_ddl.py` (`T-F4 ddl_load_fk_scan` + `T-F9 detail_check_fuzz` + `T-I14` lock trigger check):
    - Loads `db/schema.sql` into a fresh PostgreSQL 16 database.
    - Queries `information_schema.tables` to assert exactly 24 base tables exist.
    - Verifies `rhp_require_lock` raises `I14_LOCK_NOT_HELD` when inserting into `referral` without `rhp.locked_referral` GUC, and succeeds when GUC is set.
    - Verifies `i1_pending_deadline` raises `I1_NO_PENDING_DEADLINE` at COMMIT if a non-terminal referral has no PENDING deadline.
    - Verifies `one_lease` rejects a second `ACCEPTED` offer on the same referral (`I2`).
    - Verifies `rhp_detail_ok` rejects free-text strings, lowercase strings, floats, and unallowlisted keys across 200 fuzzed JSONB inputs (`T-F9`).
    - Verifies `event_ao` rejects UPDATE/DELETE on `event` even by `rhp_app`.
ATTACK TESTS FROM LAST RED-TEAM: None.
FILES YOU MAY TOUCH: `db/schema.sql`, `scripts/test_ddl.py`.
FILES YOU MUST NOT TOUCH: `spec/transitions.yaml`, `spec/conformance_vectors.json`.
TESTS TO WRITE AND RUN: `pytest -v scripts/test_ddl.py`
ACCEPTANCE (measurable): 24/24 tables created, 0 SQL warnings/errors, all trigger/constraint assertions in `test_ddl.py` pass with raw output pasted.
STOP IF: PostgreSQL 16 rejects any syntax in §7.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `db/schema.sql`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

### 5.3 Step `P3` (Lane A) — Quint Formal Spec (`spec/rhp1.qnt`) & Explicit-State Explorer

```text
=== AG-PROMPT | STEP P3 | LANE A | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Create the Quint control-plane specification (`spec/rhp1.qnt`) and Python explicit-state model checker (`scripts/model_check.py`), verifying safety invariants and vacuity checks, plus Mutation M4.
SPEC ANCHORS: Architecture §12 (Quint control-plane specification, vacuity checks, Mutation M4, transportNeverGated).
INPUT STATE: branch `lane-a/spec`, last good tag `step-P2-loop1`.
TASKS:
 1. Write `spec/rhp1.qnt` matching Architecture §12 verbatim (`FACS = 1.to(3)`, `MAXE = 4`, `safety = I2 and I12 and I1m and IDisp and I13`, `run transportNeverGated`).
 2. Write `scripts/model_check.py` which:
    - Runs Quint CLI (`quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000` and vacuity checks `--invariant "not (hs==\"ACCEPTED\")"`, `"not (hs==\"DISPATCH\")"`, `"not (hs==\"CLOSED\")"`, `"not (off.get(1)==\"SOFT\")"`) if `quint` binary is installed, AND
    - Runs an exhaustive Python BFS state-space explorer over the exact same state machine (`F=3, MAXE=4, par in {True, False}`) verifying 0 violations of `safety` across 100% of reachable states, and verifying that Mutation M4 (removing the open-offer guard so a 3rd offer opens) immediately produces an `I12` counterexample trace.
ATTACK TESTS FROM LAST RED-TEAM: None.
FILES YOU MAY TOUCH: `spec/rhp1.qnt`, `scripts/model_check.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/transitions.yaml`.
TESTS TO WRITE AND RUN: `python3 scripts/model_check.py`
ACCEPTANCE (measurable):
 - Safety invariant holds across all reachable states (0 violations).
 - All 4 vacuity checks fail as required (proving `ACCEPTED`, `DISPATCH`, `CLOSED`, and `SOFT` are reachable).
 - `transportNeverGated` trace succeeds.
 - Mutation M4 trips `I12` (`nOpen(off) > 2`) with a printed minimal counterexample trace.
STOP IF: Any safety invariant fails on the unmutated spec.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `spec/rhp1.qnt`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

### 5.4 Step `P4` (Lane B) — Signed Profiles (`spec/profiles.json`) & $T_{max}$ Validator (`F2`, `F3`, `I13`)

```text
=== AG-PROMPT | STEP P4 | LANE B | LOOP FULL #1 | RISK MED ===
Read AGENTS.md first. You are the builder only.
GOAL: Create the 4 cold-key-signed timing profiles (`spec/profiles.json`) and the startup validator (`api/config.py`) enforcing F2, F3, and I13.
SPEC ANCHORS: Architecture §6 (Unified offer-ACK window, Signed profiles table, T_max derivation F3/I13, `validate(p, REAL_DATA)`), §23 (ST-2).
INPUT STATE: branch `lane-b/spec`, clean repository root.
TASKS:
 1. Generate a deterministic dev/demo cold Ed25519 keypair (store public key in `spec/cold_pubkey.hex`; store dev private key only in `.env.example` / test fixture, never hardcoded as a production secret) and sign the 4 profiles in `spec/profiles.json`:
    - `PILOT_OB_CRITICAL`: A=60000, D=180000, rungs=[0,15000,45000], S=3, delta=5000, V=20000, F=3, eps=3000, C=90000, confirm_ttl=120000, H=7200000, DISPATCH_ACTION=300000, CLOSURE=86400000, B=900000, demo=false, voice=true
    - `PILOT_STANDARD`: A=120000, D=300000, rungs=[0,30000,90000], S=3, delta=10000, V=20000, F=3, eps=3000, C=150000, confirm_ttl=180000, H=7200000, DISPATCH_ACTION=300000, CLOSURE=86400000, B=1500000, demo=false, voice=true
    - `DEMO_FAST`: A=3000, D=4000, rungs=[0,750,2250], S=3, delta=0, V=0, F=3, eps=1000, C=2000, confirm_ttl=10000, H=30000, DISPATCH_ACTION=5000, CLOSURE=20000, B=25000, demo=true, voice=false
    - `DEMO_VOICE`: A=45000, D=20000, rungs=[0,11250,33750], S=1, delta=0, V=20000, F=2, eps=1000, C=10000, confirm_ttl=60000, H=60000, DISPATCH_ACTION=10000, CLOSURE=60000, B=150000, demo=true, voice=true
 2. Implement `api/config.py` with `validate_profile(p, real_data: bool)` checking:
    - `p.F * (p.A + p.D + p.eps) <= p.B` (I13)
    - If `p.voice`: `p.A // 4 + (p.S - 1) * p.delta + p.V <= (3 * p.A) // 4`
    - `p.rungs == [0, p.A // 4, (3 * p.A) // 4]`
    - `not (p.demo and real_data)` (F2 guard)
    - Ed25519 signature verification over RFC 8785 JCS canonical profile bytes + SHA-256 `profile_hash`.
 3. Write `tests/test_profiles.py` (`T-F2 profile_guard`, `T-F3 tmax_validator`, `ST-2`) testing all 4 valid profiles ($729\text{ s} \le 900\text{ s}$, $1269\text{ s} \le 1500\text{ s}$, $24\text{ s} \le 25\text{ s}$, $132\text{ s} \le 150\text{ s}$) and asserting startup refusal on tampered signature, $T_{max} > B$, bad rungs, voice stagger overflow, and `DEMO_FAST` with `REAL_DATA=1`.
ATTACK TESTS FROM LAST RED-TEAM: None.
FILES YOU MAY TOUCH: `spec/profiles.json`, `spec/cold_pubkey.hex`, `api/config.py`, `tests/test_profiles.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/transitions.yaml`, `spec/rhp1.qnt`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_profiles.py`
ACCEPTANCE (measurable): All assertions in `test_profiles.py` pass with verbatim output.
STOP IF: Any profile fails arithmetic validation.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `api/config.py` and `spec/profiles.json`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

### 5.5 Step `P5` (Lane B) — Synthetic Seed Data (`db/seed.sql`, `REAL_DATA=0`)

```text
=== AG-PROMPT | STEP P5 | LANE B | LOOP FAST #1 | RISK LOW ===
Read AGENTS.md first. You are the builder only.
GOAL: Create deterministic synthetic seed data (`db/seed.sql`) representing a Karnataka-style obstetric referral network (`PHC -> CHC -> FRU -> DH -> MC + DISPATCH`).
SPEC ANCHORS: Problem v7 §4, Solution v8 §9, Architecture §0, §7.
INPUT STATE: branch `lane-b/spec`, last good tag `step-P4-loop1`.
TASKS:
 1. Write `db/seed.sql` populating:
    - 6 facilities (`PHC_NANJANGUD`, `CHC_HD_KOTE`, `FRU_HUNSUR`, `DH_MYSURU`, `MC_MMCRI`, `DISPATCH_108_MYS`) with integer coordinates `lat_e5`, `lon_e5`.
    - `need_class_requirement` rows for `OBSTETRIC_EMERGENCY` (`OT`, `BLOOD`, `ANAESTHETIST`, `NICU`), `NEONATAL`, `TRAUMA`, `CARDIAC`, `STROKE`.
    - `facility_capability` rows with valid future `expires_at` timestamps.
    - `catchment_chain` approved chains (length 3) for `PHC_NANJANGUD` -> `[FRU_HUNSUR, DH_MYSURU, MC_MMCRI]`.
    - `roster` slots (`NURSE` slot 1, `CMO` slot 2, `CONSULTANT` slot 3, `CLINICIAN`, `EMT`, `DISPATCHER`, `ADMIN`, `JUDGE_DESK`) with Argon2id hashes for known test PINs (`1234` for desk roles) and synthetic `+9190000000xx` phones.
    - Registered test `device` and `session` rows for integration tests.
 2. Write `tests/test_seed.py` that loads `db/schema.sql` + `db/seed.sql` and verifies 0 constraint violations.
ATTACK TESTS FROM LAST RED-TEAM: None.
FILES YOU MAY TOUCH: `db/seed.sql`, `tests/test_seed.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_seed.py`
ACCEPTANCE (measurable): Seed loads cleanly on top of `db/schema.sql` with 0 errors.
STOP IF: Any FK or CHECK constraint fails.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

## 6. Phase E (At-Event 24-Hour Build) — Complete Prompt Catalogue

### 6.1 Step `E0` (Hours 0–2) — Repo Wiring, Docker Compose & QR Admission Shell

#### Lane A Prompt (`E0-A`)
```text
=== AG-PROMPT | STEP E0-A | LANE A | LOOP FAST #1 | RISK MED ===
Read AGENTS.md first. You are the builder only.
GOAL: Stand up `docker-compose.yml` (PostgreSQL 16 with `synchronous_commit=on` and `log_lock_waits=on`), database connection pool, and `transitions.yaml` loader.
SPEC ANCHORS: Architecture §0, §5, §7, §17.
INPUT STATE: branch `lane-a/e0`, merged Phase P artifacts.
TASKS:
 1. Create `docker-compose.yml` matching Architecture §17 (`pg`, `api`, `poller`, `relay`, `monitor` user 1001, `witness` user 1002, `toxiproxy`, `pwa`, `tunnel`).
 2. Create `api/db.py` configuring `psycopg_pool.ConnectionPool` with `READ COMMITTED` default isolation and healthcheck endpoint `GET /healthz` + `GET /mode` returning active profile, `T_max`, `B`, `REAL_DATA`, and `BROKEN_BUILD` status.
 3. Create `api/transitions_loader.py` loading and validating `spec/transitions.yaml` at startup.
 4. Write `tests/test_boot.py` verifying `/healthz` and `/mode`.
FILES YOU MAY TOUCH: `docker-compose.yml`, `api/__init__.py`, `api/main.py`, `api/db.py`, `api/transitions_loader.py`, `tests/test_boot.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/transitions.yaml`, `monitor/`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_boot.py`
ACCEPTANCE (measurable): `/healthz` returns HTTP 200 with `synchronous_commit="on"`, `T_max <= B`, and `REAL_DATA=0`.
STOP IF: `synchronous_commit` or `log_lock_waits` is off.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

#### Lane B Prompt (`E0-B`)
```text
=== AG-PROMPT | STEP E0-B | LANE B | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Implement Enrollment Ticket redemption, Session management, Rotating single-use QR judge admission (`cap <= 20`), and LAN fallback guard (`F7`, `§9`).
SPEC ANCHORS: Architecture §7 (`enrollment_ticket`, `device`, `session`), §9 (Enrollment F7, Judge admission rotating QR valid 20s rotating every 15s, Turnstile challenge, cap 20, LAN mode fails closed).
INPUT STATE: branch `lane-b/e0`, merged Phase P artifacts.
TASKS:
 1. Implement `api/enrollment.py`:
    - `POST /v1/enrollment/redeem`: verifies single-use `enrollment_ticket` (`token_hash`, `used_at IS NULL`, `expires_at > now()`), registers `device` (`pubkey` 32 bytes), marks ticket used, issues opaque session token in `HttpOnly; Secure; SameSite=Strict` cookie (`token_hash` stored in `session`).
    - `POST /v1/judge/qr-join`: verifies rotating QR `jti` (20s TTL, single-use), verifies Turnstile token (or LAN-mode synthetic-only bypass when `LAN_MODE=1` and `REAL_DATA=0`), enforces active `JUDGE_DESK` session count <= 20 (`429 ADMISSION_CAP_REACHED` on 21st), and pins witness & cold Ed25519 public keys in response.
    - Boot guard: if `LAN_MODE=1` and `REAL_DATA=1`, refuse startup immediately.
 2. Scaffold React PWA (`pwa/`) with QR scanner/join screen and role desk router.
 3. Write `tests/test_enrollment_and_qr.py` testing ticket reuse rejection, 20-desk cap enforcement (21st join gets 429), expired QR rejection, and LAN mode + `REAL_DATA=1` boot refusal.
FILES YOU MAY TOUCH: `api/enrollment.py`, `pwa/src/*`, `tests/test_enrollment_and_qr.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `monitor/*`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_enrollment_and_qr.py`
ACCEPTANCE (measurable): 20 concurrent judge joins succeed (200), 21st returns 429, reused ticket returns 409/403, expired QR returns 401.
STOP IF: Any session token is stored in plaintext in the DB.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `api/enrollment.py`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

### 6.2 Step `E1` (Hours 2–6) — The 10-Step `apply_command()` Pipeline & SSE Per-Event Authz

#### Lane A Prompt (`E1-A`)
```text
=== AG-PROMPT | STEP E1-A | LANE A | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Implement the exact 10-step `apply_command()` pipeline in `api/command.py` and wire `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, and `DECLINE`.
SPEC ANCHORS: Architecture §3 (I1, I2, I4, I5, I6, I7, I8, I9, I11, I12, I14, I15, I16), §4 (Transition Table), §5 (`apply_command()` 10 steps, Global lock order proof F1, Idempotency edge-case table F14, Offline staleness F12/I15), §9 (PIN lockout per session/call_sid F7).
INPUT STATE: branch `lane-a/e1`, last good tag `step-E0-A-loop1`.
TASKS:
 1. Implement `api/jcs.py`: RFC 8785 JCS serializer accepting ONLY dicts, lists, strings, booleans, and integers (raising `TypeError` on any `float`).
 2. Implement `api/command.py` executing the 10 steps in exact order:
    - Step 1 (IDEMPOTENCY, before referral lock): require `Idempotency-Key` (8..80 chars, else `422 MISSING_IDEMPOTENCY_KEY`); compute `request_hash = sha256(jcs(body_for_hash))`; take non-blocking `pg_try_advisory_xact_lock(hashtextextended(f"{roster_id}:{idem_key}", 0))` (else `409 DUPLICATE_IN_FLIGHT`); check `idempotency` table: if `request_hash != h` return `422 KEY_REUSED_DIFFERENT_PAYLOAD`; if `status == 'DONE'` replay stored `(http_status, response)` (including stored 409/412/422 rejections); upsert `IN_FLIGHT`.
    - Step 2 (SESSION): verify active session/device/roster at current time (else `401 SESSION_INVALID`).
    - Step 3 (PIN): for PIN-gated commands (`RESOURCE_CONFIRM`, `ACCEPT`, `COUNTER`, `DECLINE`), check `session.pin_locked_until` (`429 PIN_LOCKED` if active); verify Argon2id PIN; on failure, open a SEPARATE autonomous DB connection to increment `session.pin_failed`, apply backoff (0s, 5s, 30s, then 120s lock on 3rd strike + emit `PIN_LOCKED` outbox page to dispatcher), commit autonomous txn, and finalize main txn with `403 PIN_INVALID`.
    - Step 4 (LOCK REFERRAL FIRST): for `CREATE`, insert initial referral row locked and call `SELECT set_config('rhp.locked_referral', str(r.id), true)`; for existing referrals, `SELECT * FROM referral WHERE id=%s FOR UPDATE`, set `rhp.locked_referral` GUC, compute `ts = GREATEST(clock_timestamp(), r.head_ts)` (I16), and issue `SAVEPOINT sp_cmd`.
    - Step 5 (AUTHORITY & FENCING): verify roster role/facility match and active grant; check `expected_version == r.version` and `expected_epoch == r.lease_epoch` (on mismatch raise `Reject(412, "STALE_VERSION_OR_EPOCH")`).
    - Step 6 (TRANSITION GUARD): lock `offer` rows (`SELECT * FROM offer WHERE referral_id=%s ORDER BY id FOR UPDATE`) then `deadline` rows (`ORDER BY id FOR UPDATE`); evaluate `transitions.yaml` guards.
    - Step 7 (STALENESS / I15): on `ACCEPT`, verify offer status in `('OPEN','ACKED','SOFT_OPEN')` (else `Reject(409, "LATE_ACCEPT_REJECTED")` or `Reject(409, "LEASE_HELD")`), and verify every required capability in `need_class_requirement` has an `offer_resource_confirmation` row with `expires_at > ts` (else `Reject(409, "STALE_CONFIRMATION_RECONFIRM_REQUIRED")`).
    - Step 8 (APPLY EFFECTS): mutate `offer`, `referral.lease_epoch`, `referral.open_offers`, `payload_grant` (revoke superseded/declined grants), and `deadline` rows (`WHERE id=%s AND status='PENDING'`).
    - Step 9 (EVENT & OUTBOX): increment `seq`, compute `hash = sha256(prev_hash + jcs(core))` (`prev_hash = 32*0x00` at seq 1), insert `event`, insert `outbox` rows LAST, update `referral` (`head_seq`, `head_hash`, `head_ts`, `version = version + 1`).
    - Step 10 (FINALIZE): update `idempotency` (`status='DONE'`, `http_status=200`, `response`), commit.
    - `except Reject`: `ROLLBACK TO SAVEPOINT sp_cmd` (retaining referral lock and GUC), insert `rejected_command`, update `idempotency` (`status='DONE'`, `http_status=e.code`, `response=e.reason`), commit.
 3. Expose FastAPI routes in `api/routes.py` with Pydantic `extra='forbid'` schemas.
 4. Write `tests/test_pipeline_e1.py` covering `T-F7 pin_lockout_scope`, `T-F12 offline_stale`, `T-F14 idem_matrix` (all 8 edge cases), `T-I8` stale fencing, and `T-I16` monotone timestamp.
FILES YOU MAY TOUCH: `api/jcs.py`, `api/command.py`, `api/routes.py`, `api/main.py`, `tests/test_pipeline_e1.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `monitor/*`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_pipeline_e1.py`
ACCEPTANCE (measurable): All 8 idempotency edge cases, per-session PIN lockout isolation (rival session unlocked while attacker session locked at strike 3), stale confirmation 409, stale version/epoch 412 (recorded in `rejected_command`), and happy-path `CREATE -> ACK -> RESOURCE_CONFIRM -> ACCEPT` pass.
STOP IF: Any contract write occurs outside `apply_command()`.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `api/command.py` and `api/jcs.py`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

#### Lane B Prompt (`E1-B`)
```text
=== AG-PROMPT | STEP E1-B | LANE B | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Implement the SSE stream hub with per-event `payload_grant` authorization (`F10`, `I10`), 15s heartbeats, `Last-Event-ID` resume, and Receiving Desk PWA UI (priority queue without countdown timers, red `mgso4_status=UNKNOWN` banner).
SPEC ANCHORS: Solution v8 §0.2 (D1), §11 (Goodhart protection: no countdown clocks on receiving desk), Architecture §9 (Stream security F10/I10), §13 (React PWA).
INPUT STATE: branch `lane-b/e1`, last good tag `step-E0-B-loop1`.
TASKS:
 1. Implement `api/sse.py`:
    - Authenticates subscriber via `HttpOnly` session cookie.
    - Supports `Last-Event-ID` header to replay missed events from `event` table.
    - Before emitting ANY frame (and on every 15s heartbeat), queries `payload_grant` for `(referral_id, subscriber.facility_id, revoked_at IS NULL)`.
    - If `payload_grant` is absent or revoked, strips all `clinical_payload` fields from the SSE frame.
    - When `GRANT_REVOKED` occurs (on `DECLINE`, `CANCEL`, `SUPERSEDED`, `TIMED_OUT`, `ARRIVAL_REJECTED`), immediately pushes a `GRANT_REVOKED` control frame causing the PWA client to wipe decrypted clinical DOM state.
 2. Build the Receiving Desk view in `pwa/src/Desk.tsx`:
    - Displays incoming offers in priority order **without countdown clocks** (anti-Goodhart lock).
    - Renders a prominent red verification banner whenever `mgso4_status === 'UNKNOWN'`.
    - Implements one-by-one capability confirmation checkboxes (`RESOURCE_CONFIRM`) + PIN modal for `ACCEPT` / `COUNTER` / `DECLINE`.
    - Shows offline queued actions as `"Pending — Not Confirmed"` and handles `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` with a live reconfirmation modal.
 3. Write `tests/test_sse_revoke.py` (`T-F10 sse_revoke` / `T-I10`) verifying that within 1 relay cycle of `DECLINE` or `SUPERSEDED`, the subscriber receives `GRANT_REVOKED` and zero subsequent clinical frames.
FILES YOU MAY TOUCH: `api/sse.py`, `pwa/src/*`, `tests/test_sse_revoke.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `api/command.py`, `monitor/*`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_sse_revoke.py`
ACCEPTANCE (measurable): `T-F10 sse_revoke` passes; 0 clinical bytes emitted to a facility after `revoked_at` is set; DOM grep of `Desk.tsx` confirms 0 countdown timer components and presence of `mgso4_status === 'UNKNOWN'` red banner.
STOP IF: Clinical payload is cached or sent after grant revocation.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `api/sse.py`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

### 6.3 Step `E2` (Hours 6–9) — Two-Phase Poller, Outbox Relay & Independent Python Monitor (`F1`, `F17`)

#### Lane A Prompt (`E2-A`)
```text
=== AG-PROMPT | STEP E2-A | LANE A | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Implement the stateless two-phase deadline poller (`api/poller.py`), visibility-timeout outbox relay (`api/relay.py`), `TIMEOUT` command semantics (including notice rungs `0`, `A/4`, `3A/4`, `SOFT_OPEN`, and `ADVISORY_PREWARM`), and clock-step monitor (`F11`).
SPEC ANCHORS: Architecture §4 (`TIMEOUT` command, `advance()`, Soft-Open & Overlap rule F13), §5 (Stateless poller two-phase F1, Outbox relay visibility timeout), §6 (Notice ladder rungs F2, Clock analysis F11/I16).
INPUT STATE: branch `lane-a/e2`, last good tag `step-E1-A-loop1`.
TASKS:
 1. Implement `TIMEOUT` inside `api/command.py`:
    - Under the referral lock, re-reads `deadline` (`WHERE id=%s AND status='PENDING'`). If not `PENDING` or `epoch`/`step` mismatch, returns `200 no-op`.
    - Handles `NOTICE_VOICE` (rung `A/4`) and `NOTICE_PROXY` (rung `3A/4`) by emitting `NOTICE_SENT` event and queueing outbox rows (`VOICE` across slots $i=0..S-1$ with stagger $i \cdot \delta$, or `PROXY_PAGE`) if offer is still `OPEN`.
    - Handles `ACK` expiry: if offer is `OPEN` (silent) in `SEQUENTIAL` mode -> transition offer to `SOFT_OPEN` (closing any earlier `k-1` `SOFT_OPEN` offer to `TIMED_OUT` so `open_offers <= 2`) and open next target in `chain`; if `ACKED` -> send `ADVISORY_PREWARM` to next target (not an offer, does not increment `open_offers`).
    - Handles `DECISION` and `COUNTER_CONFIRM` expiry -> `SOFT_OPEN` (SEQ) or `TIMED_OUT` (PAR2) + `advance()` to next target or `ESCALATED_TO_DISPATCHER`.
    - Handles `HANDOVER`, `DISPATCH_ACTION`, and two-stage `CLOSURE` (stage 1 -> `CLOSURE_OVERDUE` + re-arm once; stage 2 -> auto-`CLOSE` with `UNKNOWN_COUNTER_REFERRAL`, `proxy=true`, `actor=system`).
 2. Implement `api/poller.py`:
    - Phase 1: single committed `UPDATE deadline SET claimed_until = clock_timestamp() + interval '5 seconds' WHERE id IN (... LIMIT 50 FOR UPDATE SKIP LOCKED) RETURNING id, referral_id, kind, step, epoch` with NO referral lock held.
    - Phase 2: iterates claimed rows calling `apply_command(..., TimeoutCmd(...), idem_key=f"timeout:{d.id}")`.
    - Updates `heartbeat` (`subject_kind='POLLER'`, `ntp_offset_ms`) every 5s.
 3. Implement `api/relay.py`:
    - Claims up to 20 `outbox` rows (`visible_after <= clock_timestamp() FOR UPDATE SKIP LOCKED`), sets `visible_after = +30s`, `attempts += 1`, dispatches to SSE/FCM/Voice/SMS/Proxy adapters, marks `SENT`, or marks `DEAD` + dispatcher page when `attempts > 8`.
 4. Write `tests/test_poller_and_locks.py` (`T-F1 lock_order_200way`, `T-C6` duplicate timer fire, `T-F11 clock_step`, `T-F13 open_cap`).
FILES YOU MAY TOUCH: `api/command.py`, `api/poller.py`, `api/relay.py`, `tests/test_poller_and_locks.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `monitor/*`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_poller_and_locks.py`
ACCEPTANCE (measurable):
 - 200 concurrent commands + concurrent poller ticks complete with `pg_stat_database.deadlocks` delta == 0 (`T-F1`).
 - Duplicate `timeout:<id>` firing returns 200 no-op with 0 duplicate events (`T-C6`).
 - Backward clock offset preserves monotone `server_ts` (`I16`); `open_offers` never exceeds 2 (`I12`).
STOP IF: Poller holds any `deadline` lock while acquiring a `referral` lock.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `api/poller.py` and `api/relay.py`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

#### Lane B Prompt (`E2-B` — Isolated Monitor Workspace `F17`)
```text
=== AG-PROMPT | STEP E2-B | LANE B (ISOLATED MONITOR WORKSPACE) | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are Person B's isolated monitor builder.
CRITICAL ISOLATION RULE (F17): You must NOT read, import, or inspect any file in `api/`, `spec/transitions.yaml`, or `spec/rhp1.qnt`. Derive all state-folding and invariant logic SOLELY from Architecture §3 (Invariants I1–I16 prose), §7 (read-only schema for `event`, `referral`, `offer`, `deadline`, `checkpoint`, `heartbeat`, `outbox`, `rejected_command`), and §12 (Python independent runtime monitor).
GOAL: Build the independent Python Runtime Monitor (`monitor/monitor.py`) and the Big-Screen Guarantee Arena dashboard (`pwa/src/Arena.tsx`).
SPEC ANCHORS: Architecture §3 (I1–I16), §12 (Python independent runtime monitor, `fold(rows)`, `cycle(dsn)`), §17 (30-second live proof loop).
INPUT STATE: isolated workspace `workspace-lane-b-monitor` with access only to `db/schema.sql` and Architecture §3, §7, §12.
TASKS:
 1. Implement `monitor/monitor.py`:
    - Connects exclusively as PostgreSQL role `rhp_monitor` with `isolation_level = REPEATABLE_READ` and `read_only = True`.
    - Uses a server-side cursor (`name="snap"`) to stream `event` rows ordered by `referral_id, seq` in a single consistent snapshot alongside `referral`, `offer`, `deadline`, and `rejected_command`.
    - Implements its own independent `fold(rows)` function checking:
      * `I1`: every non-terminal referral has $\ge 1$ `PENDING` deadline; no `PENDING` deadline has `clock_timestamp() - due_at > TAU_MS` ($\tau = 2 \text{ poller intervals} + 2000\text{ ms}$) without a `DEADLINE_TIMEOUT` event.
      * `I2`: at most 1 `ACCEPTED` offer per referral; `lease_epoch` strictly increases on every `LEASE_GRANTED`; no `LEASE_GRANTED` when a lease is already active.
      * `I3`: no `rejected_command` for `TR_UPDATE` has a reason code tied to `hs_state`.
      * `I4`: `seq == prev_seq + 1` (gap-free, starts at 1) and `event_id` unique.
      * `I5`: recompute `SHA256(prev_hash + JCS(core))` from genesis `32 * 0x00`; verify terminal referrals (`CLOSED`/`CANCELLED`) have non-null `outcome`.
      * `I6`: every `OFFER_ACCEPTED`, `OFFER_COUNTERED`, `OFFER_DECLINED` has a valid `actor_roster_id` or `proxy=true`.
      * `I7`: every `OFFER_CREATED` with `source='CHAIN'` targets a facility in `referral.chain`.
      * `I8`: no applied event has `epoch < st["epoch"]`.
      * `I9`: a `facility_id` appears at most once in `OFFER_CREATED` per referral.
      * `I11`: every `event.detail` key is in the allowlist and values are bool, int, enum token, or UUID.
      * `I12`: count of open offers (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) $\le 2$ at every step and in `referral.open_offers`.
      * `I16`: `server_ts_us` is non-decreasing (`e.ts >= st["ts"]`).
      * Differential Check: `st["seq"] == r.head_seq`, `st["head"] == r.head_hash`, `st["epoch"] == r.lease_epoch` (`DIFF_HEAD`, `DIFF_EPOCH`).
    - Publishes `/metrics` JSON (per-invariant green counters, violation list, p50/p95 event latency, heartbeat status, active mode banner) and updates `heartbeat(subject_kind='MONITOR')`.
 2. Build `pwa/src/Arena.tsx` displaying the live I1–I16 green/red tiles, violation inspector, measured p50/p95 latency, and flashing red `BROKEN BUILD — SCRATCH DB` banner when `/mode` reports `BROKEN_BUILD=1`.
 3. Write standalone unit tests in `monitor/test_monitor_standalone.py` feeding synthetic good and bad event histories directly into `fold()` to verify each invariant detector trips when violated.
FILES YOU MAY TOUCH: `monitor/monitor.py`, `monitor/test_monitor_standalone.py`, `pwa/src/Arena.tsx`.
FILES YOU MUST NOT TOUCH: `api/*`, `spec/transitions.yaml`, `spec/rhp1.qnt`, `db/schema.sql`.
TESTS TO WRITE AND RUN: `pytest -v monitor/test_monitor_standalone.py`
ACCEPTANCE (measurable):
 - `git grep "from api" monitor/` and `git grep "transitions.yaml" monitor/` return empty (0 matches).
 - `test_monitor_standalone.py` proves `fold()` catches injected violations for `I1`, `I2`, `I4`, `I5`, `I8`, `I9`, `I12`, `I16`, `DIFF_HEAD`, and `DIFF_EPOCH`.
STOP IF: Any server code is imported into `monitor/`.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `monitor/monitor.py`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

### 6.4 Step `E3` (Hours 9–12) — Envelope Encryption, Merkle Checkpoints & Pure-JS Browser Verifier (`F8`)

#### Lane A Prompt (`E3-A`)
```text
=== AG-PROMPT | STEP E3-A | LANE A | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Implement AES-256-GCM / AES-KW envelope encryption + crypto-shredding (`§10`) and the separate-OS-user Ed25519 Merkle checkpoint signer + cold-key `RESTORE` verifier (`F8`, `§11`).
SPEC ANCHORS: Architecture §7 (`key_version`, `event_secret`, `clinical_payload`, `checkpoint`), §10 (Envelope encryption, Crypto-shredding walk-through), §11 (Checkpoints C2SP signed-note style, Merkle inclusion proof, Restore vs tamper F8).
INPUT STATE: branch `lane-a/e3`, last good tag `step-E2-A-loop1`.
TASKS:
 1. Implement `api/crypto.py`:
    - Per-referral 256-bit DEK wrapped via AES-KW under active monthly `kek_epoch` KEK.
    - Encrypts `clinical_payload` (`AAD = referral_id || key_id || schema_ver`) and `event_secret` (`AAD = referral_id || seq || key_id`); stores `secret_hash = sha256(nonce || ciphertext)` in `event.secret_hash` so shredding never invalidates the SHA-256 hash chain.
    - Implements `shred_referral(referral_id)`: deletes `clinical_payload` and `event_secret` rows, sets `key_version.wrapped_dek = NULL, status = 'SHREDDED', shredded_at = clock_timestamp()`, and verifies the hash chain still validates 100%.
 2. Implement `witness/signer.py` (runs as OS user `rhp-sign` / UID 1002, connects as `rhp_witness`):
    - Every 5s takes a `REPEATABLE READ READ ONLY` snapshot of `referral` ordered by `id`.
    - Computes leaf `SHA256(0x00 || referral_id_16B || head_seq_8B_BE || head_hash_32B)`, interior node `SHA256(0x01 || left || right)` (odd node promoted unchanged).
    - Formats C2SP note `rhp1/<deployment>\n<tree_size>\n<root_b64>\n`, signs with witness Ed25519 key, inserts `checkpoint(kind='REGULAR')`, and appends to off-box witness file.
 3. Implement `GET /v1/checkpoints/latest` (`Cache-Control: no-store`), `GET /v1/referrals/{id}/proof` (returns O(log N) Merkle inclusion path + events), and `POST /v1/admin/restore` (verifies offline cold-key Ed25519 signature over `{restore_from_checkpoint_id, restored_at, head_map_hash}` and writes `checkpoint(kind='RESTORE')` + per-referral `RESTORE` events).
 4. Write `tests/test_crypto_and_witness.py` (`T-F8 tamper_vs_restore`, `T-P5` shred verification).
FILES YOU MAY TOUCH: `api/crypto.py`, `witness/signer.py`, `api/routes.py`, `tests/test_crypto_and_witness.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `monitor/*`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_crypto_and_witness.py`
ACCEPTANCE (measurable):
 - Shredding a referral deletes ciphertext and `wrapped_dek` while keeping `event` hash chain 100% valid.
 - Merkle inclusion proof verifies for $N \in \{1, 2, 7, 40\}$ referrals.
 - Unauthenticated head regression is flagged as `TRUNCATED`/`TAMPER`, whereas a cold-key signed `RESTORE` checkpoint validates cleanly (`T-F8`).
STOP IF: Shredding breaks `event` hash verification.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `api/crypto.py` and `witness/signer.py`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

#### Lane B Prompt (`E3-B`)
```text
=== AG-PROMPT | STEP E3-B | LANE B | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Build the pure-JS client-side tamper verifier (`verifier/verify.js` + `pwa/src/Verifier.tsx`) using `@noble/curves/ed25519` and `@noble/hashes/sha256` (working over plain LAN HTTP without `crypto.subtle`).
SPEC ANCHORS: Architecture §0, §11 (Pure-JS verifier 4 steps, exact diagnostic strings), §13 (iOS Safari / LAN HTTP compatibility).
INPUT STATE: branch `lane-b/e3`, last good tag `step-E1-B-loop1`.
TASKS:
 1. Implement `verifier/verify.js` (and bundle into `pwa/src/Verifier.tsx`) using ONLY `@noble/curves/ed25519` and `@noble/hashes/sha256` (zero `window.crypto.subtle` calls):
    - Step 1: Verify checkpoint Ed25519 signature against the pinned witness public key -> else return `"CHECKPOINT_SIG"`.
    - Step 2: Recompute referral event chain from genesis `prev_hash = 32 * 0x00` using RFC 8785 JCS; on mismatch return exact string `"BROKEN referral=<id> seq=<n> kind=PREV|HASH expected=<h1_hex> got=<h2_hex>"`; on gap return `"SEQ_GAP"`.
    - Step 3: Compute leaf `SHA256(0x00 || id_16B || head_seq_8B_BE || head_hash_32B)` and fold Merkle `path`; on mismatch with signed `root_hash` return `"ROOT_MISMATCH"`.
    - Step 4: If live chain `head_seq < checkpoint.head_seq` without a valid cold-key-signed `RESTORE` record, return `"TRUNCATED at seq=<k>"`.
    - Otherwise return `"VERIFIED"`.
 2. Write `tests/test_js_verifier.py` (invoking `node verifier/test_runner.mjs` against real outputs from `witness/signer.py`) testing valid proofs, tampered `detail` at seq 3 (`kind=HASH`), tampered `prev_hash` (`kind=PREV`), deleted middle row (`SEQ_GAP`), forged Merkle root (`ROOT_MISMATCH`), unauthorized truncation (`TRUNCATED`), and cold-key `RESTORE`.
FILES YOU MAY TOUCH: `verifier/verify.js`, `verifier/test_runner.mjs`, `pwa/src/Verifier.tsx`, `tests/test_js_verifier.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `api/*`, `monitor/*`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_js_verifier.py`
ACCEPTANCE (measurable): All 7 verification cases in `test_js_verifier.py` pass and emit the exact diagnostic strings specified in Architecture §11; `grep "subtle" verifier/verify.js` returns 0 matches.
STOP IF: `window.crypto.subtle` is used anywhere.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `verifier/verify.js`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

### 6.5 Step `E4` (Hours 12–14) — 200-Way Race, Mutation Suite (`M1`–`M6`), & Safe `BROKEN_BUILD` (`F20`)

#### Lane A Prompt (`E4-A`)
```text
=== AG-PROMPT | STEP E4-A | LANE A | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Implement the 200-way concurrent `ACCEPT` barrier test (`T-C1 race200`), Toxiproxy fault matrix (`#1`–`#8`), and automated Mutation Test Suite (`M1`–`M6` + `I3` dual-mutation, `T-F17`).
SPEC ANCHORS: Architecture §12 (Six mutation tests F17, 200-way barrier test, Toxiproxy matrix #1-#8), §24 (T0 pass criteria).
INPUT STATE: branch `lane-a/e4`, merged `E3-A` and `E3-B`.
TASKS:
 1. Write `tests/test_race200.py` matching Architecture §12:
    - Creates a `PARALLEL2` referral with 2 open offers (`OFFER[0]`, `OFFER[1]`), pre-confirms required capabilities, synchronizes 200 async HTTP clients on `asyncio.Barrier(200)`, fires 200 simultaneous `POST /v1/offers/{offer_id}/accept` requests.
    - Asserts: `sum(r.status_code == 200) == 1`, all 199 losers return `409` (`LEASE_HELD`), DB has `count(*) == 1` `ACCEPTED` offer, `max(seq) - count(*) == 0` (gap-free), `deadlocks_delta() == 0`, and `monitor.cycle(dsn)` returns `[]` (0 violations).
 2. Write `tests/test_mutations.py` (`T-F17 mutation_suite`) that programmatically toggles each of the 6 mutations in an isolated test transaction / scratch DB and asserts the named detector trips:
    - `M1` (skip `expected_epoch` fencing) -> Monitor & vector `V-STALE-EPOCH` trip `I8`.
    - `M2` (skip `FOR UPDATE` + drop `one_lease` on scratch DB) -> `race200` + Monitor trip `I2`.
    - `M3` (poller holds `deadline` lock then locks `referral`) -> `T-F1` trips deadlock / `I14`.
    - `M4` (remove open-offer cap guard in Quint/model checker) -> `model_check.py` trips `I12`.
    - `M5` (write `prev_hash` as zeros on seq > 1) -> JS Verifier + Monitor trip `I5 kind=PREV`.
    - `M6` (skip confirmation `expires_at` check on `ACCEPT`) -> vector `V-STALE-CONFIRM` + Monitor trip `I15`.
    - `M-I3` (gate `TR_UPDATE` on `hs_state != 'ESCALATED_TO_DISPATCHER'`) -> Monitor trips `I3` and Quint `transportNeverGated` fails.
 3. Write `tests/test_toxiproxy.py` executing the 8 Toxiproxy fault scenarios (`latency_up`, `latency_down`, `bandwidth`, `slow_close`, `timeout`, `reset_peer`, `slicer`, `proxy_down`) and asserting 0 duplicate events and 0 monitor violations.
FILES YOU MAY TOUCH: `tests/test_race200.py`, `tests/test_mutations.py`, `tests/test_toxiproxy.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `monitor/monitor.py`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_race200.py tests/test_mutations.py tests/test_toxiproxy.py`
ACCEPTANCE (measurable): `race200` passes (1 winner, 199 losers, 0 deadlocks, 0 monitor violations); all 7 mutations (`M1`–`M6` + `M-I3`) trip their target checker; all 8 Toxiproxy scenarios pass.
STOP IF: Any mutation fails to trip its detector.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

#### Lane B Prompt (`E4-B`)
```text
=== AG-PROMPT | STEP E4-B | LANE B | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Implement `scripts/make_scratch.sh` and the hard-isolated `BROKEN_BUILD=1` scratch database switch (`F20`, `T-F20 broken_isolation`).
SPEC ANCHORS: Architecture §1 (F20), §12 (Safe BROKEN_BUILD F20), §17 (30-second live proof loop t=12–21s).
INPUT STATE: branch `lane-b/e4`, last good tag `step-E3-B-loop1`.
TASKS:
 1. Create `scripts/make_scratch.sh` which creates database `rhp_scratch_broken` and dedicated role `rhp_scratch_app` (with no permissions on the primary database), loads `db/schema.sql` MINUS the `one_lease` unique index, and loads synthetic seed data.
 2. Implement the `BROKEN_BUILD=1` boot & runtime guard in `api/config.py` and `api/command.py`:
    - When `BROKEN_BUILD=1`:
      * Hard abort with `sys.exit(78)` if `REAL_DATA=1`.
      * Hard abort with `sys.exit(78)` if the database name in `DATABASE_URL` is not `rhp_scratch_broken`.
      * Hard abort with `sys.exit(78)` if the DB credentials can connect to the main `rhp` database.
      * Use a separate scratch witness signing key (never sign real checkpoints).
      * Skip the application-level lease guard and `FOR UPDATE` wait so two concurrent `ACCEPT` calls both succeed on `rhp_scratch_broken`, causing the independent Monitor to turn RED with `I2` within $\le 2\text{ s}$.
 3. Write `tests/test_broken_isolation.py` (`T-F20`) verifying exit code 78 on all 3 safety checks, and verifying that on `rhp_scratch_broken` two concurrent accepts trigger Monitor `I2` red within $\le 2\text{ s}$ and switching back restores Monitor green.
FILES YOU MAY TOUCH: `scripts/make_scratch.sh`, `api/config.py`, `api/command.py`, `tests/test_broken_isolation.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `monitor/monitor.py`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_broken_isolation.py`
ACCEPTANCE (measurable): Exit code 78 proven for `REAL_DATA=1`, wrong DB name, and cross-DB auth; Monitor detects `I2` violation on `rhp_scratch_broken` in $< 2000\text{ ms}$.
STOP IF: `BROKEN_BUILD=1` can ever connect to the primary database.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `scripts/make_scratch.sh` and `tests/test_broken_isolation.py`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

### 6.6 Step `E5` (Hours 14–17) — Counter-Offers, 6 Arrival Cases (`F5`), Closure (`F6`), Transport & Dispatcher Proxy (`T1`)

#### Lane A Prompt (`E5-A`)
```text
=== AG-PROMPT | STEP E5-A | LANE A | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Complete `COUNTER`, `CONFIRM_COUNTER`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`, `TR_UPDATE`, `TR_DESTINATION_CHANGE`, `CANCEL`, `CLOSE`, and `REVOKE_GRANT` in `api/command.py`, covering all 6 arrival cases (`F5`) and all 9 closure outcomes (`F6`).
SPEC ANCHORS: Architecture §4 (Complete transition table, Reachability & Exit F6, Arrival semantics cases a–f F5, Counter arithmetic F13).
INPUT STATE: branch `lane-a/e5`, Gate `G0` passed.
TASKS:
 1. Wire remaining commands in `api/command.py` and `api/routes.py`:
    - `COUNTER`: allowed when offer in `('OPEN','ACKED')` and `counter_round < 2`; increments `counter_round`, sets `counter_mask`, replaces `DECISION` deadline with `COUNTER_CONFIRM` due at `min(C, remaining_D)`.
    - `CONFIRM_COUNTER(confirmed=True|False)`: if `True`, runs `I15` confirmation expiry check and grants lease (or returns `409 LEASE_HELD` if another open offer won first); if `False`, sets offer `DECLINED` and calls `advance()`.
    - Six Arrival Cases (`F5`):
      * (a) Geofence (200m + dwell) emits `ARRIVAL_SUGGESTED` only; human EMT/desk confirms `TR_UPDATE(ARRIVED)`.
      * (b) Arrival at facility with `OPEN`/`ACKED`/`SOFT_OPEN` offer allows immediate `ACCEPT` (subject to `I15`).
      * (c) Unannounced arrival at facility with no offer emits `ARRIVAL_AT_NON_OWNER` + pages dispatcher (never blocks care).
      * (d) En-route `TR_DESTINATION_CHANGE` by crew/dispatcher with mandatory reason enum.
      * (e) Crew refuses redirect advisory -> `TR_DESTINATION_CHANGE(accepted=false)` logged, lease unchanged, dispatcher paged.
      * (f) Ambulance past highway turn-off -> detour ETA shown from cached Matrix; crew decides.
    - `ARRIVAL_REJECTED`: revokes lease, increments `lease_epoch`, revokes grant, calls `advance()`.
    - `DISPATCHER_ASSIGN`: creates offer with `source='DISPATCHER'`, `status='ACCEPTED'`, `proxy=True`, increments `lease_epoch`.
    - `CLOSE` & `CANCEL`: enforces outcome taxonomy (`ADMITTED_STABLE`, `ADMITTED_CRITICAL`, `DELIVERED_AT_RECEIVER` require `tr_state == 'HANDED_OVER'`), revokes grants, schedules crypto-shredding.
 2. Write `tests/test_arrival_and_closure.py` (`T-F5 arrival_cases`, `T-F6`, `T-I3`, `T-C4`) and run all 34 conformance vectors from `spec/conformance_vectors.json` against the live API.
FILES YOU MAY TOUCH: `api/command.py`, `api/routes.py`, `tests/test_arrival_and_closure.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `monitor/monitor.py`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_arrival_and_closure.py`
ACCEPTANCE (measurable): All 6 arrival cases (`a`–`f`), counter vs accept race (`T-C4`), transport independence in every `hs_state` (`T-I3`), and 34/34 conformance vectors pass with 0 monitor violations.
STOP IF: Geofence automatically transitions `tr_state` to `ARRIVED` without human confirmation.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

#### Lane B Prompt (`E5-B`)
```text
=== AG-PROMPT | STEP E5-B | LANE B | LOOP FAST #1 | RISK MED ===
Read AGENTS.md first. You are the builder only.
GOAL: Build the Dispatcher Console (proxy entry, `DISPATCHER_ASSIGN` override with mandatory reason enum, time-scrubber replay) and PWA Ambulance Client (foreground GPS `watchPosition`, manual update fallback, telemetry outbox).
SPEC ANCHORS: Architecture §8 (Dispatcher proxy), §13 (React PWA dispatcher console, ambulance fallback), §14 (Live data feeds TTLs), §24 (T1 pass criteria).
INPUT STATE: branch `lane-b/e5`, Gate `G0` passed.
TASKS:
 1. Implement `POST /v1/telemetry` (deduping by `event_id UNIQUE`, storing integer `lat_e5`, `lon_e5`, `acc_m`, `obs_code`, `obs_val`) and Mapbox Matrix ETA caching adapter (`api/eta.py`, 120s cache TTL, fallback label `"ETA stale"`).
 2. Build `pwa/src/Dispatcher.tsx` (proxy entry setting `proxy=true, proxy_for=<roster_id>`, `DISPATCHER_ASSIGN` modal, and event-log time-scrubber replay that folds events client-side to scrub through any referral's history).
 3. Build `pwa/src/Ambulance.tsx` (GPS `watchPosition`, offline IndexedDB/localStorage outbox queueing telemetry + transport updates with UUIDv7 `event_id` and `Idempotency-Key`, showing `"Last confirmed Ns ago"` when stale > 30s).
 4. Write `tests/test_t1_equivalence.py` running 20 paired trials comparing direct clinician/desk API entry vs dispatcher proxy entry.
FILES YOU MAY TOUCH: `api/eta.py`, `api/routes.py`, `pwa/src/Dispatcher.tsx`, `pwa/src/Ambulance.tsx`, `tests/test_t1_equivalence.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `monitor/monitor.py`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_t1_equivalence.py`
ACCEPTANCE (measurable): 20/20 paired proxy vs direct runs produce identical `hs_state`, `tr_state`, and `event.type` sequences (differing only in `proxy=true`); replay scrubber reproduces exact final state.
STOP IF: Telemetry table accepts free-text strings or floats.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

### 6.7 Step `E6` (Hours 17–20) — Exotel Outbound IVR (Press-1 Gate) & Crockford Base32 Mod-37 Paper Code (`T2`)

```text
=== AG-PROMPT | STEP E6 | LANE B (WITH LANE A REVIEW) | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. You are the builder only.
GOAL: Implement the Exotel outbound IVR webhook handler (`reach/exotel_ivr.py` with AMD + mandatory press-1 gate, 2s webhook budget, `inbox` dedupe, per-`call_sid` PIN lockout) and the 9-character Crockford Base32 + mod-37 paper code generator/validator (`api/paper.py`).
SPEC ANCHORS: Architecture §8 (Outbound-only Exotel IVR 5 rules, DLT SMS static template, Paper code 8 Crockford Base32 + 1 mod-37 check symbol), §18 (I5 voicemail ACK, N5 webhook dedupe, N6 webhook budget), §24 (T2 pass criteria).
INPUT STATE: branch `lane-b/e6`, Gate `G1` passed.
TASKS:
 1. Implement `api/paper.py`:
    - Encodes 40-bit integer $N$ into 8 Crockford Base32 characters (`0123456789ABCDEFGHJKMNPQRSTVWXYZ`) + 1 check character from the 37-symbol alphabet (`0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U`) equal to $N \bmod 37$.
    - Validates any 9-character input (normalizing `I/L->1`, `O->0`), rejecting single-symbol substitutions and adjacent transpositions before hitting the database; rate-limits `POST /v1/paper/lookup` to 10/min per session.
 2. Implement `reach/exotel_ivr.py`:
    - Step 1 (Call Connect): checks AMD status; plays prompt `"Press 1 to hear an emergency referral"`. Voicemail, silence, or machine verdict -> 0 ACKs recorded, call marked `UNANSWERED`.
    - Step 2 (Keypress `1`): deduplicates webhook via `INSERT INTO inbox(source, external_id, payload_sha256) ON CONFLICT DO NOTHING`; calls `apply_command(ACK, channel='VOICE')` with a strict 1.5s execution budget (overall webhook response $\le 2.0\text{ s}$). Spoken confirmation plays ONLY after transaction commits; if budget exceeded, plays `"Please hold"` and re-polls on next callback.
    - Step 3 (Decision + PIN): plays pre-recorded Kannada/Hindi/English de-identified summary (facility code, need class, ETA — NEVER patient name). Parses DTMF (`1` accept, `2` counter, `3` decline, `9` repeat) + PIN terminated by `#` (`%23`). Lockout is scoped to `session.call_sid` (3 failures -> hang up + page dispatcher).
 3. Implement DLT SMS adapter stub enforcing static template `"RHP alert: new referral. Open {#var#}"` with variable $\le 30$ chars and zero clinical text (`T-P2`).
 4. Write `tests/test_reach_t2.py` testing:
    - 20/20 voice ACKs recorded only after commit; 5/5 voicemail calls yield 0 ACKs (`T-F7`).
    - Duplicate Exotel webhook replay produces 1 effect (`T-N5`); webhook p95 latency $\le 2.0\text{ s}$.
    - 1,000 single-symbol mutations and 1,000 adjacent transpositions of valid paper codes are 100% rejected.
FILES YOU MAY TOUCH: `api/paper.py`, `reach/exotel_ivr.py`, `reach/sms.py`, `api/routes.py`, `tests/test_reach_t2.py`.
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `monitor/monitor.py`.
TESTS TO WRITE AND RUN: `pytest -v tests/test_reach_t2.py`
ACCEPTANCE (measurable): 1,000/1,000 mutated paper codes rejected (100%); 5/5 voicemail calls produce 0 ACKs; 20/20 committed voice ACKs succeed with p95 $< 2000\text{ ms}$; SMS lint confirms variable $\le 30$ chars and 0 PHI.
STOP IF: Any clinical text or patient name is placed in SMS or TTS prompts.
WHEN DONE, OUTPUT: (1) BUILD REPORT with raw output and full text of `reach/exotel_ivr.py` and `api/paper.py`, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

## 7. Tier Gate Verification Prompts (`G0`–`G3`)

At Hours 14 (`G0`), 17 (`G1`), 20 (`G2`), and 22 (`G3`), Gem 1 issues a **Gate Verification Prompt** in **Milestone Validation Loop** mode with **Gem 2 executing full adversarial red-team and spec audit validation**:

```text
=== AG-PROMPT | GATE <G0|G1|G2|G3> | LANE A+B | LOOP FULL #1 | RISK HIGH ===
Read AGENTS.md first. This is a mandatory Tier Gate Verification run against Architecture §24 and §23 (ST-1..ST-5).
GOAL: Execute the complete automated gate verification suite and output raw, unedited measurements for every criterion in Architecture §24.
TASKS:
 1. Run `scripts/run_gate_checks.sh <G0|G1|G2|G3>` which executes:
    - `ST-1` (`T-F1`): 200-way lock order & poller concurrency test (`deadlocks_delta == 0`).
    - `ST-2` (`T-F2`, `T-F3`): Profile signature, $T_{max} \le B$ arithmetic, and `REAL_DATA=0` guard check.
    - `ST-3` (`T-F4`): 24-table DDL constraint and `rhp_require_lock` trigger scan.
    - `ST-4` (`T-F14`): 8-case idempotency edge-case matrix.
    - `ST-5`: Forbidden-claims & banned-tech repository grep scan (asserting 0 occurrences of forbidden terms from §19 outside documentation tables, and 0 banned imports).
    - `T-C1 race200`: 200 concurrent accepts -> 1 HTTP 200, 199 HTTP 409, 1 ACCEPTED row, 0 seq gaps.
    - `T-F17`: Mutation suite `M1`–`M6` + `M-I3` (all 7 trip their detectors).
    - `T-F20`: `BROKEN_BUILD=1` turns monitor RED (`I2`) in $\le 2\text{ s}$ on `rhp_scratch_broken` and GREEN on switch-back.
    - `DEMO_FAST` full silence-to-dispatcher escalation timer run (measured elapsed time must be $\le 25.0\text{ s}$).
    - 10-minute Hypothesis randomized stateful test run (`RuleBasedStateMachine` + Toxiproxy faults) with Monitor polling continuously (must report 0 violations).
    - (If G1+): 20 paired proxy vs direct equivalence runs + replay check.
    - (If G2+): 20 voice ACK commit tests, 5 voicemail rejection tests, 1,000 mutated paper code rejections.
    - (If G3): 3 consecutive rehearsals of the 30-second live proof loop (`t=0..30s`, Architecture §17) with measured timestamps and MP4 fallback clips verified.
FILES YOU MAY TOUCH: `scripts/run_gate_checks.sh` (read-only execution of all app/spec/monitor files).
FILES YOU MUST NOT TOUCH: `db/schema.sql`, `spec/*`, `api/*`, `monitor/*`.
ACCEPTANCE (measurable): 100% of criteria for the target tier in Architecture §24 pass with raw console logs and measured latencies pasted.
WHEN DONE, OUTPUT: (1) BUILD REPORT with verbatim terminal outputs, (2) === AUDIT-REQUEST FOR GEM 2 ===.
```

---

## 8. Runtime AI Prompting Guide — Layer L6 (`T3_EXTRAS`) Intake Accelerator

> **Architectural Posture (`§16` Architecture, `§8` Solution v8):** The AI Intake Accelerator sits behind feature flag `T3_EXTRAS`, is **off by default**, is **never on the critical path**, uses **synthetic data only (`REAL_DATA=0`)**, and is built only if Gates `G0`–`G2` are green.

### 8.1 Hard Safety Locks on Runtime VLM / ASR / LLM Prompting

1. **Cognitive Forcing Function (`423 ANCHOR_REQUIRED`):** The backend endpoint `POST /v1/intake/draft` MUST refuse to invoke the model or return a draft (`HTTP 423 ANCHOR_REQUIRED`) until the clinician has manually committed both `need_class` and `mgso4_status` (`GIVEN | NONE_GIVEN | UNKNOWN`).
2. **No Confidence Scores & No Explanations (`R08` `[V]`):** Empirical research verified that displaying AI explanations increased clinician commission errors from $10\%$ to $21\%$ `[V]`, and LLM self-reported confidence is poorly calibrated `[V]`. Therefore:
   - The system prompt and Pydantic output schema MUST forbid `confidence`, `probability`, `reasoning`, `explanation`, or `rationale` fields.
   - Any model response containing extra keys is rejected by Pydantic `extra='forbid'`.
3. **Quarantined Unverified Draft + Mandatory Human Re-Entry:** Every field extracted by the model is tagged `verified: false` in client state. Critical fields (`systolic_bp`, `diastolic_bp`, `mgso4_dose_g`, `fetal_heart_rate_bpm`, `hemoglobin_g_dl`) cannot be one-click accepted; the UI forces manual keystroke confirmation, plus a $3\text{ s}$ fast-approve speed bump on AI drafts only.
4. **Never Block Care (`D1`, `I3`):** If the model fails, times out ($> 3\text{ s}$), returns malformed JSON, or is disabled (`T3_EXTRAS=0`), manual structured entry proceeds immediately with zero delay.

---

### 8.2 Exact Production System Prompt for the `T3_EXTRAS` Intake Extractor

When `T3_EXTRAS=1` and anchor fields (`need_class`, `mgso4_status`) have been committed by the clinician, `api/intake_ai.py` calls the configured cloud VLM/LLM API (with zero-retention parameters and synthetic-only guard `REAL_DATA=0`) using this exact system prompt:

```text
You are a strictly constrained clinical slip parser for emergency inter-facility referrals (ISBAR + Dakshata pre-referral checklist).
Input is a synthetic clinical note or OCR/ASR transcript of an emergency referral slip.

STRICT EXTRACTION RULES:
1. Output ONLY a single valid JSON object matching the exact schema below. Do NOT wrap in markdown code fences. Do NOT include any prose before or after the JSON object.
2. NEVER output confidence scores, probabilities, explanations, rationales, or clinical advice.
3. NEVER invent, infer, or extrapolate missing values. If a value is illegible, ambiguous, or not explicitly stated in the input text/image, set its value to `null` (or `"UNKNOWN"` for enum fields that support it).
4. Use ONLY integers for numeric measurements (convert decimals to scaled integers as specified in the field name, e.g., `hemoglobin_g_dl_x10`: 8.5 g/dL -> `85`, `mgso4_loading_dose_g`: 14 g -> `14`). Floating-point numbers are strictly forbidden.
5. Map clinical reasons and required capabilities ONLY to the allowed uppercase enum tokens:
   - `capabilities_needed`: subset of `["OT", "BLOOD", "ANAESTHETIST", "PAEDIATRICIAN", "NICU"]`
   - `indication_code`: one of `["SEVERE_PREECLAMPSIA", "ECLAMPSIA", "PPH", "APH", "OBSTRUCTED_LABOUR", "FETAL_DISTRESS", "SEPSIS", "RUPTURED_UTERUS", "OTHER_OBSTETRIC"]`
   - `mgso4_extracted_status`: one of `["GIVEN", "NONE_GIVEN", "UNKNOWN"]`
   - `oxytocin_status`: one of `["GIVEN", "NONE_GIVEN", "UNKNOWN"]`

REQUIRED JSON OUTPUT SCHEMA (no extra keys allowed):
{
  "indication_code": "SEVERE_PREECLAMPSIA" | "ECLAMPSIA" | "PPH" | "APH" | "OBSTRUCTED_LABOUR" | "FETAL_DISTRESS" | "SEPSIS" | "RUPTURED_UTERUS" | "OTHER_OBSTETRIC" | null,
  "capabilities_needed": ["OT", "BLOOD", "ANAESTHETIST", "PAEDIATRICIAN", "NICU"],
  "systolic_bp_mmhg": int | null,
  "diastolic_bp_mmhg": int | null,
  "pulse_bpm": int | null,
  "spo2_pct": int | null,
  "fetal_heart_rate_bpm": int | null,
  "hemoglobin_g_dl_x10": int | null,
  "gestational_age_weeks": int | null,
  "mgso4_extracted_status": "GIVEN" | "NONE_GIVEN" | "UNKNOWN",
  "mgso4_loading_dose_g": int | null,
  "mgso4_Administered_hhmm": "HHMM" | null,
  "oxytocin_status": "GIVEN" | "NONE_GIVEN" | "UNKNOWN",
  "clinical_summary_short": "string (max 160 ASCII chars, de-identified, no patient name/phone/ABHA)"
}
```

### 8.3 Pydantic Validation & Anchor-Conflict Check (`api/intake_ai.py`)

```python
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

class IntakeDraftSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    indication_code: Optional[Literal[
        "SEVERE_PREECLAMPSIA", "ECLAMPSIA", "PPH", "APH",
        "OBSTRUCTED_LABOUR", "FETAL_DISTRESS", "SEPSIS",
        "RUPTURED_UTERUS", "OTHER_OBSTETRIC"
    ]] = None
    capabilities_needed: list[Literal["OT", "BLOOD", "ANAESTHETIST", "PAEDIATRICIAN", "NICU"]] = Field(default_factory=list)
    systolic_bp_mmhg: Optional[int] = Field(default=None, ge=30, le=300)
    diastolic_bp_mmhg: Optional[int] = Field(default=None, ge=20, le=200)
    pulse_bpm: Optional[int] = Field(default=None, ge=20, le=260)
    spo2_pct: Optional[int] = Field(default=None, ge=30, le=100)
    fetal_heart_rate_bpm: Optional[int] = Field(default=None, ge=40, le=240)
    hemoglobin_g_dl_x10: Optional[int] = Field(default=None, ge=10, le=220)
    gestational_age_weeks: Optional[int] = Field(default=None, ge=4, le=45)
    mgso4_extracted_status: Literal["GIVEN", "NONE_GIVEN", "UNKNOWN"] = "UNKNOWN"
    mgso4_loading_dose_g: Optional[int] = Field(default=None, ge=0, le=30)
    mgso4_administered_hhmm: Optional[str] = Field(default=None, pattern=r"^[0-2][0-9][0-5][0-9]$")
    oxytocin_status: Literal["GIVEN", "NONE_GIVEN", "UNKNOWN"] = "UNKNOWN"
    clinical_summary_short: str = Field(default="", max_length=160)
```

- **Anchor Conflict Rule:** If the clinician's pre-committed `mgso4_status` anchor (e.g., `NONE_GIVEN`) disagrees with the model's `mgso4_extracted_status` (e.g., `GIVEN`), the server NEVER overwrites the clinician's anchor; it sets `anchor_conflict = True` on the response so the UI highlights both for explicit resolution.

### 8.4 20-Slip Seeded-Error Gate Prompt (`T-A1`, `T-A2`)

Before `T3_EXTRAS` may be enabled in any demo, run `tests/test_ai_seeded_gate.py`:
- **Dataset:** 20 synthetic obstetric referral slips where $30\%$ ($6$ slips) contain seeded fatal extraction errors (e.g., inverted $\text{MgSO}_4$ status `GIVEN` vs `NONE_GIVEN`, hallucinated normal BP $120/80\text{ mmHg}$ on an eclamptic patient with $190/120\text{ mmHg}$, or omitted `BLOOD` requirement in severe PPH).
- **Automated Gate Assertions:**
  1. Calling `POST /v1/intake/draft` without committed `need_class` and `mgso4_status` returns `HTTP 423 ANCHOR_REQUIRED` $100\%$ of the time (`T-A2`).
  2. Attempting to submit `CREATE` using an AI draft where critical fields have `reentered_by_human == False` returns `HTTP 422 UNVERIFIED_AI_CRITICAL_FIELD`.
  3. Across the internal A/B usability harness on the 20 slips, the critical-error rubber-stamp rate must be $\le 5\%$ and the silent-omission rate must be $\le 1\%$ (`T-A1`).

---

## 9. Invariant (`I1`–`I16`) & Closure (`F1`–`F20`) Prompt Traceability Matrix

Gem 1 and Gem 2 use this lookup table on every turn to verify that no prompt or code change regresses a locked invariant or closure:

| Invariant / Closure | Architectural Requirement | Prompt Step(s) | Mandatory Automated Test |
|---|---|---|---|
| **I1** (Liveness: No silent referral) | Non-terminal referral has $\ge 1$ `PENDING` deadline; overdue acted on within $\tau$. | `P2`, `E1-A`, `E2-A`, `E2-B` | `T-I1` (trigger `i1_pending_deadline` + monitor overdue query) |
| **I2** (Safety: Single owner lease) | $\le 1$ `ACCEPTED` offer (`one_lease`); `lease_epoch` strictly increases. | `P2`, `P3`, `E1-A`, `E2-B`, `E4-A` | `T-C1 race200` + `M2` |
| **I3** (Safety: Never block care) | `TR_UPDATE` accepted in every non-terminal `hs_state`; `mgso4_status` never blocks. | `P1`, `P3`, `E5-A` | `T-I3` + `M-I3` (`transportNeverGated`) |
| **I4** (Safety: Exactly once) | `idempotency` PK + `event_id UNIQUE` + gap-free `seq` (`rhp_event_guard`). | `P2`, `E1-A`, `E2-B` | `T-F14 idem_matrix` (8 cases) |
| **I5** (Safety: Chain integrity) | `SHA256(prev_hash \|\| JCS(core))`, append-only triggers, terminal requires `outcome`. | `P2`, `E1-A`, `E3-A`, `E3-B` | `T-F8 tamper_vs_restore` + `M5` |
| **I6** (Safety: Roster authority) | Rostered role, registered device/number, Argon2id PIN, or flagged `proxy=true`. | `E0-B`, `E1-A`, `E6` | `T-I6` + `T-F7 pin_lockout_scope` |
| **I7** (Safety: Approved chain) | `source='CHAIN'` target $\in$ `referral.chain` (`offer_chain_guard`). | `P2`, `E1-A`, `E2-B` | `T-I7` |
| **I8** (Safety: Stale fencing) | Stale `expected_version`/`expected_epoch` rejected (`412`) + logged in `rejected_command`. | `E1-A`, `E2-B`, `E4-A` | `T-I8` + `M1` (`V-STALE-EPOCH`) |
| **I9** (Safety: No referral loops) | `UNIQUE(referral_id, facility_id)` on `offer`. | `P2`, `E1-A`, `E2-B` | `T-I9` |
| **I10** (Safety: Stream grant authz) | Clinical frames only to active `payload_grant`; `GRANT_REVOKED` frame on revoke. | `E1-B` | `T-F10 sse_revoke` |
| **I11** (Safety: PHI-free detail) | `rhp_detail_ok` allowlist; booleans, $\le 12$-digit ints, uppercase enums, UUIDs only. | `P2`, `E1-A`, `E2-B` | `T-F9 detail_check_fuzz` |
| **I12** (Safety: Open offer cap) | `open_offers` (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) $\le 2$ always. | `P1`, `P2`, `P3`, `E2-A` | `T-F13 open_cap` + `M4` |
| **I13** (Safety: Bounded escalation) | $T_{max} = F \cdot (A + D + \epsilon) \le B$ verified at startup and `/healthz`. | `P4`, `E0-A` | `T-F3 tmax_validator` + `ST-2` |
| **I14** (Safety: Referral lock held) | Global lock order; `rhp_require_lock` checks `rhp.locked_referral` GUC. | `P2`, `E1-A`, `E2-A`, `E4-A` | `T-F1 lock_order_200way` + `M3` |
| **I15** (Safety: Live confirmation) | No lease granted if any required `offer_resource_confirmation.expires_at <= ts`. | `E1-A`, `E4-A` | `T-F12 offline_stale` + `M6` (`V-STALE-CONFIRM`) |
| **I16** (Safety: Monotone clock) | `ts = GREATEST(clock_timestamp(), referral.head_ts)` under referral lock. | `P2`, `E1-A`, `E2-A` | `T-F11 clock_step` |

---

## 10. Claims Discipline Linter (`ST-5`) & Context Recovery Runbook

### 10.1 Automated Forbidden-Claims Scanner (`ST-5`)

Every Gate prompt (`G0`–`G3`) runs the following check across all UI templates, API payloads, slide exports, and README files (excluding §19 of the specification where forbidden phrases are quoted as negative examples):

```bash
#!/usr/bin/env bash
set -euo pipefail
FORBIDDEN_REGEX="mathematically proven|mathematically guaranteed|mathematically impenetrable|bullet-proof|bulletproof|airtight|zero loopholes|zero silent drops|immutable log|ABDM compliant|BSA certified|lives saved|deaths prevented|eliminates ping-pong|production ready"

if git grep -iE "$FORBIDDEN_REGEX" -- api/ pwa/ monitor/ witness/ verifier/ reach/ README.md; then
  echo "ST-5 FAIL: Forbidden overclaim detected!"
  exit 1
fi
echo "ST-5 PASS: Zero forbidden claims found."
```

### 10.2 Context Recovery & Emergency Troubleshooting Runbook

| Failure Scenario During 24h Build | Immediate Recovery Protocol |
|---|---|
| **Gem chat context becomes long, slow, or hallucinates section numbers** | Open a brand-new Gem chat (Knowledge files are already attached). Paste **only**: `"Resume from this STATE LEDGER. Cite exact sections from your Knowledge files or say NOT IN SPEC."` + the latest `=== STATE LEDGER v<n> ===` + the current packet. |
| **Antigravity modifies a forbidden file or improvises around a failing test** | Gem 2 issues `VERDICT: REJECT`. Run `git reset --hard <last-good-tag>` in the terminal, then SHORT-CIRCUIT to Gem 1 to split the prompt into smaller atomic tasks. |
| **A step fails 2 fix loops (Loop #3 fails)** | Gem 1 triggers the **2-Loop Rule**: if the feature belongs to `T3`, `T2`, or `T1`, cut or stub it per the locked cut order (`T3 -> T2 -> T1`) and log in the `STATE LEDGER`. If it is in `T0`, Gem 1 outputs a `SPEC-DEVIATION PROPOSAL` for immediate human decision. |
| **Hour 22 (`H22`) is reached** | **Hard Code Freeze.** Gem 1 refuses to emit any code-modifying `AG-PROMPT`. Only configuration profile selection, rehearsal runs of the 30-second proof loop, and MP4 fallback verification are allowed during Hours 22–24. |