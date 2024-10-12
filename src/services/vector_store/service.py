from typing import Optional, List
from uuid import UUID

from src.schemas.collections import (
    CollectionDocument,
    CollectionMetadata,
    CollectionResponse,
)
from src.services.vector_store.factory import get_vector_store


class VectorStoreService:
    # TODO: Get default from env
    def __init__(self, provider: str = "chroma"):
        self.vector_store = get_vector_store(provider)

    def create_collection(
        self,
        name: str,
        source: str,
        start_url: str,
        num_pages: int,
        include_pattern: Optional[str],
        exclude_pattern: Optional[str],
        timestamp: str,
    ) -> UUID:

        metadata = CollectionMetadata(
            source=source,
            start_url=start_url,
            num_pages=num_pages,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            created_at=timestamp,
            updated_at=timestamp,
        ).model_dump(exclude_none=True)

        collection_id = self.vector_store.create_collection(name, metadata)
        return collection_id

    def add_documents(
        self, collection_name: str, documents: List[CollectionDocument], timestamp: str
    ) -> List[str]:
        return self.vector_store.add_documents(collection_name, documents, timestamp)

    def get_collection(self, collection_name: str) -> CollectionResponse:
        return self.vector_store.get_collection(collection_name)

    def get_collection_documents(
        self, collection_name: str
    ) -> List[CollectionDocument]:
        return self.vector_store.get_collection_documents(collection_name)

    def get_all_collections(self) -> List[CollectionResponse]:
        return self.vector_store.get_all_collections()

    def delete_collection(self, collection_name: str) -> None:
        self.vector_store.delete_collection(collection_name)

    def delete_collection_documents(self, collection_name: str) -> bool:
        return self.vector_store.delete_collection_documents(collection_name)

    def delete_documents(self, collection_name: str, doc_ids: List[str]) -> None:
        self.vector_store.delete_documents(collection_name, doc_ids)

    def search_collection(
        self, collection_name: str, query: str
    ) -> List[CollectionDocument]:
        return self.vector_store.search_collection(collection_name, query)

    def update_collection_timestamp(self, collection_name: str, timestamp: str) -> str:
        return self.vector_store.update_collection_timestamp(collection_name, timestamp)
