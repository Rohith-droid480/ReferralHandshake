"""Test Suite for Protocol RHP-1 Timing Model & Signed Profiles (ST-2, T-F2, T-F3, I13).

Specification Anchors:
- Architecture §6: Timing Model, Signed Profiles, T_max Derivation [F2, F3, I13]
- Architecture §18: Invariant I13 Enforcement & Voice Ladder Bounds
- BUILD_PLAN §1.3: Verification Gate (ST-2 / T-F2 / T-F3)
"""

import sys
from pathlib import Path
import pytest

# Ensure api directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "api") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "api"))

from rhp.profiles import (
    DEFAULT_COLD_PUBKEY_HEX,
    TimingProfile,
    get_profile,
    load_profiles_json,
    validate_all_profiles,
    validate_profile,
)


def test_st2_all_profiles_exist_and_validate():
    """ST-2: Asserts all 4 canonical profiles are present in spec/profiles.json and validate cleanly."""
    profiles = validate_all_profiles(real_data=False)
    assert set(profiles.keys()) == {
        "PILOT_OB_CRITICAL",
        "PILOT_STANDARD",
        "DEMO_FAST",
        "DEMO_VOICE",
    }


def test_t_f3_pilot_ob_critical_math():
    """T-F3 / I13: PILOT_OB_CRITICAL T_max = 3*(60+180+3) = 729s <= 900s, voice stagger 45s <= 45s."""
    p = get_profile("PILOT_OB_CRITICAL", real_data=False)
    assert p.A == 60000
    assert p.D == 180000
    assert p.F == 3
    assert p.eps == 3000
    assert p.B == 900000
    assert p.rungs == [0, 15000, 45000]
    assert p.S == 3
    assert p.delta == 5000
    assert p.V == 20000
    assert p.voice is True
    assert p.demo is False

    # Exact T_max arithmetic
    assert p.t_max_ms == 729000
    assert p.t_max_s == 729
    assert p.bound_s == 900
    assert p.t_max_ms <= p.B

    # Voice stagger math: A/4 + (S - 1)*delta + V <= 3*A/4
    voice_stagger = p.A // 4 + (p.S - 1) * p.delta + p.V
    max_ladder = (3 * p.A) // 4
    assert voice_stagger == 45000
    assert max_ladder == 45000
    assert voice_stagger <= max_ladder


def test_t_f3_pilot_standard_math():
    """T-F3 / I13: PILOT_STANDARD T_max = 3*(120+300+3) = 1269s <= 1500s."""
    p = get_profile("PILOT_STANDARD", real_data=False)
    assert p.A == 120000
    assert p.D == 300000
    assert p.F == 3
    assert p.eps == 3000
    assert p.B == 1500000
    assert p.rungs == [0, 30000, 90000]
    assert p.S == 3
    assert p.delta == 10000
    assert p.V == 20000
    assert p.voice is True
    assert p.demo is False

    assert p.t_max_ms == 1269000
    assert p.t_max_s == 1269
    assert p.bound_s == 1500
    assert p.t_max_ms <= p.B

    voice_stagger = p.A // 4 + (p.S - 1) * p.delta + p.V
    max_ladder = (3 * p.A) // 4
    assert voice_stagger == 70000
    assert max_ladder == 90000
    assert voice_stagger <= max_ladder


def test_t_f3_demo_fast_math():
    """T-F3 / I13: DEMO_FAST T_max = 3*(3+4+1) = 24s <= 25s, voice off."""
    p = get_profile("DEMO_FAST", real_data=False)
    assert p.A == 3000
    assert p.D == 4000
    assert p.F == 3
    assert p.eps == 1000
    assert p.B == 25000
    assert p.rungs == [0, 750, 2250]
    assert p.voice is False
    assert p.demo is True

    assert p.t_max_ms == 24000
    assert p.t_max_s == 24
    assert p.bound_s == 25
    assert p.t_max_ms <= p.B


def test_t_f3_demo_voice_math():
    """T-F3 / I13: DEMO_VOICE T_max = 2*(45+20+1) = 132s <= 150s."""
    p = get_profile("DEMO_VOICE", real_data=False)
    assert p.A == 45000
    assert p.D == 20000
    assert p.F == 2
    assert p.eps == 1000
    assert p.B == 150000
    assert p.rungs == [0, 11250, 33750]
    assert p.S == 1
    assert p.delta == 0
    assert p.V == 20000
    assert p.voice is True
    assert p.demo is True

    assert p.t_max_ms == 132000
    assert p.t_max_s == 132
    assert p.bound_s == 150
    assert p.t_max_ms <= p.B

    voice_stagger = p.A // 4 + (p.S - 1) * p.delta + p.V
    max_ladder = (3 * p.A) // 4
    assert voice_stagger == 31250
    assert max_ladder == 33750
    assert voice_stagger <= max_ladder


def test_t_f2_real_data_guard_behavior():
    """T-F2: validate_profile raises on demo profiles when real_data=True; passes for pilot profiles."""
    raw = load_profiles_json()

    # Demo profiles must raise
    with pytest.raises(AssertionError, match="FATAL F2: Demo profile DEMO_FAST strictly forbidden"):
        validate_profile(raw["DEMO_FAST"], real_data=True)

    with pytest.raises(AssertionError, match="FATAL F2: Demo profile DEMO_VOICE strictly forbidden"):
        validate_profile(raw["DEMO_VOICE"], real_data=True)

    # Pilot profiles must pass
    p1 = validate_profile(raw["PILOT_OB_CRITICAL"], real_data=True)
    assert p1.profile_id == "PILOT_OB_CRITICAL"

    p2 = validate_profile(raw["PILOT_STANDARD"], real_data=True)
    assert p2.profile_id == "PILOT_STANDARD"


def test_cold_key_signature_tamper_payload_byte():
    """Tampering with 1 byte of payload (e.g. A changed from 60000 to 60001) aborts startup."""
    raw = load_profiles_json()
    tampered = dict(raw["PILOT_OB_CRITICAL"])
    tampered["payload"] = dict(tampered["payload"])
    tampered["payload"]["A"] = 60001  # 1-byte integer tamper

    with pytest.raises(AssertionError, match="Profile hash mismatch"):
        validate_profile(tampered, real_data=False)


def test_cold_key_signature_tamper_signature_byte():
    """Tampering with 1 byte of the cold signature fails cryptographic verification."""
    raw = load_profiles_json()
    tampered = dict(raw["PILOT_OB_CRITICAL"])
    # Flip the first hex character of the signature
    sig_chars = list(tampered["sig"])
    sig_chars[0] = "0" if sig_chars[0] != "0" else "1"
    tampered["sig"] = "".join(sig_chars)

    with pytest.raises(AssertionError, match="Ed25519 cold-key signature verification failed"):
        validate_profile(tampered, real_data=False)


def test_cold_key_signature_tamper_hash_byte():
    """Tampering with 1 byte of the profile_hash field causes mismatch assertion."""
    raw = load_profiles_json()
    tampered = dict(raw["PILOT_OB_CRITICAL"])
    hash_chars = list(tampered["profile_hash"])
    hash_chars[0] = "0" if hash_chars[0] != "0" else "1"
    tampered["profile_hash"] = "".join(hash_chars)

    with pytest.raises(AssertionError, match="Profile hash mismatch"):
        validate_profile(tampered, real_data=False)


def test_i13_violation_rejection():
    """Constructed profile where T_max > B is rejected by validate_profile."""
    raw = load_profiles_json()
    entry = dict(raw["DEMO_FAST"])
    payload = dict(entry["payload"])
    # Lower bound B below T_max (24000)
    payload["B"] = 20000
    entry["payload"] = payload
    entry["profile_hash"] = entry["profile_hash_hex"]

    with pytest.raises(AssertionError, match="Invariant I13 VIOLATION: T_max"):
        validate_profile(entry, real_data=False)


def test_voice_stagger_budget_overflow_rejection():
    """Profile with voice stagger exceeding 3A/4 is rejected by validate_profile."""
    raw = load_profiles_json()
    entry = dict(raw["PILOT_OB_CRITICAL"])
    payload = dict(entry["payload"])
    # Increase call budget V beyond ladder
    payload["V"] = 50000
    entry["payload"] = payload

    with pytest.raises(AssertionError, match="Voice stagger budget overflow"):
        validate_profile(entry, real_data=False)


def test_rung_timing_misalignment_rejection():
    """Profile with misaligned rungs is rejected by validate_profile."""
    raw = load_profiles_json()
    entry = dict(raw["PILOT_OB_CRITICAL"])
    payload = dict(entry["payload"])
    payload["rungs"] = [0, 10000, 45000]  # Misaligned rung 2
    entry["payload"] = payload

    with pytest.raises(AssertionError, match="Rung timing misalignment"):
        validate_profile(entry, real_data=False)
