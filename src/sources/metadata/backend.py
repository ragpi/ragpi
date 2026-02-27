from src.common.postgres import get_postgres_engine
from src.config import Settings
from src.common.redis import RedisClient
from src.sources.metadata.base import SourceMetadataStore
from src.sources.metadata.postgres.store import PostgresMetadataStore
from src.sources.metadata.redis.store import RedisMetadataStore


def get_metadata_store_backend(
    redis_client: RedisClient,
    settings: Settings,
) -> SourceMetadataStore:
    if settings.SOURCE_METADATA_BACKEND == "postgres":
        return PostgresMetadataStore(
            engine=get_postgres_engine(settings),
        )
    elif settings.SOURCE_METADATA_BACKEND == "redis":
        return RedisMetadataStore(
            redis_client=redis_client,
            key_prefix=settings.SOURCE_METADATA_NAMESPACE,
        )
    else:
        raise ValueError(
            f"Unsupported source metadata backend: {settings.SOURCE_METADATA_BACKEND}"
        )
