# Enable post-commit push + Cursor agent auto-sync hooks.
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

git config core.hooksPath .githooks
Write-Host "Git hooks path -> .githooks (post-commit will push)"

$hookDir = Join-Path $ProjectRoot ".cursor\hooks"
New-Item -ItemType Directory -Force -Path $hookDir | Out-Null

Write-Host "Cursor stop hook -> scripts\auto_sync_git.ps1 (commit+push when agent finishes)"
Write-Host "Done. Re-open project or restart Cursor if hooks do not load."
