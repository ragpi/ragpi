from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from src.schemas.repository import RepositoryDocument, RepositoryResponse


class VectorStoreBase(ABC):
    @abstractmethod
    def create_repository(self, name: str, metadata: dict[str, Any]) -> UUID:
        pass

    @abstractmethod
    def add_documents(
        self, repository_name: str, documents: list[RepositoryDocument], timestamp: str
    ) -> list[str]:
        pass

    @abstractmethod
    def get_repository(self, repository_name: str) -> RepositoryResponse:
        pass

    @abstractmethod
    def get_repository_documents(
        self, repository_name: str
    ) -> list[RepositoryDocument]:
        pass

    @abstractmethod
    def get_all_repositories(self) -> list[RepositoryResponse]:
        pass

    @abstractmethod
    def delete_repository(self, repository_name: str) -> None:
        pass

    @abstractmethod
    def delete_repository_documents(self, repository_name: str) -> bool:
        pass

    @abstractmethod
    def delete_documents(self, repository_name: str, doc_ids: list[str]) -> None:
        pass

    @abstractmethod
    def search_repository(
        self, repository_name: str, query: str
    ) -> list[RepositoryDocument]:
        pass

    @abstractmethod
    def update_repository_timestamp(self, repository_name: str, timestamp: str) -> str:
        pass
