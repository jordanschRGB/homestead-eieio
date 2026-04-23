from __future__ import annotations

import json
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile

from app.auth import auth_dependency
from app.chunking import Chunk, chunks_from_segments, split_into_units, split_text
from app.config import Settings
from app.embed_client import ArgusEmbedClient
from app.preprocess_client import LmStudioPreprocessClient
from app.schemas import ChunkRecord, IngestResponse, IngestTextRequest, TextDocument


@dataclass
class AppState:
    api_token: str
    settings: Settings
    embed_client: object
    preprocess_client: object | None


def build_default_state() -> AppState:
    settings = Settings()
    settings.work_dir.mkdir(parents=True, exist_ok=True)
    return AppState(
        api_token=settings.api_token,
        settings=settings,
        embed_client=ArgusEmbedClient(settings.argus_base_url, settings.argus_model),
        preprocess_client=LmStudioPreprocessClient(
            settings.preprocess_base_url,
            settings.preprocess_model,
            settings.preprocess_timeout_seconds,
        ),
    )


def _batch(items: list[str], size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _records_from_documents(
    documents: list[TextDocument],
    chunk_chars: int,
    overlap_chars: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in documents:
        chunks.extend(split_text(doc.content, doc.name, chunk_chars, overlap_chars))
    return chunks


def _write_jsonl(output_path: Path, chunks: list[Chunk], vectors: list[list[float]]) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        for chunk, vector in zip(chunks, vectors, strict=True):
            handle.write(
                json.dumps(
                    {
                        "source_name": chunk.source_name,
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "unit_start": chunk.unit_start,
                        "unit_end": chunk.unit_end,
                        "label": chunk.label,
                        "reason": chunk.reason,
                        "text": chunk.text,
                        "embedding": vector,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def _ingest_documents(
    state: AppState,
    documents: list[TextDocument],
    chunk_chars: int | None,
    overlap_chars: int | None,
    batch_size: int | None,
    return_vectors_inline: bool,
    use_preprocessor: bool = False,
    preprocess_model: str | None = None,
) -> IngestResponse:
    chunk_chars = chunk_chars or state.settings.default_chunk_chars
    overlap_chars = overlap_chars or state.settings.default_overlap_chars
    batch_size = batch_size or state.settings.default_batch_size

    if use_preprocessor:
        if not state.preprocess_client:
            raise HTTPException(status_code=400, detail={"code": "preprocessor_not_configured"})
        chunks: list[Chunk] = []
        for doc in documents:
            units = split_into_units(doc.content)
            if not units:
                continue
            segments = state.preprocess_client.segment_units(doc.name, units, preprocess_model)
            chunks.extend(chunks_from_segments(doc.content, doc.name, units, segments))
    else:
        chunks = _records_from_documents(documents, chunk_chars, overlap_chars)
    if not chunks:
        raise HTTPException(status_code=400, detail={"code": "no_text_chunks"})

    vectors: list[list[float]] = []
    for text_batch in _batch([chunk.text for chunk in chunks], batch_size):
        vectors.extend(state.embed_client.embed_batch(text_batch))

    job_id = uuid.uuid4().hex
    output_path = state.settings.work_dir / f"{job_id}.jsonl"
    _write_jsonl(output_path, chunks, vectors)

    inline_chunks = None
    if return_vectors_inline:
        inline_chunks = [
            ChunkRecord(
                source_name=chunk.source_name,
                chunk_index=chunk.chunk_index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                unit_start=chunk.unit_start,
                unit_end=chunk.unit_end,
                label=chunk.label,
                reason=chunk.reason,
                text=chunk.text,
                embedding=vector,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]

    return IngestResponse(
        job_id=job_id,
        model=state.settings.argus_model,
        source_count=len(documents),
        chunk_count=len(chunks),
        output_jsonl=str(output_path),
        preprocess_used=use_preprocessor,
        chunks=inline_chunks,
    )


def _documents_from_zip(upload: UploadFile) -> list[TextDocument]:
    supported_suffixes = {".md", ".markdown", ".mdx", ".txt", ".text"}
    documents: list[TextDocument] = []

    with tempfile.TemporaryDirectory() as temp_dir:
        archive_path = Path(temp_dir) / upload.filename
        archive_path.write_bytes(upload.file.read())
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                suffix = Path(info.filename).suffix.lower()
                if suffix not in supported_suffixes:
                    continue
                text = archive.read(info).decode("utf-8", errors="replace")
                documents.append(TextDocument(name=info.filename, content=text))

    return documents


def build_app(state: AppState | None = None) -> FastAPI:
    state = state or build_default_state()
    app = FastAPI(title="EIEIO Endpoint Desktop Ingest Helper", version="0.1.0")
    auth = auth_dependency(state.api_token)

    def help_payload():
        return {
            "service": "EIEIO Endpoint Desktop Ingest Helper",
            "model": state.settings.argus_model,
            "docs_url": "/docs",
            "routes": {
                "health": {
                    "method": "GET",
                    "path": "/health",
                    "auth_required": True,
                    "purpose": "Quick liveness check.",
                },
                "ingest_text": {
                    "method": "POST",
                    "path": "/v1/ingest/text",
                    "auth_required": True,
                    "purpose": "Send raw text documents directly in JSON.",
                    "body_shape": {
                        "documents": [
                            {
                                "name": "notes.md",
                                "content": "your full text here",
                            }
                        ],
                        "chunk_chars": 4000,
                        "overlap_chars": 400,
                        "batch_size": 16,
                        "return_vectors_inline": False,
                        "use_preprocessor": False,
                        "preprocess_model": "google/gemma-4-e2b",
                    },
                },
                "ingest_archive": {
                    "method": "POST",
                    "path": "/v1/ingest/archive",
                    "auth_required": True,
                    "purpose": "Upload one zip archive containing many .md/.mdx/.txt files.",
                    "form_fields": {
                        "file": "docs.zip",
                        "chunk_chars": 4000,
                        "overlap_chars": 400,
                        "batch_size": 16,
                        "return_vectors_inline": False,
                        "use_preprocessor": False,
                    },
                    "supported_extensions": [".md", ".markdown", ".mdx", ".txt", ".text"],
                },
                "preprocess": {
                    "method": "internal",
                    "path": "LM Studio at PREPROCESS_BASE_URL",
                    "auth_required": False,
                    "purpose": "Optional semantic chunk planning before embeddings.",
                    "default_model": state.settings.preprocess_model,
                },
            },
            "notes": [
                "Use text when your caller already has the document contents in memory.",
                "Use archive when your caller has a folder of markdown or transcript files and wants one upload.",
                "Set use_preprocessor=true to ask a small LM Studio model to group source units into semantic segments before embedding.",
                "Each job writes a JSONL file with chunk metadata plus embeddings on the server.",
            ],
        }

    @app.get("/")
    def root():
        return help_payload()

    @app.get("/help")
    def help_route():
        return help_payload()

    @app.get("/health", dependencies=[Depends(auth)])
    def health():
        return {"ok": True}

    @app.post("/v1/ingest/text", response_model=IngestResponse, dependencies=[Depends(auth)])
    def ingest_text(request: IngestTextRequest):
        return _ingest_documents(
            state=state,
            documents=request.documents,
            chunk_chars=request.chunk_chars,
            overlap_chars=request.overlap_chars,
            batch_size=request.batch_size,
            return_vectors_inline=request.return_vectors_inline,
            use_preprocessor=request.use_preprocessor,
            preprocess_model=request.preprocess_model,
        )

    @app.post("/v1/ingest/archive", response_model=IngestResponse, dependencies=[Depends(auth)])
    def ingest_archive(
        file: UploadFile = File(...),
        chunk_chars: int | None = None,
        overlap_chars: int | None = None,
        batch_size: int | None = None,
        return_vectors_inline: bool = False,
        use_preprocessor: bool = False,
        preprocess_model: str | None = None,
    ):
        documents = _documents_from_zip(file)
        if not documents:
            raise HTTPException(status_code=400, detail={"code": "no_supported_files"})
        return _ingest_documents(
            state=state,
            documents=documents,
            chunk_chars=chunk_chars,
            overlap_chars=overlap_chars,
            batch_size=batch_size,
            return_vectors_inline=return_vectors_inline,
            use_preprocessor=use_preprocessor,
            preprocess_model=preprocess_model,
        )

    return app


app = build_app()
