---
title: "Embedding Provenance — Always Tag What Made the Vector"
tags: [architecture, embeddings, provenance, debugging, homestead]
date: "2026-04-02"
status: ACTIVE
related: [[embedding-ownership-decision]], [[homestead-vault-self-heal]]
---

# Embedding Provenance

Every vector stored in ruvector MUST carry metadata about how it was created. If vectors go bad, this is how we find out which machine, model, and chunk size caused it.

## Required Metadata Fields

```json
{
  "embed_model": "pplx-embed-context-q8_0",
  "embed_method": "llama-embedding-cli",
  "embed_machine": "desktop-3080",
  "embed_quant": "Q8_0",
  "chunk_strategy": "heading-aware",
  "chunk_max_chars": 24000,
  "chunk_overlap_chars": 4000,
  "embed_date": "2026-04-02T03:00:00Z"
}
```

For NPU fallback vectors:
```json
{
  "embed_model": "pplx-embed-context-w8a8",
  "embed_method": "rkllama-npu",
  "embed_machine": "rock5b-npu",
  "embed_quant": "W8A8",
  "chunk_strategy": "heading-aware",
  "chunk_max_tokens": 400,
  "chunk_overlap_tokens": 80,
  "embed_date": "2026-04-02T03:00:00Z"
}
```

## Why

Tested Apr 2, 2026: cosine similarity between 3080-Q8 full-doc embed and NPU-W8A8 400-token embed of the same document = 0.987. Cross-doc similarity = 0.968. The geometry holds — same document wins regardless of embed path.

But 0.987 is not 1.000. Over thousands of vectors, if a pattern of bad retrievals emerges, the first diagnostic question is: "were the bad vectors all embedded by the same machine?" Without provenance metadata, that question is unanswerable.

## Rule

Store it. Always. Even when it seems fine. Especially when it seems fine.
