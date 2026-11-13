# ReferralHandshake (Protocol RHP-1) — Multi-Agent Context Handoff Protocol (`HANDOFF.md`)

**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0
**Architecture Authority:** `ReferralHandshake_FINAL_LOCKED_Architecture.md`
**Workflow Authority:** `ReferralHandshake_3Gem_Antigravity_Workflow.md`

> **PURPOSE:** This document provides the **exact, copy-paste-ready handoff packets** used to move context across the 4-node ring (`Gem 1 CONDUCTOR -> Google Antigravity -> Gem 2 AUDITOR -> Gem 3 ADVERSARY -> Gem 1 CONDUCTOR`) and to recover any Gem or Antigravity session from zero context loss when a chat window grows stale.

---

## 1. Handoff Routing Rules & Loop Selection

```
  ┌──────────────┐  ① AG-PROMPT   ┌────────────────────┐  ② BUILD REPORT +   ┌──────────────┐
  │    GEM 1     │───────────────▶│ GOOGLE ANTIGRAVITY │    AUDIT-REQUEST     │    GEM 2     │
  │  CONDUCTOR   │                │   (Code Builder)   │─────────────────────▶│   AUDITOR    │
  └──────────────┘                └────────────────────┘                      └──────────────┘
         ▲                                                                         │   │
         │                                     SHORT-CIRCUIT (if Verdict = REJECT) │   │
         │◀────────────────────────────────────────────────────────────────────────┘   │
         │                                     OR FAST LOOP (if Risk = LOW/MED)        │
         │                                                                             ▼
         │        ④ DECISION PACKET (Verdict + Runnable Attack Tests)         ┌──────────────┐
         └────────────────────────────────────────────────────────────────────│    GEM 3     │
                                                                              │  ADVERSARY   │
                                                                              └──────────────┘
```

### 1.1 Which Loop Path to Execute
| Loop Type | Route | Mandatory Trigger Conditions | Target Time |
|---|---|---|---|
| **FULL** | `G1 -> AG -> G2 -> G3 -> G1` | Any `HIGH` risk step (`apply_command`, locks/triggers, DDL, idempotency, hash chain/witness/crypto, poller/relay, PIN/session/auth, SSE authz, `BROKEN_BUILD`/`REAL_DATA` guards, voice ACK), any Gate (`G0–G3`), or any `S1` defect fix. | 20–25 min |
| **FAST** | `G1 -> AG -> G2 -> G1` | `LOW` or `MED` risk steps (UI layout, seed data, copy text, config, docs) or fixes for `S2`/`S3` defects where `G2` verdict is `PASS` or `PASS-WITH-NOTES`. | 10–12 min |
| **SHORT-CIRCUIT** | `G1 -> AG -> G2 -> G1` | Gem 2 returns `VERDICT: REJECT` (code does not run, raw command output missing, forbidden files touched, or banned tech introduced). Do not waste Gem 3 tokens on a broken build. | 5 min |

### 1.2 Non-Negotiable Handoff Discipline
1. **Evidence or Automatic FAIL:** Antigravity must paste raw terminal outputs (`pytest`, `psql`, `quint`, `git diff --stat`) and full source code (or unified diffs if $>300$ lines) for every `HIGH` risk file. Summarized test claims without raw stdout/stderr are automatically rejected by Gem 2.
2. **Workspace Isolation (F17):** Lane A (`G1-A`, `G2-A`, `G3-A`, Antigravity Workspace A) and Lane B (`G1-B`, `G2-B`, `G3-B`, Antigravity Workspace B) never mix. When Lane B builds `monitor/monitor.py` (Step `E2-B`), Antigravity Workspace B is **never** given access to `api/` source files—only `db/schema.sql`, `spec/transitions.yaml`, and §3/§12 prose.
3. **Zero Secrets / Zero PHI in Packets:** Never paste `.env` secrets, Exotel API tokens, Mapbox tokens, or private keys into any handoff packet. `REAL_DATA=0` always.
4. **Two-Fix-Loop Cap:** Maximum 2 fix loops per step. On a 3rd failure, Gem 1 must either cut scope following the locked cut order (`T3 -> T2 -> T1`; `T0` is never cut) or escalate a `SPEC-QUESTION` to the human operator.

---

## 2. Packet ①: `AG-PROMPT` (`Gem 1 CONDUCTOR` $\rightarrow$ `Google Antigravity`)

Copy this block from **Gem 1** and paste it directly into **Google Antigravity**:

```markdown
=== AG-PROMPT | STEP <Step-ID> | LANE <A|B> | LOOP <FULL|FAST> #<1|2|3> | RISK <LOW|MED|HIGH> ===
Read `AGENTS.md` and `CURRENT_STATE.md` first. You are the builder only. Do not invent architecture or touch files outside `FILES YOU MAY TOUCH`.

### 1. STATE LEDGER
<Paste current STATE LEDGER block from CURRENT_STATE.md §1>

### 2. GOAL
<Single declarative sentence stating what this step delivers>

### 3. SPEC ANCHORS (Strict Precedence: Problem v7 > [V] > Solution v8 > Final Architecture)
- **Sections:** <e.g., FINAL_LOCKED_Architecture.md §4, §5, §7>
- **Invariants Enforced:** <e.g., I1, I2, I4, I8, I12, I14, I15, I16>
- **Closures & Tests:** <e.g., F1, F12, F13, F14 | T-F1, T-F12, T-F13, T-F14>

### 4. INPUT STATE
- **Branch:** `<lane-a/main or lane-b/main>`
- **Last Good Tag:** `<step-XX-loopN>`
- **Existing Verified Artifacts:** `<list files already committed and passing>`

### 5. ATOMIC TASKS
1. <Task 1 with exact function signatures, table names, or UI states>
2. <Task 2 ...>
3. <Task 3 ...>

### 6. ATTACK TESTS FROM PREVIOUS RED-TEAM (Implement & Run Now)
- `<None | A-1: description, inputs, steps, expected assertion>`

### 7. FILE BOUNDARIES (CODEOWNERS Enforced)
- **FILES YOU MAY TOUCH:**
  - `<path/to/file1>`
  - `<path/to/file2>`
- **FILES YOU MUST NOT TOUCH (Hard Lock):**
  - `spec/*` (Read-only unless Step is P1/P3/P4)
  - `db/schema.sql` (Read-only unless Step is P2)
  - `<api/* if Lane B building monitor/ | monitor/* if Lane A>`

### 8. TESTS TO WRITE & EXECUTE
1. `<exact pytest / psql / quint command>` -> Expected: `<exact pass condition>`
2. `<exact command>` -> Expected: `<exact pass condition>`

### 9. MEASURABLE ACCEPTANCE CRITERIA
- [ ] Criterion 1 (with numeric bound, e.g., deadlock delta == 0)
- [ ] Criterion 2
- [ ] Commit tagged as `step-<Step-ID>-loop<N>`

### 10. STOP CONDITIONS
STOP IMMEDIATELY and output a blocker report if:
- Any spec requirement is ambiguous or contradicts `FINAL_LOCKED_Architecture.md`.
- Achieving a passing test requires editing a file in `FILES YOU MUST NOT TOUCH`.
- You are tempted to introduce a banned technology (Redis, Kafka, WebSockets, floats in JCS, etc.).

### 11. REQUIRED OUTPUT FORMAT
When finished, output **Packet ② (`BUILD REPORT + AUDIT-REQUEST`)** using the exact template in `HANDOFF.md §3`. Paste raw command output (never summarize) and full code of all `HIGH` risk files.
```

---

## 3. Packet ②: `BUILD REPORT + AUDIT-REQUEST` (`Google Antigravity` $\rightarrow$ `Gem 2 AUDITOR`)

Antigravity must generate this exact structure at the end of every run. Copy the entire output and paste it into **Gem 2**:

```markdown
=== BUILD REPORT | STEP <Step-ID> | LANE <A|B> | LOOP <FULL|FAST> #<N> | COMMIT <git-sha> ===
**Tag Created:** `step-<Step-ID>-loop<N>`

### 1. FILES CHANGED (`git diff --stat`)
```text
<paste raw git diff --stat output>
```

### 2. SOURCE CODE OF HIGH-RISK FILES (Full file if <=300 lines; unified git diff if >300 lines)
#### File: `<path/to/file>`
```<language>
<paste exact code or diff>
```

### 3. COMMANDS RUN & RAW TERMINAL OUTPUT (Unsummarized)
```text
$ <exact command 1>
<raw stdout/stderr>

$ <exact command 2>
<raw stdout/stderr>
```

### 4. TEST SUMMARY & MEASURED METRICS
| Test ID / Name | Command | Status (PASS/FAIL) | Measured Value (Latency / Count / Delta) | Spec Target |
|---|---|---|---|---|
| `<T-xx>` | `<cmd>` | `PASS` | `<measured live>` | `<target>` |

### 5. DISCLOSURE LEDGER
- **NOT DONE / SKIPPED:** `<none or explicit list>`
- **DEVIATIONS FROM SPEC:** `<none or explicit description>`
- **ASSUMPTIONS MADE:** `<none or explicit list>`
- **OPEN QUESTIONS:** `<none or explicit list>`
- **SELF-RATED RISK (`LOW|MED|HIGH`) & TOP 3 FRAGILE POINTS:**
  1. `<point 1>`
  2. `<point 2>`
  3. `<point 3>`

---
=== AUDIT-REQUEST FOR GEM 2 ===
- **Step / Lane / Loop:** `<Step-ID> | Lane <A|B> | Loop <FULL|FAST> #<N>`
- **Spec Anchors to Audit Against:** `<copy section numbers, I1-I16, F1-F20 from AG-PROMPT>`
- **Acceptance Criteria to Verify:** `<copy acceptance checklist from AG-PROMPT>`
- **Instruction to Gem 2:** Audit the BUILD REPORT and code above against the locked spec anchors. Verify raw evidence, lock ordering (`referral > offer > deadline > outbox`), invariant enforcement, file boundaries, and test falsifiability. Output Packet ③ (`RED-TEAM REQUEST`).
```

---

## 4. Packet ③: `RED-TEAM REQUEST` (`Gem 2 AUDITOR` $\rightarrow$ `Gem 3 ADVERSARY` or `Gem 1`)

Gem 2 outputs this block after auditing Packet ②.
- If `VERDICT` is `REJECT` -> **SHORT-CIRCUIT:** Paste this directly into **Gem 1**.
- If `LOOP` is `FAST` and `VERDICT` is `PASS` / `PASS-WITH-NOTES` -> Paste this directly into **Gem 1**.
- Otherwise (`FULL` loop or `FAIL`) -> Paste this (plus the HIGH-risk code) into **Gem 3**.

```markdown
=== RED-TEAM REQUEST | STEP <Step-ID> | LANE <A|B> | LOOP <FULL|FAST> #<N> ===
**AUDITOR VERDICT:** `<PASS | PASS-WITH-NOTES | FAIL | REJECT>`
*(If REJECT: User, SHORT-CIRCUIT directly to Gem 1 without running Gem 3)*

### 1. EVIDENCE CHECK
- **Raw Command Output Present?** `<YES | NO — Automatic FAIL if NO>`
- **File Boundaries Respected?** `<YES | NO — list any unauthorized file edits>`
- **Common-Mode Independence (F17) Intact?** `<YES | VIOLATED>`
- **UNVERIFIED ITEMS (Not shown in packet):** `<list every file/behavior that could not be verified from pasted text>`

### 2. SPEC CONFORMANCE MATRIX
| Spec Anchor | Locked Requirement (Section / Rule) | Implementation (`file:line`) | Status (`MATCH` / `PARTIAL` / `MISSING` / `DEVIATES`) |
|---|---|---|---|
| `<§ / F#>` | `<exact rule>` | `<file:line>` | `<status>` |

### 3. INVARIANT SWEEP (I1–I16 Touched by This Step)
| Invariant | Enforcement Mechanism Found in Code / DDL | Falsifiable Test Present? | Status (`ENFORCED` / `WEAK` / `ABSENT`) |
|---|---|---|---|
| `<I#>` | `<trigger / unique index / FOR UPDATE / check>` | `<YES/NO + test name>` | `<status>` |

### 4. ARCHITECTURAL LOCK & CODE REVIEW CHECKS
- **Lock Order (`referral -> offer -> deadline -> outbox`):** `<PASS | FAIL | N/A>`
- **Idempotency Step-1 & Savepoint Rollback (`sp_cmd`):** `<PASS | FAIL | N/A>`
- **Banned Tech Scan:** `<CLEAN | VIOLATION: name>`
- **Test Quality (Tests that cannot fail):** `<none | list weak tests>`

### 5. DEFECT LIST
| Defect ID | Severity (`S1` Blocker / `S2` Major / `S3` Minor / `S4` Note) | Title & Mechanism | Spec Reference | Evidence (`file:line` or test output) |
|---|---|---|---|---|
| `D-1` | `<S1-S4>` | `<description>` | `<§ / I#>` | `<file:line>` |

### 6. TOP 5 ATTACK SURFACES FOR GEM 3
1. `<Surface 1: e.g., race window between phase-1 deadline claim and phase-2 apply_command>`
2. `<Surface 2>`
3. `<Surface 3>`
4. `<Surface 4>`
5. `<Surface 5>`

### 7. STATE LEDGER LINE
`<Single-line summary of current step, defects count, and clock>`
```

---

## 5. Packet ④: `DECISION PACKET` (`Gem 3 ADVERSARY` $\rightarrow$ `Gem 1 CONDUCTOR`)

Gem 3 outputs this block after red-teaming Packet ③. Copy and paste it into **Gem 1**:

```markdown
=== DECISION PACKET | STEP <Step-ID> | LANE <A|B> | LOOP #<N> | MODE <FULL|QUICK> ===
**ADVERSARY VERDICT:** `<ADVANCE | FIX-THEN-ADVANCE | REDO | SPEC-QUESTION>`

### 1. ADVERSARIAL ATTACKS & RUNNABLE TEST SPECS
| Attack ID | Scenario & Vector | Targets (`I#` / `§` / `F#`) | Spec Requirement | Prediction (`BREAKS` / `HOLDS` / `UNKNOWN`) + Exact Mechanism | Runnable Test Spec for Antigravity (Inputs, Steps, Pass Assertion) |
|---|---|---|---|---|---|
| `A-1` | `<e.g., 200 concurrent accepts + simultaneous poller timeout>` | `I2, I14, §5` | `<rule>` | `<BREAKS/HOLDS because ...>` | **Inputs:** `<...>` **Steps:** `<...>` **Assert:** `<...>` |
| `A-2` | `<...>` | `<...>` | `<...>` | `<...>` | `<...>` |

### 2. CHALLENGE TO GEM 2 (AUDITOR BLIND SPOTS)
- `<List anything Gem 2 marked MATCH/PASS without raw proof, or concurrency/clock/privacy subtleties Gem 2 missed>`

### 3. CLAIMS & DEMO INTEGRITY AUDIT (§19 Claims Register)
- **Live-Measured Rule ("Every number shown live is measured live"):** `<CLEAN | VIOLATION: file:line>`
- **Forbidden Claims Scan ("lives saved", "eliminates ping-pong", "ABDM compliant", "BSA certified", "immutable", "zero loopholes", "mathematically proven system"):** `<CLEAN | VIOLATION: quote>`
- **`REAL_DATA=0` & `BROKEN_BUILD` Isolation:** `<CLEAN | VIOLATION>`

### 4. MERGED FIX LIST FOR GEM 1
| Priority (`MUST-FIX` / `SHOULD-FIX` / `LOG`) | Defect / Attack ID | Severity (`S1–S4`) | Issue Description | Spec Reference | Closing Evidence Required in Next Loop |
|---|---|---|---|---|---|
| `MUST-FIX` | `<D-x / A-y>` | `S1` | `<description>` | `<§>` | `<exact raw test output required>` |
| `SHOULD-FIX` | `<D-x / A-y>` | `S2/S3` | `<description>` | `<§>` | `<evidence>` |
| `LOG` | `<D-x>` | `S4` | `<description>` | `<§>` | `<logged in ledger>` |

### 5. RISK-ACCEPTANCE CANDIDATES (Requires Human Approval)
- `<none | R-id: description, technical bound, and monitor alarm that bounds it>`

### 6. STATE LEDGER DELTA
- **Step Status Transition:** `<Step-ID: PENDING -> DONE | FIX-LOOP-#(N+1) | ROLLBACK>`
- **New Open Defects:** `<list>`
- **Closed Defects:** `<list>`
```

---

## 6. Emergency Escalation & Context Reset Templates

### 6.1 `SPEC-DEVIATION` Proposal (When Gem 3 Returns `SPEC-QUESTION`)
Never patch around a spec ambiguity in code. Gem 1 outputs this block to the human operator:

```markdown
=== SPEC-DEVIATION REQUEST | ID: SD-<N> | STEP <Step-ID> ===
- **Ambiguity / Conflict Discovered:** `<exact conflict between code/environment and spec section>`
- **Precedence Check:**
  1. `Problem_Statement_v7.md` says: `<quote>`
  2. `v8_LOCKED_Solution.md` says: `<quote>`
  3. `FINAL_LOCKED_Architecture.md` says: `<quote>`
- **Proposed Resolution (Minimal Delta):** `<exact rule>`
- **Invariants Impacted (I1–I16):** `<prove zero invariant relaxation>`
- **Human Decision Required:** Reply `APPROVE SD-<N>` or `REJECT SD-<N>`.
```

### 6.2 Fresh-Chat Context Re-Hydration Prompt (When Any Gem Drifts or Hits Token Limits)
If any Gem forgets a section, hallucinates an invariant, or slows down due to chat length, open a **brand-new chat** for that Gem (with the 4 knowledge files uploaded) and paste this exact bootstrap message:

```markdown
=== CONTEXT RE-HYDRATION | GEM <1 CONDUCTOR | 2 AUDITOR | 3 ADVERSARY> | LANE <A|B> ===
We are resuming the ReferralHandshake (Protocol RHP-1) build in a clean session.
1. Your uploaded Knowledge Files (`Problem_Statement_v7.md` > `v8_LOCKED_Solution.md` > `FINAL_LOCKED_Architecture.md` > `AGENTS.md`) are the locked specification.
2. Below is the authoritative `STATE LEDGER` from `CURRENT_STATE.md`:

<Paste current STATE LEDGER block from CURRENT_STATE.md §1>

3. Below is the current active packet for you to process immediately:

<Paste Packet ①, ②, ③, or ④>
```

### 6.3 Cross-Lane Sync Packet (Before Gate Steps `G0`, `G1`, `G2`, `G3`)
Before running a Gate prompt, Person A and Person B merge their `ADVANCED` branches into an integration branch (`gate-g0`, `gate-g1`, `gate-g2`, `gate-g3`) and paste this sync block into **Gem 1 (Lane A)**:

```markdown
=== CROSS-LANE GATE SYNC | GATE <G0|G1|G2|G3> | CLOCK H<hh> ===
- **Lane A Last Good Tag:** `<step-E4A-loopN>` (Commit `<sha>`)
- **Lane B Last Good Tag:** `<step-E4B-loopN>` (Commit `<sha>`)
- **Integration Branch:** `gate-<g0|g1|g2|g3>`
- **Common-Mode Independence Check (F17):**
  - `git log -- monitor/` authors: `<Person B only>`
  - `grep -rn "from api" monitor/ || echo "CLEAN"`: `CLEAN`
- **Instruction to Gem 1:** Emit the `GATE-PROMPT` (`LOOP FULL`) requiring Antigravity to execute every acceptance test for `<Tier T0|T1|T2|T3>` in `FINAL_LOCKED_Architecture.md §24` and paste raw measured outputs.
```