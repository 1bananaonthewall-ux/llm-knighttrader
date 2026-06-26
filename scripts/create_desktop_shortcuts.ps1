# Create Start / Stop shortcuts on the Windows desktop.
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LauncherDir = Join-Path $ProjectRoot "launcher"
$Desktop = [Environment]::GetFolderPath("Desktop")

$shortcuts = @(
    @{
        Name = "Start LLM KnightTrader.lnk"
        Target = Join-Path $LauncherDir "Start LLM KnightTrader.bat"
    },
    @{
        Name = "Stop LLM KnightTrader.lnk"
        Target = Join-Path $LauncherDir "Stop LLM KnightTrader.bat"
    }
)

$shell = New-Object -ComObject WScript.Shell
foreach ($item in $shortcuts) {
    $path = Join-Path $Desktop $item.Name
    $lnk = $shell.CreateShortcut($path)
    $lnk.TargetPath = $item.Target
    $lnk.WorkingDirectory = $ProjectRoot
    $lnk.WindowStyle = 1
    $lnk.Description = "LLM KnightTrader"
    $lnk.Save()
    Write-Host "Created $path"
}
