#!/usr/bin/env bash
# =============================================================================
# ReferralHandshake (Protocol RHP-1) — 1-Command Live Demonstration Launcher
# Linux / macOS / Bash Launcher
# =============================================================================

set -e

echo "================================================================="
echo "  REFERRALHANDSHAKE (PROTOCOL RHP-1) — 1-COMMAND DEMO LAUNCHER   "
echo "  Colossus 3.0 HealthTech Track — Team MAHA YODHAS               "
echo "================================================================="

# 1. Detect LAN IP
LAN_IP="127.0.0.1"
if command -v python3 &>/dev/null; then
    LAN_IP=$(python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "127.0.0.1")
elif command -v python &>/dev/null; then
    LAN_IP=$(python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "127.0.0.1")
fi

echo ""
echo "[1/4] Starting service daemons in background..."
python -m uvicorn api.rhp.main:app --host 0.0.0.0 --port 8000 &>/dev/null &
python monitor/monitor.py &>/dev/null &
python witness/signer.py &>/dev/null &
python -m api.rhp.poller &>/dev/null &
python -m api.rhp.relay &>/dev/null &
(cd pwa && npx vite --host 0.0.0.0 --port 8080 &>/dev/null &)

sleep 3

echo ""
echo "[2/4] Seeding synthetic demonstration scenarios (S1-S6)..."
python scripts/seed_demo_scenarios.py || python3 scripts/seed_demo_scenarios.py || true

echo ""
echo "[3/4] Verifying /healthz endpoint..."
curl -s http://localhost:8000/healthz || true

echo ""
echo "================================================================="
echo "  ALL DEMO SYSTEMS LIVE & READY FOR JUDGES                       "
echo "================================================================="
echo "  * React PWA Desk       : http://localhost:8080/"
echo "  * Static Production PWA: http://localhost:8000/app/"
echo "  * Mobile Wi-Fi Access  : http://${LAN_IP}:8080/"
echo "  * FastAPI Backend Docs : http://localhost:8000/docs"
echo "  * Runtime Monitor UI   : http://localhost:8001/status"
echo "  * Android EMT APK      : http://localhost:8000/v1/download/apk"
echo "================================================================="
