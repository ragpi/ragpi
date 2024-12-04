import json
from typing import Any
from langchain_openai import OpenAIEmbeddings
import numpy as np
from uuid import uuid4
from redisvl.index import SearchIndex  # type: ignore
from redisvl.schema import IndexSchema  # type: ignore
from redisvl.query import VectorQuery  # type: ignore
from redis.commands.search.query import Query

from src.config import settings
from src.document.schemas import Document
from src.exceptions import (
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    ResourceType,
)
from src.redis import get_redis_client
from src.source.schemas import (
    SourceConfig,
    SourceOverview,
    SourceType,
    SitemapConfig,
    GithubIssuesConfig,
)
from src.vector_store.base import VectorStoreBase
from src.vector_store.ranking import reciprocal_rank_fusion


SOURCE_DOC_SCHEMA: dict[str, Any] = {
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
    def __init__(self) -> None:
        self.client = get_redis_client()
        self.embeddings_function = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL, dimensions=settings.EMBEDDING_DIMENSIONS
        )
        self.schema: dict[str, Any] = SOURCE_DOC_SCHEMA
        self.document_fields = DOCUMENT_FIELDS

    def _get_index_prefix(self, source_name: str) -> str:
        return f"{source_name}:documents"

    def _get_metadata_key(self, source_name: str) -> str:
        return f"{source_name}:metadata"

    def _get_index(self, source_name: str, should_exist: bool = True) -> SearchIndex:
        prefix = self._get_index_prefix(source_name)

        index_schema = IndexSchema.from_dict(
            {
                "index": {"name": source_name, "prefix": prefix},
                **self.schema,
            }
        )
        index = SearchIndex(index_schema).set_client(self.client)  # type: ignore

        if source_name == "*":
            return index

        if should_exist and not index.exists():
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        if not should_exist and index.exists():
            raise ResourceAlreadyExistsException(ResourceType.SOURCE, source_name)

        return index

    def _extract_doc_id(self, source_name: str, key: str) -> str:
        prefix = self._get_index_prefix(source_name)
        return key.split(f"{prefix}:")[1]

    def _get_doc_key(self, source_name: str, doc_id: str) -> str:
        prefix = self._get_index_prefix(source_name)
        return f"{prefix}:{doc_id}"

    def create_source(
        self, name: str, config: SourceConfig, timestamp: str
    ) -> SourceOverview:
        index = self._get_index(name, False)

        index.create()

        metadata_key = self._get_metadata_key(name)
        id = str(uuid4())

        config_dict: dict[str, Any] = {}

        config_items = config.model_dump().items()

        for key, value in config_items:
            if isinstance(value, list):
                value = json.dumps(value)
            elif value is None:
                value = ""
            config_dict[f"config__{key}"] = value

        self.client.hset(
            metadata_key,
            mapping={
                "id": id,
                "name": name,
                **config_dict,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )

        return self.get_source(name)

    def add_source_documents(
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

    def get_source(self, name: str) -> SourceOverview:
        index = self._get_index(name)

        index_info = index.info()

        metadata_key = self._get_metadata_key(name)

        metadata = self.client.hgetall(metadata_key)

        source_type = metadata.get("config__type")

        source_config: SourceConfig

        if source_type == SourceType.SITEMAP:
            source_data: dict[str, Any] = {
                "type": source_type,
                "sitemap_url": metadata["config__sitemap_url"],
                "include_pattern": metadata["config__include_pattern"] or None,
                "exclude_pattern": metadata["config__exclude_pattern"] or None,
                "chunk_size": int(metadata["config__chunk_size"]),
                "chunk_overlap": int(metadata["config__chunk_overlap"]),
            }
            source_config = SitemapConfig(**source_data)
        elif source_type == SourceType.GITHUB_ISSUES:
            source_data = {
                "type": source_type,
                "repo_owner": metadata["config__repo_owner"],
                "repo_name": metadata["config__repo_name"],
                "state": metadata["config__state"] or None,
                "include_labels": metadata["config__include_labels"] or None,
                "exclude_labels": metadata["config__exclude_labels"] or None,
                "max_age": metadata["config__max_age"] or None,
            }

            source_data["include_labels"] = (
                json.loads(source_data["include_labels"])
                if source_data["include_labels"]
                else None
            )

            source_data["exclude_labels"] = (
                json.loads(source_data["exclude_labels"])
                if source_data["exclude_labels"]
                else None
            )

            source_config = GithubIssuesConfig(**source_data)
        else:
            raise ValueError(f"Unknown source type: {source_type}")

        return SourceOverview(
            id=metadata["id"],
            name=metadata["name"],
            num_docs=int(index_info["num_docs"]),
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
            config=source_config,
        )

    def get_source_documents(
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
                content=doc[1],
                metadata={
                    "url": doc[2],
                    "title": doc[3],
                    "header_1": doc[4],
                    "header_2": doc[5],
                    "header_3": doc[6],
                    "created_at": doc[7],
                },
            )
            for doc in docs
        ]

    def get_source_document_ids(self, name: str) -> list[str]:
        all_keys: list[str] = []

        for key in self.client.scan_iter(f"{name}:documents:*"):
            all_keys.append(key)

        return [self._extract_doc_id(name, key) for key in all_keys]

    def get_all_sources(self) -> list[SourceOverview]:
        index = self._get_index("*")

        source_names = index.listall()

        return [self.get_source(name) for name in source_names]

    def delete_source(self, name: str) -> None:
        index = self._get_index(name)

        if not index.exists():
            raise ResourceNotFoundException(ResourceType.SOURCE, name)

        index.delete()

        metadata_key = self._get_metadata_key(name)
        self.client.delete(metadata_key)

    def delete_source_documents(self, name: str, doc_ids: list[str]) -> None:
        index = self._get_index(name)

        ids = [self._get_doc_key(name, doc_id) for doc_id in doc_ids]

        index.drop_keys(ids)

    def map_search_results_to_documents(
        self, source_name: str, search_results: list[dict[str, Any]]
    ) -> list[Document]:
        return [
            Document(
                id=self._extract_doc_id(source_name, doc["id"]),
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
        self, index: SearchIndex, query: str, limit: int
    ) -> list[Document]:
        query_embedding = self.embeddings_function.embed_query(query)

        vector_query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=self.document_fields,
            num_results=limit,
        )

        # The results are sorted by distance by default
        search_results = index.query(vector_query)

        return self.map_search_results_to_documents(index.name, search_results)

    def full_text_search(
        self, index: SearchIndex, query: str, limit: int
    ) -> list[Document]:
        ft = self.client.ft(index.name)

        # Remove any leading or trailing quotation marks
        cleaned_query = query.strip("'\"")

        # Join the query with OR operator to search for any of the words
        formatted_query = " | ".join(cleaned_query.split())

        query_obj = (  # type: ignore
            Query(formatted_query)  # type: ignore
            .paging(0, limit)
            .scorer("BM25")
            .return_fields(*self.document_fields)
        )

        # The results are sorted by score (BM25) by default
        search_results = ft.search(query_obj)  # type: ignore
        return self.map_search_results_to_documents(index.name, search_results.docs)

    def search_source(self, name: str, query: str, limit: int) -> list[Document]:
        index = self._get_index(name)

        vector_search_results = self.vector_based_search(index, query, limit)

        text_search_results = self.full_text_search(index, query, limit)

        return reciprocal_rank_fusion(
            [vector_search_results, text_search_results], limit
        )

    def update_source_metadata(
        self, name: str, config: SourceConfig, timestamp: str
    ) -> SourceOverview:
        metadata_key = self._get_metadata_key(name)

        config_dict: dict[str, Any] = {}

        config_items = config.model_dump().items()

        for key, value in config_items:
            if isinstance(value, list):
                value = json.dumps(value)
            if value is None:
                value = ""
            config_dict[f"config__{key}"] = value

        self.client.hset(
            metadata_key,
            mapping={
                **config_dict,
                "updated_at": timestamp,
            },
        )

        return self.get_source(name)
