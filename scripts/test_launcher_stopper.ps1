$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Desktop = [Environment]::GetFolderPath("Desktop")
$Python = "C:\Users\mknig\AppData\Local\Programs\Python\Python312\python.exe"
$DashboardUrl = "http://127.0.0.1:8765"

function Test-Shortcut($name, $expectedBat) {
    $path = Join-Path $Desktop $name
    if (-not (Test-Path $path)) { throw "Missing shortcut: $path" }
    $shell = New-Object -ComObject WScript.Shell
    $target = $shell.CreateShortcut($path).TargetPath
    if ($target -ne $expectedBat) { throw "Shortcut $name points to $target, expected $expectedBat" }
    Write-Host "OK shortcut: $name -> $target"
}

function Get-Counts {
    $d = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "dashboard\.server" }).Count
    $t = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "trader\.agent" }).Count
    return @{ dashboard = $d; trader = $t }
}

function Test-Health {
    $r = Invoke-WebRequest -Uri "$DashboardUrl/api/health" -TimeoutSec 5 -UseBasicParsing
    return $r.StatusCode -eq 200
}

$startBat = Join-Path $ProjectRoot "launcher\Start LLM KnightTrader.bat"
$stopBat = Join-Path $ProjectRoot "launcher\Stop LLM KnightTrader.bat"

Test-Shortcut "Start LLM KnightTrader.lnk" $startBat
Test-Shortcut "Stop LLM KnightTrader.lnk" $stopBat

# Ensure clean slate
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "stop_all.ps1") | Out-Null
Start-Sleep -Seconds 2

# Test launcher (no browser for automated test)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "start_core.ps1")
Start-Sleep -Seconds 3
$c = Get-Counts
if ($c.dashboard -ne 1 -or $c.trader -ne 1) { throw "Start failed: dashboard=$($c.dashboard) trader=$($c.trader)" }
if (-not (Test-Health)) { throw "Start failed: health check" }
Write-Host "OK launcher: 1 dashboard, 1 trader, health ok"

# Test stopper
& cmd /c "`"$stopBat`""
Start-Sleep -Seconds 2
$c = Get-Counts
if ($c.dashboard -ne 0 -or $c.trader -ne 0) { throw "Stop failed: dashboard=$($c.dashboard) trader=$($c.trader)" }
try {
    Invoke-WebRequest -Uri "$DashboardUrl/api/health" -TimeoutSec 2 -UseBasicParsing | Out-Null
    throw "Stop failed: dashboard still responding"
} catch {
    Write-Host "OK stopper: all agents down, port closed"
}

Write-Host "PASS: desktop launcher and stopper work"
