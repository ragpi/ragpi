from typing import Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


EMBEDDING_MODELS = Literal[
    "text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"
]

RERANKING_MODELS = Literal[
    "ms-marco-TinyBERT-L-2-v2",
    "ms-marco-MiniLM-L-12-v2",
    "ms-marco-MultiBERT-L-12",
    "rank-T5-flan",
    "ce-esci-MiniLM-L12-v2",
    "rank_zephyr_7b_v1_full",
    "miniReranker_arabic_v1",
]


class Settings(BaseSettings):
    API_KEY: str | None = None

    VECTOR_STORE_PROVIDER: Literal["redis", "chroma"] = "redis"

    OPENAI_API_KEY: str

    REDIS_URL: str = "redis://localhost:6379"

    CHAT_MODEL: str = "gpt-4o-mini"

    RERANKING_MODEL: RERANKING_MODELS = "ms-marco-TinyBERT-L-2-v2"

    EMBEDDING_MODEL: EMBEDDING_MODELS = "text-embedding-3-small"

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
        if self.EMBEDDING_MODEL == "text-embedding-3-large":
            self.EMBEDDING_DIMENSIONS = 3072  # type: ignore
        return self


settings = Settings()  # type: ignore
