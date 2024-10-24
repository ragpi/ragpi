from abc import ABC, abstractmethod

from src.document.schemas import Document
from src.repository.schemas import (
    RepositoryMetadata,
    RepositoryOverview,
)


class VectorStoreBase(ABC):
    @abstractmethod
    async def create_repository(
        self, name: str, metadata: RepositoryMetadata, timestamp: str
    ) -> RepositoryOverview:
        pass

    @abstractmethod
    async def add_repository_documents(
        self, name: str, documents: list[Document], timestamp: str
    ) -> list[str]:
        pass

    @abstractmethod
    async def get_repository(self, name: str) -> RepositoryOverview:
        pass

    @abstractmethod
    async def get_repository_documents(
        self, name: str, limit: int | None, offset: int | None
    ) -> list[Document]:
        pass

    @abstractmethod
    async def get_repository_document_ids(self, name: str) -> list[str]:
        pass

    @abstractmethod
    async def get_all_repositories(self) -> list[RepositoryOverview]:
        pass

    @abstractmethod
    async def delete_repository(self, name: str) -> None:
        pass

    @abstractmethod
    async def delete_repository_documents(self, name: str, doc_ids: list[str]) -> None:
        pass

    @abstractmethod
    async def search_repository(
        self, name: str, query: str, num_results: int
    ) -> list[Document]:
        pass

    @abstractmethod
    async def update_repository_metadata(
        self, name: str, metadata: RepositoryMetadata, timestamp: str
    ) -> RepositoryOverview:
        pass
