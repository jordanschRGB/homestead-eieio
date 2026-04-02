---
title: "DECISION — Embedding Ownership: 3080 Embeds, Rock Queries, memorySearch Retired"
tags: [architecture, decision, embeddings, ruvector, homestead, resolved]
date: "2026-04-02"
status: PARTIALLY RESOLVED
related: [[homestead-vault-self-heal]], [[homestead-db-eieio]], [[bootstrap-review-2026-04-02]]
---

# DECISION — Embedding Ownership

**Status: PARTIALLY RESOLVED. Key decisions made. Implementation details remain.**

## Decisions Made (Apr 2, 2026)

### 1. memorySearch is OUT
Jordan has used it for months. It's mid. It's just sqlite. Everyone complains about it. It requires paid embedding. RuVector with pplx-embed is objectively superior. memorySearch gets commented out, not replaced — just removed.

### 2. The 3080 is the embed server
Post-wipe, the desktop (3080 10GB) becomes a dedicated Linux inference server on Tailscale. Its job: embed fat, juicy, rich 1024-dim vectors. pplx-embed Q8 via llama-cpp, full GPU acceleration. This is the ONLY machine that creates embeddings.

### 3. The Rock queries, it doesn't embed (for HOMESTEAD)
The Rock has ruvector. It stores and queries vectors. The NPU handles real-time embed for OpenClaw agent operations (small queries, session context). But bulk vault embedding is the 3080's job — the Rock doesn't have the RAM or the throughput.

### 4. The 5080 laptop is the daily driver
Jordan edits files and works on a 5080 laptop. The 3080 desktop sits as a headless inference server.

### 5. pplx-embed is the ONE model
1024-dim. Same model on both machines (Q8 on 3080, W8A8 on Rock NPU for real-time). mxbai is retired with memorySearch.

## What's Still Open

### Chunk size
400 tokens (Rock NPU constraint) vs larger on 3080. The heading-aware split strategy should be shared. Chunk size can differ per machine as long as splitting logic matches. Needs more exploration — this is a multi-day investigation.

### Vault sync
Vault lives on Google Drive. 3080 embeds it locally (Google Drive mounted). Vectors need to reach ruvector on the Rock. Push path: 3080 embeds → jsonl → push to ruvector via API or rsync + local ingest. Not designed yet.

### Meta-collection location
Lives on Rock (in ruvector). Confirm/revert feedback originates from Obsidian (on laptop/desktop). Cross-machine feedback path needs design.

### memorySearch migration
OpenClaw agents currently call memorySearch. Need to verify which agents depend on it, what the query interface looks like, and whether ruvector can be a drop-in or needs an adapter. Jordan said "comment it out" — that implies hard cutover, not gradual migration.

## Architecture After Resolution

```
5080 Laptop (daily driver)
  │  Jordan edits vault in Obsidian
  │  Vault on Google Drive
  ▼
3080 Desktop (inference server, Linux, Tailscale)
  │  Embeds vault files: pplx-embed Q8, llama-cpp, full GPU
  │  Fat, juicy, 1024-dim, heading-aware chunks
  │  Pushes vectors to Rock
  ▼
Rock 5B (query + operations)
  │  ruvector stores and queries vectors
  │  NPU handles real-time agent embed (small queries only)
  │  Dreamer runs as NPU time-share batch job
  │  meta-collection lives here
  ▼
OpenClaw agents query ruvector, not memorySearch
```

## Previous Context

Three paths existed before this decision:

| Machine | Script | Model | Status |
|---------|--------|-------|--------|
| Desktop (3080) | embed_vault.py | pplx-embed Q8 | KEEPER — becomes the embed server |
| Rock (NPU) | ingest-to-ruvector-v2.py | pplx-embed W8A8 | KEEPER — for real-time agent queries |
| Rock (memorySearch) | OpenClaw built-in | mxbai-embed-large-v1 | RETIRED — comment out |
