from typing import Optional, List

from src.schemas.repository import (
    RepositoryDocument,
    RepositoryMetadata,
    RepositoryResponse,
)
from src.services.vector_store.factory import get_vector_store


class VectorStoreService:
    # TODO: Get default from env
    def __init__(self, provider: str = "redis"):
        self.vector_store = get_vector_store(provider)

    async def create_repository(
        self,
        name: str,
        source: str,
        start_url: str,
        num_pages: int,
        include_pattern: Optional[str],
        exclude_pattern: Optional[str],
        timestamp: str,
    ) -> str:

        metadata = RepositoryMetadata(
            source=source,
            start_url=start_url,
            num_pages=num_pages,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            created_at=timestamp,
            updated_at=timestamp,
        )

        repository_id = await self.vector_store.create_repository(name, metadata)
        return repository_id

    async def add_documents(
        self, repository_name: str, documents: List[RepositoryDocument], timestamp: str
    ) -> List[str]:
        return await self.vector_store.add_documents(
            repository_name, documents, timestamp
        )

    async def get_repository(self, repository_name: str) -> RepositoryResponse:
        return await self.vector_store.get_repository(repository_name)

    async def get_repository_documents(
        self, repository_name: str
    ) -> List[RepositoryDocument]:
        return await self.vector_store.get_repository_documents(repository_name)

    async def get_all_repositories(self) -> List[RepositoryResponse]:
        return await self.vector_store.get_all_repositories()

    async def delete_repository(self, repository_name: str) -> None:
        await self.vector_store.delete_repository(repository_name)

    async def delete_repository_documents(self, repository_name: str) -> bool:
        return await self.vector_store.delete_repository_documents(repository_name)

    async def delete_documents(self, repository_name: str, doc_ids: List[str]) -> None:
        await self.vector_store.delete_documents(repository_name, doc_ids)

    async def search_repository(
        self, repository_name: str, query: str
    ) -> List[RepositoryDocument]:
        return await self.vector_store.search_repository(repository_name, query)

    async def update_repository_timestamp(
        self, repository_name: str, timestamp: str
    ) -> str:
        return await self.vector_store.update_repository_timestamp(
            repository_name, timestamp
        )
