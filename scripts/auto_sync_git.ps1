# Auto-commit and push project changes (used by Cursor stop hook).
param(
    [string]$Message = ""
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".git")) {
    Write-Host "auto_sync_git: not a git repo"
    exit 0
}

$status = git status --porcelain 2>$null
if (-not $status) {
    exit 0
}

git add -A
$staged = git diff --cached --name-only 2>$null
if (-not $staged) {
    exit 0
}

if (-not $Message) {
    $Message = "auto-sync: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

git commit -m $Message 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "auto_sync_git: commit skipped or failed"
    exit 0
}

$branch = git rev-parse --abbrev-ref HEAD 2>$null
git push origin $branch 2>$null
if ($LASTEXITCODE -ne 0) {
    git push -u origin $branch 2>$null
}
Write-Host "auto_sync_git: pushed $branch"
