<#
.SYNOPSIS
    Launches the Trading Bot (Python) and Web Dashboard (Next.js) side by side.
.DESCRIPTION
    - Activates the Python venv and runs main.py
    - Installs npm deps if needed and runs next dev
    - Press Ctrl+C to stop both processes
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   TRADING BOT  -  LOCAL LAUNCHER"       -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Preflight checks ─────────────────────────────────────────────
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Python venv not found at .venv\Scripts\python.exe" -ForegroundColor Red
    Write-Host "        Run:  python -m venv .venv ; .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

$webDir = Join-Path $Root "web"
$nodeModules = Join-Path $webDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "[*] Installing web dependencies (npm install)..." -ForegroundColor Yellow
    Push-Location $webDir
    npm install
    Pop-Location
    Write-Host "[OK] npm install complete." -ForegroundColor Green
}

$envLocal = Join-Path $webDir ".env.local"
if (-not (Test-Path $envLocal)) {
    Write-Host "[ERROR] web/.env.local not found. Copy web/.env.example and fill in values." -ForegroundColor Red
    exit 1
}

# ── 2. Launch Python bot ────────────────────────────────────────────
Write-Host "[*] Starting Python trading bot..." -ForegroundColor Green
$botJob = Start-Process -FilePath $venvPython `
    -ArgumentList (Join-Path $Root "main.py") `
    -WorkingDirectory $Root `
    -PassThru `
    -NoNewWindow

Write-Host "    PID: $($botJob.Id)" -ForegroundColor DarkGray

# ── 3. Launch Next.js dev server ────────────────────────────────────
Write-Host "[*] Starting Next.js dashboard on http://localhost:3000 ..." -ForegroundColor Green
$webJob  = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c","npm","run","dev" `
    -WorkingDirectory $webDir `
    -PassThru `
    -NoNewWindow

Write-Host "    PID: $($webJob.Id)" -ForegroundColor DarkGray

# ── 4. Wait & cleanup ──────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Bot PID : $($botJob.Id)"                -ForegroundColor White
Write-Host "  Web PID : $($webJob.Id)"                -ForegroundColor White
Write-Host "  Dashboard : http://localhost:3000"       -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop everything." -ForegroundColor Yellow
Write-Host ""

try {
    # Block until either process exits
    while (-not $botJob.HasExited -and -not $webJob.HasExited) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "[*] Shutting down..." -ForegroundColor Yellow

    if (-not $botJob.HasExited) {
        Stop-Process -Id $botJob.Id -Force -ErrorAction SilentlyContinue
        Write-Host "    Stopped bot (PID $($botJob.Id))" -ForegroundColor DarkGray
    }
    if (-not $webJob.HasExited) {
        Stop-Process -Id $webJob.Id -Force -ErrorAction SilentlyContinue
        # Also kill any orphaned node processes from next dev
        Get-Process -Name "node" -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowTitle -eq "" } |
            Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "    Stopped web (PID $($webJob.Id))" -ForegroundColor DarkGray
    }

    Write-Host "[OK] All processes stopped." -ForegroundColor Green
}
