"""ReferralHandshake Protocol RHP-1 — Cryptographic Core & Canonical JSON (RFC 8785).

Specification Anchors:
- Architecture §5: Canonical JSON & SHA-256 Event Chain Hasher [I5]
- Architecture §11: JCS Parity, Microsecond Timestamp & Checkpoints [F8, I5]
- BUILD_PLAN §1.4: Strict Float Rejection & Cross-Language Parity
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, Tuple, Union

GENESIS_PREV_HASH_BYTES = b"\x00" * 32
GENESIS_PREV_HASH_HEX = "00" * 32

EVENT_CORE_FIELDS = (
    "referral_id",
    "seq",
    "event_id",
    "type",
    "epoch",
    "actor_roster_id",
    "facility_id",
    "channel",
    "proxy",
    "detail",
    "secret_hash",
    "client_ts_ms",
    "server_ts_us",
)


def _assert_no_floats(obj: Any, path: str = "root") -> None:
    """Recursively validates that no floating-point numbers exist in obj.

    Raises:
        TypeError: If any float is encountered (violates RHP-1 JCS strictness).
    """
    # Note: in Python, bool is a subclass of int, but float is distinct.
    if isinstance(obj, float):
        raise TypeError(
            f"Float values strictly forbidden in RHP-1 RFC 8785 JCS canonical JSON at {path}: {obj}"
        )
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(f"Dictionary keys must be strings in JCS at {path}: {k}")
            _assert_no_floats(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for idx, item in enumerate(obj):
            _assert_no_floats(item, f"{path}[{idx}]")


def jcs(obj: Any) -> bytes:
    """Serializes a Python data structure to RFC 8785 Canonical JSON (JCS).

    Guarantees:
    - Strict rejection of float numbers (raises TypeError).
    - Deterministic lexicographical sorting of object keys.
    - Zero redundant whitespace (separators=(',', ':')).
    - Representation of null as 'null', boolean as 'true'/'false'.
    - Integers represented in base-10 without scientific notation.
    - Output encoded as UTF-8 bytes.

    Args:
        obj: The object to canonicalize.

    Returns:
        bytes: Canonical UTF-8 JSON bytes.
    """
    _assert_no_floats(obj)
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def compute_event_hash(
    prev_hash: Union[bytes, str],
    event_core: Dict[str, Any],
) -> bytes:
    """Computes the SHA-256 hash chain step: SHA256(prev_hash || JCS(event_core)).

    Args:
        prev_hash: 32-byte raw bytes or 64-character hex string.
        event_core: Dictionary containing canonical event core fields.

    Returns:
        bytes: 32-byte binary SHA-256 hash.
    """
    if isinstance(prev_hash, str):
        prev_bytes = bytes.fromhex(prev_hash)
    elif isinstance(prev_hash, (bytes, bytearray)):
        prev_bytes = bytes(prev_hash)
    else:
        raise TypeError(f"prev_hash must be bytes or hex string, got {type(prev_hash)}")

    if len(prev_bytes) != 32:
        raise ValueError(f"prev_hash must be exactly 32 bytes, got {len(prev_bytes)} bytes")

    core_bytes = jcs(event_core)
    return hashlib.sha256(prev_bytes + core_bytes).digest()


def compute_event_hash_hex(
    prev_hash: Union[bytes, str],
    event_core: Dict[str, Any],
) -> str:
    """Computes the SHA-256 hash chain step returning a 64-character lowercase hex string."""
    return compute_event_hash(prev_hash, event_core).hex()
