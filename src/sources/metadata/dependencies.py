from fastapi import Depends

from src.common.redis import get_redis_client, RedisClient
from src.config import Settings, get_settings
from src.sources.metadata.base import SourceMetadataStore
from src.sources.metadata.service import get_metadata_store_service


def get_metadata_store(
    redis_client: RedisClient = Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
) -> SourceMetadataStore:
    return get_metadata_store_service(redis_client, settings)
