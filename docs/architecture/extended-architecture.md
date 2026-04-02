---
title: "HOMESTEAD Extended Architecture — Six Extensions to EIEIO"
date: "2026-04-01"
author: "Claude Code (Sonnet 4.6)"
status: SPEC
tags: [homestead, eieio, architecture, eigen, vault, gnn, crystallization, preferences, agents]
related: [[homestead-db-eieio]], [[ruvector-crate-atlas]], [[rosetta-stone-layer-ordering-principle]], [[honcho-vs-build-comparison]], [[self-healing-vault-feasibility]]
---

# HOMESTEAD Extended Architecture — Six Extensions to EIEIO

**This document extends [[homestead-db-eieio]]. It does NOT replace it.**

The proven baseline is frozen: K=3, boost=0.05, 94% accuracy. Nothing in this document touches those parameters until an ablation says otherwise. If there is ever a conflict between this document and `homestead-db-eieio.md`, the baseline wins.

---

## Architectural Decision (Resolved)

**Vault is canonical for writes. ruvector is canonical for reads.**

Humans and agents write `.md` files to the EIGEN vault (Obsidian on Google Drive). ruvector indexes them. If they ever diverge, vault wins — re-embed and re-index from vault. ruvector is a read cache of the vault's truth.

This resolves Conflict 2 from the comparison report. The reasoning:

- Jordan actually works in Obsidian. The vault is the natural write surface.
- Git-per-action (already in the vault self-heal design) provides versioning. The vault is not less safe than ruvector — it's differently versioned.
- ruvector snapshots protect against corrupted indexes. A corrupted vault is a Git problem (revert the commit).
- The ingest gate's 9 safety checks run on write-to-ruvector, not on write-to-vault. The gate stays. It just fires from the watcher, not a manual trigger.

**Consequence for operations:**

```
WRITE PATH:  human/agent → vault .md → watcher detects → embed → ingest gate → ruvector
READ PATH:   query → ruvector → GNN → HARVEST result

DIVERGENCE:  ruvector out of sync → re-run watcher → re-embed from vault
             vault out of sync    → git revert → re-run watcher
```

ruvector never directly receives writes from anything except the embed pipeline. The vault is the only write surface.

---

## Extension 1: Wiki-Links as GNN Edges

**Status: REQUIRES ABLATION BEFORE DEPLOY**

### What

`[[wiki-links]]` in `.md` files become explicit edges in the GNN graph, alongside the existing cosine similarity edges from TILL. The GNN would operate on a hybrid graph: explicit human-curated connections + implicit embedding neighbors.

### Why

PLOW works because human curation (collection structure) outperforms algorithm-only approaches (+17%). Wiki-links are another form of human curation — a direct assertion that two nodes are related. If curation signal is what makes PLOW work, more curation signal fed into TILL might push beyond 94%.

### Risk

The existing K=3, boost=0.05 params were calibrated on a pure cosine neighborhood. Adding explicit edges changes the graph structure without retuning. Two failure modes:

1. **Parasitic edges**: Links added for navigation convenience (not semantic meaning) become noise in the GNN. FENCE detects parasitic edges — it doesn't prevent them at write time.
2. **Param drift**: Optimal K and boost may shift when the neighborhood includes explicit edges. Running the old params on the new graph may hurt before it helps.

### Test Plan (before any deploy)

1. Parse all `[[wiki-links]]` from vault `.md` files. Build an explicit edge list.
2. Load the existing HOMESTEAD benchmark (26 test queries, 3 domains).
3. Run benchmark with GNN on **cosine only** (current baseline). Confirm 94%.
4. Add wiki-link edges to GNN graph. Run benchmark again with same K=3, boost=0.05.
5. If score drops: wiki-links are parasitic at current params. Try K=2 or boost=0.03. Document findings.
6. If score holds or improves: wiki-links are safe. Update TILL spec with hybrid edge model.
7. Commit results to ablation log before any code ships.

### If Ablation Passes

The TILL section of `homestead-db-eieio.md` would gain a note (do not modify the baseline doc — add an addendum). The hybrid GNN becomes the new default. The vault watcher (Extension 2) would extract wiki-links during ingest and write them as explicit edges to ruvector's graph layer.

### EIGEN Layer

L1 — this is a TILL operation. The GNN reads grain; wiki-links are more grain.

---

## Extension 2: Vault Watcher → Embed Pipeline

**Status: READY TO BUILD (no blockers)**

### What

A daemon watches the vault directory for `.md` file changes. On change: embed the file content → upsert into ruvector → collection = parent folder name.

### Architecture

```
[Obsidian / Google Drive sync]
        |
        | file change (create, modify, delete)
        v
[vault-watcher daemon]
        |
        | POST /embed with file content
        v
[embed-proxy :6900]
        |
        | dim=1024 validated, NPU enforced
        v
[ingest gate — 9 safety checks]
        |
        | passes gate
        v
[ruvector upsert — collection = parent folder]
```

### Implementation Notes

- Extends existing `embed_ingest.py` (Rock port 8082). Don't rewrite — extend.
- Watch trigger: `inotifywait` on Linux (Rock), file system events on other platforms.
- Collection mapping: `eigen-vault/retrieval/` → `retrieval`, `eigen-vault/architecture/` → `architecture`, etc. The folder IS the collection name.
- On delete: mark vector as deleted in ruvector (soft delete, not hard drop, until tested).
- On rename: delete old path vector, ingest new path.
- Batch mode: on startup, walk all vault `.md` files and upsert anything newer than the ruvector collection's last-modified timestamp. This handles offline edits.

### Startup Sequence

```
1. watcher starts
2. walk vault: for each .md, compare mtime to ruvector record
3. embed any file where mtime > last_ingested_at
4. enter watch loop
5. on file event: embed + upsert
```

### EIGEN Layer

L0 — this is the pipe that fills the vector space. Pure infrastructure. No GNN, no FENCE, just embed → store.

---

## Extension 3: Per-Agent Memory Folders

**Status: SPECCED — BLOCKED ON CROSS-COLLECTION QUERIES**

### What

`eigen-vault/agents/<name>/` — each agent persona gets persistent `.md` files. The agent's folder is its episodic and semantic memory. It reads from its collection on dispatch. It writes crystallized results to its folder on completion.

### Folder Structure

```
eigen-vault/
  agents/
    natasha/
      session-2026-03-29-telecom-outage.md
      preference-directness.md
      knowledge-openai-token-rotation.md
    forge/
      session-2026-03-31-rkllama-debug.md
      knowledge-rknpu-conversion-pipeline.md
    guppi/
      knowledge-homestead-architecture.md
      session-2026-04-01-eigen-vault-spec.md
```

### Dispatch Pattern

```
1. Agent receives task
2. Query agent's ruvector collection with task embedding
3. Top-K relevant memories returned
4. Inject as context: "You have these relevant memories from prior work: ..."
5. Agent executes task
6. On completion: crystallize.py extracts decisions, files modified, key insights
7. Crystal written to eigen-vault/agents/<name>/ as .md
8. Vault watcher picks it up → embed → ruvector collection for that agent
```

### Blocker

Cross-collection queries. The 2 remaining misses in HOMESTEAD are cross-domain queries. Per-agent memory requires a query that spans: (1) the agent's own collection, and (2) the shared knowledge collections. This is the same unsolved problem. Until ruvector supports cross-collection queries natively, agents are limited to querying their own folder only.

**Workaround (until cross-collection queries land):** Run two queries at dispatch time — one against the agent's collection, one against the relevant domain collection — merge results in the caller. Ugly but functional.

### EIGEN Layer

L3 — agent memory is temporal and persona-specific. It depends on L0 (embed pipeline) and L1 (collection structure) being stable first.

---

## Extension 4: Session Crystallization

**Status: IMPLEMENTATION READY — crystallize.py EXISTS (built by Gastown swarm)**

### What

Session ends → `crystallize.py` extracts what happened → crystal written as `.md` to `eigen-vault/claude-sessions/` → vault watcher picks it up → next session reads recent crystals at startup.

### Crystal Schema

```yaml
---
session_id: "2026-04-01-homestead-extended-spec"
date: "2026-04-01"
agent: "claude-sonnet-4-6"
duration_minutes: ~40
files_modified:
  - "/f/My Drive/eigen-vault/architecture/homestead-extended-architecture.md"
tools_used: [Read, Write, Edit, Grep]
decisions:
  - "Vault canonical for writes, ruvector canonical for reads"
  - "Wiki-links require ablation before GNN integration"
  - "Extension 3 blocked on cross-collection queries"
key_insights:
  - "Extension 2 has no blockers — should be first build"
  - "crystallize.py already exists from Gastown swarm"
tags: [homestead, eigen, architecture]
---

# Session Crystal — HOMESTEAD Extended Architecture

[prose summary of what happened, what was learned, what was left open]
```

### Startup Injection

At session start, TAIN reads recent crystals from `eigen-vault/claude-sessions/`. How many is "recent" is tunable. Start with 5 most recent, indexed by date.

Two retrieval modes:
1. **Recency**: the 5 most recent crystals regardless of topic
2. **Relevance**: embed the session's first message, query crystals collection for top-K matches

Relevance mode is better but requires the crystals collection to exist in ruvector first. Start with recency, migrate to relevance once crystals are indexed.

### EIGEN Layer

L3 — temporal continuity. Session crystals are nodes in the temporal graph. This depends on L0 (watcher), L1 (collections), and the crystallize.py script being wired into the session teardown hook.

---

## Extension 5: Preferences as Vectors

**Status: READY TO BUILD — new UX pattern, no blockers**

### What

`eigen-vault/preferences/` folder with `.md` files — one per behavioral preference. Each preference gets embedded into a `preferences` ruvector collection. At generation time: embed the task description → find nearest preferences → inject as soft constraints.

### Preference File Format

```markdown
---
title: "tone-dry-humor"
tags: [preference, tone, communication]
weight: 0.8
---

# Dry Humor

Dry, deadpan delivery. No enthusiasm inflation. Understatement over exclamation.
The joke is in the restraint. If something is funny, the reader should arrive there
without a signpost. Never explain the joke.
```

### Write Path

```
Jordan opens Obsidian
  → edits eigen-vault/preferences/tone-dry-humor.md
    → vault watcher fires
      → embed-proxy: embed new content
        → ruvector upsert: preferences collection updated
```

The behavior change is live on the next generation call. Human-editable. No code deploy.

### Read Path

```
task arrives
  → embed task description
    → query preferences collection (top-K, K=3 default)
      → inject top preferences as context constraints
        → generation proceeds with behavioral steering
```

### DRIFT Connection

This is DRIFT voice steering applied to inference-time preferences. DRIFT modifies weights at training time. Preferences-as-vectors modify the context at inference time. Same principle: the constraint IS the product. The difference is latency — DRIFT changes are permanent; preference vectors change on the next query.

**Human-editable inference steering** is the novel UX pattern. Jordan edits prose in Obsidian. The system embeds it. The embedding becomes the behavioral constraint. No prompt engineering. No config files. No restarts.

### Ablation Note

The preference injection must not dilute the task context. Monitor for cases where injected preferences push relevant task knowledge out of the context window. Start with short preference files (< 200 words each). Measure output quality before and after preference injection with 10 test tasks.

### EIGEN Layer

L2 — preferences are a meta-layer. They modulate how the retrieval result is used, not the retrieval itself. In EIGEN terms: preference vectors adjust the gain on the output projection.

---

## Extension 6: Self-Healing Linker

**Status: SPECCED — 127 current orphans are first test dataset**

### What

A periodic process that identifies vault nodes with fewer than 2 inbound links, finds their most similar neighbors, and proposes `[[wiki-links]]` — either auto-accepting above a cosine threshold or queuing for human review.

### Algorithm

```
1. Build link graph from all [[wiki-links]] in vault
2. Identify nodes with inbound_link_count < 2  (orphans)
3. For each orphan:
   a. Query ruvector with orphan's embedding
   b. Retrieve top-5 most similar nodes (excluding existing links)
   c. For each candidate:
      - cosine > 0.85: auto-accept → add [[link]] to orphan's .md file
      - cosine 0.65–0.85: queue for human review
      - cosine < 0.65: skip
4. Auto-accepted links: git commit with similarity score in message
5. Review queue: surface in Obsidian or log file
```

### Thresholds

The 0.85 auto-accept threshold is a starting point, not a law. The existing vault self-heal design specifies a meta-collection that learns per-region thresholds from confirmed/reverted decisions. Use static thresholds for the first run. After 20+ human-reviewed decisions, train per-region thresholds from the meta-collection.

**Do not skip the meta-collection design.** Static thresholds will decay as the vault grows. The meta-collection IS the long-term calibration system.

### Parasitic Edge Risk

Auto-accepted links become GNN edges (per Extension 1, after ablation). A bad auto-accept creates a parasitic edge. FENCE (effective resistance, ruQu boundary tension) will flag it — but FENCE is diagnostic, not preventive. Two mitigations:

1. Keep the auto-accept threshold high (0.85+). At that similarity, semantic meaning is almost always genuine.
2. Log all auto-accepts with similarity scores. The git history IS the audit trail.

### First Run

The 127 current orphans are the test dataset. Run with auto-accept threshold = 0.90 (conservative). Review the resulting git diff manually before committing. Validate that the proposed links make sense. Lower threshold after the first run if coverage is too low.

### Trigger

- On new file addition (immediate run for the new file only)
- Nightly batch (full orphan scan)

Do not run on every vault watcher event — too expensive. File addition + nightly is the right cadence.

### EIGEN Layer

L1 — self-healing linker operates on graph topology (PLOW/TILL territory). It densifies the link graph, which improves GNN neighborhood quality. This is topology maintenance.

---

## Extension 7: Git Diff Ingestion

**Layer:** L0 (substrate) + L3 (dynamics)

Every git commit across tracked repos becomes a vault node:
- File: `eigen-vault/git-diffs/<repo>/<date>-<short-hash>.md`
- Content: commit message, files changed, diff summary (not full diff — summarized)
- Frontmatter: repo, branch, author, timestamp, files_changed count
- Embedded into ruvector collection: `git-diffs`
- [[wiki-links]] auto-generated to vault nodes that match changed filenames

**Why:** Git history is temporal knowledge that connects "what changed" to "why it changed." An agent asking "when did we last touch the router?" gets the commit node, which links to the architecture node, which links to the decision that prompted the change.

**Implementation:** Git hook or cron that runs `git log --since=last-run`, summarizes each commit, writes .md, triggers embed pipeline.

**Risk:** Volume — active repos produce many commits. Mitigate with summarization (don't embed raw diffs, embed the commit message + file list + one-line summary per file changed).

### Extension 8: Embedding Quality Collection (Self-Calibration)

**Layer:** L1 (structure) — meta-collection

A collection called `embedding-quality/` that stores the self-healing linker's own performance data:

- `embedding-quality/false-links.md` — links the linker proposed that a human rejected
- `embedding-quality/correct-links.md` — links that were accepted or already existed  
- `embedding-quality/near-misses.md` — high similarity pairs that are semantically different (e.g., "zombies" vs "zombie processes")
- `embedding-quality/domain-collisions.md` — terms that mean different things in different collections (e.g., "constraint" in training vs architecture vs physics)

**Why:** The failures of the linker are training data for the linker. When it wrongly links two nodes, that error tells us where the embedding space is ambiguous FOR THIS SPECIFIC VAULT. Not generic — domain-specific calibration.

**How it works:**
1. Linker proposes a [[link]] between nodes A and B (cosine > threshold)
2. If human rejects: log to false-links.md with the similarity score and both node titles
3. Over time: the rejection patterns reveal where embeddings fail in this domain
4. Threshold becomes per-collection or per-domain-pair, not global
5. Eventually: fine-tune the embedding model on these pairs (near-miss calibration, already proven concept from NPU deployment)

**Connected to:** Near-miss calibration technique from pplx-embed NPU deployment. Same principle — domain-specific adversarial pairs improve quantized model quality.

---

## Extension 9: Notion as Compiled Render Layer

**Layer:** L2 (governance) — output compilation

Notion is no longer the source of truth. It's the RENDER layer — a human-readable compilation of vault nodes.

**The compiler pattern:**
- Vault .md files = source files (granular, one concept per file)
- Notion pages = compiled output (stitched from multiple vault nodes into readable documents)
- One Notion page may compile 5-50 vault nodes by topic cluster

**Compile path (vault → Notion):**
1. Query ruvector for a topic cluster (e.g., "model routing")
2. GNN ranks nodes by relevance and suggests reading order
3. Stitch .md contents into one coherent document with section headers
4. Push to Notion via API as a single page
5. Tag the page with source node IDs for traceability

**Decompile path (Notion → vault):**
1. Human edits the Notion page (adds insight, corrects a fact)
2. Diff the edited page against its compiled sources
3. Route each change back to the originating .md file
4. If the change doesn't map to an existing node → create a new vault node
5. Trigger re-embed for changed nodes

**Why this matters:**
At 150 nodes, Obsidian's graph is readable. At 1,000+ nodes it's a hairball. At 10,000 nodes it's a screensaver. Notion stays readable forever because each page is a COMPILED VIEW of a cluster, not the raw graph.

The brain graph visualizer (D3.js, Phase 4) handles the "see the whole topology" need. Notion handles the "read about this topic" need. Obsidian handles the "edit individual nodes" need. Three views, one database.

**Implementation (future):**
- `homestead compile --topic "model routing"` → queries ruvector → stitches → pushes to Notion
- `homestead decompile --notion-url <url>` → diffs → routes changes back to vault
- Cron or webhook: Notion edit detected → auto-decompile

**Risk:** Decompilation is hard — mapping edits in a compiled doc back to individual source nodes requires good traceability tags. Start with compile-only (vault → Notion), add decompile later.

---

## Future Phase: MCP Server for Cross-Machine Access

**Not part of the immediate build. Separate project.**

An MCP server that exposes vault operations as tools: read, write, search, list. Runs on Rock (primary). Clients connect via Tailscale.

```
[Mom's Mac]  →  MCP client
[Desktop]    →  MCP client   →  [MCP server on Rock]  →  ruvector + vault
[Legion]     →  MCP client
```

Any Claude Code instance on any machine gets vault access. The vault becomes the shared persistent layer for all instances.

This is the final step that makes the vault a true multi-machine knowledge substrate. Not a feature for the current build cycle — needs the watcher, crystallization, and preference engine working first.

---

## Build Order — Rosetta Stone L0 → L3

Build in layer order. Do not start L2 work before L1 is stable. This is the [[rosetta-stone-layer-ordering-principle]] applied to HOMESTEAD.

```
L0 — INFRASTRUCTURE (no blockers)
  [1] Vault watcher daemon (extend embed_ingest.py)
      Deliverable: file change → ruvector upsert, working on Rock

L1 — TOPOLOGY (depends on L0)
  [2] Collection mapping confirmed (folders → collections, watcher routing)
  [3] Self-healing linker (first run on 127 orphans, conservative threshold)
      Deliverable: orphan graph populated, git history of auto-accepts

L2 — META LAYER (depends on L1 stable)
  [4] Preference engine (preferences/ folder, read path injection)
  [5] Wiki-link GNN ablation test
      Deliverable: ablation result. If pass: update TILL spec. If fail: document why.

L3 — DYNAMICS (depends on L2)
  [6] Session crystallization wired to teardown (crystallize.py + vault watcher)
  [7] Agent memory folders (per-agent collections, dispatch pattern)
      Note: agent memory blocked on cross-collection queries. Use two-query workaround.
```

---

## What NOT to Change

Hard constraints. These do not bend to convenience or new ideas:

- **ruvector core** — proven and deployed. Do not touch internals.
- **GNN params (K=3, boost=0.05)** — calibrated empirically. Do not change until ablation proves a better config.
- **Collection structure from ablation results** — the collection topology is what gives 94%. Do not reorganize collections without re-running the benchmark.
- **Ingest gate (9 safety checks)** — runs on every write path regardless of watcher, cron, or manual call. Not optional.
- **Anything in homestead-db-eieio.md** — that document is the frozen baseline. Extensions go here. Corrections to the baseline require a separate decision and a new date in that document.
- **embed-proxy constraints** — dim=1024, NPU only, no fallbacks. The PERPLEXAKEET calibration data is for this embedding model. Switching models invalidates the GNN calibration.

---

## Open Questions (Flagged for Resolution)

| Question | Blocking | Who decides |
|----------|----------|-------------|
| Cross-collection query implementation in ruvector | Extension 3 (agent memory) | ruvector codebase |
| Meta-collection threshold training (when to switch from static 0.85 to learned) | Extension 6 long-term | Ablation after 20+ reviews |
| Session teardown hook — what triggers crystallize.py? | Extension 4 deploy | Architecture decision |
| Preference injection window budget — how many tokens? | Extension 5 calibration | Benchmark against 10 tasks |
| SONA activation — still listed as "long game" in baseline | Not blocking anything | Wait for 1000+ live queries |

---

*Spec written: 2026-04-01*
*Baseline frozen: [[homestead-db-eieio]]*
*Architectural decision resolved: vault canonical, ruvector read cache*
*Build starts at L0: vault watcher*
