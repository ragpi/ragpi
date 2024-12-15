from src.document.store.base import DocumentStoreBase

from src.document.store.providers.redis.store import RedisDocumentStore


def get_document_store(provider: str) -> DocumentStoreBase:
    lookup: dict[str, type[DocumentStoreBase]] = {
        "redis": RedisDocumentStore,
    }

    return lookup[provider]()
