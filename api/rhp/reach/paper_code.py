"""ReferralHandshake Protocol RHP-1 — 9-Character Crockford Base32 + Mod-37 Paper Code Codec.

Specification Anchors:
- Architecture §8: Paper-First Fallback, Crockford Base32 + Mod-37 Codec [Closure F7]
- BUILD_PLAN §9.5: 9-Character Paper Code Codec & Paper-First Linking
- Test Anchor: T2 Paper Code Gate (test_paper_code_mod37.py)

Mathematical Properties:
- 40-bit random integer N in [0, 2^40 - 1] (1,099,511,627,775)
- 8 Crockford Base32 payload characters (symbols: 0-9, A-H, J-K, M-N, P-T, V-Z; excludes I, L, O, U)
- 9th check character: c = N mod 37, mapped to 37-character alphabet:
    0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U
- 100% detection of all single-character substitution errors (since 37 is prime and 32 is coprime to 37)
- 100% detection of all adjacent transposition errors of distinct characters (since 31 is coprime to 37)
"""

from __future__ import annotations

import secrets
import time
from typing import Dict, List, Optional, Tuple

# Standard 32-character Crockford Base32 Alphabet (excludes I, L, O, U)
CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CROCKFORD_MAP = {ch: i for i, ch in enumerate(CROCKFORD_BASE32)}

# 37-character Checksum Alphabet (Crockford Base32 + 5 symbols: *, ~, $, =, U)
CHECKSUM_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U"
CHECKSUM_MAP = {ch: i for i, ch in enumerate(CHECKSUM_ALPHABET)}

MAX_N = (1 << 40) - 1

# In-memory rate limiting: 10 attempts per minute per session
_RATE_LIMIT_STORE: Dict[str, List[float]] = {}
RATE_LIMIT_MAX_ATTEMPTS = 10
RATE_LIMIT_WINDOW_S = 60.0


class PaperCodeError(ValueError):
    """Base error for paper code encoding or decoding failures."""
    pass


class InvalidPaperCodeChecksumError(PaperCodeError):
    """Raised when the 9th check character does not match N mod 37."""
    pass


class RateLimitExceededError(PaperCodeError):
    """Raised when resolve attempts exceed 10 per minute per session."""
    pass


def encode_paper_code(n: Optional[int] = None) -> str:
    """Encodes a 40-bit integer into a 9-character Crockford Base32 + mod-37 paper code.

    If n is omitted, 40 cryptographically secure random bits are generated.
    """
    if n is None:
        n = secrets.randbits(40)

    if not (0 <= n <= MAX_N):
        raise PaperCodeError(f"Integer {n} out of bounds for 40-bit paper code [0, {MAX_N}]")

    # Encode 8 Crockford Base32 characters (MSB first)
    chars = []
    temp = n
    for _ in range(8):
        chars.append(CROCKFORD_BASE32[temp & 0x1F])
        temp >>= 5
    payload_str = "".join(reversed(chars))

    # Compute mod-37 check character
    check_val = n % 37
    check_char = CHECKSUM_ALPHABET[check_val]

    return f"{payload_str}{check_char}"


def normalize_paper_code(code_str: str) -> str:
    """Normalizes input string by removing whitespace/hyphens and mapping ambiguous characters."""
    s = code_str.strip().upper().replace("-", "").replace(" ", "")
    if len(s) != 9:
        raise PaperCodeError(f"Paper code must be exactly 9 characters, got {len(s)} ('{code_str}')")

    payload_chars = list(s[:8])
    for i, ch in enumerate(payload_chars):
        if ch in ("I", "L"):
            payload_chars[i] = "1"
        elif ch == "O":
            payload_chars[i] = "0"
        elif ch not in CROCKFORD_MAP:
            raise PaperCodeError(f"Invalid character '{ch}' at position {i+1} in paper code payload")

    check_char = s[8]
    if check_char not in CHECKSUM_MAP:
        raise PaperCodeError(f"Invalid check character '{check_char}' at position 9 in paper code")

    return "".join(payload_chars) + check_char


def decode_paper_code(code_str: str) -> int:
    """Decodes and verifies a 9-character paper code, returning the underlying 40-bit integer.

    Raises InvalidPaperCodeChecksumError if checksum check fails.
    """
    normalized = normalize_paper_code(code_str)
    payload = normalized[:8]
    check_char = normalized[8]

    # Reconstruct 40-bit integer
    n = 0
    for ch in payload:
        n = (n << 5) | CROCKFORD_MAP[ch]

    expected_check_val = n % 37
    actual_check_val = CHECKSUM_MAP[check_char]

    if expected_check_val != actual_check_val:
        raise InvalidPaperCodeChecksumError(
            f"422 INVALID_PAPER_CODE_CHECKSUM: Expected check symbol '{CHECKSUM_ALPHABET[expected_check_val]}' (mod 37 = {expected_check_val}), got '{check_char}' ({actual_check_val})"
        )

    return n


def verify_paper_code(code_str: str) -> bool:
    """Returns True if the paper code is valid, False otherwise."""
    try:
        decode_paper_code(code_str)
        return True
    except PaperCodeError:
        return False


def check_paper_code_rate_limit(session_id: str) -> bool:
    """Enforces 10 attempts/minute rate limit per session.

    Returns True if allowed, raises RateLimitExceededError if exceeded.
    """
    now = time.time()
    attempts = _RATE_LIMIT_STORE.get(session_id, [])
    # Filter attempts within the sliding 60-second window
    attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW_S]

    if len(attempts) >= RATE_LIMIT_MAX_ATTEMPTS:
        raise RateLimitExceededError(
            f"429 RATE_LIMIT_EXCEEDED: Maximum {RATE_LIMIT_MAX_ATTEMPTS} paper code attempts per minute exceeded"
        )

    attempts.append(now)
    _RATE_LIMIT_STORE[session_id] = attempts
    return True

