from abc import ABC, abstractmethod

from src.document_store.schemas import Document


class DocumentStoreBackend(ABC):
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
    def hybrid_search(
        self, *, source_name: str, semantic_query: str, full_text_query: str, top_k: int
    ) -> list[Document]:
        pass
