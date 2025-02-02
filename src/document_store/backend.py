from openai import OpenAI

from src.common.redis import RedisClient
from src.config import Settings
from src.document_store.base import DocumentStoreBackend
from src.document_store.postgres.store import PostgresDocumentStore
from src.document_store.redis.store import RedisDocumentStore


def get_document_store_backend(
    redis_client: RedisClient,
    openai_client: OpenAI,
    settings: Settings,
) -> DocumentStoreBackend:
    if settings.DOCUMENT_STORE_BACKEND == "postgres":
        return PostgresDocumentStore(
            database_url=settings.POSTGRES_URL,
            openai_client=openai_client,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimensions=settings.EMBEDDING_DIMENSIONS,
        )
    elif settings.DOCUMENT_STORE_BACKEND == "redis":
        return RedisDocumentStore(
            index_name=settings.DOCUMENT_STORE_NAMESPACE,
            redis_client=redis_client,
            openai_client=openai_client,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimensions=settings.EMBEDDING_DIMENSIONS,
        )
    else:
        raise ValueError(
            f"Unsupported document store backend: {settings.DOCUMENT_STORE_BACKEND}"
        )
