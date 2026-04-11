<#
.SYNOPSIS
    Launches the Trading Bot (Python), Web Dashboard (Next.js), and Crucix (Node.js).
.DESCRIPTION
    - Starts Crucix intelligence server if present (port 3117)
    - Activates the Python venv and runs main.py
    - Installs npm deps if needed and runs next dev (port 3000)
    - Press Ctrl+C to stop all processes cleanly
#>

param(
    [switch]$AuditMode,
    [switch]$DoctorOnly,
    [switch]$SkipDoctor,
    [ValidateSet("custom", "dev", "paper", "live-safe", "live-full")]
    [string]$Profile = "custom",
    [switch]$Onboard
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   NEURAL FX  -  LOCAL LAUNCHER"        -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($AuditMode) {
    # Child processes inherit this env var from the launcher process.
    $env:DEMO_MODE = "true"
    Write-Host "[SAFE MODE] Audit mode enabled: forcing DEMO_MODE=true" -ForegroundColor Yellow
}

# 1. Preflight checks

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Python venv not found at .venv\Scripts\python.exe" -ForegroundColor Red
    Write-Host "        Run: python -m venv .venv" -ForegroundColor Yellow
    Write-Host "        Then: .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

if ($Onboard) {
    $wizard = Join-Path $Root "scripts\first_run_wizard.py"
    if (-not (Test-Path $wizard)) {
        Write-Host "[ERROR] Onboarding wizard not found at scripts\first_run_wizard.py" -ForegroundColor Red
        exit 1
    }
    Write-Host "[*] Launching first-run onboarding wizard..." -ForegroundColor Yellow
    & $venvPython $wizard
    exit $LASTEXITCODE
}

if ($Profile -ne "custom") {
    $env:BOT_PROFILE = $Profile
    Write-Host "[PROFILE] Runtime profile forced by launcher: BOT_PROFILE=$Profile" -ForegroundColor Yellow
}

$doctorScript = Join-Path $Root "scripts\ops_doctor.py"
if (-not $SkipDoctor -and (Test-Path $doctorScript)) {
    Write-Host "[*] Running ops doctor preflight..." -ForegroundColor Yellow
    $proc = Start-Process -FilePath $venvPython -ArgumentList ("`"$doctorScript`" --root `"$Root`" --strict") -PassThru -Wait -NoNewWindow
    if ($proc.ExitCode -ne 0) {
        Write-Host "[ERROR] Ops doctor reported critical failures." -ForegroundColor Red
        Write-Host "        Fix issues above or rerun with -SkipDoctor to bypass." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "[OK] Ops doctor checks passed." -ForegroundColor Green
}

if ($DoctorOnly) {
    Write-Host "[*] Doctor-only mode requested. Exiting after diagnostics." -ForegroundColor Cyan
    exit 0
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

# Prevent duplicate launcher sessions that can create duplicate trades.
$existingBot = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -match '^python(\.exe)?$' -and
        $_.CommandLine -like "*$Root*" -and
        $_.CommandLine -like "*main.py*"
    }

$existingWeb = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -eq 'node.exe' -and
        $_.CommandLine -like "*$Root*web*" -and
        $_.CommandLine -like "*next dev*"
    }

if ($existingBot -or $existingWeb) {
    Write-Host "[ERROR] Existing TradeBot processes detected. Stop them before launching again." -ForegroundColor Red
    if ($existingBot) {
        Write-Host "  Running bot PID(s): $($existingBot.ProcessId -join ', ')" -ForegroundColor Yellow
    }
    if ($existingWeb) {
        Write-Host "  Running web PID(s): $($existingWeb.ProcessId -join ', ')" -ForegroundColor Yellow
    }
    exit 1
}

# Also clear any orphaned next dev servers holding ports 3000/3001 before we start.
foreach ($port in @(3000, 3001)) {
    $stalePids = @()
    foreach ($line in (netstat -ano)) {
        if ($line -match 'LISTENING') {
            $fields = $line.Trim() -split '\s+'
            if ($fields.Count -ge 5 -and ($fields[1] -like ("*:" + $port))) {
                $stalePids += $fields[4]
            }
        }
    }
    foreach ($procId in $stalePids) {
        $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($p -and $p.MainWindowTitle -eq '') {
            Write-Host ("[WARN] Port " + $port + " occupied by stale process " + $procId + " - clearing it") -ForegroundColor Yellow
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }
    }
}

# 2. Check Crucix intelligence (hosted on Vercel)

$crucixUrl = "https://crucix-pi.vercel.app"
Write-Host "[*] Checking Crucix at $crucixUrl ..." -ForegroundColor Magenta
try {
    $resp = Invoke-WebRequest -Uri "$crucixUrl/api/health" -UseBasicParsing -TimeoutSec 8 -ErrorAction Stop
    if ($resp.StatusCode -eq 200) {
        Write-Host "[OK] Crucix is live at $crucixUrl" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Crucix returned $($resp.StatusCode) - bot will use safe defaults." -ForegroundColor Yellow
    }
} catch {
    Write-Host "[WARN] Crucix unreachable - bot will use safe defaults." -ForegroundColor Yellow
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
$frontendLogDir = Join-Path (Join-Path $Root "logs") "frontend"
New-Item -ItemType Directory -Force -Path $frontendLogDir | Out-Null
$webLogFile = Join-Path $frontendLogDir "dev_server.log"
$webJob = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/c npm run dev > `"$webLogFile`" 2>&1" `
    -WorkingDirectory $webDir `
    -PassThru `
    -NoNewWindow

Write-Host "    PID: $($webJob.Id)" -ForegroundColor DarkGray

# 5. Status summary

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Crucix      : $crucixUrl" -ForegroundColor White
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
