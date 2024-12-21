from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BASE_SYSTEM_PROMPT: str = (
        "You are an automated AI support assistant designed to assist users with their queries."
    )

    API_KEY: str | None = None

    REDIS_URL: str = "redis://localhost:6379"

    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"

    VECTOR_STORE_PROVIDER: Literal["redis"] = "redis"

    CHAT_PROVIDER: Literal["openai", "ollama"] = "openai"

    EMBEDDING_PROVIDER: Literal["openai", "ollama"] = "openai"

    CHAT_MODEL: str = "gpt-4o-mini"

    EMBEDDING_MODEL: str = "text-embedding-3-small"

    EMBEDDING_DIMENSIONS: int = 1536

    OPENAI_API_KEY: str

    GITHUB_TOKEN: str

    GITHUB_API_VERSION: str = "2022-11-28"

    CHAT_HISTORY_LIMIT: int = 20

    CHAT_MAX_ATTEMPTS: int = 5

    DOCUMENT_STORE_NAMESPACE: str = "document_store"

    DOCUMENT_UUID_NAMESPACE: str = "ee747eb2-fd0f-4650-9785-a2e9ae036ff2"

    CHUNK_SIZE: int = 512

    CHUNK_OVERLAP: int = 50

    CONCURRENT_REQUESTS: int = 10

    DOCUMENT_SYNC_BATCH_SIZE: int = 500

    USER_AGENT: str = "RagApi"

    RATE_LIMIT: str = Field(
        pattern=r"^\d+/(second|minute|hour|day|month|year)$", default="60/minute"
    )

    TRACELOOP_API_KEY: str | None = None

    TRACELOOP_BASE_URL: str | None = None

    TRACELOOP_HEADERS: str | None = None


@lru_cache
def get_settings():
    return Settings()  # type: ignore
