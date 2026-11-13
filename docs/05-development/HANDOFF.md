# ReferralHandshake (Protocol RHP-1) — 2-Gem Milestone Validation Context Handoff Protocol (`HANDOFF.md`)

**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0
**Architecture Authority:** `ReferralHandshake_FINAL_LOCKED_Architecture.md`
**Workflow Authority:** `ReferralHandshake_3Gem_Antigravity_Workflow.md`

> **PURPOSE:** This document provides the **exact, copy-paste-ready handoff packets** used in the 2-Gem Milestone Validation Workflow (`Gem 1 CONDUCTOR <-> Google Antigravity`, routing to `Gem 2 MILESTONE VALIDATOR` ONLY when a complete feature or milestone/gate is achieved), and to recover any session from zero context loss when a chat thread grows long or drifts.

---

## 1. Handoff Routing Rules & Loop Selection

```text
  ┌──────────────┐     ① AG-PROMPT (or FAST-ADVANCE)     ┌────────────────────┐
  │    GEM 1     │◀─────────────────────────────────────▶│ GOOGLE ANTIGRAVITY │
  │  CONDUCTOR   │                                       │   (Code Builder)   │
  └──────────────┘                                       └────────────────────┘
         ▲                                                          │
         │                                                          │ (Case B: Feature / Milestone Complete)
         │                                                          ▼ ② BUILD REPORT + VALIDATION-REQUEST
         │       ③ DECISION PACKET (Verdict + Attack Tests)      ┌──────────────────────────────────────┐
         └───────────────────────────────────────────────────────│                GEM 2                 │
                                                                 │         MILESTONE VALIDATOR          │
                                                                 │   (Merged Spec Auditor & Adversary)  │
                                                                 └──────────────────────────────────────┘
```

### 1.1 Which Loop Path to Execute
| Loop Type | Route | Mandatory Trigger Conditions | Target Time |
|---|---|---|---|
| **MILESTONE VALIDATION** | `G1 -> AG -> G2 -> G1` | Used **ONLY** when a complete Feature or Milestone/Gate (`P1`–`P6`, `E0`–`E8`, `G0`–`G3`) is completed, or when validating an `S1` fix. Gem 2 runs combined spec audit and adversarial red-teaming. | 15–20 min |
| **SUB-STEP FAST-ADVANCE** | `G1 <-> AG` | Sub-steps within a feature (e.g. drafting schema, scaffolding tests, UI layout, iterative code). Skips Gem 2 entirely until the entire feature/milestone is ready. | 5–10 min |
| **SHORT-CIRCUIT** | `G2 -> G1` | Gem 2 returns `VERDICT: REJECT` (code does not boot, raw command output missing, forbidden files touched, or banned tech introduced). Immediately re-issue or roll back. | ~5 min |

### 1.2 Non-Negotiable Handoff Discipline
1. **Evidence or Automatic FAIL:** Antigravity must paste raw terminal outputs (`pytest`, `psql`, `quint`, `git diff --stat`) and full source code (or unified diffs if $>300$ lines) for every `HIGH` risk file. Summarized test claims without raw stdout/stderr are automatically rejected by Gem 2.
2. **Workspace Isolation (F17):** Lane A (`G1-A`, `G2-A`, Antigravity Workspace A) and Lane B (`G1-B`, `G2-B`, Antigravity Workspace B) never mix. When Lane B builds `monitor/monitor.py` (Step `E2-B`), Antigravity Workspace B is **never** given access to `api/` source files—only `db/schema.sql`, `spec/transitions.yaml`, and §3/§12 prose.
3. **Zero Secrets / Zero PHI in Packets:** Never paste `.env` secrets, Exotel API tokens, Mapbox tokens, or private keys into any handoff packet. `REAL_DATA=0` always.
4. **Two-Fix-Loop Cap:** Maximum 2 fix loops per step. On a 3rd failure, Gem 1 must either cut scope following the locked cut order (`T3 -> T2 -> T1`; `T0` is never cut) or escalate a `SPEC-QUESTION` to the human operator.

---

## 2. Packet ①: `AG-PROMPT` (`Gem 1 CONDUCTOR` $ightarrow$ `Google Antigravity`)

Copy this block from **Gem 1** and paste it directly into **Google Antigravity**:

```markdown
=== AG-PROMPT | STEP <Step-ID> | LANE <A|B> | LOOP <MILESTONE|FAST> #<1|2|3> | RISK <LOW|MED|HIGH> ===
Read `AGENTS.md` and `CURRENT_STATE.md` first. You are the builder only. Do not invent architecture or touch files outside `FILES YOU MAY TOUCH`.

GOAL: <One-sentence active-voice goal for this run>
SPEC ANCHORS: <Architecture §, Invariants I1-I16, Closures F1-F20, Verification Tests ST-1..ST-5>
INPUT STATE: branch <lane-a|lane-b>, last good tag <tag>, current commit <hash>

FILES YOU MAY TOUCH:
- <exact repo path 1>
- <exact repo path 2>

FILES YOU MUST NOT TOUCH:
- db/schema.sql (READ-ONLY after P2)
- spec/transitions.yaml (READ-ONLY after P1)
- spec/rhp1.qnt (READ-ONLY after P3)
- spec/profiles.json (READ-ONLY after P4)
- monitor/ (LANE B ONLY — FORBIDDEN TO LANE A)
- api/ (LANE A ONLY — FORBIDDEN TO LANE B)

TASKS (Execute in exact order):
 1. <Task 1: concrete, falsifiable file edits>
 2. <Task 2: verification command to run>
 3. <Task 3: git commit & tag requirement>

ACCEPTANCE CRITERIA:
- [ ] AC-1: <observable, testable condition>
- [ ] AC-2: <exact terminal command> outputs <expected string / exit 0>
- [ ] AC-3: git tag `step-<Step-ID>-loop<N>` applied cleanly

STOP CONDITIONS:
- If any spec requirement is ambiguous, if a test fails and cannot be fixed within allowed files, or if you need to touch a forbidden file: STOP IMMEDIATELY and report in OPEN QUESTIONS. Do not improvise.

LEDGER SNAPSHOT:
Clock: H<hh.mm> | Active Lane: <A|B> | Open S1: <count> | Tier Gates: G0[ ] G1[ ] G2[ ] G3[ ]

When finished, output your complete BUILD REPORT followed by the mandatory routing banner (Case A for sub-steps, Case B for complete milestones).
```

---

## 3. Antigravity Output & Mandatory Routing Banners

Antigravity must generate a complete BUILD REPORT and append one of the two mandatory routing banners at the very end:

```markdown
=== BUILD REPORT | STEP <Step-ID> | LANE <A|B> | LOOP #<N> | COMMIT <git-sha> ===
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
```

### Mandatory Routing Banner (Choose Case A or Case B):

#### Case A (Sub-step completed, feature/milestone in progress):
```text
================================================================================
🟢 SUB-STEP COMPLETE (FEATURE / MILESTONE NOT YET FINISHED) — DO NOT GO TO GEM 2 YET.
Paste the FAST-ADVANCE PACKET below directly into Gem 1 (or continue building the remaining tasks of this feature).
================================================================================
=== FAST-ADVANCE PACKET | STEP <id> | LANE <A|B> | LOOP #<n> ===
1. COMPLETED SUB-TASKS: <list tasks completed>
2. RAW TEST / VERIFICATION EVIDENCE: <summary of command outputs>
3. REMAINING TASKS FOR MILESTONE: <what tasks remain before Gem 2 review>
4. PROPOSED NEXT AG-PROMPT FOCUS: <next sub-step>
```

#### Case B (Complete Feature / Milestone / Tier Gate completed):
```text
================================================================================
🛑 FEATURE / MILESTONE COMPLETED — GO TO GEM 2 (VALIDATION GEM) NOW!
Paste the BUILD REPORT + VALIDATION-REQUEST block below into Gem 2.
================================================================================
=== VALIDATION-REQUEST FOR GEM 2 ===
FEATURE / MILESTONE: <ID> | LANE: <A|B> | LOOP #<N> | RISK: <LOW|MED|HIGH>
SPEC ANCHORS: <exact § sections, I# invariants, F# closures, T-# tests>
ACCEPTANCE CRITERIA: <copied verbatim from AG-PROMPT>
LEDGER LINE: <one-line STATE LEDGER>
attached_above: BUILD REPORT with raw outputs, browser verification, and HIGH-risk code.
QUESTION FOR GEM 2: Validate this completed milestone line-by-line against every spec anchor, invariant (I1–I16), and closure (F1–F20). Verify raw test outputs. Design adversarial attack tests (A-1..A-k). Emit the DECISION PACKET for Gem 1.
```

---

## 4. Packet ②: `DECISION PACKET` (`Gem 2 MILESTONE VALIDATOR` $ightarrow$ `Gem 1 CONDUCTOR`)

Gem 2 outputs this definitive block after performing combined spec audit and adversarial red-teaming on Packet ②. Copy and paste it directly into **Gem 1**:

```markdown
=== DECISION PACKET | FEATURE/STEP <Step-ID> | LANE <A|B> | LOOP #<N> ===
**VERDICT:** `<ADVANCE | FIX-THEN-ADVANCE | REDO | REJECT | SPEC-QUESTION>`

### 1. EVIDENCE CHECK
- **Raw Command Output Present?** `<YES | NO — Automatic REJECT if NO>`
- **File Boundaries Respected?** `<YES | NO — list unauthorized edits>`
- **Common-Mode Independence (F17) Intact?** `<YES | VIOLATED>`
- **UNVERIFIED ITEMS:** `<list items lacking raw proof>`

### 2. SPEC CONFORMANCE MATRIX
| Spec Anchor | Locked Requirement (Section / Rule) | Implementation (`file:line`) | Status (`MATCH` / `PARTIAL` / `MISSING` / `DEVIATES`) |
|---|---|---|---|
| `<§ / F#>` | `<exact rule>` | `<file:line>` | `<status>` |

### 3. INVARIANT SWEEP (I1–I16 Touched by This Milestone)
| Invariant | Enforcement Mechanism Found in Code / DDL | Falsifiable Test Present? | Status (`ENFORCED` / `WEAK` / `ABSENT`) |
|---|---|---|---|
| `<I#>` | `<trigger / unique index / FOR UPDATE / check>` | `<YES/NO + test name>` | `<status>` |

### 4. ARCHITECTURAL LOCK CHECKS
- **Lock Order (`referral -> offer -> deadline -> outbox`):** `<PASS | FAIL | N/A>`
- **Idempotency Step-1 & Savepoint Rollback (`sp_cmd`):** `<PASS | FAIL | N/A>`
- **Banned Tech Scan:** `<CLEAN | VIOLATION: name>`
- **Claims & Demo Integrity (§19 Claims Register):** `<CLEAN | VIOLATION>`

### 5. ADVERSARIAL ATTACKS & RUNNABLE TEST SPECS (RED-TEAM)
| Attack ID | Scenario & Vector | Targets (`I#` / `§` / `F#`) | Spec Requirement | Prediction (`BREAKS` / `HOLDS` / `UNKNOWN`) + Exact Mechanism | Runnable Test Spec for Antigravity (Inputs, Steps, Pass Assertion) |
|---|---|---|---|---|---|
| `A-1` | `<e.g., 200 concurrent accepts + simultaneous poller timeout>` | `I2, I14, §5` | `<rule>` | `<BREAKS/HOLDS because ...>` | **Inputs:** `<...>` **Steps:** `<...>` **Assert:** `<...>` |
| `A-2` | `<...>` | `<...>` | `<...>` | `<...>` | `<...>` |

### 6. DEFECT & REMEDIATION LIST FOR GEM 1
| Priority (`MUST-FIX` / `SHOULD-FIX` / `LOG`) | Defect / Attack ID | Severity (`S1–S4`) | Issue Description | Spec Reference | Closing Evidence Required in Next Loop |
|---|---|---|---|---|---|
| `MUST-FIX` | `<D-x / A-y>` | `S1` | `<description>` | `<§>` | `<exact raw test output required>` |
| `SHOULD-FIX` | `<D-x / A-y>` | `S2/S3` | `<description>` | `<§>` | `<evidence>` |
| `LOG` | `<D-x>` | `S4` | `<description>` | `<§>` | `<logged in ledger>` |

### 7. STATE LEDGER DELTA
- **Milestone Status:** `<PENDING -> DONE | FIX-LOOP-#(N+1) | ROLLBACK>`
- **New Open Defects:** `<list>`
- **Closed Defects:** `<list>`
```

---

## 5. Context Recovery & Session Re-Hydration Packets

Use these packets when recovering a fresh Gem session without losing context:

### 5.1 Context Re-Hydration (`Human` $ightarrow$ `Gem 1 CONDUCTOR`)
```text
=== CONTEXT RE-HYDRATION | GEM 1 CONDUCTOR | LANE <A|B> ===
You are GEM 1 (CONDUCTOR) for ReferralHandshake. Resume orchestration from this STATE LEDGER:

=== STATE LEDGER v<n> ===
Clock: H<hh.mm> of 24.00 (or Phase P) | Active Lane: <A|B>
Lane A Position: Step <id> (Last good tag: <tag>)
Lane B Position: Step <id> (Last good tag: <tag>)
Tier Gates: G0(T0)[ ]  G1(T1)[ ]  G2(T2)[ ]  G3(Rehearsal)[ ]  H22-FREEZE[ ]
Completed Steps: <comma-separated step IDs + git tags>
Open Defects: <D-id [S1|S2|S3] description (or "None")>
Pending Attack Tests: <A-id description (or "None")>
User-Accepted Bounded Risks: <R-id (or "None")>
Approved Spec Deviations: <SD-id (or "None")>
Scope Cuts Executed: <"None" or cut tier items>
Next 3 Queued Steps: <id1, id2, id3>

Emit the next AG-PROMPT now.
```

### 5.2 Context Re-Hydration (`Human` $ightarrow$ `Gem 2 MILESTONE VALIDATOR`)
```text
=== CONTEXT RE-HYDRATION | GEM 2 MILESTONE VALIDATOR | LANE <A|B> ===
You are GEM 2 (MILESTONE VALIDATOR) for ReferralHandshake (merged Spec Auditor & Red-Team Adversary; Gem 3 is retired).
Validate the attached BUILD REPORT against the locked specification, run adversarial red-team attack tests, and emit the DECISION PACKET for Gem 1.
```
