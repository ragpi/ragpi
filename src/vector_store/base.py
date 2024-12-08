from abc import ABC, abstractmethod

from src.document.schemas import Document
from src.source.schemas import (
    SourceConfig,
    SourceOverview,
)


class VectorStoreBase(ABC):
    @abstractmethod
    def create_source(
        self, name: str, description: str, config: SourceConfig, timestamp: str
    ) -> SourceOverview:
        pass

    @abstractmethod
    def add_source_documents(self, name: str, documents: list[Document]) -> list[str]:
        pass

    @abstractmethod
    def get_source(self, name: str) -> SourceOverview:
        pass

    @abstractmethod
    def get_source_documents(
        self, name: str, limit: int | None, offset: int | None
    ) -> list[Document]:
        pass

    @abstractmethod
    def get_source_document_ids(self, name: str) -> list[str]:
        pass

    @abstractmethod
    def get_all_sources(self) -> list[SourceOverview]:
        pass

    @abstractmethod
    def delete_source(self, name: str) -> None:
        pass

    @abstractmethod
    def delete_source_documents(self, name: str, doc_ids: list[str]) -> None:
        pass

    @abstractmethod
    def search_source(self, name: str, query: str, limit: int) -> list[Document]:
        pass

    @abstractmethod
    def update_source_metadata(
        self,
        name: str,
        description: str | None,
        config: SourceConfig | None,
        timestamp: str,
    ) -> SourceOverview:
        pass
