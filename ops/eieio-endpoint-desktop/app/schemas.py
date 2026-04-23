from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class TextDocument(BaseModel):
    name: str
    content: str


class IngestTextRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    documents: list[TextDocument]
    chunk_chars: int | None = None
    overlap_chars: int | None = None
    batch_size: int | None = None
    return_vectors_inline: bool = False
    use_preprocessor: bool = False
    preprocess_model: str | None = None

    @field_validator("documents")
    @classmethod
    def validate_documents(cls, value: list[TextDocument]):
        if not value:
            raise ValueError("documents must not be empty")
        return value


class ChunkRecord(BaseModel):
    source_name: str
    chunk_index: int
    start_char: int
    end_char: int
    unit_start: int | None = None
    unit_end: int | None = None
    label: str | None = None
    reason: str | None = None
    text: str | None = None
    embedding: list[float] | None = None


class IngestResponse(BaseModel):
    job_id: str
    model: str
    source_count: int
    chunk_count: int
    output_jsonl: str
    preprocess_used: bool = False
    chunks: list[ChunkRecord] | None = None
