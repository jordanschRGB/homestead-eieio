# HOMESTEAD EIEIO

**Everything In, Everything Ingested and Out.**

Self-healing knowledge graph with GNN-ranked vector retrieval. Runs on a $150 ARM board.

## What This Is

A local-first knowledge system where:
- Markdown files are nodes (human-readable)
- `[[wiki-links]]` are explicit edges (human-curated)
- Embedding similarities are implicit edges (machine-discovered)
- GNN reads both edge types for retrieval
- The graph self-heals: orphaned nodes get linked by geometry

## Architecture

- **Vault**: Obsidian-compatible markdown files (the canonical source of truth)
- **ruvector**: Rust vector DB with sqlite-vec, collections, GNN-ranked retrieval
- **Embed pipeline**: Local embeddings via NPU (80ms) or LM Studio
- **Self-healing linker**: Proposes [[links]] for under-connected nodes

## Proven Results

- **88% retrieval accuracy** (HOMESTEAD benchmark, frozen baseline — K=4, boost=0.035)
- 60 Rust crates analyzed, Bayesian-optimized collection configs
- +22% gain over 66% flat baseline (collections + GNN tuned)
- 94% observed in a single Cycle 3 parameter sweep (18 queries) — candidate result, needs revalidation before promoting

## Runs On

- Rock 5B+ (ARM64, 16GB RAM, RKNPU) — primary
- Any machine with Rust toolchain + sqlite

## Related

- [tain-cli](https://github.com/jordanschRGB/tain-cli) — the AI coding assistant that queries HOMESTEAD
- [EIGEN vault](docs/architecture/extended-architecture.md) — the knowledge graph this indexes

## Status

Proven retrieval system being extended with:
- Vault watcher daemon (auto-embed on file change)
- Self-healing linker (GNN-proposed links for orphans)
- Preference vectors (DRIFT-style steering at inference time)
- Session crystallization (compress conversations into knowledge nodes)
- Cross-machine MCP server (future)

See [docs/architecture/](docs/architecture/) for full specs.
