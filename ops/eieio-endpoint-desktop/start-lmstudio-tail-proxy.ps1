$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "python"
$script = Join-Path $root "lmstudio_tail_proxy.py"
$logs = Join-Path $root "runtime-logs"
$tailIp = (& tailscale.exe ip -4 | Select-Object -First 1).Trim()

if (-not $tailIp) {
    throw "Could not determine Tailscale IPv4 address."
}

New-Item -ItemType Directory -Force -Path $logs | Out-Null

$outLog = Join-Path $logs "lmstudio-tail-proxy.out.log"
$errLog = Join-Path $logs "lmstudio-tail-proxy.err.log"

Write-Host "Starting LM Studio tail proxy on $tailIp`:6942"
Write-Host "stdout -> $outLog"
Write-Host "stderr -> $errLog"

& $python $script --listen-host $tailIp --listen-port 6942 --target-base http://127.0.0.1:6942 1>> $outLog 2>> $errLog
