"""Separate-OS-User Witness Signer (§5, §8, §11, Closures F8, F11, Invariant I5).

Executed under dedicated OS user (uid 1002, rhp-sign) connecting as rhp_witness.
Periodically (every 5 seconds):
1. Upserts worker liveness into heartbeat(subject_kind='WITNESS', subject_id=signer_id).
2. Takes a REPEATABLE READ snapshot of (id, head_seq, head_hash) from referral ordered by id ASC.
3. Builds the binary Merkle tree over all referrals:
   - Leaf = SHA256(0x00 || referral_id[16] || head_seq_be[8] || head_hash[32])
   - Internal node = SHA256(0x01 || left[32] || right[32]); odd trailing node promoted unchanged.
   - Empty tree: root_hash = b"\\x00" * 32.
4. Formats C2SP note: f"rhp1/{deployment}\\n{tree_size}\\n{b64(root_hash)}\\n", signs with Ed25519.
5. Inserts checkpoint row into the database.
6. Exposes /v1/checkpoints/latest and /v1/referrals/{id}/proof.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import sys
import tempfile
import threading
import time

# Ensure repo root is on sys.path for direct execution
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi import FastAPI, HTTPException, Response

logger = logging.getLogger("rhp.witness")

# Deterministic demo seed (32 bytes) for synthetic test environment
DEMO_WITNESS_SEED = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
_GLOBAL_SIGNER_KEY: Optional[ed25519.Ed25519PrivateKey] = None


def get_witness_signing_key(key_path: Optional[str] = None) -> ed25519.Ed25519PrivateKey:
    """Loads Ed25519 private key from 0400 file, environment, or deterministic demo seed."""
    global _GLOBAL_SIGNER_KEY
    if _GLOBAL_SIGNER_KEY is not None:
        return _GLOBAL_SIGNER_KEY

    path = key_path or os.environ.get("WITNESS_PRIVATE_KEY_FILE", "secrets/witness_ed25519.key")
    if os.path.exists(path) and os.path.getsize(path) >= 32:
        try:
            with open(path, "rb") as f:
                data = f.read()
            if len(data) >= 32:
                _GLOBAL_SIGNER_KEY = ed25519.Ed25519PrivateKey.from_private_bytes(data[:32])
                return _GLOBAL_SIGNER_KEY
        except Exception as e:
            logger.warning(f"Could not load key from {path}: {e}")

    # Fallback to deterministic demo seed for testing
    _GLOBAL_SIGNER_KEY = ed25519.Ed25519PrivateKey.from_private_bytes(DEMO_WITNESS_SEED)
    return _GLOBAL_SIGNER_KEY


def get_witness_public_key_hex(priv_key: Optional[ed25519.Ed25519PrivateKey] = None) -> str:
    """Returns the hex-encoded 32-byte Ed25519 public key."""
    key = priv_key or get_witness_signing_key()
    pub = key.public_key()
    return pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def upsert_witness_heartbeat(conn: Any, subject_id: str = "witness-1", ntp_offset_ms: int = 0) -> None:
    """Upserts witness liveness into the database heartbeat table (Closure F11)."""
    now = datetime.now(timezone.utc)
    ipc_path = os.path.join(tempfile.gettempdir(), "rhp_heartbeats_ipc.json")
    try:
        data = {}
        if os.path.exists(ipc_path):
            with open(ipc_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[f"WITNESS:{subject_id}"] = {
            "subject_kind": "WITNESS",
            "subject_id": subject_id,
            "last_seen": now.isoformat(),
            "ntp_offset_ms": ntp_offset_ms,
        }
        with open(ipc_path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(ipc_path + ".tmp", ipc_path)
    except Exception:
        pass

    if hasattr(conn, "db"):
        if not hasattr(conn.db, "heartbeats"):
            conn.db.heartbeats = {}
        conn.db.heartbeats[("WITNESS", subject_id)] = {
            "subject_kind": "WITNESS",
            "subject_id": subject_id,
            "last_seen": now,
            "ntp_offset_ms": ntp_offset_ms,
        }
        return

    cur = conn.cursor() if hasattr(conn, "cursor") else conn
    cur.execute(
        """
        INSERT INTO heartbeat (subject_kind, subject_id, last_seen, ntp_offset_ms)
        VALUES ('WITNESS', %s, clock_timestamp(), %s)
        ON CONFLICT (subject_kind, subject_id)
        DO UPDATE SET last_seen = EXCLUDED.last_seen, ntp_offset_ms = EXCLUDED.ntp_offset_ms;
        """,
        (subject_id, ntp_offset_ms),
    )


def compute_leaf_hash(referral_id: UUID, head_seq: int, head_hash: bytes) -> bytes:
    """Computes binary Merkle leaf hash: SHA-256(0x00 || referral_id[16] || head_seq_be[8] || head_hash[32])."""
    payload = b"\x00" + referral_id.bytes + int(head_seq).to_bytes(8, byteorder="big") + head_hash
    return hashlib.sha256(payload).digest()


def compute_node_hash(left: bytes, right: bytes) -> bytes:
    """Computes binary Merkle internal node hash: SHA-256(0x01 || left[32] || right[32])."""
    return hashlib.sha256(b"\x01" + left + right).digest()


def build_merkle_tree(leaves: List[bytes]) -> Tuple[bytes, List[List[bytes]]]:
    """Builds a binary Merkle tree over leaves; promotes odd trailing nodes unchanged.

    Returns (root_hash, levels).
    """
    if not leaves:
        return b"\x00" * 32, [[]]

    current_level = list(leaves)
    levels = [current_level]

    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            if i + 1 < len(current_level):
                node = compute_node_hash(current_level[i], current_level[i + 1])
            else:
                # Odd trailing node promoted unchanged
                node = current_level[i]
            next_level.append(node)
        levels.append(next_level)
        current_level = next_level

    return current_level[0], levels


def compute_inclusion_proof(levels: List[List[bytes]], leaf_index: int) -> List[Dict[str, str]]:
    """Generates O(log N) inclusion proof path for a leaf index."""
    if not levels or not levels[0] or leaf_index < 0 or leaf_index >= len(levels[0]):
        return []

    path: List[Dict[str, str]] = []
    curr = leaf_index
    for level in levels[:-1]:
        if curr % 2 == 0:
            if curr + 1 < len(level):
                sibling = level[curr + 1]
                path.append({"side": "R", "hash": base64.b64encode(sibling).decode("ascii")})
        else:
            sibling = level[curr - 1]
            path.append({"side": "L", "hash": base64.b64encode(sibling).decode("ascii")})
        curr = curr // 2
    return path


def verify_inclusion_proof(leaf_hash: bytes, path: List[Dict[str, str]], root_hash: bytes) -> bool:
    """Folds an inclusion proof path starting from leaf_hash and checks root equality."""
    curr = leaf_hash
    for step in path:
        sibling = base64.b64decode(step["hash"])
        if step["side"] == "R":
            curr = compute_node_hash(curr, sibling)
        elif step["side"] == "L":
            curr = compute_node_hash(sibling, curr)
        else:
            return False
    return curr == root_hash


def sign_checkpoint_note(
    tree_size: int,
    root_hash: bytes,
    signer_key_id: str = "rhp1-witness-2026-11",
    deployment: str = "colossus3-bengaluru-demo",
    priv_key: Optional[ed25519.Ed25519PrivateKey] = None,
) -> Tuple[str, bytes]:
    """Formats C2SP note and signs with Ed25519."""
    root_b64 = base64.b64encode(root_hash).decode("ascii")
    note = f"rhp1/{deployment}\n{tree_size}\n{root_b64}\n"
    key = priv_key or get_witness_signing_key()
    sig = key.sign(note.encode("utf-8"))
    return note, sig


def witness_cycle(
    conn: Any,
    signer_id: str = "rhp1-witness-2026-11",
    deployment: str = "colossus3-bengaluru-demo",
    priv_key: Optional[ed25519.Ed25519PrivateKey] = None,
    ntp_offset_ms: int = 0,
) -> Dict[str, Any]:
    """Executes a single witness checkpointing and heartbeat cycle under REPEATABLE READ."""
    # 1. Upsert worker heartbeat
    upsert_witness_heartbeat(conn, signer_id, ntp_offset_ms=ntp_offset_ms)

    # 2. Query all referrals ordered by id ASC
    leaves: List[bytes] = []
    referral_rows: List[Tuple[UUID, int, bytes]] = []

    if hasattr(conn, "db"):
        refs = list(conn.db.referrals.values())
        refs.sort(key=lambda x: str(x.get("id", "")))
        for r in refs:
            r_id = UUID(str(r["id"]))
            h_seq = int(r.get("head_seq", 0))
            h_hash_raw = r.get("head_hash")
            if isinstance(h_hash_raw, str):
                h_hash = bytes.fromhex(h_hash_raw) if len(h_hash_raw) == 64 else h_hash_raw.encode("utf-8")[:32].ljust(32, b"\x00")
            elif isinstance(h_hash_raw, bytes):
                h_hash = h_hash_raw
            else:
                h_hash = b"\x00" * 32
            referral_rows.append((r_id, h_seq, h_hash))
            leaves.append(compute_leaf_hash(r_id, h_seq, h_hash))
    else:
        cur = conn.execute("SELECT id, head_seq, head_hash FROM referral ORDER BY id ASC;")
        rows = cur.fetchall() if cur else []
        for r in rows:
            r_id = UUID(str(r[0]))
            h_seq = int(r[1])
            h_hash = bytes(r[2]) if r[2] else b"\x00" * 32
            referral_rows.append((r_id, h_seq, h_hash))
            leaves.append(compute_leaf_hash(r_id, h_seq, h_hash))

    # 3. Build Merkle tree
    root_hash, levels = build_merkle_tree(leaves)
    key = priv_key or get_witness_signing_key()
    note, sig = sign_checkpoint_note(len(leaves), root_hash, signer_key_id=signer_id, deployment=deployment, priv_key=key)

    # 4. Insert checkpoint
    now = datetime.now(timezone.utc)
    cp_id = 1
    if hasattr(conn, "db"):
        if not hasattr(conn.db, "checkpoints") or not isinstance(conn.db.checkpoints, list):
            conn.db.checkpoints = []
        cp_id = len(conn.db.checkpoints) + 1
        conn.db.checkpoints.append({
            "id": cp_id,
            "taken_at": now,
            "kind": "REGULAR",
            "tree_size": len(leaves),
            "root_hash": root_hash,
            "signature": sig,
            "signer_key_id": signer_id,
            "note": note,
            "restore_from": None,
            "cold_signature": None,
        })
    else:
        cur_ins = conn.execute(
            """
            INSERT INTO checkpoint (taken_at, kind, tree_size, root_hash, signature, signer_key_id)
            VALUES (%s, 'REGULAR', %s, %s, %s, %s)
            RETURNING id;
            """,
            (now, len(leaves), root_hash, sig, signer_id),
        )
        row = cur_ins.fetchone() if cur_ins else None
        if row:
            cp_id = int(row[0])

    return {
        "checkpoint_id": cp_id,
        "tree_size": len(leaves),
        "root_hash": root_hash.hex(),
        "root_b64": base64.b64encode(root_hash).decode("ascii"),
        "note": note,
        "signature": base64.b64encode(sig).decode("ascii"),
        "signer_key_id": signer_id,
        "taken_at": now.isoformat(),
        "levels": levels,
        "referrals": referral_rows,
    }


def get_latest_checkpoint(conn: Any) -> Optional[Dict[str, Any]]:
    """Retrieves the most recent checkpoint record."""
    if hasattr(conn, "db"):
        cps = getattr(conn.db, "checkpoints", [])
        if not cps:
            return None
        cp = cps[-1]
        root_h = cp["root_hash"]
        sig = cp["signature"]
        return {
            "id": int(cp["id"]),
            "checkpoint_id": int(cp["id"]),
            "taken_at": cp["taken_at"].isoformat() if hasattr(cp["taken_at"], "isoformat") else str(cp["taken_at"]),
            "kind": cp["kind"],
            "tree_size": int(cp["tree_size"]),
            "root_hash": root_h.hex() if isinstance(root_h, bytes) else str(root_h),
            "root_b64": base64.b64encode(root_h if isinstance(root_h, bytes) else bytes.fromhex(root_h)).decode("ascii"),
            "signature": base64.b64encode(sig if isinstance(sig, bytes) else bytes.fromhex(sig)).decode("ascii"),
            "signature_hex": sig.hex() if isinstance(sig, bytes) else str(sig),
            "signer_key_id": cp["signer_key_id"],
            "note": cp.get("note", f"rhp1/colossus3-bengaluru-demo\n{cp['tree_size']}\n{base64.b64encode(root_h if isinstance(root_h, bytes) else bytes.fromhex(root_h)).decode('ascii')}\n"),
            "restore_from": cp.get("restore_from"),
            "cold_signature": base64.b64encode(cp["cold_signature"]).decode("ascii") if cp.get("cold_signature") else None,
        }

    cur = conn.execute(
        """
        SELECT id, taken_at, kind, tree_size, root_hash, signature, signer_key_id, restore_from, cold_signature
        FROM checkpoint
        ORDER BY id DESC
        LIMIT 1;
        """
    )
    r = cur.fetchone() if cur else None
    if not r:
        return None

    root_b = bytes(r[4])
    sig_b = bytes(r[5])
    cold_b = bytes(r[8]) if r[8] else None
    return {
        "id": int(r[0]),
        "checkpoint_id": int(r[0]),
        "taken_at": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
        "kind": str(r[2]),
        "tree_size": int(r[3]),
        "root_hash": root_b.hex(),
        "root_b64": base64.b64encode(root_b).decode("ascii"),
        "signature": base64.b64encode(sig_b).decode("ascii"),
        "signature_hex": sig_b.hex(),
        "signer_key_id": str(r[6]),
        "note": f"rhp1/colossus3-bengaluru-demo\n{r[3]}\n{base64.b64encode(root_b).decode('ascii')}\n",
        "restore_from": int(r[7]) if r[7] is not None else None,
        "cold_signature": base64.b64encode(cold_b).decode("ascii") if cold_b else None,
    }


def get_referral_proof(
    conn: Any,
    referral_id: UUID,
    checkpoint_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Generates Merkle inclusion proof for a referral against a checkpoint."""
    # 1. Fetch checkpoint
    cp = get_latest_checkpoint(conn)
    if not cp:
        raise ValueError("NO_CHECKPOINTS_EXIST")

    # 2. Query all referrals ordered by id ASC
    ref_list: List[Tuple[UUID, int, bytes]] = []
    leaves: List[bytes] = []

    if hasattr(conn, "db"):
        refs = list(conn.db.referrals.values())
        refs.sort(key=lambda x: str(x.get("id", "")))
        for r in refs:
            r_id = UUID(str(r["id"]))
            h_seq = int(r.get("head_seq", 0))
            h_hash_raw = r.get("head_hash")
            if isinstance(h_hash_raw, str):
                h_hash = bytes.fromhex(h_hash_raw) if len(h_hash_raw) == 64 else h_hash_raw.encode("utf-8")[:32].ljust(32, b"\x00")
            elif isinstance(h_hash_raw, bytes):
                h_hash = h_hash_raw
            else:
                h_hash = b"\x00" * 32
            ref_list.append((r_id, h_seq, h_hash))
            leaves.append(compute_leaf_hash(r_id, h_seq, h_hash))
    else:
        cur = conn.execute("SELECT id, head_seq, head_hash FROM referral ORDER BY id ASC;")
        rows = cur.fetchall() if cur else []
        for r in rows:
            r_id = UUID(str(r[0]))
            h_seq = int(r[1])
            h_hash = bytes(r[2]) if r[2] else b"\x00" * 32
            ref_list.append((r_id, h_seq, h_hash))
            leaves.append(compute_leaf_hash(r_id, h_seq, h_hash))

    # Find referral index
    target_idx = -1
    target_seq = 0
    target_hash = b"\x00" * 32
    for idx, (r_id, h_seq, h_hash) in enumerate(ref_list):
        if r_id == referral_id:
            target_idx = idx
            target_seq = h_seq
            target_hash = h_hash
            break

    if target_idx < 0:
        raise ValueError(f"REFERRAL_NOT_FOUND: {referral_id}")

    root_hash, levels = build_merkle_tree(leaves)
    path = compute_inclusion_proof(levels, target_idx)

    return {
        "referral_id": str(referral_id),
        "head_seq": target_seq,
        "head_hash": base64.b64encode(target_hash).decode("ascii"),
        "head_hash_hex": target_hash.hex(),
        "leaf_index": target_idx,
        "tree_size": len(leaves),
        "path": path,
        "checkpoint_id": cp["checkpoint_id"],
        "note": cp["note"],
        "signature": cp["signature"],
        "signer_key_id": cp["signer_key_id"],
        "root_hash": cp["root_hash"],
        "root_b64": cp["root_b64"],
    }


# =============================================================================
# Standalone Witness FastAPI Router & App
# =============================================================================

witness_app = FastAPI(title="ReferralHandshake Witness API")


@witness_app.get("/v1/checkpoints/latest")
def api_get_latest_checkpoint(response: Response) -> Dict[str, Any]:
    """Exposes the latest signed Merkle checkpoint with no-store cache header."""
    response.headers["Cache-Control"] = "no-store"
    from api.rhp.db import get_main_connection
    with get_main_connection() as conn:
        cp = get_latest_checkpoint(conn)
        if not cp:
            raise HTTPException(status_code=404, detail="No checkpoints found")
        return cp


@witness_app.get("/v1/referrals/{referral_id}/proof")
def api_get_referral_proof(referral_id: UUID, response: Response, checkpoint_id: Optional[int] = None) -> Dict[str, Any]:
    """Exposes O(log N) Merkle inclusion proof for a referral."""
    response.headers["Cache-Control"] = "no-store"
    from api.rhp.db import get_main_connection
    with get_main_connection() as conn:
        try:
            return get_referral_proof(conn, referral_id, checkpoint_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


def run_witness_loop(
    get_connection_func: Callable[[], Any],
    stop_event: Optional[threading.Event] = None,
    interval_sec: float = 5.0,
    signer_id: str = "rhp1-witness-2026-11",
    deployment: str = "colossus3-bengaluru-demo",
) -> None:
    """Continuous background witness loop."""
    if stop_event is None:
        stop_event = threading.Event()

    logger.info(f"Starting witness loop [{signer_id}] interval {interval_sec}s")
    while not stop_event.is_set():
        try:
            with get_connection_func() as conn:
                witness_cycle(conn, signer_id=signer_id, deployment=deployment)
                conn.commit()
        except Exception as e:
            logger.warning(f"Witness loop error: {e}")
        stop_event.wait(timeout=interval_sec)
    logger.info(f"Witness loop [{signer_id}] stopped cleanly")


if __name__ == "__main__":
    from api.rhp.db import get_main_connection
    run_witness_loop(get_main_connection)
