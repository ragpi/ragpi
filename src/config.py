from functools import lru_cache
from typing import Literal
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_ONLY: bool = False
    BASE_SYSTEM_PROMPT: str = "You are an automated AI support assistant designed to assist users with their queries."
    API_KEYS: list[str] | None = None
    REDIS_URL: str = "redis://localhost:6379"
    OPENAI_API_KEY: str | None = None
    OLLAMA_BASE_URL: str | None = None
    VECTOR_STORE_PROVIDER: Literal["redis"] = "redis"
    CHAT_PROVIDER: Literal["openai", "ollama"] = "openai"
    EMBEDDING_PROVIDER: Literal["openai", "ollama"] = "openai"
    DEFAULT_CHAT_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    GITHUB_TOKEN: str | None = None
    GITHUB_API_VERSION: str = "2022-11-28"
    CHAT_HISTORY_LIMIT: int = 20
    MAX_CHAT_ATTEMPTS: int = 5
    DOCUMENT_STORE_NAMESPACE: str = "document_store"
    DOCUMENT_UUID_NAMESPACE: str = "ee747eb2-fd0f-4650-9785-a2e9ae036ff2"
    DEFAULT_CHUNK_SIZE: int = 512
    DEFAULT_CHUNK_OVERLAP: int = 50
    MAX_CONCURRENT_REQUESTS: int = 10
    DOCUMENT_SYNC_BATCH_SIZE: int = 500
    USER_AGENT: str = "Ragpi"
    ENABLE_OTEL: bool = False
    OTEL_SERVICE_NAME: str = "ragpi"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

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
    return Settings()  # type: ignore
