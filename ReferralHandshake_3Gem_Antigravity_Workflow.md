# ReferralHandshake — 3-Gem + Antigravity Build Workflow

**Team:** MAHA YODHAS · **Event:** Colossus 3.0, 13–14 Nov 2026, Bengaluru (24 h build, 2 students)
**Spec set (locked):** Problem Statement v7 > Solution v8 > FINAL_LOCKED_Architecture (precedence in that order)
**Builder:** Google Antigravity (the ONLY thing that writes product code) · **Reviewers:** 3 Gemini Gems

---

## 0. Verdict on your idea

Your idea is good. The ring `Gem 1 → Antigravity → Gem 2 → Gem 3 → Gem 1` separates three jobs that fail when one model does all of them: **planning**, **verifying**, and **attacking**. Three Gems is the right number. More would only add copy-paste overhead.

Four upgrades make it work under 24-hour pressure (all built into this file):

| # | Upgrade | Why |
|---|---|---|
| 1 | **Evidence-based reports.** Antigravity must paste raw test output and the code/diff of risky files. "Tests pass" with no output = automatic FAIL. | Gems can't see your repo. Without evidence, Gem 2 is auditing a self-claim. |
| 2 | **Gem 3 attacks produce tests, not opinions.** Every attack becomes a runnable test in the next Antigravity prompt. | A red team that can't run code is only useful if its attacks get executed by someone. |
| 3 | **Three loop types** (FULL / FAST / SHORT-CIRCUIT) chosen by risk. | A 25-minute full ring on a CSS tweak wastes the one thing you can't buy: hours. |
| 4 | **STATE LEDGER** carried in every packet. | Gem chats drift and get long. The ledger lets you restart any Gem in a fresh chat with zero loss. |

---

## 1. Roles (who owns what, who must never do what)

| | **Gem 1 — CONDUCTOR** | **Gem 2 — AUDITOR** | **Gem 3 — ADVERSARY** |
|---|---|---|---|
| **Owns** | Plan, step order, tier gates, cut decisions, the Antigravity prompts, the STATE LEDGER | Spec conformance, code review, checking that test evidence is real and sufficient, defect list | Breaking the build: races, partitions, crashes, bad input, demo failure; challenging Gem 2's audit; claims integrity; GO/NO-GO recommendation |
| **Input** | Decision Packet from Gem 3 (+ you) | Build Report + code from Antigravity | Red-Team Request from Gem 2 |
| **Output** | AG-PROMPT (to Antigravity) | RED-TEAM REQUEST (to Gem 3) | DECISION PACKET (to Gem 1) |
| **Never does** | Write product code. Accept a step with open S1 defects. Change the spec silently. | Write fixes or code. Plan next steps. Approve without evidence. | Fix code. Decide scope. Report an attack as "breaks" without a stated mechanism. |
| **Mindset** | "What is the smallest next step that moves a gate?" | "Does this match the spec, line by line, with proof?" | "How do I make this fail on stage?" |

**Antigravity** receives prompts only from Gem 1 (or a Gem-1-approved hotfix). It never decides architecture.

---

## 2. The Ring

```
                        ┌──────────────────────────────────────────────┐
                        │            YOU (the courier + final say)     │
                        └──────────────────────────────────────────────┘

  ┌─────────┐ ① AG-PROMPT  ┌─────────────┐ ② BUILD REPORT + AUDIT-REQUEST ┌─────────┐
  │  GEM 1  │─────────────▶│ ANTIGRAVITY │───────────────────────────────▶│  GEM 2  │
  │CONDUCTOR│              │  (builder)  │                                │ AUDITOR │
  └─────────┘              └─────────────┘                                └─────────┘
       ▲                                                                       │
       │ ④ DECISION PACKET                          ③ RED-TEAM REQUEST         │
       │   (+ attack tests, fix list,                  (verdict + defects)     ▼
       │    ledger delta)                                                 ┌─────────┐
       └──────────────────────────────────────────────────────────────── │  GEM 3  │
                                                                          │ADVERSARY│
                                                                          └─────────┘
```

### Loop types (Gem 1 picks one and writes it in the AG-PROMPT header)

| Type | Path | Use when |
|---|---|---|
| **FULL** | G1 → AG → G2 → G3 → G1 | Step is HIGH risk, any gate step, any S1 fix |
| **FAST** | G1 → AG → G2 → G1 | Step is LOW/MED risk (UI, seed data, config, docs), or a fix for S2/S3 defects |
| **SHORT-CIRCUIT** | G2 → G1 directly | Gem 2 verdict is **REJECT** (build doesn't run / tests can't execute / wrong files touched). No point attacking a broken build. |

**HIGH risk** = anything touching: `apply_command`, locks/triggers, DDL, idempotency, hash chain/witness/crypto, poller/relay, PIN/session/auth, SSE per-event authz, `BROKEN_BUILD` / `REAL_DATA` guards, voice ACK path.
**LOW risk** = styling, seed data, copy text, config, README.

### Time budget
Target **≈20–25 min per FULL loop** (Antigravity 8–12, Gem 2 4, Gem 3 4, Gem 1 3, pasting 2) and **≈12 min per FAST loop**. Gem 1 tracks the clock in the ledger and cuts scope using the tier cut order (T3 first, then T2, then T1; T0 never).

---

## 3. One-time setup (do this BEFORE the event)

### 3.1 Knowledge files (Gem → Knowledge)
Upload the same files to **all three Gems** so they never disagree about the spec:
1. `ReferralHandshake_LOCKED_Problem_Statement_v7.md`
2. `ReferralHandshake_v8_LOCKED_Solution.md`
3. `ReferralHandshake_FINAL_LOCKED_Architecture.md`
4. `AGENTS.md` (section 3.3, also placed in the repo root)

### 3.2 Gem instructions (paste into each Gem's "Instructions" box)
If Gemini limits the box length, paste the short version and put the rest in a `GEM_RULES.md` knowledge file.

#### Gem 1 — CONDUCTOR

~~~text
You are CONDUCTOR for ReferralHandshake (team MAHA YODHAS, Colossus 3.0, 24-hour build, 2 students). Knowledge files are the LOCKED spec. Precedence: Problem v7 > Solution v8 > Architecture FINAL. Never contradict them. If something is not in them, say "NOT IN SPEC" and ask; never guess.

JOB: plan the build, write prompts for Google Antigravity (the only builder), keep the STATE LEDGER, decide advance/fix/cut. You NEVER write product code.

EVERY REPLY = (1) the updated STATE LEDGER, (2) one AG-PROMPT, (3) one line telling the user where to paste the result (Antigravity -> Gem 2).

AG-PROMPT must contain: header (STEP id, LANE A/B, LOOP FULL/FAST, RISK, loop count n), GOAL (1 sentence), SPEC ANCHORS (exact section numbers, invariant ids I1-I16, test ids T-xx), INPUT STATE (branch, last good commit), TASKS (numbered, atomic), FILES MAY TOUCH, FILES MUST NOT TOUCH, TESTS TO WRITE+RUN, MEASURABLE ACCEPTANCE, STOP CONDITIONS (ambiguity or failing test = stop and report, do not improvise), and the REQUIRED OUTPUT: a BUILD REPORT with raw command output pasted, then an AUDIT-REQUEST block for Gem 2.

INPUT YOU RECEIVE: a DECISION PACKET from Gem 3. Rules: advance only if zero open S1 defects and every MUST-FIX is closed with evidence. Turn every Gem 3 ATTACK into a test task in the next AG-PROMPT. Max 2 fix loops per step; on the 3rd, cut scope by tier order (T3, T2, T1; T0 never) or raise a SPEC-QUESTION to the user. Spec changes only via a SPEC-DEVIATION the user approves. Respect pre-event vs at-event work and the code freeze at H22. Keep real data out (REAL_DATA=0), never ask for secrets/keys in chat.

Use the step catalogue in the user's WORKFLOW file. Be terse. No praise.
~~~

#### Gem 2 — AUDITOR

~~~text
You are AUDITOR for ReferralHandshake. Knowledge files are the LOCKED spec (Problem v7 > Solution v8 > Architecture FINAL). You audit ONLY what is pasted/attached; anything not shown to you is UNVERIFIED, never assumed OK. You NEVER write code or fixes and never plan next steps.

INPUT: a BUILD REPORT + AUDIT-REQUEST from Antigravity (with the AG-PROMPT's spec anchors).

DO, in order:
1. EVIDENCE CHECK: raw test output present? commands shown? any "passes" with no output = FAIL. List what you could not verify.
2. SPEC CONFORMANCE: for every anchor in the AG-PROMPT, a row: anchor | requirement (quote or exact section) | what code does (file:line) | MATCH / PARTIAL / MISSING / DEVIATES.
3. INVARIANT SWEEP: for every invariant I1-I16 the step touches, name the enforcement mechanism in the code (index, trigger, lock, check) or flag it absent.
4. CODE REVIEW: lock order (referral > offer > deadline > outbox), transaction boundaries, idempotency position, error paths, hard-coded secrets/real data, banned tech (blockchain, Kafka, Redis, Kubernetes, WhatsApp, on-device LLM, CRDT for authoritative state), scope creep beyond FILES MAY TOUCH.
5. TEST QUALITY: do the tests actually fail when the invariant is broken? Name any test that cannot fail.
6. DEFECT LIST: id D-n, severity S1 blocker (breaks an invariant or demo) / S2 major / S3 minor / S4 note, spec reference, expected behavior, evidence.

VERDICT: PASS / PASS-WITH-NOTES / FAIL / REJECT (REJECT = does not run or wrong scope; tell the user to SHORT-CIRCUIT back to Gem 1).

OUTPUT: the audit, then a RED-TEAM REQUEST block for Gem 3 containing: step id, loop type, verdict, defect list, UNVERIFIED list, the 5 most dangerous attack surfaces you see, and the ledger line. Terse and exact. Never soften a defect.
~~~

#### Gem 3 — ADVERSARY (red team)

~~~text
You are ADVERSARY for ReferralHandshake. Knowledge files are the LOCKED spec. You cannot run code; you reason from the spec and the pasted code, and you turn every attack into a RUNNABLE TEST for Antigravity. You NEVER fix code or decide scope.

INPUT: a RED-TEAM REQUEST from Gem 2 (verdict, defects, unverified list, attack surfaces).

DO:
1. ATTACK. For each attack: id A-n | scenario | which invariant/section it targets | expected behavior per spec | prediction BREAKS / HOLDS / UNKNOWN with the exact mechanism | a runnable test spec (inputs, steps, pass condition). Cover as relevant: concurrency/races (200-way accept, double timeout fire, outbox redelivery), crash/restart mid-transaction, network partition and replay, clock steps, stale/offline commands, idempotency edge cases, auth/PIN/session abuse, privacy leaks (PHI in logs/push/SSE), tamper and restore, broken-build isolation from real data.
2. CHALLENGE THE AUDITOR: what did Gem 2 miss, over-trust, or mark PASS without evidence? Name it.
3. CLAIMS + DEMO INTEGRITY: any claim, number or UI element that could be shown as real but is simulated or pre-computed? Anything breaking "every number shown live is measured live", or implying mortality / time-saved impact? Flag against the Claims Register.
4. FULL vs QUICK: at gates run FULL attack (all categories). Otherwise QUICK (top 5 attacks for this step).

OUTPUT = DECISION PACKET for Gem 1: verdict ADVANCE / FIX-THEN-ADVANCE / REDO / SPEC-QUESTION; merged fix list tagged MUST-FIX / SHOULD-FIX / LOG (each with severity S1-S4, spec reference, and the evidence that would close it); the attack tests to implement; any approved-risk candidates; ledger delta. Never report BREAKS without a mechanism. No praise.
~~~

### 3.3 `AGENTS.md` (repo root; Antigravity reads it, also add as a workspace rule if available)

~~~text
# AGENTS.md — ReferralHandshake builder rules
1. Spec files in /spec are READ-ONLY. Precedence: Problem v7 > Solution v8 > Architecture FINAL. Never reinterpret them.
2. Stack is locked: Python 3.12, FastAPI, psycopg3, PostgreSQL 16, React PWA, Pydantic extra='forbid'. Banned: blockchain, Kafka, Redis, Kubernetes, WhatsApp, on-device LLM, CRDT for authoritative state.
3. Only do what the current AG-PROMPT says. Touch only the files it lists. If something is ambiguous or a test cannot pass: STOP and report. Do not improvise or "make it work".
4. REAL_DATA=0 always. Synthetic data only. Never put keys/secrets in code or in reports; use .env.
5. Every step ends with a git commit tagged step-<ID>-loop<n>. Rollback = last tag marked good.
6. Never claim a test passes without pasting the raw command and its output.
7. If you deviate from the spec in any way, list it under DEVIATIONS in the report. Silent deviation is a failure.
8. Contract writes go only through apply_command(); no other path writes referral/offer/deadline/event state.
9. The Python monitor (Lane B) must NOT import or read server code; it reads only the DB event log and transitions.yaml.

## BUILD REPORT format (end every task with this, in this order)
STEP / LOOP / commit hash
FILES CHANGED (git diff --stat)
CODE: full text of every file marked HIGH risk (or git diff if >300 lines)
COMMANDS RUN + RAW OUTPUT (pasted, not summarised)
TESTS: name | pass/fail | measured numbers
NOT DONE / SKIPPED
DEVIATIONS FROM SPEC (or "none")
ASSUMPTIONS
OPEN QUESTIONS
SELF-RATED RISK + the 3 things most likely to be wrong
Then output the AUDIT-REQUEST block for Gem 2.
~~~

### 3.4 Chats and lanes
- You are two people, so run **two lanes in parallel**: **Lane A** (backend / proof, "Person A") and **Lane B** (clients / reach / monitor, "Person B").
- Each lane uses the same 3 Gems but **its own chat thread per Gem** (name them `G1-A`, `G1-B`, `G2-A`, …). Each lane has its own Antigravity workspace branch.
- **Monitor independence (F17):** Lane B builds the Python monitor in a separate Antigravity conversation that is **never shown the server code**, only the DB schema, `transitions.yaml` and spec. Gem 2 checks this on every Lane B monitor step. This is what stops "spec and monitor are wrong in the same way."
- Merge to `main` only after a step is ADVANCED by Gem 1. Never merge on red.

### 3.5 Event rules check (do first)
The architecture (§2, §21) marks product code as **at-event** work and pre-event work as documents only, "verify against event rules." Confirm with the organisers whether pre-built code and AI-assisted coding are allowed. If NOT allowed, run **Phase P** only (spec artefacts), and do all of **Phase E** inside the 24 hours.

---

## 4. The packets (exact copy-paste formats)

### 4.0 STATE LEDGER (Gem 1 prints it in every reply; it travels in every packet)

```text
=== STATE LEDGER v<n> ===
Clock: H<hh> of 24 (or Phase P) | Lane A step: <id> | Lane B step: <id>
Gates:  G0(T0)[ ]  G1(T1)[ ]  G2(T2)[ ]  G3(rehearsal)[ ]  FREEZE H22[ ]
Done steps: <ids with last good tag>
Open defects: <D-id sev short title> ...
Accepted risks (user-approved): <R-id ...>
Approved spec deviations: <none | ids>
Last good commit/tag: <lane A> / <lane B>
Cut so far: <none | T3 ...>
Next 3 steps: <ids>
```

### 4.1 ① AG-PROMPT (Gem 1 → Antigravity)

```text
=== AG-PROMPT | STEP <id> | LANE <A|B> | LOOP <FULL|FAST> #<n> | RISK <LOW|MED|HIGH> ===
Read AGENTS.md first. You are the builder only.
GOAL: <one sentence>
SPEC ANCHORS: <§ numbers>, <I# invariants>, <T-# tests>
INPUT STATE: branch <x>, last good tag <y>, existing: <what already works>
TASKS:
 1. ...
 2. ...
FILES YOU MAY TOUCH: ...
FILES YOU MUST NOT TOUCH: ...
TESTS TO WRITE AND RUN: ...
ATTACK TESTS FROM LAST RED-TEAM (implement now): <A-ids with test specs, or none>
ACCEPTANCE (measurable): ...
STOP IF: spec is ambiguous, a test cannot pass, or you need to touch a forbidden file.
LEDGER: <one-line ledger>
WHEN DONE, OUTPUT IN THIS ORDER:
 (1) BUILD REPORT in the format from AGENTS.md (raw outputs pasted; full code of HIGH-risk files),
 (2) a block that starts with the line "=== AUDIT-REQUEST FOR GEM 2 ===" containing: step, loop, spec anchors, acceptance list, the BUILD REPORT, and the question "audit this against the anchors".
```

**You:** paste into Antigravity. When it finishes, copy the whole output (report + audit-request) and paste into **Gem 2**. If the code is too big to paste, attach the files to the Gem 2 message.

### 4.2 ③ RED-TEAM REQUEST (Gem 2 → Gem 3)

```text
=== RED-TEAM REQUEST | STEP <id> | LOOP <FULL|FAST> #<n> ===
VERDICT: PASS | PASS-WITH-NOTES | FAIL
EVIDENCE CHECK: <ok | gaps>
CONFORMANCE SUMMARY: <n MATCH / n PARTIAL / n MISSING / n DEVIATES> + the rows that are not MATCH
INVARIANTS TOUCHED: <I# → mechanism found | ABSENT>
DEFECTS: D-1 [S?] <title> | spec <§> | evidence <file:line>
UNVERIFIED (I could not see/prove): ...
TOP ATTACK SURFACES: 1..5
ATTACH: the code/diff of HIGH-risk files from the report
LEDGER: <one-line ledger>
```

**You:** paste into **Gem 3** (and attach the same code/diff). If Gem 2's verdict is **REJECT**, skip Gem 3 and paste Gem 2's output into **Gem 1** (SHORT-CIRCUIT). On a **FAST** loop, paste Gem 2's verdict into Gem 1 directly.

### 4.3 ④ DECISION PACKET (Gem 3 → Gem 1)

```text
=== DECISION PACKET | STEP <id> | LOOP #<n> | MODE <FULL|QUICK> ===
VERDICT: ADVANCE | FIX-THEN-ADVANCE | REDO | SPEC-QUESTION
ATTACKS:
 A-1 | scenario | targets <I#/§> | spec says <…> | BREAKS/HOLDS/UNKNOWN because <mechanism>
     TEST SPEC: inputs <…>; steps <…>; pass condition <…>
AUDITOR CHALLENGE: <what Gem 2 missed or over-trusted>
CLAIMS/DEMO INTEGRITY: <flags or "clean">
FIX LIST:
 MUST-FIX   [S1] <issue> | spec <§> | closes when <evidence>
 SHOULD-FIX [S2/S3] ...
 LOG        [S4] ...
RISK-ACCEPT CANDIDATES: <for the user to approve, with bound>
LEDGER DELTA: <changes>
```

**You:** paste into **Gem 1**. Gem 1 updates the ledger and emits the next AG-PROMPT (the loop restarts).

---

## 5. Decision rules (Gem 1 applies these; you can overrule)

| Situation | Action |
|---|---|
| Gem 2 PASS/PASS-WITH-NOTES + Gem 3 ADVANCE, no open S1 | Mark step done, tag good, next step |
| Gem 3 FIX-THEN-ADVANCE | Next prompt = MUST-FIX items + the attack tests. Re-loop FULL if any S1, otherwise FAST |
| Gem 3 REDO | Roll back to last good tag; re-prompt the step with the lessons added |
| Gem 3 SPEC-QUESTION | Gem 1 writes a SPEC-DEVIATION proposal; **you** approve or reject; only then does it enter the ledger |
| Gem 2 REJECT | SHORT-CIRCUIT to Gem 1 |
| Same step fails 3 loops | Cut scope by tier order (T3 → T2 → T1; T0 never) or ask you for a spec decision |
| Gem 2 and Gem 3 disagree | Spec text wins, then Gem 3's mechanism-backed attack beats an unsupported PASS. Gem 1 asks for evidence rather than choosing a side |
| Antigravity claims done without raw output | Treated as FAIL. Re-prompt: "paste raw output" |
| H22 reached | **Code freeze.** Only config changes, rehearsal, MP4 fallbacks |

**Severity:** S1 breaks an invariant (I1–I16), the demo, or data safety · S2 wrong behavior with a workaround · S3 minor · S4 note.
**Definition of "step done":** acceptance met with measured evidence, no open S1, committed and tagged.

---

## 6. Step catalogue (Gem 1 follows this order; gates are from Architecture §24)

### Phase P — before the event (spec artefacts only; run only what the rules allow)

| ID | Lane | Step | Spec | Risk | Loop |
|---|---|---|---|---|---|
| P1 | A | `transitions.yaml` + conformance vectors from the §4 transition table | §4, §5 | HIGH | FULL |
| P2 | A | Load the §7 DDL into Postgres 16; run the FK/constraint scan; fix DDL (ST-3) | §7 | HIGH | FULL |
| P3 | A | Quint control-plane spec; `quint run safety`; vacuity checks fail as required | §12 | HIGH | FULL |
| P4 | B | Signed profile file + T_max validator (I13) | §6 | MED | FAST (FULL if the guard is touched) |
| P5 | B | Synthetic seed data (`REAL_DATA=0`) | §2, §10 | LOW | FAST |
| P6 | B | Run the §21 pre-event verification list; record results | §21 | LOW | FAST |

### Phase E — at the event (hours from Architecture §17)

| ID | Hours | Lane A (backend / proof) | Lane B (clients / reach) | Risk | Gate |
|---|---|---|---|---|---|
| E0 | 0–2 | Repo, docker-compose, DDL load, seed, `transitions.yaml` loader | PWA shell, rotating-QR admission | MED | — |
| E1 | 2–6 | `apply_command()` steps 1–10: CREATE / ACK / ACCEPT / DECLINE | Desk UI, SSE with per-event authz | HIGH | — |
| E2 | 6–9 | Poller (2-phase), outbox relay, TIMEOUT, notice ladder | Big screen; Python monitor (separate workspace) | HIGH | — |
| E3 | 9–12 | Hash chain, witness/signer (separate OS user), checkpoints | Browser verifier (pure-JS Ed25519 / SHA-256) | HIGH | — |
| E4 | 12–14 | `race200` test, mutation tests M1–M3 | `BROKEN_BUILD` scratch DB + banner | HIGH | **G0 = T0 pass** |
| E5 | 14–17 | COUNTER, arrival cases, closure | Dispatcher console, PWA GPS | HIGH | **G1 = T1 pass** |
| E6 | 17–20 | Idempotency matrix, fencing tests | Exotel IVR (press-1 gate), paper code | HIGH | **G2 = T2 pass** |
| E7 | 20–22 | Fixes from test results | Record MP4 fallbacks, rehearsal ×3 | MED | **G3 = rehearsal** |
| E8 | 22–24 | Config-only changes | Final rehearsal, backup laptop | LOW | **FREEZE** |

T3 (Kotlin app, AI intake, FHIR/XES) runs only if G0–G2 are green.

### Gate steps (use a FULL loop with Gem 3 in FULL attack mode)
At G0–G3 Gem 1 issues a **GATE-PROMPT**: Antigravity runs every acceptance criterion of that tier from Architecture §24 and pastes raw numbers (e.g. G0: `race200` = exactly 1 of 200 returns 200; deadlock delta 0; M1–M6 trip their checkers; monitor 0 violations in the 10-minute randomised run; `BROKEN_BUILD` turns the monitor red ≤2 s; silence-to-dispatcher ≤25 s on `DEMO_FAST`). Gem 2 checks each number against §24; Gem 3 attacks the demo itself (30-second proof loop, §17).

---

## 7. Failure handling

| Problem | Fix |
|---|---|
| A Gem forgets the spec or gets vague | Start a fresh chat for that Gem; paste the latest STATE LEDGER and the current packet. Nothing else is needed |
| Gem invents a section/invariant | Reply "cite the exact section from the knowledge file or say NOT IN SPEC" |
| Antigravity "fixes" things you didn't ask for | Gem 2 flags scope creep (FILES MUST NOT TOUCH); roll back to the last tag |
| Context too large to paste | Attach files instead of pasting; keep the BUILD REPORT itself under ~400 lines |
| Antigravity stuck in a loop | Stop it; Gem 1 splits the step into smaller tasks |
| Spec seems wrong | Never patch in code. Gem 3 raises SPEC-QUESTION, Gem 1 drafts a SPEC-DEVIATION, you decide |
| Anything involves keys, real patient data, Exotel credentials | Keep out of every chat and report. `.env` only |

---

## 8. Kickoff (your first three messages)

**Message 1 → Gem 1 (new chat `G1-A`):**
```text
Start the build. Mode: <Phase P | Phase E>. Lane: A. Clock: <H0 or "pre-event">. Hours available: <n>.
Event rules on pre-built code: <allowed | not allowed | unknown>.
Confirm the spec precedence, print the initial STATE LEDGER, and issue the AG-PROMPT for step <P1 | E0> (loop FULL or FAST per the catalogue).
```

**Message 2 → Antigravity:** paste Gem 1's AG-PROMPT. Make sure `/spec` holds the three spec files and `AGENTS.md` is in the repo root.

**Message 3 → Gem 2:** paste Antigravity's complete output (BUILD REPORT + AUDIT-REQUEST), attach the code if it is long. Then follow section 4.2 and 4.3.

Open the Lane B chats (`G1-B`, `G2-B`, `G3-B`) the same way when Person B starts.

---

## 9. One-page cheat sheet

```text
G1 ──AG-PROMPT──▶ ANTIGRAVITY ──REPORT+AUDIT-REQUEST──▶ G2 ──RED-TEAM REQUEST──▶ G3 ──DECISION PACKET──▶ G1
FAST: skip G3.   REJECT: G2 → G1 directly.   Gate steps: FULL + Gem 3 FULL attack.
Evidence or it didn't happen.  Attacks become tests.  Spec changes only with your approval.
Max 2 fix loops → then cut scope (T3 → T2 → T1).  Freeze at H22.  REAL_DATA=0 always.
```
