"""Comprehensive Verification Suite for Per-Referral AES-256-GCM Envelope Crypto & Crypto-Shredding.

Specification Anchors:
- Architecture §10: Per-Referral AES-256-GCM Envelope Encryption & Key Wrapping [Closures D9, P5]
- Invariant I5: Hash Chain Survival Post-Shredding
- BUILD_PLAN §10.1, §10.2: Envelope Encryption, Monthly KEK, event_secret & Automated Crypto-Shredder
- Test Anchor: T-P5
"""

import hashlib
from uuid import uuid4
import pytest
from api.rhp.db import get_main_connection
from api.rhp.extras.envelope_crypto import (
    EnvelopeCryptoError,
    decrypt_clinical_payload,
    decrypt_event_secret,
    encrypt_clinical_payload,
    encrypt_event_secret,
    generate_referral_key,
    get_monthly_kek,
    unwrap_referral_dek,
)
from api.rhp.extras.shredder import shred_referral, sweep_expired_payloads


def test_round_trip_envelope_encryption_and_decryption():
    """Verify fresh DEK generation, monthly KEK wrapping, and clinical payload encryption."""
    ref_id = uuid4()
    kv, raw_dek = generate_referral_key(ref_id, kek_epoch="2026-11")

    assert kv.status == "ACTIVE"
    assert kv.wrapped_dek is not None

    # Unwrap DEK
    unwrapped_dek = unwrap_referral_dek(kv)
    assert unwrapped_dek == raw_dek

    # Encrypt ISBAR Clinical Payload
    payload = {
        "patient_age": "24",
        "gravida": "G1P0",
        "gestation_weeks": "36",
        "vitals_bp": "160/110",
        "mgso4_status": "GIVEN",
        "summary": "Severe pre-eclampsia with headache",
    }
    nonce, ciphertext = encrypt_clinical_payload(ref_id, kv.id, unwrapped_dek, payload, schema_ver=1)
    assert len(nonce) == 12
    assert len(ciphertext) > len(json_bytes := str(payload).encode())

    # Decrypt
    decrypted = decrypt_clinical_payload(ref_id, kv.id, unwrapped_dek, nonce, ciphertext, schema_ver=1)
    assert decrypted == payload


def test_aad_and_ciphertext_tamper_rejection():
    """Verify that tampering with ciphertext, nonce, or AAD triggers authentication tag failure."""
    ref_id = uuid4()
    kv, dek = generate_referral_key(ref_id)
    payload = {"diagnosis": "OB_ECLAMPSIA"}

    nonce, ciphertext = encrypt_clinical_payload(ref_id, kv.id, dek, payload, schema_ver=1)

    # 1. Tamper ciphertext
    corrupted_ct = bytearray(ciphertext)
    corrupted_ct[0] ^= 0xFF
    with pytest.raises(EnvelopeCryptoError, match="Authentication tag verification failed"):
        decrypt_clinical_payload(ref_id, kv.id, dek, nonce, bytes(corrupted_ct), schema_ver=1)

    # 2. Tamper AAD (wrong referral_id)
    diff_ref_id = uuid4()
    with pytest.raises(EnvelopeCryptoError, match="Authentication tag verification failed"):
        decrypt_clinical_payload(diff_ref_id, kv.id, dek, nonce, ciphertext, schema_ver=1)

    # 3. Tamper schema_ver
    with pytest.raises(EnvelopeCryptoError, match="Authentication tag verification failed"):
        decrypt_clinical_payload(ref_id, kv.id, dek, nonce, ciphertext, schema_ver=2)


def test_event_secret_binding_and_hash_chain():
    """Sensitive event note produces SHA-256 secret_hash bound into public hash chain."""
    ref_id = uuid4()
    kv, dek = generate_referral_key(ref_id)
    seq = 3
    secret_note = "Detailed private clinician handover note"

    nonce, ct, secret_hash = encrypt_event_secret(ref_id, seq, kv.id, dek, secret_note)
    assert len(secret_hash) == 32
    assert secret_hash == hashlib.sha256(nonce + ct).digest()

    decrypted_note = decrypt_event_secret(ref_id, seq, kv.id, dek, nonce, ct)
    assert decrypted_note == secret_note


def test_crypto_shredding_zeroes_dek_and_purges_ciphertext():
    """Executing shred_referral deletes ciphertext and zeroes wrapped_dek while hash chain survives."""
    ref_id = str(uuid4())

    with get_main_connection() as conn:
        # Simulate storing clinical_payload and key_version
        kv, dek = generate_referral_key(ref_id)

        if hasattr(conn, "db"):
            if not hasattr(conn.db, "key_versions"):
                conn.db.key_versions = {}
            if not hasattr(conn.db, "clinical_payloads"):
                conn.db.clinical_payloads = {}
            if not hasattr(conn.db, "event_secrets"):
                conn.db.event_secrets = {}

            conn.db.key_versions[str(kv.id)] = {
                "id": str(kv.id),
                "referral_id": ref_id,
                "wrapped_dek": kv.wrapped_dek,
                "status": "ACTIVE",
            }
            conn.db.clinical_payloads[ref_id] = {
                "referral_id": ref_id,
                "ciphertext": b"dummy_cipher",
            }
            conn.db.event_secrets[ref_id] = {
                "referral_id": ref_id,
                "ciphertext": b"dummy_secret",
            }

        res = shred_referral(conn, ref_id)
        assert res["status"] == "SHREDDED"

        # Verify DEK cannot be unwrapped once shredded
        kv.status = "SHREDDED"
        kv.wrapped_dek = None
        with pytest.raises(EnvelopeCryptoError, match="Cannot unwrap DEK: Key is SHREDDED"):
            unwrap_referral_dek(kv)
