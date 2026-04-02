---
title: "EIEIO Spec vs New Opus Architecture — Comparison Report"
date: "2026-04-01"
author: "Claude Code (Sonnet 4.6)"
status: REVIEW
tags: [homestead, eieio, architecture, comparison, eigen]
related: [[homestead-db-eieio]], [[homestead-vault-self-heal]], [[ruvector-crate-atlas]], [[ruvector-self-organizing-plan]]
---

# EIEIO Spec vs New Opus Architecture — Comparison Report

**Purpose:** Determine whether to extend the existing EIEIO spec or write a new one.

**Sources read:**
- `/f/My Drive/eigen-vault/retrieval/homestead-db-eieio.md` — primary EIEIO spec
- `/f/My Drive/eigen-vault/retrieval/homestead-vault-self-heal.md` — vault self-heal design doc
- `/f/My Drive/eigen-vault/retrieval/ruvector-crate-atlas.md` — ablation results and crate catalog
- `/f/My Drive/eigen-vault/retrieval/ruvector-self-organizing-plan.md` — original March 16 build plan
- Notion: EIGEN Framework — Complete Architecture (336616ac-62ea-81f5)
- Notion: Why HOMESTEAD Matters (336616ac-62ea-811f)

---

## What the Existing EIEIO Spec Covers

### The Core Model (PROVEN, DEPLOYED)

EIEIO is built on the **EIGEN geometric load framework**. The four operations are fully specified and empirically validated:

| Operation | What | Result |
|-----------|------|--------|
| PLOW | Reshape topology — ruvector collections, domain separation | +17% over baseline |
| TILL | Read the grain — GNN K=3, boost=0.05, top=3, static KNN graph | +5% on top of PLOW |
| FENCE | Protect boundaries — effective resistance, coherence, boundary tension, ingest gate | Diagnostic only |
| HARVEST | Retrieve — collection-scoped query | 94% accuracy |

The spec has **15+ tests, 11 killed hypotheses, empirical benchmarks** on 26-92 chunks across 3 domains (bob/parakeet: 10, cuda: 8, historical: 8). This is not speculative — it's proven on deployed hardware.

**Infrastructure is deployed:**
```
PERPLEXAKEET (pplx-embed W8A8, 46,500 tok/s on NPU)
  → embed-proxy :6900
    → ruvector 2.1.0 at /opt/ruvector/collections
      → agent_knowledge (51 vectors), personal (3), corpus (38)
    → ingest gate (9 safety checks)
```

**The layer ordering principle is formalized:**
- L0: Vectors, cosine
- L1: Collections, GNN
- L2: Coherence, sparsifier (meta layer)
- L3: Sona, temporal-tensor (dynamics)
- Rule proven empirically: applying L2 to L0 (IIT on flat space) = poison (-17%)

### The Vault Self-Heal Design (DESIGN STATUS — not deployed)

The `homestead-vault-self-heal.md` doc extends the base spec with:
- Obsidian vault as the substrate (.md files on Google Drive)
- Vault watcher concept (ingest script walking vault .md files)
- Meta-collection: calibration surface storing confirmed/reverted link decisions
- Git-per-action with similarity scores in commit messages
- Human approval loop (Obsidian graph view → confirm or revert)
- Dynamic per-region thresholds replacing the static 0.5/0.7/0.7 cutoffs from the March 16 plan
- Dreamer batch script pattern (same NPU time-share, different input)

This doc explicitly maps vault operations to HOMESTEAD operations (PLOW/TILL/FENCE/HARVEST).

### What the March 16 Build Plan Already Proposed

The `ruvector-self-organizing-plan.md` (Step 6) proposed the self-organizing ingest pattern with static thresholds. The vault self-heal doc explicitly supersedes Step 6 with dynamic thresholds from the meta-collection.

### Known Gaps Listed in the Existing Spec

The existing EIEIO spec itself lists what it doesn't have:
1. Nightly cron ingest
2. rkllama systemd unit
3. Cross-collection queries (2 remaining misses)
4. SONA (learns from query patterns over time)
5. Scale testing (all results on 26-92 chunks, need 1000+)

---

## The New Opus Architecture — Layer by Layer

Opus proposed:

> The EIGEN vault IS the database. Every piece of data (knowledge, preferences, sessions, agent memories) lives as a .md file. Every file gets embedded into ruvector. Collections = folders. GNN reads both [[wiki-links]] (explicit edges) and embedding similarity (implicit edges). Preferences are vectors, not rules. Sessions get crystallized into vault nodes. Agent personas get persistent memory folders. Self-healing linker proposes [[links]] for orphans.

**Layer map:**
- **L0:** Vault watcher → embed pipeline → ruvector vectors
- **L1:** Collections = folders, GNN on wiki-links + similarity, self-healing linker
- **L2:** EIGEN vault as canonical truth, preferences as .md files (steerable vectors)
- **L3:** Session reader, agent memory folders, crystallization, temporal edges

---

## Comparison: What Matches

### Solid Matches (Existing spec already covers this)

| New Architecture Element | Existing Spec Coverage |
|--------------------------|------------------------|
| Vault watcher → embed pipeline → ruvector vectors | Specified in vault self-heal doc (ingest script item). Infrastructure (embed-proxy :6900) is deployed. Script is the missing piece. |
| Collections = folders | Deployed. ruvector 2.1.0 collections. +17% proven. |
| GNN on embedding similarity (implicit edges) | Deployed. TILL operation. K=3, boost=0.05, top=3 optimal config proven. |
| Self-healing linker for orphans | Specified in vault self-heal doc as "Dreamer batch script: query ruvector, apply modifiers, propose actions as git commits." |
| L0/L1/L2/L3 layer ordering | Formalized in EIGEN framework. Rosetta Stone layer ordering principle. Empirically enforced (L2 on L0 = poison proven). |
| Human approval loop | Specified in vault self-heal doc (git-per-action, confirm = keep, reject = revert). |
| Meta-collection as calibration surface | Specified in vault self-heal doc. The regional modifier system with confirmed/reverted decisions. |

### Partial Matches (Concept exists, implementation not specified)

| New Architecture Element | Gap |
|--------------------------|-----|
| GNN reads [[wiki-links]] as explicit edges | Existing spec has GNN on embedding similarity only (implicit). Wiki-links as explicit graph edges is NOT in the spec. This is new. |
| Preferences as .md files (steerable vectors) | Existing spec has a "personal" collection (3 vectors). Preferences as first-class steerable vectors — the idea that you edit the .md to steer behavior — is not specified. |
| Agent memory folders (persistent, per-agent) | Existing spec has agent_knowledge collection (51 vectors). Per-agent folder structure with persistent identity memory is not specified. |
| Temporal edges | ruvector-temporal-tensor is listed in the crate atlas as Tier 3. Not configured. No spec for how temporal edges work. |
| Session crystallization into vault nodes | Vault self-heal doc mentions "the Dreamer that reads sessions" as a parallel use of the Dreamer pattern. Full crystallization pipeline is not specified. |

---

## What's NEW in the Opus Architecture (Not in Existing Spec)

### 1. Wiki-Links as Explicit Graph Edges in GNN

The existing spec's GNN reads embedding similarity only. Opus adds wiki-links (`[[note-name]]`) as a second edge type — explicit human-curated connections feeding directly into the GNN alongside implicit cosine neighbors.

This is architecturally significant: the GNN would now operate on a **hybrid graph** (explicit + implicit edges) rather than a pure similarity graph. This has never been tested in the ablation harness. It could help (human curation is already what makes PLOW work) or it could hurt (parasitic edges are a documented failure mode — FENCE exists to detect them).

**Risk:** Wiki-links are not guaranteed to be semantically meaningful. A link added for navigation convenience might become a parasitic GNN edge. Needs an ablation test.

### 2. Vault as the Canonical Database (Inversion of Architecture)

The existing spec has ruvector as the canonical store. Obsidian vault is the human-facing interface, and the self-heal system syncs FROM ruvector decisions back TO the vault.

The new architecture inverts this: **the vault IS the database**. The .md files are canonical. ruvector is the index, not the source of truth.

This is a meaningful architectural shift. In the existing spec, if a link is added to the vault, ruvector doesn't know unless it's re-ingested. In the new architecture, the vault is the write surface and ruvector is a derived view.

**Implication:** Vault watcher must run continuously (or on commit hooks) to keep ruvector in sync. This is closer to an event-driven architecture than the nightly cron pattern in the existing spec.

### 3. Preferences as Steerable Vectors

The existing spec stores preferences in a "personal" collection. The new architecture treats preference .md files as the control interface: editing the file steers behavior because re-embedding the file changes the vector the agents query against.

This is a novel UX pattern — prose-editable behavior steering. It works IF the embedding model is sensitive enough to preference changes. With PERPLEXAKEET at 1024 dims and proven within-domain separation, this is plausible. Not tested.

### 4. Agent Memory Folders with Persistent Persona Identity

The existing spec has a unified agent_knowledge collection. The new architecture proposes per-agent memory folders — each agent has its own vault folder that becomes its episodic and semantic memory.

This requires:
- Folder-per-agent collection structure in ruvector (extension of existing collections model)
- Ingest pipeline that tags vectors with agent identity
- Cross-agent queries need to span collections (currently the 2 remaining misses in HARVEST are cross-domain — same problem)

**The cross-collection query gap in the existing spec (listed item #3 in "What EIEIO Doesn't Have") becomes a blocker for this feature.**

### 5. Session Crystallization

Sessions get converted into vault nodes that persist beyond the session lifetime. This is not specified anywhere in the existing docs beyond the Dreamer pattern mention. No schema, no format, no trigger condition.

The March 16 build plan (Step 7) has a "runtime context hook" that pulls context at session start — the inverse direction. Crystallization (session → vault) is not specified.

### 6. Temporal Edges

The new architecture adds temporal edges at L3. The existing spec lists ruvector-temporal-tensor as Tier 3 infrastructure (exists, not configured). No spec for what temporal edges mean: time-of-creation? time-of-access? decay function? cross-session chronology?

---

## Conflicts Between Existing Spec and New Architecture

### Conflict 1: GNN Edge Source

- **Existing spec:** GNN reads embedding similarity (cosine K-nearest neighbors). Proven: K=3, boost=0.05, top=3.
- **New architecture:** GNN also reads wiki-links as explicit edges.
- **Conflict type:** Additive extension, but the proven GNN params were calibrated on pure cosine neighborhoods. Adding explicit edges changes the graph structure. The optimal params (K, boost) may need retuning.
- **Resolution:** Ablation test. Run the existing harness with wiki-links as additional edges. Check whether +explicit edges helps or introduces parasitic connections.

### Conflict 2: Canonical Truth (Vault vs ruvector)

- **Existing spec:** ruvector is the operational database. The vault self-heal system proposes changes to the vault via git commits.
- **New architecture:** Vault .md files are canonical. ruvector is a derived index.
- **Conflict type:** Architectural inversion.
- **Resolution:** This is a genuine design decision that needs a call. The existing spec's approach (ruvector as source of truth, vault as view) is more operationally safe — ruvector has snapshots, a 9-check ingest gate, and is fully versioned. The new architecture's approach (vault as source of truth) is more human-friendly and aligns with how Jordan actually works (editing .md files in Obsidian). The git-per-action pattern in the vault self-heal doc partially bridges this — the vault IS versioned. But a corrupted vault corrupts the index. With ruvector as canonical, a corrupted vault only corrupts the UI.

### Conflict 3: Threshold Model

- **March 16 plan (Step 6):** Static cutoffs — 0.7 assign, 0.5-0.7 borderline, <0.5 new category.
- **Vault self-heal doc:** Meta-collection replaces static thresholds with learned per-region thresholds. This supersedes Step 6 explicitly.
- **New architecture:** Does not address thresholds directly. Implicitly assumes self-healing linker proposes links (agrees with meta-collection model).
- **Conflict type:** None with new architecture. The vault self-heal doc already won this argument against the March 16 plan.

### Conflict 4: Data Type of Preferences

- **Existing spec:** Preferences in "personal" collection as embedded chunks, same model as everything else.
- **New architecture:** Preferences as .md files that are specifically steerable — the file IS the control.
- **Conflict type:** The existing collection model stores preferences as read-only knowledge. The new model makes preferences writable-by-editing. These aren't mutually exclusive but the spec doesn't account for the write path (edit .md → re-embed → collection updates).
- **Resolution:** Requires a preference watcher pattern: monitor preference .md files for changes, trigger selective re-embedding, update ruvector vector for that document. Not currently in any spec.

---

## Verdict: Extend or Rewrite?

**Extend the existing spec.** The existing EIEIO spec is not wrong — it's proven, deployed, and empirically validated. The new Opus architecture is the next layer on top of a solid foundation.

The existing spec covers L0 (embed pipeline) and L1 (collections + GNN) completely. The vault self-heal doc already specified much of what Opus is proposing for the human-facing layer. What's genuinely new is:

1. Wiki-links as explicit GNN edges — needs ablation, then add to TILL spec
2. Vault-as-canonical inversion — needs a design decision, then resolve Conflict 2
3. Per-agent memory folders — extends existing collections model, blocked on cross-collection queries
4. Session crystallization — needs schema spec, ingest trigger, format
5. Preference watcher — needs write path spec (edit → re-embed → update)
6. Temporal edges — needs definition before implementation

**Recommended action:**
- Keep `homestead-db-eieio.md` as the PROVEN DEPLOYED baseline (do not modify)
- Keep `homestead-vault-self-heal.md` as the DESIGN layer (L2 + feedback loop)
- Create a new spec: `homestead-extended-architecture.md` covering items 1-6 above
- Items 1 and 2 need architectural decisions before specs. Flag for Opus review.
- Items 3-6 are additive extensions — can be specced now, blocked on cross-collection queries for item 3.

---

## What to Build Next (Priority Order)

Based on existing spec gaps + new architecture delta:

| Priority | Item | Status | Blocker |
|----------|------|--------|---------|
| 1 | Nightly cron ingest (vault .md → ruvector) | Not built | None — ingest gate + embed-proxy already deployed |
| 2 | Ablation: wiki-links as GNN edges | Not tested | Needs test harness run |
| 3 | Preference watcher (edit .md → re-embed) | Not built | Cron ingest first |
| 4 | Session crystallization schema + trigger | Not specced | Schema decision needed |
| 5 | Cross-collection queries | Not built | Needed for per-agent memory folders |
| 6 | Per-agent memory folders | Not built | Cross-collection queries first |
| 7 | Temporal edges config | Not configured | temporal-tensor crate exists, needs schema |
| 8 | Scale testing at 1000+ chunks | Not done | Cron ingest first (to get more vectors) |
| 9 | SONA activation | Not deployed | Needs live traffic (1000+ queries) |

---

*Report generated: 2026-04-01*
*Sources: 4 vault files + 2 Notion pages*
*Decision pending: Conflict 2 (vault vs ruvector canonical truth)*

---

## Conflict Resolutions

*Resolved: 2026-04-02*

### Resolution 1: GNN Edge Sources

**Decision:** Vault wikilinks are primary edges. Embedding similarity is secondary/candidate edges. Both feed the GNN, but wikilinks get higher weight.

**Reasoning:** Wikilinks are human-authored connections — they represent verified intent, not statistical proximity. They are already part of the human approval loop design (git-per-action, confirm/revert). Embedding similarity is useful for discovering candidate edges the human hasn't created yet, but it cannot override an explicit human choice. In GNN terms: wikilink edges are trusted; similarity edges are proposed.

**Implementation note:** The existing K=3, boost=0.05, top=3 params were tuned on a pure cosine graph. Adding wikilink edges changes the graph topology. Ablation is still required before shipping — but the weighting hierarchy is settled: wikilinks win ties, similarity fills gaps.

**Layer:** L1 (TILL operation extension).

---

### Resolution 2: Canonical Truth Location

**Decision:** The vault (markdown files) is canonical truth. RuVector is a derived index. If they disagree, vault wins.

**Reasoning:** The vault can be rebuilt from scratch into RuVector at any time — the embed pipeline is the reconstruction path. RuVector cannot be rebuilt into a vault; it contains vectors, not human-readable documents with structure, metadata, and wikilinks. Canonical truth must live in the thing that is not reconstructable. The vault is that thing.

**Corollary:** A corrupted vault is a real emergency. A corrupted RuVector is a rebuild job. Design accordingly — vault gets the same care as production data: git versioning, backup, no destructive writes without a commit.

**Operational consequence:** The vault watcher is not optional infrastructure. It is the sync path between canonical truth (vault) and the query index (RuVector). Staleness in RuVector is tolerable; staleness in the vault is data loss.

**Supersedes:** The existing spec's framing of ruvector as the operational database. That framing made sense before the vault self-heal design was added. It no longer reflects the architecture.

---

### Resolution 3: Threshold Models

**Decision:** Start with static global thresholds. Dynamic per-region thresholds from the meta-collection are an L2 extension, implemented only after the static system is proven.

**Reasoning:** This is a direct application of Rosetta Stone layer ordering — L0 before L1 before L2, no skipping. Static thresholds (0.7 assign, 0.5-0.7 borderline, <0.5 new category) are simple, inspectable, and debuggable. Dynamic thresholds depend on a functioning meta-collection, which depends on a functioning ingest pipeline, which depends on a static threshold system to generate the confirmed/reverted decisions the meta-collection learns from.

**Build order enforced:** Static thresholds ship in the nightly cron ingest (Priority 1). Meta-collection dynamic thresholds are blocked until the static system has generated enough confirmed/reverted decisions to train against. Attempting to skip this produces the same failure mode as running IIT on flat vector space — you're applying an L2 mechanism to an L0 substrate.

**The vault self-heal doc's framing** ("dynamic thresholds supersede Step 6") is correct about the eventual state. It is not a license to skip static thresholds on the way there.

---

### Resolution 4: Data Type of Preferences

**Decision:** Store preferences as structured key-value pairs in frontmatter, not as free-text embeddings.

**Reasoning:** Embeddings capture semantic similarity — they are the right tool for "find things like this." Preferences require exact recall — "always use metric units," "never suggest X," "respond in style Y." A preference stored as an embedding can be retrieved approximately. A preference stored as a frontmatter key-value pair is retrieved exactly, every time, with zero drift.

**The Opus proposal** (preferences as steerable vectors you edit to change behavior) is architecturally interesting but conflates two different retrieval needs. Semantic steering via embeddings works for knowledge retrieval. It is unreliable for behavioral constraints, which need deterministic lookup.

**Practical format:**
```yaml
---
preference_key: response_style
value: concise
scope: global
---
```

The preference .md file can still be embedded for semantic search purposes — but the authoritative value is always read from frontmatter, not inferred from the vector. Embedding captures the prose explanation; frontmatter carries the executable rule.

**Layer:** L0/L1 boundary — frontmatter parsing happens at ingest, before embedding. The structure must be established at L0 or it cannot be depended on at L1+.
