from fastapi import Depends
from openai import OpenAI

from src.common.openai import get_embedding_openai_client
from src.common.redis import get_redis_client, RedisClient
from src.config import Settings, get_settings
from src.document_store.base import DocumentStoreService
from src.document_store.providers.redis.store import RedisDocumentStore


def get_document_store(
    redis_client: RedisClient = Depends(get_redis_client),
    openai_client: OpenAI = Depends(get_embedding_openai_client),
    settings: Settings = Depends(get_settings),
) -> DocumentStoreService:
    return RedisDocumentStore(
        index_name=settings.DOCUMENT_STORE_NAMESPACE,
        redis_client=redis_client,
        openai_client=openai_client,
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_dimensions=settings.EMBEDDING_DIMENSIONS,
    )
