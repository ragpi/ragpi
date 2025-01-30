from src.config import Settings
from src.common.redis import RedisClient
from src.sources.metadata.base import SourceMetadataStore
from src.sources.metadata.providers.postgres.store import PostgresMetadataStore
from src.sources.metadata.providers.redis.store import RedisMetadataStore


def get_metadata_store_service(
    redis_client: RedisClient,
    settings: Settings,
) -> SourceMetadataStore:
    if settings.METADATA_STORE_PROVIDER == "postgres":
        return PostgresMetadataStore(
            database_url=settings.POSTGRES_URL,
        )
    elif settings.METADATA_STORE_PROVIDER == "redis":
        return RedisMetadataStore(
            redis_client=redis_client,
        )
    else:
        raise ValueError(
            f"Unsupported metadata store provider: {settings.METADATA_STORE_PROVIDER}"
        )
