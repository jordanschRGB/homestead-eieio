param(
    [string]$ModelPath = "C:\Users\jorda\.lmstudio\models\argus-ai\pplx-embed-context-v1-0.6b-GGUF\pplx-embed-context-v1-0.6b-q8_0.gguf",
    [string]$ServerExe = "C:\Users\jorda\.docker\bin\inference\llama-server.exe",
    [string]$Alias = "pplx-embed-context-v1-0.6b-q8_0.gguf",
    [int]$Port = 8010,
    [int]$CtxSize = 32768,
    [int]$BatchSize = 2048,
    [int]$UBatchSize = 2048
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $root "runtime-logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "llama8010.log"

if (-not (Test-Path $ServerExe)) {
    throw "llama-server executable not found at $ServerExe"
}

if (-not (Test-Path $ModelPath)) {
    throw "Model not found at $ModelPath"
}

& $ServerExe `
    --model $ModelPath `
    --host 0.0.0.0 `
    --port $Port `
    --embeddings `
    --ctx-size $CtxSize `
    --batch-size $BatchSize `
    --ubatch-size $UBatchSize `
    --gpu-layers all `
    --alias $Alias `
    --no-webui `
    --log-prefix `
    --log-timestamps `
    --log-file $logFile
