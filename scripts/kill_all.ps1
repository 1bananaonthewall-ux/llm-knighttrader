# Kill Python processes running hermes-llm-trader agent modules (not this script).
$ErrorActionPreference = "SilentlyContinue"
Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq "python.exe" -and $_.CommandLine -match "hermes-llm-trader" -and (
            $_.CommandLine -match "trader\.agent" -or
            $_.CommandLine -match "dashboard\.server" -or
            $_.CommandLine -match "monitor\.agent" -or
            $_.CommandLine -match "watch_and_fix" -or
            $_.CommandLine -match "watch_logs"
        )
    } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force
        Write-Host "Killed PID $($_.ProcessId)"
    }
Start-Sleep -Seconds 1
$left = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and $_.CommandLine -match "hermes-llm-trader" -and (
        $_.CommandLine -match "trader\.agent|dashboard\.server|monitor\.agent|watch_and_fix|watch_logs"
    )
})
if ($left.Count -gt 0) {
    Write-Host "WARNING: $($left.Count) python agent processes still running"
} else {
    Write-Host "All KnightTrader python agents stopped."
}
