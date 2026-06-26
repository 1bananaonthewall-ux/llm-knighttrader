# Restart only dashboard + trader if down. No browser, no monitor kill.
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\mknig\AppData\Local\Programs\Python\Python312\python.exe"
$PidDir = Join-Path $ProjectRoot "data\pids"
New-Item -ItemType Directory -Force -Path $PidDir | Out-Null

function Test-ModuleRunning($fragment) {
    $n = (Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "python.exe" -and $_.CommandLine -match $fragment
    } | Measure-Object).Count
    return $n -gt 0
}

function Wait-DashboardHealth([int]$MaxSec = 20) {
    for ($i = 0; $i -lt $MaxSec; $i++) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/health" -TimeoutSec 2 -UseBasicParsing
            if ($r.StatusCode -eq 200) { return $true }
        } catch {}
        Start-Sleep -Seconds 1
    }
    return $false
}

if (-not (Wait-DashboardHealth 3)) {
    & $Python (Join-Path $ProjectRoot "monitor\dashboard_reload.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "dashboard hot-reload failed exit=$LASTEXITCODE"
    }
    Wait-DashboardHealth | Out-Null
}

if (-not (Test-ModuleRunning "trader.agent")) {
    $proc = Start-Process -FilePath $Python -ArgumentList "-m", "trader.agent" -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
    Set-Content -Path (Join-Path $PidDir "trader.pid") -Value $proc.Id
    Write-Host "restarted trader PID $($proc.Id)"
}
