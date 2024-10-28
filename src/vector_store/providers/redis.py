from typing import Any
from langchain_openai import OpenAIEmbeddings
import numpy as np
from uuid import uuid4
from redisvl.index import SearchIndex  # type: ignore
from redisvl.schema import IndexSchema  # type: ignore
from redisvl.query import VectorQuery  # type: ignore

from src.config import settings
from src.document.schemas import Document
from src.exceptions import (
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    ResourceType,
)
from src.redis import get_redis_client
from src.repository.schemas import (
    RepositoryConfig,
    RepositoryOverview,
)
from src.vector_store.base import VectorStoreBase


REPOSITORY_DOC_SCHEMA: dict[str, Any] = {
    "fields": [
        {"name": "id", "type": "tag"},
        {"name": "content", "type": "text"},
        {"name": "url", "type": "tag"},
        {"name": "created_at", "type": "tag"},
        {"name": "title", "type": "tag"},
        {"name": "header_1", "type": "tag"},
        {"name": "header_2", "type": "tag"},
        {"name": "header_3", "type": "tag"},
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {
                "dims": settings.EMBEDDING_DIMENSIONS,
                "distance_metric": "cosine",
                "algorithm": "flat",
                "datatype": "float32",
            },
        },
    ],
}


class RedisVectorStore(VectorStoreBase):
    def __init__(self):
        self.client = get_redis_client()
        self.embeddings_function = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL, dimensions=settings.EMBEDDING_DIMENSIONS
        )
        self.schema: dict[str, Any] = REPOSITORY_DOC_SCHEMA

    def _get_index(self, name: str, should_exist: bool = True) -> SearchIndex:
        index_schema = IndexSchema.from_dict(
            {
                "index": {"name": name, "prefix": f"{name}:documents"},
                **self.schema,
            }
        )
        index = SearchIndex(index_schema).set_client(self.client)  # type: ignore

        if name == "*":
            return index

        if should_exist and not index.exists():
            raise ResourceNotFoundException(ResourceType.REPOSITORY, name)

        if not should_exist and index.exists():
            raise ResourceAlreadyExistsException(ResourceType.REPOSITORY, name)

        return index

    def _extract_doc_id(self, prefix: str, key: str) -> str:
        return key.split(f"{prefix}:")[1]

    def _get_doc_key(self, prefix: str, doc_id: str) -> str:
        return f"{prefix}:{doc_id}"

    def create_repository(
        self, name: str, config: RepositoryConfig, timestamp: str
    ) -> RepositoryOverview:
        index = self._get_index(name, False)

        index.create()

        metadata_key = f"{name}:metadata"
        id = str(uuid4())

        self.client.hset(
            metadata_key,
            mapping={
                "id": id,
                "name": name,
                "start_url": config.start_url,
                "include_pattern": config.include_pattern or "",
                "exclude_pattern": config.exclude_pattern or "",
                "page_limit": config.page_limit or "",
                "chunk_size": config.chunk_size,
                "chunk_overlap": config.chunk_overlap,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )

        return self.get_repository(name)

    def add_repository_documents(
        self, name: str, documents: list[Document], timestamp: str
    ) -> list[str]:
        index = self._get_index(name)

        doc_embeddings = self.embeddings_function.embed_documents(
            [doc.content for doc in documents]
        )

        def create_doc_dict(doc: Document, embedding: list[float]) -> dict[str, Any]:
            doc_dict: dict[str, Any] = {
                "id": doc.id,
                "content": doc.content,
                "created_at": timestamp,
                "embedding": np.array(embedding, dtype=np.float32).tobytes(),
            }

            for key in [
                "url",
                "title",
                "header_1",
                "header_2",
                "header_3",
            ]:
                if key in doc.metadata:
                    doc_dict[key] = doc.metadata[key]
            return doc_dict

        data = [
            create_doc_dict(doc, embedding)
            for doc, embedding in zip(documents, doc_embeddings)
        ]

        keys = index.load(id_field="id", data=data)  # type: ignore

        ids = [self._extract_doc_id(index.prefix, key) for key in keys]

        return ids

    def get_repository(self, name: str) -> RepositoryOverview:
        index = self._get_index(name)

        index_info = index.info()

        metadata_key = f"{name}:metadata"

        metadata = self.client.hgetall(metadata_key)

        config = RepositoryConfig(
            start_url=metadata["start_url"],
            include_pattern=metadata["include_pattern"] or None,
            exclude_pattern=metadata["exclude_pattern"] or None,
            page_limit=int(metadata["page_limit"]) if metadata["page_limit"] else None,
            chunk_size=int(metadata["chunk_size"]),
            chunk_overlap=int(metadata["chunk_overlap"]),
        )

        return RepositoryOverview(
            id=metadata["id"],
            name=metadata["name"],
            num_docs=index_info["num_docs"],
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
            config=config,
        )

    def get_repository_documents(
        self, name: str, limit: int | None, offset: int | None
    ) -> list[Document]:
        self._get_index(name)

        all_keys: list[str] = []

        for key in self.client.scan_iter(f"{name}:documents:*"):
            all_keys.append(key)

        start = offset or 0
        end = start + limit if limit else len(all_keys)

        keys = all_keys[start:end]

        pipeline = self.client.pipeline()

        for key in keys:
            pipeline.hmget(
                key,
                [
                    "id",
                    "url",
                    "title",
                    "header_1",
                    "header_2",
                    "header_3",
                    "created_at",
                    "content",
                ],
            )

        docs = pipeline.execute()

        return [
            Document(
                id=doc[0],
                content=doc[7],
                metadata={
                    "url": doc[1],
                    "title": doc[2],
                    "header_1": doc[3],
                    "header_2": doc[4],
                    "header_3": doc[5],
                    "created_at": doc[6],
                },
            )
            for doc in docs
        ]

    def get_repository_document_ids(self, name: str) -> list[str]:
        index = self._get_index(name)

        all_keys: list[str] = []

        for key in self.client.scan_iter(f"{name}:documents:*"):
            all_keys.append(key)

        return [self._extract_doc_id(index.prefix, key) for key in all_keys]

    def get_all_repositories(self) -> list[RepositoryOverview]:
        index = self._get_index("*")

        repo_names = index.listall()

        return [self.get_repository(name) for name in repo_names]

    def delete_repository(self, name: str) -> None:
        index = self._get_index(name)

        if not index.exists():
            raise ResourceNotFoundException(ResourceType.REPOSITORY, name)

        index.delete()

        metadata_key = f"{name}:metadata"
        self.client.delete(metadata_key)

    def delete_repository_documents(self, name: str, doc_ids: list[str]) -> None:
        index = self._get_index(name)

        ids = [self._get_doc_key(index.prefix, doc_id) for doc_id in doc_ids]

        index.drop_keys(ids)

    def search_repository(
        self, name: str, query: str, num_results: int
    ) -> list[Document]:
        index = self._get_index(name)

        query_embedding = self.embeddings_function.embed_query(query)

        vector_query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=[
                "id",
                "content",
                "url",
                "title",
                "header_1",
                "header_2",
                "header_3",
                "created_at",
            ],
            num_results=num_results,
        )

        search_results = index.query(vector_query)

        repository_documents = [
            Document(
                id=self._extract_doc_id(index.prefix, doc["id"]),
                content=doc["content"],
                metadata={
                    "url": doc["url"],
                    "title": doc["title"],
                    "created_at": doc["created_at"],
                    **{
                        header: doc[header]
                        for header in ["header_1", "header_2", "header_3"]
                        if header in doc
                    },
                },
            )
            for doc in search_results
        ]

        return repository_documents

    def update_repository_metadata(
        self, name: str, config: RepositoryConfig, timestamp: str
    ) -> RepositoryOverview:
        metadata_key = f"{name}:metadata"

        self.client.hset(
            metadata_key,
            mapping={
                "start_url": config.start_url,
                "include_pattern": config.include_pattern or "",
                "exclude_pattern": config.exclude_pattern or "",
                "page_limit": config.page_limit or "",
                "chunk_size": config.chunk_size,
                "chunk_overlap": config.chunk_overlap,
                "updated_at": timestamp,
            },
        )

        return self.get_repository(name)
