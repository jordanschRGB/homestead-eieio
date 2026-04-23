param(
    [string]$ArgusBaseUrl = "http://127.0.0.1:8010",
    [string]$ArgusModel = "pplx-embed-context-v1-0.6b-q8_0.gguf",
    [string]$ApiToken = "change-me",
    [string]$PreprocessBaseUrl = "http://127.0.0.1:6942",
    [string]$PreprocessModel = "google/gemma-4-e2b",
    [int]$Port = 8020
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

$python = Join-Path $root ".venv\\Scripts\\python.exe"

try {
    & $python -c "import fastapi, uvicorn, requests, pydantic_settings, httpx" | Out-Null
} catch {
    & $python -m pip install --upgrade pip
    & $python -m pip install -r requirements.txt
}

$env:ARGUS_BASE_URL = $ArgusBaseUrl
$env:ARGUS_MODEL = $ArgusModel
$env:API_TOKEN = $ApiToken
$env:PREPROCESS_BASE_URL = $PreprocessBaseUrl
$env:PREPROCESS_MODEL = $PreprocessModel
$env:PORT = [string]$Port

& $python -m uvicorn app.main:app --host 0.0.0.0 --port $Port
