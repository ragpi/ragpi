from typing import Any
from langchain_openai import OpenAIEmbeddings
import numpy as np
from uuid import uuid4
from redisvl.index import SearchIndex  # type: ignore
from redisvl.schema import IndexSchema  # type: ignore
from redisvl.query import VectorQuery, BaseQuery  # type: ignore

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
from src.vector_store.ranking import reciprocal_rank_fusion


REPOSITORY_DOC_SCHEMA: dict[str, Any] = {
    "fields": [
        {"name": "id", "type": "tag"},
        {"name": "content", "type": "text"},
        {"name": "url", "type": "tag"},
        {"name": "created_at", "type": "tag"},
        {"name": "title", "type": "text"},
        {"name": "header_1", "type": "text"},
        {"name": "header_2", "type": "text"},
        {"name": "header_3", "type": "text"},
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

DOCUMENT_FIELDS = [
    "id",
    "content",
    "url",
    "title",
    "header_1",
    "header_2",
    "header_3",
    "created_at",
]


class RedisVectorStore(VectorStoreBase):
    def __init__(self):
        self.client = get_redis_client()
        self.embeddings_function = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL, dimensions=settings.EMBEDDING_DIMENSIONS
        )
        self.schema: dict[str, Any] = REPOSITORY_DOC_SCHEMA
        self.document_fields = DOCUMENT_FIELDS

    def _get_index_prefix(self, repository_name: str) -> str:
        return f"{repository_name}:documents"

    def _get_metadata_key(self, repository_name: str) -> str:
        return f"{repository_name}:metadata"

    def _get_index(
        self, repository_name: str, should_exist: bool = True
    ) -> SearchIndex:
        prefix = self._get_index_prefix(repository_name)

        index_schema = IndexSchema.from_dict(
            {
                "index": {"name": repository_name, "prefix": prefix},
                **self.schema,
            }
        )
        index = SearchIndex(index_schema).set_client(self.client)  # type: ignore

        if repository_name == "*":
            return index

        if should_exist and not index.exists():
            raise ResourceNotFoundException(ResourceType.REPOSITORY, repository_name)

        if not should_exist and index.exists():
            raise ResourceAlreadyExistsException(
                ResourceType.REPOSITORY, repository_name
            )

        return index

    def _extract_doc_id(self, repository_name: str, key: str) -> str:
        prefix = self._get_index_prefix(repository_name)
        return key.split(f"{prefix}:")[1]

    def _get_doc_key(self, repository_name: str, doc_id: str) -> str:
        prefix = self._get_index_prefix(repository_name)
        return f"{prefix}:{doc_id}"

    def create_repository(
        self, name: str, config: RepositoryConfig, timestamp: str
    ) -> RepositoryOverview:
        index = self._get_index(name, False)

        index.create()

        metadata_key = self._get_metadata_key(name)
        id = str(uuid4())

        self.client.hset(
            metadata_key,
            mapping={
                "id": id,
                "name": name,
                "sitemap_url": config.sitemap_url,
                "include_pattern": config.include_pattern or "",
                "exclude_pattern": config.exclude_pattern or "",
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

        ids = [self._extract_doc_id(name, key) for key in keys]

        return ids

    def get_repository(self, name: str) -> RepositoryOverview:
        index = self._get_index(name)

        index_info = index.info()

        metadata_key = self._get_metadata_key(name)

        metadata = self.client.hgetall(metadata_key)

        config = RepositoryConfig(
            sitemap_url=metadata["sitemap_url"],
            include_pattern=metadata["include_pattern"] or None,
            exclude_pattern=metadata["exclude_pattern"] or None,
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
                *self.document_fields,
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
        all_keys: list[str] = []

        for key in self.client.scan_iter(f"{name}:documents:*"):
            all_keys.append(key)

        return [self._extract_doc_id(name, key) for key in all_keys]

    def get_all_repositories(self) -> list[RepositoryOverview]:
        index = self._get_index("*")

        repo_names = index.listall()

        return [self.get_repository(name) for name in repo_names]

    def delete_repository(self, name: str) -> None:
        index = self._get_index(name)

        if not index.exists():
            raise ResourceNotFoundException(ResourceType.REPOSITORY, name)

        index.delete()

        metadata_key = self._get_metadata_key(name)
        self.client.delete(metadata_key)

    def delete_repository_documents(self, name: str, doc_ids: list[str]) -> None:
        index = self._get_index(name)

        ids = [self._get_doc_key(name, doc_id) for doc_id in doc_ids]

        index.drop_keys(ids)

    def map_search_results_to_documents(
        self, repository_name: str, search_results: list[dict[str, Any]]
    ) -> list[Document]:
        return [
            Document(
                id=self._extract_doc_id(repository_name, doc["id"]),
                content=doc["content"],
                metadata={
                    "url": doc["url"],
                    "title": doc["title"],
                    "created_at": doc["created_at"],
                    **{
                        header: doc[header]
                        for header in ["header_1", "header_2", "header_3"]
                        if hasattr(doc, header)
                    },
                },
            )
            for doc in search_results
        ]

    def vector_based_search(
        self, index: SearchIndex, query: str, num_results: int
    ) -> list[Document]:
        query_embedding = self.embeddings_function.embed_query(query)

        vector_query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=self.document_fields,
            num_results=num_results,
        )

        # The results are already sorted by distance by default
        search_results = index.query(vector_query)

        return self.map_search_results_to_documents(index.name, search_results)

    def full_text_search(
        self, index: SearchIndex, query: str, num_results: int
    ) -> list[Document]:
        text_query = (  # type: ignore
            BaseQuery(query)  # type: ignore
            .paging(0, num_results)
            .scorer("BM25")
            .return_fields(
                *self.document_fields,
            )
        )

        # The results are already sorted by BM25 score by default
        search_results = index.search(text_query)  # type: ignore

        return self.map_search_results_to_documents(index.name, search_results.docs)

    def search_repository(
        self, name: str, query: str, num_results: int
    ) -> list[Document]:
        index = self._get_index(name)

        vector_search_results = self.vector_based_search(index, query, num_results)

        text_search_results = self.full_text_search(index, query, num_results)

        return reciprocal_rank_fusion(
            [vector_search_results, text_search_results], num_results
        )

    def update_repository_metadata(
        self, name: str, config: RepositoryConfig, timestamp: str
    ) -> RepositoryOverview:
        metadata_key = self._get_metadata_key(name)

        self.client.hset(
            metadata_key,
            mapping={
                "sitemap_url": config.sitemap_url,
                "include_pattern": config.include_pattern or "",
                "exclude_pattern": config.exclude_pattern or "",
                "chunk_size": config.chunk_size,
                "chunk_overlap": config.chunk_overlap,
                "updated_at": timestamp,
            },
        )

        return self.get_repository(name)
