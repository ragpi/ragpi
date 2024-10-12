from typing import Any
import chromadb
from uuid import UUID
from chromadb.api.types import IncludeEnum, Metadata
from langchain_openai import OpenAIEmbeddings

from src.schemas.repository import RepositoryDocument, RepositoryResponse
from src.services.vector_store.base import VectorStoreBase


class ChromaVectorStore(VectorStoreBase):
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.embeddings_function = OpenAIEmbeddings(model="text-embedding-3-small")

    def create_repository(self, name: str, metadata: dict[str, Any]) -> UUID:
        collection = self.client.create_collection(name, metadata=metadata)
        return collection.id

    def add_documents(
        self, repository_name: str, documents: list[RepositoryDocument], timestamp: str
    ) -> list[str]:
        BATCH_SIZE = 10000
        collection = self.client.get_collection(repository_name)

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

            print(f"Adding {len(batch_ids)} documents to repository {repository_name}")

            collection.add(  # type: ignore
                ids=batch_ids,
                documents=batch_contents,
                metadatas=batch_metadatas,
                embeddings=batch_embeddings,  # type: ignore
            )

        return doc_ids

    def get_repository(self, repository_name: str) -> RepositoryResponse:
        collection = self.client.get_collection(repository_name)
        metadata = collection.metadata

        return RepositoryResponse(
            id=collection.id,
            name=collection.name,
            start_url=metadata["start_url"],
            source=metadata["source"],
            include_pattern=metadata.get("include_pattern"),
            exclude_pattern=metadata.get("exclude_pattern"),
            num_pages=metadata["num_pages"],
            num_documents=collection.count(),
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
        )

    def get_repository_documents(
        self, repository_name: str
    ) -> list[RepositoryDocument]:
        collection = self.client.get_collection(repository_name)
        collection_data = collection.get(
            include=[IncludeEnum.metadatas, IncludeEnum.documents]
        )

        return self._map_repository_documents(
            collection_data["ids"],
            collection_data["metadatas"],
            collection_data["documents"],
        )

    def get_all_repositories(self) -> list[RepositoryResponse]:
        collections = self.client.list_collections()

        return [
            RepositoryResponse(
                id=collection.id,
                name=collection.name,
                start_url=collection.metadata["start_url"],
                source=collection.metadata["source"],
                include_pattern=collection.metadata.get("include_pattern"),
                exclude_pattern=collection.metadata.get("exclude_pattern"),
                num_pages=collection.metadata["num_pages"],
                num_documents=collection.count(),
                created_at=collection.metadata["created_at"],
                updated_at=collection.metadata["updated_at"],
            )
            for collection in collections
        ]

    def delete_repository(self, repository_name: str) -> None:
        # TODO: Need custom exception handling for collection not found.
        self.client.delete_collection(repository_name)

    def delete_repository_documents(self, repository_name: str) -> bool:
        collection = self.client.get_collection(repository_name)
        doc_ids = collection.get(include=[])["ids"]

        if len(doc_ids) > 0:
            collection.delete(ids=doc_ids)

        return True

    def delete_documents(self, repository_name: str, doc_ids: list[str]) -> None:
        if len(doc_ids) == 0:
            return

        collection = self.client.get_collection(repository_name)
        collection.delete(ids=doc_ids)

    def search_repository(
        self, repository_name: str, query: str
    ) -> list[RepositoryDocument]:
        collection = self.client.get_collection(repository_name)

        query_embedding = self.embeddings_function.embed_query(query)

        collection_data = collection.query(  # type: ignore
            query_embeddings=[query_embedding],
            include=[IncludeEnum.metadatas, IncludeEnum.documents],
            n_results=10,
        )

        return self._map_repository_documents(
            collection_data["ids"][0],
            collection_data["metadatas"][0] if collection_data["metadatas"] else [],
            collection_data["documents"][0] if collection_data["documents"] else [],
        )

    def update_repository_timestamp(self, repository_name: str, timestamp: str) -> str:
        collection = self.client.get_collection(repository_name)

        collection_metadata = collection.metadata
        collection.modify(metadata={**collection_metadata, "updated_at": timestamp})

        return timestamp

    def _map_repository_documents(
        self,
        ids: list[str],
        metadatas: list[Metadata] | None,
        documents: list[str] | None,
    ) -> list[RepositoryDocument]:
        if not ids or not metadatas or not documents:
            raise ValueError(
                "Invalid data: 'ids', 'metadatas', or 'documents' are missing."
            )

        if len(ids) != len(metadatas) or len(ids) != len(documents):
            raise ValueError(
                "Mismatched lengths of 'ids', 'metadatas', and 'documents'."
            )

        repository_documents: list[RepositoryDocument] = []
        for doc_id, metadata, content in zip(ids, metadatas, documents):
            repository_doc = RepositoryDocument(
                id=doc_id, content=content, metadata=dict(metadata)
            )
            repository_documents.append(repository_doc)

        return repository_documents
