from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_ONLY: bool = False

    BASE_SYSTEM_PROMPT: str = (
        "You are an automated AI support assistant designed to assist users with their queries."
    )

    API_KEY: str | None = None

    REDIS_URL: str = "redis://localhost:6379"

    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"

    VECTOR_STORE_PROVIDER: Literal["redis"] = "redis"

    CHAT_PROVIDER: Literal["openai", "ollama"] = "openai"

    EMBEDDING_PROVIDER: Literal["openai", "ollama"] = "openai"

    DEFAULT_CHAT_MODEL: str = "gpt-4o-mini"

    EMBEDDING_MODEL: str = "text-embedding-3-small"

    EMBEDDING_DIMENSIONS: int = 1536

    OPENAI_API_KEY: str

    GITHUB_TOKEN: str

    GITHUB_API_VERSION: str = "2022-11-28"

    CHAT_HISTORY_LIMIT: int = 20

    MAX_CHAT_ATTEMPTS: int = 5

    DOCUMENT_STORE_NAMESPACE: str = "document_store"

    DOCUMENT_UUID_NAMESPACE: str = "ee747eb2-fd0f-4650-9785-a2e9ae036ff2"

    DEFAULT_CHUNK_SIZE: int = 512

    DEFAULT_CHUNK_OVERLAP: int = 50

    MAX_CONCURRENT_REQUESTS: int = 10

    DOCUMENT_SYNC_BATCH_SIZE: int = 500

    USER_AGENT: str = "RagApi"

    RATE_LIMIT: str = Field(
        pattern=r"^\d+/(second|minute|hour|day|month|year)$", default="60/minute"
    )

    ENABLE_OTEL: bool = False

    OTEL_SERVICE_NAME: str = "rag-api"

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


@lru_cache
def get_settings():
    return Settings()  # type: ignore
