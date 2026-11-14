"""ReferralHandshake Protocol RHP-1 — Tamper Evidence vs Cold-Key Restore Test Suite.

Specification Anchors:
- Architecture §11: Integrity, Merkle Proofs & Independent Witnesses [F8]
- Invariant I5: Hash Chaining & Append-Only Log
- BUILD_PLAN §6.2: RESTORE Protocol & Rollback Detection
- Gates: T-F8, T-S2, T-I5
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from api.rhp.crypto import compute_event_hash, jcs
from api.rhp.db import get_main_connection
from scripts.cold_sign_restore import (
    create_restore_checkpoint,
    canonical_jcs,
    DEFAULT_TEST_COLD_SEED,
)
from scripts.witness_pull_sync import RollbackError, WitnessSyncClient
from witness.signer import (
    build_merkle_tree,
    compute_inclusion_proof,
    compute_leaf_hash,
    sign_checkpoint_note,
    witness_cycle,
    DEMO_WITNESS_SEED,
)


def _build_test_event_chain(referral_id: UUID, n_events: int = 3):
    """Helper to build a valid hash-chained list of events in memory."""
    events = []
    prev_hash = b"\x00" * 32
    base_time = datetime(2026, 11, 14, 2, 0, 0, tzinfo=timezone.utc)

    for seq in range(1, n_events + 1):
        event_id = uuid4()
        server_ts = base_time + timedelta(seconds=seq)
        core = {
            "referral_id": str(referral_id),
            "seq": seq,
            "event_id": str(event_id),
            "type": "REFERRAL_CREATED" if seq == 1 else "OFFER_ACKED",
            "epoch": 0,
            "actor_roster_id": None,
            "actor_facility_id": None,
            "channel": "SYSTEM",
            "proxy": False,
            "detail": {"step": seq},
            "secret_hash": None,
            "client_ts_ms": None,
            "server_ts_us": int(server_ts.timestamp() * 1_000_000),
        }
        h = compute_event_hash(prev_hash, core)
        events.append({
            "referral_id": str(referral_id),
            "seq": seq,
            "event_id": str(event_id),
            "type": core["type"],
            "epoch": 0,
            "detail": core["detail"],
            "prev_hash": prev_hash.hex(),
            "hash": h.hex(),
            "server_ts_us": core["server_ts_us"],
            "channel": "SYSTEM",
            "proxy": False,
            "actor_roster_id": None,
            "actor_facility_id": None,
            "secret_hash": None,
            "client_ts_ms": None,
        })
        prev_hash = h
    return events


def test_tamper_detection_corrupted_hash():
    """Mutating event detail or hash breaks verification immediately."""
    ref_id = uuid4()
    events = _build_test_event_chain(ref_id, n_events=3)

    # Corrupt event 2 detail
    events[1]["detail"]["tampered"] = True

    # Re-evaluate hash chain verification in Python
    prev = b"\x00" * 32
    broken_detected = False
    broken_message = ""

    for ev in events:
        expected_prev = bytes.fromhex(ev["prev_hash"])
        if expected_prev != prev:
            broken_detected = True
            broken_message = f"BROKEN referral={ref_id} seq={ev['seq']} kind=PREV expected={prev.hex()} got={ev['prev_hash']}"
            break

        core = {
            "referral_id": ev["referral_id"],
            "seq": ev["seq"],
            "event_id": ev["event_id"],
            "type": ev["type"],
            "epoch": ev["epoch"],
            "actor_roster_id": ev["actor_roster_id"],
            "actor_facility_id": ev["actor_facility_id"],
            "channel": ev["channel"],
            "proxy": ev["proxy"],
            "detail": ev["detail"],
            "secret_hash": ev["secret_hash"],
            "client_ts_ms": ev["client_ts_ms"],
            "server_ts_us": ev["server_ts_us"],
        }
        computed = compute_event_hash(prev, core)
        if computed.hex() != ev["hash"]:
            broken_detected = True
            broken_message = f"BROKEN referral={ref_id} seq={ev['seq']} kind=HASH expected={computed.hex()} got={ev['hash']}"
            break
        prev = computed

    assert broken_detected is True
    assert "kind=HASH" in broken_message
    assert f"referral={ref_id}" in broken_message
    assert "seq=2" in broken_message


def test_witness_pull_sync_detects_checkpoint_regression():
    """Off-box witness detects split-view or restore if checkpoint ID regresses."""
    witness_priv = ed25519.Ed25519PrivateKey.from_private_bytes(DEMO_WITNESS_SEED)
    witness_pub_hex = witness_priv.public_key().public_bytes_raw().hex()

    client = WitnessSyncClient(witness_pubkey_hex=witness_pub_hex)

    # Checkpoint 5
    root5 = b"\x05" * 32
    note5, sig5 = sign_checkpoint_note(1, root5, priv_key=witness_priv)
    cp5 = {
        "id": 5,
        "tree_size": 1,
        "root_hash": root5.hex(),
        "signature": base64.b64encode(sig5).decode("ascii"),
        "note_text": note5,
        "kind": "REGULAR",
    }
    client.process_checkpoint(cp5)
    assert client.last_checkpoint_id == 5

    # Checkpoint 4 (regressed ID!)
    root4 = b"\x04" * 32
    note4, sig4 = sign_checkpoint_note(1, root4, priv_key=witness_priv)
    cp4 = {
        "id": 4,
        "tree_size": 1,
        "root_hash": root4.hex(),
        "signature": base64.b64encode(sig4).decode("ascii"),
        "note_text": note4,
        "kind": "REGULAR",
    }

    with pytest.raises(RollbackError) as exc_info:
        client.process_checkpoint(cp4)
    assert "SPLIT_VIEW_OR_ROLLBACK_DETECTED" in str(exc_info.value)
    assert "regressed from 5 to 4" in str(exc_info.value)


def test_witness_pull_sync_detects_referral_seq_regression_without_restore():
    """Unannounced truncation of referral history raises SPLIT_VIEW_OR_ROLLBACK_DETECTED."""
    witness_priv = ed25519.Ed25519PrivateKey.from_private_bytes(DEMO_WITNESS_SEED)
    witness_pub_hex = witness_priv.public_key().public_bytes_raw().hex()

    client = WitnessSyncClient(witness_pubkey_hex=witness_pub_hex)
    ref_id = str(uuid4())

    # Checkpoint 10 with ref at seq=7
    root10 = b"\x10" * 32
    note10, sig10 = sign_checkpoint_note(1, root10, priv_key=witness_priv)
    cp10 = {
        "id": 10,
        "tree_size": 1,
        "root_hash": root10.hex(),
        "signature": base64.b64encode(sig10).decode("ascii"),
        "note_text": note10,
        "kind": "REGULAR",
    }
    client.process_checkpoint(cp10, referral_heads_sample={ref_id: (7, "hash7")})

    # Checkpoint 11 with ref at seq=3 (regressed without RESTORE!)
    root11 = b"\x11" * 32
    note11, sig11 = sign_checkpoint_note(1, root11, priv_key=witness_priv)
    cp11 = {
        "id": 11,
        "tree_size": 1,
        "root_hash": root11.hex(),
        "signature": base64.b64encode(sig11).decode("ascii"),
        "note_text": note11,
        "kind": "REGULAR",
    }

    with pytest.raises(RollbackError) as exc_info:
        client.process_checkpoint(cp11, referral_heads_sample={ref_id: (3, "hash3")})
    assert "SPLIT_VIEW_OR_ROLLBACK_DETECTED" in str(exc_info.value)
    assert "head_seq regressed from 7 to 3" in str(exc_info.value)


def test_cold_key_signed_restore_protocol():
    """Valid cold-key RESTORE checkpoint allows legitimate disaster recovery restore."""
    witness_priv = ed25519.Ed25519PrivateKey.from_private_bytes(DEMO_WITNESS_SEED)
    witness_pub_hex = witness_priv.public_key().public_bytes_raw().hex()

    cold_priv = ed25519.Ed25519PrivateKey.from_private_bytes(DEFAULT_TEST_COLD_SEED)
    cold_pub_hex = cold_priv.public_key().public_bytes_raw().hex()

    ref_id = uuid4()
    with get_main_connection() as conn:
        # Create base checkpoint #1
        if hasattr(conn, "db"):
            conn.db.referrals[str(ref_id)] = {
                "id": str(ref_id),
                "head_seq": 1,
                "head_hash": b"\x11" * 32,
                "head_ts": datetime.now(timezone.utc),
                "lease_epoch": 0,
            }
        else:
            conn.execute(
                """
                INSERT INTO referral (id, paper_code, head_seq, head_hash, head_ts, lease_epoch)
                VALUES (%s, 'DEMO-001', 1, %s, now(), 0)
                ON CONFLICT (id) DO UPDATE SET head_seq = 1, head_hash = EXCLUDED.head_hash;
                """,
                (str(ref_id), b"\x11" * 32),
            )
        cp1 = witness_cycle(conn)
        base_cp_id = cp1["checkpoint_id"]

        # Run cold sign restore from base checkpoint
        restore_res = create_restore_checkpoint(
            conn=conn,
            restore_from_checkpoint_id=base_cp_id,
            cold_priv_key=cold_priv,
            witness_priv_key=witness_priv,
        )

        assert restore_res["kind"] == "RESTORE"
        assert restore_res["restore_from"] == base_cp_id
        assert restore_res["cold_signature"] is not None

        # Verify that an off-box witness accepts this RESTORE checkpoint even with regressed seq
        client = WitnessSyncClient(witness_pubkey_hex=witness_pub_hex, cold_pubkey_hex=cold_pub_hex)
        # Seed witness state with high seq 10
        client.last_checkpoint_id = base_cp_id
        client.referral_heads[str(ref_id)] = (10, "high_hash")

        restore_cp_payload = {
            "id": restore_res["id"],
            "tree_size": restore_res["tree_size"],
            "root_hash": restore_res["root_hash"],
            "signature": base64.b64encode(bytes.fromhex(restore_res["witness_signature"])).decode("ascii"),
            "kind": "RESTORE",
            "restore_from": base_cp_id,
            "cold_signature": base64.b64encode(bytes.fromhex(restore_res["cold_signature"])).decode("ascii"),
            "taken_at": restore_res["taken_at"],
        }

        # Restored referral has seq 2 (regressed from 10, but covered by RESTORE!)
        ok = client.process_checkpoint(
            restore_cp_payload,
            referral_heads_sample={str(ref_id): (2, "restored_hash")}
        )
        assert ok is True
        assert client.last_checkpoint_id == restore_res["id"]
        assert client.referral_heads[str(ref_id)][0] == 2
