from enum import Enum
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class VectorStoreProvider(str, Enum):
    REDIS = "redis"
    CHROMA = "chroma"


class EmbeddingModel(str, Enum):
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"


class Settings(BaseSettings):
    API_KEY: str | None = None

    VECTOR_STORE_PROVIDER: VectorStoreProvider = VectorStoreProvider.REDIS

    OPENAI_API_KEY: str

    REDIS_URL: str = "redis://localhost:6379"

    CHAT_MODEL: str = "gpt-4o-mini"

    RERANKING_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    EMBEDDING_MODEL: EmbeddingModel = EmbeddingModel.TEXT_EMBEDDING_3_SMALL

    EMBEDDING_DIMENSIONS: int = 1536

    CHUNK_SIZE: int = 512

    CHUNK_OVERLAP: int = 128

    SYSTEM_PROMPT: str = (
        "You are an expert on {repository} and can answer any questions about it."
    )

    MAX_CONCURRENT_REQUESTS: int = 10

    DOCUMENT_SYNC_BATCH_SIZE: int = 500

    RETRIEVAL_LIMIT: int = 25

    USER_AGENT: str = "RagApi"

    RATE_LIMIT: str = Field(
        pattern=r"^\d+/(second|minute|hour|day|month|year)$", default="60/minute"
    )

    @model_validator(mode="after")
    def set_embedding_dimensions(self):
        if self.EMBEDDING_MODEL == EmbeddingModel.TEXT_EMBEDDING_3_LARGE:
            self.EMBEDDING_DIMENSIONS = 3072  # type: ignore
        return self


settings = Settings()  # type: ignore
