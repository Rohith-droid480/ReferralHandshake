"""ReferralHandshake Protocol RHP-1 — Automated Crypto-Shredding Worker.

Specification Anchors:
- Architecture §10: Automated Crypto-Shredding & PHI Lifecycle [Closures D9, P5]
- Invariant I5: Cryptographic Hash Chaining Survival Post-Shredding
- BUILD_PLAN §10.2: Automated Crypto-Shredding Worker (DEK Zeroing & Ciphertext Purge)
- Test Anchor: T-P5 (test_envelope_crypto.py)

Key Requirements:
1. Purge clinical ciphertexts:
   - DELETE FROM clinical_payload WHERE referral_id = %s;
   - DELETE FROM event_secret WHERE referral_id = %s;
2. Zero out DEK in key_version:
   - UPDATE key_version SET wrapped_dek = NULL, status = 'SHREDDED', shredded_at = clock_timestamp() WHERE referral_id = %s;
3. Survival of Hash Chain (Invariant I5):
   - event.secret_hash remains SHA256(nonce || ciphertext) in the event log.
   - Merkle root checkpoints and C2SP notes remain 100% verifiable without holding plaintext.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

logger = logging.getLogger("rhp.extras.shredder")


def shred_referral(conn: Any, referral_id: Union[UUID, str]) -> Dict[str, Any]:
    """Permanently crypto-shreds all PHI and clinical ciphertexts for a referral.

    Zeroes out the wrapped DEK in key_version and purges rows from
    clinical_payload and event_secret.
    """
    ref_id = str(referral_id)
    now = datetime.now(timezone.utc)

    # In-memory mock DB support
    if hasattr(conn, "db"):
        db = conn.db
        if not hasattr(db, "clinical_payloads"):
            db.clinical_payloads = {}
        if not hasattr(db, "event_secrets"):
            db.event_secrets = {}
        if not hasattr(db, "key_versions"):
            db.key_versions = {}

        deleted_payload = db.clinical_payloads.pop(ref_id, None) is not None

        # Delete from event_secrets where referral_id matches
        to_del = [k for k, v in db.event_secrets.items() if v.get("referral_id") == ref_id or k[0] == ref_id]
        deleted_secrets_count = len(to_del)
        for k in to_del:
            del db.event_secrets[k]

        # Update key_version
        shredded_keys = 0
        for kv in db.key_versions.values():
            if kv.get("referral_id") == ref_id:
                kv["wrapped_dek"] = None
                kv["status"] = "SHREDDED"
                kv["shredded_at"] = now
                shredded_keys += 1

        return {
            "referral_id": ref_id,
            "status": "SHREDDED",
            "shredded_at": now.isoformat(),
            "payload_deleted": deleted_payload,
            "secrets_deleted": deleted_secrets_count,
            "keys_zeroed": shredded_keys,
        }

    # PostgreSQL transactional execution
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM clinical_payload WHERE referral_id = %s;", (ref_id,))
        cur.execute("DELETE FROM event_secret WHERE referral_id = %s;", (ref_id,))
        cur.execute(
            """
            UPDATE key_version
               SET wrapped_dek = NULL,
                   status = 'SHREDDED',
                   shredded_at = clock_timestamp()
             WHERE referral_id = %s;
            """,
            (ref_id,),
        )
        if hasattr(conn, "commit") and not getattr(conn, "autocommit", False):
            conn.commit()

        return {
            "referral_id": ref_id,
            "status": "SHREDDED",
            "shredded_at": now.isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to crypto-shred referral {ref_id}: {e}")
        if hasattr(conn, "rollback") and not getattr(conn, "autocommit", False):
            conn.rollback()
        raise


def sweep_expired_payloads(conn: Any) -> List[str]:
    """Sweeps for and shreds all clinical payloads where expires_at <= now()."""
    now = datetime.now(timezone.utc)
    shredded_ids: List[str] = []

    if hasattr(conn, "db"):
        db = conn.db
        if hasattr(db, "clinical_payloads"):
            for ref_id, payload in list(db.clinical_payloads.items()):
                exp = payload.get("expires_at")
                if exp and exp <= now:
                    shred_referral(conn, ref_id)
                    shredded_ids.append(ref_id)
        return shredded_ids

    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT referral_id FROM clinical_payload
             WHERE expires_at <= clock_timestamp();
            """
        )
        rows = cur.fetchall()
        for row in rows:
            ref_id = str(row[0])
            shred_referral(conn, ref_id)
            shredded_ids.append(ref_id)
        return shredded_ids
    except Exception as e:
        logger.error(f"Failed to sweep expired payloads: {e}")
        return []

