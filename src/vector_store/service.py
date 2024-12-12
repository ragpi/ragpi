from src.vector_store.base import VectorStoreBase

from src.vector_store.providers.redis.store import RedisVectorStore


def get_vector_store_service(provider: str) -> VectorStoreBase:
    lookup: dict[str, type[VectorStoreBase]] = {
        "redis": RedisVectorStore,
    }

    return lookup[provider]()
