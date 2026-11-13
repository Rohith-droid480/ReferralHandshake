"""ReferralHandshake Protocol RHP-1 — Signed Timing Profiles & Invariant I13 Validator.

Specification Anchors:
- Architecture §6: Timing Model, Signed Profiles, T_max Derivation [F2, F3, I13]
- Architecture §18: Invariant I13 Matrix (T_max <= B)
- BUILD_PLAN §1.3: Signed Profiles & Boot Time Validation Gate
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from pydantic import BaseModel, ConfigDict, Field

# Pinned Ed25519 cold public key for profile and restore checkpoint signatures
DEFAULT_COLD_PUBKEY_HEX = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"

PAYLOAD_FIELDS = (
    "profile_id",
    "A",
    "D",
    "rungs",
    "S",
    "delta",
    "V",
    "voice",
    "F",
    "eps",
    "C",
    "confirm_ttl",
    "H",
    "dispatch_action",
    "closure",
    "B",
    "demo",
)


def canonical_jcs(obj: Any) -> bytes:
    """RFC 8785 JSON Canonicalization Scheme (JCS) serialization.

    Restricted to ASCII keys, integers, booleans, strings, and lists (zero floats).
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


class TimingProfile(BaseModel):
    """Pydantic model representing an RHP-1 timing profile with millisecond timing parameters."""

    model_config = ConfigDict(extra="ignore")

    profile_id: str
    A: int = Field(description="ACK window in milliseconds")
    D: int = Field(description="Decision window in milliseconds")
    rungs: List[int] = Field(description="Rung notification delays [0, A/4, 3A/4] in ms")
    S: int = Field(description="Number of concurrent duty role slots")
    delta: int = Field(description="Voice stagger interval in milliseconds")
    V: int = Field(description="Voice call budget in milliseconds")
    voice: bool = Field(description="Whether voice IVR ladder is enabled")
    F: int = Field(description="Maximum cascade facility hops")
    eps: int = Field(description="Per-hop poller and apply budget in milliseconds")
    C: int = Field(description="Counter-offer confirmation window in milliseconds")
    confirm_ttl: int = Field(description="Capability resource confirmation TTL in milliseconds")
    H: int = Field(description="Handover deadline in milliseconds")
    dispatch_action: int = Field(description="Dispatcher action deadline in milliseconds")
    closure: int = Field(description="Post-handover outcome closure deadline in milliseconds")
    B: int = Field(description="Worst-case escalation bound B in milliseconds")
    demo: bool = Field(description="True if demo profile (forbidden when REAL_DATA=1)")

    # Cryptographic integrity attributes
    profile_hash: str = Field(description="SHA-256 hex digest of JCS canonical payload")
    sig: str = Field(description="Ed25519 cold-key signature hex over JCS canonical payload")

    @property
    def t_max_ms(self) -> int:
        """Derives worst-case escalation bound T_max = F * (A + D + eps) in milliseconds."""
        return self.F * (self.A + self.D + self.eps)

    @property
    def t_max_s(self) -> int:
        """Derives worst-case escalation bound T_max in whole seconds."""
        return self.t_max_ms // 1000

    @property
    def bound_s(self) -> int:
        """Escalation bound B in whole seconds."""
        return self.B // 1000

    def payload_dict(self) -> Dict[str, Any]:
        """Extracts the exact canonical payload fields for hashing and signature verification."""
        return {k: getattr(self, k) for k in PAYLOAD_FIELDS}

    def canonical_bytes(self) -> bytes:
        """Returns the JCS canonical byte representation of this profile's payload."""
        return canonical_jcs(self.payload_dict())

    def compute_hash(self) -> str:
        """Computes the SHA-256 hex digest of the canonical payload."""
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def profile_hash_bytes(self) -> bytes:
        """Returns the 32-byte SHA-256 digest for binding into referral.profile_hash."""
        return bytes.fromhex(self.profile_hash)


def validate_profile(
    p: Union[TimingProfile, Dict[str, Any]],
    real_data: bool = False,
    cold_pubkey_hex: str = DEFAULT_COLD_PUBKEY_HEX,
) -> TimingProfile:
    """Validates an RHP-1 timing profile against formal invariants and cold-key cryptographic signature.

    Enforces:
    1. Invariant I13: T_max = F * (A + D + eps) <= B
    2. Voice Stagger Budget: If voice enabled, A/4 + (S - 1)*delta + V <= 3*A/4
    3. Ladder Rung Alignment: rungs == [0, A/4, 3*A/4]
    4. Safety Guard (F2): Demo profile forbidden when real_data is True
    5. Ed25519 Cold Signature: Signature over JCS canonical payload verifies with cold pubkey
    6. SHA-256 Digest Integrity: profile_hash matches SHA-256(JCS(payload))
    """
    if isinstance(p, dict):
        # Extract payload if wrapped
        payload = p.get("payload", p)
        profile_data = {**payload}
        profile_data["profile_hash"] = p.get("profile_hash") or p.get("profile_hash_hex") or ""
        profile_data["sig"] = p.get("sig") or p.get("cold_signature_hex") or ""
        profile = TimingProfile.model_validate(profile_data)
    else:
        profile = p

    # 1. Invariant I13: T_max <= B
    t_max = profile.t_max_ms
    assert (
        t_max <= profile.B
    ), f"Invariant I13 VIOLATION: T_max ({t_max} ms) > bound B ({profile.B} ms) for {profile.profile_id}"

    # 2. Voice Ladder Stagger Budget
    if profile.voice:
        voice_stagger = profile.A // 4 + (profile.S - 1) * profile.delta + profile.V
        max_ladder = (3 * profile.A) // 4
        assert voice_stagger <= max_ladder, (
            f"Voice stagger budget overflow: {voice_stagger} ms > {max_ladder} ms "
            f"for {profile.profile_id} (A={profile.A}, S={profile.S}, delta={profile.delta}, V={profile.V})"
        )

    # 3. Ladder Rung Alignment
    expected_rungs = [0, profile.A // 4, (3 * profile.A) // 4]
    assert profile.rungs == expected_rungs, (
        f"Rung timing misalignment: rungs {profile.rungs} != expected {expected_rungs} "
        f"for {profile.profile_id}"
    )

    # 4. Safety Guard (F2): Refuse boot if demo profile loaded with REAL_DATA=1
    if profile.demo and real_data:
        raise AssertionError(
            f"FATAL F2: Demo profile {profile.profile_id} strictly forbidden with REAL_DATA=1"
        )

    # 5. SHA-256 Digest Integrity
    can_bytes = profile.canonical_bytes()
    expected_hash = hashlib.sha256(can_bytes).hexdigest()
    assert (
        profile.profile_hash.lower() == expected_hash.lower()
    ), f"Profile hash mismatch for {profile.profile_id}: {profile.profile_hash} != {expected_hash}"

    # 6. Ed25519 Cold Signature Verification
    try:
        cold_pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(cold_pubkey_hex))
        sig_bytes = bytes.fromhex(profile.sig)
        cold_pub.verify(sig_bytes, can_bytes)
    except (InvalidSignature, ValueError) as err:
        raise AssertionError(
            f"Ed25519 cold-key signature verification failed for {profile.profile_id}: {err}"
        ) from err

    return profile


def load_profiles_json(spec_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Loads raw spec/profiles.json dictionary from disk."""
    if spec_path is None:
        # Search relative to repo root or current file
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "spec" / "profiles.json",
            Path("spec/profiles.json"),
            Path("/app/spec/profiles.json"),
        ]
        target = None
        for cand in candidates:
            if cand.exists():
                target = cand
                break
        if target is None:
            raise FileNotFoundError("Could not locate spec/profiles.json in search candidates")
    else:
        target = Path(spec_path)
        if not target.exists():
            raise FileNotFoundError(f"profiles.json not found at {target}")

    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def get_profile(
    profile_id: str,
    real_data: bool = False,
    spec_path: Optional[Union[str, Path]] = None,
    cold_pubkey_hex: str = DEFAULT_COLD_PUBKEY_HEX,
) -> TimingProfile:
    """Loads and validates a specific profile by ID from spec/profiles.json."""
    raw = load_profiles_json(spec_path)
    if profile_id not in raw:
        raise KeyError(f"Unknown profile_id: {profile_id}. Available: {list(raw.keys())}")
    return validate_profile(raw[profile_id], real_data=real_data, cold_pubkey_hex=cold_pubkey_hex)


def validate_all_profiles(
    real_data: bool = False,
    spec_path: Optional[Union[str, Path]] = None,
    cold_pubkey_hex: str = DEFAULT_COLD_PUBKEY_HEX,
) -> Dict[str, TimingProfile]:
    """Validates all profiles found in spec/profiles.json."""
    raw = load_profiles_json(spec_path)
    validated: Dict[str, TimingProfile] = {}
    for pid, entry in raw.items():
        validated[pid] = validate_profile(entry, real_data=real_data, cold_pubkey_hex=cold_pubkey_hex)
    return validated
