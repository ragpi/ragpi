from abc import ABC, abstractmethod

from src.document.schemas import Document


class VectorStoreBase(ABC):
    @abstractmethod
    def add_source_documents(self, name: str, documents: list[Document]) -> list[str]:
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
    def get_document_count(self, name: str) -> int:
        pass

    @abstractmethod
    def delete_source(self, name: str) -> None:
        pass

    @abstractmethod
    def delete_source_documents(self, name: str, doc_ids: list[str]) -> None:
        pass

    @abstractmethod
    def search_source(self, name: str, query: str, top_k: int) -> list[Document]:
        pass
