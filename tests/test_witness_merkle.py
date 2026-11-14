"""ReferralHandshake Protocol RHP-1 — Witness Signer & Merkle Proofs Test Suite.

Specification Anchors:
- Architecture §11: Integrity, Merkle Proofs & Independent Witnesses [F8]
- Invariant I5: Hash Chaining & Append-Only Log
- BUILD_PLAN §6.1: Witness Signer 5s Binary Merkle Tree
- Gates: T-F8, T-S2, T-I5
"""

from __future__ import annotations

import base64
from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi.testclient import TestClient

from witness.signer import (
    build_merkle_tree,
    compute_inclusion_proof,
    compute_leaf_hash,
    compute_node_hash,
    get_latest_checkpoint,
    get_referral_proof,
    sign_checkpoint_note,
    verify_inclusion_proof,
    witness_app,
    DEMO_WITNESS_SEED,
)


def test_merkle_leaf_hash_specification():
    """Leaf = SHA256(0x00 || referral_id(16B) || head_seq(8B BE) || head_hash(32B))."""
    ref_id = UUID("e1111111-0000-0000-0000-000000000001")
    seq = 42
    h_hash = b"\xaa" * 32

    leaf = compute_leaf_hash(ref_id, seq, h_hash)
    assert len(leaf) == 32
    assert isinstance(leaf, bytes)

    # Different seq produces different leaf
    leaf2 = compute_leaf_hash(ref_id, seq + 1, h_hash)
    assert leaf != leaf2

    # Different hash produces different leaf
    leaf3 = compute_leaf_hash(ref_id, seq, b"\xbb" * 32)
    assert leaf != leaf3

    # Different referral_id produces different leaf
    leaf4 = compute_leaf_hash(uuid4(), seq, h_hash)
    assert leaf != leaf4


def test_merkle_tree_construction_and_odd_node_promotion():
    """Tests binary Merkle tree folding across sizes, verifying odd node promotion."""
    # Size 0
    root0, levels0 = build_merkle_tree([])
    assert root0 == b"\x00" * 32

    # Size 1
    leaf1 = compute_leaf_hash(uuid4(), 1, b"\x01" * 32)
    root1, levels1 = build_merkle_tree([leaf1])
    assert len(levels1) == 1
    assert root1 == leaf1

    # Sizes 2, 3, 5, 7, 16, 25
    for n in (2, 3, 5, 7, 16, 25):
        leaves = [compute_leaf_hash(uuid4(), i, bytes([i % 256]) * 32) for i in range(n)]
        root, levels = build_merkle_tree(leaves)
        assert len(root) == 32

        # Every leaf must have an inclusion proof folding exactly to the root
        for i in range(n):
            proof = compute_inclusion_proof(levels, i)
            assert verify_inclusion_proof(leaves[i], proof, root) is True, f"Fold mismatch for size {n} leaf {i}"


def test_inclusion_proof_rejection_on_altered_leaf():
    """Tampering with leaf inputs or path causes proof verification to fail."""
    ref_id = uuid4()
    leaves = [compute_leaf_hash(uuid4(), i, bytes([i]) * 32) for i in range(5)]
    root, levels = build_merkle_tree(leaves)

    proof = compute_inclusion_proof(levels, 2)
    assert verify_inclusion_proof(leaves[2], proof, root) is True

    # Altered leaf hash fails
    tampered_leaf = compute_leaf_hash(ref_id, 999, bytes([2]) * 32)
    assert verify_inclusion_proof(tampered_leaf, proof, root) is False

    # Corrupted proof step fails
    corrupted_proof = [dict(step) for step in proof]
    corrupted_proof[0]["hash"] = base64.b64encode(b"\xff" * 32).decode("ascii")
    assert verify_inclusion_proof(leaves[2], corrupted_proof, root) is False


def test_signed_checkpoint_note_format_and_verification():
    """Verifies C2SP signed-note style format and Ed25519 signature."""
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(DEMO_WITNESS_SEED)
    pub_key = priv_key.public_key()

    root = b"\x42" * 32
    tree_size = 17
    deployment = "colossus3-bengaluru-demo"

    note_text, sig = sign_checkpoint_note(
        tree_size=tree_size,
        root_hash=root,
        signer_key_id="rhp1-witness-2026-11",
        deployment=deployment,
        priv_key=priv_key,
    )
    lines = note_text.splitlines()

    assert lines[0] == f"rhp1/{deployment}"
    assert lines[1] == "17"
    assert lines[2] == base64.b64encode(root).decode("ascii")

    # Verify signature directly with cryptography
    pub_key.verify(sig, note_text.encode("utf-8"))

    # Corrupted note fails verification
    with pytest.raises(Exception):
        pub_key.verify(sig, (note_text + "tamper").encode("utf-8"))


def test_witness_endpoints():
    """Tests /v1/checkpoints/latest and /v1/referrals/{id}/proof FastAPI routes."""
    from api.rhp.db import get_main_connection
    from witness.signer import witness_cycle
    import json

    ref_id = uuid4()
    with get_main_connection() as conn:
        # Insert a sample referral into DB to ensure referrals exist
        if hasattr(conn, "db"):
            conn.db.referrals[str(ref_id)] = {
                "id": str(ref_id),
                "head_seq": 1,
                "head_hash": b"\xaa" * 32,
            }
        else:
            conn.execute(
                """
                INSERT INTO referral (id, paper_code, head_seq, head_hash)
                VALUES (%s, 'DEMO-001', 1, %s)
                ON CONFLICT (id) DO NOTHING;
                """,
                (str(ref_id), b"\xaa" * 32),
            )
        # Execute witness cycle to take checkpoint
        witness_cycle(conn)

    client = TestClient(witness_app)

    # 1. Latest checkpoint
    r1 = client.get("/v1/checkpoints/latest")
    assert r1.status_code == 200
    cp = r1.json()
    assert "id" in cp
    assert "root_hash" in cp
    assert "signature" in cp
    assert "tree_size" in cp
    assert cp["kind"] in ("REGULAR", "RESTORE")
    assert cp["tree_size"] >= 1

    # 2. Inclusion proof
    r2 = client.get(f"/v1/referrals/{ref_id}/proof")
    assert r2.status_code == 200
    proof_data = r2.json()
    assert proof_data["referral_id"] == str(ref_id)
    assert "head_seq" in proof_data
    assert "path" in proof_data
    assert "checkpoint_id" in proof_data
