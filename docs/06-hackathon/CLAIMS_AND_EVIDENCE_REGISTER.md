# ReferralHandshake (Protocol RHP-1) — Claims & Evidence Discipline Specification

**Authority:** `ReferralHandshake_LOCKED_Problem_Statement_v7.md` (Highest Precedence) $\rightarrow$ `ReferralHandshake_v8_LOCKED_Solution.md` (§14–§16) $\rightarrow$ `ReferralHandshake_FINAL_LOCKED_Architecture.md` (§19–§21)  
**CI Gate:** Self-Audit Test `ST-5` scans all slides, UI strings, READMEs, and documentation for forbidden claims.

---

## 1. Evidence Status Tag Legend & Precedence Rules

Every empirical statistic, regulatory citation, or technical capability cited in ReferralHandshake documentation, UI copy, or pitch slides must carry its locked status tag and obey its usage rule:

| Tag | Meaning | Mandatory Usage Rule |
|---|---|---|
| **`[V]`** | Verified in primary research or official technical documentation. | May be cited directly with the exact study setting, sample size, and year. Never extrapolate to national prevalence. |
| **`[V*]`** | Verified only from a secondary, blog, law-firm, or vendor source. | Must be framed cautiously (e.g., *"reported in secondary sources"*, *"not found in public documentation of the systems audited"*). Confirm primary text before putting on a slide. |
| **`[CONFLICT]`** | Research files or primary sources disagree on an exact figure or clause. | State the conflict transparently or quote only the invariant part (e.g., quote percentages for Das et al., 2023; use the conservative later date for DPDP commencement). |
| **`[GAP]`** | No reliable primary evidence exists in the literature. | **No claim may be made.** Must be treated as a policy parameter, an explicit limitation, or a pilot hypothesis. |
| **`[verify]`** | Requires pre-event empirical verification from Section 21 checklist. | Execute the time-boxed verification test before the pitch; use the pre-decided fallback if verification fails. |
| **`CLOSED`** | Architectural weakness closed by a concrete mechanism and named automated test. | State the mechanism and test ID (`T-xx`). |
| **`BOUNDED`** | Architectural weakness has an unavoidable technical residual bounded by a stated figure and monitor alarm. | Always state the bound and reason (never write bare *"none"*). |
| **`OPEN`** | Residual legal or operational risk that software alone cannot close. | State the assigned owner and the exact closing evidence required before real-world use. |

---

## 2. Locked Evidence Register (What You May Cite & How)

| Empirical Finding / Citation | Setting & Source | Tag | Exact Usage Rule |
|---|---|---|---|
| Referring facility phoned receiving facility in **$47\%$** of referrals ($11,988$); **$53\%$** had no prior phone contact. | Urban Maharashtra, 2016–2019, $199,888$ deliveries (Das et al., 2023) | `[V]` / Denominator `[CONFLICT]` | Denominator is $25,253$ in some tables and $28,020$ in others (`47%`, `37%`, `60%` reproduce with $25,253$). **Quote percentages and setting only**; confirm paper tables. |
| **$37\%$** of referral slips were fully documented ($9,279$). | Same study (Das et al., 2023) | `[V]` | Cite as urban Maharashtra obstetric data only. |
| **$60\%$** of referred women could be tracked at the higher facility ($40\%$ loss attributed by authors to incomplete documentation and demographic errors). | Same study (Das et al., 2023) | `[V]` | Do not claim ReferralHandshake "eliminates" the $40\%$ loss; frame traceability improvement as a pilot hypothesis. |
| **$19\%$** of referrals driven purely by missing resources; within that resource-driven group: no emergency OT (**$47\%$**), no NICU (**$45\%$**), no anaesthetist (**$24\%$**), no paediatrician (**$22\%$**). | Same study (Das et al., 2023) | `[V]` | State clearly that $47\% / 45\% / 24\% / 22\%$ are shares *within the $19\%$ resource-driven subset*, not shares of all referrals. |
| **$90.6\%$** of critically ill obstetric patients arrived with no prior communication; **$70\%$** had no escort; referral slips incomplete in **$50\%$**. | Safdarjung Hospital, Delhi, $3,220$ inter-facility obstetric ICU referrals, 2018–2023 | `[V]` | Always qualify as *"one tertiary obstetric ICU centre in Delhi"*, never national prevalence. |
| **$47.3\%$** had visited $\ge 2$ hospitals before reaching the tertiary centre ("ping-pong"); authors link this to delay. | Same audit (Safdarjung Hospital, 2018–2023) | `[V]` | Cite as evidence of multi-stop referral chains at one tertiary centre; never claim RHP-1 "eliminates ping-pong". |
| Vula Mobile (South Africa) handled **$52\%$** of one hospital's gynaecology referrals by advice alone, but evaluation found delays when receivers did not respond (no mandated deadline). | Vula Mobile evaluations, South Africa | `[V]` | Cite as direct empirical evidence for why enforced response deadlines (`ACK` and `DECISION` timers) are necessary. |
| National Ambulance Services (NAS) Guidelines 2026 call for GIS mapping of facilities, bed/critical-care readiness, and command centres linked toward ERSS 112. | NAS Guidelines (29 June 2026) via PIB/secondary summaries | `[V]` | Note that NAS 2026 states the desired outcome, not a concrete inter-facility handover protocol. Verify official clause text before quoting verbatim. |
| Automatic inter-facility escalation and a hard single-owner lease guarantee were **not found in public documentation** of the systems audited (ABDM FHIR, eSanjeevani, NIC e-Hospital, CHT, DHIS2, OpenSRP, Pulsara, ReferralMD, Epic Transfer Center). | Competitor & standards audit | `[V*]` | Always say *"not found in public documentation of the systems audited"*; **never** say *"first"*, *"only"*, or *"no competitor has this"*. |
| National prevalence of silent referrals, ambulance-minutes lost to referral failure in India, and mortality effect of digital handshakes. | Literature search across Waves 1–4 | `[GAP]` | **Zero claims permitted.** State plainly that claims are operational (handover reliability, documentation completeness, auditability), never clinical mortality outcomes. |
| Ethiopia "$47\%$ refused referral" statistic. | External study | Excluded | **Do not use** (measures patient refusal of referral, a different phenomenon). |

---

## 3. Authorized vs. Forbidden Claims Register [§19]

| Topic | Authorized Wording (MUST USE) | Forbidden Wording (NEVER USE — Blocked by `ST-5`) |
|---|---|---|
| **Problem Scope** | *"Referral communication and documentation gaps are documented in specific urban Indian obstetric studies (Das et al., 2023; Safdarjung 2018–2023)."* | *"National prevalence"*, *"lives saved"*, *"deaths prevented"*, *"reduces maternal mortality"*. |
| **Uniqueness / Competitors** | *"Hard single-owner lease guarantees and automated two-level escalation were not found in public documentation of the systems audited."* | *"First"*, *"only"*, *"no competitor has this"*, *"unique in the world"*. |
| **Formal Verification & Proof** | *"The control-plane model is bounded-model-checked in Quint ($F=3, \text{MAXE}=4$); the implementation is checked by conformance vectors, 200-way concurrency tests, mutation tests (M1–M6), and a live independent runtime monitor."* | *"Mathematically proven system"*, *"mathematically guaranteed"*, *"mathematically impenetrable"*, *"formally verified code"*. |
| **Reliability & Resilience** | *"Every identified weakness in our 52-row failure matrix is CLOSED with a named test, BOUNDED with a stated technical residual and monitor alarm, or OPEN with an assigned owner."* | *"Bullet-proof"*, *"airtight"*, *"zero loopholes"*, *"zero silent drops"*, *"guaranteed"*, *"immune"*, *"crash-proof"*. |
| **Audit Log & Legal Evidence** | *"Tamper-evident hash-chained log with independent Ed25519 Merkle witnesses and a BSA s.63-ready export bundle (with Part A/B certificate templates)."* | *"Immutable log"*, *"blockchain ledger"*, *"smart contract"*, *"BSA certified"*, *"legally conclusive"*. |
| **Regulatory & Interoperability** | *"Designed to comply with DPDP principles using synthetic data (`REAL_DATA=0`); FHIR R4-shaped export; ABDM-sandbox aligned (only if sandbox calls are made)."* | *"ABDM compliant"*, *"DPDP compliant"*, *"HIPAA compliant"*, *"production ready"*, *"live 108 integration"*. |
| **Operational Impact** | *"Reducing silent referrals and unannounced arrivals is an operational hypothesis to be tested in an ethics-approved district pilot. The system does not create beds or capacity; it surfaces refusal earlier."* | *"Eliminates ping-pong"*, *"eliminates referral delays"*, *"creates capacity"*, *"routes by live beds"*, *"MTTR 3s"* (unless measured live on stage). |

### 3.1 Automated CI Forbidden-Phrase Linter (`scripts/lint_claims.py` — Self-Audit `ST-5`)
Every commit must pass the following check across all `.md`, `.tsx`, `.ts`, `.py`, and `.html` files (excluding Section 3 of `claims-discipline.md` and Section 19 of `ReferralHandshake_FINAL_LOCKED_Architecture.md`):

```python
import pathlib
import re
import sys

FORBIDDEN_PATTERNS = [
    r"\bmathematically\s+proven\s+system\b",
    r"\bmathematically\s+guaranteed\b",
    r"\bmathematically\s+impenetrable\b",
    r"\bbullet[- ]?proof\b",
    r"\bairtight\b",
    r"\bzero\s+loopholes\b",
    r"\bzero\s+silent\s+drops\b",
    r"\bcrash[- ]?proof\b",
    r"\bimmutable\s+log\b",
    r"\babdm\s+compliant\b",
    r"\bbsa\s+certified\b",
    r"\blives\s+saved\b",
    r"\bdeaths\s+prevented\b",
    r"\beliminates\s+ping[- ]?pong\b",
    r"\blive\s+beds\b",
]

EXEMPT_FILES = {"claims-discipline.md", "ReferralHandshake_FINAL_LOCKED_Architecture.md", "ReferralHandshake_v8_LOCKED_Solution.md", "ReferralHandshake_LOCKED_Problem_Statement_v7.md"}

def scan_repo(root: pathlib.Path) -> int:
    failures = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.name in EXEMPT_FILES or ".git" in path.parts:
            continue
        if path.suffix in {".md", ".py", ".ts", ".tsx", ".html", ".json", ".yaml"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pat in FORBIDDEN_PATTERNS:
                for m in re.finditer(pat, text, flags=re.IGNORECASE):
                    print(f"[ST-5 FAIL] {path}: forbidden claim '{m.group(0)}'")
                    failures += 1
    return failures

if __name__ == "__main__":
    sys.exit(1 if scan_repo(pathlib.Path(".")) > 0 else 0)
```

---

## 4. Live Demo Honesty & Anti-Goodhart Operational Rules

1. **Every Number Shown Live Is Measured Live (`D5`, `F16`):** The Guarantee Arena big screen must never display pre-baked latency, recovery time, or throughput constants. `p50`/`p95` command latency, failover recovery time, and invariant counters (`I1`–`I16`) are computed dynamically from the live database and runtime monitor.
2. **Transparent Fallback Disclosure (`D4`):** If a pre-recorded MP4 clip (`clip A`–`clip D`) is used due to venue network or telephony failure, the screen must display a visible badge: `"RECORDED FALLBACK CLIP"` and the presenter must state it aloud.
3. **Visible `BROKEN_BUILD` Banner (`F20`):** When switching to `rhp_scratch_broken` to demonstrate the monitor catching a double lease (`I2`), the UI must render a flashing red banner: `"BROKEN BUILD — SCRATCH DB (SYNTHETIC FAULT INJECTION)"`.
4. **Anti-Goodhart UI Design (`D18`, `K2`):**
   - Receiving hospital desks display a clinical priority queue **without countdown clocks** (countdown timers distort clinical triage under the Manchester Triage System findings `[V]`).
   - Facility capability attestations always display their **age** (`"Attested 4h ago"`) and expire automatically; they are never labelled `"Live Beds"`.
   - Arrival-to-handover time (**APOT**) is reported separately from offer acceptance latency so "accept to hit the KPI, then hold the patient on the stretcher" is immediately visible.
   - District command-centre views aggregate refusal reasons (`NO_NICU`, `NO_OT`, `NO_ANAESTHETIST`, `AT_CAPACITY`) as **systemic capacity signals for resource allocation**, never individual clinician blame boards.

---

## 5. Ranked Residual-Risk Register (§20) & Pre-Event Verification Checklist (§21)

### 5.1 Ranked Top-10 Residual Risks

| Rank | Risk Item | Status | Owner | Enforced Mitigation | Closing Evidence Required |
|---|---|---|---|---|---|
| 1 | Automated voice clinical prompt legality (`L1`) | `OPEN` | Legal Advisor | Exotel trial sandbox + $\le 10$ whitelisted team phones + de-identified synthetic prompts | Written legal opinion on TRAI/health voice rules before real use |
| 2 | DPDP s.8(7) erasure vs 3-year clinical retention (`L2`) | `OPEN` | Legal Advisor | Parameterized `clinical_payload.expires_at` + DEK crypto-shredding | Counsel's legal interpretation for inter-facility handover records |
| 3 | Witness Ed25519 signing key theft (`S3`) | `OPEN` | Person A (T1) | Separate OS user `rhp-sign` (`0400`) + cold-key `RESTORE` + rotation drill | Cloud KMS / HSM integration in district pilot + drill log |
| 4 | Receiver adoption incentives | `OPEN` | Person B (T2) | Validated decline vocabulary (`AT_CAPACITY`, missing resource) + capacity-signal framing + APOT split | $\ge 3$ structured interviews with clinician, 108 EMT/dispatcher, and district officer |
| 5 | Software creates zero physical bed capacity | `BOUNDED` | District Admin | Surfaces refusal before ambulance reaches the door; logs bottleneck evidence | District pilot bottleneck aggregation report |
| 6 | Host NTP clock step bounds (`T2`/`T3`) | `BOUNDED` | Person A (T1) | `GREATEST(clock_timestamp(), head_ts)` (`I16`) + chrony slew-only + $> 2\text{ s}$ offset alarm | Clock-step fault-injection test `T-F11` green |
| 7 | Clinician rubber-stamping AI intake drafts (`A1`) | `BOUNDED` | Person B (T2) | Cognitive Forcing Function (`423 ANCHOR_REQUIRED`), mandatory re-entry, AI off by default | 20-slip seeded-error usability gate ($\le 5\%$ rubber-stamp, $\le 1\%$ silent omission) |
| 8 | Android OEM battery savers killing background GPS (`F4`) | `BOUNDED` | Person B (T2) | Foreground location service + device `heartbeat` + PWA manual update button | 2-hour screen-off GPS soak test on demo phone |
| 9 | Low-volume re-identification risk (`P1`/`F9`) | `BOUNDED` | Person A (T1) | `rhp_detail_ok` closed enums + $4\text{-hour}$ export buckets + $k \ge 5$ cell suppression | Fuzz test `T-F9` + export anonymization audit |
| 10 | AI-generated concurrency defects | `BOUNDED` | Both (A & B) | Spec-first `transitions.yaml`, `race200` barrier test, M1–M6 mutation suite, independent monitor | All T0 acceptance gates green in CI |

### 5.2 Pre-Event Verification Checklist (§21)

| # | Verification Item | Time Box | Exact Test Procedure | Pre-Decided Fallback |
|---|---|---|---|---|
| 1 | Hackathon rules on pre-built work & AI-assisted coding | $1\text{ h}$ | Read official Colossus 3.0 rules and confirm with organisers | Keep pre-event work strictly to spec documents (Phase P); build all code at event (Phase E) |
| 2 | Exotel concurrency, DTMF `%23`, and AMD behavior | $1.5\text{ h}$ | Place 5 concurrent outbound calls to team phones; test voicemail box | Sequential call stagger $\delta$; QR web desks for judges |
| 3 | Exotel webhook $\le 5\text{ s}$ timeout under load | $30\text{ min}$ | Replay 20 concurrent webhook callbacks against local tunnel | `"Please hold"` loop response at $1.5\text{ s}$ budget |
| 4 | LAN HTTP + iOS camera QR scan | $30\text{ min}$ | Scan `http://192.168.x.x` QR on iPhone Safari | Cloudflare tunnel domain or pre-installed local CA |
| 5 | Pure-JS Ed25519 verification on iPhone Safari | $30\text{ min}$ | Verify 40-leaf Merkle checkpoint using `@noble/curves/ed25519` | Labelled server-side verification endpoint |
| 6 | Quint / Apalache bounded check at $F=3, \text{MAXE}=4$ | $1\text{ h}$ | Run `quint verify spec/rhp1.qnt --invariant safety` | Python explicit-state explorer over `transitions.yaml` |
| 7 | Mapbox Matrix API rate limits and key validity | $30\text{ min}$ | Execute 1 Matrix call ($25$ coords on `mapbox/driving`) | Cached synthetic ETAs labelled `"ETA cached"` |
| 8 | Android foreground location service 2-hour soak | $2\text{ h}$ | Screen-off GPS logging on demo Android handset | PWA foreground GPS + manual `"Update Location"` button |
| 9 | DPDP Rules commencement date conflict (13 vs 14 Nov 2025) | $1\text{ h}$ | Inspect official Gazette notification PDF | Cite both dates or use 14 Nov 2025 conservatively |
| 10 | DPDP s.7(f) vs s.7(d) emergency clause numbering | $30\text{ min}$ | Inspect official Act PDF | Cite as *"DPDP Act emergency medical processing provision"* |
| 11 | Das et al. (2023) denominator ($25,253$ vs $28,020$) | $30\text{ min}$ | Inspect published tables in Das et al. (2023) | Quote verified percentages ($47\%, 37\%, 60\%, 19\%$) only |
| 12 | Chrony slew-only configuration & NTP offset alarm | $30\text{ min}$ | Step host clock by $3\text{ s}$ in container test | Demonstrate `heartbeat.ntp_offset_ms` $> 2000\text{ ms}$ alarm and `GREATEST()` monotonicity |