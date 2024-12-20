from fastapi import Depends

from src.common.redis import get_redis_client, RedisClient
from src.document_store.base import DocumentStoreBase
from src.document_store.providers.redis.store import RedisDocumentStore


def get_document_store(
    redis_client: RedisClient = Depends(get_redis_client),
) -> DocumentStoreBase:
    return RedisDocumentStore(redis_client=redis_client)
