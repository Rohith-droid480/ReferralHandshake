---
trigger: always_on
scope: "**/*"
authority: ReferralHandshake_LOCKED_Problem_Statement_v7.md
secondary_authority: "ReferralHandshake_FINAL_LOCKED_Architecture.md (§18, §19, §20, §23)"
linter_test: "T-F15 / ST-5"
---

# `.agents/rules/claims-discipline.md` — Evidence Tags, Claims Register & Anti-Goodhart Rules

This rule file governs all text in READMEs, documentation, UI labels, slide decks, pitch scripts, API responses, and code comments for **ReferralHandshake (Protocol RHP-1)**. Violating claims discipline is a `S1` blocker flagged by Gem 2 (Auditor) and Gem 3 (Adversary).

---

## 1. Core Epistemic Principle

1. **Operational Process Claims Only:** ReferralHandshake makes verifiable claims about **handover protocol mechanics** (offer, acknowledgement, single-owner lease under test conditions, bounded timer escalation, tamper-evident hash-chained logs). It **NEVER** claims clinical outcomes, lives saved, deaths prevented, or measured ambulance time saved in India (`[GAP]`).
2. **Live Measurement Mandate:** Every performance figure shown in the UI or on stage (p50/p95 event latency, recovery time after container kill, escalation duration, invariant violation count) **MUST** be measured live from the running system during the demo—never hardcoded or pre-claimed.
3. **Synthetic Data Mandate (`REAL_DATA=0`):** All demo, test, and simulation views must clearly state that they run on synthetic data only.

---

## 2. Mandatory Status Tags & Residual Discipline (`F15`)

### 2.1 Evidence Tags (Preserve in Documentation & Slide Notes)
- **`[V]`** — Verified from primary research or official technical documentation.
- **`[V*]`** — Verified only from a secondary, blog, law-firm, or vendor source; must be confirmed from primary text before appearing unqualified on a slide.
- **`[CONFLICT]`** — Research files or primary sources disagree; both sides or the conservative bound must be stated.
- **`[GAP]`** — No reliable primary evidence exists; parameterized as a policy/clinical configuration or stated as an open hypothesis for a pilot.
- **`[verify]`** — Pre-event verification checklist item (§21 of Architecture).

### 2.2 Weakness & Failure-Matrix Status Tags (`F15`)
Every row in any failure-mode matrix, threat model, or risk ledger **MUST** carry one of three tags:
- **`CLOSED`** — Backed by a concrete mechanism in the spec **and** a named automated test (`T-xx`).
- **`BOUNDED`** — Carries an explicit technical residual bound, the reason that residual exists, and a monitor/heartbeat alarm.
- **`OPEN`** — Carries a named owner and the specific closing evidence required before real-world use.
- **No Bare `"none"` Rule (`F15`):** Writing a bare `"none"` or `"N/A"` in a residual-risk column is strictly forbidden and fails CI test `T-F15`. Even `CLOSED` rows must state their underlying assumption (e.g., `"relies on PG lock/unique correctness"`).

---

## 3. Authorized vs. Forbidden Claims Register (§19, v7 §12, v8 §15)

| Topic | Authorized Wording (USE THIS) | Forbidden Claim (NEVER USE — CI `ST-5` FAIL) |
|---|---|---|
| **Epidemiology & Problem Scale** | "Referral communication and documentation gaps are documented in specific urban Indian obstetric studies (Das et al., 2023 in urban Maharashtra; Safdarjung Hospital audit, 2018–2023 in Delhi)." | "National prevalence", "Across India 90% of referrals fail", "Lives saved", "Deaths prevented", "Reduces maternal mortality" |
| **Competitor Landscape** | "Automatic inter-facility escalation and a hard single-owner lease guarantee were not found in public documentation of the systems audited (`[V*]`)." | "First in the world", "Only system that does this", "No competitor has this" |
| **Formal Methods & Proof** | "Control-plane model checked within stated bounds ($F=3$ facilities, $E=4$ epochs) in Quint; implementation checked by conformance vectors, 200-way barrier tests, and an independent live runtime monitor." | "Mathematically proven system", "Mathematically guaranteed", "Mathematically impenetrable", "100% bug-free", "Proves the code correct for all sizes" |
| **System Reliability & Security** | "Every identified weakness in our ledger is `CLOSED` with a named test, `BOUNDED` with a stated residual and alarm, or `OPEN` with an owner." | "Bullet-proof", "Airtight", "Zero loopholes", "Guaranteed", "Immune", "Crash-proof", "Zero silent drops", "MTTR 3 s" (unless measured live on stage) |
| **Audit Log & Legal Evidence** | "Tamper-evident hash-chained log with signed Merkle checkpoints held by independent witnesses; generates a BSA s.63-ready export bundle with Part A/B certificate templates." | "Immutable log", "Blockchain ledger", "Tamper-proof", "Legally conclusive", "BSA certified", "Prevents sysadmin tampering" (it *detects*, not prevents) |
| **Interoperability & ABDM** | "Designed to comply; NRCeS/FHIR R4-shaped export (`ServiceRequest`, `Task`, `Encounter`, `Communication`) using a curated code subset; claim 'ABDM-sandbox aligned' only if sandbox calls are made." | "ABDM compliant", "Live integration with 108 / ERSS / eSanjeevani / hospitals", "Production ready" |
| **Operational Impact** | "Surfaces refusal before the ambulance reaches the door; process improvement is a hypothesis to be tested in an ethics-approved district pilot." | "Eliminates ping-pong", "Measured ambulance time saved", "Creates hospital bed capacity", "Live bed availability" |

---

## 4. Primary Evidence Register & Exact Citation Rules (v7 §1, Appendix A)

When citing research numbers in UI, docs, or pitch materials, enforce these exact qualifiers:

1. **Urban Maharashtra Study (Das et al., 2023 — $199,888$ deliveries, 2016–2019) `[V]`:**
   - Referring facility phoned the receiving facility in **$47\%$** of referrals ($11,988$); **$53\%$** had no phone contact.
   - **$37\%$** of referral slips were fully documented ($9,279$).
   - **$60\%$** of referred women could be tracked at the higher facility ($40\%$ loss attributed by authors to incomplete documentation and demographic errors).
   - **$19\%$** of referrals were driven purely by missing resources; **within that resource-driven group**, shares were: no emergency OT ($47\%$), no NICU ($45\%$), no anaesthetist ($24\%$), no paediatrician ($22\%$).
   - **Denominator Rule (`[CONFLICT]`):** Reports disagree between $25,253$ and $28,020$ total referrals (the $47\%, 37\%, 60\%$ figures reproduce with $25,253$). **Quote percentages only** until confirmed from the paper's primary tables.
2. **Safdarjung Hospital, Delhi Audit ($3,220$ inter-facility obstetric referrals, 2018–2023) `[V]`:**
   - Must always be qualified as **"one tertiary obstetric ICU centre in Delhi"**.
   - **$90.6\%$** of critically ill obstetric patients arrived with no prior communication; **$70\%$** had no escort; slips were incomplete in **$50\%$**; **$47.3\%$** had visited two or more hospitals first ("ping-pong").
3. **Vula Mobile, South Africa `[V]`:**
   - $52\%$ of one hospital's gynaecology referrals were handled by advice alone, **but** its evaluation documented delays when receivers did not respond because there was no mandated response deadline. Cite as direct evidence for enforced deadlines and process outcomes only.
4. **OpenStreetMap India Healthcare Tags `[V]` (Fixes `D14`):**
   - $98\%$ of mapped healthcare features have a *name*, whereas `capacity:beds` is present on **$0.08\%$** and `emergency` on **$1.03\%$**. Never misquote this as "$>98\%$ of clinical capability tags missing."
5. **DPDP Act 2023 & DPDP Rules 2025 (`[V]` / `[CONFLICT]` / `[GAP]`):**
   - Notification date is cited as 13 Nov 2025 in some summaries and Gazette 14 Nov 2025 in others (`[CONFLICT]`; use 14 Nov 2025 conservatively; core obligations 13/14 May 2027).
   - Cite "emergency processing provision" (s.7(f) vs s.7(d) `[CONFLICT]`), s.7(i) for staff telemetry (requires prior written notice, minimization, HR siloing, erasure), s.8(5) safeguard penalty ceiling (up to ₹250 Cr), s.8(6) breach reporting ceiling (up to ₹200 Cr; 72 h report to DPBI), and s.8(7) erasure vs NMC 3-year retention (`[GAP]`, parameterized).
6. **Reconciled 6-Month Pilot Cloud Cost (`F18`, `[verify]`):**
   - AWS `ap-south-1` Multi-AZ estimate: Base DB+storage+ALB = $\$140/\text{mo}$ ($\$840/6\text{ mo}$); with app VMs, S3 backups, logs, transfer = $\$190/\text{mo}$ ($\$1,140/6\text{ mo}$); with $\$25/\text{mo}$ telephony and $10\%$ contingency = **$\$236.50/\text{mo}$ ($\$1,419 \approx \$1,420$ for 6 months)**. Always state the range $\$1,140\text{–}\$1,500$ and how the earlier figures reconcile.

---

## 5. Anti-Goodhart UI & Analytics Rules (§15, v8 §11)

1. **No Countdown Clocks on Receiving Desks:** Receiving clinicians see a prioritized queue and resource checklists, **NEVER** ticking countdown timers (which distort clinical triage under Goodhart's Law `[V]`).
2. **Separate Acceptance from Handover (APOT Separation):** Dashboards **MUST** report `ARRIVED -> HANDED_OVER` latency separately from `OFFER_CREATED -> OFFER_ACCEPTED` latency so "accept to hit the KPI, then hold the patient in the ambulance" is immediately visible.
3. **Capacity Signals, Not Individual Blame:** District command-centre views aggregate refusal reasons (`AT_CAPACITY`, missing `NICU`/`OT`/`ANAESTHETIST`) at the facility/district level to highlight infrastructure bottlenecks, never naming or ranking individual clinicians.
4. **Descriptive Network & Simulation Labels:** Network betweenness centrality (`networkx`) must be labelled `"Descriptive (derived from log), not causal"`. Any digital-twin or counterfactual view must display its assumptions and a badge reading `"SIMULATED — SYNTHETIC DATA"`.

---

## 6. Automated Claims & Residual Linter (`scripts/lint_claims.py`, `ST-5` / `T-F15`)

Run this script in CI before every gate. It must exit `0`:
```python
#!/usr/bin/env python3
import pathlib, re, sys

FORBIDDEN_PHRASES = [
    r"mathematically proven system",
    r"mathematically guaranteed",
    r"mathematically impenetrable",
    r"bullet-?proof",
    r"airtight",
    r"zero loopholes",
    r"crash-?proof",
    r"immutable log",
    r"abdm compliant",
    r"bsa[ -]certified",
    r"lives saved",
    r"deaths prevented",
    r"eliminates ping-?pong",
    r"zero silent drops",
]
EXEMPT_FILES = {
    "spec/ReferralHandshake_FINAL_LOCKED_Architecture.md",
    "spec/ReferralHandshake_v8_LOCKED_Solution.md",
    "spec/ReferralHandshake_LOCKED_Problem_Statement_v7.md",
    ".agents/rules/claims-discipline.md",
}

failures = []
for path in pathlib.Path(".").rglob("*"):
    if not path.is_file() or ".git" in path.parts or path.suffix not in {".md", ".py", ".ts", ".tsx", ".html"}:
        continue
    rel = path.as_posix()
    if rel in EXEMPT_FILES or rel.endswith("lint_claims.py"):
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for pat in FORBIDDEN_PHRASES:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            failures.append(f"{rel}: forbidden phrase '{m.group(0)}'")

if failures:
    print("\n".join(failures), file=sys.stderr)
    sys.exit(1)
print("ST-5 / T-F15 claims discipline lint: PASS (0 violations)")
```