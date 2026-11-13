"""Test Suite for RFC 8785 Canonical JSON (JCS) & SHA-256 Event Chain Parity (ST-4, A-2).

Specification Anchors:
- Architecture §5: Canonical JSON & Event Chain Hasher [I5]
- Architecture §11: JCS Parity & Bit-for-Bit Determinism [F8, I5]
- BUILD_PLAN §1.4: Strict Float Rejection & 10 Cross-Language Parity Vectors
"""

import json
import sys
from pathlib import Path
import pytest

# Ensure api directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "api") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "api"))

from rhp.crypto import (
    GENESIS_PREV_HASH_BYTES,
    GENESIS_PREV_HASH_HEX,
    compute_event_hash,
    compute_event_hash_hex,
    jcs,
)


@pytest.fixture(scope="module")
def parity_vectors():
    vec_path = REPO_ROOT / "spec" / "parity_vectors.json"
    assert vec_path.exists(), f"Missing spec/parity_vectors.json: {vec_path}"
    with open(vec_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "vectors" in data
    assert len(data["vectors"]) == 10
    return data["vectors"]


def test_jcs_10_parity_vectors(parity_vectors):
    """Verifies that api.rhp.crypto.jcs() matches all 10 vectors in spec/parity_vectors.json bit-for-bit."""
    for vec in parity_vectors:
        seq = vec["seq"]
        core = vec["core"]
        expected_jcs = vec["canonical_jcs"]

        actual_jcs_bytes = jcs(core)
        assert (
            actual_jcs_bytes.decode("utf-8") == expected_jcs
        ), f"JCS mismatch on vector seq={seq}:\nActual:   {actual_jcs_bytes.decode('utf-8')}\nExpected: {expected_jcs}"


def test_sha256_hash_chain_10_parity_vectors(parity_vectors):
    """Verifies that compute_event_hash() chaining matches expected SHA-256 digests across all 10 vectors."""
    running_prev_hash = GENESIS_PREV_HASH_HEX

    for vec in parity_vectors:
        seq = vec["seq"]
        core = vec["core"]
        expected_hash = vec["expected_hash"]
        vector_prev_hash = vec["prev_hash"]

        assert (
            running_prev_hash == vector_prev_hash
        ), f"Chain break before vector seq={seq}: running {running_prev_hash} != vector {vector_prev_hash}"

        computed_hash_hex = compute_event_hash_hex(vector_prev_hash, core)
        assert (
            computed_hash_hex == expected_hash
        ), f"SHA-256 digest mismatch on vector seq={seq}:\nComputed: {computed_hash_hex}\nExpected: {expected_hash}"

        running_prev_hash = computed_hash_hex


def test_attack_a2_float_injection_rejected():
    """Attack Test A-2: Float injection into JCS payload MUST raise TypeError or ValueError."""
    # Test spec: Profile dict with float value for A
    bad_profile = {
        "profile_id": "DEMO_FAST",
        "A": 3000.0,  # Float injected
        "D": 4000,
        "F": 3,
    }
    with pytest.raises((TypeError, ValueError)):
        jcs(bad_profile)


def test_float_rejection_nested_dict():
    """Confirms floats nested deeply inside dictionaries are rejected."""
    bad_payload = {"a": {"b": {"c": 1.234}}}
    with pytest.raises(TypeError, match="Float values strictly forbidden"):
        jcs(bad_payload)


def test_float_rejection_nested_list():
    """Confirms floats nested inside lists or tuples are rejected."""
    bad_payload = {"items": [1, 2, [3, 4.0]]}
    with pytest.raises(TypeError, match="Float values strictly forbidden"):
        jcs(bad_payload)


def test_float_rejection_standalone():
    """Confirms standalone float values are rejected."""
    with pytest.raises(TypeError):
        jcs(0.0)
    with pytest.raises(TypeError):
        jcs(100.5)


def test_jcs_key_sorting_and_whitespace():
    """Confirms object keys are sorted lexicographically with zero extraneous whitespace."""
    data = {"z": 1, "a": 2, "m": 3, "b": 4}
    assert jcs(data) == b'{"a":2,"b":4,"m":3,"z":1}'


def test_jcs_null_and_boolean_formatting():
    """Confirms null, true, and false serialize to exact canonical JSON literals."""
    data = {"active": True, "archived": False, "revoked_at": None}
    assert jcs(data) == b'{"active":true,"archived":false,"revoked_at":null}'


def test_non_string_dict_key_rejected():
    """Confirms dictionary keys that are not strings are rejected."""
    data = {1: "integer_key"}
    with pytest.raises(TypeError, match="Dictionary keys must be strings"):
        jcs(data)


def test_genesis_hash_computation_bytes_and_hex():
    """Confirms compute_event_hash accepts both 32-byte raw bytes and 64-char hex strings."""
    core = {"seq": 1, "type": "TEST"}
    h1 = compute_event_hash(GENESIS_PREV_HASH_BYTES, core)
    h2 = compute_event_hash(GENESIS_PREV_HASH_HEX, core)
    assert h1 == h2
    assert len(h1) == 32
