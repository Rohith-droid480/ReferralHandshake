"""ReferralHandshake Protocol RHP-1 — Off-Box Witness Pull Sync Client.

Specification Anchors:
- Architecture §11: Integrity, Merkle Proofs & Independent Witnesses [F8]
- BUILD_PLAN §6.2: Witness Pull Sync & Rollback Detection
- Invariant I5: Hash Chaining & Append-Only Log

Runs on a second witness client (or judge phone / local auditor), polling
/v1/checkpoints/latest, verifying the Ed25519 witness signature, appending
to an append-only local log, and raising SPLIT_VIEW_OR_ROLLBACK_DETECTED if
a newly fetched checkpoint has a lower id or if any referral's head_seq
regresses without a valid cold-key-signed RESTORE checkpoint.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from api.rhp.config import get_settings

logger = logging.getLogger("rhp.witness_sync")


class RollbackError(RuntimeError):
    """Raised when an off-box witness detects history truncation or split-view."""
    pass


def canonical_jcs(obj: Any) -> bytes:
    """RFC 8785 JSON Canonicalization Scheme."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class WitnessSyncClient:
    """Independent witness pull client that verifies checkpoints and detects rollback."""

    def __init__(
        self,
        witness_pubkey_hex: Optional[str] = None,
        cold_pubkey_hex: Optional[str] = None,
        log_file: Optional[Path] = None,
    ):
        settings = get_settings()
        self.witness_pubkey_hex = witness_pubkey_hex or settings.WITNESS_PUBKEY_HEX
        self.cold_pubkey_hex = cold_pubkey_hex or settings.COLD_PUBKEY_HEX
        self.witness_pubkey = ed25519.Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(self.witness_pubkey_hex)
        )
        self.cold_pubkey = ed25519.Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(self.cold_pubkey_hex)
        )
        self.log_file = log_file

        self.last_checkpoint_id: Optional[int] = None
        # referral_id -> (head_seq, head_hash_hex)
        self.referral_heads: Dict[str, Tuple[int, str]] = {}

    def verify_checkpoint_sig(self, note_text: str, signature_b64_or_hex: str) -> bool:
        """Verifies Ed25519 signature of checkpoint note text."""
        try:
            # Try base64 first, then hex
            try:
                sig_bytes = base64.b64decode(signature_b64_or_hex)
                if len(sig_bytes) != 64:
                    sig_bytes = bytes.fromhex(signature_b64_or_hex)
            except Exception:
                sig_bytes = bytes.fromhex(signature_b64_or_hex)

            self.witness_pubkey.verify(sig_bytes, note_text.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError) as e:
            logger.error(f"Checkpoint signature verification failed: {e}")
            raise ValueError(f"CHECKPOINT_SIG: Invalid witness signature: {e}") from e

    def verify_restore_sig(
        self,
        restore_payload: bytes,
        cold_sig_b64_or_hex: str,
    ) -> bool:
        """Verifies cold Ed25519 signature for a RESTORE checkpoint."""
        try:
            try:
                sig_bytes = base64.b64decode(cold_sig_b64_or_hex)
                if len(sig_bytes) != 64:
                    sig_bytes = bytes.fromhex(cold_sig_b64_or_hex)
            except Exception:
                sig_bytes = bytes.fromhex(cold_sig_b64_or_hex)

            self.cold_pubkey.verify(sig_bytes, restore_payload)
            return True
        except (InvalidSignature, ValueError) as e:
            logger.error(f"Cold restore signature verification failed: {e}")
            return False

    def process_checkpoint(
        self,
        checkpoint_data: Dict[str, Any],
        referral_heads_sample: Optional[Dict[str, Tuple[int, str]]] = None,
    ) -> bool:
        """Processes a newly fetched checkpoint and updates witness state.

        Raises:
            ValueError: If signature verification fails (CHECKPOINT_SIG)
            RollbackError: If checkpoint id or referral head regresses without RESTORE
        """
        c_id = checkpoint_data["id"]
        note_text = checkpoint_data.get("note_text")
        if not note_text:
            # Reconstruct note text if not provided directly
            tree_size = checkpoint_data["tree_size"]
            root_b64 = checkpoint_data.get("root_hash_b64") or base64.b64encode(
                bytes.fromhex(checkpoint_data["root_hash"])
            ).decode("ascii")
            deployment = checkpoint_data.get("deployment", "colossus3-bengaluru-demo")
            note_text = f"rhp1/{deployment}\n{tree_size}\n{root_b64}\n"

        sig = checkpoint_data["signature"]
        # 1. Verify witness signature
        self.verify_checkpoint_sig(note_text, sig)

        # 2. Check for checkpoint ID regression (split-view or DB restore without notification)
        if self.last_checkpoint_id is not None and c_id < self.last_checkpoint_id:
            msg = (
                f"SPLIT_VIEW_OR_ROLLBACK_DETECTED: Checkpoint ID regressed "
                f"from {self.last_checkpoint_id} to {c_id}"
            )
            logger.error(msg)
            raise RollbackError(msg)

        # 3. Check for referral sequence regressions
        kind = checkpoint_data.get("kind", "REGULAR")
        if referral_heads_sample:
            for ref_id, (new_seq, new_hash) in referral_heads_sample.items():
                if ref_id in self.referral_heads:
                    prev_seq, prev_hash = self.referral_heads[ref_id]
                    if new_seq < prev_seq:
                        # Regression detected! Must be covered by a valid RESTORE checkpoint
                        if kind != "RESTORE":
                            msg = (
                                f"SPLIT_VIEW_OR_ROLLBACK_DETECTED: Referral {ref_id} "
                                f"head_seq regressed from {prev_seq} to {new_seq} "
                                f"in non-RESTORE checkpoint {c_id}"
                            )
                            logger.error(msg)
                            raise RollbackError(msg)

                        # Verify RESTORE cold signature
                        cold_sig = checkpoint_data.get("cold_signature")
                        if not cold_sig or not checkpoint_data.get("restore_from"):
                            msg = (
                                f"SPLIT_VIEW_OR_ROLLBACK_DETECTED: Referral {ref_id} "
                                f"head_seq regressed without valid RESTORE record in checkpoint {c_id}"
                            )
                            logger.error(msg)
                            raise RollbackError(msg)

                        # Check cold signature payload
                        root_hex = checkpoint_data.get("root_hash") or ""
                        if isinstance(root_hex, bytes):
                            root_hex = root_hex.hex()
                        taken_at = str(checkpoint_data.get("taken_at", ""))
                        restore_from = checkpoint_data["restore_from"]
                        tree_size = checkpoint_data["tree_size"]

                        restore_payload = canonical_jcs({
                            "checkpoint_id": int(restore_from),
                            "kind": "RESTORE",
                            "root_hash": root_hex,
                            "taken_at": taken_at,
                            "tree_size": tree_size,
                        })

                        if not self.verify_restore_sig(restore_payload, cold_sig):
                            # Also check alternative note payload
                            alt_payload = f"rhp1/restore/{restore_from}\n{tree_size}\n{root_hex}\n".encode("utf-8")
                            if not self.verify_restore_sig(alt_payload, cold_sig):
                                msg = f"SPLIT_VIEW_OR_ROLLBACK_DETECTED: Invalid cold signature on RESTORE checkpoint {c_id}"
                                logger.error(msg)
                                raise RollbackError(msg)

                self.referral_heads[ref_id] = (new_seq, new_hash)

        self.last_checkpoint_id = c_id

        # 4. Append to local log if specified
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            log_entry = {
                "checkpoint_id": c_id,
                "kind": kind,
                "tree_size": checkpoint_data["tree_size"],
                "root_hash": checkpoint_data.get("root_hash"),
                "synced_at": time.time(),
            }
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

        return True

    def sync_once(self, base_url: str) -> Dict[str, Any]:
        """Fetches /v1/checkpoints/latest and processes it."""
        url = f"{base_url.rstrip('/')}/v1/checkpoints/latest"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "RHP-Witness-Sync/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        self.process_checkpoint(data)
        return data


def main() -> None:
    parser = argparse.ArgumentParser(description="RHP-1 Off-Box Witness Pull Sync")
    parser.add_argument("--url", default="http://localhost:8000", help="Witness or API base URL")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds")
    parser.add_argument("--log-file", type=Path, default=Path("witness_sync_log.jsonl"), help="Path to local append log")
    args = parser.parse_args()

    client = WitnessSyncClient(log_file=args.log_file)
    logger.info(f"Starting witness pull sync against {args.url} every {args.interval}s...")

    while True:
        try:
            client.sync_once(args.url)
        except Exception as e:
            logger.error(f"Witness sync error: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
