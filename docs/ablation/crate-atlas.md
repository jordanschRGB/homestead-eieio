---
title: "RuVector Crate Atlas — 60+ Crates Analyzed"
notion_id: "335616ac-62ea-816f-9382-f2c8650b70c7"
last_modified: "2026-04-02"
tags: [retrieval, research, infrastructure, eigen]
---

# RuVector Crate Atlas — 60+ Crates Analyzed

Complete catalog of every RuVector crate, categorized by mechanism. Used for selecting which crates to install, ablation testing, and matching crate capabilities to Jordan's Hessian landscape theory.

Source: github.com/ruvnet/ruvector/tree/main/crates

> This page is part of the EIGEN framework. See: [[eigen-framework-complete-architecture]] for the full tree. The crate taxonomy maps to HOMESTEAD EIEIO operations (PLOW/TILL/FENCE/HARVEST).

## Stacked Ablation Results (2026-04-01) — LATEST

**Dataset:** 26 chunks across 3 domains (bob/parakeet: 10, cuda: 8, historical: 8), 18 queries with domain tags.
**Embedding model:** pplx-embed-context-v1-0.6b Q8 (1024-dim, llama-server)

| Stack | Score | Delta vs Flat | Notes |
|-------|-------|---------------|-------|
| flat_baseline | 66% | — | All chunks in one space |
| coll+baseline | 83% | +17% | Collections alone. Zero regressions. |
| **coll+gnn_tuned** | **88%** | **+22%** | **BEST. K=4, boost=0.035.** |
| coll+gnn (default) | 77% | +11% | Default GNN params HURT inside collections |
| coll+hyperbolic | 83% | +17% | Neutral on top of collections |
| coll+prime_radiant | 83% | +17% | Neutral — no contradictions in data |
| coll+iit | 66% | 0% | POISON PILL — wipes out collection gains |

**Key findings:**
1. Collections is the biggest win (+17%). 78% of flat queries had cross-domain contamination. Architecture > algorithm.
2. GNN needs retuning inside collections. Default K=3 boost=0.02 hurts. K=4 boost=0.035 works.
3. IIT is a poison pill. Zeroes out all gains in every combo.
4. Only 2 queries still miss: "survival prioritization" and "professionalism under pressure" — both require cross-domain reasoning.

**UPDATE (late 2026-04-01):** Cycle 3 parameter sweep found **94% (17/18) at K=3, boost=0.05, top=3.** Tightest graph projection = best result. See [[rosetta-stone-layer-ordering-principle]] for full analysis.

## Crate Classification System

The 60+ ruvector crates reduce to 4 functional classes.

### Class 1: SHAPERS (architecture layer)
Reshape the search space topology before retrieval touches it.

- **ruvector-collections** — manual domain separation. PROVEN +17%.
- **sparsifier + mincut** — automated boundary discovery. Strips loud signal (PC1), exposes quiet structure (PC3). PROVEN 72% zero-label.
- **morphogenetic** — reaction-diffusion collection growth. 67%.
- **thermorust** — energy minimization partition. 56-61%.

### Class 2: READERS (graph layer)
Read permanent neighborhood structure. Confirm eigenspace activation.

- **ruvector-gnn** — static KNN graph activation check. PROVEN +5% on collections (88-94%).
- K=3, boost=0.05, top=3 is optimal. Tightest projection = best.

### Class 3: AMPLIFIERS (measurement layer)
Find load-bearing structure. Diagnostic, not operational.

- **effective resistance** — identifies structural necessity per edge. Same-domain 1.19x higher resistance.
- **ruvector-coherence** — Fiedler eigenvalue per collection.
- **ruQu boundary tension** — detects misassigned chunks. F1=56% screening.
- **entanglement** — 2.2x within/cross domain separation.

### Class 4: NOISE (wrong layer or wrong mechanism)
Impose structure, average globally, or measure properties the space doesn't have.

- **IIT within collections** — POISON (-17%).
- **Hopfield flat** — POISON (-33%).
- **PPR** — graph random walk dilutes query signal.
- **Consensus voting** — mutual reinforcement doesn't match GNN's mechanism.

## TIER 1: Geometry-First / Non-Anthropomorphic

### ruvector-hyperbolic-hnsw
- **Mechanism:** Poincare ball geometry. Hierarchy IS distance.
- **Tested:** +6% on 19 chunks, -4% on 36 chunks. Hub penalty coefficient doesn't scale with chunk count.

### prime-radiant
- **Mechanism:** Sheaf Laplacian mathematics. Energy = contradiction between connected nodes. Not confidence — coherence.
- **Formula:** `E(S) = Σ wₑ · ‖ρᵤ(xᵤ) - ρᵥ(xᵥ)‖²`
- **Tested:** Neutral on Bob (no contradictions). Will shine on real agent memory.

### ruvector-mincut
- **Mechanism:** Dynamic min-cut. Finds thinnest connections between clusters.
- **Published:** crates.io v2.0.6, 14,876 downloads (most downloaded ruvector crate!)

### thermorust
- **Mechanism:** Thermodynamic principles. Energy-based computation. Information flows downhill.
- **Why Hessian-relevant:** If the landscape metaphor is literal, this treats retrieval as finding the energy minimum.

### ruvector-sparsifier
- **Mechanism:** Spectral graph sparsification. Compressed shadow graph preserving spectral properties.
- **What it does:** Finds the minimum skeleton that keeps the topology intact.

### ruvector-consciousness
- **Mechanism:** Possibly IIT 4.0 which is pure topology.
- **Status:** Tested — IIT is poison on L0/L1. On collection GRAPH: untested.

### ruQu
- **Mechanism:** Quantum error correction via dynamic min-cut.
- **What it does:** Detects "something is wrong with the geometry" without knowing what the error IS.

## TIER 2: Bio-Inspired / Emergent

### ruvector-nervous-system
- **Mechanism:** 5-layer spiking neural network. Timing-based, not weight-based.
- **Prediction:** Useless cold. After 1000+ queries: learns which collections fire together for which query types.

### sona
- **Mechanism:** Self-Optimizing Neural Architecture. Three loops: Instant (<1ms MicroLoRA), Background (K-means hourly), Deep (EWC++ weekly).
- **Tested:** -7% on small dataset (not enough history). Designed for long-term use.
- **Published:** crates.io v0.1.9, 5,310 downloads

## TIER 3: Architecture / Infrastructure

### ruvector-collections
- **Status: PROVEN +17%.** Compiled into ruvector-cli 2.1.0 as of 2026-04-01.
- **OOM fix applied:** HnswConfig max_elements reduced from 10M (3.8GB/DB) to 100K (38MB/DB).

### ruvector-filter
- Metadata queries (source:youtube, date>2026-03, agent:natasha)

### ruvector-snapshot
- Point-in-time backups before experiments. Safety net.

### ruvector-verified
- Proof-gated mutations. Formal verification that changes are authorized.

### ruvector-temporal-tensor
- Tiered compression. Old data compresses, recent stays hot.

### ruvector-domain-expansion
- Cross-domain verified transfer learning. Knowledge from YouTube only transfers to personal collection IF it measurably improves retrieval.

## TIER 4: Distributed / Infrastructure (Skip for Now)
Single Rock 5B. Not distributed. Skip: ruvector-cluster, ruvector-raft, ruvector-replication.

## Collection-to-Crate Mapping

| Collection | Tier 1 (install now) | Tier 2 (geometry) | Tier 3 (emergent) |
|------------|---------------------|------------------|------------------|
| Knowledge (YouTube, papers) | collections, filter, sona, temporal-tensor | mincut, sparsifier | domain-expansion |
| Personal (sessions, prefs) | collections, filter, sona | prime-radiant, coherence | nervous-system |
| Governance (AGENTS.md, SOUL.md) | collections, verified | prime-radiant | — (frozen, no learning) |
| Research (Hessian, DRIFT) | collections, filter, sona | math, hyperbolic-hnsw, mincut | consciousness, thermorust |

## Hessian Hypothesis Predictions

If the loss landscape has intrinsic geometry that good algorithms respect, then:
1. **mincut** should find natural cluster boundaries that match human-perceived topic boundaries
2. **hyperbolic-hnsw** should correctly represent hierarchies (Gerald veto → flavor → delivery) that flat cosine collapses
3. **thermorust** should converge to the same answer regardless of starting point (ergodic search)
4. **sparsifier** should identify load-bearing vectors
5. **prime-radiant** should detect contradictions as high-energy states in the sheaf
6. **consciousness (IIT)** should measure information integration

These are falsifiable. The ablation harness exists. Run each one and check.

## The Core Principle

**"Retrieval quality is dominated by the topology of the search space, not the algorithm traversing it."**

- Crates that DISCOVER existing structure help (collections, GNN, sparsifier)
- Crates that IMPOSE structure hurt (IIT, attn-mincut)
- Architecture changes (+17%) dominate algorithm changes (+5%)
- Don't build a better compass. Build a better map.

## DRIFT Connection

DRIFT (staged scaffold training) is geometric load management across training time.

| DRIFT stage | Training action | Geometric load equivalent |
|-------------|----------------|--------------------------|
| VOICE (peak 1/pi) | Burn identity into steep eigenvalues | Create high-lambda subspace first |
| STRUCTURE (peak 0.5) | Add operational patterns on voice | Add mid-lambda directions within committed subspace |
| CAPABILITIES (peak (pi-1)/pi) | Build skills on voice+structure | Fill remaining dimensions |
| BURN (peak pi/(pi+1)) | Destroy RLHF escape valley | Raise energy cost of old attractor |

## Test Harness

All on GitHub: `jordanschRGB/NaTASHA` branch `v2`
- `tests/benchmark_runner.py` — living ablation harness with algo registry, auto-logging
- `tests/benchmark_results.jsonl` — append-only log of every run
- To add a new algorithm: `@register_algo` decorator, 10 lines of Python.

## See Also
- [[eigen-framework-complete-architecture]]
- [[homestead-db-eieo]]
- [[rosetta-stone-layer-ordering-principle]]
- [[embedding-infrastructure-2026-03-31]]
