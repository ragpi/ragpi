from src.document_store.base import DocumentStoreBase

from src.document_store.providers.redis.store import RedisDocumentStore


def get_document_store(provider: str) -> DocumentStoreBase:
    lookup: dict[str, type[DocumentStoreBase]] = {
        "redis": RedisDocumentStore,
    }

    return lookup[provider]()
