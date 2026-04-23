# EIEIO Endpoint Desktop Ingest Helper

Thin ingest API that accepts raw documents or zipped markdown/text folders, chunks them server-side, calls the live Perplexity Embedding endpoint, and writes a JSONL manifest of chunk metadata plus vectors.

## Endpoints

- `GET /`
- `GET /help`
- `GET /health`
- `POST /v1/ingest/text`
- `POST /v1/ingest/archive`

## Behavior

- Supports `.md`, `.markdown`, `.mdx`, `.txt`, and `.text` inside uploaded zip archives
- Chunks documents by character window with overlap
- Batches chunk text to the upstream Perplexity Embedding endpoint
- Writes one JSONL output file per job
- Can optionally return inline vectors for smaller jobs

## Which Route Do I Use?

- `POST /v1/ingest/text`: use this when your caller already has the document contents and can send JSON.
- `POST /v1/ingest/archive`: use this when you have a folder full of markdown or transcript files; zip it once and upload the archive.
- `GET /help`: returns the plain-English route summary and example request shapes.

## Run

```powershell
.\run-local.ps1 -ArgusBaseUrl http://127.0.0.1:8010 -ArgusModel pplx-embed-context-v1-0.6b-q8_0.gguf -ApiToken change-me -Port 8020
```

## Service Scripts

- `start-argus-raw.ps1`: launches the raw `8010` embedding server with the known-good `32768` context and `2048` physical batch size.
- `start-argus-ingest.ps1`: launches the `8020` wrapper without reinstalling dependencies on every boot unless the venv is missing packages.
- `start-lmstudio-tail-proxy.ps1`: binds the current Tailscale IPv4 on `6942` and forwards to LM Studio on `127.0.0.1:6942`, waking the LM Studio server on demand if it is asleep.
- `install-argus-tasks.ps1`: installs user Startup-folder launchers for `ArgusLlama8010`, `ArgusIngest8020`, and `LMStudioTailProxy6942`.

Legacy note:

- filenames and env vars still say `argus` in a few places because they were written before the naming cleanup
- the actual model family is **Perplexity Embedding** / `pplx-embed-context-v1-0.6b`
- `argus-ai` is only the current publisher breadcrumb in the local model path
- LM Studio itself still listens on `127.0.0.1:6942`; the tail proxy is what makes that preprocess lane reachable from the Pi
