from fastapi import Depends
from openai import OpenAI

from src.common.openai import get_embedding_openai_client
from src.common.redis import get_redis_client, RedisClient
from src.config import Settings, get_settings
from src.document_store.base import DocumentStoreService
from src.document_store.providers.postgres.store import PostgresDocumentStore
from src.document_store.providers.redis.store import RedisDocumentStore


# TODO: Move to service.py file
# Factory that can be used outside of FastAPI. e.g. SourceSyncService
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


# FastAPI dependency
def get_document_store(
    redis_client: RedisClient = Depends(get_redis_client),
    openai_client: OpenAI = Depends(get_embedding_openai_client),
    settings: Settings = Depends(get_settings),
) -> DocumentStoreService:
    return get_document_store_service(redis_client, openai_client, settings)
