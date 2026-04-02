---
title: "Honcho vs Build — Agent Memory Architecture Comparison"
date: "2026-04-01"
tags: [architecture, memory, honcho, ruvector, tain, agent]
status: DECISION
related: [[honcho-ai-memory-framework]], [[dreamer-observer-model]], [[rosetta-stone-layer-ordering-principle]], [[why-homestead-matters]], [[ruvector-crate-atlas]]
---

# Honcho vs Build — Agent Memory Architecture Comparison

> **Bottom line up front:** Hybrid. Honcho is not the right L3 either — we're already building a better one (Dreamer Observer). Use ruvector for L1, Dreamer for L3, EIGEN vault for L2. Honcho is worth watching but not worth running.

---

## The Capability Matrix

| Capability | Honcho Gives Free | We'd Have to Build | Already Have |
|---|---|---|---|
| **Session continuity** | Native. `session.context(tokens=N)` with token budget. Cross-session by default. | Wire it into TAIN CLI startup | SessionLogger writes JSONL per session. Context not injected back yet — that's the gap. |
| **User modeling** | Native via Neuromancer background workers. Peer Cards (40-fact deduped snapshot). Deductive + inductive + abductive reasoning per message. | The whole annotation + DPO + DRIFT pipeline for Dreamer | crystallize.py exists but is a stub — keyword matching for "decision:" prefixes, not reasoning. |
| **Metamemory** | Partial. Honcho knows what it extracted; doesn't explicitly model "what I don't know." | Explicit gap-tracking layer | Not present anywhere yet. |
| **Cross-agent memory sharing** | Native. All agents are Peers in same workspace. Agent A's observations feed shared user representation automatically. | A shared ruvector collection + routing conventions | ruvector has collections but no agent-to-agent share protocol. Manual plumbing needed. |
| **Memory decay** | No native decay. Consolidation removes contradictions but doesn't time-weight. | Time-weighted scoring layer on top of ruvector | Not present. ruvector retrieval is static cosine + GNN rank. |
| **Semantic search over memories** | Native. Hybrid text + semantic search over Collections. ~50ms. | Already solved | ruvector with collections + GNN. 94% retrieval accuracy. Faster than Honcho's ~200ms chat endpoint. |
| **Memory consolidation** | Background Dreaming workers. Async, no runtime cost. Removes contradictions, deduplicates Peer Cards. | Dreamer Observer batch job (planned, NPU time-share) | Nightly review pass exists as a prompted pattern. Dreamer is PLANNING stage. |
| **Collection topology** | Primitive. Documents live in Collections but topology is flat — no GNN, no layer ordering, no collection-scoped search geometry. | Already solved — don't replace it | ruvector Collections + GNN. L1 structure layer. +17-28% retrieval vs flat. This is the core HOMESTEAD advantage. |
| **GNN-ranked retrieval** | Not present. Honcho retrieval is similarity + hybrid text, no graph structure. | Already solved | ruvector GNN crate. Static GNN K=3 b=0.05 top=3 = 94% accuracy. |
| **Human-readable audit** | No. PostgreSQL rows. Not browsable without tooling. | EIGEN vault already solves this | EIGEN vault (Obsidian). Every memory has a markdown file a human can open, read, edit, and wiki-link. L2 governance layer. |
| **Training data export** | No native export. Messages are stored; no built-in HF format or DRIFT-ready pipeline. | dataclaw.py already exists | dataclaw.py exports JSONL sessions to HuggingFace format. Works today. |
| **Self-healing** | No self-healing of knowledge gaps. Consolidation removes contradictions but doesn't detect and fill gaps. | Future Dreamer capability — "what should I know that I don't" | Not present. Nightly review pass is the closest thing. |

---

## The Real Capability Gap

Only two capabilities are genuinely missing and not covered by anything we have:

1. **Session context injection** — SessionLogger writes sessions, but TAIN CLI doesn't read them back at startup. The loop is broken. This is a few hours of plumbing, not a new system.

2. **User modeling / observation reasoning** — crystallize.py is a keyword stub, not a reasoner. The plan is Dreamer Observer. Honcho's Neuromancer is the commercial equivalent. We're building our own with DRIFT on our own session logs.

Everything else either already exists in better form (semantic search, collection topology, GNN, human audit, training export) or isn't worth building yet (memory decay, metamemory, self-healing).

---

## Rock 5B Feasibility: Running Honcho + ruvector + rkllama + gateway

Current Rock 5B memory baseline (approximate):
- openclaw gateway: ~300MB
- ruvector: ~150MB
- rkllama (Qwen3-VL-2B): ~2.5GB active
- openclaw-pairing: ~200MB per instance
- kokoro-tts, monit, SearXNG, mcp-searxng-native, itr8: ~400MB combined
- OS + kernel buffers: ~1.5GB

**Approximate idle baseline: ~5GB used, 11GB available**

Honcho adds:
- PostgreSQL 15 + pgvector: ~500MB–1.5GB depending on dataset size
- FastAPI server: ~200MB
- Deriver background worker: ~500MB–1.5GB depending on reasoning load (calls an LLM API)
- Redis (optional): ~100MB

**Honcho total: 1.3–3.3GB**

**Verdict: Technically fits, but the Deriver worker calls an external LLM API for every reasoning pass.** That's Anthropic/OpenAI/Gemini billing per observation. Not free. The Rock doesn't do the reasoning — it just stores the results. You're paying per session observation, same as the managed service, just hosting PostgreSQL yourself. That's not cost-effective unless you route Deriver through rkllama, which requires testing and likely degrades quality significantly.

**Additional risk:** The Deriver is a long-running background process that hits an LLM API. Add that to the OOM risk profile. Rock already had an OOM cascade when Next.js + Chrome + parallel agents co-occurred. Honcho's Deriver is another concurrent LLM call process on an already busy box.

---

## Integration Complexity: Wiring Honcho into TAIN CLI

Honcho integration requires:
1. Add `honcho-ai` Python SDK to dependencies
2. On session start: create or resume a Peer for the user + Peer for TAIN
3. After each turn: call `session.add_messages()` — triggers Deriver async
4. Before each LLM call: inject `session.context(tokens=2000)` or call `peer.chat()` for synthesis
5. Handle Honcho being unreachable (it's another network service)

Rough estimate: 2–3 days to integrate cleanly, handle errors, test across sessions.

Compare to the alternative:
- Session context injection into TAIN: ~4 hours (read last N sessions from `~/.tain/sessions/`, inject as context prefix)
- Dreamer Observer annotation: separate offline batch job, not on the hot path

**The integration tax for Honcho buys you Neuromancer reasoning.** That reasoning is the one thing we don't have today. But we're building Dreamer Observer to replace it, on our own hardware, with our own training data, at zero marginal cost. Honcho accelerates getting to L3 dynamics today at the cost of ongoing API billing + 2–3 days integration + new service dependency.

---

## The Hybrid Option: Honcho for L3, ruvector for L1

Mapping to the Rosetta Stone layer model:

| Layer | What it covers | Current system | Honcho | Conflict? |
|---|---|---|---|---|
| L0: Substrate | Vectors, cosine, HNSW | ruvector sqlite-vec | PostgreSQL + pgvector | Parallel, not conflicting. Different stores. |
| L1: Structure | Collections, GNN, topology | ruvector collections + GNN | Flat document collections, no GNN | Honcho's L1 is weaker than ours. No conflict — don't replace. |
| L2: Meta/Governance | Human-readable, auditable, editable | EIGEN vault (Obsidian) | PostgreSQL rows, no audit trail | Honcho doesn't touch L2. No conflict. |
| L3: Dynamics | Agent state across sessions, user modeling | MISSING (gap) | Neuromancer + Peer Cards + Dreaming | Honcho fills the gap today. Dreamer Observer fills it later. |

The hybrid is theoretically clean: Honcho owns L3 (session state, peer modeling, cross-session continuity) while ruvector owns L1 (retrieval topology, collection scoping, GNN ranking). They don't step on each other.

**But the hybrid creates two problems:**

1. **Double storage.** Session messages go into both Honcho (for reasoning) and SessionLogger/ruvector (for retrieval + training export). Sync complexity, potential divergence.

2. **The Deriver LLM dependency.** Honcho's L3 value comes from Neuromancer reasoning, which requires calling an LLM API on every observation pass. Self-hosting PostgreSQL doesn't remove this cost — it just removes the hosting fee. You still pay per reasoning call unless you route through a local model, which degrades quality and needs testing.

---

## Decision Framework

Three paths:

**Path A: Adopt Honcho (managed or self-hosted)**
- Get L3 today, no custom training required
- Cost: $2/M ingestion tokens + ongoing API billing for Deriver reasoning
- Risk: new service dependency, OOM risk on Rock, integration work
- Payoff: skip 4–8 weeks of Dreamer Observer build time

**Path B: Build (current plan)**
- Session context injection: ~4 hours, closes the worst gap immediately
- Dreamer Observer: 4–8 weeks to train, test, deploy on NPU
- Cost: zero marginal after training
- Risk: training data quality, time investment
- Payoff: own model, own data, runs on NPU at zero cost per inference, training data is ours

**Path C: Hybrid (Honcho for bridge, Dreamer for production)**
- Use managed Honcho as a temporary L3 while Dreamer is built
- Migrate to Dreamer when it's ready
- Complexity: two integrations, one migration
- Only makes sense if the 4–8 week gap is genuinely painful

---

## Recommendation

**Build. Path B. Close the session context gap immediately, build Dreamer on schedule.**

The reasoning:

1. **Honcho's actual moat is Neuromancer.** The rest (PostgreSQL, vector search, session storage) is infrastructure we already have in better form. Neuromancer is a small trained model with a peer-frame observer bias. We reverse-engineered what it is. We're building the equivalent with DRIFT on our own data. That's a better moat — our data is more domain-specific than generic user-AI conversations.

2. **The worst gap is context injection, not reasoning.** TAIN writes sessions but doesn't read them back. Fix that first. It's 4 hours, not 4 weeks. Agents get cross-session continuity immediately without adding any dependency.

3. **Honcho on Rock is not free.** Self-hosting moves the PostgreSQL bill ($0, we can do that) but not the Deriver API bill. Every background reasoning pass calls an LLM. That's ongoing cost that scales with session volume, plus OOM risk on a box that already has too many concurrent processes.

4. **Hybrid introduces sync complexity we don't need.** Two session stores, two retrieval paths, one migration. The transition cost probably exceeds the gap it fills.

5. **The L1 advantage is ours.** Honcho's retrieval is flat similarity. Ours is 94% with GNN-ranked collection-scoped search. Replacing it with Honcho would be a regression.

**If the Dreamer Observer build stalls for more than 8 weeks, revisit Honcho managed service as a bridge.** At that point the integration cost amortizes against a real timeline slippage, not a planning estimate.

---

## Immediate Actions

1. Wire session context injection into TAIN CLI startup — read last N session files from `~/.tain/sessions/`, inject as context prefix. Closes the biggest gap today.

2. Define Dreamer Observer training data schema (what the annotation prompt extracts, in what structured format).

3. Leave Honcho on the watchlist. Their evals (LongMem S: 90.4%, LoCoMo: 89.9%) are real benchmarks. If Dreamer underperforms on eval, Honcho managed is a credible fallback for the reasoning layer only.

---

## Summary Table

| Factor | Honcho | Build |
|---|---|---|
| Time to L3 | Days (integration) | 4–8 weeks (Dreamer training) |
| Ongoing cost | API billing per reasoning pass | Zero marginal after training |
| Retrieval quality | Weaker than ruvector (flat similarity) | 94% (GNN + collections) |
| Human audit | No (PostgreSQL rows) | Yes (EIGEN vault, Obsidian) |
| Training export | No built-in pipeline | dataclaw.py exists today |
| Rock 5B OOM risk | Adds ~2–3GB + Deriver process | Session injection: near zero |
| Data ownership | Plastic Labs stores your sessions (managed) | Ours, always |
| Domain fit | Generic user-AI | Our sessions, our patterns |
| Architecture fit | L3 only, weak at L1 | Full stack, strong at L1 |

**Honcho is a well-designed system solving the right problem.** The peer-frame observer concept is correct. The Neuromancer bet is sound. If you were starting from scratch with no ruvector, no HOMESTEAD, no DRIFT methodology — use Honcho.

We're not starting from scratch. L0, L1, L2 are solved. The L3 gap is real but closeable with targeted work. Building Dreamer Observer is compression: 10 sessions → 1 structured user model, running on hardware we own, on training data that encodes exactly the patterns we care about.

That's better than renting someone else's trained observer for our sessions.

---

*Generated: 2026-04-01 | Author: Guppi (Claude Code, Sonnet 4.6)*
