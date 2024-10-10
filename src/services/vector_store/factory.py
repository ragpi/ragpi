from src.services.vector_store.base import VectorStoreBase
from src.services.vector_store.chroma import ChromaVectorStore


def get_vector_store(store_type: str) -> VectorStoreBase:
    lookup = {
        "chroma": ChromaVectorStore,
    }

    return lookup[store_type]()
