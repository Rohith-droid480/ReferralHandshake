# ReferralHandshake (Protocol RHP-1) — Master Execution, Build, Verification & Operations Playbook

**System:** Referral Handshake Protocol (RHP-1) + Reference Platform  
**Team:** MAHA YODHAS (2-Person Engineering Team: Person A / T1 & Person B / T2)  
**Event:** Colossus 3.0 — HealthTech Track (13–14 Nov 2026, Bengaluru; 24-Hour Build; 5-Minute Pitch with $\ge 30\text{ s}$ Live Demo `[V]`)  
**Data Mode:** Synthetic Only (`REAL_DATA=0`)  
**First Clinical Pathway:** Emergency Obstetric Referral across Karnataka-style tiers (`PHC -> CHC -> FRU / DH -> MC`); generic data model extensible to `NEONATAL`, `TRAUMA`, `CARDIAC`, and `STROKE`.

---

## 1. Authority Hierarchy, Architectural Locks & Tag Legend

### 1.1 Strict Input Precedence (Non-Negotiable)
Every ambiguity across project artifacts is resolved in this exact order of authority:
1. **`ReferralHandshake_LOCKED_Problem_Statement_v7.md`** — Highest authority on problem framing, evidence status tags, operational boundaries, and claims discipline.
2. **Primary Research Findings tagged `[V]`** — Verified quantitative and regulatory facts inside the source documents.
3. **`ReferralHandshake_v8_LOCKED_Solution.md`** — Authority on D1–D20 defect closures, 28 conformance scenarios, 40-item loophole ledger, and clinical/district operating model.
4. **`ReferralHandshake_FINAL_LOCKED_Architecture.md`** — Ultimate technical authority on F1–F20 architectural closures, I1–I16 invariants, 24-table PostgreSQL 16 DDL, 10-step `apply_command()` pipeline, timing math, Quint specification (`rhp1.qnt`), independent Python runtime monitor, and T0–T3 build tiers.
5. **`ReferralHandshake_3Gem_Antigravity_Workflow.md`** — Authority on multi-agent governance (`Gem 1 -> Antigravity -> Gem 2 -> Gem 3 -> Gem 1`), `AGENTS.md`, `STATE LEDGER`, and Lane A / Lane B separation.

### 1.2 Status & Evidence Tags
- **`[V]`**: Verified from primary research or official technical documentation.
- **`[V*]`**: Verified only from secondary, vendor, or legal-commentary sources (must be confirmed from primary text before appearing on a slide).
- **`[CONFLICT]`**: Research sources disagree (must state both bounds or quote only verified percentages).
- **`[GAP]`**: No reliable primary evidence found; treated strictly as a configurable policy parameter or pilot hypothesis, never a factual claim.
- **`[verify]`**: Pre-event verification test required (tracked in Section 4).
- **Weakness Status Tags**:
  - **`CLOSED`**: Enforced by a deterministic code/DB mechanism + verified by a named automated test.
  - **`BOUNDED`**: Technical residual explicitly quantified + guarded by a live runtime monitor alarm.
  - **`OPEN`**: Residual outside software control; assigned to a named owner with explicit closing evidence required prior to real-world use.

### 1.3 Ten Hard Architectural Locks
| Lock ID | Rule | Enforcement Mechanism |
|---|---|---|
| **L-01** | **Coherence Rule** | Every component in the repository must be (a) a state or event in the contract, (b) an interface producing or consuming those events, or (c) a read-only projection of the committed event log. Anything else is out of scope and must be deleted. |
| **L-02** | **Locked Stack** | Python 3.12, FastAPI, `psycopg3`, PostgreSQL 16 single writable primary (`synchronous_commit=on`, `READ COMMITTED` + explicit `SELECT ... FOR UPDATE`), React PWA (SSE with `Last-Event-ID`, $15\text{ s}$ heartbeats, bundled pure-JS `@noble/curves/ed25519` & `@noble/hashes/sha256`), Native Android Kotlin (`T3_EXTRAS`) / PWA GPS fallback (`T1_TRANSPORT`), Exotel outbound IVR (`T2_REACH`), Mapbox Directions/Matrix, Toxiproxy, Quint (`rhp1.qnt`). |
| **L-03** | **Banned Tech** | **NEVER** introduce blockchain, Kafka, Debezium, Redis, Kubernetes, WebSockets, WhatsApp, on-device LLMs, CRDTs for authoritative contract state, or floating-point numbers in RFC 8785 JCS canonical JSON. |
| **L-04** | **Global Lock Order (F1 / I14)** | Strictly `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`. Poller Phase 1 claims due deadlines in a single committed `UPDATE ... FOR UPDATE SKIP LOCKED` statement without holding referral locks; Phase 2 calls `apply_command(TIMEOUT)` which locks `referral` first. Enforced by PostgreSQL trigger `rhp_require_lock` checking session GUC `rhp.locked_referral`. |
| **L-05** | **Two Parallel Tracks (I3 / D1)** | Handshake track (`CREATED`, `OFFERED`, `ACKNOWLEDGED`, `ACCEPTED`, `COUNTERED`, `ESCALATED_TO_DISPATCHER`, `CANCELLED`, `CLOSED`) and Transport track (`REQUESTED`, `DISPATCHED`, `EN_ROUTE`, `ARRIVED`, `HANDED_OVER`, `TR_CANCELLED`) run independently. Transport never reads `hs_state` and never blocks care. `mgso4_status` (`GIVEN | NONE_GIVEN | UNKNOWN`) is answer-required, never knowledge-required, and never blocks dispatch. |
| **L-06** | **Single Lease & Offer Cap (I2 / I12 / F13)** | Optimistic row `version` (`412` on stale precondition) is separate from monotonic `lease_epoch` (`409` on lost race). Partial unique index `one_lease` on `offer(referral_id) WHERE status = 'ACCEPTED'`. Concurrent `open_offers` (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) $\le 2$ always. |
| **L-07** | **Unified Timing Bound (F2 / F3 / I13)** | Notice ladder rungs fire at $0$ (SSE + empty-payload FCM), $A/4$ (Exotel voice with AMD + press-1 gate, slot $i$ at $A/4 + i \cdot \delta$), and $3A/4$ (dispatcher proxy page) inside ACK window $A$. Worst-case escalation bound $T_{\max} = F \cdot (A + D + \epsilon) \le B$. Server time is monotone per referral via `GREATEST(clock_timestamp(), referral.head_ts)` (I16). |
| **L-08** | **Common-Mode Independence (F17)** | Person A (Lane A) authors the backend API, `transitions.yaml`, and Quint spec. Person B (Lane B) authors the independent Python runtime monitor from Section 3 invariant prose alone, in an isolated workspace that imports zero server modules and connects via read-only role `rhp_monitor`. |
| **L-09** | **Scratch DB Isolation (F20)** | `BROKEN_BUILD=1` routes only to `rhp_scratch_broken` (missing `one_lease` and code lease check). Process aborts with `exit(78)` if `REAL_DATA=1`, if DSN DB $\neq$ `rhp_scratch_broken`, or if the scratch DB role can connect to the primary DB. |
| **L-10** | **Claims Discipline (§19)** | Every number shown live on stage is measured live. Never claim mortality reduction, national prevalence, measured ambulance minutes saved in India, or forbidden buzzwords ("bullet-proof", "airtight", "zero loopholes", "mathematically proven system", "immutable log", "ABDM compliant", "BSA certified", "eliminates ping-pong"). |

---

## 2. Multi-Agent Build Governance: The 3-Gem + Antigravity Ring

### 2.1 Ring Topology & Division of Labor
To prevent LLM self-grading, hallucinated test passes, and silent spec drift during the 24-hour build, all product code is written by **Google Antigravity** under the supervision of a three-Gem verification ring:

```
                        +----------------------------------------------+
                        |     HUMAN OPERATORS (Person A & Person B)    |
                        |      Courier + Final Spec/Cut Authority      |
                        +----------------------------------------------+

  +-----------+  (1) AG-PROMPT   +---------------+  (2) BUILD REPORT +   +-----------+
  |   GEM 1   |----------------->|  ANTIGRAVITY  |      AUDIT-REQUEST    |   GEM 2   |
  | CONDUCTOR |                  | (Sole Builder)|---------------------->|  AUDITOR  |
  +-----------+                  +---------------+                       +-----------+
        ^                                                                      |
        |  (4) DECISION PACKET                     (3) RED-TEAM REQUEST        |
        |      (Attack tests + Fix list +              (Verdict + Defects +    v
        |       Ledger delta)                           Attack surfaces) +-----------+
        +----------------------------------------------------------------|   GEM 3   |
                                                                         | ADVERSARY |
                                                                         +-----------+
```

| Role | Owns | Input | Output | Strictly Prohibited From |
|---|---|---|---|---|
| **Gem 1 — CONDUCTOR** | Build sequence, step scoping, tier gates, scope cuts, `AG-PROMPT` generation, `STATE LEDGER` maintenance | `DECISION PACKET` from Gem 3 (or `SHORT-CIRCUIT` from Gem 2) | Updated `STATE LEDGER` + next `AG-PROMPT` | Writing product code; advancing with open `S1` defects; silently altering the spec. |
| **Antigravity — BUILDER** | Writing code, migrations, tests, and executing verification commands inside its assigned lane branch | `AG-PROMPT` from Gem 1 + repo `AGENTS.md` | Git commit/tag + `BUILD REPORT` + `AUDIT-REQUEST` | Touching files outside `FILES YOU MAY TOUCH`; claiming tests pass without raw output; editing `/spec`. |
| **Gem 2 — AUDITOR** | Line-by-line spec conformance, invariant mechanism check, lock-order review, test quality verification | `BUILD REPORT` + `AUDIT-REQUEST` + raw diffs/code | Audit table + `RED-TEAM REQUEST` (or `REJECT` short-circuit) | Writing code or fixes; planning next steps; approving anything without raw command output (`UNVERIFIED`). |
| **Gem 3 — ADVERSARY** | Concurrency/chaos/security red-teaming, challenging Gem 2's assumptions, claims linting, runnable attack test specs | `RED-TEAM REQUEST` from Gem 2 + HIGH-risk code | `DECISION PACKET` (`ADVANCE`, `FIX-THEN-ADVANCE`, `REDO`, `SPEC-QUESTION`) | Writing production code; changing scope; claiming `BREAKS` without an exact failure mechanism + runnable test. |

### 2.2 Loop Selection & Time Budgets
Gem 1 selects the loop mode and stamps it in the `AG-PROMPT` header:
1. **`FULL` Loop (`G1 -> AG -> G2 -> G3 -> G1`, target $20\text{–}25\text{ min}$):** Mandatory for all `HIGH` risk steps, all Tier Gate steps (`G0`, `G1`, `G2`, `G3`), and any `S1` blocker fix.
   - *HIGH-risk surfaces:* `apply_command()`, lock order / triggers, PostgreSQL DDL, idempotency, hash chain / witness / crypto, poller / outbox relay, PIN / session / enrollment auth, SSE per-event grant filtering, `BROKEN_BUILD` / `REAL_DATA` guards, Exotel voice ACK path.
2. **`FAST` Loop (`G1 -> AG -> G2 -> G1`, target $\approx 12\text{ min}$):** Permitted only for `LOW`/`MED` risk steps (UI styling, synthetic seed data, static copy, documentation) or `S2`/`S3` non-blocker fixes.
3. **`SHORT-CIRCUIT` (`G2 -> G1` directly, target $\approx 5\text{ min}$):** Triggered automatically whenever Gem 2 returns `VERDICT: REJECT` (code fails to run, raw test output missing, or forbidden files modified).

### 2.3 Two Parallel Lanes & Common-Mode Isolation (F17)
- **Lane A (Person A / T1 — Protocol, Backend & Formal Proof):** Runs chat threads `G1-A`, `G2-A`, `G3-A` and Antigravity workspace branch `lane-a`. Owns `db/`, `spec/`, `api/`, `witness/`, Quint model (`rhp1.qnt`), and concurrency/mutation test suites.
- **Lane B (Person B / T2 — Clients, Reach, Independent Monitor & Demo Ops):** Runs chat threads `G1-B`, `G2-B`, `G3-B` and two separate Antigravity workspaces:
  - `lane-b-monitor`: Isolated workspace for `monitor/` (Person B). **Must never have access to `api/` server source code**; reads only the PostgreSQL schema (§7), `transitions.yaml`, and Section 3 invariant prose.
  - `lane-b-clients`: Workspace for `pwa/`, Exotel voice adapter, paper code utility, and Guarantee Arena UI.

---

## 3. Copy-Paste Agent Configuration & Packet Templates

### 3.1 Knowledge Base Upload (All 3 Gems)
Before starting Phase P or Phase E, upload these exact four files into the Knowledge drawer of **Gem 1**, **Gem 2**, and **Gem 3**:
1. `ReferralHandshake_LOCKED_Problem_Statement_v7.md`
2. `ReferralHandshake_v8_LOCKED_Solution.md`
3. `ReferralHandshake_FINAL_LOCKED_Architecture.md`
4. `AGENTS.md` (copied from Section 3.3 below)

### 3.2 Gem System Instructions (Copy-Paste Verbatim)

#### Gem 1 — CONDUCTOR System Instructions
```text
You are CONDUCTOR for ReferralHandshake (team MAHA YODHAS, Colossus 3.0, 24-hour build, 2 students). Knowledge files are the LOCKED spec. Precedence: Problem v7 > Solution v8 > Architecture FINAL. Never contradict them. If something is not in them, say "NOT IN SPEC" and ask; never guess.

JOB: plan the build, write prompts for Google Antigravity (the only builder), keep the STATE LEDGER, decide advance/fix/cut. You NEVER write product code.

EVERY REPLY = (1) the updated STATE LEDGER, (2) one AG-PROMPT, (3) one line telling the user where to paste the result (Antigravity -> Gem 2).

AG-PROMPT must contain: header (STEP id, LANE A/B, LOOP FULL/FAST, RISK, loop count n), GOAL (1 sentence), SPEC ANCHORS (exact section numbers, invariant ids I1-I16, test ids T-xx), INPUT STATE (branch, last good commit), TASKS (numbered, atomic), FILES MAY TOUCH, FILES MUST NOT TOUCH, TESTS TO WRITE+RUN, MEASURABLE ACCEPTANCE, STOP CONDITIONS (ambiguity or failing test = stop and report, do not improvise), and the REQUIRED OUTPUT: a BUILD REPORT with raw command output pasted, then an AUDIT-REQUEST block for Gem 2.

INPUT YOU RECEIVE: a DECISION PACKET from Gem 3. Rules: advance only if zero open S1 defects and every MUST-FIX is closed with evidence. Turn every Gem 3 ATTACK into a test task in the next AG-PROMPT. Max 2 fix loops per step; on the 3rd, cut scope by tier order (T3, T2, T1; T0 never) or raise a SPEC-QUESTION to the user. Spec changes only via a SPEC-DEVIATION the user approves. Respect pre-event vs at-event work and the code freeze at H22. Keep real data out (REAL_DATA=0), never ask for secrets/keys in chat.

Use the step catalogue in the user's WORKFLOW file. Be terse. No praise.
```

#### Gem 2 — AUDITOR System Instructions
```text
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
```

#### Gem 3 — ADVERSARY System Instructions
```text
You are ADVERSARY for ReferralHandshake. Knowledge files are the LOCKED spec. You cannot run code; you reason from the spec and the pasted code, and you turn every attack into a RUNNABLE TEST for Antigravity. You NEVER fix code or decide scope.

INPUT: a RED-TEAM REQUEST from Gem 2 (verdict, defects, unverified list, attack surfaces).

DO:
1. ATTACK. For each attack: id A-n | scenario | which invariant/section it targets | expected behavior per spec | prediction BREAKS / HOLDS / UNKNOWN with the exact mechanism | a runnable test spec (inputs, steps, pass condition). Cover as relevant: concurrency/races (200-way accept, double timeout fire, outbox redelivery), crash/restart mid-transaction, network partition and replay, clock steps, stale/offline commands, idempotency edge cases, auth/PIN/session abuse, privacy leaks (PHI in logs/push/SSE), tamper and restore, broken-build isolation from real data.
2. CHALLENGE THE AUDITOR: what did Gem 2 miss, over-trust, or mark PASS without evidence? Name it.
3. CLAIMS + DEMO INTEGRITY: any claim, number or UI element that could be shown as real but is simulated or pre-computed? Anything breaking "every number shown live is measured live", or implying mortality / time-saved impact? Flag against the Claims Register.
4. FULL vs QUICK: at gates run FULL attack (all categories). Otherwise QUICK (top 5 attacks for this step).

OUTPUT = DECISION PACKET for Gem 1: verdict ADVANCE / FIX-THEN-ADVANCE / REDO / SPEC-QUESTION; merged fix list tagged MUST-FIX / SHOULD-FIX / LOG (each with severity S1-S4, spec reference, and the evidence that would close it); the attack tests to implement; any approved-risk candidates; ledger delta. Never report BREAKS without a mechanism. No praise.
```

### 3.3 Repository `AGENTS.md` & `CODEOWNERS`

#### `AGENTS.md` (Place in Repo Root)
```markdown
# AGENTS.md — ReferralHandshake Builder Rules
1. Spec files in `/spec` are READ-ONLY. Precedence: Problem v7 > Solution v8 > Architecture FINAL. Never reinterpret them.
2. Stack is locked: Python 3.12, FastAPI, psycopg3, PostgreSQL 16, React PWA, Pydantic `extra='forbid'`. Banned: blockchain, Kafka, Debezium, Redis, Kubernetes, WebSockets, WhatsApp, on-device LLM, CRDT for authoritative state, floats in JCS JSON.
3. Only do what the current AG-PROMPT says. Touch only the files it lists. If something is ambiguous or a test cannot pass: STOP and report. Do not improvise or "make it work".
4. `REAL_DATA=0` always. Synthetic data only. Never put keys/secrets in code or in reports; use `.env`.
5. Every step ends with a git commit tagged `step-<ID>-loop<n>`. Rollback = last tag marked good.
6. Never claim a test passes without pasting the raw command and its output.
7. If you deviate from the spec in any way, list it under DEVIATIONS in the report. Silent deviation is a failure.
8. Contract writes go only through `apply_command()` following global lock order `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`; no other path writes referral/offer/deadline/event state.
9. The Python monitor (`monitor/`, Lane B) must NOT import or read server code (`api/`); it reads only the DB event log (`rhp_monitor` read-only role) and §3 prose.

## BUILD REPORT Format (End Every Task With This Exact Order)
STEP / LOOP / commit hash
FILES CHANGED (`git diff --stat`)
CODE: full text of every file marked HIGH risk (or `git diff` if >300 lines)
COMMANDS RUN + RAW OUTPUT (pasted verbatim, never summarised)
TESTS: name | pass/fail | measured numbers
NOT DONE / SKIPPED
DEVIATIONS FROM SPEC (or "none")
ASSUMPTIONS
OPEN QUESTIONS
SELF-RATED RISK + the 3 things most likely to be wrong
Then output the `=== AUDIT-REQUEST FOR GEM 2 ===` block.
```

#### `.github/CODEOWNERS` (Enforces F17 & Reward-Hacking Prevention)
```text
# Frozen specification and schema (Person A human approval required; AI agents may not edit to pass CI)
/spec/                          @person-a
/db/schema.sql                  @person-a

# Independent runtime monitor (Person B human approval required; isolated from server code)
/monitor/                       @person-b
```

### 3.4 Handoff Packet Templates (Copy-Paste Formats)

#### Packet 0: `STATE LEDGER` (Maintained by Gem 1 in Every Reply)
```text
=== STATE LEDGER v<n> ===
Clock: H<hh> of 24 (or Phase P) | Lane A step: <id> | Lane B step: <id>
Gates:  G0(T0)[ ]  G1(T1)[ ]  G2(T2)[ ]  G3(rehearsal)[ ]  FREEZE H22[ ]
Done steps: <ids with last good git tag>
Open defects: <D-id [S1|S2|S3|S4] short title> ...
Accepted risks (user-approved): <R-id with stated bound>
Approved spec deviations: <none | SD-id>
Last good commit/tag: <lane A tag> / <lane B tag>
Cut so far: <none | T3 ...>
Next 3 steps: <ids>
```

#### Packet 1: `AG-PROMPT` (Gem 1 $\to$ Antigravity)
```text
=== AG-PROMPT | STEP <id> | LANE <A|B> | LOOP <FULL|FAST> #<n> | RISK <LOW|MED|HIGH> ===
Read AGENTS.md first. You are the builder only.
GOAL: <one sentence>
SPEC ANCHORS: <§ numbers>, <I# invariants>, <F# closures>, <T-# tests>
INPUT STATE: branch <x>, last good tag <y>, existing: <what already works>
TASKS:
 1. <atomic task 1>
 2. <atomic task 2>
FILES YOU MAY TOUCH: <explicit file paths>
FILES YOU MUST NOT TOUCH: <explicit file paths, always including /spec>
TESTS TO WRITE AND RUN: <test names and commands>
ATTACK TESTS FROM LAST RED-TEAM (implement now): <A-ids with test specs, or "none">
ACCEPTANCE (measurable): <exact pass criteria and numeric thresholds>
STOP IF: spec is ambiguous, a test cannot pass, or you need to touch a forbidden file.
LEDGER: <one-line ledger summary>
WHEN DONE, OUTPUT IN THIS ORDER:
 (1) BUILD REPORT in the format from AGENTS.md (raw outputs pasted; full code of HIGH-risk files),
 (2) a block that starts with the line "=== AUDIT-REQUEST FOR GEM 2 ===" containing: step, loop, spec anchors, acceptance list, the BUILD REPORT, and the prompt "Audit this against the anchors."
```

#### Packet 2: `RED-TEAM REQUEST` (Gem 2 $\to$ Gem 3)
```text
=== RED-TEAM REQUEST | STEP <id> | LOOP <FULL|FAST> #<n> ===
VERDICT: PASS | PASS-WITH-NOTES | FAIL | REJECT
EVIDENCE CHECK: <ok | exact missing raw outputs>
CONFORMANCE SUMMARY: <n MATCH / n PARTIAL / n MISSING / n DEVIATES> + full rows for any non-MATCH
INVARIANTS TOUCHED: <I# -> exact enforcement mechanism in file:line | ABSENT>
DEFECTS:
 D-1 [S1|S2|S3|S4] <title> | spec <§/I#> | evidence <file:line> | expected <behavior>
UNVERIFIED (not shown in report): <list>
TOP 5 ATTACK SURFACES:
 1. ...
 2. ...
 3. ...
 4. ...
 5. ...
ATTACH: full code/diff of HIGH-risk files from the report
LEDGER: <one-line ledger summary>
```

#### Packet 3: `DECISION PACKET` (Gem 3 $\to$ Gem 1)
```text
=== DECISION PACKET | STEP <id> | LOOP #<n> | MODE <FULL|QUICK> ===
VERDICT: ADVANCE | FIX-THEN-ADVANCE | REDO | SPEC-QUESTION
ATTACKS:
 A-1 | <scenario> | targets <I#/§> | spec says <...> | BREAKS/HOLDS/UNKNOWN because <exact mechanism>
     TEST SPEC: inputs <...>; steps <...>; pass condition <...>
AUDITOR CHALLENGE: <what Gem 2 missed, over-trusted, or marked PASS without raw evidence>
CLAIMS/DEMO INTEGRITY: <flags against §19 Claims Register or "clean">
FIX LIST:
 MUST-FIX   [S1] <issue> | spec <§> | closes when <measurable test evidence>
 SHOULD-FIX [S2/S3] <issue> | spec <§> | closes when <evidence>
 LOG        [S4] <issue>
RISK-ACCEPT CANDIDATES: <items for human approval with stated technical bound>
LEDGER DELTA: <updates to apply to STATE LEDGER>
```

### 3.5 Kickoff Messages (Start Here)
To launch **Lane A**, paste this into a fresh **Gem 1 (`G1-A`)** chat:
```text
Start the build. Mode: <Phase P | Phase E>. Lane: A. Clock: <H0 or "pre-event">. Hours available: 24.
Event rules on pre-built code: <allowed | not allowed | spec-only>.
Confirm the spec precedence (Problem v7 > [V] research > Solution v8 > Architecture FINAL > Workflow), print the initial STATE LEDGER v1, and issue the AG-PROMPT for step <P1 | E0> (loop FULL or FAST per the step catalogue).
```
To launch **Lane B**, paste the identical message into **Gem 1 (`G1-B`)** with `Lane: B` and step `<P4 | E0>`.

---

## 4. Pre-Event Preparation & Verification Runbook (Phase P & §21)

### 4.1 Pre-Event Verification Checklist (§21 `[verify]` Gates)
Execute all 12 checks before the 24-hour clock starts. If any primary check fails, lock in the pre-decided fallback immediately.

| # | Verification Item | Time Box | Exact Test Procedure | Pre-Decided Fallback if Test Fails |
|---|---|---|---|---|
| 1 | Event rules on pre-built work & AI-assisted coding | $1.0\text{ h}$ | Read official Colossus 3.0 rulebook; confirm with organizers in writing. | Keep only Phase P spec/document artifacts pre-event; generate 100% of product code during the 24-hour window. |
| 2 | Exotel trial concurrency, DTMF `%23`, and AMD behavior | $1.5\text{ h}$ | Trigger 5 concurrent outbound calls to whitelisted team phones + 1 call to a voicemail box; enter PIN + `#`. | Switch profile stagger $\delta$ to sequential calls; use PWA QR desks for judge interaction. |
| 3 | Exotel webhook latency $\le 5\text{ s}$ under load `[V]` | $30\text{ min}$ | Replay 20 signed Exotel webhook callbacks concurrently against local tunnel; assert HTTP 200 $< 2.0\text{ s}$. | Return immediate "please hold" IVR applet response at $1.5\text{ s}$ and read committed state on next callback. |
| 4 | LAN HTTP + QR camera scan on iOS Safari | $30\text{ min}$ | Scan `http://192.168.x.x:3000/join?jti=...` from an iPhone camera on a phone hotspot with cellular data off. | Use Cloudflare tunnel domain (`https://...`) or pre-installed local root CA on demo devices. |
| 5 | Pure-JS Ed25519 & SHA-256 speed on iPhone Safari | $30\text{ min}$ | Run `@noble/curves/ed25519` + `@noble/hashes/sha256` verification over a 50-event chain + Merkle proof in Mobile Safari. | Display labelled server-side verification alongside raw downloadable JSON proof bundle. |
| 6 | Quint / Apalache model checker at $F=3, E=4$ | $1.0\text{ h}$ | Run `quint run rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000` and `quint verify rhp1.qnt --invariant safety`. | If Apalache JVM startup/verification exceeds $10\text{ min}$, run `quint run` simulator + Python explicit-state BFS explorer over `transitions.yaml`. |
| 7 | Mapbox Matrix API rate limits & API key | $30\text{ min}$ | Issue 1 `mapbox/driving` Matrix request ($25\text{ coords}$, limit $60\text{ req/min}$) and 1 `driving-traffic` request ($10\text{ coords}$, limit $30\text{ req/min}$) `[V]`. | Serve cached synthetic ETAs labelled `"ETA cached / synthetic"` in UI. |
| 8 | Android foreground location service soak | $2.0\text{ h}$ | Run `FOREGROUND_SERVICE_TYPE_LOCATION` with screen off for $2\text{ hours}$ on demo Android phone; log GPS heartbeat gaps. | Use Tier T1 PWA foreground GPS (`watchPosition`) + manual `"Update Location"` button on stage. |
| 9 | DPDP Rules 2025 commencement date conflict `[CONFLICT]` | $1.0\text{ h}$ | Inspect official Gazette notification text (13 Nov 2025 vs 14 Nov 2025 `[CONFLICT]`; core obligations 13/14 May 2027 `[V]`). | Cite both dates or conservatively state `"notified mid-November 2025 (core obligations May 2027)"`. |
| 10 | DPDP emergency clause citation (`s.7(f)` vs `s.7(d)`) `[CONFLICT]` | $30\text{ min}$ | Verify exact section letter in the Gazette Act text. | Cite as `"DPDP Act Section 7 emergency medical processing provision"` without hardcoding an unverified letter on slides. |
| 11 | Das et al. (2023) Maharashtra denominator `[CONFLICT]` | $30\text{ min}$ | Check paper tables for $25,253$ vs $28,020$ referred deliveries ($47\%, 37\%, 60\%$ reproduce only with $25,253$). | Quote only the verified percentages ($47\%$ phoned, $37\%$ documented, $60\%$ tracked) `[V]`. |
| 12 | Chrony slew-only clock behavior & NTP offset alarm | $30\text{ min}$ | Configure chrony without post-boot `makestep`; inject a $3\text{ s}$ clock offset in test container; verify monitor `ntp_offset_ms > 2000` alarm. | Trigger simulated clock-step fault via test harness parameter during Guarantee Arena demo. |

### 4.2 Phase P Step Catalogue (Pre-Event Spec Artifacts Only)
| Step ID | Lane | Artifact | Spec Anchors | Risk | Loop Mode | Gate / Verification Command |
|---|---|---|---|---|---|---|
| **P1** | A | `spec/transitions.yaml` + 28 conformance vectors (§4.8) | §4, §5 | `HIGH` | `FULL` | `python3 scripts/validate_transitions.py` (BFS reachability `T-F6`) |
| **P2** | A | `db/schema.sql` (24-table PostgreSQL 16 DDL + triggers + roles) | §7, F1, F4, F9, I1–I16 | `HIGH` | `FULL` | Load into PG16; run `ST-3` `pg_constraint` & trigger scan (`T-F4`) |
| **P3** | A | `spec/rhp1.qnt` (Quint formal specification) | §12, I1, I2, I3, I12, I13 | `HIGH` | `FULL` | `quint run rhp1.qnt --invariant safety --max-samples 20000` + vacuity checks fail |
| **P4** | B | `spec/profiles.json` + Ed25519 signature + `T_max` validator | §6, F2, F3, I13 | `MED` | `FULL` | `python3 scripts/validate_profiles.py` (`T-F2`, `T-F3`) |
| **P5** | B | `db/seed_synthetic.sql` (`REAL_DATA=0` Karnataka tier seed) | §2, §7, §9, §10 | `LOW` | `FAST` | Load seed on top of `db/schema.sql`; verify 0 real PII tokens |
| **P6** | B | Pre-event verification report (§21 checklist execution log) | §21 | `LOW` | `FAST` | All 12 rows logged with measured outputs or active fallback |

---

## 5. 24-Hour At-Event Build Playbook (Phase E, Tiers T0–T3 & Cut Lines)

### 5.1 Feature Tiers & Strict Cut Order (§2, F16)
Every feature sits behind an environment flag. If any step fails **3 loops** or the clock slips behind schedule, Gem 1 cuts strictly from the bottom up (**Cut 1st: `T3_EXTRAS` $\to$ Cut 2nd: `T2_REACH` $\to$ Cut 3rd: `T1_TRANSPORT` $\to$ Never Cut: `T0`**).

| Tier | Feature Flag | Scope & Deliverables | Cut Priority |
|---|---|---|---|
| **T0** | Always ON | FastAPI `apply_command()` (10 steps), PostgreSQL 16 primary (24 tables), 2-phase Poller, Outbox Relay, React PWA receiving desks with rotating QR admission, SSE with `Last-Event-ID` & per-event grant authz, Independent Python Runtime Monitor (Person B), Separate-OS-user Ed25519 Witness/Signer, Pure-JS Browser Verifier, `BROKEN_BUILD=1` scratch DB isolation. | **NEVER CUT** (Core MVP + Guarantee Arena) |
| **T1** | `T1_TRANSPORT=1` | Parallel Transport track (`TR_UPDATE`, `TR_DESTINATION_CHANGE`, 6 arrival cases), PWA ambulance client with foreground GPS + manual fallback, Dispatcher Console with proxy entry (`proxy=true`, `proxy_for`) & override, Time-scrubber Replay UI. | **Cut 3rd** (Protect T0 first) |
| **T2** | `T2_REACH=1` | Outbound Exotel Voice IVR (`NOTICE_VOICE` at $A/4$, AMD + press-1 gate, Kannada/Hindi/English pre-recorded prompts, DTMF PIN), DLT-compliant static SMS stub, 9-char Crockford Base32 + mod-37 Paper Code linking & printable card-as-slip. | **Cut 2nd** (If telephony stalls, fallback to recorded clip + PWA desk) |
| **T3** | `T3_EXTRAS=1` | Native Kotlin Android ambulance app (`FOREGROUND_SERVICE_TYPE_LOCATION`, Room outbox), AI Intake Accelerator with Cognitive Forcing Function (`423 ANCHOR_REQUIRED` until `need_class` + `mgso4_status` committed), FHIR R4 (`ServiceRequest`, `Task`, `Encounter`, `Communication`) & IEEE 1849 XES exporters. | **Cut 1st** (Build only after `G0`, `G1`, `G2` are green) |

### 5.2 Hour-by-Hour Execution Schedule (H00 to H24)
| Step ID | Clock | Lane A (Person A — Backend & Proof) | Lane B (Person B — Clients, Monitor & Demo) | Risk | Loop | Gate |
|---|---|---|---|---|---|---|
| **E0** | `H00–H02` | `docker-compose.yml` up, load `db/schema.sql` & `db/seed_synthetic.sql`, `transitions.yaml` loader, startup profile validator (`I13`). | React PWA scaffold, rotating QR admission (`jti`, $20\text{ s}$ TTL, cap 20 desks), session/enrollment ticket endpoints. | `MED` | `FAST` | — |
| **E1** | `H02–H06` | `apply_command()` steps 1–10: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `DECLINE`, `REVOKE_GRANT`, `I14` lock GUC, savepoint rejection logging. | Receiving Desk UI (priority queue without countdown clocks, red `mgso4_status=UNKNOWN` banner), SSE hub with `Last-Event-ID`, $15\text{ s}$ heartbeats, and `GRANT_REVOKED` frame stripping. | `HIGH` | `FULL` | — |
| **E2** | `H06–H09` | Stateless 2-phase Poller (`CLAIM` + `apply_command(TIMEOUT)`), Outbox Relay ($30\text{ s}$ visibility timeout), unified notice ladder rungs ($0, A/4, 3A/4$), `SOFT_OPEN` & `PARALLEL2` rules. | Guarantee Arena Big Screen UI + **Independent Python Runtime Monitor** (`monitor/monitor.py` in isolated workspace, `rhp_monitor` role, differential check + `I1–I16`). | `HIGH` | `FULL` | — |
| **E3** | `H09–H12` | RFC 8785 JCS SHA-256 event hash chain, envelope encryption (`key_version`, `clinical_payload`, `event_secret`), `rhp-sign` witness process ($5\text{ s}$ binary Merkle checkpoints + O(log N) inclusion proof API). | Pure-JS Browser Verifier (`@noble/curves/ed25519`, `@noble/hashes/sha256`) on judge QR page (`CHECKPOINT_SIG`, `BROKEN`, `SEQ_GAP`, `ROOT_MISMATCH`, `TRUNCATED`). | `HIGH` | `FULL` | — |
| **E4** | `H12–H14` | `race200` 200-way asyncio barrier test (`T-C1`), lock-order deadlock test (`T-F1`), mutation suite `M1–M6` (`T-F17`), Toxiproxy chaos script. | `BROKEN_BUILD=1` scratch DB script (`scripts/make_scratch.sh`), exit 78 safety guards (`T-F20`), flashing red banner on Big Screen. | `HIGH` | `FULL` | **G0 (`T0` Pass)** |
| **E5** | `H14–H17` | `COUNTER`, `CONFIRM_COUNTER`, `ARRIVAL_REJECTED`, `DISPATCHER_ASSIGN`, `TR_UPDATE`, `TR_DESTINATION_CHANGE`, 6 arrival cases (`F5`), 2-stage `CLOSURE` (`F6`). | Dispatcher Console (proxy entry, override with reason enum), PWA Ambulance GPS tracker, Referral Replay time-scrubber. | `HIGH` | `FULL` | **G1 (`T1` Pass)** |
| **E6** | `H17–H20` | Full idempotency edge-case matrix (`T-F14`), offline stale confirmation rejection (`409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`, `T-F12`), Argon2id autonomous PIN failure counter (`T-F7`). | Outbound Exotel Voice IVR (`inbox` dedupe, AMD + press-1 gate, $<2\text{ s}$ webhook budget), 9-char Crockford Base32 + mod-37 Paper Code entry & printable slip. | `HIGH` | `FULL` | **G2 (`T2` Pass)** |
| **E7** | `H20–H22` | Fix any defects surfaced in `G0–G2`; run 10-minute randomized Hypothesis + Toxiproxy soak test; verify zero invariant violations. | Record 4 fallback MP4 clips (`Clip A`, `Clip B`, `Clip C`, `Clip D`); run 3 full dress rehearsals of the $30\text{ s}$ proof loop & 5-minute pitch. | `MED` | `FULL` | **G3 (Rehearsal)** |
| **E8** | `H22–H24` | **HARD CODE FREEZE AT H22.** Config-only tuning, DB snapshot backup, pre-flight verification. | Stage setup: primary phone hotspot + venue Wi-Fi, Cloudflare tunnel + LAN-QR fallback, feature phone charged, witness laptop running. | `LOW` | `FAST` | **FREEZE** |

### 5.3 Tier Acceptance Gates (§24 Definition of Done)
Gem 1 must not mark a gate passed until Antigravity pastes the raw command output proving every metric below:

1. **Gate G0 (`T0` Acceptance):**
   - `race200` (`T-C1`): Exactly $1$ of $200$ concurrent `ACCEPT` requests returns HTTP `200`; remaining $199$ return `409`/`412`/`429`; `SELECT count(*) FROM offer WHERE referral_id=$1 AND status='ACCEPTED'` $= 1$; `SELECT max(seq)-count(*) FROM event WHERE referral_id=$1` $= 0$ (gap-free); PostgreSQL `pg_stat_database.deadlocks` delta $= 0$.
   - Mutation Suite (`T-F17`): Mutations `M1` through `M6` each trip their designated detector within $\le 1\text{ cycle}$.
   - Continuous Monitor: $0$ violations across a $10\text{-minute}$ randomized Hypothesis stateful run with Toxiproxy fault injection.
   - Formal Model: `quint run rhp1.qnt --invariant safety --max-samples 20000` passes; vacuity checks (`not (hs == "ACCEPTED")`, `not (hs == "DISPATCH")`, `not (hs == "CLOSED")`, `not (off.get(1) == "SOFT")`) all fail as expected.
   - Tamper Verifier (`T-F8`): Direct `psql` superuser edit on scratch DB causes browser verifier to output `BROKEN referral=<id> seq=<n> kind=HASH`.
   - Broken Build (`T-F20`): `BROKEN_BUILD=1` on `rhp_scratch_broken` allows 2 leases and turns monitor red (`I2`) in $\le 2\text{ s}$; switching back to `BROKEN_BUILD=0` restores green.
   - Escalation Bound (`T-F3`): `DEMO_FAST` silence-to-dispatcher measured end-to-end $\le 25\text{ s}$ ($T_{\max} = 24\text{ s} \le B = 25\text{ s}$).
2. **Gate G1 (`T1` Acceptance):**
   - Proxy Equivalence: Dispatcher proxy entry and direct clinician/EMT API entry produce identical `referral` state transitions and `event` sequences across $20$ paired runs.
   - Chain Exhaustion Recovery: Dispatcher console assigns destination via `DISPATCHER_ASSIGN` (`source='DISPATCHER'`, `proxy=true`) after `ESCALATED_TO_DISPATCHER`.
   - Deterministic Replay: Time-scrubber replay reconstructs the exact terminal state from `event` rows alone.
3. **Gate G2 (`T2` Acceptance):**
   - Voice Commit Integrity: $20/20$ Exotel voice `ACK`s are recorded in `event` only after the DB transaction commits; voicemail calls produce $0$ `ACK`s across $5$ trials (`T-F7`); webhook latency $p95 \le 2.0\text{ s}$.
   - Paper Code Checksum: $100\%$ of single-symbol mutations and adjacent transpositions rejected across $1,000$ mutated 9-character Crockford Base32 + mod-37 codes.
4. **Gate G3 (`T3` Acceptance — Optional if Reached):**
   - Android Foreground Service: Continuous GPS logging $\ge 2\text{ hours}$ with screen off on demo phone.
   - Cognitive Forcing Function (`T-A1`, `T-A2`): Draft endpoint returns `423 ANCHOR_REQUIRED` before `need_class` and `mgso4_status` are committed; 20-slip seeded-error test achieves critical-error rubber-stamp rate $\le 5\%$ and silent-omission rate $\le 1\%$.
   - Interop Validation: Exported FHIR R4 bundle (`ServiceRequest`, `Task`, `Encounter`, `Communication`) passes schema validation.

---

## 6. Technical Verification & Mutation Testing Playbook

### 6.1 Invariants I1–I16 Master Verification Matrix (§3)
| Inv | Type | Formal Predicate | Primary Enforcement | Independent Monitor Check (`rhp_monitor`) | Test ID |
|---|---|---|---|---|---|
| **I1** | Liveness | Every non-terminal referral has $\ge 1$ `PENDING` deadline and a responsible role; overdue deadlines acted on within $\tau$. | `DEFERRABLE INITIALLY DEFERRED` constraint trigger `i1_pending_deadline` on `referral` at `COMMIT`. | `SELECT referral_id FROM deadline WHERE status='PENDING' AND due_at < clock_timestamp() - TAU_MS` ($\tau = 2\text{ poll intervals} + 2000\text{ ms}$). | `T-I1` |
| **I2** | Safety | At most $1$ active ownership lease per referral; `lease_epoch` strictly increases on each grant/revoke. | Partial unique index `one_lease ON offer(referral_id) WHERE status='ACCEPTED'` + `SELECT ... FOR UPDATE` on `referral`. | Fold `event` stream: flag if active lease count $> 1$ or `LEASE_GRANTED.epoch <= prev_epoch`; compare derived `epoch` with `referral.lease_epoch`. | `T-I2` |
| **I3** | Safety | Transport updates (`TR_UPDATE`, `TR_DESTINATION_CHANGE`) are accepted in every non-terminal `hs_state`. | `TR_UPDATE` handler checks only `hs_state NOT IN ('CLOSED','CANCELLED')` and valid `tr_state` progression; never gates on handshake state. | Scan `rejected_command` for `TR_UPDATE` where `reason_code` is not terminal or invalid `tr_state` transition. | `T-I3` |
| **I4** | Safety | Each `event_id` appears once; per-referral `seq` is gap-free ($1, 2, \dots, n$). | `idempotency` PK `(actor_id, key)`, `event.event_id UNIQUE`, `PRIMARY KEY (referral_id, seq)`, trigger `rhp_event_guard`. | Fold `event` stream ordered by `seq`: flag if `e.seq != st.seq + 1` or duplicate `event_id`. | `T-I4` |
| **I5** | Safety | Hash chain & checkpoint signatures verify; `CLOSED`/`CANCELLED` always carries an `outcome`. | Append-only triggers `event_ao`/`checkpoint_ao`, `rhp_event_guard`, `referral` CHECK `(hs_state IN ('CLOSED','CANCELLED')) = (outcome IS NOT NULL AND closed_at IS NOT NULL)`. | Recompute `SHA256(prev_hash || JCS(core))` for every event; compare final `(seq, hash)` with `referral.(head_seq, head_hash)` and signed Merkle root. | `T-I5` |
| **I6** | Safety | Every `ACCEPT`, `COUNTER`, `DECLINE` originates from a rostered role, registered device/number, and verified PIN, or is flagged `proxy=true`. | `apply_command()` Steps 2, 3, and 5 (`load_session`, `argon2_verify`, `authorize`). | Verify `event.actor_roster_id` has an active `roster` window `[valid_from, valid_to]` covering `server_ts` or `proxy=true`. | `T-I6` |
| **I7** | Safety | System-chosen offer targets belong to `referral.chain`; out-of-chain offers require `source='DISPATCHER'`. | BEFORE INSERT trigger `offer_chain_guard` on `offer`. | Flag any `offer` where `source='CHAIN'` and `facility_id != ALL(referral.chain)`. | `T-I7` |
| **I8** | Safety | Commands with stale `expected_version` or `expected_epoch` are never applied and are logged. | `apply_command()` Step 5 (`fence()`) rolls back to `SAVEPOINT sp_cmd` and inserts into `rejected_command` (`412`). | Flag any committed `event` where `event.epoch < prior_epoch` + verify `rejected_command` audit rows. | `T-I8` |
| **I9** | Safety | A facility is targeted at most once per referral (no $A \to B \to A$ referral loops). | `UNIQUE (referral_id, facility_id)` constraint on `offer`. | Track seen `facility_id` set per referral during `OFFER_CREATED` fold; flag duplicates. | `T-I9` |
| **I10** | Safety | Clinical payload frames are delivered only to subscribers holding an active (unrevoked) `payload_grant`. | SSE emitter checks `payload_grant.revoked_at IS NULL` on every frame and $15\text{ s}$ heartbeat; emits `GRANT_REVOKED` control frame on revocation. | Audit SSE emission log against `payload_grant.revoked_at` timestamps. | `T-I10` |
| **I11** | Safety | `event.detail` contains only allowlisted keys per `event.type` with boolean, $\le 12\text{-digit}$ integer, UUID, or uppercase enum values (no free-text PHI). | Pydantic `Literal` schemas (`extra='forbid'`) + PostgreSQL immutable CHECK `rhp_detail_ok(type, detail)`. | Scan `event.detail` across all rows for non-allowlisted keys or regex violations. | `T-I11` |
| **I12** | Safety | At most $2$ open offers (`OPEN`, `ACKED`, `COUNTERED`, `SOFT_OPEN`) exist per referral at any instant. | `referral.open_offers CHECK (open_offers BETWEEN 0 AND 2)` maintained under `referral` lock. | Count offers in `('OPEN','ACKED','COUNTERED','SOFT_OPEN')` per referral; flag if $> 2$ or $\neq$ `referral.open_offers`. | `T-I12` |
| **I13** | Safety | Configured worst-case escalation time $T_{\max} = F \cdot (A + D + \epsilon) \le B$ for the active profile; demo profiles refuse boot if `REAL_DATA=1`. | Startup `validate(profile, REAL_DATA)` check + Ed25519 cold-key signature check on profile JSON. | Recompute `F * (A + D + eps) <= B` on startup and on `/healthz`. | `T-I13` |
| **I14** | Safety | No contract-state write (`referral`, `offer`, `deadline` status/due, `event`, `payload_grant`, `outbox` insert) occurs without holding the `referral` row lock. | PostgreSQL trigger `rhp_require_lock` verifying `current_setting('rhp.locked_referral', true) = referral_id`. | Monitor `pg_stat_database.deadlocks` delta $= 0$ and `log_lock_waits`. | `T-I14` |
| **I15** | Safety | No ownership lease is granted if any required capability confirmation in `offer_resource_confirmation` has `expires_at <= server_ts`. | `apply_command()` Step 7 (`check_confirmations`) rejects with `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED`. | Join `OFFER_ACCEPTED` events with `offer_resource_confirmation` and `need_class_requirement`; flag if $\min(\text{expires\_at}) \le \text{server\_ts}$. | `T-I15` |
| **I16** | Safety | Per-referral `server_ts` is monotonically non-decreasing (`server_ts >= prior_server_ts`). | `ts = GREATEST(clock_timestamp(), referral.head_ts)` under `referral` lock + trigger `rhp_event_guard`. | Fold `event` stream per referral: flag if `e.server_ts_us < st.ts`. | `T-I16` |

### 6.2 Six Mutation Tests Runbook (`T-F17`)
To prove the verification suite and Person B's runtime monitor catch real bugs (and are not vacuous), run `scripts/run_mutations.sh` at Gate `G0`. Each mutation temporarily injects a single defect into a throwaway test run; the suite **passes only if the named detector fails/trips**.

| Mutation ID | Injected Fault | Target Artifact | Required Detector That Must Trip | Expected Violation Signal |
|---|---|---|---|---|
| **M1** | Comment out `expected_epoch` check in `fence()` (Step 5 of `apply_command`). | `api/commands.py` | Conformance vector `V-STALE-EPOCH` + Python Monitor | Monitor emits `("I8", referral_id, seq)` on applied stale epoch. |
| **M2** | Remove `FOR UPDATE` on `referral` and run against scratch schema without `one_lease`. | `api/commands.py` + `rhp_scratch_broken` | `T-C1 race200` barrier test + Python Monitor | `race200` sees $>1$ HTTP `200`; Monitor emits `("I2", referral_id, seq)`. |
| **M3** | Make Poller hold `SELECT ... FOR UPDATE` on `deadline` across the call to `apply_command(TIMEOUT)` while concurrent `ACCEPT`s run. | `api/poller.py` | `T-F1 lock_order_200way` | PostgreSQL raises deadlock (`40P01`) or `I14_LOCK_NOT_HELD`; deadlock delta $> 0$. |
| **M4** | Remove `nOpen(m1) > 0` / cap guard in Quint `decline`/`timeout` so a 3rd offer opens simultaneously. | `spec/rhp1.qnt` | `quint run rhp1.qnt --invariant safety` | Quint produces a counterexample trace violating `I12` (`nOpen(off) > 2`). |
| **M5** | Overwrite `prev_hash = b'\x00' * 32` on `seq = 2` inside `append_event()`. | `api/events.py` | Trigger `rhp_event_guard` (if enabled) + Browser Verifier + Python Monitor | DB raises `CHAIN_BREAK seq=2`; if trigger bypassed in test, Verifier prints `BROKEN referral=... seq=2 kind=PREV` and Monitor emits `("I5", referral_id, 2)`. |
| **M6** | Skip `expires_at > ts` check inside `check_confirmations()` (Step 7 of `apply_command`). | `api/commands.py` | Conformance vector `V-STALE-CONFIRM` + Python Monitor | Vector fails (gets `200` instead of `409`); Monitor emits `("I15", referral_id, seq)`. |

---

## 7. Live Demo & Stage Operations Playbook (The Guarantee Arena)

### 7.1 Pre-Flight Checklist (Execute at `H22:30` and `T-30 min` Before Pitch)
- [ ] **Environment Locks:** `REAL_DATA=0`, `PROFILE=DEMO_FAST`, `BROKEN_BUILD=0` verified on `/healthz`.
- [ ] **Database Clean Slate:** Fresh synthetic seed loaded (`db/seed_synthetic.sql`); `pg_stat_database` deadlock baseline recorded; `rhp_scratch_broken` initialized via `scripts/make_scratch.sh`.
- [ ] **Services Green:** `pg`, `api`, `poller`, `relay`, `monitor` (UID `1001`), `witness` (UID `1002`), `toxiproxy`, `pwa`, and `tunnel` containers running; all 4 worker heartbeats (`POLLER`, `RELAY`, `MONITOR`, `WITNESS`) $< 5\text{ s}$ old on Big Screen.
- [ ] **Dual Network & Admission:** Primary laptop connected to mobile hotspot; Cloudflare tunnel active; rotating QR code (`15\text{ s}` rotation, `20\text{ s}` JTI validity, cap 20 desks) tested on 2 phones; local LAN-QR fallback script (`scripts/switch_lan_mode.sh`) armed.
- [ ] **Hardware & Telephony:** Feature phone charged to $100\%$, ringer volume maximum, whitelisted in Exotel console; Exotel trial balance verified; Android phone GPS active.
- [ ] **Fallback Media Armed:** VLC / browser tabs pre-loaded and paused at frame 0 for `Clip A` (QR Join + Voice Ring), `Clip B` (200-way Race + Single Lease), `Clip C` (`BROKEN_BUILD=1` Red Alarm + Switch Back), and `Clip D` (`psql` Tamper + Browser Verifier Proof).

### 7.2 The Mandatory 30-Second Live Proof Loop (`DEMO_FAST`, F16)
Colossus 3.0 requires a live demonstration of at least $30\text{ seconds}$ inside the 5-minute pitch `[V]`. Execute this exact sequence first so the core proof is banked even if time runs short:

| Window | Operator Action (T1 = Pitch / Voice, T2 = Keyboard) | Live Screen & Judge Phone Output | Instant Fallback |
|---|---|---|---|
| **$0\text{–}4\text{ s}$** | **T1:** Invites 2 judges to scan the rotating QR on the Big Screen. **T2:** Triggers `race200` background swarm alongside the 2 judge desks (`D1`, `D2`). | Two judge browsers join as competing hospital desks (`D1`, `D2`; admission counter shows `2/20`). | `Clip A` |
| **$4\text{–}7\text{ s}$** | **T2:** Clicks **One-Tap Create** (`PARALLEL2` obstetric emergency referral, `mgso4_status=UNKNOWN`). | Both judge phones and Big Screen flash the incoming `OPEN` offer with red `MgSO4 UNKNOWN — Verify Before Dosing` banner; ambulance dot begins moving on `REQUESTED -> EN_ROUTE` track. | `Clip A` |
| **$7\text{–}12\text{ s}$** | **T1:** Counts down *"3, 2, 1 — Accept!"* Both judges tap **Accept** simultaneously while 198 automated coroutines fire across an `asyncio.Barrier`. | Exactly **1** winner receives HTTP `200` (`LEASE_GRANTED`, `lease_epoch=1`); the other judge and all 198 coroutines receive `409 LEASE_HELD`. Monitor counter stays **GREEN** (`Violations: 0`, `Deadlocks: 0`). | `Clip B` |
| **$12\text{–}18\text{ s}$** | **T2:** Flips toggle `BROKEN_BUILD=1` (routes to `rhp_scratch_broken` without `one_lease`) and fires a second concurrent Accept. | Screen border flashes **RED (`BROKEN BUILD — SCRATCH DB`)**; both desks win a lease; Person B's independent Python Monitor turns **RED** within $\le 2\text{ s}$ displaying `VIOLATION: I2 (DOUBLE_LEASE)`. | `Clip C` |
| **$18\text{–}21\text{ s}$** | **T2:** Flips toggle back to `BROKEN_BUILD=0` (production contract DB). | Banner clears; fresh referral shows single lease enforced; Monitor returns to **GREEN**. | `Clip C` |
| **$21\text{–}27\text{ s}$** | **T2:** Runs pre-staged superuser `psql` one-liner editing `detail` on `seq=2` in the scratch/demo log. | Judge phones (running pure-JS `@noble/ed25519` + `@noble/sha256` against the pinned checkpoint) immediately print: `BROKEN referral=<id> seq=2 kind=HASH expected=... got=...`. | `Clip D` |
| **$27\text{–}30\text{ s}$** | **T1:** Points to the live Guarantee Arena telemetry bar. | Live-measured `p50 / p95` command latency, `I1–I16` green checkmarks, and `Deadlocks: 0` displayed (zero pre-claimed numbers). | `Clip D` |

### 7.3 Full 5-Minute Pitch & Attack Choreography (When Extending Beyond the 30s Loop)
1. **$0:00\text{–}0:45$ — The Problem & The Feature Phone Rings:**
   - **T1** introduces a composite PHC medical officer persona (explicitly labelled composite) and cites the two verified urban Indian studies: $53\%$ of referrals in the Maharashtra study had no prior phone contact and $37\%$ had complete slips (Das et al., 2023) `[V]`; $90.6\%$ of critically ill obstetric patients arrived unannounced at Safdarjung Hospital Delhi and $47.3\%$ visited $\ge 2$ hospitals first `[V]`.
   - **T2** switches profile to `DEMO_VOICE` or triggers the `NOTICE_VOICE` rung. A physical feature phone held by a judge rings live via Exotel outbound IVR: *"Press 1 to hear an emergency obstetric referral."* Judge presses `1` (`OFFER_ACKED` committed), hears the pre-recorded Kannada/English de-identified prompt, and enters `1` + PIN + `#` to accept.
2. **$0:45\text{–}1:45$ — The 30-Second Live Proof Loop (Section 7.2):**
   - Executes the QR race, `BROKEN_BUILD=1` monitor catch, and `psql` tamper detection live on judges' phones.
3. **$1:45\text{–}2:45$ — Silence Escalation & Parallel Transport:**
   - **T2** creates a `DEMO_FAST` referral and leaves the receiving desk untouched. The audience watches rung $0$ (SSE), rung $A/4$, rung $3A/4$ (dispatcher proxy page), `SOFT_OPEN` handover to Facility 2, and automatic transition to `ESCALATED_TO_DISPATCHER` within $\le 24\text{ s}$ ($T_{\max} = 3 \cdot (3 + 4 + 1) = 24\text{ s} \le 25\text{ s}$), while the ambulance dot moves independently along the transport track (`I3`).
4. **$2:45\text{–}3:45$ — Network Partition, Crash & Degraded World:**
   - **T2** enables Toxiproxy `reset_peer` / `timeout` and kills the `api` container mid-referral while the ambulance PWA queues GPS/vitals offline (`"Pending, not confirmed"`). On restart, `Idempotency-Key` replays produce zero duplicate events (`I4`), offline observations merge via set union, and a paper-code lookup (`9-char Crockford Base32 + mod 37`) links the printable referral slip at the receiving desk.
5. **$3:45\text{–}5:00$ — Loop Closure, Anti-Goodhart View & Honest Limits:**
   - Receiving desk submits mandatory `CLOSED` outcome (`ADMITTED_STABLE`); referring PHC receives instant closure notification.
   - **T1** shows the district command centre (APOT arrival-to-handover separated from acceptance to prevent gaming) and closes with the **Honest Limits & Claims Slide** (creates no beds;surfaces refusals before the ambulance arrives; operational process claims only; ready for an ethics-approved shadow-mode district pilot).

---

## 8. Comprehensive Failure-Mode, Attack & Operations Matrix (§18)

Every identified weakness in ReferralHandshake RHP-1 is tracked below with its exact detection signal, automated response, human fallback, mapped invariant, quantified bounded residual, verification test, and status (`CLOSED`, `BOUNDED`, or `OPEN`).

| ID | Class | Scenario | Detection | Auto-Response | Human Fallback | Inv | Quantified Bounded Residual & Reason | Test ID | Status |
|---|---|---|---|---|---|---|---|---|---|
| **C1** | Concurrency | 200 simultaneous `ACCEPT` requests | Row lock wait | `SELECT ... FOR UPDATE` on `referral` + `one_lease` index; 1 wins (`200`), 199 get `409` | — | `I2` | Relies on PostgreSQL 16 single-primary row-lock and unique-index correctness. | `T-C1` | `CLOSED` |
| **C2** | Concurrency | `ACCEPT` vs `TIMEOUT` race | Lock acquisition order | First lock holder commits; loser sees updated state (`409` or `200 no-op`) | — | `I2` | Either outcome is legal and deterministic under lock order; both are fully audited. | `T-C2` | `CLOSED` |
| **C3** | Concurrency | Late `ACCEPT` after successor `ACK` | Offer status check | Returns `409 LATE_ACCEPT_REJECTED` (since `SOFT_OPEN` closed on successor `ACK`) | Dispatcher may re-assign if clinically needed | `I2` | Offline receiver sees rejection only upon reconnect sync. | `T-C3` | `CLOSED` |
| **C4** | Concurrency | `COUNTER` + competing `ACCEPT` | Referral row lock | First commit wins lease; loser gets `409 LEASE_HELD` and offer becomes `SUPERSEDED` | Referrer sees winning facility | `I2, I12` | Decided atomically under single referral row lock. | `T-C4` | `CLOSED` |
| **C5** | Concurrency | Poller vs command deadlock | `log_lock_waits=on` | Poller Phase 1 is a single committed `SKIP LOCKED` statement; Phase 2 locks `referral` first | — | `I14` | PostgreSQL internal lock manager assumed correct; deadlock delta monitored ($=0$). | `T-F1` | `CLOSED` |
| **C6** | Concurrency | Duplicate timer firing | Deadline status re-read | `WHERE id=$1 AND status='PENDING'` under referral lock + `timeout:<id>` idempotency key $\to$ `200 no-op` | — | `I1, I4` | Status check under referral lock prevents double transition. | `T-C6` | `CLOSED` |
| **C7** | Concurrency | Stale writer (old `version` or `epoch`) | `apply_command` Step 5 | Rollback to `SAVEPOINT sp_cmd`, log to `rejected_command`, return `412` | Client refetches latest state | `I8` | Stale write is deterministically fenced under referral lock. | `T-I8` | `CLOSED` |
| **C8** | Concurrency | Third concurrent offer attempted | DB CHECK constraint | `open_offers BETWEEN 0 AND 2` rejects 3rd offer; earlier `SOFT_OPEN` closed first | Escalates to dispatcher when chain exhausted | `I12` | Enforced by both transition guard and DB CHECK under lock. | `T-F13` | `CLOSED` |
| **T1** | Timer | Poller process crash | `heartbeat` table stale | `claimed_until` expires in $\le 5\text{ s}$; another poller instance re-claims | Operator restarts container | `I1` | Extra escalation delay bounded by $\le 5\text{ s claim expiry} + 1\text{ s poll interval} = 6\text{ s}$. | `T-T1` | `BOUNDED` |
| **T2** | Timer | Host clock forward step $\Delta$ | `heartbeat.ntp_offset_ms` | Deadlines fire up to $\Delta$ early (premature escalation only; `SOFT_OPEN` preserves prior offer) | Operator investigates NTP | `I2, I16` | Extra escalations bounded by step size $\Delta$; fan-out capped at $50\text{ claims/tick}$. | `T-F11` | `BOUNDED` |
| **T3** | Timer | Host clock backward step $\Delta$ | `ntp_offset_ms > 2000` | `GREATEST(clock_timestamp(), referral.head_ts)` preserves monotone event timestamps | Operator investigates NTP | `I16` | Wall-clock deadline firing delayed by at most $\Delta$ ($\le 2\text{ s}$ before monitor alarm). | `T-F11` | `BOUNDED` |
| **T4** | Timer | Deadline backlog storm after outage | Pending deadline count | Poller drains $50\text{ rows/tick}$ ordered by `due_at` | Dispatcher paged on overdue `I1` alarm | `I1` | Additional drain latency bounded by $\lceil n / 50 \rceil \text{ ticks}$ ($1\text{ tick/s}$). | `T-T4` | `BOUNDED` |
| **T5** | Timer | DB primary failover mid-timer | Connection reset | In-flight txn aborts; durable `deadline` rows survive on synchronous standby; poller retries | — | `I1` | Managed Multi-AZ failover window typically $60\text{–}120\text{ s}$ `[V*]`. | `T-T5` | `BOUNDED` |
| **T6** | Timer | Timing profile tampering | Cold-key Ed25519 verify | Startup `validate()` aborts boot on invalid signature or $T_{\max} > B$ | Admin restores signed profile | `I13` | Offline cold-key compromise is outside software scope (same root as `S3`). | `T-F2` | `CLOSED` |
| **N1** | Network | Offline stale `ACCEPT` | Step 7 `expires_at <= ts` | Returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` | PWA opens live reconfirm modal | `I15` | Enforced against server monotone timestamp `ts` under lock. | `T-F12` | `CLOSED` |
| **N2** | Network | Lost HTTP response + client retry | `idempotency` lookup | Returns stored `http_status` and `response` JSON (`200`, `409`, `412`, `422`) | — | `I4` | $48\text{ h}$ key retention window; beyond $48\text{ h}$, `event.event_id UNIQUE` still blocks duplicate events. | `T-F14` | `CLOSED` |
| **N3** | Network | SSE stream disconnect | $15\text{ s}$ heartbeat timeout | Browser reconnects with `Last-Event-ID` and replays missed frames | Manual page refresh | `I4` | Desk UI view may be stale for up to $\le 15\text{ s}$ heartbeat interval. | `T-N3` | `BOUNDED` |
| **N4** | Network | Ambulance enters cellular dead zone | Device `heartbeat` age $> 30\text{ s}$ | Telemetry queues in Room/PWA outbox; UI displays `"Last confirmed Ns ago"` | Crew phones dispatcher directly | `I3` | Live map dot position is stale for the duration of the cellular outage. | `T-N4` | `BOUNDED` |
| **N5** | Network | Duplicate Exotel webhook retry | `inbox(source, external_id)` | `INSERT ... ON CONFLICT DO NOTHING` deduplicates before command execution | — | `I4` | Unique constraint on `(source, external_id)` prevents double execution. | `T-N5` | `CLOSED` |
| **N6** | Network | Webhook DB execution $> 1.5\text{ s}$ | Handler $1.5\text{ s}$ timer | Returns immediate `"please hold"` TwiML/Exotel XML within $2\text{ s}$; next callback reads committed state | Escalates to next ladder rung at $3A/4$ | `I1` | Caller waits at most one additional IVR callback cycle ($\le 5\text{ s}$). | `T-N6` | `BOUNDED` |
| **N7** | Network | Venue internet outage during demo | Tunnel health probe | Switch to local hotspot LAN mode (`REAL_DATA=0`, cap 20, PIN disabled on plain HTTP) | Play pre-recorded MP4 fallback clips | — | Plain LAN HTTP lacks browser WebCrypto (`crypto.subtle`); bundled pure-JS `@noble` libraries used. | `T-N7` | `BOUNDED` |
| **N8** | Network | Flaky-network retry storm | Token-bucket rate limiter | Returns `429`; advisory try-lock returns `409 DUPLICATE_IN_FLIGHT` on concurrent duplicates | — | `I4` | Initial burst up to rate-limiter window ($\le 1\text{ s}$) reaches FastAPI workers. | `T-N8` | `BOUNDED` |
| **I1-A** | Identity | Unauthorized person attempts `ACCEPT` | Roster + session check | Step 2 & Step 5 reject with `401`/`403` and log to `rejected_command` | Admin reviews audit log | `I6` | Physical sharing of a valid unlocked device + known PIN inside a rostered slot cannot be distinguished by software. | `T-I6` | `CLOSED` |
| **I2-A** | Identity | PIN brute-force guessing | `session.pin_failed` counter | Argon2id ($\approx 100\text{ ms}$) + autonomous txn increment + $0\text{ s}/5\text{ s}/30\text{ s}$ backoff + $120\text{ s}$ lock at 3rd failure + dispatcher page | Dispatcher verifies by phone | `I6` | A new `call_sid`/session resets per-session counter, but requires control of a pre-registered roster phone/device. | `T-F7` | `BOUNDED` |
| **I3-A** | Identity | Rival locks out hospital duty role | Per-session lockout scope | Lockout applies only to the offending `(session_id \| call_sid)`; legitimate ward tablet session is unaffected | — | `I6` | Scoped to `session` row rather than `roster` row. | `T-F7` | `CLOSED` |
| **I4-A** | Identity | SIM swap on rostered duty phone | Repeated `PIN_LOCKED` events | Automatic role-slot suspension on repeated lockouts + security alert | Admin revokes roster phone | `I6` | Exposure window lasts until PIN failure threshold or admin revocation. | `T-I4a` | `BOUNDED` |
| **I5-A** | Identity | Voicemail greeting counted as `ACK` | Exotel AMD + press-1 gate | Call requires human DTMF `1` within $8\text{ s}$ before `apply_command(ACK)` is called | Escalates to $3A/4$ proxy rung | `I6` | Any person answering the rostered phone can press `1` to `ACK`, but `ACCEPT`/`COUNTER`/`DECLINE` still requires the secret PIN. | `T-F7` | `CLOSED` |
| **I6-A** | Identity | BOLA / mass-assignment of `hs_state` | Pydantic `extra='forbid'` + facility authz | Rejects unknown fields with `422` and cross-facility access with `403` | — | `I6` | Enforced on all routes covered by the conformance role matrix. | `T-I6b` | `CLOSED` |
| **P1** | Privacy | Free-text PHI injected into `event.detail` | `rhp_detail_ok` DB CHECK + Pydantic | Transaction aborts with `422` / CHECK violation | — | `I11` | A valid uppercase string matching `^[A-Z0-9_]{1,40}$` could still encode a short identifier if API `Literal` validation were bypassed; guarded by CI fuzzing. | `T-F9` | `BOUNDED` |
| **P2** | Privacy | Clinical text leaked over DLT SMS | Static template enforcement | SMS adapter formats only static template + short code ($\le 30\text{ chars}$) | — | — | Clinical payload table is never queried by the SMS worker. | `T-P2` | `CLOSED` |
| **P3** | Privacy | Clinical text leaked via FCM push | Zero-payload wake design | FCM sends empty wake ping; client fetches via authenticated HTTPS with active `payload_grant` | — | `I10` | Push payload contains zero clinical bytes. | `T-P3` | `CLOSED` |
| **P4** | Privacy | SSE stream outlives `payload_grant` | Per-frame grant check | Relay pushes `GRANT_REVOKED` control frame; server strips clinical fields; PWA wipes DOM state | — | `I10` | Data already rendered on screen or photographed prior to revocation cannot be recalled. | `T-F10` | `BOUNDED` |
| **P5** | Privacy | Crypto-shredded DEK remains in old WAL/backups | Monthly `kek_epoch` lifecycle | Deleting `wrapped_dek` shreds live DB immediately; destroying expired monthly `kek_epoch` shreds WAL/backups | Admin rotates KEK epoch | — | Backups remain decryptable by the KEK until the youngest referral in that monthly `kek_epoch` expires. | `T-P5` | `BOUNDED` |
| **A1** | AI Safety | Clinician rubber-stamps hallucinated AI draft | Cognitive Forcing Function | Draft hidden (`423`) until anchors committed; critical fields require manual re-entry; no confidence scores shown | Manual structured entry | — | Human commission error is reduced (target $\le 5\%$ in 20-slip gate), never $0\%$. | `T-A1` | `BOUNDED` |
| **A2** | AI Safety | Client fetches AI draft before anchors | Server state check | API returns `423 ANCHOR_REQUIRED` until `need_class` and `mgso4_status` are saved | — | — | Enforced server-side before draft ciphertext is returned. | `T-A2` | `CLOSED` |
| **A3** | AI Safety | Indic ASR misrecognizes rural Kannada dialect | Seeded-error gate | AI is optional (`T3_EXTRAS=0` default); structured tap-first card requires zero typing/dictation | Turn AI off | — | Indic ASR WER $> 20\%$ on rural dialects `[V]`; AI is never authoritative. | `T-A3` | `BOUNDED` |
| **K1** | Clinical | Pre-referral $\text{MgSO}_4$ dose unknown | Mandatory 3-state enum | Clinician selects `UNKNOWN`; dispatch proceeds immediately; receiving desk shows red verification banner | Receiving clinician verifies before dosing | `I3` | Prevents care delay, but still depends on the receiving clinician reading the red banner. | `T-K1` | `BOUNDED` |
| **K2** | Clinical | Hospital accepts to game KPI, then holds patient in ambulance | APOT metric separation | `ARRIVAL_TO_HANDOVER` tracked separately from `ACCEPT`; `ARRIVAL_REJECTED` revokes lease & logs broken commitment | District officer reviews APOT gap | `I2` | Software surfaces the bottleneck and broken commitment but cannot create physical ICU/OT beds. | `T-K2` | `BOUNDED` |
| **K3** | Clinical | Escalation funnels every case to tertiary MC | Facility load guard | Facility at open-offer cap returns structured `AT_CAPACITY` decline; chain advances without looping | Dispatcher overrides if needed | `I7` | Depends on district administrators configuring realistic catchment chains. | `T-K3` | `BOUNDED` |
| **K4** | Clinical | Ambulance already past highway turn-off on redirect | Cached Matrix detour ETA | Crew/dispatcher receives redirect advisory with detour ETA; ambulance is never auto-rerouted | Crew decides whether to divert or continue (Case `f`) | `I3` | Crew in a cellular dead zone may not receive the advisory until coverage resumes. | `T-F5` | `BOUNDED` |
| **S1** | Insider | DB superuser edits or deletes an `event` row | Hash chain + Merkle proof | Browser verifier & monitor pinpoint exact `seq` (`BROKEN` / `SEQ_GAP` / `TRUNCATED`) within $\le 5\text{ s}$ | Security incident response | `I5` | Hash chains and witnesses *detect* superuser tampering; they do not physically prevent a root user from mutating disk blocks. | `T-F8` | `BOUNDED` |
| **S2** | Insider | Operator serves split-view history to different parties | Multi-witness gossip | Signed checkpoints broadcast every $5\text{ s}$ to Big Screen, judge phones, and off-box witness log | Audit compares witness heads | `I5` | Requires $\ge 2$ independent witnesses to compare signed roots. | `T-S2` | `BOUNDED` |
| **S3** | Insider | Theft of `rhp-sign` online Ed25519 signing key | Separate OS user `0400` permissions | Key rotation runbook + cold-key `RESTORE` authority | Admin rotates witness key (HSM/KMS in pilot) | `I5` | Compromised online signer key could sign forged checkpoints until rotated (`OPEN` for pilot HSM). | `T-S3` | `OPEN` |
| **S4** | Insider | Dispatcher abuses manual override | Mandatory `reason` enum + `proxy=true` | Monitor highlights all `DISPATCHER_ASSIGN` / override events in district audit view | District medical officer review | `I6` | Authorized human dispatcher can still enter a pretextual reason code; mitigated by audit visibility. | `T-S4` | `BOUNDED` |
| **F1-I** | Infra | FastAPI worker container killed mid-request | Docker healthcheck | Uncommitted txn aborts cleanly; client retries with `Idempotency-Key` against restarted worker | — | `I4` | Request latency increases by container restart / retry backoff window ($\le 3\text{ s}$). | `T-F1b` | `BOUNDED` |
| **F2-I** | Infra | PostgreSQL primary instance failure (pilot) | Multi-AZ health probe | Synchronous standby promoted to primary; clients and workers reconnect | Operator verifies promotion | `I1` | $60\text{–}120\text{ s}$ Multi-AZ promotion window `[V*]`. | `T-F2b` | `BOUNDED` |
| **F3-I** | Infra | Outbox relay crashes after sending, before marking `SENT` | `visible_after` $30\text{ s}$ timeout | Row becomes visible again after $30\text{ s}$ and redelivers; consumers deduplicate by `outbox.id` | — | `I4` | Duplicate notification possible within $30\text{ s}$ window; state remains idempotent. | `T-F3b` | `BOUNDED` |
| **F4-I** | Infra | Android OEM battery-saver kills background location | Device `heartbeat` monitor | Dispatcher sees `"Last confirmed Ns ago"` alert; onboarding checklist disables MIUI/OEM battery optimization | Crew taps manual `"Update Location"` | `I3` | Aggressive OEM killers can still suspend background services until app returns to foreground `[GAP]`. | `T-F4b` | `BOUNDED` |
| **L1** | Legal | Regulatory status of automated voice calls to duty phones | Pre-pilot legal review | Prototype uses Exotel sandbox + $\le 10$ whitelisted team numbers + de-identified synthetic prompts | Written legal opinion before field use | — | Unsettled telecom interpretation for automated emergency clinical alerts `[GAP]`. | `T-L1` | `OPEN` |
| **L2** | Legal | DPDP `s.8(7)` erasure vs NMC 3-year record retention | Parameterised TTL | `clinical_payload.expires_at` and `kek_epoch` schedule are configuration parameters | Counsel opinion before field use | — | Legal applicability of 3-year teleconsultation retention to handover records is unverified `[GAP]`. | `T-L2` | `OPEN` |
| **L3** | Legal | Over-claiming BSA 2023 `s.63` certification | Claims linter (`ST-5`) | System exports hash-bearing bundle + Part A/Part B templates; never claims legal certification | Human sign-off on Part A/B | `I5` | Admissibility requires human custodian (Part A) and expert (Part B) signatures at trial `[V*]`. | `T-L3` | `CLOSED` |
| **L4** | Legal | CERT-In $6\text{ h}$ & DPBI $72\text{ h}$ breach reporting clock | Security alert runbook | Automated tamper/lockout alerts page operator with pre-formatted incident summary | Operator files statutory report | — | Reporting timeliness depends on human operator response after alert fires. | `T-L4` | `BOUNDED` |
| **D1** | Demo | iOS Safari lacks native Ed25519 WebCrypto | Browser capability check | Bundled pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256` run in all browsers | Labelled server-side verify view | `I5` | Adds $\approx 15\text{ KB}$ gzipped JS bundle load time on first QR scan. | `T-D1` | `BOUNDED` |
| **D2** | Demo | Exotel trial account limited to $\le 10$ whitelisted numbers `[V]` | Preflight whitelist check | Feature phone demo uses pre-verified team number; judges participate via QR web desks | Play `Clip A` if cell tower congested | — | Arbitrary judge phone numbers cannot receive live outbound PSTN calls on a trial account. | `T-D2` | `BOUNDED` |
| **D3** | Demo | Accidental `BROKEN_BUILD=1` against primary DB | Startup hard-abort guard | Process exits with code `78` if `REAL_DATA=1`, DSN $\neq$ `rhp_scratch_broken`, or role has main DB access | — | `I2` | Enforced deterministically at process start and DB authentication layer. | `T-F20` | `CLOSED` |
| **D4** | Demo | Complete venue Wi-Fi and cellular failure | Preflight connectivity check | Local laptop hotspot LAN mode + pre-recorded MP4 clips (`Clip A–D`) | Disclose clip playback to judges | — | Pre-recorded clips are fallback evidence, explicitly disclosed if used. | `T-D4` | `BOUNDED` |
| **D5** | Demo | Last-minute breaking code edit before pitch | `H22` hard code freeze | Only config/env changes permitted after `H22:00`; rollback tag `step-E7-good` pinned | `git checkout step-E7-good` | — | Process control enforced by team discipline and git tags. | `T-D5` | `BOUNDED` |

---

## 9. Production & Security Operations Runbooks

### 9.1 Cold-Key Signed `RESTORE` Runbook (F8)
If the PostgreSQL primary must be restored from a backup or WAL archive point prior to the latest witness checkpoint, any head regression (`referral.head_seq < checkpoint.head_seq`) will immediately trigger a `TRUNCATED` tamper alarm on all witnesses unless a cold-key signed `RESTORE` record is appended:
1. **Isolate & Restore:** Stop `api`, `poller`, and `relay`. Restore PostgreSQL primary to the target recovery point.
2. **Compute Head Map:** Run `scripts/export_restore_heads.py` to generate the canonical JSON map of `(referral_id, restored_head_seq, restored_head_hash)` and reference the last valid `checkpoint_id` (`restore_from`).
3. **Offline Cold-Key Signature:** On the air-gapped cold-key holder, sign `{restore_from_checkpoint_id, restored_at, head_map_hash}` using the Ed25519 cold private key.
4. **Commit Restore Events:** Run `scripts/apply_restore.py --signature <cold_sig_b64>`:
   - Inserts `checkpoint(kind='RESTORE', restore_from=<id>, cold_signature=<sig>, ...)` as `rhp_witness`.
   - For each affected referral, acquires the referral lock and appends an `event(type='RESTORE', prev_hash=restored_head_hash, detail={'checkpoint_id': <id>})`.
5. **Verify:** Run the browser verifier (`T-F8`); confirm `TRUNCATED` is cleared and the `RESTORE` lineage verifies against `COLD_PUB`.

### 9.2 Crypto-Shredding & Monthly KEK Epoch Destruction Runbook (§10)
1. **Per-Referral Shredding (Automated Daily Job):**
   ```sql
   -- 1. Delete expired clinical ciphertext and secret event payloads
   DELETE FROM event_secret WHERE referral_id IN (
     SELECT referral_id FROM clinical_payload WHERE expires_at <= clock_timestamp()
   );
   DELETE FROM clinical_payload WHERE expires_at <= clock_timestamp();
   -- 2. Nullify wrapped DEK and mark SHREDDED (preserves event.secret_hash so hash chain still verifies)
   UPDATE key_version SET wrapped_dek = NULL, status = 'SHREDDED', shredded_at = clock_timestamp()
    WHERE status = 'ACTIVE' AND referral_id NOT IN (SELECT referral_id FROM clinical_payload);
   ```
2. **Monthly KEK Epoch Destruction (Shreds Historical WAL & Backups):**
   - Once `SELECT count(*) FROM key_version WHERE kek_epoch = $1 AND status = 'ACTIVE'` $= 0$, destroy the master KEK for `$1` in the KMS/keystore. Any ciphertext remaining in older WAL segments or logical backups from that cohort is rendered permanently unrecoverable.

### 9.3 Reconciled 6-Month District Pilot Cloud Budget (F18, AWS `ap-south-1` `[verify]`)
| Component | Specification | Monthly Cost (USD) | 6-Month Cost (USD) |
|---|---|---|---|
| **Managed PostgreSQL 16 Primary + Sync Standby** | Amazon RDS Multi-AZ `db.t4g.medium` | $\$95.00$ | $\$570.00$ |
| **Database Storage** | $2 \times 100\text{ GB}$ `gp3` storage | $\$23.00$ | $\$138.00$ |
| **Application Load Balancer** | AWS ALB + LCU baseline | $\$22.00$ | $\$132.00$ |
| *Base Infrastructure Subtotal* | *(Reconciles Report 3's $\$810$ figure within $\$30$ ALB rounding)* | *$\$140.00$* | *$\$840.00$* |
| **Application & Worker Compute** | $2 \times$ small Linux VMs (`api`, `poller`, `relay`, `monitor`, `witness`) | $\$26.00$ | $\$156.00$ |
| **Backups & S3 Witness Archive** | Automated snapshots + S3 Object Lock witness log | $\$8.00$ | $\$48.00$ |
| **Logs & Telemetry** | 180-day CERT-In compliant log retention in India | $\$10.00$ | $\$60.00$ |
| **Data Transfer** | Outbound HTTPS / SSE / webhook traffic | $\$6.00$ | $\$36.00$ |
| *Core Platform Subtotal* | *(Matches low end of v4's $\$900\text{–}\$1,000$ lean estimate before telephony)* | *$\$190.00$* | *$\$1,140.00$* |
| **Telephony & DLT SMS Allowance** | Outbound IVR minutes + static DLT alerts | $\$25.00$ | $\$150.00$ |
| **10% Operational Contingency** | $10\%$ on $\$215.00/\text{month}$ | $\$21.50$ | $\$129.00$ |
| **LOCKED TOTAL PILOT BUDGET** | **Full Multi-AZ 1-District Shadow Pilot (6 Months)** | **$\$236.50/\text{mo}$** | **$\$1,419.00$ ($\approx \$1,420$)** |

---

## 10. Claims Discipline, Evidence Register & Judge Q&A Playbook

### 10.1 Verified Evidence Register (v7 Appendix A)
| Finding / Figure | Tag | Mandatory Citation Rule on Slides & in Pitch |
|---|---|---|
| **$47\%$ phoned ahead ($11,988$); $53\%$ no phone contact; $37\%$ slips fully documented ($9,279$); $60\%$ tracked ($40\%$ lost to incomplete documentation/demographic errors)** | `[V]` (`[CONFLICT]` on $25,253$ vs $28,020$ denominator) | Cite as: *"Urban Maharashtra study, 2016–2019, 199,888 deliveries (Das et al., 2023)"*. Quote percentages only until denominator table is inspected. |
| **$19\%$ of referrals driven purely by missing resources** (within that group: no emergency OT $47\%$, no NICU $45\%$, no anaesthetist $24\%$, no paediatrician $22\%$) | `[V]` | State clearly that resource percentages are shares *within the $19\%$ resource-driven referral subgroup*. |
| **$90.6\%$ arrived with no prior communication; $70\%$ had no escort; $50\%$ incomplete slips; $47.3\%$ visited $\ge 2$ hospitals first ("ping-pong")** | `[V]` | Cite as: *"Safdarjung Hospital, Delhi — single tertiary obstetric ICU audit of 3,220 inter-facility referrals, 2018–2023"*. Never generalize as national prevalence. |
| **Vula Mobile (South Africa): $52\%$ of one hospital's gynaecology referrals handled by advice alone; evaluation found delays when receivers did not respond (no mandated deadline)** | `[V]` | Cite as direct process evidence for why asynchronous chat needs enforced response deadlines. |
| **National Ambulance Services Guidelines 2026 (29 June 2026)** call for GIS mapping of facilities, bed/critical-care readiness, and command centres linked toward ERSS 112 | `[V]` | State that NAS 2026 defines the policy outcome, while RHP-1 specifies the verifiable handover protocol. |
| **Competitor audit** (ABDM FHIR, eSanjeevani, NIC e-Hospital, CHT, DHIS2, OpenSRP, Pulsara, ReferralMD, Epic Transfer Center) | `[V*]` / `[GAP]` | Always say: *"Automatic inter-facility escalation and a hard single-owner lease guarantee were not found in public documentation of the systems audited."* Never say "first" or "only". |
| **National ambulance time lost to referral failure in India; mortality reduction from digital handshakes** | `[GAP]` | **Make zero claims.** State explicitly that no Indian baseline exists and that claims are strictly operational (handover reliability, documentation, traceability). |

### 10.2 Authorized vs. Forbidden Language (§19 Claims Linter)
| Topic | Authorized Wording (Always Use) | Forbidden Wording (Never Use — `ST-5` Failure) |
|---|---|---|
| **Clinical Impact** | *"Referral communication and documentation gaps are documented in specific urban Indian studies (Das 2023; Safdarjung 2018–23)."* | *"National prevalence"*, *"lives saved"*, *"deaths prevented"*, *"eliminates ping-pong"*. |
| **Uniqueness** | *"Hard single-owner leases and timed inter-facility escalation were not found in public documentation of the systems audited."* | *"World's first"*, *"only system"*, *"no competitor has this"*. |
| **Formal Verification** | *"Control-plane model checked within stated bounds ($3$ facilities, $4$ epochs); implementation checked by conformance vectors, 200-way concurrency tests, and an independent live runtime monitor."* | *"Mathematically proven system"*, *"mathematically impenetrable"*, *"zero bugs"*. |
| **Failure Resilience** | *"Every identified weakness in our 54-item matrix is CLOSED by a tested mechanism, BOUNDED with a quantified residual and monitor alarm, or OPEN with a named owner."* | *"Bullet-proof"*, *"airtight"*, *"zero loopholes"*, *"crash-proof"*, *"immune"*, *"zero silent drops"*. |
| **Audit Log & Law** | *"Tamper-evident hash-chained log with independent witnesses and a BSA s.63-ready export bundle; designed to comply with DPDP emergency provisions using synthetic data."* | *"Immutable log"*, *"BSA certified"*, *"ABDM compliant"*, *"production ready"*. |

### 10.3 Ranked Top-10 Residual-Risk Register (§20)
| Rank | Residual Risk | Status | Owner | Active Mitigation | Closing Evidence Required for Field Use |
|---|---|---|---|---|---|
| **1** | Voice call regulatory classification unsettled (`L1`) | `OPEN` | Legal Advisor | Exotel trial sandbox, $\le 10$ whitelisted team numbers, de-identified synthetic prompts | Written telecom/legal opinion before calling real hospital numbers |
| **2** | DPDP `s.8(7)` erasure vs NMC 3-year retention (`L2`) | `OPEN` | Legal Advisor | Parameterised `expires_at` and monthly `kek_epoch` destruction schedule | Counsel opinion on handover-record retention classification |
| **3** | Online witness signing key theft (`S3`) | `OPEN` | Person A (T1) | Separate OS user `rhp-sign`, mode `0400`, offline cold key for `RESTORE` | Cloud KMS / HSM integration + key-rotation drill log |
| **4** | Receiver adoption incentives in busy wards | `OPEN` | Person B (T2) | Valid `DECLINE`/`COUNTER` vocabulary, no countdown clocks, aggregated district capacity framing | $\ge 3$ structured interviews with CMO, 108 dispatcher, and district officer |
| **5** | Physical bed/ICU capacity is not created | `BOUNDED` | District Admin | Surfaces refusals before ambulance departure; logs structured bottleneck data (`AT_CAPACITY`) | District shadow-mode pilot bottleneck report |
| **6** | Host clock step bounds (`T2` / `T3`) | `BOUNDED` | Person A (T1) | Chrony slew-only config, `GREATEST(clock_timestamp(), head_ts)`, $>2\text{ s}$ NTP offset alarm | NTP fault-injection test report (`T-F11`) |
| **7** | Clinician rubber-stamping of AI drafts (`A1`) | `BOUNDED` | Person B (T2) | Cognitive Forcing Function (`423 ANCHOR_REQUIRED`), manual re-entry, AI off by default | 20-slip seeded-error usability gate ($\le 5\%$ rubber-stamp, $\le 1\%$ omission) |
| **8** | Android OEM battery-savers killing GPS (`F4-I`) | `BOUNDED` | Person B (T2) | Foreground location service, $30\text{ s}$ staleness indicator, manual update button | 2-hour screen-off soak test on target OEM handset |
| **9** | Re-identification risk at low-volume clinics (`P1`) | `BOUNDED` | Person A (T1) | Closed `event.detail` enums, $4\text{-hour}$ timestamp bucketing, $k \ge 5$ cell suppression | Export privacy audit + fuzz test (`T-F9`) |
| **10** | AI-generated concurrency defects during build | `BOUNDED` | Both (T1 & T2) | Frozen spec, `CODEOWNERS`, 3-Gem ring, 6 mutation tests (`M1–M6`), independent monitor | Gate `G0` raw output (`race200` + `M1–M6` green) |

### 10.4 Hard Judge Questions — Exact Prepared Responses
1. **"What if every hospital in the district is full? Your software doesn't create ICU beds or obstetricians."**
   - *"Correct — ReferralHandshake does not create physical capacity, and we state that limit up front. Today, when three hospitals are full, the ambulance discovers that by driving door-to-door with a critically ill mother in the back (`47.3%` in the Safdarjung audit). RHP-1 discovers refusal in seconds via structured `AT_CAPACITY` declines before the ambulance reaches the wrong door, escalates cleanly to the district dispatcher with full context, and gives district officers concrete time-series evidence of whether the bottleneck is missing OT, blood, or anaesthetists."*
2. **"Why didn't you use a blockchain or smart contract for the referral log?"**
   - *"A district emergency referral has a single natural arbiter — the district health authority / 108 command centre — so Byzantine consensus across untrusted miners adds latency and operational complexity with zero clinical benefit. Instead, we use a per-referral RFC 8785 JCS SHA-256 hash chain plus 5-second Ed25519 Merkle checkpoints broadcast to independent witnesses (including judges' phones right now). That gives cryptographic tamper detection and split-view defence in milliseconds on a single PostgreSQL primary."*
3. **"Does your Quint/TLA+ model prove your Python and SQL code has no bugs?"**
   - *"No, and claiming that would be dishonest. Bounded model checking in Quint verifies our control-plane design (`I2` single lease, `I12` offer cap $\le 2$, `I3` transport independence) up to $3$ facilities and $4$ epochs. Our actual Python/PostgreSQL code is verified by (1) replaying conformance vectors, (2) firing a 200-way `asyncio.Barrier` concurrency test against `SELECT ... FOR UPDATE` and the `one_lease` partial unique index, (3) running 6 mutation tests (`M1–M6`) to prove our checks aren't vacuous, and (4) running Person B's independent Python runtime monitor continuously against the live database."*
4. **"What happens if the referring PHC or ambulance has no internet, or the receiving hospital only has a basic feature phone?"**
   - *"Three independent mechanisms handle that: First, the transport track is never gated by the handshake track (`I3`) and `mgso4_status=UNKNOWN` never blocks dispatch, so the ambulance leaves immediately. Second, the receiving hospital does not need an app: at $A/4$ into the ACK window, Exotel places an outbound voice call to the rostered duty number with AMD voicemail filtering, a press-1 human gate, Kannada/Hindi/English prompts, and keypad PIN acceptance; at $3A/4$ the dispatcher can enter a phone-assisted proxy response. Third, the printed referral card carries a 9-character Crockford Base32 + mod-37 checksummed paper code so the receiving desk can link the record even if the network was down during transit."*
5. **"Why would a busy casualty medical officer ever press Decline instead of just ignoring the alert?"**
   - *"In existing apps like Vula Mobile, silence has no timer and no consequence, while declining feels like taking blame. In RHP-1, a structured `DECLINE` for a missing resource (`NO_NICU`, `NO_ANAESTHETIST`) takes 3 seconds, is logged as a valid capacity signal rather than a clinical failure, stops the escalation phone from ringing across the hospital ladder, and prevents an unannounced critical arrival at their casualty door. Silence is the only unrecorded outcome, and silence automatically escalates up the intra-facility ladder and then to the next facility."*