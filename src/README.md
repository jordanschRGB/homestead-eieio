# src/

Extension code for the HOMESTEAD EIEIO retrieval system.

## What goes here

- **Rust crate extensions** for ruvector: GNN tuning, collection management utilities, FENCE diagnostics
- **Python tooling** for meta-collection operations (cross-collection queries, topology inspection, bulk re-index)

## What does NOT go here

- **Operational scripts** → `vault-tools/` (ingestion, sync, nightly jobs)
- **Documentation** → `docs/` (architecture decisions, comparisons, references)

## Structure (expected)

```
src/
  rust/        # ruvector crate extensions
  python/      # meta-collection tooling
```

Code here extends the retrieval stack. It is not a runtime service.
