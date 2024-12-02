from abc import ABC, abstractmethod

from src.document.schemas import Document
from src.repository.schemas import (
    RepositorySource,
    RepositoryOverview,
)


class VectorStoreBase(ABC):
    @abstractmethod
    def create_repository(
        self, name: str, source: RepositorySource, timestamp: str
    ) -> RepositoryOverview:
        pass

    @abstractmethod
    def add_repository_documents(
        self, name: str, documents: list[Document], timestamp: str
    ) -> list[str]:
        pass

    @abstractmethod
    def get_repository(self, name: str) -> RepositoryOverview:
        pass

    @abstractmethod
    def get_repository_documents(
        self, name: str, limit: int | None, offset: int | None
    ) -> list[Document]:
        pass

    @abstractmethod
    def get_repository_document_ids(self, name: str) -> list[str]:
        pass

    @abstractmethod
    def get_all_repositories(self) -> list[RepositoryOverview]:
        pass

    @abstractmethod
    def delete_repository(self, name: str) -> None:
        pass

    @abstractmethod
    def delete_repository_documents(self, name: str, doc_ids: list[str]) -> None:
        pass

    @abstractmethod
    def search_repository(self, name: str, query: str, limit: int) -> list[Document]:
        pass

    @abstractmethod
    def update_repository_metadata(
        self, name: str, source: RepositorySource, timestamp: str
    ) -> RepositoryOverview:
        pass
