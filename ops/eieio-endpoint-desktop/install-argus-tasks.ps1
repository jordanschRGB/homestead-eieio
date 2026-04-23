param(
    [string]$ApiToken = "change-me"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$powershell = (Get-Command powershell.exe).Source
$rawScript = Join-Path $root "start-argus-raw.ps1"
$ingestScript = Join-Path $root "start-argus-ingest.ps1"
$proxyScript = Join-Path $root "start-lmstudio-tail-proxy.ps1"
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$rawStartup = Join-Path $startupDir "ArgusLlama8010.cmd"
$ingestStartup = Join-Path $startupDir "ArgusIngest8020.cmd"
$proxyStartup = Join-Path $startupDir "LMStudioTailProxy6942.cmd"

$rawTaskCommand = "`"$powershell`" -NoProfile -ExecutionPolicy Bypass -File `"$rawScript`""
$ingestTaskCommand = "`"$powershell`" -NoProfile -ExecutionPolicy Bypass -File `"$ingestScript`" -ApiToken `"$ApiToken`""
$proxyTaskCommand = "`"$powershell`" -NoProfile -ExecutionPolicy Bypass -File `"$proxyScript`""

New-Item -ItemType Directory -Force -Path $startupDir | Out-Null
Set-Content -Path $rawStartup -Value "@echo off`r`n$rawTaskCommand`r`n" -Encoding ASCII
Set-Content -Path $ingestStartup -Value "@echo off`r`n$ingestTaskCommand`r`n" -Encoding ASCII
Set-Content -Path $proxyStartup -Value "@echo off`r`n$proxyTaskCommand`r`n" -Encoding ASCII

Write-Output "Installed Startup launchers:"
Write-Output " - $rawStartup"
Write-Output " - $ingestStartup"
Write-Output " - $proxyStartup"
