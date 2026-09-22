from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Multi-Agent Support Ticket Automation API"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = Field(default="/api/v1", pattern=r"^/")
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/support_tickets"
    )
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout_seconds: float = Field(default=30.0, gt=0)
    ollama_embedding_model: str = "embeddinggemma"
    chroma_persist_directory: str = "chroma_data"
    chroma_collection_name: str = "support_knowledge"
    knowledge_top_k: int = Field(default=5, ge=1, le=20)
    knowledge_min_relevance: float = Field(default=0.40, ge=0.0, le=1.0)
    solution_min_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    retry_max_attempts: int = Field(default=3, ge=1, le=5)
    retry_base_delay_seconds: float = Field(default=0.1, ge=0.0, le=5.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
