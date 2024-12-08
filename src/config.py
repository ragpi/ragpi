from typing import Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


EMBEDDING_MODELS = Literal[
    "text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"
]


class Settings(BaseSettings):
    API_KEY: str | None = None

    VECTOR_STORE_PROVIDER: Literal["redis"] = "redis"

    OPENAI_API_KEY: str

    GITHUB_TOKEN: str

    TRACELOOP_API_KEY: str | None = None

    TRACELOOP_BASE_URL: str | None = None

    TRACELOOP_HEADERS: str | None = None

    GITHUB_API_VERSION: str = "2022-11-28"

    REDIS_URL: str = "redis://localhost:6379"

    CHAT_MODEL: str = "gpt-4o-mini"

    EMBEDDING_MODEL: EMBEDDING_MODELS = "text-embedding-3-small"

    EMBEDDING_DIMENSIONS: int = 1536

    CHUNK_SIZE: int = 512

    CHUNK_OVERLAP: int = 50

    CONCURRENT_REQUESTS: int = 10

    DOCUMENT_SYNC_BATCH_SIZE: int = 500

    USER_AGENT: str = "RagApi"

    RATE_LIMIT: str = Field(
        pattern=r"^\d+/(second|minute|hour|day|month|year)$", default="60/minute"
    )

    @model_validator(mode="after")
    def set_embedding_dimensions(self):
        if self.EMBEDDING_MODEL == "text-embedding-3-large":
            self.EMBEDDING_DIMENSIONS = 3072  # type: ignore
        return self


settings = Settings()  # type: ignore
