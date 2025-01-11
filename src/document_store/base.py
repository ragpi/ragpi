from abc import ABC, abstractmethod

from src.common.schemas import Document


class DocumentStoreService(ABC):
    @abstractmethod
    def add_documents(self, source_name: str, documents: list[Document]) -> None:
        pass

    @abstractmethod
    def get_documents(
        self, source_name: str, limit: int, offset: int
    ) -> list[Document]:
        pass

    @abstractmethod
    def get_document_ids(self, source_name: str) -> list[str]:
        pass

    @abstractmethod
    def delete_all_documents(self, source_name: str) -> None:
        pass

    @abstractmethod
    def delete_documents(self, source_name: str, doc_ids: list[str]) -> None:
        pass

    @abstractmethod
    def search_documents(
        self, source_name: str, query: str, top_k: int
    ) -> list[Document]:
        pass
