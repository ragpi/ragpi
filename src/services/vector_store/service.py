from typing import Optional, List

from src.config import settings
from src.schemas.repository import (
    RepositoryDocument,
    RepositoryMetadata,
    RepositoryOverview,
)
from src.services.vector_store.factory import get_vector_store
from src.utils.current_datetime import current_datetime


class VectorStoreService:
    def __init__(self, provider: str = settings.VECTOR_STORE_PROVIDER):
        self.vector_store = get_vector_store(provider)

    async def create_repository(
        self,
        name: str,
        start_url: str,
        num_pages: int,
        include_pattern: Optional[str],
        exclude_pattern: Optional[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> str:

        timestamp = current_datetime()

        metadata = RepositoryMetadata(
            start_url=start_url,
            num_pages=num_pages,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        repository_id = await self.vector_store.create_repository(
            name, metadata, timestamp
        )
        return repository_id

    async def add_repository_documents(
        self, name: str, documents: List[RepositoryDocument]
    ) -> List[str]:
        if not documents:
            return []

        timestamp = current_datetime()

        return await self.vector_store.add_repository_documents(
            name, documents, timestamp
        )

    async def get_repository(self, name: str) -> RepositoryOverview:
        return await self.vector_store.get_repository(name)

    async def get_repository_documents(
        self, name: str, limit: int | None, offset: int | None
    ) -> List[RepositoryDocument]:
        return await self.vector_store.get_repository_documents(name, limit, offset)

    async def get_repository_document_ids(self, name: str) -> List[str]:
        return await self.vector_store.get_repository_document_ids(name)

    async def get_all_repositories(self) -> List[RepositoryOverview]:
        return await self.vector_store.get_all_repositories()

    async def delete_repository(self, name: str) -> None:
        await self.vector_store.delete_repository(name)

    async def delete_repository_documents(self, name: str, doc_ids: List[str]) -> None:
        if not doc_ids:
            return

        await self.vector_store.delete_repository_documents(name, doc_ids)

    async def search_repository(
        self, name: str, query: str, num_results: int
    ) -> List[RepositoryDocument]:
        return await self.vector_store.search_repository(name, query, num_results)

    async def update_repository_metadata(
        self, name: str, metadata: RepositoryMetadata
    ) -> RepositoryOverview:
        timestamp = current_datetime()

        return await self.vector_store.update_repository_metadata(
            name, metadata, timestamp
        )
