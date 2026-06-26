# LLM KnightTrader
param(
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\mknig\AppData\Local\Programs\Python\Python312\python.exe"
& $Python (Join-Path $PSScriptRoot "kill_agents.py") | Out-Null
Start-Sleep -Seconds 2
$Python = "C:\Users\mknig\AppData\Local\Programs\Python\Python312\python.exe"
$PidDir = Join-Path $ProjectRoot "data\pids"
New-Item -ItemType Directory -Force -Path $PidDir | Out-Null

function Save-Pid($name, $proc) {
    $path = Join-Path $PidDir "$name.pid"
    Set-Content -Path $path -Value $proc.Id
}

$LogDir = Join-Path $ProjectRoot "data\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Wait-DashboardHealth([int]$MaxSec = 25) {
    for ($i = 0; $i -lt $MaxSec; $i++) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/health" -TimeoutSec 2 -UseBasicParsing
            if ($r.StatusCode -eq 200) { return $true }
        } catch {}
        Start-Sleep -Seconds 1
    }
    return $false
}

function Start-KnightTraderDashboard {
    $dashPid = Join-Path $PidDir "dashboard.pid"
    if (Test-Path $dashPid) {
        $old = Get-Content $dashPid -ErrorAction SilentlyContinue
        if ($old -and (Get-Process -Id $old -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $old -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
    $proc = Start-Process -FilePath $Python -ArgumentList "-m", "dashboard.server" -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
    Save-Pid "dashboard" $proc
    if (Wait-DashboardHealth) {
        Write-Host "LLM KnightTrader dashboard started PID $($proc.Id) -> http://127.0.0.1:8765"
    } else {
        Write-Host "LLM KnightTrader dashboard PID $($proc.Id) started but health check failed - see data\logs\dashboard.err"
    }
}

function Start-KnightTrader {
    $traderPid = Join-Path $PidDir "trader.pid"
    if (Test-Path $traderPid) {
        $old = Get-Content $traderPid -ErrorAction SilentlyContinue
        if ($old -and (Get-Process -Id $old -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $old -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
    $proc = Start-Process -FilePath $Python -ArgumentList "-m", "trader.agent" -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
    Save-Pid "trader" $proc
    Write-Host "LLM KnightTrader agent started PID $($proc.Id)"
}

function Start-KnightTraderMonitor {
    $monPid = Join-Path $PidDir "monitor.pid"
    if (Test-Path $monPid) {
        $old = Get-Content $monPid -ErrorAction SilentlyContinue
        if ($old -and (Get-Process -Id $old -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $old -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
    $proc = Start-Process -FilePath $Python -ArgumentList "-m", "monitor.agent" -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
    Save-Pid "monitor" $proc
    Write-Host "LLM KnightTrader monitor started PID $($proc.Id) (checks every 120s)"
}

Start-KnightTraderDashboard
Start-Sleep -Seconds 3
Start-KnightTrader
Start-Sleep -Seconds 2
Start-KnightTraderMonitor
if ($OpenBrowser -and (Wait-DashboardHealth 5)) {
    Start-Process "http://127.0.0.1:8765"
}
