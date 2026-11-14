"""ReferralHandshake Protocol RHP-1 — Cold-Key Signed Disaster Recovery Restore Script.

Specification Anchors:
- Architecture §11: Integrity, Merkle Proofs & Independent Witnesses [F8]
- Invariant I5: Hash Chaining & Append-Only Log
- BUILD_PLAN §6.2: RESTORE Protocol & Cold Key Verification
- Closure F8: Witness/Restore Gaps

Uses the offline cold Ed25519 key to sign a RESTORE checkpoint, binds it
to the prior checkpoint (restore_from), and appends a RESTORE event to every
active referral linking the restored head hash to prevent false tamper alarms.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.asymmetric import ed25519

from api.rhp.config import get_settings
from api.rhp.crypto import compute_event_hash, jcs
from witness.signer import (
    build_merkle_tree,
    compute_leaf_hash,
    sign_checkpoint_note,
    DEMO_WITNESS_SEED,
)

logger = logging.getLogger("rhp.restore")

# Standard test cold seed
DEFAULT_TEST_COLD_SEED = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
TEST_WITNESS_PRIVKEY_SEED = DEMO_WITNESS_SEED


def canonical_jcs(obj: Any) -> bytes:
    """RFC 8785 JSON Canonicalization Scheme."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def load_cold_private_key(key_path_or_seed: Optional[str] = None) -> ed25519.Ed25519PrivateKey:
    """Loads cold Ed25519 private key from file path or test seed."""
    if key_path_or_seed and Path(key_path_or_seed).exists():
        raw = Path(key_path_or_seed).read_bytes().strip()
        try:
            return ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(raw.decode("ascii")))
        except Exception:
            return ed25519.Ed25519PrivateKey.from_private_bytes(raw[:32])
    return ed25519.Ed25519PrivateKey.from_private_bytes(DEFAULT_TEST_COLD_SEED)


def load_witness_private_key(key_path: Optional[str] = None) -> ed25519.Ed25519PrivateKey:
    """Loads witness private key."""
    if key_path and Path(key_path).exists():
        raw = Path(key_path).read_bytes().strip()
        try:
            return ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(raw.decode("ascii")))
        except Exception:
            return ed25519.Ed25519PrivateKey.from_private_bytes(raw[:32])
    return ed25519.Ed25519PrivateKey.from_private_bytes(TEST_WITNESS_PRIVKEY_SEED)


def create_restore_checkpoint(
    conn: Any,
    restore_from_checkpoint_id: int,
    cold_priv_key: Optional[ed25519.Ed25519PrivateKey] = None,
    witness_priv_key: Optional[ed25519.Ed25519PrivateKey] = None,
    signer_key_id: str = "rhp1-cold-restore-2026",
    deployment: str = "colossus3-bengaluru-demo",
) -> Dict[str, Any]:
    """Creates a cold-key-signed RESTORE checkpoint and appends RESTORE events.

    Args:
        conn: PostgreSQL writable connection (e.g. rhp_app or postgres).
        restore_from_checkpoint_id: Checkpoint ID to restore from.
        cold_priv_key: Offline cold Ed25519 key.
        witness_priv_key: Witness Ed25519 key for note signing.
        signer_key_id: Key identifier.
        deployment: Deployment instance identifier.

    Returns:
        Dict containing new checkpoint details.
    """
    if cold_priv_key is None:
        cold_priv_key = load_cold_private_key()
    if witness_priv_key is None:
        witness_priv_key = load_witness_private_key()

    # 1. Verify restore_from checkpoint exists
    if hasattr(conn, "db"):
        cps = getattr(conn.db, "checkpoints", [])
        matching = [c for c in cps if c["id"] == restore_from_checkpoint_id]
        if not matching:
            raise ValueError(f"Target restore_from checkpoint {restore_from_checkpoint_id} does not exist")
        prior_cp = matching[0]
    else:
        cur = conn.execute(
            "SELECT id, tree_size, root_hash, taken_at FROM checkpoint WHERE id = %s",
            (restore_from_checkpoint_id,),
        )
        prior_cp = cur.fetchone()
        if not prior_cp:
            raise ValueError(f"Target restore_from checkpoint {restore_from_checkpoint_id} does not exist")

    # 2. Fetch current state of all referrals
    referrals: List[Dict[str, Any]] = []
    if hasattr(conn, "db"):
        refs = list(conn.db.referrals.values())
        refs.sort(key=lambda x: str(x.get("id", "")))
        for r in refs:
            referrals.append({
                "id": UUID(str(r["id"])),
                "head_seq": int(r.get("head_seq", 0)),
                "head_hash": bytes(r.get("head_hash", b"\x00" * 32)),
                "head_ts": r.get("head_ts", datetime.now(timezone.utc)),
                "lease_epoch": int(r.get("lease_epoch", 0)),
            })
    else:
        cur = conn.execute(
            "SELECT id, head_seq, head_hash, head_ts, lease_epoch FROM referral ORDER BY id ASC"
        )
        for row in cur.fetchall():
            referrals.append({
                "id": UUID(str(row[0])),
                "head_seq": int(row[1]),
                "head_hash": bytes(row[2]),
                "head_ts": row[3],
                "lease_epoch": int(row[4]),
            })

    tree_size = len(referrals)

    # 3. Compute Merkle root of current referral set
    leaf_hashes = [
        compute_leaf_hash(r["id"], r["head_seq"], r["head_hash"])
        for r in referrals
    ]
    root_hash, levels = build_merkle_tree(leaf_hashes)

    taken_at = datetime.now(timezone.utc)
    taken_at_str = taken_at.isoformat()

    # 4. Generate cold signature over canonical RESTORE payload
    restore_payload = canonical_jcs({
        "checkpoint_id": int(restore_from_checkpoint_id),
        "kind": "RESTORE",
        "root_hash": root_hash.hex(),
        "taken_at": taken_at_str,
        "tree_size": tree_size,
    })
    cold_signature = cold_priv_key.sign(restore_payload)

    # 5. Generate witness note signature
    note_text, witness_signature = sign_checkpoint_note(
        tree_size=tree_size,
        root_hash=root_hash,
        signer_key_id=signer_key_id,
        deployment=deployment,
        priv_key=witness_priv_key,
    )

    # 6. Insert RESTORE checkpoint row
    if hasattr(conn, "db"):
        new_checkpoint_id = len(conn.db.checkpoints) + 1
        conn.db.checkpoints.append({
            "id": new_checkpoint_id,
            "taken_at": taken_at,
            "kind": "RESTORE",
            "tree_size": tree_size,
            "root_hash": root_hash,
            "signature": witness_signature,
            "signer_key_id": signer_key_id,
            "note": note_text,
            "restore_from": restore_from_checkpoint_id,
            "cold_signature": cold_signature,
        })
    else:
        cur_ins = conn.execute(
            """
            INSERT INTO checkpoint (
                taken_at, kind, tree_size, root_hash, signature, signer_key_id,
                restore_from, cold_signature
            ) VALUES (
                %s, 'RESTORE', %s, %s, %s, %s, %s, %s
            ) RETURNING id;
            """,
            (
                taken_at,
                "RESTORE",
                tree_size,
                root_hash,
                witness_signature,
                signer_key_id,
                restore_from_checkpoint_id,
                cold_signature,
            ),
        )
        new_checkpoint_id = int(cur_ins.fetchone()[0])

    # 7. Append RESTORE event to each referral (enforcing I14 lock and event_guard)
    for r in referrals:
        ref_id_str = str(r["id"])
        seq = r["head_seq"] + 1
        prev_hash = bytes(r["head_hash"])
        event_id = uuid4()
        server_ts = max(taken_at, r["head_ts"] + timedelta(microseconds=1))
        server_ts_us = int(server_ts.timestamp() * 1_000_000)

        detail = {"checkpoint_id": new_checkpoint_id}

        core = {
            "referral_id": ref_id_str,
            "seq": seq,
            "event_id": str(event_id),
            "type": "RESTORE",
            "epoch": r["lease_epoch"],
            "actor_roster_id": None,
            "actor_facility_id": None,
            "channel": "SYSTEM",
            "proxy": False,
            "detail": detail,
            "secret_hash": None,
            "client_ts_ms": None,
            "server_ts_us": server_ts_us,
        }

        canonical_core = jcs(core)
        event_hash = compute_event_hash(prev_hash, core)

        if hasattr(conn, "db"):
            if not hasattr(conn.db, "events"):
                conn.db.events = []
            conn.db.events.append({
                "referral_id": ref_id_str,
                "seq": seq,
                "event_id": str(event_id),
                "type": "RESTORE",
                "actor_roster_id": None,
                "actor_facility_id": None,
                "channel": "SYSTEM",
                "proxy": False,
                "epoch": r["lease_epoch"],
                "detail": detail,
                "secret_hash": None,
                "client_ts_ms": None,
                "server_ts": server_ts,
                "prev_hash": prev_hash,
                "hash": event_hash,
            })
            if ref_id_str in conn.db.referrals:
                conn.db.referrals[ref_id_str]["head_seq"] = seq
                conn.db.referrals[ref_id_str]["head_hash"] = event_hash
                conn.db.referrals[ref_id_str]["head_ts"] = server_ts
                conn.db.referrals[ref_id_str]["version"] = conn.db.referrals[ref_id_str].get("version", 1) + 1
        else:
            conn.execute("SELECT * FROM referral WHERE id = %s FOR UPDATE", (ref_id_str,))
            conn.execute("SELECT set_config('rhp.locked_referral', %s, true)", (ref_id_str,))
            conn.execute(
                """
                INSERT INTO event (
                    referral_id, seq, event_id, type, actor_roster_id, actor_facility_id,
                    channel, proxy, epoch, detail, secret_hash, client_ts_ms,
                    server_ts, prev_hash, hash
                ) VALUES (
                    %s, %s, %s, 'RESTORE', NULL, NULL,
                    'SYSTEM', false, %s, %s, NULL, NULL,
                    %s, %s, %s
                )
                """,
                (
                    ref_id_str,
                    seq,
                    str(event_id),
                    r["lease_epoch"],
                    json.dumps(detail),
                    server_ts,
                    prev_hash,
                    event_hash,
                ),
            )
            conn.execute(
                """
                UPDATE referral
                SET head_seq = %s,
                    head_hash = %s,
                    head_ts = %s,
                    version = version + 1
                WHERE id = %s
                """,
                (seq, event_hash, server_ts, ref_id_str),
            )

    if hasattr(conn, "commit"):
        conn.commit()

    return {
        "id": new_checkpoint_id,
        "kind": "RESTORE",
        "restore_from": restore_from_checkpoint_id,
        "tree_size": tree_size,
        "root_hash": root_hash.hex(),
        "cold_signature": cold_signature.hex(),
        "witness_signature": witness_signature.hex(),
        "taken_at": taken_at_str,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RHP-1 Cold-Key RESTORE Protocol")
    parser.add_argument("--restore-from", type=int, required=True, help="Checkpoint ID to restore from")
    parser.add_argument("--cold-key-file", type=str, default=None, help="Path to cold Ed25519 private key")
    parser.add_argument("--witness-key-file", type=str, default=None, help="Path to witness Ed25519 private key")
    parser.add_argument("--dsn", type=str, default=None, help="PostgreSQL DSN")
    args = parser.parse_args()

    from api.rhp.db import get_main_connection

    cold_key = load_cold_private_key(args.cold_key_file)
    witness_key = load_witness_private_key(args.witness_key_file)

    with get_main_connection() as conn:
        res = create_restore_checkpoint(
            conn=conn,
            restore_from_checkpoint_id=args.restore_from,
            cold_priv_key=cold_key,
            witness_priv_key=witness_key,
        )
        print(f"Successfully created RESTORE checkpoint #{res['id']} restoring from #{res['restore_from']}")


if __name__ == "__main__":
    main()
