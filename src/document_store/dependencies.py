from fastapi import Depends
from openai import OpenAI

from src.common.openai import get_embedding_openai_client
from src.common.redis import get_redis_client, RedisClient
from src.config import Settings, get_settings
from src.document_store.base import DocumentStoreService
from src.document_store.service import get_document_store_service


def get_document_store(
    redis_client: RedisClient = Depends(get_redis_client),
    openai_client: OpenAI = Depends(get_embedding_openai_client),
    settings: Settings = Depends(get_settings),
) -> DocumentStoreService:
    return get_document_store_service(redis_client, openai_client, settings)
