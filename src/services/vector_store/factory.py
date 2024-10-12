from src.services.vector_store.base import VectorStoreBase
from src.services.vector_store.providers.chroma import ChromaVectorStore


def get_vector_store(provider: str) -> VectorStoreBase:
    lookup = {
        "chroma": ChromaVectorStore,
    }

    return lookup[provider]()
