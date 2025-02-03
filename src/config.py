from functools import lru_cache
from typing import Literal
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

from src.llm_providers.constants import ChatProvider, EmbeddingProvider
from src.llm_providers.validators import validate_provider_settings


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
    CHAT_PROVIDER: ChatProvider = ChatProvider.OPENAI
    EMBEDDING_PROVIDER: EmbeddingProvider = EmbeddingProvider.OPENAI

    OPENAI_API_KEY: str | None = None

    OLLAMA_BASE_URL: str | None = None

    DEEPSEEK_API_KEY: str | None = None

    CHAT_OPENAI_COMPATIBLE_BASE_URL: str | None = None
    CHAT_OPENAI_COMPATIBLE_API_KEY: str | None = None

    EMBEDDING_OPENAI_COMPATIBLE_BASE_URL: str | None = None
    EMBEDDING_OPENAI_COMPATIBLE_API_KEY: str | None = None

    DEFAULT_CHAT_MODEL: str = "gpt-4o"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536  # Default for text-embedding-3-small model

    # Database Configuration
    REDIS_URL: str = "redis://localhost:6379"
    POSTGRES_URL: str = "postgresql://localhost:5432/ragpi"  # Assumes a local Postgres db named 'ragpi' exists

    # Store Configuration
    DOCUMENT_STORE_BACKEND: Literal["postgres", "redis"] = "postgres"
    DOCUMENT_STORE_NAMESPACE: str = "document_store"

    SOURCE_METADATA_BACKEND: Literal["postgres", "redis"] = "postgres"
    SOURCE_METADATA_NAMESPACE: str = "source_metadata"

    # GitHub Configuration
    GITHUB_TOKEN: str | None = None
    GITHUB_API_VERSION: str = "2022-11-28"

    # Model Settings
    BASE_SYSTEM_PROMPT: str = "You are an AI assistant specialized in retrieving and synthesizing technical information to provide relevant answers to queries."

    # Chat Settings
    CHAT_HISTORY_LIMIT: int = 20
    MAX_CHAT_ITERATIONS: int = 5
    RETRIEVAL_TOP_K: int = 10

    # Document Processing Configuration
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
    def validate_llm_providers(self):
        return validate_provider_settings(self)


@lru_cache
def get_settings():
    return Settings()
