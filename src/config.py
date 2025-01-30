from functools import lru_cache
from typing import Literal
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Configuration
    API_NAME: str = "Ragpi"
    API_SUMMARY: str = "Ragpi is an AI assistant specialized in retrieving and synthesizing technical information to provide relevant answers to queries."
    API_KEYS: list[str] | None = None
    WORKERS_ENABLED: bool = True
    TASK_RETENTION_DAYS: int = 7
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    USER_AGENT: str = "Ragpi"
    MAX_CONCURRENT_REQUESTS: int = 10

    # LLM Provider Configuration
    CHAT_PROVIDER: Literal["openai", "ollama"] = "openai"
    EMBEDDING_PROVIDER: Literal["openai", "ollama"] = "openai"
    OLLAMA_BASE_URL: str | None = None
    OPENAI_API_KEY: str | None = None

    # Document Store Configuration
    DOCUMENT_STORE_PROVIDER: Literal["postgres", "redis"] = "postgres"
    POSTGRES_URL: str = "postgresql://localhost:5432/ragpi"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"

    # GitHub Configuration
    GITHUB_TOKEN: str | None = None
    GITHUB_API_VERSION: str = "2022-11-28"

    # Model Settings
    DEFAULT_CHAT_MODEL: str = "gpt-4o"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536  # Default for text-embedding-3-small model
    BASE_SYSTEM_PROMPT: str = "You are an AI assistant specialized in retrieving and synthesizing technical information to provide relevant answers to queries."

    # Chat Settings
    CHAT_HISTORY_LIMIT: int = 20
    MAX_CHAT_ITERATIONS: int = 5

    # Document Processing Configuration
    DOCUMENT_STORE_NAMESPACE: str = "documents"
    DOCUMENT_UUID_NAMESPACE: str = "ee747eb2-fd0f-4650-9785-a2e9ae036ff2"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    DOCUMENT_SYNC_BATCH_SIZE: int = 500

    # OpenTelemetry Settings
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "ragpi"

    @field_validator("API_KEYS", mode="before")
    def split_api_keys(cls, value: str) -> list[str]:
        return value.split(",") if value else []

    @model_validator(mode="after")
    def validate_provider_settings(self):
        if self.CHAT_PROVIDER == "ollama" and not self.OLLAMA_BASE_URL:
            raise ValueError(
                "OLLAMA_BASE_URL must be set when CHAT_PROVIDER is 'ollama'"
            )

        if self.EMBEDDING_PROVIDER == "ollama" and not self.OLLAMA_BASE_URL:
            raise ValueError(
                "OLLAMA_BASE_URL must be set when EMBEDDING_PROVIDER is 'ollama'"
            )

        if self.CHAT_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY must be set when CHAT_PROVIDER is 'openai'"
            )

        if self.EMBEDDING_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY must be set when EMBEDDING_PROVIDER is 'openai'"
            )

        return self


@lru_cache
def get_settings():
    return Settings()
