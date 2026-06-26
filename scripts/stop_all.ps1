# Stop LLM KnightTrader — dashboard, trader, monitor, babysit watchers.
$ErrorActionPreference = "SilentlyContinue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidDir = Join-Path $ProjectRoot "data\pids"
$Python = "C:\Users\mknig\AppData\Local\Programs\Python\Python312\python.exe"

function Stop-ByPidFile($name) {
    $path = Join-Path $PidDir "$name.pid"
    if (-not (Test-Path $path)) { return }
    $procId = Get-Content $path -ErrorAction SilentlyContinue
    if ($procId) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped $name (PID $procId)"
    }
    Remove-Item $path -Force -ErrorAction SilentlyContinue
}

function Get-AgentCount {
    param([string]$Fragment)
    return @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "python.exe" -and $_.CommandLine -match $Fragment
    }).Count
}

Stop-ByPidFile "monitor"
Stop-ByPidFile "trader"
Stop-ByPidFile "dashboard"

& $Python (Join-Path $PSScriptRoot "kill_agents.py")
Start-Sleep -Seconds 1

$dash = Get-AgentCount "dashboard\.server"
$trader = Get-AgentCount "trader\.agent"
$mon = Get-AgentCount "monitor\.agent"
$babysit = Get-AgentCount "babysit"

if ($dash -eq 0 -and $trader -eq 0 -and $mon -eq 0 -and $babysit -eq 0) {
    Write-Host "LLM KnightTrader stopped."
    exit 0
}

Write-Host "ERROR: agents still running dashboard=$dash trader=$trader monitor=$mon babysit=$babysit"
exit 1
