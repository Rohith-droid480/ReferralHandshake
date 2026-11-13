"""ReferralHandshake Protocol RHP-1 — Per-Referral AES-256-GCM Envelope Encryption.

Specification Anchors:
- Architecture §10: Cryptography, Key Wrapping & Envelope Encryption [Closure D9, P5]
- Invariant I5: Cryptographic SHA-256 Hash Chaining with Bound secret_hash
- BUILD_PLAN §10.1: Per-Referral AES-256-GCM Envelope Encryption, Monthly KEK Wrapping & event_secret Binding
- Test Anchor: T-P5 (test_envelope_crypto.py)

Structure:
1. Per-Referral DEK (Data Encryption Key): 256-bit random key (os.urandom(32)).
2. Monthly KEK (Key Encryption Key): AES Key Wrap (RFC 3394 / aes_key_wrap) wrapping DEK.
3. Clinical Payload: AES-256-GCM authenticated encryption with AAD = f"{referral_id}:{key_id}:{schema_ver}".
4. Event Secret: Sensitive event notes encrypted with AAD = f"{referral_id}:{seq}:{key_id}",
   producing secret_hash = SHA256(nonce || ciphertext) bound into the public event hash chain.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.keywrap import aes_key_unwrap, aes_key_wrap

# Default master monthly KEK salt for deterministic test derivation (256-bit)
DEFAULT_MASTER_KEK_SECRET = b"RHP1-MASTER-MONTHLY-KEK-202611-KEY"


def get_monthly_kek(kek_epoch: str = "2026-11", master_secret: bytes = DEFAULT_MASTER_KEK_SECRET) -> bytes:
    """Derives a 256-bit AES KEK for the given monthly epoch."""
    return hashlib.sha256(master_secret + kek_epoch.encode("utf-8")).digest()


class EnvelopeCryptoError(Exception):
    """Raised on crypto failure or authentication tag mismatch."""
    pass


class KeyVersion:
    """Represents a per-referral DEK wrapped by a monthly KEK."""

    def __init__(
        self,
        id: UUID,
        referral_id: UUID,
        kek_epoch: str,
        wrapped_dek: Optional[bytes],
        status: str = "ACTIVE",
        created_at: Optional[datetime] = None,
        shredded_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.referral_id = referral_id
        self.kek_epoch = kek_epoch
        self.wrapped_dek = wrapped_dek
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.shredded_at = shredded_at


def generate_referral_key(
    referral_id: Union[UUID, str],
    kek_epoch: str = "2026-11",
    kek: Optional[bytes] = None,
) -> Tuple[KeyVersion, bytes]:
    """Generates a fresh 256-bit DEK, wraps it with the monthly KEK, and returns the KeyVersion and raw DEK."""
    ref_uuid = UUID(str(referral_id))
    key_id = uuid4()
    raw_dek = os.urandom(32)

    if kek is None:
        kek = get_monthly_kek(kek_epoch)

    wrapped_dek = aes_key_wrap(kek, raw_dek)

    kv = KeyVersion(
        id=key_id,
        referral_id=ref_uuid,
        kek_epoch=kek_epoch,
        wrapped_dek=wrapped_dek,
        status="ACTIVE",
    )
    return kv, raw_dek


def unwrap_referral_dek(
    kv: KeyVersion,
    kek: Optional[bytes] = None,
) -> bytes:
    """Unwraps the DEK using the monthly KEK. Raises EnvelopeCryptoError if shredded or invalid."""
    if kv.status == "SHREDDED" or kv.wrapped_dek is None:
        raise EnvelopeCryptoError("Cannot unwrap DEK: Key is SHREDDED and DEK has been zeroed")

    if kek is None:
        kek = get_monthly_kek(kv.kek_epoch)

    try:
        raw_dek = aes_key_unwrap(kek, kv.wrapped_dek)
        return raw_dek
    except Exception as e:
        raise EnvelopeCryptoError(f"Failed to unwrap DEK: {e}") from e


def encrypt_clinical_payload(
    referral_id: Union[UUID, str],
    key_id: Union[UUID, str],
    dek: bytes,
    payload_dict: Dict[str, Any],
    schema_ver: int = 1,
) -> Tuple[bytes, bytes]:
    """Encrypts a clinical payload using AES-256-GCM.

    AAD = f"{referral_id}:{key_id}:{schema_ver}".encode()
    Returns (nonce_12b, ciphertext).
    """
    nonce = os.urandom(12)
    aad = f"{referral_id}:{key_id}:{schema_ver}".encode("utf-8")
    plaintext = json.dumps(payload_dict, sort_keys=True).encode("utf-8")

    aesgcm = AESGCM(dek)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
    return nonce, ciphertext


def decrypt_clinical_payload(
    referral_id: Union[UUID, str],
    key_id: Union[UUID, str],
    dek: bytes,
    nonce: bytes,
    ciphertext: bytes,
    schema_ver: int = 1,
) -> Dict[str, Any]:
    """Decrypts a clinical payload using AES-256-GCM.

    Rejects tampered AAD or ciphertext with InvalidTag / EnvelopeCryptoError.
    """
    aad = f"{referral_id}:{key_id}:{schema_ver}".encode("utf-8")
    aesgcm = AESGCM(dek)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        return json.loads(plaintext.decode("utf-8"))
    except InvalidTag as e:
        raise EnvelopeCryptoError("Authentication tag verification failed: Ciphertext or AAD tampered") from e


def encrypt_event_secret(
    referral_id: Union[UUID, str],
    seq: int,
    key_id: Union[UUID, str],
    dek: bytes,
    secret_text: str,
) -> Tuple[bytes, bytes, bytes]:
    """Encrypts sensitive event notes and computes secret_hash for the event hash chain.

    AAD = f"{referral_id}:{seq}:{key_id}".encode()
    secret_hash = SHA256(nonce || ciphertext)
    Returns (nonce_12b, ciphertext, secret_hash_32b).
    """
    nonce = os.urandom(12)
    aad = f"{referral_id}:{seq}:{key_id}".encode("utf-8")
    plaintext = secret_text.encode("utf-8")

    aesgcm = AESGCM(dek)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)

    secret_hash = hashlib.sha256(nonce + ciphertext).digest()
    return nonce, ciphertext, secret_hash


def decrypt_event_secret(
    referral_id: Union[UUID, str],
    seq: int,
    key_id: Union[UUID, str],
    dek: bytes,
    nonce: bytes,
    ciphertext: bytes,
) -> str:
    """Decrypts sensitive event notes."""
    aad = f"{referral_id}:{seq}:{key_id}".encode("utf-8")
    aesgcm = AESGCM(dek)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        return plaintext.decode("utf-8")
    except InvalidTag as e:
        raise EnvelopeCryptoError("Event secret authentication tag verification failed") from e

