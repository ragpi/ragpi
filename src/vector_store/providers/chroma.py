from typing import Any
import chromadb
from chromadb.api.types import IncludeEnum, Metadata
from chromadb.errors import InvalidCollectionException
from chromadb.db.base import UniqueConstraintError
from langchain_openai import OpenAIEmbeddings

from src.config import settings
from src.document.schemas import Document
from src.exceptions import (
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    ResourceType,
)
from src.repository.schemas import (
    RepositoryConfig,
    RepositoryOverview,
)
from src.vector_store.base import VectorStoreBase


class ChromaVectorStore(VectorStoreBase):
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.embeddings_function = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)

    def _map_collection_overview(
        self, collection: chromadb.Collection
    ) -> RepositoryOverview:
        metadata = collection.metadata

        return RepositoryOverview(
            id=str(collection.id),
            name=collection.name,
            start_url=metadata["start_url"],
            include_pattern=metadata.get("include_pattern"),
            exclude_pattern=metadata.get("exclude_pattern"),
            page_limit=metadata.get("page_limit"),
            num_docs=collection.count(),
            chunk_size=metadata["chunk_size"],
            chunk_overlap=metadata["chunk_overlap"],
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
        )

    def _map_repository_documents(
        self,
        ids: list[str],
        metadatas: list[Metadata] | None,
        documents: list[str] | None,
    ) -> list[Document]:
        if not ids or not metadatas or not documents:
            raise ValueError(
                "Invalid data: 'ids', 'metadatas', or 'documents' are missing."
            )

        if len(ids) != len(metadatas) or len(ids) != len(documents):
            raise ValueError(
                "Mismatched lengths of 'ids', 'metadatas', and 'documents'."
            )

        repository_documents: list[Document] = []
        for doc_id, metadata, content in zip(ids, metadatas, documents):
            repository_doc = Document(
                id=doc_id, content=content, metadata=dict(metadata)
            )
            repository_documents.append(repository_doc)

        return repository_documents

    async def create_repository(
        self, name: str, config: RepositoryConfig, timestamp: str
    ) -> RepositoryOverview:
        try:
            metadata: dict[str, Any] = {
                **config.model_dump(exclude_none=True),
                "created_at": timestamp,
                "updated_at": timestamp,
            }

            collection = self.client.create_collection(name, metadata=metadata)
            return self._map_collection_overview(collection)
        except UniqueConstraintError as e:
            raise ResourceAlreadyExistsException(ResourceType.REPOSITORY, name) from e

    async def add_repository_documents(
        self, name: str, documents: list[Document], timestamp: str
    ) -> list[str]:
        BATCH_SIZE = 10000
        collection = self.client.get_collection(name)

        doc_ids: list[str] = []
        doc_contents: list[str] = []
        doc_metadatas: list[Metadata] = []

        for doc in documents:
            doc.metadata["created_at"] = timestamp
            doc_ids.append(doc.id)
            doc_metadatas.append(doc.metadata)
            doc_contents.append(doc.content)

        doc_embeddings = self.embeddings_function.embed_documents(doc_contents)

        for i in range(0, len(doc_ids), BATCH_SIZE):
            batch_ids = doc_ids[i : i + BATCH_SIZE]
            batch_contents = doc_contents[i : i + BATCH_SIZE]
            batch_metadatas = doc_metadatas[i : i + BATCH_SIZE]
            batch_embeddings = doc_embeddings[i : i + BATCH_SIZE]

            collection.add(  # type: ignore
                ids=batch_ids,
                documents=batch_contents,
                metadatas=batch_metadatas,
                embeddings=batch_embeddings,  # type: ignore
            )

        return doc_ids

    async def get_repository(self, name: str) -> RepositoryOverview:
        try:
            collection = self.client.get_collection(name)
            return self._map_collection_overview(collection)
        except InvalidCollectionException as e:
            raise ResourceNotFoundException(ResourceType.REPOSITORY, name) from e

    async def get_repository_documents(
        self, name: str, limit: int | None, offset: int | None
    ) -> list[Document]:
        try:
            collection = self.client.get_collection(name)
            collection_data = collection.get(
                include=[IncludeEnum.metadatas, IncludeEnum.documents],
                limit=limit,
                offset=offset,
            )

            return self._map_repository_documents(
                collection_data["ids"],
                collection_data["metadatas"],
                collection_data["documents"],
            )
        except InvalidCollectionException as e:
            raise ResourceNotFoundException(ResourceType.REPOSITORY, name) from e

    async def get_repository_document_ids(self, name: str) -> list[str]:
        try:
            collection = self.client.get_collection(name)
            collection_data = collection.get(include=[])

            return collection_data["ids"]
        except InvalidCollectionException as e:
            raise ResourceNotFoundException(ResourceType.REPOSITORY, name) from e

    async def get_all_repositories(self) -> list[RepositoryOverview]:
        collections = self.client.list_collections()

        return [self._map_collection_overview(collection) for collection in collections]

    async def delete_repository(self, name: str) -> None:
        try:
            self.client.delete_collection(name)
        except InvalidCollectionException as e:
            raise ResourceNotFoundException(ResourceType.REPOSITORY, name) from e

    async def delete_repository_documents(self, name: str, doc_ids: list[str]) -> None:
        if len(doc_ids) == 0:
            return

        try:
            collection = self.client.get_collection(name)
            collection.delete(ids=doc_ids)
        except InvalidCollectionException as e:
            raise ResourceNotFoundException(ResourceType.REPOSITORY, name) from e

    async def search_repository(
        self, name: str, query: str, num_results: int
    ) -> list[Document]:
        try:
            collection = self.client.get_collection(name)

            query_embedding = self.embeddings_function.embed_query(query)

            collection_data = collection.query(  # type: ignore
                query_embeddings=[query_embedding],
                include=[IncludeEnum.metadatas, IncludeEnum.documents],
                n_results=num_results,
            )

            return self._map_repository_documents(
                collection_data["ids"][0],
                collection_data["metadatas"][0] if collection_data["metadatas"] else [],
                collection_data["documents"][0] if collection_data["documents"] else [],
            )
        except InvalidCollectionException as e:
            raise ResourceNotFoundException(ResourceType.REPOSITORY, name) from e

    async def update_repository_metadata(
        self, name: str, config: RepositoryConfig, timestamp: str
    ) -> RepositoryOverview:
        try:
            existing_metadata = self.client.get_collection(name).metadata

            new_metadata: dict[str, Any] = {
                **config.model_dump(exclude_none=True),
                "created_at": existing_metadata["created_at"],
                "updated_at": timestamp,
            }

            collection = self.client.get_collection(name)
            collection.modify(metadata=new_metadata)

            return self._map_collection_overview(collection)
        except InvalidCollectionException as e:
            raise ResourceNotFoundException(ResourceType.REPOSITORY, name) from e
