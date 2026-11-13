"""Comprehensive Verification Suite for 9-Character Crockford Base32 + Mod-37 Codec.

Specification Anchors:
- Architecture §8: Paper Code Codec & Mod-37 Mathematical Integrity [Closure F7]
- BUILD_PLAN §9.5: 9-Character Paper Code Codec & Paper-First Linking UI
- Test Anchor: T2 Paper Code Gate (1000 mutated codes 100% error rejection)
"""

import random
import pytest
from api.rhp.reach.paper_code import (
    CHECKSUM_ALPHABET,
    CROCKFORD_BASE32,
    InvalidPaperCodeChecksumError,
    PaperCodeError,
    RateLimitExceededError,
    check_paper_code_rate_limit,
    decode_paper_code,
    encode_paper_code,
    normalize_paper_code,
    verify_paper_code,
)


def test_round_trip_encode_decode():
    """Verify that 100 random 40-bit integers round-trip identically."""
    for _ in range(100):
        n = random.getrandbits(40)
        code = encode_paper_code(n)
        assert len(code) == 9
        decoded_n = decode_paper_code(code)
        assert decoded_n == n
        assert verify_paper_code(code) is True


def test_normalization_and_ambiguous_characters():
    """Test normalization: case insensitivity, hyphens/spaces, and I/L->1, O->0 mapping."""
    n = 123456789012
    code = encode_paper_code(n)

    # Hyphenated code
    hyphenated = f"{code[:4]}-{code[4:]}"
    assert decode_paper_code(hyphenated) == n

    # Lowercase with spaces
    spaced = f"  {code.lower()}  "
    assert decode_paper_code(spaced) == n

    # Ambiguous mappings: if code has '1', replacing with 'I' or 'L' should decode identically
    # If code has '0', replacing with 'O' should decode identically
    # Let's craft an explicit code with 1 and 0
    # Payload = "01ABCDEF"
    test_str = "01ABCDEF"
    # Find check char
    n_val = 0
    for ch in test_str:
        n_val = (n_val << 5) | CROCKFORD_BASE32.index(ch)
    check_char = CHECKSUM_ALPHABET[n_val % 37]
    base_code = f"{test_str}{check_char}"

    # Replace '0' with 'O', '1' with 'I' or 'L'
    assert decode_paper_code(f"OIABCDEF{check_char}") == n_val
    assert decode_paper_code(f"OLABCDEF{check_char}") == n_val


def test_1000_single_symbol_substitution_errors_rejected():
    """Mutate 1,000 valid codes by altering exactly one character at a random position.

    Mathematical guarantee: 100% of single-symbol errors MUST be detected and rejected.
    """
    rejected_count = 0
    trials = 1000

    for _ in range(trials):
        n = random.getrandbits(40)
        code = encode_paper_code(n)

        # Pick random position to mutate (0 through 8)
        pos = random.randint(0, 8)
        orig_char = code[pos]

        if pos < 8:
            # First 8 positions use CROCKFORD_BASE32
            candidates = [c for c in CROCKFORD_BASE32 if c != orig_char]
            new_char = random.choice(candidates)
        else:
            # 9th position uses CHECKSUM_ALPHABET
            candidates = [c for c in CHECKSUM_ALPHABET if c != orig_char]
            new_char = random.choice(candidates)

        mutated = code[:pos] + new_char + code[pos + 1 :]

        try:
            decode_paper_code(mutated)
        except InvalidPaperCodeChecksumError:
            rejected_count += 1
        except PaperCodeError:
            rejected_count += 1

    # Exact 100% rejection rate
    assert rejected_count == trials, f"Expected {trials} rejections, got {rejected_count}"


def test_1000_adjacent_transposition_errors_rejected():
    """Mutate 1,000 valid codes by swapping two adjacent distinct characters.

    Mathematical guarantee: 100% of adjacent transpositions MUST be detected and rejected.
    """
    rejected_count = 0
    trials = 1000

    for _ in range(trials):
        while True:
            n = random.getrandbits(40)
            code = encode_paper_code(n)
            # Pick position in [0, 6] so we swap within the 8 payload characters
            pos = random.randint(0, 6)
            if code[pos] != code[pos + 1]:
                break

        # Swap pos and pos+1
        chars = list(code)
        chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
        transposed = "".join(chars)

        try:
            decode_paper_code(transposed)
        except InvalidPaperCodeChecksumError:
            rejected_count += 1
        except PaperCodeError:
            rejected_count += 1

    assert rejected_count == trials, f"Expected {trials} transposition rejections, got {rejected_count}"


def test_rate_limiting_10_attempts_per_min():
    """Verify check_paper_code_rate_limit permits 10 calls and rejects the 11th with 429."""
    session_id = f"test-sess-{random.randint(1000, 9999)}"

    for i in range(10):
        assert check_paper_code_rate_limit(session_id) is True

    # 11th attempt must raise RateLimitExceededError
    with pytest.raises(RateLimitExceededError, match="429 RATE_LIMIT_EXCEEDED"):
        check_paper_code_rate_limit(session_id)

