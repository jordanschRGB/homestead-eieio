from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    argus_base_url: str = Field(default="http://127.0.0.1:8010", alias="ARGUS_BASE_URL")
    argus_model: str = Field(default="pplx-embed-context-v1-0.6b-q8_0.gguf", alias="ARGUS_MODEL")
    api_token: str = Field(default="change-me", alias="API_TOKEN")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8020, alias="PORT")
    work_dir: Path = Field(
        default=Path(r"C:\Users\jorda\Desktop\argus-ingest-wrapper-data"),
        alias="WORK_DIR",
    )
    default_chunk_chars: int = Field(default=2400, alias="DEFAULT_CHUNK_CHARS")
    default_overlap_chars: int = Field(default=300, alias="DEFAULT_OVERLAP_CHARS")
    default_batch_size: int = Field(default=24, alias="DEFAULT_BATCH_SIZE")
    preprocess_base_url: str = Field(default="http://127.0.0.1:6942", alias="PREPROCESS_BASE_URL")
    preprocess_model: str = Field(default="google/gemma-4-e2b", alias="PREPROCESS_MODEL")
    preprocess_timeout_seconds: int = Field(default=180, alias="PREPROCESS_TIMEOUT_SECONDS")
