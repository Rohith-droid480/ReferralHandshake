"""ReferralHandshake Protocol RHP-1 — Judge Admission & Rotating QR Test Suite.

Specification Anchors:
- Architecture §9: Judge QR Admission, Cloudflare Turnstile & 20-Desk Cap
- Architecture §17: Local & Demo Topology
- BUILD_PLAN §7.2: Rotating QR Admission, Cloudflare Gate & LAN Mode Fallback
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.rhp.commands.judge_join import (
    _QR_TOKENS,
    judge_app,
    mint_qr_token,
    reset_judge_desks,
)
from api.rhp.config import get_settings


@pytest.fixture(autouse=True)
def clean_judge_state():
    reset_judge_desks()
    yield
    reset_judge_desks()


def test_mint_qr_token_structure_and_rotation():
    """GET /v1/judge/qr-token mints valid single-use QR payload rotated every 15s."""
    client = TestClient(judge_app)
    r = client.get("/v1/judge/qr-token")
    assert r.status_code == 200
    data = r.json()

    assert "jti" in data
    assert "expires_at" in data
    assert data["expires_in_s"] == 20
    assert "witness_pubkey_hex" in data
    assert "cold_pubkey_hex" in data
    assert "turnstile_site_key" in data
    assert r.headers["cache-control"] == "no-store"


def test_judge_join_allocates_desks_alternating_facilities():
    """Odd slots go to CHC_RAMANAGARA, even slots go to DH_MANDYA."""
    client = TestClient(judge_app)

    # Judge 1 (Slot 1)
    tok1 = client.get("/v1/judge/qr-token").json()
    r1 = client.post("/v1/judge/join", json={"jti": tok1["jti"], "turnstile_response": "1x-dummy"})
    assert r1.status_code == 200
    res1 = r1.json()
    assert res1["status"] == "OK"
    assert res1["slot_no"] == 1
    assert res1["facility_code"] == "CHC_RAMANAGARA"
    assert "set-cookie" in r1.headers

    # Judge 2 (Slot 2)
    tok2 = client.get("/v1/judge/qr-token").json()
    r2 = client.post("/v1/judge/join", json={"jti": tok2["jti"], "turnstile_response": "1x-dummy"})
    assert r2.status_code == 200
    res2 = r2.json()
    assert res2["status"] == "OK"
    assert res2["slot_no"] == 2
    assert res2["facility_code"] == "DH_MANDYA"


def test_jti_single_use_enforcement():
    """Attempting to reuse a consumed JTI returns 403 JTI_ALREADY_USED."""
    client = TestClient(judge_app)
    tok = client.get("/v1/judge/qr-token").json()

    # First use succeeds
    r1 = client.post("/v1/judge/join", json={"jti": tok["jti"], "turnstile_response": "1x-dummy"})
    assert r1.status_code == 200

    # Second use with exact same JTI is rejected
    r2 = client.post("/v1/judge/join", json={"jti": tok["jti"], "turnstile_response": "1x-dummy"})
    assert r2.status_code == 403
    assert r2.json()["detail"] == "JTI_ALREADY_USED"


def test_expired_or_unknown_jti_rejection():
    """Expired or unregistered JTI returns 400 QR_TOKEN_EXPIRED."""
    client = TestClient(judge_app)

    # 1. Non-existent JTI
    r1 = client.post("/v1/judge/join", json={"jti": str(uuid4()), "turnstile_response": "1x-dummy"})
    assert r1.status_code == 400
    assert r1.json()["detail"] == "QR_TOKEN_EXPIRED"

    # 2. Expired JTI
    tok = client.get("/v1/judge/qr-token").json()
    # Artificially expire the token in metadata
    _QR_TOKENS[tok["jti"]]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)

    r2 = client.post("/v1/judge/join", json={"jti": tok["jti"], "turnstile_response": "1x-dummy"})
    assert r2.status_code == 400
    assert r2.json()["detail"] == "QR_TOKEN_EXPIRED"


def test_20_desk_admission_cap():
    """Joining succeeds up to 20 active desks; the 21st join receives 429 ADMISSION_CAP_REACHED."""
    client = TestClient(judge_app)

    for i in range(1, 21):
        tok = client.get("/v1/judge/qr-token").json()
        r = client.post("/v1/judge/join", json={"jti": tok["jti"], "turnstile_response": "1x-dummy"})
        assert r.status_code == 200
        assert r.json()["slot_no"] == i

    # 21st join attempt
    tok21 = client.get("/v1/judge/qr-token").json()
    r21 = client.post("/v1/judge/join", json={"jti": tok21["jti"], "turnstile_response": "1x-dummy"})
    assert r21.status_code == 429
    assert r21.json()["detail"] == "ADMISSION_CAP_REACHED"

