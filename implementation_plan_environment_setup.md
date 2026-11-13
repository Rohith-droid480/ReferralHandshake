# ReferralHandshake (Protocol RHP-1) — Environment Setup & Implementation Plan

**Team:** MAHA YODHAS | **Track:** HealthTech | **Event:** Colossus 3.0 (13–14 Nov 2026, Bengaluru, 24-Hour Build, 2 Students) `[V]`
**Target Artifact:** `implementation_plan(ENVIRONMENT SETUP) .md`
**Data Posture:** Synthetic data only (`REAL_DATA=0`)
**First Clinical Pathway:** Emergency obstetric referral across Karnataka-style tiers (`PHC -> CHC -> FRU -> DH -> MC`); generic schema supports `NEONATAL`, `TRAUMA`, `CARDIAC`, and `STROKE`.

---

## 0. Authority Hierarchy, Coherence Rule & Hard Architectural Locks

### 0.1 Input Precedence (Non-Negotiable)
Any ambiguity discovered during environment setup, tooling configuration, or implementation is resolved strictly in this order:
1. `ReferralHandshake_LOCKED_Problem_Statement_v7.md` (Highest authority on problem framing, evidence tags, and claims discipline)
2. Research findings tagged `[V]` inside the locked documents
3. `ReferralHandshake_v8_LOCKED_Solution.md` (Authority on D1–D20 fixes, 28 scenarios, 40-item loophole ledger, and operating model)
4. `ReferralHandshake_FINAL_LOCKED_Architecture.md` (Ultimate authority on F1–F20 closures, I1–I16 invariants, 24-table PostgreSQL 16 DDL, 10-step `apply_command()` pipeline, timing math, Quint spec, independent Python monitor, and T0–T3 tiers)
5. `ReferralHandshake_3Gem_Antigravity_Workflow.md` (Authority on `AGENTS.md`, Lane A/B isolation, 3-Gem verification ring, and step-tagging rules)

### 0.2 Status & Weakness Tags
- **Evidence Tags:** `[V]` verified primary source · `[V*]` secondary/vendor source · `[CONFLICT]` sources disagree · `[GAP]` no reliable fact found (parameterised) · `[verify]` pre-event verification test required (§21).
- **Weakness Tags:** `CLOSED` (enforced by code/DB mechanism + named test) · `BOUNDED` (stated technical residual + monitor alarm) · `OPEN` (assigned owner + closing evidence required).

### 0.3 The Coherence Rule
Every file, container, script, and dependency in this environment must belong to exactly one of three categories:
1. **(a) Contract Core:** A state or event in the RHP-1 contract (`PostgreSQL 16`, `apply_command()`, durable timers, outbox).
2. **(b) Channel Interface:** An adapter that produces or consumes contract events (`React PWA`, `Kotlin Android`, `Exotel IVR`, `DLT SMS`, `Paper Code`, `Dispatcher Console`).
3. **(c) Read-Only Projection:** A reader of the committed append-only event log (`Independent Python Monitor`, `Ed25519 Witness/Signer`, `Pure-JS Browser Verifier`, `Command Centre`, `FHIR/XES Exporters`).
Anything outside `(a)`, `(b)`, or `(c)` is strictly out of scope.

### 0.4 Locked Stack vs. Banned Technologies

| Layer | Locked Technology | Banned Technologies (CI Hard-Fail if Present) |
|---|---|---|
| **Database** | PostgreSQL 16 single writable primary (`synchronous_commit=on`, `READ COMMITTED`, explicit `SELECT ... FOR UPDATE`, `FOR UPDATE SKIP LOCKED`) | SQLite for contract state, distributed NoSQL, read-replica locking, CRDTs for authoritative state |
| **Backend API & Workers** | Python 3.12, FastAPI, `psycopg` (v3), Pydantic v2 (`extra='forbid'`), stateless 2-phase Poller, visibility-timeout Outbox Relay | Kafka, Debezium, RabbitMQ, Redis, Celery, Kubernetes, GraphQL |
| **Web Clients** | React 18 + TypeScript + Vite PWA, SSE (`Last-Event-ID`, 15 s heartbeats), pure-JS `@noble/curves/ed25519` & `@noble/hashes/sha256` | WebSockets, native WebCrypto `crypto.subtle` for Ed25519 (breaks on iOS Safari & LAN HTTP `[V]`) |
| **Mobile Client** | Native Android Kotlin (`FOREGROUND_SERVICE_TYPE_LOCATION`, `FusedLocationProviderClient`, Room outbox, empty-payload FCM wake); PWA GPS fallback (`T1`) | Unencrypted push payloads containing PHI, background iOS location claims |
| **Reach Channels** | Exotel outbound IVR (AMD + press-1 gate, $\le 10$ whitelisted sandbox numbers, HTTP 200 within $\le 2\text{ s}$ budget `[V]`), DLT static SMS, 9-char Crockford Base32 + mod-37 paper code | WhatsApp, inbound unauthenticated IVR, dynamic PHI in SMS variables |
| **Serialization & Crypto** | RFC 8785 JCS canonical JSON (integers, ASCII strings, booleans only), SHA-256 hash chain, Ed25519 checkpoints, AES-256-GCM DEK + AES-KW KEK, Argon2id | Floating-point numbers in JCS payloads, blockchain / smart contracts, salt-deletion "crypto-shredding" |
| **Verification & Chaos** | Quint (`rhp1.qnt`) + Apalache, Person B Python Monitor (`REPEATABLE READ READ ONLY`), `asyncio.Barrier(200)`, Hypothesis, Toxiproxy | Shared code between `api/` and `monitor/`, AI-modifiable specs, on-device LLMs |

---

## 1. Repository Layout & Two-Lane Ownership Boundaries (F17)

To enforce **F17 (Common-Mode Failure Prevention)**, **Person A (Lane A)** owns the backend, database DDL, `transitions.yaml`, and Quint specification, while **Person B (Lane B)** writes the independent Python runtime monitor from §3 prose alone and owns the client/reach interfaces. The `monitor/` directory must have **zero** imports from `api/`.

```text
referral-handshake/
├── AGENTS.md                           # Mandatory builder rules for Google Antigravity
├── CODEOWNERS                          # Pinned human ownership for spec/, db/, monitor/
├── .gitignore                          # Excludes .env, *.key, *.mp4, __pycache__, node_modules
├── .env.example                        # Template environment configuration (REAL_DATA=0)
├── docker-compose.yml                  # 9-service local/demo stack (PG16, API, Poller, Relay, Monitor, Witness, Toxiproxy, PWA, Tunnel)
├── docker-compose.broken.yml           # Override for F20 safe BROKEN_BUILD=1 against rhp_scratch_broken
├── spec/                               # READ-ONLY for coding agents; SHA-256 pinned in CI
│   ├── ReferralHandshake_LOCKED_Problem_Statement_v7.md
│   ├── ReferralHandshake_v8_LOCKED_Solution.md
│   ├── ReferralHandshake_FINAL_LOCKED_Architecture.md
│   ├── transitions.yaml                # Frozen declarative state-transition table (Lane A)
│   ├── profiles.json                   # 4 timing profiles + cold-key Ed25519 signatures (Lane B)
│   ├── rhp1.qnt                        # Quint formal control-plane specification (Lane A)
│   └── vectors/                        # Conformance test vectors V-01..V-28 + mutation vectors
├── db/                                 # Database schema and seed scripts (Lane A)
│   ├── schema.sql                      # Complete 24-table PostgreSQL 16 DDL + triggers + roles (§7)
│   ├── seed_synthetic.sql              # Synthetic Karnataka facilities, rosters, chains (REAL_DATA=0)
│   └── verify_ddl.sql                  # Self-audit ST-3 constraint, trigger, and role verifier
├── api/                                # Contract Core & Channel Webhooks (Lane A)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── rhp/
│       ├── __init__.py
│       ├── config.py                   # Startup validator: T_max <= B (I13), REAL_DATA, BROKEN_BUILD guards
│       ├── db.py                       # psycopg3 connection pool + autonomous PIN-failure connection
│       ├── jcs.py                      # RFC 8785 canonical JSON (rejects floats) + SHA-256 chain
│       ├── crypto.py                   # AES-256-GCM envelope encryption, AES-KW, Argon2id, Crockford mod-37
│       ├── transitions.py              # Loader and evaluator for spec/transitions.yaml
│       ├── pipeline.py                 # 10-step apply_command() with referral>offer>deadline>outbox lock order
│       ├── main.py                     # FastAPI routes, SSE per-event grant filter, Exotel/Turnstile webhooks
│       ├── poller.py                   # Stateless 2-phase deadline poller (50 claims/tick, 5 s lease)
│       ├── relay.py                    # Outbox relay (20 rows/tick, 30 s visibility timeout)
│       └── explorer.py                 # Fallback Python explicit-state model checker over transitions.yaml
├── monitor/                            # Independent Runtime Monitor (Lane B — ZERO imports from api/)
│   ├── Dockerfile                      # Runs as UID 1001, connects as rhp_monitor (READ ONLY)
│   ├── requirements.txt
│   └── monitor.py                      # Independent event-log fold + differential check vs referral row
├── witness/                            # Independent Ed25519 Checkpoint Signer (Lane A/B)
│   ├── Dockerfile                      # Runs as OS user rhp-sign (UID 1002), key mode 0400
│   ├── requirements.txt
│   └── signer.py                       # 5 sREPEATABLE READ snapshot, binary Merkle tree, C2SP note signer
├── pwa/                                # React 18 PWA Desks, Big Screen, Verifier, Dispatcher Console (Lane B)
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── crypto/verifier.ts          # Pure-JS @noble/curves/ed25519 & @noble/hashes/sha256 verifier
│       ├── views/ClinicianCard.tsx     # ISBAR+Dakshata card, mgso4_status, printable paper-code slip
│       ├── views/ReceivingDesk.tsx     # Priority queue (no countdowns), resource confirm, ACCEPT/COUNTER/DECLINE
│       ├── views/DispatcherConsole.tsx # ESCALATED_TO_DISPATCHER assignment, proxy entry, replay scrubber
│       ├── views/AmbulancePwa.tsx      # T1 foreground watchPosition GPS + manual update fallback
│       └── views/GuaranteeArena.tsx    # Live I1-I16 counters, race QR, BROKEN_BUILD banner, p50/p95 latency
├── android/                            # Native Android Kotlin EMT Client — Tier T3 (Lane B)
│   └── app/src/main/java/in/mahayodhas/rhp/
├── scripts/                            # Operational, Chaos, and Audit Scripts
│   ├── gen_keys.sh                     # Generates Ed25519 cold/witness keys & signs spec/profiles.json
│   ├── make_scratch.sh                 # Creates rhp_scratch_broken without one_lease for F20 BROKEN_BUILD
│   ├── init_toxiproxy.sh               # Configures Toxiproxy proxies for the 8-toxic fault matrix
│   ├── run_self_audit.sh               # Runs ST-1..ST-5 (lock order, T_max math, DDL scan, idem, forbidden words)
│   └── install_git_hooks.sh            # Installs pre-commit guardrails
└── tests/                              # Conformance, Concurrency, Chaos, and Mutation Suites
    ├── test_conformance.py             # Replays 28 scenario vectors (V-01..V-28)
    ├── test_race200.py                 # T-C1 / T-F1: 200-way asyncio.Barrier concurrent ACCEPT test
    ├── test_mutations.py               # T-F17: M1–M6 mutation suite verifying monitor/verifier detection
    ├── test_toxiproxy.py               # 8-toxic network partition and retry tests
    └── test_invariants_pbt.py          # Hypothesis RuleBasedStateMachine stateful property tests
```

---

## 2. Host Prerequisites, Clock Discipline & Network Topology

### 2.1 Workstation Software Versions (Both Laptops: Laptop A & Laptop B)

Run the following verification commands on both student laptops before starting Phase P or Phase E:

| Tool | Required Version | Verification Command | Purpose |
|---|---|---|---|
| **OS** | Ubuntu 22.04/24.04 LTS, macOS 14+, or WSL2 (Ubuntu) | `uname -a` | Host operating system |
| **Docker Engine & Compose** | Docker $\ge 24.0$, Compose $\ge 2.20$ | `docker --version && docker compose version` | Container orchestration for the 9-service stack |
| **Python** | Python $3.12.\text{x}$ | `python3.12 --version` | Local test runner, Quint explorer fallback, key scripts |
| **Node.js & npm** | Node.js $\ge 20.10\text{ LTS}$, npm $\ge 10$ | `node -v && npm -v` | React PWA build and `@informalsystems/quint` CLI |
| **Java Runtime (JRE/JDK)** | OpenJDK $17$ or $21$ | `java -version` | Required by Quint's Apalache bounded model checker (`quint verify`) |
| **Quint CLI** | `@informalsystems/quint` $\ge 0.21.0$ | `npx @informalsystems/quint --version` | Formal specification simulator & verifier (§12) |
| **PostgreSQL Client** | `psql` $16.\text{x}$ | `psql --version` | Direct DDL inspection, `ST-3` audit, and live forgery demo |
| **Chrony** | `chronyd` $\ge 4.2$ | `chronyc tracking` | Slew-only NTP synchronization (`[F11, I16]`) |
| **Cloudflare Tunnel** | `cloudflared` $\ge 2024.6$ | `cloudflared --version` | Public HTTPS ingress for judge QR desks |

#### Host Installation Script (`Ubuntu / Debian / WSL2`)
```bash
#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y \
  ca-certificates curl gnupg lsb-release git jq build-essential \
  python3.12 python3.12-venv python3.12-dev \
  postgresql-client-16 chrony openjdk-17-jre-headless

# Install Quint globally via npm
sudo npm install -g @informalsystems/quint

# Verify installations
python3.12 --version
psql --version
quint --version
java -version
```

### 2.2 Host Clock Discipline — Slew-Only NTP (`[F11, I16]`)
Per **F11** and **I16**, server time is the sole deadline authority (`ts = GREATEST(clock_timestamp(), referral.head_ts)` under the referral row lock). To prevent unscheduled host clock jumps after boot, configure `chrony` in **slew-only mode** (no `makestep` after boot) against NIC/NPL stratum servers `[V*]`:

```bash
# /etc/chrony/chrony.conf (Pilot & Linux Demo Host)
server time.nplindia.org iburst
server samay1.nic.in iburst
server samay2.nic.in iburst

# Allow step ONLY on the first 3 clock updates at boot if offset > 1.0s;
# after boot, slew all adjustments at max 83333 ppm so clock_timestamp() never steps backward.
makestep 1.0 3
maxslewrate 83333.333
rtcsync
driftfile /var/lib/chrony/chrony.drift
logdir /var/log/chrony
```

The witness and poller record the host's current NTP offset every $5\text{ s}$ into `heartbeat(subject_kind, subject_id, last_seen, ntp_offset_ms)` using `chronyc -c tracking`. Any $| \text{ntp\_offset\_ms} | > 2000\text{ ms}$ triggers an immediate amber clock alarm on the Guarantee Arena big screen (`T-F11`).

### 2.3 Dual-Uplink & Fail-Closed LAN Mode (`[F7, F10, D4]`)
1. **Primary Uplink:** Team mobile hotspot (`5G/4G`) bound as default route.
2. **Secondary Uplink:** Venue Wi-Fi configured with higher route metric (`metric 200`) for automatic failover.
3. **Judge QR Admission Path A (Internet Up):** Cloudflare Tunnel (`cloudflared`) exposes `https://arena.<domain>` behind Cloudflare WAF + Turnstile challenge. Rotating single-use QR (`jti` valid $20\text{ s}$, rotates every $15\text{ s}$) mints a `JUDGE_DESK` session (admission cap $20$).
4. **Judge QR Admission Path B (Venue Internet Down — Fail-Closed LAN Mode):**
   - Laptop hosts local Wi-Fi AP / hotspot on `http://192.168.42.1:8080`.
   - `LAN_MODE=1` fails closed: refuses boot if `REAL_DATA=1`, enforces admission cap $20$, restricts QR tokens to synthetic `JUDGE_DESK` role, and **disables PIN entry over plain HTTP**.
   - Because iOS Safari and Chrome disable `window.crypto.subtle` on insecure `http://192.168.x.x` origins `[V]`, the PWA uses bundled pure-JS `@noble/curves/ed25519` and `@noble/hashes/sha256` so the browser tamper verifier runs identically on LAN HTTP (`D1`, `N7`).

---

## 3. Cryptographic Keys, Signed Profiles & Environment Variables

### 3.1 Environment Variable Template (`.env.example`)
Create `.env.example` in the repository root and copy it to `.env` (`cp .env.example .env`). **Never commit `.env` or `.secrets/` to Git.**

```ini
# ============================================================================
# ReferralHandshake (Protocol RHP-1) — Environment Configuration
# ============================================================================

# --- Safety & Mode Locks (F2, F20) ---
REAL_DATA=0
BROKEN_BUILD=0
LAN_MODE=0
ACTIVE_PROFILE=DEMO_FAST

# --- Feature Tier Flags (§2, F16) ---
T0_CORE=1
T1_TRANSPORT=1
T2_REACH=1
T3_EXTRAS=0

# --- PostgreSQL 16 Role DSNs (§7, F17, F20) ---
PG_SUPERUSER_DSN=postgresql://postgres:rhp_super_local_only@pg:5432/rhp1
PG_APP_DSN=postgresql://rhp_app:rhp_app_local_only@pg:5432/rhp1
PG_MONITOR_DSN=postgresql://rhp_monitor:rhp_monitor_local_only@pg:5432/rhp1
PG_WITNESS_DSN=postgresql://rhp_witness:rhp_witness_local_only@pg:5432/rhp1
PG_SCRATCH_BROKEN_DSN=postgresql://rhp_scratch:rhp_scratch_local_only@pg:5432/rhp_scratch_broken

# --- Toxiproxy DSN Overrides (Used during Chaos Suite) ---
PG_APP_TOXIC_DSN=postgresql://rhp_app:rhp_app_local_only@toxiproxy:25432/rhp1

# --- Cryptographic Keys & Envelope Encryption (§10, §11, F8) ---
COLD_PUBLIC_KEY_HEX=
WITNESS_PUBLIC_KEY_HEX=
WITNESS_PRIVATE_KEY_PATH=/run/secrets/witness_ed25519.key
SIGNER_KEY_ID=rhp1-witness-2026-11
DEPLOYMENT_ID=colossus3-bengaluru
ACTIVE_KEK_EPOCH=2026-11
KEK_2026_11_HEX=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef

# --- Argon2id Parameters (~100 ms on demo laptop, F7) ---
ARGON2_TIME_COST=2
ARGON2_MEMORY_COST_KIB=65536
ARGON2_PARALLELISM=2

# --- Worker & Monitor Cadence (§5, §11, §12) ---
POLLER_INTERVAL_MS=1000
POLLER_BATCH_LIMIT=50
POLLER_CLAIM_LEASE_S=5
RELAY_INTERVAL_MS=500
RELAY_BATCH_LIMIT=20
RELAY_VISIBILITY_TIMEOUT_S=30
WITNESS_INTERVAL_MS=5000
MONITOR_INTERVAL_MS=1000
MONITOR_TAU_MS=4000

# --- Reach & External APIs (Sandbox / Trial Only, §8, §9, §14) ---
EXOTEL_SID=sandbox_sid
EXOTEL_API_KEY=sandbox_key
EXOTEL_API_TOKEN=sandbox_token
EXOTEL_CALLER_ID=+918040000000
EXOTEL_WEBHOOK_BUDGET_MS=1500
DLT_SMS_TEMPLATE_ID=1107160000000000000
DLT_WHITELISTED_DOMAIN=rhp.example.org
MAPBOX_ACCESS_TOKEN=
CLOUDFLARE_TURNSTILE_SECRET=1x0000000000000000000000000000000AA
JUDGE_ADMISSION_CAP=20
QR_ROTATION_SECONDS=15
QR_TTL_SECONDS=20
```

### 3.2 Key Generation & Profile Signing Script (`scripts/gen_keys.sh`)
Per **§6 (F2, F3, I13)** and **§11 (F8)**, the 4 timing profiles (`PILOT_OB_CRITICAL`, `PILOT_STANDARD`, `DEMO_FAST`, `DEMO_VOICE`) must be signed offline by the Ed25519 cold key, and their SHA-256 hash is pinned in `referral.profile_hash`. The witness signer uses a separate Ed25519 key owned by OS user `rhp-sign` (`UID 1002`, mode `0400`).

Create and make executable `scripts/gen_keys.sh`:

```bash
#!/usr/bin/env bash
# scripts/gen_keys.sh — Generates Ed25519 Cold Key, Witness Key, and Signs spec/profiles.json
set -euo pipefail

mkdir -p .secrets spec
chmod 700 .secrets

python3.12 - <<'PY'
import hashlib, json, os, secrets
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def gen_ed25519(priv_path: str):
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    with open(priv_path, "wb") as f:
        f.write(priv_bytes)
    os.chmod(priv_path, 0o400)
    return priv, pub_bytes.hex()

def jcs(obj) -> bytes:
    # RFC 8785 JCS subset: integers, ASCII strings, booleans, lists, dicts only
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

cold_priv, cold_pub_hex = gen_ed25519(".secrets/cold_ed25519.key")
wit_priv, wit_pub_hex = gen_ed25519(".secrets/witness_ed25519.key")

profiles_raw = [
    {
        "profile_id": "PILOT_OB_CRITICAL",
        "A": 60000, "D": 180000,
        "rungs": [0, 15000, 45000],
        "S": 3, "delta": 5000, "V": 20000, "voice": True,
        "F": 3, "eps": 3000,
        "C": 90000, "confirm_ttl": 120000,
        "H": 7200000, "DISPATCH_ACTION": 300000, "CLOSURE": 86400000,
        "B": 900000, "demo": False
    },
    {
        "profile_id": "PILOT_STANDARD",
        "A": 120000, "D": 300000,
        "rungs": [0, 30000, 90000],
        "S": 3, "delta": 10000, "V": 20000, "voice": True,
        "F": 3, "eps": 3000,
        "C": 150000, "confirm_ttl": 180000,
        "H": 7200000, "DISPATCH_ACTION": 300000, "CLOSURE": 86400000,
        "B": 1500000, "demo": False
    },
    {
        "profile_id": "DEMO_FAST",
        "A": 3000, "D": 4000,
        "rungs": [0, 750, 2250],
        "S": 3, "delta": 0, "V": 0, "voice": False,
        "F": 3, "eps": 1000,
        "C": 2000, "confirm_ttl": 10000,
        "H": 30000, "DISPATCH_ACTION": 5000, "CLOSURE": 20000,
        "B": 25000, "demo": True
    },
    {
        "profile_id": "DEMO_VOICE",
        "A": 45000, "D": 20000,
        "rungs": [0, 11250, 33750],
        "S": 1, "delta": 0, "V": 20000, "voice": True,
        "F": 2, "eps": 1000,
        "C": 10000, "confirm_ttl": 60000,
        "H": 60000, "DISPATCH_ACTION": 10000, "CLOSURE": 60000,
        "B": 150000, "demo": True
    }
]

signed_profiles = {}
for p in profiles_raw:
    # Verify I13 and F2/F3 invariants at signing time
    t_max = p["F"] * (p["A"] + p["D"] + p["eps"])
    assert t_max <= p["B"], f"I13 violation on {p['profile_id']}: {t_max} > {p['B']}"
    assert p["rungs"] == [0, p["A"] // 4, (3 * p["A"]) // 4], f"Rung mismatch on {p['profile_id']}"
    if p["voice"]:
        stagger_end = (p["A"] // 4) + (p["S"] - 1) * p["delta"] + p["V"]
        assert stagger_end <= (3 * p["A"]) // 4, f"Voice stagger exceeds 3A/4 on {p['profile_id']}"
    canonical_bytes = jcs(p)
    profile_hash_hex = hashlib.sha256(canonical_bytes).hexdigest()
    sig_hex = cold_priv.sign(canonical_bytes).hex()
    signed_profiles[p["profile_id"]] = {
        "payload": p,
        "profile_hash_hex": profile_hash_hex,
        "cold_signature_hex": sig_hex
    }

out = {
    "cold_public_key_hex": cold_pub_hex,
    "witness_public_key_hex": wit_pub_hex,
    "profiles": signed_profiles
}
with open("spec/profiles.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, sort_keys=True)

print(f"COLD_PUBLIC_KEY_HEX={cold_pub_hex}")
print(f"WITNESS_PUBLIC_KEY_HEX={wit_pub_hex}")
print("Signed 4 profiles into spec/profiles.json successfully.")
PY
```

### 3.3 Timing Bound Verification Table ($T_{max}$ Math — `[F2, F3, I13]`)
The script above enforces the locked timing equations from **§6**:
- **Worst-Case Escalation Bound:**
  $$T_{max} = F \cdot (A + D + \epsilon) \le B$$
- **Voice Slot Stagger Bound inside ACK Window $A$:**
  $$\frac{A}{4} + (S - 1)\delta + V \le \frac{3A}{4}$$

| Profile ID | $A$ ($\text{ms}$) | $D$ ($\text{ms}$) | $\epsilon$ ($\text{ms}$) | $F$ | Computed $T_{max}$ ($\text{ms}$) | Bound $B$ ($\text{ms}$) | Voice Stagger Check ($\text{ms}$) | `REAL_DATA=1` Allowed |
|---|---|---|---|---|---|---|---|---|
| `PILOT_OB_CRITICAL` | $60000$ | $180000$ | $3000$ | $3$ | $3 \cdot 243000 = 729000$ ($729\text{ s}$) | $900000$ ($900\text{ s}$) | $15000 + 2 \cdot 5000 + 20000 = 45000 \le 45000$ | Yes |
| `PILOT_STANDARD` | $120000$ | $300000$ | $3000$ | $3$ | $3 \cdot 423000 = 1269000$ ($1269\text{ s}$) | $1500000$ ($1500\text{ s}$) | $30000 + 2 \cdot 10000 + 20000 = 70000 \le 90000$ | Yes |
| `DEMO_FAST` | $3000$ | $4000$ | $1000$ | $3$ | $3 \cdot 8000 = 24000$ ($24\text{ s}$) | $25000$ ($25\text{ s}$) | Voice off | **No (Refuses Boot)** |
| `DEMO_VOICE` | $45000$ | $20000$ | $1000$ | $2$ | $2 \cdot 66000 = 132000$ ($132\text{ s}$) | $150000$ ($150\text{ s}$) | $11250 + 0 + 20000 = 31250 \le 33750$ | **No (Refuses Boot)** |

---

## 4. Docker Compose & Multi-Container Architecture (§17)

### 4.1 Complete `docker-compose.yml`
This file orchestrates the 9-service stack with strict OS user isolation (`UID 1001` for `monitor`, `UID 1002` for `witness` with `0400` key mount) and PostgreSQL 16 configured with `synchronous_commit=on` and `log_lock_waits=on`.

```yaml
name: rhp1

services:
  pg:
    image: postgres:16-alpine
    container_name: rhp_pg
    command:
      - "postgres"
      - "-c"
      - "synchronous_commit=on"
      - "-c"
      - "log_lock_waits=on"
      - "-c"
      - "deadlock_timeout=200ms"
      - "-c"
      - "max_connections=250"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: rhp_super_local_only
      POSTGRES_DB: rhp1
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./db/schema.sql:/docker-entrypoint-initdb.d/01_schema.sql:ro
      - ./db/seed_synthetic.sql:/docker-entrypoint-initdb.d/02_seed.sql:ro
      - ./scripts/make_scratch.sh:/docker-entrypoint-initdb.d/03_make_scratch.sh:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d rhp1"]
      interval: 2s
      timeout: 2s
      retries: 15

  toxiproxy:
    image: ghcr.io/shopify/toxiproxy:2.9.0
    container_name: rhp_toxiproxy
    ports:
      - "8474:8474"   # Toxiproxy HTTP control API
      - "25432:25432" # Proxied PostgreSQL port (API <-> DB fault injection)
      - "28000:28000" # Proxied API port (Phone/Client <-> API fault injection)
    depends_on:
      pg:
        condition: service_healthy

  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: rhp_api
    env_file: .env
    environment:
      ACTIVE_PROFILE: ${ACTIVE_PROFILE:-DEMO_FAST}
      REAL_DATA: ${REAL_DATA:-0}
      BROKEN_BUILD: ${BROKEN_BUILD:-0}
    ports:
      - "8000:8000"
    volumes:
      - ./spec:/app/spec:ro
    depends_on:
      pg:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 3s
      timeout: 2s
      retries: 10

  poller:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: rhp_poller
    command: ["python", "-m", "rhp.poller"]
    env_file: .env
    volumes:
      - ./spec:/app/spec:ro
    depends_on:
      api:
        condition: service_healthy

  relay:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: rhp_relay
    command: ["python", "-m", "rhp.relay"]
    env_file: .env
    volumes:
      - ./spec:/app/spec:ro
    depends_on:
      api:
        condition: service_healthy

  monitor:
    build:
      context: ./monitor
      dockerfile: Dockerfile
    container_name: rhp_monitor
    user: "1001:1001"
    read_only: true
    env_file: .env
    environment:
      PG_MONITOR_DSN: ${PG_MONITOR_DSN}
      MONITOR_TAU_MS: ${MONITOR_TAU_MS:-4000}
    ports:
      - "8001:8001"
    depends_on:
      pg:
        condition: service_healthy

  witness:
    build:
      context: ./witness
      dockerfile: Dockerfile
    container_name: rhp_witness
    user: "1002:1002"
    read_only: true
    env_file: .env
    volumes:
      - ./.secrets/witness_ed25519.key:/run/secrets/witness_ed25519.key:ro
      - witness_notes:/var/log/rhp_witness
    depends_on:
      pg:
        condition: service_healthy

  pwa:
    build:
      context: ./pwa
      dockerfile: Dockerfile
    container_name: rhp_pwa
    ports:
      - "8080:8080"
    environment:
      VITE_API_BASE_URL: http://localhost:8000
      VITE_MONITOR_URL: http://localhost:8001
    depends_on:
      - api
      - monitor

  tunnel:
    image: cloudflare/cloudflared:latest
    container_name: rhp_tunnel
    command: ["tunnel", "--no-autoupdate", "--url", "http://pwa:8080"]
     profiles: ["tunnel"]
    depends_on:
      - pwa

volumes:
  pg_data:
  witness_notes:
```

### 4.2 Service Dockerfiles & Dependency Manifests

#### 1. `api/requirements.txt` & `api/Dockerfile` (Contract Core, Poller, Relay — Lane A)
```text
# api/requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
psycopg[binary,pool]==3.2.2
pydantic==2.9.2
argon2-cffi==23.1.0
cryptography==43.0.1
pyyaml==6.0.2
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
hypothesis==6.112.1
```

```dockerfile
# api/Dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY rhp/ ./rhp/
EXPOSE 8000
CMD ["uvicorn", "rhp.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### 2. `monitor/requirements.txt` & `monitor/Dockerfile` (Independent Monitor — Lane B, UID 1001)
```text
# monitor/requirements.txt
psycopg[binary]==3.2.2
fastapi==0.115.0
uvicorn[standard]==0.30.6
pytest==8.3.3
```

```dockerfile
# monitor/Dockerfile
FROM python:3.12-slim
RUN groupadd -g 1001 rhp-mon && useradd -u 1001 -g 1001 -M -s /usr/sbin/nologin rhp-mon
WORKDIR /monitor
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY monitor.py .
USER 1001:1001
EXPOSE 8001
CMD ["python", "monitor.py"]
```

#### 3. `witness/requirements.txt` & `witness/Dockerfile` (Separate-OS-User Signer — UID 1002)
```text
# witness/requirements.txt
psycopg[binary]==3.2.2
cryptography==43.0.1
```

```dockerfile
# witness/Dockerfile
FROM python:3.12-slim
RUN groupadd -g 1002 rhp-sign && useradd -u 1002 -g 1002 -M -s /usr/sbin/nologin rhp-sign \
    && mkdir -p /var/log/rhp_witness && chown 1002:1002 /var/log/rhp_witness
WORKDIR /witness
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY signer.py .
USER 1002:1002
CMD ["python", "signer.py"]
```

#### 4. `pwa/package.json` & `pwa/Dockerfile` (Pure-JS Noble Crypto + React 18 PWA — Lane B)
```json
{
  "name": "rhp1-pwa",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 8080",
    "build": "tsc && vite build",
    "preview": "vite preview --host 0.0.0.0 --port 8080"
  },
  "dependencies": {
    "@noble/curves": "1.6.0",
    "@noble/hashes": "1.5.0",
    "mapbox-gl": "3.6.0",
    "pmtiles": "3.2.0",
    "qrcode.react": "4.1.0",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/react": "18.3.5",
    "@types/react-dom": "18.3.0",
    "@vitejs/plugin-react": "4.3.1",
    "typescript": "5.5.4",
    "vite": "5.4.6"
  }
}
```

```dockerfile
# pwa/Dockerfile
FROM node:20-alpine
WORKDIR /pwa
COPY package.json ./
RUN npm install
COPY . .
EXPOSE 8080
CMD ["npm", "run", "dev"]
```

---

## 5. Database Bootstrap, 24-Table Verification & `BROKEN_BUILD` Scratch DB

### 5.1 Complete 24-Table Schema & Role Grants (`db/schema.sql` — `[F4, F9, I1–I16]`)
`db/schema.sql` must contain the exact 24-table PostgreSQL 16 DDL locked in **Architecture §7**, plus explicit passwords for the local container roles:

| # | Table Name | Category | Primary Key | Enforced Invariants & Constraints |
|---|---|---|---|---|
| 1 | `facility` | Directory | `id (uuid)` | `tier IN ('PHC','CHC','FRU','DH','MC','DISPATCH')` |
| 2 | `roster` | Identity | `id (uuid)` | `role_slot`, `slot_no`, `pin_hash`, `UNIQUE(facility_id, role_slot, slot_no, valid_from)` (I6) |
| 3 | `facility_capability` | Capability | `(facility_id, capability)` | `capability IN ('OT','BLOOD','ANAESTHETIST','PAEDIATRICIAN','NICU')`, `expires_at` |
| 4 | `need_class_requirement` | Capability | `(need_class, capability)` | Maps `OBSTETRIC_EMERGENCY`, `NEONATAL`, `TRAUMA`, `CARDIAC`, `STROKE` to required `cap_t` |
| 5 | `catchment_chain` | Escalation | `(origin_facility_id, need_class, position)` | `position BETWEEN 1 AND 8`, `origin_facility_id <> target_facility_id` (I7) |
| 6 | `device` | Identity | `id (uuid)` | `octet_length(pubkey)=32`, `revoked_at` (I6) |
| 7 | `enrollment_ticket` | Identity | `id (uuid)` | Single-use `token_hash UNIQUE`, `used_at` (F7) |
| 8 | `session` | Identity | `id (uuid)` | `pin_failed`, `pin_locked_until`, `CHECK (device_id IS NOT NULL OR call_sid IS NOT NULL)` (F7) |
| 9 | `referral` | Contract Core | `id (uuid)` | `hs_state`, `tr_state`, `version`, `lease_epoch`, `open_offers BETWEEN 0 AND 2` (I12), `mgso4_status` (D1, I3), terminal outcome CHECK (I5), `lk_referral` (I14), deferred `i1_pending_deadline` (I1) |
| 10 | `offer` | Contract Core | `id (uuid)` | `UNIQUE(referral_id, facility_id)` (I9), partial unique index `one_lease WHERE status='ACCEPTED'` (I2), `counter_round BETWEEN 0 AND 2`, `offer_chain_guard` (I7), `lk_offer` (I14) |
| 11 | `offer_resource_confirmation` | Contract Core | `(offer_id, capability)` | `CHECK (expires_at > confirmed_at)` (F12, I15) |
| 12 | `deadline` | Contract Core | `id (uuid)` | `kind`, `due_at`, `status`, `claimed_until`, `lk_deadline` (I14) |
| 13 | `event` | Evidence Log | `(referral_id, seq)` | `event_id UNIQUE` (I4), `rhp_detail_ok(type, detail)` (F9, I11), `event_ao` append-only trigger, `event_guard` chain & monotone `server_ts` trigger (I5, I16), `lk_event` (I14) |
| 14 | `key_version` | Crypto/Privacy | `id (uuid)` | `status IN ('ACTIVE','SHREDDED')`, `CHECK ((status='SHREDDED') = (wrapped_dek IS NULL))` (D9, §10) |
| 15 | `event_secret` | Crypto/Privacy | `(referral_id, seq)` | AES-256-GCM ciphertext per event |
| 16 | `clinical_payload` | Crypto/Privacy | `referral_id (uuid)` | Envelope-encrypted ISBAR + Dakshata payload |
| 17 | `payload_grant` | Crypto/Privacy | `id (uuid)` | Partial unique index `one_active_grant WHERE revoked_at IS NULL`, `lk_grant` (F10, I10, I14) |
| 18 | `telemetry` | Observations | `id (bigserial)` | `event_id UNIQUE`, append-only GPS & vitals (`kind IN ('GPS','OBS')`) |
| 19 | `idempotency` | Exactly-Once | `(actor_id, key)` | `request_hash`, `status IN ('IN_FLIGHT','DONE')`, stored HTTP status & JSON response (F14, I4) |
| 20 | `inbox` | Webhook Dedupe | `id (bigserial)` | `UNIQUE(source, external_id)` for Exotel/SMS callbacks |
| 21 | `outbox` | Delivery | `id (bigserial)` | `status IN ('PENDING','SENT','DEAD')`, `visible_after`, `attempts`, `lk_outbox` (I14) |
| 22 | `rejected_command` | Fencing Audit | `id (bigserial)` | `http_status IN (401,403,409,412,422,429)`, `rejected_ao` append-only trigger (I8) |
| 23 | `checkpoint` | Witness | `id (bigserial)` | `kind IN ('REGULAR','RESTORE')`, `cold_signature` CHECK, `checkpoint_ao` trigger (F8, I5) |
| 24 | `heartbeat` | Liveness | `(subject_kind, subject_id)` | `last_seen`, `ntp_offset_ms` (F11, §14) |

Append the local password assignments to the end of `db/schema.sql`:
```sql
ALTER ROLE rhp_app WITH PASSWORD 'rhp_app_local_only';
ALTER ROLE rhp_monitor WITH PASSWORD 'rhp_monitor_local_only';
ALTER ROLE rhp_witness WITH PASSWORD 'rhp_witness_local_only';
```

### 5.2 Safe `BROKEN_BUILD` Scratch Database Script (`scripts/make_scratch.sh` — `[F20]`)
Per **F20**, `BROKEN_BUILD=1` must never touch the primary database or run when `REAL_DATA=1`. `scripts/make_scratch.sh` creates `rhp_scratch_broken` from `db/schema.sql` **without** the `one_lease` unique index and isolates credentials so `rhp_scratch` cannot connect to `rhp1`:

```bash
#!/usr/bin/env bash
# scripts/make_scratch.sh — Creates isolated rhp_scratch_broken database without one_lease (F20)
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "rhp1" <<-EOSQL
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rhp_scratch') THEN
      CREATE ROLE rhp_scratch LOGIN PASSWORD 'rhp_scratch_local_only';
    END IF;
  END
  \$\$;
  REVOKE CONNECT ON DATABASE rhp1 FROM rhp_scratch;
EOSQL

psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "postgres" -c "DROP DATABASE IF EXISTS rhp_scratch_broken;"
psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "postgres" -c "CREATE DATABASE rhp_scratch_broken OWNER postgres;"

# Load full schema into rhp_scratch_broken, then drop one_lease so concurrent ACCEPTs can double-grant
psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "rhp_scratch_broken" -f /docker-entrypoint-initdb.d/01_schema.sql
psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "rhp_scratch_broken" -f /docker-entrypoint-initdb.d/02_seed.sql
psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "rhp_scratch_broken" <<-EOSQL
  DROP INDEX IF EXISTS one_lease;
  GRANT CONNECT ON DATABASE rhp_scratch_broken TO rhp_scratch;
  GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO rhp_scratch;
  GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rhp_scratch;
  REVOKE UPDATE, DELETE ON event, checkpoint, rejected_command FROM rhp_scratch;
EOSQL
```

### 5.3 Self-Audit `ST-3` DDL Verification Script (`db/verify_ddl.sql`)
Run `psql "$PG_SUPERUSER_DSN" -v ON_ERROR_STOP=1 -f db/verify_ddl.sql` to verify that all 24 tables, triggers, indexes, and role separations are active:

```sql
-- db/verify_ddl.sql — Self-Audit ST-3: Verifies 24 tables, triggers, indexes, and roles
DO $$
DECLARE
  tbl_count int;
  trg_count int;
BEGIN
  SELECT count(*) INTO tbl_count
  FROM information_schema.tables
  WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
  IF tbl_count <> 24 THEN
    RAISE EXCEPTION 'ST-3 FAIL: Expected exactly 24 base tables, found %', tbl_count;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'one_lease') THEN
    RAISE EXCEPTION 'ST-3 FAIL: Partial unique index one_lease (I2) is missing';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'one_active_grant') THEN
    RAISE EXCEPTION 'ST-3 FAIL: Partial unique index one_active_grant (I10) is missing';
  END IF;

  SELECT count(*) INTO trg_count
  FROM pg_trigger
  WHERE tgname IN (
    'event_ao', 'checkpoint_ao', 'rejected_ao', 'event_guard',
    'lk_referral', 'lk_offer', 'lk_deadline', 'lk_event', 'lk_grant', 'lk_outbox',
    'i1_pending_deadline', 'offer_chain_guard'
  );
  IF trg_count <> 12 THEN
    RAISE EXCEPTION 'ST-3 FAIL: Expected 12 RHP triggers, found %', trg_count;
  END IF;

  -- Verify rhp_monitor has zero privileges on clinical_payload and event_secret
  IF has_table_privilege('rhp_monitor', 'clinical_payload', 'SELECT')
     OR has_table_privilege('rhp_monitor', 'event_secret', 'SELECT') THEN
    RAISE EXCEPTION 'ST-3 FAIL: rhp_monitor must not have SELECT on clinical tables';
  END IF;

  -- Verify rhp_app cannot UPDATE or DELETE event rows
  IF has_table_privilege('rhp_app', 'event', 'UPDATE')
     OR has_table_privilege('rhp_app', 'event', 'DELETE') THEN
    RAISE EXCEPTION 'ST-3 FAIL: rhp_app must not have UPDATE/DELETE on event';
  END IF;

  RAISE NOTICE 'ST-3 PASS: All 24 tables, 12 triggers, partial unique indexes, and role boundaries verified.';
END $$;
```

---

## 6. Startup Guards, Toxiproxy Setup & Self-Audit Script (`ST-1`..`ST-5`)

### 6.1 Startup Configuration & `BROKEN_BUILD` Guard (`api/rhp/config.py` — `[F2, F3, F20, I13]`)
Every backend process (`api`, `poller`, `relay`) executes `validate_boot_environment()` before binding a port or opening a database pool:

```python
# api/rhp/config.py
import hashlib, json, os, sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import psycopg

def jcs(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def validate_boot_environment() -> dict:
    real_data = os.getenv("REAL_DATA", "0") == "1"
    broken_build = os.getenv("BROKEN_BUILD", "0") == "1"
    lan_mode = os.getenv("LAN_MODE", "0") == "1"
    profile_id = os.getenv("ACTIVE_PROFILE", "DEMO_FAST")

    # F20: Hard abort (exit 78) if BROKEN_BUILD is enabled near real data or main DB
    if broken_build:
        if real_data:
            sys.stderr.write("FATAL F20: BROKEN_BUILD=1 forbidden when REAL_DATA=1\n")
            sys.exit(78)
        dsn = os.getenv("PG_SCRATCH_BROKEN_DSN", "")
        if "rhp_scratch_broken" not in dsn or "rhp_scratch" not in dsn:
            sys.stderr.write("FATAL F20: BROKEN_BUILD=1 requires rhp_scratch_broken DSN\n")
            sys.exit(78)
        # Verify scratch role cannot connect to main database rhp1
        main_dsn = dsn.replace("/rhp_scratch_broken", "/rhp1")
        try:
            with psycopg.connect(main_dsn, connect_timeout=2):
                sys.stderr.write("FATAL F20: Scratch role was able to authenticate to main DB rhp1\n")
                sys.exit(78)
        except psycopg.OperationalError:
            pass

    if lan_mode and real_data:
        sys.stderr.write("FATAL: LAN_MODE=1 forbidden when REAL_DATA=1\n")
        sys.exit(78)

    with open("/app/spec/profiles.json", "r", encoding="utf-8") as f:
        bundle = json.load(f)

    cold_pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(bundle["cold_public_key_hex"]))
    entry = bundle["profiles"][profile_id]
    p = entry["payload"]

    # Verify Ed25519 cold-key signature & SHA-256 hash on active profile
    canonical = jcs(p)
    cold_pub.verify(bytes.fromhex(entry["cold_signature_hex"]), canonical)
    assert hashlib.sha256(canonical).hexdigest() == entry["profile_hash_hex"], "Profile hash mismatch"

    # F2 / F3 / I13: Verify T_max <= B and voice ladder stagger math
    t_max = p["F"] * (p["A"] + p["D"] + p["eps"])
    assert t_max <= p["B"], f"I13: T_max ({t_max}) > B ({p['B']})"
    if p["voice"]:
        assert (p["A"] // 4) + (p["S"] - 1) * p["delta"] + p["V"] <= (3 * p["A"]) // 4, "Voice stagger exceeds 3A/4"
    assert p["rungs"] == [0, p["A"] // 4, (3 * p["A"]) // 4], "Rung mismatch"
    if p["demo"] and real_data:
        sys.stderr.write(f"FATAL F2: Demo profile {profile_id} forbidden with REAL_DATA=1\n")
        sys.exit(78)

    return {"profile": p, "profile_hash": bytes.fromhex(entry["profile_hash_hex"]), "broken_build": broken_build}
```

### 6.2 Toxiproxy Initialization Script (`scripts/init_toxiproxy.sh`)
Configures the proxies required by the §12 8-toxic fault-injection matrix (`latency up`, `latency down`, `bandwidth`, `slow_close`, `timeout`, `reset_peer`, `slicer`, `limit_data`):

```bash
#!/usr/bin/env bash
# scripts/init_toxiproxy.sh — Initializes API<->DB and Phone<->API proxies in Toxiproxy
set -euo pipefail

TOXI_URL="${TOXI_URL:-http://localhost:8474}"

curl -sf -X DELETE "${TOXI_URL}/proxies/pg_proxy" >/dev/null 2>&1 || true
curl -sf -X DELETE "${TOXI_URL}/proxies/api_proxy" >/dev/null 2>&1 || true

curl -sf -X POST "${TOXI_URL}/proxies" \
  -H "Content-Type: application/json" \
  -d '{"name":"pg_proxy","listen":"0.0.0.0:25432","upstream":"pg:5432","enabled":true}'

curl -sf -X POST "${TOXI_URL}/proxies" \
  -H "Content-Type: application/json" \
  -d '{"name":"api_proxy","listen":"0.0.0.0:28000","upstream":"api:8000","enabled":true}'

echo "Toxiproxy pg_proxy (:25432 -> pg:5432) and api_proxy (:28000 -> api:8000) armed."
```

### 6.3 Self-Audit Runner (`scripts/run_self_audit.sh` — `ST-1`..`ST-5`)
Executes all 5 mandatory CI self-audits defined in **Architecture §23**:

```bash
#!/usr/bin/env bash
# scripts/run_self_audit.sh — Executes ST-1..ST-5 from Architecture §23
set -euo pipefail

echo "=== [ST-1] Lock Order & I14 Trigger Verification ==="
pytest -q tests/test_race200.py -k "test_lock_order_and_i14"

echo "=== [ST-2] T_max & Voice Stagger Arithmetic Verification ==="
python3.12 scripts/gen_keys.sh >/dev/null

echo "=== [ST-3] 24-Table DDL, FK, Index, and Role Privilege Scan ==="
psql "${PG_SUPERUSER_DSN:-postgresql://postgres:rhp_super_local_only@localhost:5432/rhp1}" \
  -v ON_ERROR_STOP=1 -f db/verify_ddl.sql

echo "=== [ST-4] Idempotency Edge-Case Matrix (8/8 Cases) ==="
pytest -q tests/test_conformance.py -k "test_idempotency_matrix"

echo "=== [ST-5] Claims Discipline & Lane Isolation Scan ==="
# 1. Verify monitor/ imports nothing from api/
if grep -R -E "from rhp|import rhp" monitor/; then
  echo "ST-5 FAIL: monitor/ must never import server code (F17 violation)"
  exit 1
fi
# 2. Verify no banned technologies appear in dependency manifests
if grep -i -E "kafka|debezium|redis|celery|web3|ethereum|whatsapp|langchain" api/requirements.txt monitor/requirements.txt pwa/package.json; then
  echo "ST-5 FAIL: Banned technology detected in dependency manifests"
  exit 1
fi
# 3. Verify forbidden claims do not appear in UI / README copy (excluding §19 register)
if grep -R -i -E "mathematically proven system|bullet-proof|airtight|zero loopholes|immutable log|ABDM compliant|BSA certified|lives saved|eliminates ping-pong" pwa/src/ README.md 2>/dev/null; then
  echo "ST-5 FAIL: Forbidden claim phrase found in UI/docs (§19 violation)"
  exit 1
fi

echo "=== ALL SELF-AUDITS (ST-1..ST-5) PASSED ==="
```

---

## 7. Multi-Agent Governance Setup (3-Gem + Antigravity Ring)

### 7.1 `CODEOWNERS` & Pre-Commit Hook (`scripts/install_git_hooks.sh`)
Per **§7.1 of v8** and **§12 (F17)**, the specification, conformance vectors, database DDL, and independent monitor are owned by humans and hash-pinned so coding agents cannot alter the spec or tests to make a failing build pass (reward-hacking prevention).

Create `CODEOWNERS` in the repository root:
```text
# CODEOWNERS — Human-owned frozen specifications and independent monitor (F17)
/spec/                  @person-a @person-b
/db/schema.sql          @person-a
/monitor/               @person-b
/AGENTS.md              @person-a @person-b
```

Create `scripts/install_git_hooks.sh` and run it once per clone:
```bash
#!/usr/bin/env bash
# scripts/install_git_hooks.sh — Installs pre-commit guardrails for Antigravity
set -euo pipefail

cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

# 1. Block committing .env or private keys
if git diff --cached --name-only | grep -E '^\.env$|^\.secrets/.*\.key$'; then
  echo "PRE-COMMIT BLOCKED: Never commit .env or .secrets/*.key files."
  exit 1
fi

# 2. Enforce F17: monitor/ must never import api/rhp
if grep -R -E "from rhp|import rhp" monitor/ 2>/dev/null; then
  echo "PRE-COMMIT BLOCKED (F17): monitor/ must not import server code."
  exit 1
fi

# 3. Enforce spec freeze unless OVERRIDE_SPEC_FREEZE=1 is explicitly set by human
if [[ "${OVERRIDE_SPEC_FREEZE:-0}" != "1" ]]; then
  if git diff --cached --name-only | grep -E '^spec/(ReferralHandshake_.*|transitions\.yaml|rhp1\.qnt|vectors/)'; then
    echo "PRE-COMMIT BLOCKED: /spec files are frozen. Human must set OVERRIDE_SPEC_FREEZE=1 after SPEC-DEVIATION approval."
    exit 1
  fi
fi
HOOK
chmod +x .git/hooks/pre-commit
echo "Installed .git/hooks/pre-commit successfully."
```

### 7.2 Setting Up the 3 Gemini Gems & Two Antigravity Workspaces
Before the clock starts, configure two parallel lanes (**Lane A** for Person A, **Lane B** for Person B):

1. **Upload the 4 Locked Knowledge Files to Gem 1 (CONDUCTOR), Gem 2 (AUDITOR), and Gem 3 (ADVERSARY):**
   - `ReferralHandshake_LOCKED_Problem_Statement_v7.md`
   - `ReferralHandshake_v8_LOCKED_Solution.md`
   - `ReferralHandshake_FINAL_LOCKED_Architecture.md`
   - `AGENTS.md`
2. **Create 6 Dedicated Gem Chat Threads:**
   - Lane A: `G1-A (Conductor)`, `G2-A (Auditor)`, `G3-A (Adversary)`
   - Lane B: `G1-B (Conductor)`, `G2-B (Auditor)`, `G3-B (Adversary)`
3. **Create 3 Isolated Antigravity Workspaces:**
   - **Workspace A (`branch: lane-a/backend-proof`):** Builds `api/`, `witness/`, `db/`, `spec/rhp1.qnt`, and backend tests.
   - **Workspace B-Client (`branch: lane-b/clients-reach`):** Builds `pwa/`, `android/`, Exotel/SMS/paper-code views.
   - **Workspace B-Monitor (`branch: lane-b/monitor-isolated`):** Builds `monitor/monitor.py` with **no access to `api/`** (only `db/schema.sql` and Architecture §3 prose are visible in this workspace, enforcing F17).

---

## 8. Pre-Event Verification Runbook (§21) & Phase P / Phase E Execution Schedule

### 8.1 Pre-Event Verification Checklist (§21 `[verify]`)
Run every item in this table during **Phase P Step P6** and record the outcome in the STATE LEDGER before the 24-hour build begins:

| # | Verification Item | Time Box | Exact Command / Test Procedure | Locked Fallback if Test Fails |
|---|---|---|---|---|
| 1 | Event rules on pre-built work & AI-assisted coding | $1.0\text{ h}$ | Read official Colossus 3.0 rulebook & confirm with organisers in writing | Keep only Phase P spec documents; build all application code at the event in Phase E |
| 2 | Exotel concurrency, DTMF `%23`, and AMD | $1.5\text{ h}$ | Trigger 5 concurrent outbound sandbox calls to whitelisted team phones; test voicemail box vs human `Press 1` + `PIN#` (`%23`) | Sequential slot calls ($\delta > 0$); PWA receiving desks for judges |
| 3 | Exotel webhook $\le 5\text{ s}$ limit under load (`2 s` budget) | $0.5\text{ h}$ | Replay 20 signed Exotel callbacks via `httpx` against `/v1/webhooks/exotel`; assert p95 $\le 2000\text{ ms}$ and `inbox` dedupe | Play `"please hold"` prompt after $1.5\text{ s}$ and read committed state on next callback |
| 4 | LAN HTTP + QR camera on iPhone | $0.5\text{ h}$ | Connect iPhone to laptop hotspot; scan rotating QR pointing to `http://192.168.42.1:8080/join?jti=...` | Use Cloudflare Tunnel HTTPS domain or pre-installed local root CA |
| 5 | Pure-JS Ed25519 on iPhone Safari (`@noble/curves`) | $0.5\text{ h}$ | Open `/verifier` on iPhone Safari over plain LAN HTTP; verify 50-leaf Merkle inclusion proof + checkpoint signature | Labelled server-side verify endpoint `/v1/verify-proof` |
| 6 | Quint + Apalache at bounds $F=3, \text{MAXE}=4$ | $1.0\text{ h}$ | Run `quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000` and `quint verify spec/rhp1.qnt --invariant safety` | Run `python3.12 -m rhp.explorer` explicit-state BFS over `spec/transitions.yaml` |
| 7 | Mapbox Matrix API limits & token | $0.5\text{ h}$ | Execute 1 `mapbox/driving` Matrix call ($25$ coords, $60\text{ req/min}$) and 1 `driving-traffic` call ($10$ coords, $30\text{ req/min}$) `[V]` | Serve cached synthetic ETAs labelled `"ETA cached/synthetic"` |
| 8 | Android foreground location soak | $2.0\text{ h}$ | Run `FOREGROUND_SERVICE_TYPE_LOCATION` with screen off for $2\text{ h}$ on demo Android phone; inspect `telemetry` gaps and battery drain | Use PWA foreground `watchPosition` + manual `"Update Location"` button (`T1`) |
| 9 | DPDP Act / Rules commencement date `[CONFLICT]` | $1.0\text{ h}$ | Inspect primary Gazette notification (13 Nov 2025 vs 14 Nov 2025) | Cite the later date (`14 Nov 2025` / `14 May 2027`) conservatively |
| 10 | DPDP emergency processing clause (`s.7(f)` vs `s.7(d)`) | $0.5\text{ h}$ | Inspect primary Act text for medical emergency exemption numbering | Cite `"DPDP Act s.7 emergency processing provision"` without sub-letter on slides |
| 11 | Das et al. (2023) Maharashtra denominator `[CONFLICT]` | $0.5\text{ h}$ | Check primary paper tables ($25,253$ vs $28,020$) | Quote verified percentages only ($47\%, 37\%, 60\%$) |
| 12 | Chrony slew-only clock step test (`T-F11`) | $0.5\text{ h}$ | Inject $+3\text{ s}$ clock offset in test container; verify `heartbeat.ntp_offset_ms > 2000` triggers big-screen alarm and `I16` holds | Demo clock-step alarm via simulated `ntp_offset_ms` injection |

### 8.2 Step-by-Step Build & Verification Gates (Phase P & Phase E)

#### Phase P — Pre-Event Spec & Environment Bootstrap
| Step | Lane | Deliverable | Verification Command | Gate Criteria |
|---|---|---|---|---|
| **P1** | A | `spec/transitions.yaml` + conformance vectors `V-01..V-28` | `pytest tests/test_conformance.py --collect-only` | All 14 commands & 28 scenarios mapped (`[F5, F6, F13, F19]`) |
| **P2** | A | `db/schema.sql` + `db/verify_ddl.sql` (`ST-3`) | `docker compose up -d pg && ./scripts/run_self_audit.sh` | 24 tables, 12 triggers, `one_lease`, `one_active_grant`, role grants pass `ST-3` |
| **P3** | A | `spec/rhp1.qnt` formal verification + vacuity checks | `quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000` | `safety` holds; vacuity runs (`not (hs=="ACCEPTED")`, `DISPATCH`, `CLOSED`, `SOFT`) fail as required |
| **P4** | B | `spec/profiles.json` + `scripts/gen_keys.sh` (`ST-2`) | `python3.12 scripts/gen_keys.sh` | All 4 profiles signed; $T_{max} \le B$ (I13) and voice stagger verified |
| **P5** | B | `db/seed_synthetic.sql` (`REAL_DATA=0`) | `psql "$PG_APP_DSN" -c "SELECT count(*) FROM facility;"` | Synthetic Karnataka PHC/CHC/FRU/DH/MC facilities, rosters, and chains loaded |
| **P6** | B | §21 Pre-Event Verification Checklist | Execute table §8.1 above | All 12 items tested or fallback locked in STATE LEDGER |

#### Phase E — 24-Hour Hackathon Build Schedule & Tier Gates (§17, §24)
| Step | Hours | Lane A (Backend / Proof) | Lane B (Clients / Monitor / Reach) | Mandatory Gate Command & Measurable Pass Criteria (§24) |
|---|---|---|---|---|
| **E0** | `H00–H02` | `docker-compose.yml` up, `config.py` startup validator, `transitions.yaml` loader | PWA shell, rotating QR admission (`/join`), Turnstile + LAN-mode fallback | `docker compose ps` all healthy; `/healthz` returns `200` with active profile hash |
| **E1** | `H02–H06` | `apply_command()` steps 1–10: `CREATE`, `ACK`, `RESOURCE_CONFIRM`, `ACCEPT`, `DECLINE` | Receiving Desk UI, Clinician Card (`mgso4_status` banner), SSE per-event grant filter | `pytest tests/test_conformance.py -k "create or ack or accept or decline"` green; `GRANT_REVOKED` strips PHI |
| **E2** | `H06–H09` | 2-phase `poller.py`, visibility-timeout `relay.py`, `TIMEOUT`, unified notice ladder | Big screen UI; `monitor/monitor.py` in isolated Workspace B-Monitor | Monitor reports `0` violations; `DEMO_FAST` silence-to-dispatcher measured $\le 25\text{ s}$ |
| **E3** | `H09–H12` | RFC 8785 JCS hash chain, `witness/signer.py` (UID 1002, 5 s Merkle checkpoints), inclusion proofs | Browser pure-JS verifier (`verifier.ts` using `@noble/curves/ed25519` & `@noble/hashes/sha256`) | Tampering 1 event row in `psql` causes browser verifier to print exact `BROKEN referral=... seq=... kind=HASH` |
| **E4** | `H12–H14` | `test_race200.py` (`200`-way barrier), `test_mutations.py` (`M1`–`M6`), Toxiproxy 8-toxic suite | `BROKEN_BUILD=1` scratch DB switch + flashing red banner on Guarantee Arena | **GATE G0 (`T0` Pass):** `race200` yields $1\times 200$ and $199\times 409$, `deadlocks_delta == 0`, seq gap-free; `M1`–`M6` all trip checkers; `BROKEN_BUILD=1` turns monitor red in $\le 2\text{ s}$ |
| **E5** | `H14–H17` | `COUNTER`, `CONFIRM_COUNTER`, `ARRIVAL_REJECTED`, 6 arrival cases, `CLOSE` + 2-stage `CLOSURE` | Dispatcher Console (`DISPATCHER_ASSIGN`, proxy entry, replay scrubber), PWA GPS (`T1`) | **GATE G1 (`T1` Pass):** Proxy vs direct API entry yields identical state/seq in 20 paired runs; replay reproduces final state from log |
| **E6** | `H17–H20` | Idempotency 8-case matrix (`ST-4`), stale epoch/confirmation fencing (`I8`, `I15`), autonomous PIN lockout | Exotel outbound IVR (`Press 1` gate + `PIN#`), DLT SMS stub, 9-char Crockford mod-37 paper code | **GATE G2 (`T2` Pass):** 20/20 voice ACKs recorded only after commit; voicemail yields 0 ACKs in 5 trials; webhook p95 $\le 2\text{ s}$; 1,000/1,000 single-symbol paper-code errors rejected |
| **E7** | `H20–H22` | Fix any defects surfaced by Gem 2 / Gem 3; run full `./scripts/run_self_audit.sh` | Record MP4 fallback clips (`Clip A`–`Clip D`); rehearse 30-second live proof loop $\times 3$ | **GATE G3 (Rehearsal Pass):** 30-second proof loop completes inside $30\text{ s}$ three times in a row; all 4 MP4 clips verified |
| **E8** | `H22–H24` | **CODE FREEZE AT H22:** Config-only adjustments; standby backup laptop synced | Final stage check: feature phone charged, hotspot armed, witness page open on judge QR | **FREEZE GATE:** `git status` clean; tag `release-colossus3-locked` pushed |

---

## 9. Quick-Start Verification Commands (Copy-Paste Runbook)

Execute this exact sequence on a clean machine to bootstrap, verify, and test the entire ReferralHandshake RHP-1 environment:

```bash
# 1. Clone, install git guardrails, and generate cryptographic keys + signed profiles
cp .env.example .env
./scripts/install_git_hooks.sh
./scripts/gen_keys.sh

# 2. Run formal control-plane check (Quint simulation + vacuity checks)
quint run spec/rhp1.qnt --invariant safety --max-steps 25 --max-samples 20000
quint run spec/rhp1.qnt --invariant "not (hs == \"ACCEPTED\")" --max-steps 25 || echo "Vacuity check ACCEPTED passed (reachable)"
quint run spec/rhp1.qnt --invariant "not (hs == \"DISPATCH\")" --max-steps 25 || echo "Vacuity check DISPATCH passed (reachable)"
quint run spec/rhp1.qnt --invariant "not (hs == \"CLOSED\")"   --max-steps 25 || echo "Vacuity check CLOSED passed (reachable)"

# 3. Boot the 9-service Docker Compose stack and initialize Toxiproxy
docker compose up -d --build
./scripts/init_toxiproxy.sh

# 4. Run Self-Audits ST-1..ST-5, 200-way concurrency barrier, and M1..M6 mutation tests
./scripts/run_self_audit.sh
pytest -v tests/test_conformance.py tests/test_race200.py tests/test_mutations.py tests/test_toxiproxy.py
```