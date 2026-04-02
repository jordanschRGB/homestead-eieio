#!/usr/bin/env python3
"""
ingest-to-ruvector-v2.py — Contextual embedding ingest for RuVector

Redesigned to use contextual embedding: each chunk is embedded with a
prefix describing WHAT the chunk is and WHERE it comes from. This makes
retrieval task-aware rather than purely text-similar.

API FINDING (tested 2026-06-12):
  The NPU model (pplx-embed-context-w8a8 at localhost:8081) IGNORES
  the `context` field — vectors are identical with or without it.
  The ONLY approach that works is string prepending:
    input = "[ctx] " + chunk_text
  This is what v2 uses.

CHANGE LOG (2026-06-14):
  Added frontmatter-aware context builder (build_context):
  - Parses YAML frontmatter from markdown files (--- delimited block)
  - Generates richer context prefix from filepath patterns + frontmatter fields
  - Context prefix is prepended to each chunk's text at embed time
  - Prefix is NOT included in chunk size calculations (no double-counting)
  - --dry-run mode prints context prefix + first 200 chars of each chunk
  - Old build_context_prefix() retained for backward compat but no longer
    called by default — build_context() is the primary path now.

Usage:
  python3 ingest-to-ruvector-v2.py --source <path_or_file> --type <doc_type>
  python3 ingest-to-ruvector-v2.py --source /path/to/vault --type governance
  python3 ingest-to-ruvector-v2.py --source /path/to/skills --type skill
  python3 ingest-to-ruvector-v2.py --help

Document types:
  governance  — AGENTS.md, SOUL.md, policy files
  memory      — MEMORY.md, USER.md, session handoffs
  knowledge   — wiki pages, research notes, docs
  skill       — SKILL.md files, agent capability definitions
  transcript  — meeting notes, YouTube transcripts
  code        — source files, scripts (use sparingly — prefer grep)

Context prefix format (new, from build_context):
  SOURCE: YouTube transcript, channel name
  INGEST: nightly cron, 2026-06-14
  DOMAIN: context-management, token-efficiency
  TYPE: reference material, not necessarily user-authored
  ---
  [chunk text follows]
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# =============================================================================
# CONFIGURATION
# =============================================================================

EMBED_URL = "http://127.0.0.1:8081/api/embed"
EMBED_MODEL = "pplx-embed-context-w8a8"
EMBED_DIM = 1024  # pplx-embed-context-w8a8 output dimension

RUVECTOR_DB = "/opt/ruvector/data/ruvector.db"

CHUNK_TOKENS = 400       # ~1600 chars — matches NPU sweet spot (3-5s latency)
CHUNK_OVERLAP_TOKENS = 80
THROTTLE_SEC = 0.6       # ARM NPU throttle between embeds

LOG_DIR = Path("/home/openclaw/.openclaw/workspace/logs")

# Document type descriptions — used in legacy context prefix
DOC_TYPE_DESCRIPTIONS = {
    "governance": "governance rules and operational policy for the AI agent system",
    "memory":     "durable learned facts, user preferences, and session state",
    "knowledge":  "reference knowledge, research notes, and documentation",
    "skill":      "agent skill definition and capability instructions",
    "transcript": "meeting notes, conversation transcripts, or video content",
    "code":       "source code, scripts, and technical implementation details",
}

VALID_TYPES = set(DOC_TYPE_DESCRIPTIONS.keys())

# File extensions to ingest per type
TYPE_EXTENSIONS = {
    "governance": {".md", ".txt"},
    "memory":     {".md", ".txt", ".json"},
    "knowledge":  {".md", ".txt", ".rst"},
    "skill":      {".md"},
    "transcript": {".md", ".txt", ".vtt", ".srt"},
    "code":       {".py", ".sh", ".ts", ".js", ".rs", ".go"},
}

# =============================================================================
# LOGGING
# =============================================================================

def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"ingest-ruvector-v2-{datetime.now().strftime('%Y-%m-%d')}.log"
    logger = logging.getLogger("ingest-v2")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

logger = setup_logging()

# =============================================================================
# FRONTMATTER PARSER
# =============================================================================
# WHY: Many markdown files in the vault have YAML frontmatter — a --- delimited
# block at the very top containing metadata like date, tags, source, channel.
# We parse this once per file and pass it to build_context() so the context
# prefix reflects actual document metadata rather than just guessing from the
# file path or doc_type argument.
#
# FORMAT SUPPORTED:
#   ---
#   title: My Document
#   tags: [memory, agent]
#   source: https://youtube.com/...
#   date: 2026-06-14
#   ---
#
# If the file has no frontmatter, returns {} and the remaining text is the
# full file content. If parsing fails (malformed YAML), logs a warning and
# returns {} to avoid crashing the ingest run.

def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from a markdown file.

    Returns (frontmatter_dict, body_text) where body_text has the frontmatter
    block stripped. If no frontmatter is found, returns ({}, original_text).

    The frontmatter block must:
    - Start at line 1 with exactly "---"
    - End with a line containing exactly "---"
    - Contain valid YAML between the markers

    We use a minimal YAML parser to avoid requiring PyYAML as a hard dep.
    If PyYAML is not installed, falls back to a simple key: value parser that
    handles the most common cases in this vault (strings, lists in bracket
    notation, dates).
    """
    lines = text.splitlines(keepends=True)

    # File must start with --- for frontmatter to be present
    if not lines or lines[0].strip() != "---":
        return {}, text

    # Find the closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        # No closing --- found — not valid frontmatter
        logger.debug("  Frontmatter: opening --- found but no closing --- marker")
        return {}, text

    frontmatter_lines = lines[1:end_idx]
    body_text = "".join(lines[end_idx + 1:])

    # Try PyYAML first (most accurate)
    try:
        import yaml  # type: ignore
        fm = yaml.safe_load("".join(frontmatter_lines)) or {}
        if not isinstance(fm, dict):
            fm = {}
        return fm, body_text
    except ImportError:
        pass  # PyYAML not installed, fall through to simple parser
    except Exception as e:
        logger.warning(f"  Frontmatter YAML parse error (PyYAML): {e} — using simple parser")

    # Simple fallback parser: handles "key: value" and "tags: [a, b, c]"
    # This covers 95%+ of files in this vault without needing PyYAML.
    fm: dict[str, Any] = {}
    for line in frontmatter_lines:
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, raw_val = line.partition(":")
        key = key.strip()
        raw_val = raw_val.strip()

        if not key:
            continue

        # Handle bracket-style lists: [a, b, c] or ['a', 'b']
        if raw_val.startswith("[") and raw_val.endswith("]"):
            inner = raw_val[1:-1]
            items = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
            fm[key] = items
        elif raw_val.lower() in ("true", "yes"):
            fm[key] = True
        elif raw_val.lower() in ("false", "no"):
            fm[key] = False
        else:
            # Strip surrounding quotes if present
            if (raw_val.startswith('"') and raw_val.endswith('"')) or \
               (raw_val.startswith("'") and raw_val.endswith("'")):
                raw_val = raw_val[1:-1]
            fm[key] = raw_val

    return fm, body_text


# =============================================================================
# CONTEXT BUILDER (new, filepath + frontmatter aware)
# =============================================================================
# WHY: The old build_context_prefix() only knew doc_type and file_name.
# This new build_context() also inspects:
#   - The full filepath to determine source type (sessions/, training/, knowledge/, etc.)
#   - frontmatter fields: source, channel, date, tags
#
# The resulting prefix is much richer — the model "knows" it's looking at a
# YouTube transcript from a specific channel on a specific date with certain
# domain tags, rather than just "a knowledge doc named transcript-xyz.md".
#
# The prefix ends with "---\n" so it reads as a clean separator from the chunk.
# This is the string that gets prepended to every chunk before embedding.
# The prefix is NOT stored in chunk_text — it's only used at embed time.

def build_context(filepath: str, frontmatter: dict[str, Any]) -> str:
    """
    Build a context prefix string for contextual embedding.

    Uses filepath patterns + frontmatter metadata to describe the document's
    origin, domain, and authority level. The prefix is prepended to each
    chunk at embed time (but NOT stored in the chunk payload or counted toward
    chunk size).

    Args:
        filepath:    Absolute or relative path to the source file.
        frontmatter: Dict of parsed YAML frontmatter (may be empty {}).

    Returns:
        A multi-line string ending with "---\n". Example:
            SOURCE: YouTube transcript, Nate B
            INGEST: nightly cron, 2026-06-14
            DOMAIN: context-management, token-efficiency
            TYPE: reference material, not necessarily user-authored
            ---
    """
    parts = []

    # ------------------------------------------------------------------
    # SOURCE: determine where this document came from
    # Priority: filepath patterns first, then frontmatter source field.
    # ------------------------------------------------------------------
    if "sessions/" in filepath:
        # Claude Code / coding agent session logs
        parts.append("SOURCE: Claude Code session log")

    elif "training/" in filepath:
        # Documents explicitly placed in a training/ subdirectory
        parts.append("SOURCE: Training methodology document")

    elif "youtube" in frontmatter.get("source", "").lower():
        # YouTube transcripts — frontmatter often has source: https://youtu.be/...
        # and optionally channel: speaker name
        channel = frontmatter.get("channel", "unknown channel")
        parts.append(f"SOURCE: YouTube transcript, {channel}")

    elif "knowledge/" in filepath:
        # General knowledge base — research notes, wiki pages, reference docs
        parts.append("SOURCE: Knowledge base document")

    elif "memory/" in filepath:
        # Session handoffs, MEMORY.md, agent-written notes
        parts.append("SOURCE: Session memory / handoff")

    elif "skills/" in filepath:
        # SKILL.md files and supporting skill content
        parts.append("SOURCE: Agent skill definition")

    elif (
        "governance/" in filepath
        or any(filepath.endswith(fname) for fname in ("AGENTS.md", "SOUL.md", "USER.md", "IDENTITY.md"))
    ):
        # Top-level governance files — highest authority in the system
        parts.append("SOURCE: Governance document")

    # If none of the above matched, SOURCE is omitted — caller knows doc_type

    # ------------------------------------------------------------------
    # INGEST: when was this ingested and by what mechanism
    # Uses frontmatter date if available, otherwise "unknown date".
    # ------------------------------------------------------------------
    ingest_date = frontmatter.get("date", "unknown date")
    parts.append(f"INGEST: nightly cron, {ingest_date}")

    # ------------------------------------------------------------------
    # DOMAIN: topic tags from frontmatter
    # Makes retrieval domain-aware: "find context-management content"
    # ------------------------------------------------------------------
    tags = frontmatter.get("tags")
    if tags:
        if isinstance(tags, list):
            parts.append(f"DOMAIN: {', '.join(str(t) for t in tags)}")
        elif isinstance(tags, str):
            parts.append(f"DOMAIN: {tags}")

    # ------------------------------------------------------------------
    # TYPE: epistemic status — is this authoritative? agent-written?
    # Helps the model weight retrieval results appropriately.
    # ------------------------------------------------------------------
    if (
        "governance/" in filepath
        or any(filepath.endswith(fname) for fname in ("AGENTS.md", "SOUL.md"))
    ):
        parts.append("TYPE: governance rule, authoritative, user-authored")

    elif "research/" in filepath or "knowledge/" in filepath:
        parts.append("TYPE: reference material, not necessarily user-authored")

    elif "memory/" in filepath:
        parts.append("TYPE: session memory, agent-authored")

    # If TYPE was not set (e.g. sessions/, training/, skills/), omit it —
    # no false claim about authority level for unlabeled content.

    # ------------------------------------------------------------------
    # Assemble: join all parts with newlines, append --- separator
    # ------------------------------------------------------------------
    return "\n".join(parts) + "\n---\n"


# =============================================================================
# LEGACY CONTEXT PREFIX BUILDER (kept for backward compatibility)
# =============================================================================
# WHY KEPT: The old function is still used by embed_with_context() as a
# fallback when filepath is not available, and by any callers that use
# doc_type + file_name only (e.g. code files where frontmatter doesn't apply).
# Do NOT remove until all call sites are migrated.

def build_context_prefix(
    doc_type: str,
    file_name: str,
    section: str | None = None,
    description: str | None = None,
) -> str:
    """
    Build a context prefix string from doc_type and file_name only.

    DEPRECATED: Prefer build_context(filepath, frontmatter) for richer output.
    This function is retained for backward compatibility and as a fallback.

    Format:
      [TYPE:governance | FILE:AGENTS.md | SECTION:Consent Boundaries]
      Document purpose: governance rules and operational policy for the AI agent system
    """
    type_desc = DOC_TYPE_DESCRIPTIONS.get(doc_type, "unknown document type")
    parts = [f"TYPE:{doc_type}", f"FILE:{file_name}"]
    if section:
        parts.append(f"SECTION:{section}")
    header = "[" + " | ".join(parts) + "]"
    desc_line = f"Document purpose: {description or type_desc}"
    return f"{header}\n{desc_line}\n\n"


def build_contextual_input(prefix: str, chunk_text: str) -> str:
    """Combine context prefix with chunk text for embedding."""
    return prefix + chunk_text


# =============================================================================
# SECTION DETECTION
# =============================================================================

def extract_section_heading(chunk_text: str) -> str | None:
    """
    Detect the most recent markdown heading in a chunk.
    Returns the heading text without the # characters, or None.
    """
    lines = chunk_text.strip().split("\n")
    for line in lines:
        m = re.match(r"^#{1,4}\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return None


def split_by_headings(text: str) -> list[tuple[str | None, str]]:
    """
    Split document text into (heading, content) pairs.
    Returns list of (section_heading, section_text).
    """
    sections = []
    current_heading = None
    current_lines = []

    for line in text.split("\n"):
        m = re.match(r"^#{1,4}\s+(.+)$", line.strip())
        if m:
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return [(h, t) for h, t in sections if t]


# =============================================================================
# CHUNKING
# =============================================================================

def chunk_section(section_text: str) -> list[str]:
    """
    Chunk a section into ~CHUNK_TOKENS token segments with overlap.
    Uses word-based splitting as a token approximation.
    """
    words = section_text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + CHUNK_TOKENS
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - CHUNK_OVERLAP_TOKENS
        if len(chunks) > 200:  # safety cap
            logger.warning("Too many chunks — truncating at 200")
            break

    return chunks


def chunk_document(text: str, doc_type: str, file_name: str) -> list[dict[str, Any]]:
    """
    Chunk a full document into embed-ready pieces with section metadata.

    NOTE: The input `text` should be the body text with frontmatter already
    stripped. Frontmatter is handled separately and passed to build_context().

    Strategy:
    1. Split by markdown headings (preserves section context)
    2. Chunk each section into ~400-token pieces
    3. Track section heading per chunk
    """
    if not text.strip():
        return []

    sections = split_by_headings(text)
    if not sections:
        # No headings — treat whole doc as one section
        sections = [(None, text)]

    all_chunks = []
    chunk_index = 0

    for heading, section_text in sections:
        if not section_text.strip():
            continue

        section_chunks = chunk_section(section_text)
        for chunk_text in section_chunks:
            if not chunk_text.strip():
                continue
            all_chunks.append({
                "chunk_index": chunk_index,
                "section": heading,
                "chunk_text": chunk_text,
            })
            chunk_index += 1

    logger.debug(f"  {file_name}: {len(all_chunks)} chunks from {len(sections)} sections")
    return all_chunks


# =============================================================================
# EMBEDDING
# =============================================================================

def embed_with_context(
    chunk_text: str,
    context_prefix: str,
) -> list[float] | None:
    """
    Embed a chunk WITH contextual prefix prepended.

    CHANGED (2026-06-14): Now accepts a pre-built context_prefix string
    (from build_context() or build_context_prefix()) instead of building it
    internally. This decouples prefix generation from embedding so the caller
    can log, inspect, or dry-run the prefix independently.

    The pplx-embed-context-w8a8 model ignores the `context` API field
    (tested: identical vectors with/without it). String prepending is
    the only method confirmed to work.

    The context prefix is included in the text sent to the embedding
    endpoint but is NOT counted toward chunk size — chunk_text is sized
    independently before this function is called.
    """
    # Combine: prefix + chunk text. This is the string sent to the model.
    contextual_input = build_contextual_input(context_prefix, chunk_text)

    try:
        response = requests.post(
            EMBED_URL,
            json={"model": EMBED_MODEL, "input": contextual_input},
            timeout=60,  # NPU can take ~25s for large inputs
        )
        response.raise_for_status()
        data = response.json()

        # pplx model returns {"embeddings": [[...]]}
        if "embeddings" in data and data["embeddings"]:
            emb = data["embeddings"][0]
            if len(emb) != EMBED_DIM:
                logger.error(f"Dimension mismatch: got {len(emb)}, expected {EMBED_DIM}")
                return None
            return emb

        # OpenAI-compatible fallback {"data": [{"embedding": [...]}]}
        if "data" in data and data["data"]:
            emb = data["data"][0]["embedding"]
            if len(emb) != EMBED_DIM:
                logger.error(f"Dimension mismatch: got {len(emb)}, expected {EMBED_DIM}")
                return None
            return emb

        logger.error(f"Unexpected embed response structure: {list(data.keys())}")
        return None

    except requests.exceptions.Timeout:
        logger.error("Embed request timed out — input may be too long")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to embed endpoint: {EMBED_URL}")
        return None
    except Exception as e:
        logger.error(f"Embed error: {e}")
        return None


# =============================================================================
# RUVECTOR INSERT
# =============================================================================

def insert_vector(
    vector_id: str,
    embedding: list[float],
    metadata: dict[str, Any],
) -> bool:
    """Insert a single vector into RuVector via mcporter."""
    vector_payload = json.dumps([{
        "id": vector_id,
        "vector": embedding,
        "metadata": metadata,
    }])

    try:
        result = subprocess.run(
            ["mcporter", "call", "ruvector.vector_db_insert",
             f"db_path={RUVECTOR_DB}",
             f"vectors={vector_payload}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error(f"Insert failed: {result.stderr[:200]}")
            return False
        return True
    except Exception as e:
        logger.error(f"Insert exception: {e}")
        return False


# =============================================================================
# FILE PROCESSING
# =============================================================================

def resolve_files(source: str, doc_type: str) -> list[Path]:
    """Resolve source path to list of files to ingest."""
    p = Path(source)
    extensions = TYPE_EXTENSIONS.get(doc_type, {".md", ".txt"})

    if p.is_file():
        return [p]

    if p.is_dir():
        files = []
        for ext in extensions:
            files.extend(p.rglob(f"*{ext}"))
        return sorted(files)

    logger.error(f"Source not found: {source}")
    return []


def ingest_file(
    file_path: Path,
    doc_type: str,
    description: str | None,
    dry_run: bool,
) -> dict[str, int]:
    """
    Ingest a single file into RuVector with contextual embeddings.

    CHANGED (2026-06-14):
    - Parses YAML frontmatter before chunking (strip it from body text)
    - Calls build_context(filepath, frontmatter) to generate the context prefix
    - Passes pre-built prefix to embed_with_context() instead of building inside
    - In dry-run mode: prints the full context prefix + first 200 chars of each
      chunk, clearly labeled, without hitting the embedding endpoint

    The context prefix is per-FILE (same for all chunks in a file). This is
    intentional — SOURCE, INGEST, DOMAIN, TYPE are file-level metadata.
    Section-level metadata (heading) is still tracked in chunk metadata but
    is NOT added to the context prefix to avoid making it too long.

    Returns {"chunks": N, "embedded": N, "inserted": N, "failed": N}.
    """
    stats = {"chunks": 0, "embedded": 0, "inserted": 0, "failed": 0}
    file_name = file_path.name
    filepath_str = str(file_path)

    try:
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.error(f"Cannot read {file_path}: {e}")
        return stats

    if not raw_text.strip():
        logger.info(f"  Skipping empty file: {file_name}")
        return stats

    # ------------------------------------------------------------------
    # STEP 1: Parse frontmatter, get body text
    # frontmatter: dict of YAML key-value pairs (may be empty)
    # body_text: file content with the --- block stripped
    # ------------------------------------------------------------------
    frontmatter, body_text = parse_frontmatter(raw_text)
    if frontmatter:
        logger.debug(f"  Frontmatter keys: {list(frontmatter.keys())}")

    # ------------------------------------------------------------------
    # STEP 2: Build context prefix for this file
    # This is computed ONCE per file and reused for all chunks.
    # It's based on filepath patterns + frontmatter, not chunk content.
    # ------------------------------------------------------------------
    context_prefix = build_context(filepath_str, frontmatter)

    logger.info(f"  Ingesting: {file_name} ({len(raw_text)} chars, {len(body_text)} body chars)")

    # ------------------------------------------------------------------
    # STEP 3: Chunk the body text (frontmatter already stripped)
    # Chunk sizes are measured against body_text only — the context prefix
    # is NOT included in CHUNK_TOKENS math, avoiding double-counting.
    # ------------------------------------------------------------------
    chunks = chunk_document(body_text, doc_type, file_name)
    stats["chunks"] = len(chunks)

    # ------------------------------------------------------------------
    # STEP 4: Embed each chunk (or print in dry-run mode)
    # ------------------------------------------------------------------
    for chunk in chunks:
        chunk_text = chunk["chunk_text"]
        section = chunk["section"]
        chunk_index = chunk["chunk_index"]
        vector_id = f"{doc_type}:{file_name}:chunk{chunk_index}"

        if dry_run:
            # Dry-run: show the context prefix and first 200 chars of chunk.
            # This lets Jordan verify what the model will "see" without
            # actually hitting the NPU or writing to RuVector.
            print(f"\n{'='*60}")
            print(f"[DRY-RUN] File: {file_name} | Chunk {chunk_index} | Section: {section or '(none)'}")
            print(f"{'='*60}")
            print("CONTEXT PREFIX:")
            print(context_prefix)
            print(f"CHUNK (first 200 chars):")
            print(chunk_text[:200])
            print(f"{'='*60}")
            stats["embedded"] += 1
            stats["inserted"] += 1
            continue

        # Live mode: embed context + chunk, insert into RuVector
        embedding = embed_with_context(
            chunk_text=chunk_text,
            context_prefix=context_prefix,
        )

        if embedding is None:
            logger.warning(f"  Failed to embed chunk {chunk_index}")
            stats["failed"] += 1
            time.sleep(THROTTLE_SEC)
            continue

        stats["embedded"] += 1

        metadata = {
            "doc_type": doc_type,
            "file_name": file_name,
            "file_path": filepath_str,
            "section": section or "",
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            # Store the context prefix in metadata for debugging retrieval quality.
            # This lets us inspect what context the model saw for any retrieved chunk.
            "context_prefix": context_prefix,
            "description": description or DOC_TYPE_DESCRIPTIONS.get(doc_type, ""),
            "ingested_at": datetime.utcnow().isoformat() + "Z",
            # Store frontmatter fields inline for richer filtering later
            "fm_date": str(frontmatter.get("date", "")),
            "fm_tags": json.dumps(frontmatter.get("tags", [])) if isinstance(frontmatter.get("tags"), list) else str(frontmatter.get("tags", "")),
            "fm_source": str(frontmatter.get("source", "")),
            "fm_channel": str(frontmatter.get("channel", "")),
        }

        if insert_vector(vector_id, embedding, metadata):
            stats["inserted"] += 1
        else:
            stats["failed"] += 1

        time.sleep(THROTTLE_SEC)  # ARM NPU throttle

    return stats


# =============================================================================
# CLI
# =============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Contextual embedding ingest for RuVector (v2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest AGENTS.md as governance doc
  python3 ingest-to-ruvector-v2.py --source ~/.openclaw/workspace/AGENTS.md --type governance

  # Ingest all skill files
  python3 ingest-to-ruvector-v2.py --source ~/.openclaw/workspace/skills --type skill

  # Ingest a transcript with custom description
  python3 ingest-to-ruvector-v2.py --source notes.md --type transcript \\
      --description "weekly sync with Jordan on memory architecture"

  # Dry run to inspect context prefixes without embedding or inserting
  python3 ingest-to-ruvector-v2.py --source AGENTS.md --type governance --dry-run

  # Dry run on a specific knowledge file to verify context prefix + chunk preview
  python3 ingest-to-ruvector-v2.py --source knowledge/transcript-xyz.md --type knowledge --dry-run
        """
    )
    parser.add_argument("--source", required=True,
                        help="File or directory to ingest")
    parser.add_argument("--type", required=True, choices=sorted(VALID_TYPES),
                        dest="doc_type",
                        help="Document type — controls context prefix and retrieval tags")
    parser.add_argument("--description", default=None,
                        help="Override the auto-generated document description in context prefix")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show context prefixes and chunk previews (first 200 chars) "
                             "without embedding or inserting into RuVector")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max files to process (useful for testing)")
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("=" * 60)
    logger.info("RuVector Contextual Ingest v2")
    logger.info(f"Source:      {args.source}")
    logger.info(f"Type:        {args.doc_type}")
    logger.info(f"Description: {args.description or '(auto)'}")
    logger.info(f"Dry run:     {args.dry_run}")
    logger.info(f"Embed URL:   {EMBED_URL}")
    logger.info(f"DB:          {RUVECTOR_DB}")
    logger.info("=" * 60)

    files = resolve_files(args.source, args.doc_type)
    if not files:
        logger.error("No files found to ingest.")
        sys.exit(1)

    if args.limit:
        files = files[:args.limit]

    logger.info(f"Files to ingest: {len(files)}")

    total = {"chunks": 0, "embedded": 0, "inserted": 0, "failed": 0}

    for i, file_path in enumerate(files, 1):
        logger.info(f"\n[{i}/{len(files)}] {file_path.name}")
        stats = ingest_file(
            file_path=file_path,
            doc_type=args.doc_type,
            description=args.description,
            dry_run=args.dry_run,
        )
        for k in total:
            total[k] += stats[k]
        logger.info(
            f"  → chunks={stats['chunks']} embedded={stats['embedded']} "
            f"inserted={stats['inserted']} failed={stats['failed']}"
        )

    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info(f"  Files processed: {len(files)}")
    logger.info(f"  Total chunks:    {total['chunks']}")
    logger.info(f"  Embedded:        {total['embedded']}")
    logger.info(f"  Inserted:        {total['inserted']}")
    logger.info(f"  Failed:          {total['failed']}")
    logger.info("=" * 60)

    if total["failed"] > 0:
        logger.warning(f"{total['failed']} chunks failed — check logs")
        sys.exit(2)


if __name__ == "__main__":
    main()
