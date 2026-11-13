# ReferralHandshake — 2-Gem + Antigravity Milestone Build Workflow

**Team:** MAHA YODHAS · **Event:** Colossus 3.0, 13–14 Nov 2026, Bengaluru (24 h build, 2 students)
**Spec set (locked):** Problem Statement v7 > Solution v8 > FINAL_LOCKED_Architecture (precedence in that order)
**Builder:** Google Antigravity (the ONLY thing that writes product code) · **Reviewers:** 2 Gemini Gems (Gem 1 Conductor + Gem 2 Milestone Validator)

---

## 0. Why the 2-Gem Milestone Workflow

Running a 3-Gem ring on every small task burns hours in copy-paste overhead during a 24-hour hackathon. The **2-Gem Milestone Workflow** preserves 100% of the verification rigor while cutting orchestration time in half:

| # | Core Principle | Why It Works Under 24h Pressure |
|---|---|---|
| 1 | **Gem 1 (CONDUCTOR) is unchanged.** | Plans feature/milestone steps, maintains the `STATE LEDGER`, issues `AG-PROMPT`s, and accepts standard `DECISION PACKET` inputs. |
| 2 | **Gem 2 (MILESTONE VALIDATOR) merges Auditor + Adversary.** | One Gem performs both line-by-line Spec Conformance Auditing AND High-Impact Red-Team Attack + Claims Integrity validation in a single pass. Gem 3 is eliminated. |
| 3 | **Gem 2 is invoked ONLY when a Feature or Milestone/Gate is completed.** | In-progress sub-steps never stop for external Gem auditing. Antigravity explicitly alerts you to go to Gem 2 **only** when a feature or milestone (`P1–P6`, `E0–E8`, `G0–G3`) is complete. |
| 4 | **Gem 2 outputs the exact prompt (`DECISION PACKET`) for Gem 1.** | Gem 2 ends every validation with a ready-to-paste `DECISION PACKET` block formatted directly for Gem 1, so Gem 1 requires zero instruction edits. |
| 5 | **Evidence-based reports remain mandatory.** | Raw command and test outputs must be pasted in every Milestone `BUILD REPORT`. "Tests pass" with no raw output = automatic FAIL. |

---

## 1. Roles (Who Owns What, Who Must Never Do What)

| | **Gem 1 — CONDUCTOR (Unchanged)** | **Antigravity — BUILDER** | **Gem 2 — MILESTONE VALIDATOR (Auditor + Red-Team)** |
|---|---|---|---|
| **Owns** | Build plan, milestone/step order, tier gates, cut decisions, `AG-PROMPT`s, `STATE LEDGER` | Writing product code & tests, running verification suites, committing/tagging, explicitly telling the user whether to go to Gem 1 (in-progress) or Gem 2 (feature/milestone completed) | **Milestone-only validation:** Spec conformance, invariant sweep (`I1–I16`), code review, high-impact red-team attack tests, claims integrity, and generating the `DECISION PACKET` prompt for Gem 1 |
| **Input** | `DECISION PACKET` prompt from Gem 2 (after a completed feature/milestone) or `FAST-ADVANCE PACKET` (for sub-steps) | `AG-PROMPT` from Gem 1 | `BUILD REPORT + VALIDATION-REQUEST` from Antigravity (**ONLY when a feature or milestone is completed**) |
| **Output** | `AG-PROMPT` (to Antigravity) | Code + Tests + `BUILD REPORT` + Explicit routing banner (to Gem 2 on feature/milestone completion, or straight to Gem 1 on sub-step) | Milestone Validation Audit + Ready-to-paste `DECISION PACKET` prompt (to Gem 1) |
| **Never does** | Write product code. Accept a milestone with open S1 defects. Change the spec silently. | Decide architecture. Improvise on ambiguous specs. Send the user to Gem 2 before a feature/milestone is finished. | Write fixes or product code. Validate half-built micro-steps. Approve without raw test output. |
| **Mindset** | "What is the next complete feature/milestone step that moves a gate?" | "Build the complete feature cleanly, prove it with raw test output, and route the user accurately." | "Does this completed feature/milestone match the spec line by line with proof, and how can I break it on stage?" |

---

## 2. The 2-Gem Ring & Routing Rules

### 2.0 Half-Module Execution Cadence (1 Prompt = 1 Half-Module)
- **Half-Module Granularity (`M1-A`, `M1-B` ... `M12-A`, `M12-B`):** Every module (`MODULE 1` through `MODULE 12` in `BUILD_PLAN.md`) is divided into two executable Half-Modules: **Part A** and **Part B** (24 Half-Module Prompts in total).
- **1 AG-PROMPT = 1 Half-Module:** Each prompt from Gem 1 instructs Antigravity to build exactly half of a module (2 to 3 sub-segments) in a single pass.
- **Mandatory Gem 2 Validation After Every Half-Module:** Immediately upon completing `M<N>-A` or `M<N>-B`, Antigravity runs the combined verification gate command for that half-module, creates git tag `step-M<N><A|B>-loop<k>`, and outputs the mandatory banner:
  ```text
  🛑 HALF-MODULE M<N>-<A|B> COMPLETED — GO TO GEM 2 (VALIDATION GEM) NOW!
  Paste the BUILD REPORT + VALIDATION-REQUEST block below into Gem 2.
  ```
- **Gem 2 Audit & Red-Teaming:** Gem 2 audits the completed half-module and emits the ready-to-paste `DECISION PACKET` prompt for Gem 1 to issue the next Half-Module prompt.

```
                        ┌──────────────────────────────────────────────┐
                        │            YOU (the courier + final say)     │
                        └──────────────────────────────────────────────┘

  ┌───────────┐ ① AG-PROMPT        ┌──────────────────┐ ② ONLY WHEN FEATURE / MILESTONE IS COMPLETED  ┌─────────────┐
  │   GEM 1   │───────────────────▶│   ANTIGRAVITY    │──────────────────────────────────────────────▶│    GEM 2    │
  │ CONDUCTOR │                    │    (builder)     │   (BUILD REPORT + VALIDATION-REQUEST)         │  VALIDATOR  │
  └───────────┘                    └──────────────────┘                                               │(Audit+RedTm)│
       ▲                                    │                                                         └─────────────┘
       │                                    │ (2a) Sub-step only (feature not yet done):                     │
       │                                    │      FAST-ADVANCE PACKET (skip Gem 2)                          │
       │                                    ▼                                                                │
       └────────────────────────────────────┴────────────────────────────────────────────────────────────────┘
                                     ③ PROMPT FOR GEM 1 (DECISION PACKET:
                                       Verdict + S1-S4 Fixes + Attack Tests + Ledger Delta)
```

### Routing Types (Enforced by Antigravity at the end of every run)

| Loop / Route | Path | When to Use | Antigravity Mandatory Banner |
|---|---|---|---|
| **MILESTONE VALIDATION** | `G1 → AG → G2 → G1` | **ONLY when a Feature or Milestone/Gate (`P1–P6`, `E0–E8`, `G0–G3`) is completed**, or when verifying an S1 milestone fix. | `🛑 FEATURE / MILESTONE COMPLETED — GO TO GEM 2 (VALIDATION GEM) NOW!` |
| **SUB-STEP FAST-ADVANCE** | `G1 → AG → G1` (Skips Gem 2) | When a low-risk sub-task is done but the feature/milestone is NOT yet finished, or for pure docs/config/seed tweaks. | `🟢 SUB-STEP COMPLETE (FEATURE / MILESTONE NOT YET FINISHED) — DO NOT GO TO GEM 2 YET. Go directly to Gem 1.` |
| **REJECT SHORT-CIRCUIT** | `G2 → G1` | Gem 2 marks **REJECT** (build broken / raw output missing / forbidden files touched). | Gem 2 outputs an immediate REDO/FIX `DECISION PACKET` for Gem 1. |

**HIGH-risk features requiring Milestone Validation in Gem 2 upon completion:** `apply_command()`, locks/triggers, PostgreSQL 16 DDL, idempotency, hash chain/witness/crypto, poller/relay, PIN/session/auth, SSE per-event authz, `BROKEN_BUILD` / `REAL_DATA` guards, voice ACK path, Lane B independent Python monitor, and all Gates `G0–G3`.

### Time Budget
Target **≈10–14 min per Milestone Validation loop** (Antigravity builds the complete feature/milestone in 6–10 min, Gem 2 validates & outputs the Gem 1 prompt in 2–3 min, Gem 1 issues the next prompt in 1 min). Gem 1 tracks the clock in the `STATE LEDGER` and cuts scope using the tier cut order (`T3` first, then `T2`, then `T1`; `T0` never).

---

## 3. One-Time Setup & Gem Configuration

### 3.1 Knowledge Files (Upload to Both Gem 1 and Gem 2)
Keep the same authoritative files in **both Gems** so they never disagree about the spec or workflow:
1. `ReferralHandshake_LOCKED_Problem_Statement_v7.md`
2. `ReferralHandshake_v8_LOCKED_Solution.md`
3. `ReferralHandshake_FINAL_LOCKED_Architecture.md`
4. `ReferralHandshake_3Gem_Antigravity_Workflow.md` (updated to this 2-Gem Milestone Workflow)
5. `AGENTS.md` and `GEMINI.md`
6. Core verification/spec docs (`Master Verification & Test Plan.md`, `feature_specification_referralhandshake_rhp_1.md`, `STATE_TRANSITION_SPECIFICATION.md`, `DEFINITION_OF_DONE.md`)

### 3.2 Gem Instructions

#### Gem 1 — CONDUCTOR (Unchanged)
Gem 1 remains unchanged. Because Gem 2 outputs a standard `DECISION PACKET` formatted exactly as Gem 1 expects, Gem 1 seamlessly processes Gem 2's output, updates the `STATE LEDGER`, and emits the next `AG-PROMPT`.

#### Gem 2 — MILESTONE VALIDATOR (Merged Auditor + Adversary)
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

### 3.3 AGENTS.md Rules (Repo Root)
1. Spec files in `/spec` are READ-ONLY. Precedence: Problem v7 > Solution v8 > Architecture FINAL. Never reinterpret them.
2. Stack is locked: Python 3.12, FastAPI, psycopg3, PostgreSQL 16, React PWA, Pydantic `extra='forbid'`. Banned: blockchain, Kafka, Redis, Kubernetes, WhatsApp, on-device LLM, CRDT for authoritative state.
3. Only do what the current AG-PROMPT says. Touch only the files it lists. If something is ambiguous or a test cannot pass: STOP and report. Do not improvise.
4. `REAL_DATA=0` always. Synthetic data only. Never put keys/secrets in code or in reports; use `.env`.
5. Every step/milestone ends with a git commit tagged `step-<ID>-loop<n>`. Rollback = last tag marked good.
6. Never claim a test passes without pasting the raw command and its output.
7. Silent deviation from the spec is a failure; list any issue under DEVIATIONS.
8. Contract writes go only through `apply_command()`; no other path writes referral/offer/deadline/event state.
9. The Python monitor (Lane B) must NOT import or read server code; it reads only the DB event log and `transitions.yaml`.
10. **2-Gem Milestone Routing Discipline:** Never send the user to Gem 2 for an incomplete feature or mid-feature sub-task. Explicitly instruct the user to go to Gem 2 (Milestone Validator) ONLY when a complete feature or milestone/gate is finished.

### 3.4 Chats and Lanes
- Run two lanes in parallel: **Lane A** (backend / proof, "Person A") and **Lane B** (clients / reach / monitor, "Person B").
- Each lane uses only 2 Gems (`G1-A` + `G2-A` for Lane A; `G1-B` + `G2-B` for Lane B). Gem 3 threads (`G3-A`, `G3-B`) are no longer needed.
- **Monitor independence (F17):** Lane B builds the Python monitor in a separate Antigravity conversation that is never shown the server code, only the DB schema, `transitions.yaml`, and spec. Gem 2 verifies this at every Lane B monitor milestone.

---

## 4. The Packets (Exact Copy-Paste Formats)

### 4.0 STATE LEDGER (Gem 1 prints it in every reply; travels in every packet)

```text
=== STATE LEDGER v<n> ===
Clock: H<hh> of 24 (or Phase P) | Lane A step: <id> | Lane B step: <id>
Gates:  G0(T0)[ ]  G1(T1)[ ]  G2(T2)[ ]  G3(rehearsal)[ ]  FREEZE H22[ ]
Done steps/milestones: <ids with last good tag>
Open defects: <D-id sev short title> ...
Accepted risks (user-approved): <R-id ...>
Approved spec deviations: <none | ids>
Last good commit/tag: <lane A> / <lane B>
Cut so far: <none | T3 ...>
Next 3 milestones: <ids>
```

### 4.1 ① AG-PROMPT (Gem 1 → Antigravity)
Gem 1 issues an `AG-PROMPT` for the target feature or milestone. Antigravity executes all tasks in the prompt, runs the required tests, commits and tags, and outputs the `BUILD REPORT`.

### 4.2 ② ANTIGRAVITY OUTPUT + ROUTING BANNER (Antigravity → Gem 2 OR Gem 1)
Every Antigravity completion MUST end with the `BUILD REPORT` followed immediately by one of these two routing blocks:

#### Option A: Feature or Milestone IS Completed (Route to Gem 2)
```text
🛑 FEATURE / MILESTONE COMPLETED — GO TO GEM 2 (VALIDATION GEM) NOW!
Copy and paste the entire block below into Gem 2 for Milestone Validation.

=== VALIDATION-REQUEST FOR GEM 2 (AUDIT-REQUEST FOR GEM 2) ===
STEP / MILESTONE: <id> | LANE: <A|B> | LOOP: #<n> | COMMIT/TAG: <hash / step-ID-loopN>
SPEC ANCHORS: <§ numbers, I# invariants, T-# tests>
ACCEPTANCE CRITERIA: <measurable criteria from AG-PROMPT>
FILES CHANGED (git diff --stat):
<pasted output>
HIGH-RISK CODE / DIFFS:
<full text or diff of HIGH-risk files>
COMMANDS RUN + RAW OUTPUT:
<exact commands + raw terminal output>
TESTS SUMMARY: <name | pass/fail | measured numbers>
DEVIATIONS / ASSUMPTIONS / OPEN QUESTIONS: <none or details>
SELF-RATED RISK + TOP 3 FAILURE SURFACES: <...>
LEDGER: <one-line ledger>
QUESTION FOR GEM 2: Validate this completed feature/milestone against all spec anchors and invariants, run the targeted red-team & claims integrity check, and output the DECISION PACKET prompt for Gem 1.
```

#### Option B: Sub-Step Only / Feature Still In Progress (Skip Gem 2 → Route Directly to Gem 1)
```text
🟢 SUB-STEP COMPLETE (FEATURE / MILESTONE NOT YET FINISHED) — DO NOT GO TO GEM 2 YET!
Skip Gem 2 and paste the block below directly into Gem 1 (Conductor) to continue building.

=== DECISION PACKET (SUB-STEP FAST-ADVANCE FOR GEM 1) | STEP <id> | LOOP #<n> ===
VERDICT: ADVANCE
ATTACKS: none (sub-step; full milestone validation deferred to Gem 2 upon feature/milestone completion)
AUDITOR CHALLENGE: none
CLAIMS/DEMO INTEGRITY: clean
FIX LIST:
 MUST-FIX   [S1] none
 SHOULD-FIX [S2/S3] none
 LOG        [S4] Sub-step completed with raw test output verified locally.
LEDGER DELTA: Advance sub-step <id> (tag <step-ID-loopN>) toward milestone completion.
```

### 4.3 ③ GEM 2 PROMPT FOR GEM 1 (DECISION PACKET from Gem 2 → Gem 1)
When Gem 2 finishes validating a completed feature or milestone, Gem 2 outputs its audit followed by this exact block, which you copy and paste directly into Gem 1:

```text
=== PROMPT FOR GEM 1 (COPY AND PASTE THIS ENTIRE BLOCK INTO GEM 1) ===
Milestone/Feature Validation completed by Gem 2. Process this DECISION PACKET, update the STATE LEDGER, and generate the next AG-PROMPT.

=== DECISION PACKET | STEP/MILESTONE <id> | LOOP #<n> | MODE <MILESTONE-VALIDATION | GATE-FULL> ===
VERDICT: ADVANCE | FIX-THEN-ADVANCE | REDO | SPEC-QUESTION
EVIDENCE & CONFORMANCE SUMMARY: <n MATCH / n PARTIAL / n MISSING / n DEVIATES>
INVARIANTS VERIFIED: <I# -> mechanism verified | ABSENT>
ATTACKS:
 A-1 | scenario | targets <I#/§> | spec says <…> | BREAKS/HOLDS/UNKNOWN because <mechanism>
     TEST SPEC: inputs <…>; steps <…>; pass condition <…>
AUDITOR CHALLENGE / SELF-CHECK: <what remained unverified or edge cases to watch>
CLAIMS/DEMO INTEGRITY: <flags or "clean">
FIX LIST:
 MUST-FIX   [S1] <issue or "none"> | spec <§> | closes when <evidence>
 SHOULD-FIX [S2/S3] <issue or "none">
 LOG        [S4] <issue or "none">
RISK-ACCEPT CANDIDATES: <for the user to approve, with bound>
LEDGER DELTA: <changes>
NEXT INSTRUCTION FOR GEM 1: <Emit AG-PROMPT for next feature/milestone or S1 targeted fix>
```

---

## 5. Decision Rules (Gem 1 Applies These; You Can Overrule)

| Situation | Action |
|---|---|
| Gem 2 ADVANCE (zero open S1 defects) | Mark feature/milestone done in STATE LEDGER, tag good, issue next milestone AG-PROMPT |
| Gem 2 FIX-THEN-ADVANCE | Next AG-PROMPT = S1 MUST-FIX items + broken attack tests. Re-verify in Gem 2 once fixed |
| Gem 2 REDO or REJECT | Roll back to last good git tag; re-prompt the milestone with explicit constraints |
| Gem 2 SPEC-QUESTION | Gem 1 drafts a SPEC-DEVIATION proposal; you approve or reject before it enters the ledger |
| Same milestone fails 3 validation loops | Cut scope by tier order (`T3` → `T2` → `T1`; `T0` never) or raise a spec decision to you |
| Antigravity claims done without raw output | Automatic FAIL. Re-prompt: "paste raw command and test output" |
| H22 reached | **Code freeze.** Only config changes, rehearsal, MP4 fallbacks |

---

## 6. Milestone & Feature Catalogue (Gem 2 Validates Upon Completion of Each Row)

### Phase P — Pre-Event Spec Artefacts

| ID | Lane | Feature / Milestone | Spec | Risk | Validate in Gem 2 When |
|---|---|---|---|---|---|
| P1 | A | `transitions.yaml` + 28 conformance vectors from §4 | §4, §5 | HIGH | Complete `transitions.yaml` + vector suite runs |
| P2 | A | PostgreSQL 16 DDL (`01_schema.sql`, `02_roles.sql`) + `verify_ddl.sql` (ST-3) | §7 | HIGH | DDL loads cleanly + ST-3 scan passes |
| P3 | A | Quint control-plane spec + vacuity checks | §12 | HIGH | `quint run safety` passes + vacuity checks fail as required |
| P4 | B | Signed profile file + $T_{\max}$ validator (`I13`) | §6 | MED | Validator passes all profile bounds |
| P5 | B | Synthetic seed data (`REAL_DATA=0`) | §2, §10 | LOW | Seed script loads with `REAL_DATA=0` verified |
| P6 | B | Pre-event verification checklist (§21) | §21 | LOW | Checklist completed and recorded |

### Phase E — At-Event Build Milestones (24 Half-Module Prompts)

| Half-Module ID | Hours | Scope & Sub-Segments Built | Primary Lane | Combined Verification Command | Git Tag | Gem 2 Trigger |
|---|---|---|---|---|---|---|
| **`M1-A`** | `H00–H01` | `1.1`–`1.3`: Workspace, Docker topology, PG16 24-table DDL, seed & signed timing profiles | Lane A + B | `pytest tests/test_boot_guards.py tests/test_ddl_constraints.py tests/test_tmax_profiles.py` | `step-M1A-loop1` | **Validate `M1-A` in Gem 2** |
| **`M1-B`** | `H01–H02` | `1.4`–`1.6`: RFC 8785 JCS parity, `transitions.yaml` loader, Quint `rhp1.qnt` & Explorer | Lane A | `pytest tests/test_jcs_parity.py tests/test_transitions_table.py && python tests/explore_transitions.py && quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000` | `step-M1B-loop1` | **Validate `M1-B` in Gem 2 (Completes Module 1)** |
| **`M2-A`** | `H02–H03` | `2.1`–`2.3`: Dual connection pools, sessions (cookie/voice), Argon2id autonomous lockout | Lane A | `pytest tests/test_auth_sessions.py tests/test_pin_lockout_scope.py` | `step-M2A-loop1` | **Validate `M2-A` in Gem 2** |
| **`M2-B`** | `H03–H04` | `2.4`–`2.5`: Role-command authz matrix, Pydantic schemas, 10-step `apply_command()` pipeline | Lane A | `pytest tests/test_authz_matrix.py tests/test_pipeline_core.py` | `step-M2B-loop1` | **Validate `M2-B` in Gem 2 (Completes Module 2)** |
| **`M3-A`** | `H04–H05` | `3.1`–`3.3`: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT` single-owner lease arbitration | Lane A | `pytest tests/test_cmd_create.py tests/test_cmd_ack_confirm.py tests/test_cmd_accept.py` | `step-M3A-loop1` | **Validate `M3-A` in Gem 2** |
| **`M3-B`** | `H05–H06` | `3.4`–`3.6`: `DECLINE` + `advance()`, `COUNTER` negotiation, terminal commands (`CLOSE`, etc.) | Lane A | `pytest tests/test_cmd_decline_advance.py tests/test_cmd_counter.py tests/test_cmd_lifecycle.py` | `step-M3B-loop1` | **Validate `M3-B` in Gem 2 (Completes Module 3)** |
| **`M4-A`** | `H06–H07` | `4.1`–`4.2`: Independent runtime monitor `monitor.py` (F17), 200-way concurrency barrier (`race200`), idempotency matrix | Lane B / A | `pytest tests/test_monitor_fold.py tests/test_race200.py tests/test_idempotency_matrix.py` | `step-M4A-loop1` | **Validate `M4-A` in Gem 2** |
| **`M4-B`** | `H07–H08` | `4.3`–`4.4`: Safe `BROKEN_BUILD` scratch DB isolation, mutation tests `M1`–`M6`, 28 conformance vectors | Lane B / A | `pytest tests/test_broken_build.py tests/test_mutations.py tests/test_conformance_vectors.py` | `step-M4B-loop1` | **Validate `M4-B` in Gem 2 (Completes Module 4 / T0 Proof Core)** |
| **`M5-A`** | `H08–H09` | `5.1`–`5.3`: Two-phase stateless poller, intra-facility notice ladder ($0, A/4, 3A/4$), outbox relay | Lane A | `pytest tests/test_poller_liveness.py tests/test_notice_ladder_and_closure.py` | `step-M5A-loop1` | **Validate `M5-A` in Gem 2** |
| **`M5-B`** | `H09–H10` | `5.4`–`5.5`: Authorized SSE hub with `GRANT_REVOKED` stream stripping, heartbeats & clock-step guard | Lane A + B | `pytest tests/test_sse_revoke.py tests/test_clock_and_heartbeats.py` | `step-M5B-loop1` | **Validate `M5-B` in Gem 2 (Completes Module 5)** |
| **`M6-A`** | `H10–H11` | `6.1`–`6.2`: Separate-OS-user witness signer 5s Merkle tree, off-box sync & cold-key `RESTORE` | Lane A | `pytest tests/test_witness_merkle.py tests/test_tamper_vs_restore.py` | `step-M6A-loop1` | **Validate `M6-A` in Gem 2** |
| **`M6-B`** | `H11–H12` | `6.3`: Pure-JS browser verifier (`verifier.ts` with `@noble`) & superuser SQL `tamper.sh` | Lane B | `npm --prefix pwa test -- verifier && bash scripts/tamper.sh --dry-check` | `step-M6B-loop1` | **Validate `M6-B` in Gem 2 (Completes Module 6)** |
| **`M7-A`** | `H12–H13` | `7.1`–`7.3`: React PWA shell, SSE state store, rotating judge QR admission, referring clinician card | Lane B | `pytest tests/test_judge_join.py && npm --prefix pwa run build` | `step-M7A-loop1` | **Validate `M7-A` in Gem 2** |
| **`M7-B`** | `H13–H14` | `7.4`–`7.6`: Receiving duty desk, judge race desk + verifier drawer, Guarantee Arena big screen | Lane B | `npm --prefix pwa test && make gate-t0` | `step-M7B-loop1` | **Validate `M7-B` in Gem 2 (GATE G0 = T0 PASS)** |
| **`M8-A`** | `H14–H15` | `8.1`–`8.2`: Parallel transport track API, 6 arrival cases, Mapbox Matrix ETA service cache | Lane A | `pytest tests/test_transport_and_arrivals.py` | `step-M8A-loop1` | **Validate `M8-A` in Gem 2** |
| **`M8-B`** | `H15–H16` | `8.3`–`8.4`: PWA ambulance client (foreground GPS) & Dispatcher Console with replay scrubber | Lane B | `pytest tests/test_dispatcher_proxy_and_replay.py && make gate-t1` | `step-M8B-loop1` | **Validate `M8-B` in Gem 2 (GATE G1 = T1 PASS)** |
| **`M9-A`** | `H16–H17` | `9.1`–`9.3`: Outbound Exotel IVR, AMD + Press-1 human gate, DTMF menu & per-call PIN verification | Lane B + A | `pytest tests/test_exotel_ivr.py` | `step-M9A-loop1` | **Validate `M9-A` in Gem 2** |
| **`M9-B`** | `H17–H18` | `9.4`–`9.5`: TRAI DLT static SMS adapter & 9-char Crockford Base32 + mod-37 paper code codec | Lane B | `pytest tests/test_dlt_sms_lint.py tests/test_paper_code_mod37.py && make gate-t2` | `step-M9B-loop1` | **Validate `M9-B` in Gem 2 (GATE G2 = T2 PASS)** |
| **`M10-A`** | `H18–H19` | `10.1`–`10.2`: AES-256-GCM envelope encryption, monthly KEK wrapping, automated crypto-shredder | Lane A | `pytest tests/test_envelope_crypto.py` | `step-M10A-loop1` | **Validate `M10-A` in Gem 2** |
| **`M10-B`** | `H19–H20` | `10.3`–`10.4`: District command centre live map/APOT KPIs & `networkx` graph aggregations ($k \ge 5$) | Lane A + B | `pytest tests/test_analytics_recompute.py` | `step-M10B-loop1` | **Validate `M10-B` in Gem 2 (Completes Module 10)** |
| **`M11-A`** | `H20–H20:30` | `11.1`–`11.2`: Cognitive-forcing AI intake (`423 ANCHOR_REQUIRED`) + 20-slip gate, FHIR R4 exporter | Lane A + B | `pytest tests/test_ai_seeded_errors.py tests/test_fhir_exporter.py` | `step-M11A-loop1` | **Validate `M11-A` in Gem 2** |
| **`M11-B`** | `H20:30–H21` | `11.3`–`11.4`: IEEE 1849 XES / BSA s.63 evidence generator & native Kotlin Android EMT client | Lane A + B | `pytest tests/test_bsa_xes_exports.py tests/test_fcm_zero_payload.py && make gate-t3` | `step-M11B-loop1` | **Validate `M11-B` in Gem 2 (Completes Module 11 & T3)** |
| **`M12-A`** | `H21–H21:45` | `12.1`–`12.2`: Eight-scenario Toxiproxy fault matrix & automated self-audit CI scripts (`ST-1`..`ST-5`) | Lane A | `pytest tests/test_toxiproxy_chaos.py tests/test_lock_order.py tests/test_tmax_profiles.py tests/test_ddl_constraints.py tests/test_idempotency_matrix.py tests/test_claims_lexicon.py` | `step-M12A-loop1` | **Validate `M12-A` in Gem 2** |
| **`M12-B`** | `H21:45–H22` | `12.3`: Master tier acceptance gate runner `Makefile` (`gate-all`) & `scripts/preflight.sh` rehearsal | Lane A + B | `make gate-all && bash scripts/preflight.sh` | `step-M12B-loop1` | **Validate `M12-B` in Gem 2 (GATE G3 = REHEARSAL)** |
| **`FREEZE`** | `H22–H24` | **HARD CODE FREEZE AT H22:** Configuration-only tweaks, 30s live proof loop rehearsal $\times 3$, dual-uplink check | Team A + B | `bash scripts/preflight.sh` | `step-FREEZE` | **STAGE READY** |

## 7. One-Page Cheat Sheet

```text
IN-PROGRESS SUB-STEPS:   G1 ──AG-PROMPT──▶ ANTIGRAVITY ──FAST-ADVANCE PACKET──▶ G1 (Do NOT use Gem 2 yet)
MILESTONE COMPLETED:     G1 ──AG-PROMPT──▶ ANTIGRAVITY ──VALIDATION-REQUEST──▶ GEM 2 (Audit + Red-Team) ──DECISION PACKET──▶ G1

Gem 1 is unchanged. Gem 2 validates ONLY completed features/milestones and writes the prompt for Gem 1.
Evidence or it didn't happen. Max 2 fix loops → then cut scope (T3 → T2 → T1). Freeze at H22. REAL_DATA=0 always.
```
