#!/usr/bin/env pwsh
# Updates the Crucix submodule to the latest commit from the upstream owner

$ErrorActionPreference = "Stop"

Write-Host "Pulling Crucix updates from calesthio..." -ForegroundColor Green
Set-Location crucix
git fetch upstream
git merge upstream/master --no-edit
git push origin master
Set-Location ..

Write-Host "Updating TradeBot submodule pointer..." -ForegroundColor Green
git add crucix
git commit -m "chore: sync crucix to latest upstream $(Get-Date -Format 'yyyy-MM-dd')" 
# Ignore error if no changes
$LastExitCode = 0
git push

Write-Host "Done. Restart Crucix and TradeBot via start.ps1" -ForegroundColor Cyan
