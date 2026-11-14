# ReferralHandshake (Protocol RHP-1) — The 30 Hardest Judge Questions & Honest Answers

> **Evaluation Guide:** Designed for hackathon judges, technical architects, and health system evaluators.  
> Each answer is strictly 2–4 sentences, candid about trade-offs, and tagged `[STRONG]` or `[WEAK POINT - handle carefully]`.

---

### Category 1: Clinical Problem, Scope & Adoption

#### Q1: Why not just use WhatsApp groups like doctors do today?
`[STRONG]` WhatsApp is an unverified broadcast channel with zero concurrency control, zero guaranteed timeouts, and zero legally admissible auditability. When two hospitals reply "we can take her" on WhatsApp, both believe the other is handling it, or an ambulance arrives to find the bed was given to someone else. RHP-1 provides strict single-leaseholder concurrency, automated silence escalation ladders, and tamper-evident audit logs that WhatsApp fundamentally cannot support.

#### Q2: Doesn't Ayushman Bharat Digital Mission (ABDM) already solve health data exchange?
`[STRONG]` ABDM provides clinical record federations (M1/M2/M3) designed for static longitudinal history, not fast-moving 60-second emergency referral negotiations. ABDM does not coordinate bed leases, does not run two-phase timeout pollers, and does not provide worst-case escalation bounds when a facility is silent. RHP-1 acts as the real-time operational state machine that can link to ABDM ABHA IDs once care is accepted.

#### Q3: Who adopts this platform in a real health system, and who pays for it?
`[STRONG]` The primary buyer is the State National Health Mission (NHM) and State Emergency Medical Services (108 GVK-EMRI / Arogya Kavacha). It deploys at the district level under maternal and child health coordination grants, saving costs by reducing ambulance turnaround times and emergency room re-triaging. Facilities adopt it because it gives receiving doctors structured advance notice and prevents chaotic gatekeeper confrontations.

#### Q4: How does this scale beyond a single district to an entire state or country?
`[WEAK POINT - handle carefully]` Our single-primary PostgreSQL design is intentionally scoped to a single district or administrative division (approx. 200–500 facilities) to preserve sub-second strict serializability without distributed consensus overhead. Scaling to a state like Karnataka requires horizontal sharding where each district runs its own primary database, federated by a lightweight inter-district gateway for apex referrals. We chose strong local guarantees over brittle distributed consistency.

#### Q5: What happens when hospital beds or OTs are simply full across the entire district?
`[STRONG]` Software cannot physically construct hospital beds or manufacture blood units; we make zero claims of creating capacity. However, RHP-1 prevents ambulances from blindly driving to three full hospitals in sequence. When all local facilities decline or time out, the system deterministically escalates the case to the 108 Central Dispatcher with complete capability telemetry to arrange inter-district diversion.

---

### Category 2: Engineering Architecture & Database Design

#### Q6: Why PostgreSQL 16 on a single primary? What happens if that primary server fails?
`[WEAK POINT - handle carefully]` We chose a single writable primary with `synchronous_commit=on` because multi-master and distributed databases cannot provide strict per-referral row locking (`SELECT FOR UPDATE`) and instant partial unique index enforcement during high-concurrency races. In a production deployment, this requires an active streaming replica with automated failover via Patroni or AWS RDS Multi-AZ. For this 24-hour hackathon, we prioritized zero race conditions and verified serializability over multi-node clustering.

#### Q7: Why are there 24 tables in the schema? Isn't this massively overbuilt for a hackathon?
`[STRONG]` Every single table directly enforces a specific legal, security, or state invariant in our locked architecture. For example, separating `clinical_payload` and `event_secret` from `referral` and `event` allows instantaneous cryptographic shredding under DPDP Act 2023 without breaking the SHA-256 hash chain. Merging these tables into a "simple" schema would introduce unencrypted data leakage, race conditions, or unindexed state collisions.

#### Q8: How does your 10-step `apply_command()` pipeline prevent database deadlocks?
`[STRONG]` We enforce a strict total lock order across the entire database: `referral -> offer (ORDER BY id) -> deadline (ORDER BY id) -> outbox`. Because transactions always acquire locks in this exact sequence, circular wait dependencies are mathematically impossible. Furthermore, our 2-phase poller claims deadlines in a separate auto-committed transaction before invoking commands under the referral lock.

#### Q9: What is the purpose of the 2-Phase Stateless Deadline Poller? Why not just use `asyncio.sleep`?
`[STRONG]` In-memory timers like `asyncio.sleep` or Redis timers vanish instantly if a server crashes, restarts, or deploys an update, leaving pregnant mothers stranded in un-escalated limbo. Our poller is completely stateless: Phase 1 claims due deadlines in PostgreSQL using `FOR UPDATE SKIP LOCKED` with a 5-second lease, and Phase 2 executes the timeout under the referral lock. If the worker crashes, the row's claim lease expires and another worker claims it seamlessly.

#### Q10: How do you handle duplicate requests if an EMT or doctor taps 'Accept' multiple times on a flaky network?
`[STRONG]` Step 1 of our pipeline executes transaction advisory locks combined with a 48-hour `idempotency` table keyed on `(actor_id, client_key)`. If an identical request hash arrives while in-flight, it returns `409 DUPLICATE_IN_FLIGHT`; if already completed, it replays the exact stored HTTP response without re-executing state mutations. If a client reuses an idempotency key with different data, it is rejected with `422 KEY_REUSED_DIFFERENT_PAYLOAD`.

---

### Category 3: Concurrency, Integrity & The Guarantee Arena

#### Q11: How do you prove that two hospitals cannot both accept the same referral?
`[STRONG]` We enforce this at the database engine level using partial unique index `one_lease ON offer(referral_id) WHERE status = 'ACCEPTED'`. In our `test_race200.py` concurrency suite, 200 concurrent threads hit the accept endpoint across an `asyncio.Barrier`: exactly one thread succeeds with HTTP 200, and the remaining 199 receive deterministic rejections. You can verify this live in our Guarantee Arena right now.

#### Q12: What is the independent runtime monitor, and why is it isolated from the API?
`[STRONG]` To prevent shared-code blindspots (common-mode failure), the monitor was developed by Person B from prose specification without importing a single line of server code or API models. It connects using a read-only PostgreSQL role (`rhp_monitor`), maintains its own internal transition table, and evaluates Invariants I1–I16 on every event append. Our automated AST test (`test_monitor_ast_isolation.py`) enforces that the monitor has zero imports from `api/`.

#### Q13: What does the `BROKEN_BUILD=1` switch do, and why is it safe?
`[STRONG]` It deliberately proves that our verification layer is not fake or cosmetic. Flipping the switch connects exclusively to an isolated scratch database (`rhp_scratch_broken`) that was created without the `one_lease` index. When two judges accept simultaneously, two leases are granted, and within 2 seconds our independent monitor trips an alarm and turns the screen bright red.

#### Q14: How does the pure-JS browser verifier work without trusting your backend?
`[STRONG]` Every event core is serialized using RFC 8785 Canonical JSON and hashed into an append-only SHA-256 chain. An isolated witness process signs binary Merkle tree roots every 5 seconds using an Ed25519 cold key. The browser verifier fetches the signed checkpoint note and verifies the signature and Merkle inclusion proof using pure JavaScript (`@noble/curves/ed25519`) directly inside the judge's browser DOM.

#### Q15: What happens if a database administrator manually tampers with a record in SQL?
`[STRONG]` Because every event's hash commits to `prev_hash || JCS(event_core)`, altering a single character in the event detail or state breaks the cryptographic chain. The witness signer's Merkle root will not match, and the client browser verifier immediately flags the referral with a flashing red `TAMPER DETECTED` banner.

---

### Category 4: Offline Resilience, Reach & Telecom Realities

#### Q16: What happens when an ambulance travels through a complete rural cell dead-zone?
`[STRONG]` The PWA and Android apps feature local IndexedDB / Room outbox queues that buffer GPS telemetry, vitals, and transit status offline with exponential retry. For clinical care, the referring clinician prints the emergency referral slip containing a 9-character Crockford Base32 paper code with a modulo-37 checksum. The receiving hospital can admit the patient and enter treatment details completely offline using this paper code.

#### Q17: Why use a 9-character Crockford Base32 code instead of a standard QR code?
`[STRONG]` Thermal paper referral slips printed at rural clinics frequently get crumpled, torn, smudged with fluid, or scanned under poor lighting where cameras fail. A 9-character Crockford code (e.g., `XKV68JK68`) excludes confusing characters like `I`, `O`, and `L`, and can be read aloud over a scratchy wireless radio or entered manually in 5 seconds. The modulo-37 check character instantly detects 100% of single-character typos and letter swaps.

#### Q18: What is real versus simulated in your telephony and push notification integrations?
`[WEAK POINT - handle carefully]` Our core state machine, 10-step pipeline, PostgreSQL locks, Merkle witness, and browser verifier are 100% real, active, and test-verified. The Exotel Voice IVR, TRAI DLT SMS, Mapbox Directions, and FCM push notifications run on fully functioning mock adapters with realistic latency, Automated Machine Detection (AMD) keypress gates, and TRAI character limits. In a hackathon setting without paid vendor trunks, running realistic simulation adapters prevents fragile external network failures while proving protocol conformance.

#### Q19: Why do you require Automated Machine Detection (AMD) and a "Press 1" gate on voice calls?
`[STRONG]` If an automated voice call reaches a doctor's mobile voicemail or an operator's "subscriber is currently busy" message, an un-gated IVR would interpret the phone pickup as a human acknowledgment. RHP-1 enforces an audio silence detector and requires the clinician to physically press '1' followed by their 4-digit PIN before granting an `ACK` or `ACCEPT`.

---

### Category 5: Clinical Safety, Anti-Gaming & Human Factors

#### Q20: What is the Pre-Referral Magnesium Sulfate ($\text{MgSO}_4$) rule, and why is it answer-required?
`[STRONG]` Magnesium Sulfate is the primary anticonvulsant for eclampsia, but overdosing causes fatal respiratory depression while underdosing causes status epilepticus. In RHP-1, indicating $\text{MgSO}_4$ status is **answer-required, never knowledge-required**: clinicians can choose `GIVEN`, `NONE_GIVEN`, or `UNKNOWN`. Choosing `UNKNOWN` never delays dispatch, but arms a high-priority red alert on the receiving hospital desk so doctors verify before injecting.

#### Q21: How do you prevent hospital doctors from gaming the system to reject difficult patients?
`[STRONG]` First, receiving desks display ordered acuity queues with strictly **zero countdown timers** (Defect D18, anti-Goodhart protection), preventing staff from watching the clock tick down to zero to let a case expire. Second, every decline requires a mandatory structured reason code that is logged to the non-repudiable audit chain. Third, facility acceptance rates and time-to-decision metrics are exposed to the district command center for administrative review.

#### Q22: Why doesn't the system automatically mark an ambulance as "Arrived" when it enters the hospital geofence?
`[STRONG]` An ambulance entering a 200-meter hospital radius does not mean the patient has received emergency care; the vehicle might be stuck in gate traffic, or the crew might be searching for a stretcher. Under Closure F5, a geofence crossing only emits an `ARRIVAL_SUGGESTED` advisory. Physical arrival and handover require explicit human confirmation by the EMT crew or receiving triage nurse.

#### Q23: What are the 9 mandatory clinical closure outcomes, and why can't the system invent one?
`[STRONG]` Every referral must conclude with an accountable human outcome: `ADMITTED_STABLE`, `ADMITTED_CRITICAL`, `DELIVERED_AT_RECEIVER`, `DELIVERED_EN_ROUTE`, `PATIENT_REFUSED`, `TRANSPORT_CANCELLED`, `DETERIORATED_OR_DIED_PRE_HANDOVER`, `REDIRECTED_ON_ARRIVAL`, or `UNKNOWN_COUNTER_REFERRAL`. If hospital staff fail to close the record after repeated deadline reminders, the system auto-closes with `UNKNOWN_COUNTER_REFERRAL` marked with `proxy=true` and `actor=system`—it never fabricates a clinical success.

---

### Category 6: Privacy, Compliance & AI Safety

#### Q24: How does RHP-1 protect sensitive maternal health data under the Digital Personal Data Protection (DPDP) Act 2023?
`[STRONG]` We implement AES-256-GCM envelope encryption where each referral has a dedicated Data Encryption Key (DEK) wrapped by rotating monthly Key Encryption Keys (KEKs). In our Command Centre, 1-click DPDP Crypto-Shredding permanently zeroes out the referral's DEK (`wrapped_dek = NULL`) and destroys clinical ciphertexts, rendering patient data unrecoverable while leaving the outer event hash chain intact for administrative statistics.

#### Q25: How was the AI intake assistant limited and made safe? Why won't it hallucinate clinical advice?
`[STRONG]` The AI intake assistant is placed completely off the critical transaction path behind a **Cognitive Forcing Function** (Closure A1/A2). The assistant returns `HTTP 423 ANCHOR_REQUIRED` and refuses to reveal diagnostic drafts until the human clinician manually commits their primary findings (`need_class` and `mgso4_status`). The AI never suggests destinations, never makes routing decisions, and never dispenses medication dosages.

#### Q26: Are your exported event bundles legally admissible in an Indian court of law?
`[STRONG]` Under Section 63 of the Bharatiya Sakshya Adhiniyam (BSA) 2023, electronic records are admissible when accompanied by a certificate verifying device custody and cryptographic hash integrity. Our Command Centre generates an automated Section 63 Certificate Bundle that binds the full SHA-256 hash chain and Ed25519 witness checkpoints to the referral timeline.

---

### Category 7: Project Retrospective & Future Work

#### Q27: What did you NOT build during this 24-hour hackathon?
`[STRONG]` We did not build autonomous AI routing algorithms (which we consider clinically dangerous and irresponsible), we did not build a consumer patient-facing smartphone app (since mothers in active labor need emergency medical care, not an app), and we did not connect live commercial Exotel telecom trunks or live Mapbox billing accounts (relying instead on verified simulation adapters).

#### Q28: If you had another 48 hours, what would you build next?
`[STRONG]` We would implement:
1. Native integration with Karnataka's 108 GVK-EMRI Computer-Aided Dispatch (CAD) software.
2. ABDM ABHA onboarding APIs (M1/M2/M3) to bind verified national health IDs to the envelope-encrypted payload.
3. Multi-node streaming replication with automated Patroni failover for multi-district resilience.

#### Q29: How did you test this system under extreme conditions?
`[STRONG]` We executed an automated test suite of 255 verified tests including:
1. `test_race200.py`: 200 concurrent threads racing to accept one referral across an `asyncio.Barrier`.
2. `test_toxiproxy_chaos.py`: Injecting 15-second network latencies and connection resets using Shopify Toxiproxy.
3. `test_mutations.py`: M1–M6 mutation tests asserting that corrupted payload signatures are rejected.
4. `test_monitor_ast_isolation.py`: AST parsing confirming zero server imports in our independent monitor.

#### Q30: Why should ReferralHandshake win Colossus 3.0?
`[STRONG]` Most hackathon health projects build superficial chatbot interfaces or dashboard mockups over unverified assumptions. ReferralHandshake built an end-to-end, mathematically bounded, cryptographic protocol backed by 24 PostgreSQL tables, an independent runtime monitor, 255 passing tests, and 8 responsive clinical views. We addressed the single most fatal operational gap in Indian public maternal healthcare—the Referral Carousel—with uncompromising engineering discipline.
