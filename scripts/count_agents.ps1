$d = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "dashboard\.server" }).Count
$t = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "trader\.agent" }).Count
$m = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "monitor\.agent" }).Count
Write-Host "dashboard=$d trader=$t monitor=$m"
