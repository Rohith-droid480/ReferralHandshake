# ReferralHandshake (Protocol RHP-1) — Testing & Formal Verification Requirements

**Verification Strategy:** Bounded Model Checking (`Quint`) + Independent Runtime Monitor + 6 Mutation Tests + 200-Way Barrier Concurrency + Toxiproxy Chaos + 52-Row Failure Matrix  
**Common-Mode Independence Rule (`F17`):** Person A authors `/api/**`, `/spec/transitions.yaml`, and `/spec/rhp1.qnt`. Person B authors `/monitor/monitor.py` from Section 3 prose of the architecture specification alone, in an isolated workspace that imports zero server modules.

---

## 1. Executable Quint Control-Plane Specification (`spec/rhp1.qnt`)

```quint
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

**Mandatory Quint Commands & Non-Vacuity Gates:**
1. `quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000` $\rightarrow$ Must pass (`0` violations).
2. `quint verify spec/rhp1.qnt --invariant safety --max-steps 25` $\rightarrow$ Bounded model check at $F=3, \text{MAXE}=4$.
3. **Non-Vacuity Assertions (each MUST find a counterexample proving state reachability):**
   - `quint run spec/rhp1.qnt --invariant 'not (hs == "ACCEPTED")'` $\rightarrow$ Must FAIL.
   - `quint run spec/rhp1.qnt --invariant 'not (hs == "DISPATCH")'` $\rightarrow$ Must FAIL.
   - `quint run spec/rhp1.qnt --invariant 'not (hs == "CLOSED")'` $\rightarrow$ Must FAIL.
   - `quint run spec/rhp1.qnt --invariant 'not (FACS.exists(f => off.get(f) == "SOFT"))'` $\rightarrow$ Must FAIL.

---

## 2. Executable Independent Python Runtime Monitor (`monitor/monitor.py`)

Written by Person B from Section 3 prose alone; connects as `rhp_monitor` (`REPEATABLE READ READ ONLY`):

```python
import hashlib
import json
import os
import time
import psycopg
from psycopg.rows import namedtuple_row

TAU_MS = int(os.getenv("RHP_TAU_MS", "4000"))

def jcs(o: dict) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def compute_hash(prev: bytes, core: dict) -> bytes:
    return hashlib.sha256(prev + jcs(core)).digest()

EVENT_QUERY = """
SELECT referral_id, seq, event_id, type, epoch,
       actor_roster_id::text AS a, actor_facility_id::text AS f,
       channel, proxy, detail, encode(secret_hash, 'hex') AS sh, client_ts_ms,
       (extract(epoch FROM server_ts) * 1000000)::bigint AS ts, prev_hash, hash
FROM event
ORDER BY referral_id, seq
"""

def fold(rows):
    st = dict(seq=0, head=b"\x00" * 32, epoch=0, lease=None, ts=0, seen_ids=set(), targets=set(), viol=[])
    for e in rows:
        if e.seq != st["seq"] + 1:
            st["viol"].append(("I4_SEQ_GAP", e.seq))
        if e.event_id in st["seen_ids"]:
            st["viol"].append(("I4_DUP_EVENT_ID", e.seq))
        st["seen_ids"].add(e.event_id)
        if bytes(e.prev_hash) != st["head"]:
            st["viol"].append(("I5_PREV_HASH", e.seq))
        core = dict(
            referral_id=str(e.referral_id), seq=e.seq, event_id=str(e.event_id),
            type=e.type, epoch=e.epoch, actor_roster_id=e.a, facility_id=e.f,
            channel=e.channel, proxy=e.proxy, detail=e.detail,
            secret_hash=e.sh, client_ts_ms=e.client_ts_ms, server_ts_us=e.ts
        )
        if compute_hash(bytes(e.prev_hash), core) != bytes(e.hash):
            st["viol"].append(("I5_HASH_MISMATCH", e.seq))
        if e.ts < st["ts"]:
            st["viol"].append(("I16_NON_MONOTONE_TS", e.seq))
        if e.epoch < st["epoch"]:
            st["viol"].append(("I8_STALE_EPOCH_APPLIED", e.seq))
        if e.type == "OFFER_CREATED":
            fac = e.detail.get("facility")
            if fac in st["targets"] and e.detail.get("source") == "CHAIN":
                st["viol"].append(("I9_DUP_TARGET", e.seq))
            st["targets"].add(fac)
        if e.type == "LEASE_GRANTED":
            if st["lease"] is not None or e.epoch <= st["epoch"]:
                st["viol"].append(("I2_DOUBLE_OR_STALE_LEASE", e.seq))
            st["lease"] = e.detail.get("facility")
        if e.type in ("LEASE_REVOKED", "ARRIVAL_REJECTED", "CANCELLED"):
            st["lease"] = None
        st["epoch"] = max(st["epoch"], e.epoch)
        st["seq"] = e.seq
        st["head"] = bytes(e.hash)
        st["ts"] = e.ts
    return st

def cycle(dsn: str) -> list:
    with psycopg.connect(dsn, row_factory=namedtuple_row) as c:
        c.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        c.read_only = True
        rows = {}
        refs = {r.id: r for r in c.execute("SELECT * FROM referral").fetchall()}
        with c.cursor(name="snap") as cur:
            cur.execute(EVENT_QUERY)
            for e in cur:
                rows.setdefault(e.referral_id, []).append(e)
        out = []
        for rid, ev in rows.items():
            st, r = fold(ev), refs[rid]
            if (st["seq"], st["head"]) != (r.head_seq, bytes(r.head_hash)):
                out.append(("DIFF_HEAD", str(rid), st["seq"]))
            if st["epoch"] != r.lease_epoch:
                out.append(("DIFF_EPOCH", str(rid), st["epoch"]))
            out += [(v[0], str(rid), v[1]) for v in st["viol"]]
            if r.open_offers > 2 or r.open_offers < 0:
                out.append(("I12_OPEN_OFFERS_CAP", str(rid), r.open_offers))
        acc_counts = c.execute(
            "SELECT referral_id FROM offer WHERE status='ACCEPTED' GROUP BY referral_id HAVING count(*) > 1"
        ).fetchall()
        for row in acc_counts:
            out.append(("I2_MULTIPLE_ACCEPTED_OFFERS", str(row.referral_id), 0))
        overdue = c.execute(
            "SELECT referral_id FROM deadline WHERE status='PENDING' "
            "AND due_at < clock_timestamp() - (%s * interval '1 millisecond')",
            (TAU_MS,)
        ).fetchall()
        for d in overdue:
            out.append(("I1_OVERDUE_DEADLINE", str(d.referral_id), 0))
        bad_tr = c.execute(
            "SELECT referral_id FROM rejected_command WHERE command='TR_UPDATE' "
            "AND reason_code NOT IN ('INVALID_TR','REFERRAL_TERMINAL')"
        ).fetchall()
        for b in bad_tr:
            out.append(("I3_TRANSPORT_BLOCKED", str(b.referral_id), 0))
        return out
```

---

## 3. Six Mandatory Mutation Tests (`F17`) & Concurrency / Chaos Suites

### 3.1 Mutation Suite (`T-F17`)
Each mutation disables a specific guard; CI passes **only if** the independent checker immediately trips with the expected signal:

| ID | Injected Mutation | Target Artifact | Checker That Must Trip | Expected Violation Signal |
|---|---|---|---|---|
| **M1** | Comment out `expected_epoch == r.lease_epoch` check in Step 5 of `apply_command()`. | Server (`api/`) | Monitor + Conformance Vector `V-STALE-EPOCH` | `I8_STALE_EPOCH_APPLIED` |
| **M2** | Remove `FOR UPDATE` on `referral` and run against `rhp_scratch_broken` (without `one_lease`). | Server + Scratch DB | `T-C1` (`race200`) + Monitor | `I2_MULTIPLE_ACCEPTED_OFFERS` (within $\le 2\text{ s}$) |
| **M3** | Modify poller to hold `SELECT ... FOR UPDATE` on `deadline` while calling `apply_command()`. | Poller (`api/`) | `T-F1` (`lock_order_200way`) + `rhp_require_lock` | `deadlocks_delta > 0` or `I14_LOCK_NOT_HELD` |
| **M4** | Remove `nOpen(m1) > 0` cap guard in `rhp1.qnt` so a 3rd offer opens simultaneously. | Quint (`spec/rhp1.qnt`) | `quint run spec/rhp1.qnt --invariant safety` | `I12` counterexample trace |
| **M5** | Write `prev_hash = b"\x00" * 32` on `seq >= 2` in `append_event()`. | Server (`api/`) | Browser Verifier + Monitor | `I5_PREV_HASH` (`BROKEN ... kind=PREV`) |
| **M6** | Bypass `expires_at > ts` check on `offer_resource_confirmation` during `ACCEPT`. | Server (`api/`) | Vector `V-STALE-CONFIRM` + Monitor | `I15` violation |

### 3.2 200-Way Asyncio Barrier Concurrency Test (`T-C1` / `race200`)
- Spawns $n = 200$ coroutines synchronized on `asyncio.Barrier(200)` firing `POST /v1/offers/{offer_id}/accept` across both open offers of a `PARALLEL2` referral.
- **Pass Criteria:**
  1. `sum(r.status_code == 200 for r in rs) == 1` (exactly one winner).
  2. All $199$ losers return deterministic `409` or `412` (`0` HTTP `500`s).
  3. `SELECT count(*) FROM offer WHERE referral_id = $1 AND status = 'ACCEPTED'` equals `1`.
  4. `SELECT max(seq) - count(*) FROM event WHERE referral_id = $1` equals `0` (gap-free sequence).
  5. `pg_stat_database.deadlocks` delta before vs. after equals `0`.

### 3.3 Toxiproxy 8-Fault Chaos Matrix (API $\leftrightarrow$ DB and Client $\leftrightarrow$ API)
1. **Latency Up ($500\text{ ms} \pm 200\text{ ms}$):** p95 grows; zero duplicate events (`I4`).
2. **Latency Down:** Retries replay stored response (`F14`); single state transition.
3. **Bandwidth Cap ($10\text{ KB/s}$):** SSE stream resumes cleanly via `Last-Event-ID` (`T-N3`).
4. **Slow Close:** No leaked `IN_FLIGHT` rows after TTL purge.
5. **Timeout ($2\text{ s}$ cut):** Client retry with same `Idempotency-Key` receives stored or fresh `200 OK`; single event row.
6. **Reset Peer (`RST` mid-flight):** Aborted transaction leaves zero orphan rows; retry succeeds cleanly.
7. **TCP Slicer ($16\text{-byte}$ slices):** JSON frames reassemble; RFC 8785 hash chain verified intact (`I5`).
8. **Limit Data / Complete Partition (`enabled=false` for $10\text{ s}$):** Outbox relay redelivers within visibility timeout ($\le 30\text{ s}$); monitor stays green (`0` violations).

---

## 4. Complete 52-Row Failure-Mode & Attack Matrix [F15]

Every identified weakness is classified as `CLOSED` (enforced mechanism + automated test), `BOUNDED` (stated technical residual + live monitor alarm), or `OPEN` (named owner + closing evidence):

| ID | Class | Scenario | Detection | Auto-Response | Human Fallback | Inv | Bounded Technical Residual & Reason | Test ID | Status |
|---|---|---|---|---|---|---|---|---|---|
| **C1** | Concurrency | 200 simultaneous `ACCEPT` requests | Lock wait log | `referral` row lock + `one_lease`; losers get `409` | — | `I2` | Relies on PostgreSQL 16 row-lock and unique-index correctness | `T-C1` | `CLOSED` |
| **C2** | Concurrency | `ACCEPT` vs `TIMEOUT` race | Lock order | First lock holder decides; both outcomes legal | — | `I2` | Either outcome possible within $\le 1\text{ ms}$ lock window; both audited | `T-C2` | `CLOSED` |
| **C3** | Concurrency | Late `ACCEPT` after successor `ACK` | Offer state check | `409 LATE_ACCEPT_REJECTED` | Desk re-offers via dispatcher | `I2` | Offline receiver sees rejection only upon reconnect sync | `T-C3` | `CLOSED` |
| **C4** | Concurrency | `COUNTER` + competing `ACCEPT` | Referral lock | Loser gets `409 LEASE_HELD` | Referrer sees reason | `I2`, `I12` | Decided deterministically under single referral row lock | `T-C4` | `CLOSED` |
| **C5** | Concurrency | Poller vs command deadlock | `log_lock_waits` | Single-statement Phase 1 claim; global lock order | — | `I14` | PostgreSQL internal lock manager assumed sound | `T-F1` | `CLOSED` |
| **C6** | Concurrency | Duplicate timer firing | Status re-read | Returns `200` no-op under lock | — | `I1`, `I4` | `status='PENDING'` verified inside `referral` lock | `T-C6` | `CLOSED` |
| **C7** | Concurrency | Stale writer (old version/epoch) | Step 5 check | `412` + `rejected_command` row | Client refetches state | `I8` | Deterministic rejection under savepoint `sp_cmd` | `T-I8` | `CLOSED` |
| **C8** | Concurrency | 3rd concurrent offer attempted | DB CHECK | Rejected; escalates to dispatcher | Dispatcher assigns | `I12` | Enforced by `CHECK (open_offers BETWEEN 0 AND 2)` | `T-F13` | `CLOSED` |
| **T1** | Timer | Poller process crash | `heartbeat` table | Claim lapses in $\le 5\text{ s}$; standby poller claims | Operator restart | `I1` | Extra escalation delay $\le 5\text{ s claim} + 1\text{ s poll} = 6\text{ s}$ | `T-T1` | `BOUNDED` |
| **T2** | Timer | Host clock forward step $\Delta$ | NTP offset alarm | Deadlines fire up to $\Delta$ early | Operator alert | `I2`, `I16` | Premature escalation only; `SOFT_OPEN` preserves accept ability | `T-F11` | `BOUNDED` |
| **T3** | Timer | Host clock backward step $\Delta$ | NTP offset $> 2\text{ s}$ | `GREATEST(clock_timestamp(), head_ts)` preserves order | Operator alert | `I16` | Deadlines delayed by $\le \Delta$ ($\le 2\text{ s}$ before alarm trips) | `T-F11` | `BOUNDED` |
| **T4** | Timer | Deadline storm after DB outage | Queue depth metric | Drains $50\text{ claims/tick}$ ordered by `due_at` | Dispatcher paged | `I1` | Drain latency $\lceil n / 50 \rceil$ poller ticks | `T-T4` | `BOUNDED` |
| **T5** | Timer | Primary DB failover mid-timer | Connection reset | Poller reconnects; durable `deadline` rows survive | — | `I1` | Managed Multi-AZ failover window $60\text{–}120\text{ s}$ `[V*]` | `T-T5` | `BOUNDED` |
| **T6** | Timer | Signed profile file tampered | Ed25519 verify | Refuses application boot | Admin restores profile | `I13` | Offline cold-key compromise out of software scope | `T-F2` | `CLOSED` |
| **N1** | Network | Offline stale `ACCEPT` replayed | Step 7 `expires_at` | `409 STALE_CONFIRMATION_RECONFIRM_REQUIRED` | Live reconfirm UI | `I15` | Enforced by `expires_at > server_ts` under lock | `T-F12` | `CLOSED` |
| **N2** | Network | HTTP response lost, client retries | `idempotency` PK | Returns stored response without re-execution | — | `I4` | $48\text{ h}$ key TTL; `event.event_id UNIQUE` guards permanently | `T-F14` | `CLOSED` |
| **N3** | Network | SSE connection dropped | $15\text{ s}$ heartbeat | Auto-reconnects with `Last-Event-ID` | Browser refresh | `I4` | Desk UI view stale for $\le 15\text{ s}$ until heartbeat timeout | `T-N3` | `BOUNDED` |
| **N4** | Network | Ambulance enters cellular dead zone | Device `heartbeat` | Room outbox queues; UI shows `"last confirmed Ns ago"` | Crew phones dispatcher | `I3` | Live map GPS position stale for duration of dead zone | `T-N4` | `BOUNDED` |
| **N5** | Network | Exotel webhook duplicate retry | `inbox` UNIQUE | Deduplicated via `ON CONFLICT DO NOTHING` | — | `I4` | Zero duplicate `ACK`/`ACCEPT` commands | `T-N5` | `CLOSED` |
| **N6** | Network | Webhook DB lock wait $> 1.5\text{ s}$ | Internal timer | Returns `"please hold"` XML; re-polls next callback | Next notice rung | `I1` | Caller waits $\le 1$ extra IVR callback cycle ($\approx 3\text{ s}$) | `T-N6` | `BOUNDED` |
| **N7** | Network | Venue internet down during demo | Uplink probe | Switches to local hotspot LAN mode | LAN QR + MP4 clips | — | Plain HTTP lacks WebCrypto; pure-JS `@noble` libraries used | `T-N7` | `BOUNDED` |
| **N8** | Network | Flaky-network retry storm | Rate limiter | Returns `429` + idempotent replay | — | `I4` | Initial burst $\le 1\text{ s}$ window before token bucket engages | `T-N8` | `BOUNDED` |
| **I1** | Identity | Unrostered person attempts `ACCEPT` | Step 5 roster check | `403` + `rejected_command` audit row | Admin roster update | `I6` | Physical sharing of a valid PIN among colleagues at same desk | `T-I6` | `CLOSED` |
| **I2** | Identity | PIN brute-force guessing | `pin_failed` count | Argon2id + backoff + $120\text{ s}$ lock at 3rd fail | Dispatcher paged | `I6` | New call/session resets scope, but requires registered phone/device | `T-F7` | `BOUNDED` |
| **I3** | Identity | Rival locks out hospital's duty role | Per-session scope | Lockout isolated to attacker's `session_id`/`call_sid` | — | `I6` | Legitimate ward tablet session remains unlocked | `T-F7` | `CLOSED` |
| **I4** | Identity | SIM swap on duty phone number | Lockout alert rate | Admin suspends `roster` slot after repeated lockouts | Dispatcher proxy | `I6` | Exposure window between carrier SIM swap and lockout detection | `T-I4` | `BOUNDED` |
| **I5** | Identity | Voicemail auto-answers Exotel call | AMD + press-1 gate | Marks call `UNANSWERED`; zero `ACK` recorded | Next ladder rung | `I6` | Unauthorized human pressing `1` hears de-identified prompt; PIN still gates `ACCEPT` | `T-F7` | `CLOSED` |
| **I6** | Identity | BOLA / JSON mass-assignment of `hs_state` | Authz + Pydantic | `403` facility mismatch; `422` `extra='forbid'` | — | `I6` | New routes added in future must include authz matrix test | `T-I6b` | `CLOSED` |
| **P1** | Privacy | PHI injected into `event.detail` | `rhp_detail_ok` | Rejected by Pydantic + PostgreSQL CHECK constraint | — | `I11` | Uppercase enum string could theoretically encode a short code; blocked by `Literal` | `T-F9` | `BOUNDED` |
| **P2** | Privacy | PHI leaked in DLT SMS text | Template lint | Static alert text + short code only | — | — | Zero clinical variables in SMS template | `T-P2` | `CLOSED` |
| **P3** | Privacy | PHI leaked in FCM push payload | Payload lint | Empty wake ping `{}` + authenticated HTTPS fetch | — | `I10` | Zero payload bytes sent through FCM | `T-P3` | `CLOSED` |
| **P4** | Privacy | SSE stream read after grant revoked | Per-frame filter | Emits `GRANT_REVOKED`; strips clinical frames; wipes DOM | — | `I10` | Data already viewed or photographed on screen prior to revocation | `T-F10` | `BOUNDED` |
| **P5** | Privacy | Shredded payload persists in WAL/backup | Restore test | Monthly `kek_epoch` master key destruction | — | — | Backups remain decryptable until the monthly `kek_epoch` cohort expires | `T-P5` | `BOUNDED` |
| **A1** | AI | Hallucinated VLM/ASR draft field | 20-slip seeded gate | Cognitive Forcing Function + mandatory critical re-entry | Clinician manual edit | — | Target rubber-stamp rate $\le 5\%$, not $0\%$ | `T-A1` | `BOUNDED` |
| **A2** | AI | AI draft viewed before clinician anchors | API guard test | Returns `423 ANCHOR_REQUIRED` until `need_class` + `mgso4_status` set | — | — | Enforced server-side before draft JSON is returned | `T-A2` | `CLOSED` |
| **A3** | AI | Kannada ASR dialect transcription error | Safety gate | `T3_EXTRAS` off by default; structured manual entry primary | Manual entry | — | Indic ASR WER $> 20\%$ on rural dialects `[V]` | `T-A3` | `BOUNDED` |
| **K1** | Clinical | Pre-referral $\text{MgSO}_4$ dose unknown | Mandatory enum | Allows `UNKNOWN`; sets red desk banner; never blocks dispatch | Receiver verifies | `I3` | Depends on receiving clinician reading the red verification banner | `T-K1` | `BOUNDED` |
| **K2** | Clinical | Hospital accepts to game KPI, delays bed | APOT metric split | Tracks `ARRIVED -> HANDED_OVER` separately; `ARRIVAL_REJECTED` | District review | `I2` | Software cannot create physical ICU/OT beds | `T-K2` | `BOUNDED` |
| **K3** | Clinical | Tertiary hospital funnelling overload | Open-offer cap | Returns `AT_CAPACITY` decline; advances down catchment chain | Dispatcher override | `I7` | Depends on district administrators configuring realistic capacity caps | `T-K3` | `BOUNDED` |
| **K4** | Clinical | Ambulance already past highway turn-off | Redirect advisory | Displays cached Mapbox detour ETA; never auto-reroutes | Crew/dispatcher decides | `I3` | Crew may be unreachable in dead zone during redirect | `T-F5` | `BOUNDED` |
| **S1** | Insider | DBA edits `event` row as superuser | Browser verifier | Recomputes SHA-256 chain; names exact `seq` & `kind=HASH` | Incident response | `I5` | Tamper-*evident* (detects within $\le 5\text{ s}$), not tamper-preventive against root | `T-F8` | `BOUNDED` |
| **S2** | Insider | Operator serves split-view history | Witness compare | Judges' phones + big screen + off-box laptop compare roots | Audit investigation | `I5` | Requires $\ge 2$ independent honest witnesses holding checkpoints | `T-S2` | `BOUNDED` |
| **S3** | Insider | Witness Ed25519 signing key stolen | Key rotation drill | OS user isolation (`0400`); key rotation + cold-key revoke | Admin rotates key | `I5` | Attacker with key + DB root can sign forged checkpoints until rotation (HSM absent) | `T-S3` | `OPEN` |
| **S4** | Insider | Dispatcher abuses override assignment | Monitor audit flag | Requires reason enum; flagged `proxy=true` on big screen | District officer review | `I6` | Authorized human can enter a plausible but false override reason | `T-S4` | `BOUNDED` |
| **F1** | Infra | FastAPI container killed mid-request | Health probe | Container restarts; client retries with `Idempotency-Key` | — | `I4` | In-flight uncommitted txn aborts cleanly; client retry adds $\le 2\text{ s}$ | `T-F1b` | `BOUNDED` |
| **F2** | Infra | PostgreSQL primary instance failure | Multi-AZ monitor | Synchronous standby promoted; clients/workers reconnect | Operator runbook | `I1` | $60\text{–}120\text{ s}$ Multi-AZ promotion window `[V*]` | `T-F2b` | `BOUNDED` |
| **F3** | Infra | Outbox relay crashes after sending | Visibility timeout | Row reappears after $30\text{ s}$; consumers dedupe by `outbox.id` | — | `I4` | Up to $30\text{ s}$ redelivery delay on crashed relay batch | `T-F3b` | `BOUNDED` |
| **F4** | Infra | OEM battery saver kills Android service | Device `heartbeat` | Big screen flags stale GPS; PWA manual location button | Crew taps manual update | `I3` | MIUI/ColorOS background kill behavior varies by OEM `[GAP]` | `T-F4b` | `BOUNDED` |
| **L1** | Legal | Automated voice clinical prompt legality | Legal review | Sandbox + $\le 10$ whitelisted team numbers + synthetic data | Dispatcher phone call | — | Unsettled under Indian telecom/health regulations `[GAP]` (Owner: Legal Advisor) | `T-L1` | `OPEN` |
| **L2** | Legal | DPDP s.8(7) erasure vs 3-yr retention | Policy parameter | Configurable `expires_at` + DEK crypto-shredding | Legal counsel | — | Applicability of 3-yr telemedicine rule to handover records `[GAP]` (Owner: Legal) | `T-L2` | `OPEN` |
| **L3** | Legal | Over-claiming BSA s.63 certification | CI claims linter | Exports hash bundle + Part A/B templates only; never claims certified | — | `I5` | Enforced by automated forbidden-phrase CI scan (`ST-5`) | `T-L3` | `CLOSED` |
| **L4** | Legal | CERT-In 6 h / DPBI 72 h breach clock | Incident runbook | Automated tamper/lockout alerts trigger incident log | Operator files report | — | Reporting clock depends on human operator acknowledging alert | `T-L4` | `BOUNDED` |
| **D1** | Demo | iOS Safari lacks WebCrypto Ed25519 | Preflight test | Uses bundled pure-JS `@noble/curves/ed25519` | Server verify (labelled) | `I5` | Pure-JS verification takes $\approx 15\text{–}40\text{ ms}$ per checkpoint on mobile | `T-D1` | `BOUNDED` |
| **D2** | Demo | Exotel trial restricted to $\le 10$ numbers | Preflight check | Calls team's pre-verified feature phone; judges use QR web desks | MP4 call recording | — | Judge personal phone numbers cannot be dialed live on trial account `[V]` | `T-D2` | `BOUNDED` |
| **D3** | Demo | `BROKEN_BUILD=1` accidentally hits real DB | Startup guard | Hard abort (exit `78`) if `REAL_DATA=1` or DSN $\neq$ `rhp_scratch_broken` | — | `I2` | Enforced at process startup before opening listener socket | `T-F20` | `CLOSED` |
| **D4** | Demo | Venue Wi-Fi & cellular both fail on stage | Dual-uplink probe | Local hotspot LAN QR mode + pre-recorded MP4 scene clips | Play MP4 clip (disclosed) | — | Pre-recorded fallback clips are disclosed as recorded on slide | `T-D4` | `BOUNDED` |
| **D5** | Demo | Last-minute code edit breaks demo | Git hook / freeze | Hard code freeze at Hour 22 (`H22`); config-only thereafter | Rollback to last good tag | — | Process control enforced by 3-Gem workflow ledger | `T-D5` | `BOUNDED` |