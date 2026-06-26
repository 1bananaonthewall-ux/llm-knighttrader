# Hot-reload dashboard only (no browser, no trader/monitor kill).
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\mknig\AppData\Local\Programs\Python\Python312\python.exe"
& $Python (Join-Path $ProjectRoot "monitor\dashboard_reload.py")
exit $LASTEXITCODE
