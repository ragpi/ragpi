from src.services.vector_store.base import VectorStoreBase
from src.services.vector_store.providers.chroma import ChromaVectorStore
from src.services.vector_store.providers.redis import RedisVectorStore


def get_vector_store_service(provider: str) -> VectorStoreBase:
    lookup: dict[str, type[VectorStoreBase]] = {
        "chroma": ChromaVectorStore,
        "redis": RedisVectorStore,
    }

    return lookup[provider]()
