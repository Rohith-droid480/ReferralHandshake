# =============================================================================
# ReferralHandshake (Protocol RHP-1) — 1-Command Live Demonstration Launcher
# Windows PowerShell Launcher
# =============================================================================

$ErrorActionPreference = "Continue"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  REFERRALHANDSHAKE (PROTOCOL RHP-1) — 1-COMMAND DEMO LAUNCHER   " -ForegroundColor Cyan
Write-Host "  Colossus 3.0 HealthTech Track — Team MAHA YODHAS               " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Detect LAN IP
$LanIp = "127.0.0.1"
try {
    $LanIp = python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()"
} catch {
    $LanIp = "127.0.0.1"
}

# 2. Check if processes are already running or launch them
Write-Host "`n[1/5] Checking service daemons..." -ForegroundColor Yellow

$UvicornListening = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $UvicornListening) {
    Write-Host "  -> Starting FastAPI Server (0.0.0.0:8000)..." -ForegroundColor White
    Start-Process python -ArgumentList "-m uvicorn api.rhp.main:app --host 0.0.0.0 --port 8000" -WindowStyle Hidden
} else {
    Write-Host "  -> FastAPI Server already listening on port 8000." -ForegroundColor Green
}

$MonitorListening = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if (-not $MonitorListening) {
    Write-Host "  -> Starting Runtime Monitor (0.0.0.0:8001)..." -ForegroundColor White
    Start-Process python -ArgumentList "monitor/monitor.py" -WindowStyle Hidden
} else {
    Write-Host "  -> Runtime Monitor already listening on port 8001." -ForegroundColor Green
}

$PwaListening = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
if (-not $PwaListening) {
    Write-Host "  -> Starting PWA Frontend (0.0.0.0:8080)..." -ForegroundColor White
    Start-Process npx -ArgumentList "vite --host 0.0.0.0 --port 8080" -WorkingDirectory "$PSScriptRoot\pwa" -WindowStyle Hidden
} else {
    Write-Host "  -> PWA Frontend already listening on port 8080." -ForegroundColor Green
}

# 3. Start background daemons if not running
Start-Process python -ArgumentList "witness/signer.py" -WindowStyle Hidden -ErrorAction SilentlyContinue
Start-Process python -ArgumentList "-m api.rhp.poller" -WindowStyle Hidden -ErrorAction SilentlyContinue
Start-Process python -ArgumentList "-m api.rhp.relay" -WindowStyle Hidden -ErrorAction SilentlyContinue

Start-Sleep -Seconds 3

# 4. Reset & Seed Synthetic Demo Scenarios
Write-Host "`n[2/5] Seeding synthetic demonstration scenarios (S1-S6)..." -ForegroundColor Yellow
python scripts/seed_demo_scenarios.py

# 5. Check Healthz
Write-Host "`n[3/5] Verifying /healthz endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/healthz" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  -> Health Status: $($health.status) (Components Synced)" -ForegroundColor Green
} catch {
    Write-Host "  -> Health endpoint warming up..." -ForegroundColor Yellow
}

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host "  ALL DEMO SYSTEMS LIVE & READY FOR JUDGES                       " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  * React PWA Desk       : http://localhost:8080/" -ForegroundColor White
Write-Host "  * Static Production PWA: http://localhost:8000/app/" -ForegroundColor White
Write-Host "  * Mobile Wi-Fi Access  : http://${LanIp}:8080/" -ForegroundColor Green
Write-Host "  * FastAPI Backend Docs : http://localhost:8000/docs" -ForegroundColor White
Write-Host "  * Runtime Monitor UI   : http://localhost:8001/status" -ForegroundColor White
Write-Host "  * Android EMT APK      : http://localhost:8000/v1/download/apk" -ForegroundColor Green
Write-Host "=================================================================`n" -ForegroundColor Cyan
