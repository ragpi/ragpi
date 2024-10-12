from typing import Optional, List
from uuid import UUID

from src.schemas.repository import (
    RepositoryDocument,
    RepositoryMetadata,
    RepositoryResponse,
)
from src.services.vector_store.factory import get_vector_store


class VectorStoreService:
    # TODO: Get default from env
    def __init__(self, provider: str = "chroma"):
        self.vector_store = get_vector_store(provider)

    def create_repository(
        self,
        name: str,
        source: str,
        start_url: str,
        num_pages: int,
        include_pattern: Optional[str],
        exclude_pattern: Optional[str],
        timestamp: str,
    ) -> UUID:

        metadata = RepositoryMetadata(
            source=source,
            start_url=start_url,
            num_pages=num_pages,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            created_at=timestamp,
            updated_at=timestamp,
        ).model_dump(exclude_none=True)

        repository_id = self.vector_store.create_repository(name, metadata)
        return repository_id

    def add_documents(
        self, repository_name: str, documents: List[RepositoryDocument], timestamp: str
    ) -> List[str]:
        return self.vector_store.add_documents(repository_name, documents, timestamp)

    def get_repository(self, repository_name: str) -> RepositoryResponse:
        return self.vector_store.get_repository(repository_name)

    def get_repository_documents(
        self, repository_name: str
    ) -> List[RepositoryDocument]:
        return self.vector_store.get_repository_documents(repository_name)

    def get_all_repositories(self) -> List[RepositoryResponse]:
        return self.vector_store.get_all_repositories()

    def delete_repository(self, repository_name: str) -> None:
        self.vector_store.delete_repository(repository_name)

    def delete_repository_documents(self, repository_name: str) -> bool:
        return self.vector_store.delete_repository_documents(repository_name)

    def delete_documents(self, repository_name: str, doc_ids: List[str]) -> None:
        self.vector_store.delete_documents(repository_name, doc_ids)

    def search_repository(
        self, repository_name: str, query: str
    ) -> List[RepositoryDocument]:
        return self.vector_store.search_repository(repository_name, query)

    def update_repository_timestamp(self, repository_name: str, timestamp: str) -> str:
        return self.vector_store.update_repository_timestamp(repository_name, timestamp)
