"""
Application configuration.

All settings are loaded from environment variables (and `.env` file in dev).
Validation happens at startup — if a required value is missing or malformed,
the app will refuse to boot instead of failing silently later.

Key design decisions:
- Use pydantic-settings for typed, validated configuration.
- A single `Settings` instance is created once and shared via dependency
  injection (see app/dependencies.py).
- Secret fields (API keys, passwords) are marked with `SecretStr` so they are
  never accidentally logged.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ───────── Application ─────────
    app_name: str = "agentic-rag-backend"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = False
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # ───────── Gemini ─────────
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.8-flash"
    gemini_temperature: float = 0.2
    gemini_timeout_seconds: int = 60
    gemini_max_output_tokens: int = 2048

    # ───────── Database ─────────
    database_url: str = "postgresql+asyncpg://app:password@localhost:5432/agentic_rag"
    pg_pool_size: int = 10
    pg_max_overflow: int = 20
    pg_pool_timeout: int = 30

    # ───────── Redis ─────────
    redis_url: str = "redis://localhost:6379/0"

    # ───────── Storage ─────────
    storage_backend: str = "minio"  # "s3" or "minio"
    aws_region: str = "ap-south-1"
    s3_bucket_name: str = "agentic-rag-documents"
    s3_endpoint_url: str | None = "http://localhost:9000"
    aws_access_key_id: SecretStr = SecretStr("")
    aws_secret_access_key: SecretStr = SecretStr("")
    s3_use_path_style: bool = True
    s3_presign_expiry_seconds: int = 3600

    # ───────── Embeddings ─────────
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    embedding_cache_dir: str = "./models"
    embedding_dimensions: int = 384  # bge-small-en-v1.5 = 384

    # ───────── RAG ─────────
    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_top_k: int = 5
    rerank_candidate_count: int = 10
    max_agent_steps: int = 6
    max_query_refinements: int = 1

    # ───────── Upload limits ─────────
    max_upload_size_mb: int = 20
    allowed_content_types: List[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        ]
    )

    # ───────── Worker ─────────
    worker_concurrency: int = 4
    task_max_retries: int = 3
    task_retry_delay_seconds: int = 30

    # ───────── Weather MCP server ─────────
    weather_api_base: str = "https://api.open-meteo.com/v1"
    weather_timeout_seconds: int = 10

    # ───────── Security ─────────
    api_key: SecretStr = SecretStr("")
    default_owner_id: str = "local-dev"

    # ───────── Validators ─────────

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("allowed_content_types", mode="before")
    @classmethod
    def _parse_types(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @model_validator(mode="after")
    def _check_gemini_in_production(self):
        # Only fail loudly when explicitly production. Dev should still boot
        # for foundation-only phases (Phase 1 doesn't need Gemini yet).
        if self.app_env == "production" and not self.gemini_api_key.get_secret_value():
            raise ValueError("GEMINI_API_KEY is required in production")
        return self

    # ───────── Convenience properties ─────────

    @property
    def is_dev(self) -> bool:
        return self.app_env != "production"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance. Use everywhere — never re-read env."""
    return Settings()