# ReferralHandshake — 1-Gem Post-Build Validation, Testing, Fixing & Completion Workflow

**Team:** MAHA YODHAS · **Event:** Colossus 3.0, 13–14 Nov 2026, Bengaluru (24 h build, 2 students)
**Spec set (locked):** Problem Statement v7 > Solution v8 > FINAL_LOCKED_Architecture (precedence in that order)
**Status:** All 12 Modules (`MODULE 1` through `MODULE 12`) are FULLY BUILT.
**Active Loop:** Direct 1-Gem Post-Build Loop (`Gem 1 <-> Antigravity`).
**Sole Reviewer & Conductor:** Gem 1 (Master Validation Auditor, Root-Cause Debugger & Completion Conductor). Gem 2 and Gem 3 are retired.
**Builder & Fixer:** Google Antigravity (executes surgical fixes, audits, integration verification, and runs tests).

---

## 0. The 1-Gem Direct Post-Build Validation & Fixing Loop

All 12 modules (`MODULE 1` through `MODULE 12`) have completed their initial construction. We have transitioned to a **1-Gem Direct Loop (`Gem 1 <-> Antigravity`)** focused exclusively on **Validation, Testing, Bug Fixing, Full-Stack Integration Wiring, and Stage Demo Completion**.

| # | Core Principle | Operational Rule |
|---|---|---|
| 1 | **Gem 1 is the SOLE Gem.** | Gem 1 acts as Master Validation Auditor, Root-Cause Debugger, and Completion Conductor. Gem 2 and Gem 3 are officially retired. |
| 2 | **Direct Loop Cadence (`Gem 1 -> Antigravity -> Gem 1`).** | Gem 1 issues diagnostic, validation, or fix prompts (`AG-PROMPT`). Antigravity executes tasks, runs verification commands, pastes verbatim terminal output, commits/tags, and reports directly back to Gem 1. |
| 3 | **Five Structured Validation Stages (V1..V5).** | Systematic gate-by-gate verification across V1 (Spine/Self-Audits), V2 (Tier 0 Gate), V3 (Tier 1 & Tier 2 Gates), V4 (Tier 3 Gate & Chaos Matrix), and V5 (Full-Stack Preflight & Live Proof Loop). |
| 4 | **Evidence-Based Reporting.** | Raw command and test outputs must be pasted verbatim in every report. "Tests pass" without raw output = automatic FAIL. |
| 5 | **Mandatory Antigravity Banner.** | Every run ends with: `🛑 VALIDATION & FIX STEP COMPLETED — PASTE THIS REPORT DIRECTLY BACK INTO GEM 1!` |

---

## 1. Role Responsibilities in the 1-Gem Loop

| | **Gem 1 — CONDUCTOR & MASTER AUDITOR** | **Antigravity — BUILDER, FIXER & RUNNER** |
|---|---|---|
| **Owns** | Master validation plan, test sequencing, root-cause diagnosis, issuing surgical `AG-PROMPT` fix/audit directives, `STATE LEDGER` | Code modifications, wiring verification, AST & runtime self-audits, test execution, browser execution, git tagging, verbatim reporting |
| **Input** | `VALIDATION & FIX REPORT` from Antigravity | `AG-PROMPT` from Gem 1 |
| **Output** | `AG-PROMPT` (to Antigravity) with surgical tasks, targeted fixes, or next stage gate directives | Code / fix diffs + test suites + verbatim terminal output + mandatory Gem 1 banner |
| **Never does** | Write product code directly. Approve gates without raw test outputs. Silently modify specifications. | Touch forbidden spec files (`/spec/*`, `db/01_schema.sql`). Improvise domain rules. Mask test failures. |

---

## 2. The Five Post-Build Validation Stages (V1–V5)

The post-build workflow systematically proves correctness and integration health across five stages:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        POST-BUILD VALIDATION & FIXING PIPELINE                         │
├─────────────┬──────────────────────────────────────────┬───────────────────────────────┤
│ Stage V1    │ Self-Audits ST-1..ST-5 & Spine Integrity │ AST lock order, Tmax math,   │
│             │                                          │ DDL triggers, Idempotency,   │
│             │                                          │ Claims lexicon check         │
├─────────────┼──────────────────────────────────────────┼───────────────────────────────┤
│ Stage V2    │ Tier 0 Gate (`make gate-t0`)             │ Handshake commands, race200, │
│             │                                          │ M1-M6 mutations, vectors,    │
│             │                                          │ BROKEN_BUILD, poller/relay,  │
│             │                                          │ witness Merkle, verifier     │
├─────────────┼──────────────────────────────────────────┼───────────────────────────────┤
│ Stage V3    │ Tier 1 & Tier 2 Gates                    │ Transport track, arrivals,   │
│             │ (`make gate-t1`, `make gate-t2`)         │ Dispatcher console/replay,   │
│             │                                          │ Exotel IVR, DLT SMS, Paper   │
├─────────────┼──────────────────────────────────────────┼───────────────────────────────┤
│ Stage V4    │ Tier 3 Gate & Toxiproxy Chaos Matrix     │ Envelope crypto, Analytics,  │
│             │ (`make gate-t3`, `test_toxiproxy_chaos`) │ 423 AI intake, FHIR/XES/BSA, │
│             │                                          │ Kotlin FCM, 8 Toxics         │
├─────────────┼──────────────────────────────────────────┼───────────────────────────────┤
│ Stage V5    │ Full-Stack Preflight & Live Proof Loop   │ `make gate-all`, preflight.sh│
│             │ (`bash scripts/preflight.sh`)            │ 30-Second Stage Proof Loop   │
└─────────────┴──────────────────────────────────────────┴───────────────────────────────┘
```

---

## 3. Communication Packets

### 3.1 `AG-PROMPT` (Gem 1 → Antigravity)
Gem 1 provides:
- The target Stage (`V1` through `V5`) or specific defect (`D-n`) to diagnose and fix.
- Specific files allowed to touch.
- Exact verification and test commands to run.
- Measurable acceptance criteria.

### 3.2 `VALIDATION & FIX REPORT` (Antigravity → Gem 1)
Antigravity executes and returns:
1. Summary of Diagnostics & Fixes applied.
2. Invariant & Defect Verification Matrix (`I1`..`I16`, `D1`..`D20`, `F1`..`F20`).
3. Full Verbatim Terminal Output (every test, migration, and linter run).
4. Full Code Diffs of modified files.
5. Updated `STATE LEDGER`.
6. Mandatory Banner:
   ```text
   🛑 VALIDATION & FIX STEP COMPLETED — PASTE THIS REPORT DIRECTLY BACK INTO GEM 1!
   ```

---

## 4. One-Page Quick Reference

```text
POST-BUILD LOOP: Gem 1 ──AG-PROMPT──▶ Antigravity ──VALIDATION & FIX REPORT──▶ Gem 1
Gem 1 is the sole reviewer and conductor. Gem 2 and Gem 3 are retired.
Evidence or it didn't happen: verbatim terminal output for every test command.
Freeze at H22. REAL_DATA=0 always.
```
