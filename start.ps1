<#
.SYNOPSIS
    Launches the Trading Bot (Python), Web Dashboard (Next.js), and Crucix (Node.js).
.DESCRIPTION
    - Starts Crucix intelligence server if present (port 3117)
    - Activates the Python venv and runs main.py
    - Installs npm deps if needed and runs next dev (port 3000)
    - Press Ctrl+C to stop all processes cleanly
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   NEURAL FX  -  LOCAL LAUNCHER"        -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Preflight checks

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Python venv not found at .venv\Scripts\python.exe" -ForegroundColor Red
    Write-Host "        Run: python -m venv .venv" -ForegroundColor Yellow
    Write-Host "        Then: .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
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

$envFile = Join-Path $Root ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "[ERROR] .env not found. Copy .env.example and fill in your values." -ForegroundColor Red
    exit 1
}

# 2. Launch Crucix intelligence server (optional)

$crucixDir    = Join-Path $Root "crucix"
$crucixServer = Join-Path $crucixDir "server.mjs"
$crucixJob    = $null

if (Test-Path $crucixServer) {
    Write-Host "[*] Starting Crucix on http://localhost:3117 ..." -ForegroundColor Magenta
    $crucixJob = Start-Process `
        -FilePath "node" `
        -ArgumentList $crucixServer `
        -WorkingDirectory $crucixDir `
        -PassThru `
        -NoNewWindow
    Write-Host "    PID: $($crucixJob.Id)" -ForegroundColor DarkGray
    Start-Sleep -Seconds 5
} else {
    Write-Host "[*] crucix/server.mjs not found - skipping (bot runs without it)" -ForegroundColor DarkGray
}

# 3. Launch Python trading bot

Write-Host "[*] Starting Python trading bot..." -ForegroundColor Green
$botJob = Start-Process `
    -FilePath $venvPython `
    -ArgumentList (Join-Path $Root "main.py") `
    -WorkingDirectory $Root `
    -PassThru `
    -NoNewWindow

Write-Host "    PID: $($botJob.Id)" -ForegroundColor DarkGray

# 4. Launch Next.js dashboard

Write-Host "[*] Starting Next.js dashboard on http://localhost:3000 ..." -ForegroundColor Green
$webJob = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm", "run", "dev" `
    -WorkingDirectory $webDir `
    -PassThru `
    -NoNewWindow

Write-Host "    PID: $($webJob.Id)" -ForegroundColor DarkGray

# 5. Status summary

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($null -ne $crucixJob) {
    Write-Host "  Crucix PID  : $($crucixJob.Id)  (http://localhost:3117)" -ForegroundColor White
}
Write-Host "  Bot PID     : $($botJob.Id)" -ForegroundColor White
Write-Host "  Web PID     : $($webJob.Id)  (http://localhost:3000)" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop everything." -ForegroundColor Yellow
Write-Host ""

# 6. Wait and clean up on exit

try {
    while (-not $botJob.HasExited -and -not $webJob.HasExited) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "[*] Shutting down..." -ForegroundColor Yellow

    if (-not $botJob.HasExited) {
        Stop-Process -Id $botJob.Id -Force -ErrorAction SilentlyContinue
        Write-Host "    Stopped bot     (PID $($botJob.Id))" -ForegroundColor DarkGray
    }

    if ($null -ne $crucixJob -and -not $crucixJob.HasExited) {
        Stop-Process -Id $crucixJob.Id -Force -ErrorAction SilentlyContinue
        Write-Host "    Stopped Crucix  (PID $($crucixJob.Id))" -ForegroundColor DarkGray
    }

    if (-not $webJob.HasExited) {
        Stop-Process -Id $webJob.Id -Force -ErrorAction SilentlyContinue
        Get-Process -Name "node" -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowTitle -eq "" } |
            Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "    Stopped web     (PID $($webJob.Id))" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "[OK] All processes stopped." -ForegroundColor Green
}
