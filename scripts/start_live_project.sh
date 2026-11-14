#!/usr/bin/env bash
# =============================================================================
# ReferralHandshake Protocol RHP-1 — Complete Live Full-Stack Startup Launcher
# =============================================================================

set -e

LAN_IP=$(python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "127.0.0.1")

echo "================================================================="
echo "  REFERRALHANDSHAKE (PROTOCOL RHP-1) — LIVE STACK LAUNCHER       "
echo "================================================================="
echo "  -> Local Loopback : http://localhost:8080"
echo "  -> Mobile Wi-Fi IP: http://${LAN_IP}:8080"
echo "  -> Backend API    : http://${LAN_IP}:8000"
echo "  -> Runtime Monitor: http://${LAN_IP}:8001/status"
echo "  -> Android EMT APK: http://${LAN_IP}:8000/v1/download/apk"
echo "================================================================="

# Start background services
python -m uvicorn api.rhp.main:app --host 0.0.0.0 --port 8000 &
python monitor/monitor.py &
python witness/signer.py &
python -m api.rhp.poller &
python -m api.rhp.relay &
(cd pwa && npx vite --host 0.0.0.0 --port 8080) &

wait
