---
title: "HOMESTEAD DB — EIEIO"
notion_id: "336616ac-62ea-81b9-a604-fd7fce04fb9f"
last_modified: "2026-04-02"
tags: [retrieval, infrastructure, architecture, eigen]
---

# HOMESTEAD DB — EIEIO

**Everything In, Everything Out.**

Retrieval system built on the EIGEN geometric load framework. Information goes in as vectors. Comes out as geometry. Quality depends on what happens between in and out.

Part of the EIGEN family:
- **EIGEN** — Everything Is Generally Eigen Networks (the framework)
- **3BODY** — 3 Bound Operators, Deterministic Yield (H, R, t)
- **SOFON** — Surface Orthogonal Folding Over Null-space (dimensional projection)
- **DRIFT** — Developmental Reorganization through Intentional Fine-Tuning (training)
- **HOMESTEAD** — the retrieval system that applies the geometry

## The Four Operations

### PLOW — Reshape the ground

Change the topology of the search space before retrieval touches it. The biggest single gain (+17%) comes from here. Architecture over algorithm.

- **ruvector-collections** — domain separation. Manual or auto-discovered.
- **sparsifier + mincut** — automated boundary discovery via effective resistance.
- **morphogenetic** — reaction-diffusion collection growth from uniform initial conditions.

In EIGEN terms: PLOW selects which eigenspace to project into. It is the measurement operator. Collections are R for retrieval.

### TILL — Read the grain

Read the permanent neighborhood structure. Confirm eigenspace activation. The only algorithm that adds value on top of PLOW (+5%).

- **ruvector-gnn** — static KNN graph activation check. K=3, boost=0.05, top=3.
- Tightest projection = best result. More graph information = more noise.

In EIGEN terms: TILL reads the existing eigenvectors. It confirms that the query activates a coherent region of the static graph. It does not create structure — it reads it.

### FENCE — Protect the boundaries

Diagnostic layer. Measures whether the geometry is honest. Detects misassigned chunks, parasitic edges, collection degradation. Does not change results — validates them.

- **Effective resistance** — identifies structurally necessary edges. Same-domain 1.19x higher.
- **ruvector-coherence** — Fiedler eigenvalue per collection.
- **ruQu boundary tension** — detects misassigned chunks. F1=56% screening pass.
- **Entanglement** — 2.2x within/cross domain separation.
- **Ingest gate** — 9 safety checks before any vector touches the DB.

In EIGEN terms: FENCE measures the eigenvalue spectrum. Is the curvature (commitment) where it should be? Are the boundaries (near-zero eigenvalues) clean?

### HARVEST — Take what grew

The retrieval itself. The query that reaps. Everything before this is preparation.

- Collection-scoped search with GNN activation
- The query is the measurement. It projects the collection into a result set.
- 94% accuracy. 1 miss remaining (cross-domain query, unsolvable within collections by design).

In EIGEN terms: HARVEST is the projection R applied to the state. The query selects the eigenbasis. The result is the measurement outcome.

## The Principle

**The geometry has all the information. Every intervention that works is a gain change — amplify quiet signal, suppress loud signal. Every intervention that fails tries to add information the geometry already contains.**

PLOW changes gain (removes dominant PC1, exposes quiet PC3).
TILL reads gain (checks if neighbors confirm the query's activation).
FENCE measures gain (is the structure still honest?).
HARVEST delivers the result.

## Evidence

| Config | Score | Delta |
|--------|-------|-------|
| Flat baseline (no PLOW) | 66% | -- |
| PLOW only (collections) | 83% | +17% |
| PLOW + TILL (coll + GNN K=3 b=0.05 top=3) | 94% | +28% |
| PLOW + wrong TILL (default GNN params) | 77% | +11% |
| No PLOW + TILL (GNN on flat) | 66% | 0% |
| PLOW + SALT (IIT within collections) | 66% | 0% (erased PLOW gains) |

11 killed hypotheses. 15+ tests. Topology confirmed representation-invariant.

## Infrastructure

```
pplx-embed-context-0.6b W8A8 on RK3588 NPU (46,500 tok/s)
  -> embed-proxy :6900 (validates dim=1024, NPU only, no fallbacks)
    -> ruvector 2.1.0 collections (/opt/ruvector/collections)
       agent_knowledge: 51 vectors
       personal: 3 vectors
       corpus: 38 vectors
    -> ingest gate (9 safety checks, rate limit, snapshots)
```

Zero cloud. Zero desktop dependency. $0/forever. $80 ARM board.

PERPLEXAKEET calibration data: Opus 4.6 reasoning traces + Wikipedia questions + Bob's parakeet system memory (110 adversarial pairs). Named after Gerald the parakeet, unofficial QA department.

## What EIEIO Doesn't Have Yet

1. **Nightly cron ingest** — scan for new data, embed via NPU, insert through gate.
2. **rkllama systemd unit** — NPU model server needs auto-start on reboot.
3. **Cross-collection queries** — the 2 remaining misses need HARVEST across collections.
4. **SONA** — learns from query patterns over time. Needs live traffic. Long game.
5. **Scale testing** — all results on 26-92 chunks. Need 1000+ to validate.

Discovery date: 2026-04-01
Framework: EIGEN
Hardware: Rock 5B+ (RK3588, 16GB, NPU)
Repo: jordanschRGB/NaTASHA branch v2

## See Also
- [[eigen-framework-complete-architecture]]
- [[ruvector-crate-atlas]]
- [[embedding-infrastructure-2026-03-31]]
- [[why-homestead-matters]]
