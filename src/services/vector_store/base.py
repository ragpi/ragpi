from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from src.schemas.collections import CollectionDocument, CollectionResponse


class VectorStoreBase(ABC):
    @abstractmethod
    def create_collection(self, name: str, metadata: dict[str, Any]) -> UUID:
        pass

    @abstractmethod
    def add_documents(
        self, collection_name: str, documents: list[CollectionDocument], timestamp: str
    ) -> list[str]:
        pass

    @abstractmethod
    def get_collection(self, collection_name: str) -> CollectionResponse:
        pass

    @abstractmethod
    def get_collection_documents(
        self, collection_name: str
    ) -> list[CollectionDocument]:
        pass

    @abstractmethod
    def get_all_collections(self) -> list[CollectionResponse]:
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        pass

    @abstractmethod
    def delete_collection_documents(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def delete_documents(self, collection_name: str, doc_ids: list[str]) -> None:
        pass

    @abstractmethod
    def search_collection(
        self, collection_name: str, query: str
    ) -> list[CollectionDocument]:
        pass

    @abstractmethod
    def update_collection_timestamp(self, collection_name: str, timestamp: str) -> str:
        pass
