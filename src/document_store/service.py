from openai import OpenAI

from src.common.redis import RedisClient
from src.config import Settings
from src.document_store.base import DocumentStoreService
from src.document_store.providers.postgres.store import PostgresDocumentStore
from src.document_store.providers.redis.store import RedisDocumentStore


def get_document_store_service(
    redis_client: RedisClient,
    openai_client: OpenAI,
    settings: Settings,
) -> DocumentStoreService:
    if settings.DOCUMENT_STORE_PROVIDER == "postgres":
        return PostgresDocumentStore(
            database_url=settings.POSTGRES_URL,
            table_name=settings.DOCUMENT_STORE_NAMESPACE,
            openai_client=openai_client,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimensions=settings.EMBEDDING_DIMENSIONS,
        )
    elif settings.DOCUMENT_STORE_PROVIDER == "redis":
        return RedisDocumentStore(
            index_name=settings.DOCUMENT_STORE_NAMESPACE,
            redis_client=redis_client,
            openai_client=openai_client,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimensions=settings.EMBEDDING_DIMENSIONS,
        )
    else:
        raise ValueError(
            f"Unsupported document store provider: {settings.DOCUMENT_STORE_PROVIDER}"
        )
