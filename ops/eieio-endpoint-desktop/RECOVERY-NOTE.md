# EIEIO Endpoint Desktop Recovery Note

This directory is the desktop-side EIEIO Endpoint stack preserved out of `C:\Users\jorda\Documents\Codex\2026-04-22-argus-ingest-wrapper` before the desktop gets wiped for a Linux rebuild.

What is here:

- runnable desktop helper code in `app/`
- tests in `tests/`
- startup and service scripts for `8010`, `8020`, and the LM Studio tail proxy on `6942`
- runtime logs captured from the working Windows setup
- snapshots of the LM Studio settings/preset files that mattered during repair
- sanitized Startup launcher snapshots under `config-snapshots/startup/`

Important reality notes:

- `Argus` in old filenames is legacy naming only. The actual embedding model family here is **Perplexity Embedding** / `pplx-embed-context-v1-0.6b`.
- LM Studio itself listens on `127.0.0.1:6942`; the `lmstudio_tail_proxy.py` shim is what exposed preprocess traffic on the desktop Tailscale IP for the Pi-facing EIEIO service.
- `config-snapshots/startup/ArgusIngest8020.cmd` is intentionally sanitized to `change-me` instead of the live bearer token.
- These files are preserved as operational receipts, not as a claim that the Windows layout is the final architecture.

Last verified behavior before preservation:

- Pi `3103` ingest succeeded with `preprocess_used=true`
- desktop `8010` raw embeddings worked
- desktop `6942` preprocess recovered through the tail proxy even after LM Studio was stopped first
