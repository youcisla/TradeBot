<#
.SYNOPSIS
    Clears all generated/cached artifacts for the TradingBot project.
.DESCRIPTION
    Removes:
      - Next.js build cache  (web/.next)
      - Python __pycache__   (all subdirectories)
      - Python .pytest_cache
      - Downloaded history CSVs  (data/history)
      - Bot log files            (logs/)
    Does NOT remove node_modules, .venv, or trained models.
#>

$Root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   TRADING BOT  -  CLEAR CACHE"          -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Remove-Dir($path, $label) {
    if (Test-Path $path) {
        Remove-Item -Recurse -Force $path
        Write-Host "  [cleared] $label" -ForegroundColor Green
    } else {
        Write-Host "  [skip]    $label (not found)" -ForegroundColor DarkGray
    }
}

# ── Next.js build cache ─────────────────────────────────────────────
Remove-Dir (Join-Path $Root "web\.next") "Next.js build cache  (web/.next)"

# ── Python __pycache__ (all nested) ─────────────────────────────────
$pycaches = Get-ChildItem -Path $Root -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "\\.venv\\" }
foreach ($dir in $pycaches) {
    Remove-Item -Recurse -Force $dir.FullName
}
if ($pycaches.Count -gt 0) {
    Write-Host "  [cleared] Python __pycache__ ($($pycaches.Count) dirs)" -ForegroundColor Green
} else {
    Write-Host "  [skip]    Python __pycache__ (none found)" -ForegroundColor DarkGray
}

# ── Python .pytest_cache ─────────────────────────────────────────────
Remove-Dir (Join-Path $Root ".pytest_cache") "pytest cache"

# ── Downloaded history CSVs ──────────────────────────────────────────
Remove-Dir (Join-Path $Root "data\history") "History CSVs       (data/history)"

# ── Bot log files ─────────────────────────────────────────────────────
Remove-Dir (Join-Path $Root "logs") "Bot logs            (logs/)"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Done. Run .\start.ps1 to restart."     -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
