# ReferralHandshake (Protocol RHP-1) — Domain Invariants & Verification Specification

**System:** Referral Handshake Protocol (RHP-1) & Reference Platform  
**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0  
**Document ID:** `DOMAIN_INVARIANTS.md` | **Status:** LOCKED (`REAL_DATA=0`)  
**Authority Precedence:** `Problem_Statement_v7.md` $>$ `[V]` Research Findings $>$ `v8_LOCKED_Solution.md` $>$ `FINAL_LOCKED_Architecture.md`

---

## 1. Provability Philosophy & Four-Layer Enforcement Architecture

ReferralHandshake replaces unverified promises with **provable operational guarantees** within stated bounds (`3` facilities, `4` epochs in bounded model checking; continuous differential runtime monitoring in production and live attack demos).

Every domain invariant (`I1`–`I16`) is enforced across four independent layers:
1. **Layer 1 — Command Pipeline Guards (`apply_command()`):** Deterministic preconditions, optimistic version checks (`412`), lease epoch fencing (`409`), confirmation TTL checks, and Pydantic `extra='forbid'` schemas.
2. **Layer 2 — PostgreSQL 16 Kernel Enforcement:** Partial unique indexes (`one_lease`), deferrable constraint triggers (`i1_pending_deadline`), append-only and hash-continuity triggers (`rhp_event_guard`), lock-order session GUC triggers (`rhp_require_lock`), and JSONB allowlist checks (`rhp_detail_ok`).
3. **Layer 3 — Bounded Model Checking (`spec/rhp1.qnt`):** Formal Quint specification authored by Person A, verified via simulator and Apalache symbolic model checker with explicit non-vacuity assertions.
4. **Layer 4 — Clean-Room Independent Runtime Monitor (`monitor/monitor.py`) & Browser Verifier:** Person B writes the runtime monitor solely from §3 prose in `FINAL_LOCKED_Architecture.md`, importing **zero** server modules and connecting via read-only role `rhp_monitor` (`REPEATABLE READ READ ONLY`). It re-derives every referral's state from the `event` log and cross-checks it against the `referral` row.

---

## 2. Master Invariant Matrix (`I1`–`I16`)

| ID | Invariant Name | Type | Formal Predicate | Primary DB / API Enforcement | Independent Monitor Rule (`Person B`) | Mutation / CI Test |
|---|---|---|---|---|---|---|
| **I1** | **No Silent Referral** | Liveness (`L`) | $\forall r \in \text{Referral}: r.\text{hs\_state} \notin \{\text{CLOSED}, \text{CANCELLED}\} \implies (\exists d \in \text{Deadline}: d.\text{referral\_id}=r.\text{id} \land d.\text{status}=\text{'PENDING'}) \land (\text{now}() - d.\text{due\_at} \le \tau)$ | `DEFERRABLE INITIALLY DEFERRED` constraint trigger `i1_pending_deadline` on `referral` at `COMMIT`; two-phase stateless poller | Query `deadline WHERE status='PENDING' AND due_at < clock_timestamp() - TAU_MS`; flag `("I1", referral_id)` | `T-I1`, `T-T1` |
| **I2** | **One Patient, One Owner** | Safety (`S`) | $\forall r \in \text{Referral}: \|\{o \in \text{Offer}(r) : o.\text{status}=\text{'ACCEPTED'}\}\| \le 1 \land \text{lease\_epoch strictly increases on each grant/revoke}$ | Partial unique index `one_lease ON offer(referral_id) WHERE status='ACCEPTED'`; `SELECT ... FOR UPDATE` on `referral` | In event fold: if `LEASE_GRANTED` when `st["lease"] != None` or `e.epoch <= st["epoch"]` $\rightarrow$ flag `("I2", seq)`; diff check `st["epoch"] == r.lease_epoch` | `T-I2`, `T-C1 race200`, `M2` |
| **I3** | **Never Block Care** | Safety (`S`) | $\forall r \in \text{Referral}: r.\text{hs\_state} \notin \{\text{CLOSED}, \text{CANCELLED}\} \implies \text{TR\_UPDATE is never rejected due to } r.\text{hs\_state} \text{ or } \text{mgso4\_status}$ | `TR_UPDATE` handler never reads `hs_state` (except terminal check); `mgso4_status` defaults to `'UNKNOWN'` with `CHECK IN ('GIVEN','NONE_GIVEN','UNKNOWN')` | Scan `rejected_command WHERE command='TR_UPDATE'` for any `reason_code` not in `{'REFERRAL_TERMINAL','INVALID_TR_TRANSITION','HUMAN_CONFIRMATION_REQUIRED'}` | `T-I3`, `T-K1`, `transportNeverGated` |
| **I4** | **Exactly-Once Event & Gap-Free Sequence** | Safety (`S`) | $\forall r \in \text{Referral}: \text{seq}(r) = \langle 1, 2, \dots, r.\text{head\_seq}\rangle \land \forall e_1 \ne e_2: e_1.\text{event\_id} \ne e_2.\text{event\_id}$ | `idempotency` PK `(actor_id, key)` + `pg_try_advisory_xact_lock`; `event.event_id UNIQUE`; `event` PK `(referral_id, seq)`; trigger `rhp_event_guard` (`NEW.seq == r.head_seq + 1`) | In event fold: if `e.seq != st["seq"] + 1` $\rightarrow$ flag `("I4", e.seq)`; diff check `st["seq"] == r.head_seq` | `T-I4`, `T-F14` |
| **I5** | **Cryptographic Hash Chain & Closure Integrity** | Safety (`S`) | $\forall e_k \in \text{Event}(r): e_k.\text{prev\_hash} = e_{k-1}.\text{hash} \land e_k.\text{hash} = \text{SHA256}(e_k.\text{prev\_hash} \parallel \text{JCS}(\text{core}(e_k))) \land (r.\text{hs\_state} \in \{\text{CLOSED},\text{CANCELLED}\} \iff r.\text{outcome} \ne \text{NULL})$ | Triggers `event_ao`, `checkpoint_ao` (reject `UPDATE`/`DELETE`); trigger `rhp_event_guard`; `referral` `CHECK ((hs_state IN ('CLOSED','CANCELLED')) = (outcome IS NOT NULL AND closed_at IS NOT NULL))` | Recompute `SHA256(prev_hash + jcs(core))` on every event row; verify `prev_hash == st["head"]`; verify Ed25519 checkpoint signatures | `T-I5`, `T-F8`, `M5` |
| **I6** | **Roster, Device & PIN Authority** | Safety (`S`) | Every mutating response (`ACCEPT`, `COUNTER`, `DECLINE`) is authored by a valid `roster` slot (`valid_from <= ts < valid_to`) on a registered `device` or `call_sid` with verified Argon2id PIN, or carries `proxy=true` by a rostered `DISPATCHER` | `apply_command()` Steps 2, 3, and 5; autonomous PIN failure counter in `session`; `CHECK (device_id IS NOT NULL OR call_sid IS NOT NULL)` | Join `event.actor_roster_id` against `roster`; flag `("I6", e.seq)` if actor lacks active roster validity at `e.server_ts` or facility mismatch without `proxy=true` | `T-I6`, `T-F7` |
| **I7** | **No Invented Destination** | Safety (`S`) | $\forall o \in \text{Offer}(r): o.\text{source}=\text{'CHAIN'} \implies o.\text{facility\_id} \in r.\text{chain}$ | Trigger `offer_chain_guard` (`BEFORE INSERT ON offer`) raises `I7_NOT_IN_CHAIN` if `NEW.source='CHAIN'` and `NEW.facility_id != ALL(r.chain)` | Check every `offer` row: if `source == 'CHAIN'` and `facility_id not in referral.chain` $\rightarrow$ flag `("I7", offer.id)` | `T-I7`, `T-K3` |
| **I8** | **Stale Writers Fenced** | Safety (`S`) | Any command carrying `expected_version != r.version` or `expected_epoch != r.lease_epoch` is rejected (`412`) and never mutates contract state | `apply_command()` Step 5 fencing guard + `ROLLBACK TO SAVEPOINT sp_cmd` + log row in `rejected_command` | In event fold: if any applied event has `e.epoch < st["epoch"]` $\rightarrow$ flag `("I8", e.seq)` | `T-I8`, `M1` |
| **I9** | **No Referral Loops** | Safety (`S`) | $\forall r \in \text{Referral}, \forall o_1 \ne o_2 \in \text{Offer}(r): o_1.\text{facility\_id} \ne o_2.\text{facility\_id}$ | Table constraint `UNIQUE (referral_id, facility_id)` on `offer`; `advance()` filters `offered_facilities` | In event fold: track seen `OFFER_CREATED` facilities per referral; if duplicate facility $\rightarrow$ flag `("I9", e.seq)` | `T-I9` |
| **I10** | **Revocable Clinical Payload Grants** | Safety (`S`) | Clinical payload frames are emitted only to subscribers holding an active `payload_grant` (`revoked_at IS NULL`) at emit time | Partial unique index `one_active_grant`; per-frame SSE authz check + 15s heartbeat re-check + `GRANT_REVOKED` control frame | Compare SSE emit audit timestamps against `payload_grant.revoked_at`; flag `("I10", grant.id)` if frame emitted after revocation | `T-I10`, `T-F10` |
| **I11** | **PHI-Free Event Metadata** | Safety (`S`) | $\forall e \in \text{Event}: \text{keys}(e.\text{detail}) \subseteq \text{rhp\_allowed}(e.\text{type}) \land \forall v \in \text{values}(e.\text{detail}): v \in \text{Bool} \cup \text{Int}_{12} \cup \text{UUID} \cup \text{EnumToken}_{40}$ | Pydantic `Literal` schemas (`extra='forbid'`) + PostgreSQL `CHECK (rhp_detail_ok(type, detail))` on `event` | Scan `event.detail` keys and value regexes on every fold cycle; flag `("I11", e.seq)` on any violation | `T-I11`, `T-F9` |
| **I12** | **Bounded Open Offers ($\le 2$)** | Safety (`S`) | $\forall r \in \text{Referral}: 0 \le \|\{o \in \text{Offer}(r) : o.\text{status} \in \{\text{OPEN},\text{ACKED},\text{COUNTERED},\text{SOFT\_OPEN}\}\}\| \le 2$ | Column constraint `open_offers CHECK (open_offers BETWEEN 0 AND 2)` on `referral`; maintained under referral lock in `advance()` | Count `offer` rows in `OPEN_SET` per referral and check `r.open_offers <= 2`; flag `("I12", r.id)` if count $> 2$ or mismatch | `T-I12`, `T-F13`, `M4` |
| **I13** | **Bounded Escalation Time ($T_{max} \le B$)** | Safety (`S`) | For active profile $p$: $T_{max}(p) = p.F \cdot (p.A + p.D + p.\epsilon) \le p.B \land \neg(p.\text{demo} \land \text{REAL\_DATA}=1)$ | Startup validator `validate(p, REAL_DATA)` verifies Ed25519 cold-key signature and math bounds before FastAPI binds socket | Recompute $F \cdot (A + D + \epsilon) \le B$ and voice stagger bound on boot and on every `/healthz` poll | `T-I13`, `T-F2`, `T-F3` |
| **I14** | **Strict Referral Lock Discipline** | Safety (`S`) | No transaction may `INSERT` or `UPDATE` contract state (`referral`, `offer`, `deadline` status/due, `event`, `payload_grant`, `outbox` insert) unless `current_setting('rhp.locked_referral', true) == referral_id::text` | Trigger `rhp_require_lock()` (`BEFORE INSERT OR UPDATE` on all 6 contract tables); raises `I14_LOCK_NOT_HELD` | Monitor `pg_stat_database.deadlocks` delta ($= 0$) and `log_lock_waits` | `T-I14`, `T-F1`, `M3` |
| **I15** | **Unexpired Resource Confirmations** | Safety (`S`) | An `ACCEPT` or `CONFIRM_COUNTER(true)` succeeds only if $\forall c \in \text{Req}(r.\text{need\_class}): \exists \text{conf}(o, c) \text{ with } \text{conf}.\text{expires\_at} > \text{server\_ts}$ | `apply_command()` Step 7 `check_confirmations()` under referral lock; returns `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` | Join `OFFER_ACCEPTED` event `server_ts` against `offer_resource_confirmation.expires_at`; flag `("I15", e.seq)` if $\min(\text{expires\_at}) \le \text{server\_ts}$ | `T-I15`, `T-F12`, `M6` |
| **I16** | **Monotone Per-Referral Server Timestamp** | Safety (`S`) | $\forall r \in \text{Referral}, \forall k \ge 2: e_k.\text{server\_ts} \ge e_{k-1}.\text{server\_ts}$ | `ts = GREATEST(clock_timestamp(), r.head_ts)` under referral lock (Step 4); trigger `rhp_event_guard` checks `NEW.server_ts >= r.head_ts` | In event fold: if `e.ts < st["ts"]` $\rightarrow$ flag `("I16", e.seq)` | `T-I16`, `T-F11` |

---

## 3. Timing Model, Escalation Arithmetic & Clock Bounds (`F2`, `F3`, `F11`, `I1`, `I13`, `I16`)

### 3.1 Unified Offer-ACK Window ($A$) & Notice Ladder (`F2`)
In earlier drafts (`v4`/`v5`), an intra-facility notice ladder raced the offer ACK timer. RHP-1 eliminates that race by placing all notice rungs **inside** the single offer ACK window $A$:
- **$t = 0$ (Offer `OPEN`):** Push notification over SSE and zero-payload FCM wake ping to **all** rostered duty slots (`NURSE`, `CMO`, `CONSULTANT`) concurrently.
- **$t = A / 4$ (`NOTICE_VOICE` deadline):** Outbound Exotel IVR calls to pre-registered duty numbers, with slot $i \in \{0, \dots, S-1\}$ dialled at $A/4 + i \cdot \delta$.
- **$t = 3A / 4$ (`NOTICE_PROXY` deadline):** Dispatcher console receives a high-priority proxy page to perform a phone-assisted check.
- **$t = A$ (`ACK` deadline):** If no human has ACKed, `TIMEOUT(ACK)` fires (`SOFT_OPEN` + next facility `OPEN` in `SEQUENTIAL` mode). If an `ACK` occurred at any time $t_{\text{ack}} < A$, the notice ladder is cancelled immediately and a hard `DECISION` deadline is set for $t_{\text{ack}} + D$.

### 3.2 Worst-Case Escalation Bound $T_{max}$ (`F3`, `I13`)
Because all $S$ rostered slots at a facility are notified within window $A$, slots never multiply the facility timeout. The worst-case time spent at a single facility occurs when the receiver ACKs just before $A$ expires ($A - \epsilon'$) and then remains silent through the full decision window $D$ (counter-offers are capped by $\min(C, \text{remaining } D)$ and cannot extend $D$). Including per-hop poller + transaction overhead $\epsilon$, the maximum time from `CREATE` to `ESCALATED_TO_DISPATCHER` across $F$ facilities is:
$$T_{max} = F \cdot (A + D + \epsilon) \le B$$

Additionally, when voice is enabled, the staggered outbound calls of duration budget $V$ must complete before the $3A/4$ proxy rung:
$$\lfloor A / 4 \rfloor + (S - 1) \cdot \delta + V \le \lfloor 3A / 4 \rfloor$$

### 3.3 Locked Signed Timing Profiles (All Durations in Milliseconds)

| Parameter | `PILOT_OB_CRITICAL` | `PILOT_STANDARD` | `DEMO_FAST` | `DEMO_VOICE` |
|---|---|---|---|---|
| **ACK Window ($A$)** | $60{,}000\text{ ms}$ ($60\text{ s}$) | $120{,}000\text{ ms}$ ($120\text{ s}$) | $3{,}000\text{ ms}$ ($3\text{ s}$) | $45{,}000\text{ ms}$ ($45\text{ s}$) |
| **Decision Window ($D$)** | $180{,}000\text{ ms}$ ($180\text{ s}$) | $300{,}000\text{ ms}$ ($300\text{ s}$) | $4{,}000\text{ ms}$ ($4\text{ s}$) | $20{,}000\text{ ms}$ ($20\text{ s}$) |
| **Notice Rungs ($0, A/4, 3A/4$)** | $0 / 15{,}000 / 45{,}000$ | $0 / 30{,}000 / 90{,}000$ | $0 / 750 / 2{,}250$ | $0 / 11{,}250 / 33{,}750$ |
| **Slots ($S$), Stagger ($\delta$), Call Budget ($V$)** | $S=3, \delta=5{,}000, V=20{,}000$ | $S=3, \delta=10{,}000, V=20{,}000$ | $S=3, \delta=0, \text{voice}=\text{off}$ | $S=1, \delta=0, V=20{,}000$ |
| **Max Facilities ($F$)** | $3$ | $3$ | $3$ | $2$ |
| **Per-Hop Budget ($\epsilon$)** | $3{,}000\text{ ms}$ ($3\text{ s}$) | $3{,}000\text{ ms}$ ($3\text{ s}$) | $1{,}000\text{ ms}$ ($1\text{ s}$) | $1{,}000\text{ ms}$ ($1\text{ s}$) |
| **Counter Confirm ($C$)** | $90{,}000\text{ ms}$ | $150{,}000\text{ ms}$ | $2{,}000\text{ ms}$ | $10{,}000\text{ ms}$ |
| **Confirmation TTL (`confirm_ttl`)** | $120{,}000\text{ ms}$ | $180{,}000\text{ ms}$ | $10{,}000\text{ ms}$ | $60{,}000\text{ ms}$ |
| **Handover ($H$) / Dispatch / Closure** | $7.2\times 10^6 / 3\times 10^5 / 8.64\times 10^7$ | $7.2\times 10^6 / 3\times 10^5 / 8.64\times 10^7$ | $30{,}000 / 5{,}000 / 20{,}000$ | $60{,}000 / 10{,}000 / 60{,}000$ |
| **Worked $T_{max} = F \cdot (A + D + \epsilon)$** | $3 \cdot (60 + 180 + 3)\text{ s} = 729\text{ s}$ | $3 \cdot (120 + 300 + 3)\text{ s} = 1{,}269\text{ s}$ | $3 \cdot (3 + 4 + 1)\text{ s} = 24\text{ s}$ | $2 \cdot (45 + 20 + 1)\text{ s} = 132\text{ s}$ |
| **Configured Bound ($B$)** | $900{,}000\text{ ms}$ ($900\text{ s}$) | $1{,}500{,}000\text{ ms}$ ($1{,}500\text{ s}$) | $25{,}000\text{ ms}$ ($25\text{ s}$) | $150{,}000\text{ ms}$ ($150\text{ s}$) |
| **Voice Stagger Check** | $15\text{s} + 10\text{s} + 20\text{s} = 45\text{s} \le 45\text{s}$ | $30\text{s} + 20\text{s} + 20\text{s} = 70\text{s} \le 90\text{s}$ | Voice disabled | $11.25\text{s} + 0 + 20\text{s} = 31.25\text{s} \le 33.75\text{s}$ |
| **Boot Allowed with `REAL_DATA=1`** | **YES** | **YES** | **NO (Hard Abort)** | **NO (Hard Abort)** |

---

## 4. Formal Control-Plane Model (`spec/rhp1.qnt`)

Person A maintains `spec/rhp1.qnt` to verify invariants `I2`, `I3`, `I12`, `I13`, and escalation completeness across all non-deterministic interleavings.

```quint
// spec/rhp1.qnt — RHP-1 Bounded Model Checker Specification (Person A)
module rhp1 {
  val FACS = 1.to(3)
  val MAXE = 4
  val OPEN_ST = Set("OPEN", "ACKED", "COUNTERED", "SOFT")
  var hs: str
  var off: int -> str
  var lease: int
  var epoch: int
  var cursor: int
  var tr: str
  var par: bool

  def nOpen(m) = FACS.filter(f => OPEN_ST.contains(m.get(f))).size()
  def live = hs != "CLOSED" and hs != "CANCELLED"
  def inFlight = Set("OFFERED", "ACKNOWLEDGED", "COUNTERED").contains(hs)
  def nextTr(t) = if (t == "REQUESTED") "DISPATCHED" else if (t == "DISPATCHED") "EN_ROUTE" else if (t == "EN_ROUTE") "ARRIVED" else if (t == "ARRIVED") "HANDED_OVER" else t

  action init = {
    nondet p = Set(true, false).oneOf()
    all { hs' = "CREATED", off' = FACS.mapBy(f => "NONE"), lease' = 0, epoch' = 0, cursor' = 0, tr' = "REQUESTED", par' = p }
  }
  action offerFirst = all {
    hs == "CREATED",
    off' = FACS.mapBy(f => if (f == 1 or (par and f == 2)) "OPEN" else "NONE"),
    cursor' = if (par) 2 else 1, hs' = "OFFERED",
    lease' = lease, epoch' = epoch, tr' = tr, par' = par
  }
  action ack(f) = all {
    inFlight, off.get(f) == "OPEN",
    off' = FACS.mapBy(g => if (g == f) "ACKED" else if (g == f - 1 and off.get(g) == "SOFT") "TIMEOUT" else off.get(g)),
    hs' = "ACKNOWLEDGED", lease' = lease, epoch' = epoch, cursor' = cursor, tr' = tr, par' = par
  }
  action grant(f, from) = all {
    inFlight, lease == 0, epoch < MAXE, from.contains(off.get(f)),
    off' = FACS.mapBy(g => if (g == f) "ACCEPTED" else if (OPEN_ST.contains(off.get(g))) "SUPERSEDED" else off.get(g)),
    lease' = f, epoch' = epoch + 1, hs' = "ACCEPTED", cursor' = cursor, tr' = tr, par' = par
  }
  action accept(f) = grant(f, Set("OPEN", "ACKED", "SOFT"))
  action confirm(f) = grant(f, Set("COUNTERED"))
  action counter(f) = all {
    inFlight, Set("OPEN", "ACKED").contains(off.get(f)),
    off' = off.set(f, "COUNTERED"), hs' = "COUNTERED",
    lease' = lease, epoch' = epoch, cursor' = cursor, tr' = tr, par' = par
  }
  action decline(f) = {
    val m1 = off.set(f, "DECLINED")
    val nxt = f + 1
    all {
      inFlight, OPEN_ST.contains(off.get(f)),
      if (nOpen(m1) > 0) all { off' = m1, cursor' = cursor, hs' = hs }
      else if (nxt <= 3 and off.get(nxt) == "NONE") all { off' = m1.set(nxt, "OPEN"), cursor' = nxt, hs' = "OFFERED" }
      else all { off' = m1, cursor' = cursor, hs' = "DISPATCH" },
      lease' = lease, epoch' = epoch, tr' = tr, par' = par
    }
  }
  action timeout(f) = {
    val nxt = f + 1
    val canNext = nxt <= 3 and off.get(nxt) == "NONE"
    all {
      inFlight, Set("OPEN", "ACKED", "COUNTERED").contains(off.get(f)),
      if (canNext) all {
        off' = FACS.mapBy(g => if (g == f) (if (par) "TIMEOUT" else "SOFT") else if (g == nxt) "OPEN" else if (off.get(g) == "SOFT") "TIMEOUT" else off.get(g)),
        cursor' = nxt, hs' = "OFFERED"
      } else all {
        off' = off.set(f, "TIMEOUT"), cursor' = cursor,
        hs' = if (nOpen(off.set(f, "TIMEOUT")) > 0) hs else "DISPATCH"
      },
      lease' = lease, epoch' = epoch, tr' = tr, par' = par
    }
  }
  action arrivalRejected = all {
    hs == "ACCEPTED", lease != 0, epoch < MAXE,
    off' = if (lease < 3 and off.get(lease + 1) == "NONE") off.set(lease, "REJECTED").set(lease + 1, "OPEN") else off.set(lease, "REJECTED"),
    hs' = if (lease < 3 and off.get(lease + 1) == "NONE") "OFFERED" else "DISPATCH",
    cursor' = if (lease < 3 and off.get(lease + 1) == "NONE") lease + 1 else cursor,
    lease' = 0, epoch' = epoch + 1, tr' = tr, par' = par
  }
  action dispatchAssign(f) = all {
    hs == "DISPATCH", epoch < MAXE, Set("NONE", "TIMEOUT").contains(off.get(f)),
    off' = off.set(f, "ACCEPTED"), lease' = f, epoch' = epoch + 1, hs' = "ACCEPTED", cursor' = cursor, tr' = tr, par' = par
  }
  action trStep = all {
    live, tr != "HANDED_OVER", tr' = nextTr(tr),
    hs' = hs, off' = off, lease' = lease, epoch' = epoch, cursor' = cursor, par' = par
  }
  action cancel = all {
    live, hs' = "CANCELLED",
    off' = FACS.mapBy(f => if (OPEN_ST.contains(off.get(f)) or off.get(f) == "ACCEPTED") "WITHDRAWN" else off.get(f)),
    lease' = 0, epoch' = epoch, cursor' = cursor, tr' = tr, par' = par
  }
  action close = all {
    Set("ACCEPTED", "DISPATCH").contains(hs), hs' = "CLOSED",
    off' = off, lease' = lease, epoch' = epoch, cursor' = cursor, tr' = tr, par' = par
  }
  action step = {
    nondet f = FACS.oneOf()
    any { offerFirst, ack(f), accept(f), confirm(f), counter(f), decline(f), timeout(f), arrivalRejected, dispatchAssign(f), trStep, cancel, close }
  }

  val nAcc = FACS.filter(f => off.get(f) == "ACCEPTED").size()
  val I2 = nAcc <= 1 and ((lease != 0) == (nAcc == 1))
  val I12 = nOpen(off) <= 2
  val I1m = inFlight implies nOpen(off) >= 1
  val IDisp = (hs == "DISPATCH") implies nOpen(off) == 0
  val I13 = epoch <= MAXE
  val safety = I2 and I12 and I1m and IDisp and I13

  run transportNeverGated = init.then(trStep).then(offerFirst).then(trStep)
}
```

---

## 5. Clean-Room Independent Runtime Monitor (`F17`) & Mutation Suite (`M1`–`M6`)

### 5.1 Common-Mode Independence (`F17`)
To prevent a shared bug between the server and the monitor:
1. **Person A** owns `api/`, `spec/transitions.yaml`, and `spec/rhp1.qnt`.
2. **Person B** owns `monitor/monitor.py`, writing it solely from the §3 invariant table in `FINAL_LOCKED_Architecture.md` in an isolated workspace.
3. `monitor/monitor.py` imports **zero** application modules from `api/`, connects to PostgreSQL using the read-only role `rhp_monitor` (`REPEATABLE READ READ ONLY`), folds every referral's `event` stream from genesis (`seq = 1`), evaluates `I1`–`I16`, and performs a differential state check against the live `referral` and `offer` tables.

```python
# monitor/monitor.py — Person B Independent Runtime Monitor (Zero Server Imports)
import hashlib
import json
import os
import time
import psycopg
from psycopg.rows import namedtuple_row

TAU_MS = int(os.environ.get("RHP_MONITOR_TAU_MS", "4000"))  # 2 poller intervals + 2000 ms

def jcs(obj: dict) -> bytes:
    """RFC 8785 Canonical JSON for ASCII keys and int/str/bool values (no floats)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def compute_hash(prev_hash: bytes, core: dict) -> bytes:
    return hashlib.sha256(prev_hash + jcs(core)).digest()

EVENT_QUERY = """
SELECT referral_id, seq, event_id, type, epoch,
       actor_roster_id::text AS a, actor_facility_id::text AS f,
       channel, proxy, detail, encode(secret_hash, 'hex') AS sh,
       client_ts_ms, (extract(epoch FROM server_ts) * 1000000)::bigint AS ts,
       prev_hash, hash, server_ts
  FROM event
 ORDER BY referral_id, seq
"""

def fold_referral_events(rows, ref_row, offers_for_ref, roster_map, confirm_map):
    st = {
        "seq": 0,
        "head": b"\x00" * 32,
        "epoch": 0,
        "lease": None,
        "ts": 0,
        "seen_facilities": set(),
        "viol": [],
    }
    for e in rows:
        # I4: Gap-free sequence
        if e.seq != st["seq"] + 1:
            st["viol"].append(("I4", e.seq))
        # I5: Hash chain continuity
        if bytes(e.prev_hash) != st["head"]:
            st["viol"].append(("I5", e.seq))
        core = {
            "referral_id": str(e.referral_id),
            "seq": e.seq,
            "event_id": str(e.event_id),
            "type": e.type,
            "epoch": e.epoch,
            "actor_roster_id": e.a,
            "facility_id": e.f,
            "channel": e.channel,
            "proxy": e.proxy,
            "detail": e.detail,
            "secret_hash": e.sh,
            "client_ts_ms": e.client_ts_ms,
            "server_ts_us": e.ts,
        }
        if compute_hash(bytes(e.prev_hash), core) != bytes(e.hash):
            st["viol"].append(("I5", e.seq))
        # I16: Monotone server_ts
        if e.ts < st["ts"]:
            st["viol"].append(("I16", e.seq))
        # I8: Epoch never decreases on applied events
        if e.epoch < st["epoch"]:
            st["viol"].append(("I8", e.seq))
        # I9 & I7: No duplicate facility in OFFER_CREATED and target in chain
        if e.type == "OFFER_CREATED":
            fac = e.detail.get("facility")
            if fac in st["seen_facilities"]:
                st["viol"].append(("I9", e.seq))
            st["seen_facilities"].add(fac)
            if e.detail.get("source") == "CHAIN" and fac not in [str(x) for x in ref_row.chain]:
                st["viol"].append(("I7", e.seq))
        # I2: Single lease & strictly increasing epoch on grant
        if e.type == "LEASE_GRANTED":
            if st["lease"] is not None or e.epoch <= st["epoch"]:
                st["viol"].append(("I2", e.seq))
            st["lease"] = e.detail.get("facility")
        if e.type in ("LEASE_REVOKED", "ARRIVAL_REJECTED", "CANCELLED"):
            st["lease"] = None
        # I6: Roster validity on response events
        if e.type in ("OFFER_ACCEPTED", "OFFER_COUNTERED", "OFFER_DECLINED") and not e.proxy:
            r_slot = roster_map.get(e.a)
            if r_slot is None or not (r_slot.valid_from <= e.server_ts and (r_slot.valid_to is None or e.server_ts <= r_slot.valid_to)):
                st["viol"].append(("I6", e.seq))
        # I15: Unexpired confirmations on OFFER_ACCEPTED
        if e.type == "OFFER_ACCEPTED":
            fac = e.detail.get("facility")
            exp_list = confirm_map.get((str(e.referral_id), fac), [])
            if exp_list and min(exp_list) <= e.server_ts:
                st["viol"].append(("I15", e.seq))

        st["epoch"] = max(st["epoch"], e.epoch)
        st["seq"] = e.seq
        st["head"] = bytes(e.hash)
        st["ts"] = e.ts

    # Check active ACCEPTED offers count (I2) and open offers count (I12)
    acc_offers = [o for o in offers_for_ref if o.status == "ACCEPTED"]
    open_offers = [o for o in offers_for_ref if o.status in ("OPEN", "ACKED", "COUNTERED", "SOFT_OPEN")]
    if len(acc_offers) > 1:
        st["viol"].append(("I2", st["seq"]))
    if len(open_offers) > 2 or ref_row.open_offers > 2 or len(open_offers) != ref_row.open_offers:
        st["viol"].append(("I12", st["seq"]))
    # I5: Terminal outcome presence
    if (ref_row.hs_state in ("CLOSED", "CANCELLED")) != (ref_row.outcome is not None):
        st["viol"].append(("I5", st["seq"]))

    return st

def cycle(dsn: str) -> list:
    with psycopg.connect(dsn, row_factory=namedtuple_row) as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        refs = {r.id: r for r in conn.execute("SELECT * FROM referral").fetchall()}
        offers_by_ref = {}
        for o in conn.execute("SELECT * FROM offer").fetchall():
            offers_by_ref.setdefault(o.referral_id, []).append(o)
        roster_map = {str(r.id): r for r in conn.execute("SELECT * FROM roster").fetchall()}
        confirm_map = {}
        for c in conn.execute(
            "SELECT o.referral_id, o.facility_id, orc.expires_at FROM offer_resource_confirmation orc JOIN offer o ON o.id = orc.offer_id"
        ).fetchall():
            confirm_map.setdefault((str(c.referral_id), str(c.facility_id)), []).append(c.expires_at)

        events_by_ref = {}
        with conn.cursor(name="snap_events") as cur:
            cur.execute(EVENT_QUERY)
            for e in cur:
                events_by_ref.setdefault(e.referral_id, []).append(e)

        violations = []
        for rid, r in refs.items():
            ev_list = events_by_ref.get(rid, [])
            st = fold_referral_events(ev_list, r, offers_by_ref.get(rid, []), roster_map, confirm_map)
            if (st["seq"], st["head"]) != (r.head_seq, bytes(r.head_hash)):
                violations.append(("DIFF_HEAD", str(rid), st["seq"]))
            if st["epoch"] != r.lease_epoch:
                violations.append(("DIFF_EPOCH", str(rid), st["seq"]))
            for v_code, v_seq in st["viol"]:
                violations.append((v_code, str(rid), v_seq))

        # I1: Overdue PENDING deadlines beyond tolerance TAU_MS
        for d in conn.execute(
            "SELECT referral_id FROM deadline WHERE status='PENDING' AND due_at < clock_timestamp() - (%s * interval '1 millisecond')",
            (TAU_MS,),
        ).fetchall():
            violations.append(("I1", str(d.referral_id), 0))

        # I3: Check rejected_command for illegal TR_UPDATE blocks
        for rc in conn.execute(
            "SELECT referral_id, id FROM rejected_command WHERE command='TR_UPDATE' AND reason_code NOT IN ('REFERRAL_TERMINAL','INVALID_TR_TRANSITION','HUMAN_CONFIRMATION_REQUIRED')"
        ).fetchall():
            violations.append(("I3", str(rc.referral_id), rc.id))

        return violations
```

### 5.2 Six Mandatory Mutation Tests (`F17`) & Safe `BROKEN_BUILD` (`F20`)

Every mutation test disables a specific guard; CI passes **only** if the designated independent checker trips and names the exact invariant violation:

| Mutation ID | Injected Fault | Target Artifact | Checker That Must Trip | Expected Violation Signal |
|---|---|---|---|---|
| **M1** | Bypass `expected_epoch == r.lease_epoch` check in Step 5 of `apply_command()` | Server (`api/`) | Monitor + Vector `V-STALE-EPOCH` | `("I8", referral_id, seq)` |
| **M2** | Remove `FOR UPDATE` on `referral` and drop `one_lease` index on scratch DB (`BROKEN_BUILD=1`) | Server + Scratch DB | `T-C1 race200` + Monitor | `("I2", referral_id, seq)` ($\ge 2$ `ACCEPTED` offers within $\le 2\text{ s}$) |
| **M3** | Make poller hold `SELECT ... FOR UPDATE` on `deadline` across `apply_command()` call | Poller (`api/poller.py`) | `T-F1 lock_order_200way` | `deadlocks_delta() > 0` or `I14_LOCK_NOT_HELD` |
| **M4** | Remove `nOpen(m1) > 0` / cap check in `rhp1.qnt` so a 3rd offer opens simultaneously | Quint (`spec/rhp1.qnt`) | `quint run rhp1.qnt --invariant safety` | Counterexample trace violating `I12` (`nOpen(off) == 3`) |
| **M5** | Write `prev_hash = b'\x00' * 32` on `seq > 1` in `append_event()` | Server (`api/`) | Pure-JS Browser Verifier + Monitor | `BROKEN referral=... seq=2 kind=PREV` and `("I5", referral_id, 2)` |
| **M6** | Skip `expires_at > ts` check on `offer_resource_confirmation` during `ACCEPT` | Server (`api/`) | Vector `V-STALE-CONFIRM` + Monitor | `("I15", referral_id, seq)` |

**Safe `BROKEN_BUILD` Isolation (`F20`):**
When `BROKEN_BUILD=1` is toggled in the Guarantee Arena demo (Scene 5), the server routes exclusively to the isolated scratch database `rhp_scratch_broken` (created by `scripts/make_scratch.sh` without the `one_lease` index). The startup guard executes three hard-abort checks (`sys.exit(78)`) before binding any port:
1. `os.environ.get("REAL_DATA") != "1"`,
2. `dsn_dbname == "rhp_scratch_broken"`, and
3. The scratch database role fails authentication against the primary `rhp` database.
The `/mode` endpoint causes the big screen, witness, and PWA desks to render a flashing red banner: **`BROKEN BUILD — SCRATCH DB`**.