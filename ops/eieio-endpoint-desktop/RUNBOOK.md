# EIEIO Endpoint Desktop Wrapper Runbook

This is the thin service layer sitting in front of the working Perplexity Embedding endpoint on `jordandesktot2`.

## Live Target

- Host: `100.94.187.104`
- Desktop name: `jordandesktot2`

## Ports

- Raw embeddings: `8010`
- Smart ingest wrapper: `8020`
- LM Studio local preprocess endpoint: `6942`
- LM Studio tail proxy endpoint: `http://jordandesktot2:6942`

## Models

- Raw embed model: `pplx-embed-context-v1-0.6b-q8_0.gguf`
- Model family: `pplx-embed-context-v1-0.6b` (Perplexity Embedding)
- Default preprocess model: `google/gemma-4-e2b`

## Windows Task Names

- Raw Argus server: `ArgusLlama8010`
- Ingest wrapper: `ArgusIngest8020`
- LM Studio tail proxy: `LMStudioTailProxy6942`

## What Runs Where

- `8010` is the custom `hellc/llama.cpp` server serving the Perplexity Embedding GGUF directly.
- `8020` is the Python wrapper that can:
  - accept raw text documents
  - accept zipped markdown/text archives
  - optionally call LM Studio for semantic chunk planning
  - send final chunks to the Perplexity Embedding server
- LM Studio itself listens only on `127.0.0.1:6942`.
- `start-lmstudio-tail-proxy.ps1` binds the current Tailscale IPv4 on `6942` and forwards to `127.0.0.1:6942`.
- The Pi should use `http://jordandesktot2:6942` for preprocess traffic.

## Core Endpoints

- `GET /help`
- `GET /health`
- `POST /v1/ingest/text`
- `POST /v1/ingest/archive`

## Auth

- Wrapper bearer token: set via `API_TOKEN`

## Local Run

```powershell
.\run-local.ps1 `
  -ArgusBaseUrl http://127.0.0.1:8010 `
  -ArgusModel pplx-embed-context-v1-0.6b-q8_0.gguf `
  -ApiToken change-me `
  -Port 8020
```

## Service Mode

```powershell
.\start-argus-raw.ps1
.\start-argus-ingest.ps1 -ApiToken change-me
.\start-lmstudio-tail-proxy.ps1
.\install-argus-tasks.ps1 -ApiToken change-me
```

Known-good raw launch details:

- `--ctx-size 32768`
- `--batch-size 2048`
- `--ubatch-size 2048`
- `--gpu-layers all`

Why the batch flags matter:

- the earlier transient `500` was not random
- the server had been launched with `n_ubatch = 512`
- chunks around `804` tokens caused `input is too large to process`
- raising both batch sizes to `2048` fixed the failure in live retests

## Persistence Note

- this desktop currently denies scheduled-task creation without elevation
- `install-argus-tasks.ps1` therefore installs Startup-folder launchers instead
- the launcher names still match the historical task names so the mental model stays the same

## Naming Note

- `Argus` is not the model name
- the actual model family here is **Perplexity Embedding** / `pplx-embed-context-v1-0.6b`
- `argus-ai` only appears as the current publisher breadcrumb in the local GGUF path and should not be treated as the service or model identity

## Proof Commands

### Raw model list

```powershell
Invoke-RestMethod -Method Get -Uri 'http://100.94.187.104:8010/v1/models'
```

### Wrapper help

```powershell
Invoke-RestMethod -Method Get -Uri 'http://100.94.187.104:8020/help'
```

### LM Studio tail proxy

```powershell
Invoke-RestMethod -Method Get -Uri 'http://100.94.187.104:6942/v1/models'
```

### Smart ingest with preprocess

```powershell
$body = @{
  documents = @(
    @{
      name = 'transcript.md'
      content = '# Scene 1`n`nDad: Curiosity starts when you admit you do not know.'
    }
  )
  use_preprocessor = $true
  preprocess_model = 'google/gemma-4-e2b'
  return_vectors_inline = $false
} | ConvertTo-Json -Depth 8

Invoke-RestMethod -Method Post `
  -Uri 'http://100.94.187.104:8020/v1/ingest/text' `
  -Headers @{ Authorization = 'Bearer change-me' } `
  -ContentType 'application/json' `
  -Body $body
```

## Known Good Behavior

- `8020/help` returns the route summary and preprocess default.
- `use_preprocessor=true` calls LM Studio with a JSON-schema chunk plan request.
- The Pi-side `3103` smart-ingest path reaches preprocess through `http://jordandesktot2:6942`, which is the tail proxy, not LM Studio's raw bind.
- The wrapper writes JSONL output files with:
  - source metadata
  - unit ranges
  - semantic labels/reasons
  - chunk text
  - embeddings

## Things Not To Commit

- `.venv`
- output JSONL artifacts
- downloaded model files
- local caches
