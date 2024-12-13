import json
import re
from typing import Any
import numpy as np
from uuid import uuid4
from openai import OpenAI
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
from src.source.config import SOURCE_CONFIG_REGISTRY, SourceConfig
from src.source.schemas import (
    SourceOverview,
)
from src.vector_store.base import VectorStoreBase
from src.vector_store.providers.redis.index_schema import (
    DOCUMENT_FIELDS,
    DOCUMENT_SCHEMA,
)
from src.vector_store.ranking import reciprocal_rank_fusion


class RedisVectorStore(VectorStoreBase):
    def __init__(self) -> None:
        self.client = get_redis_client()
        self.embedding_model = settings.EMBEDDING_MODEL
        self.embedding_dimensions = settings.EMBEDDING_DIMENSIONS
        self.embedding_client = OpenAI().embeddings
        self.document_schema: dict[str, Any] = DOCUMENT_SCHEMA
        self.document_fields = DOCUMENT_FIELDS
        self.source_config_classes = SOURCE_CONFIG_REGISTRY
        self.config_prefix = "config__"

    def _get_index_prefix(self, source_name: str) -> str:
        return f"{source_name}:documents"

    def _get_metadata_key(self, source_name: str) -> str:
        return f"{source_name}:metadata"

    def _get_index(self, source_name: str, should_exist: bool = True) -> SearchIndex:
        prefix = self._get_index_prefix(source_name)

        index_schema = IndexSchema.from_dict(
            {
                "index": {"name": source_name, "prefix": prefix},
                **self.document_schema,
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
        self, name: str, description: str, config: SourceConfig, timestamp: str
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
            elif isinstance(value, bool):
                value = int(value)  # 1 for True, 0 for False
            elif value is None:
                value = ""
            config_dict[f"{self.config_prefix}{key}"] = value

        self.client.hset(
            metadata_key,
            mapping={
                "id": id,
                "name": name,
                "description": description,
                **config_dict,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )

        return self.get_source(name)

    def add_source_documents(self, name: str, documents: list[Document]) -> list[str]:
        index = self._get_index(name)

        embeddings_data = self.embedding_client.create(
            input=[doc.content for doc in documents],
            model=self.embedding_model,
            dimensions=self.embedding_dimensions,
        ).data

        doc_embeddings = [embedding.embedding for embedding in embeddings_data]

        def create_doc_dict(doc: Document, embedding: list[float]) -> dict[str, Any]:
            doc_dict: dict[str, Any] = {
                "id": doc.id,
                "content": doc.content,
                "title": doc.title,
                "url": doc.url,
                "created_at": doc.created_at,
                "embedding": np.array(embedding, dtype=np.float32).tobytes(),
            }
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

        source_type = metadata.get(f"{self.config_prefix}type")
        if source_type not in self.source_config_classes:
            raise ValueError(f"Unknown source type: {source_type}")

        config_dict: dict[str, Any] = {}
        for key, value in metadata.items():
            if key.startswith(f"{self.config_prefix}"):
                config_key = key.split(f"{self.config_prefix}")[1]
                config_dict[config_key] = value

        # The pydantic models defined in SOURCE_CONFIG_REGISTRY should be able to parse the string inputs
        source_config = self.source_config_classes[source_type](**config_dict)

        return SourceOverview(
            id=metadata["id"],
            name=metadata["name"],
            description=metadata["description"],
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
                title=doc[3],
                url=doc[2],
                created_at=doc[4],
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
                title=doc["title"],
                url=doc["url"],
                created_at=doc["created_at"],
            )
            for doc in search_results
        ]

    def vector_based_search(
        self, index: SearchIndex, query: str, top_k: int
    ) -> list[Document]:
        query_embedding = (
            self.embedding_client.create(
                input=query,
                model=self.embedding_model,
                dimensions=self.embedding_dimensions,
            )
            .data[0]
            .embedding
        )

        vector_query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=self.document_fields,
            num_results=top_k,
        )

        # The results are sorted by distance by default
        search_results = index.query(vector_query)

        return self.map_search_results_to_documents(index.name, search_results)

    def full_text_search(
        self, index: SearchIndex, query: str, top_k: int
    ) -> list[Document]:

        def escape_special_characters(text: str) -> str:
            special_chars = r'.,<>{}\[\]"\'\:;!@#$%^&*()\-\+=~'

            pattern = re.compile(f"([{re.escape(special_chars)}])")
            return pattern.sub(r"\\\1", text)

        # Escape special characters in the query
        escaped_terms = [escape_special_characters(term) for term in query.split()]

        # Join the query with OR operator to search for any of the words
        formatted_query = " | ".join(escaped_terms)

        query_obj = (  # type: ignore
            Query(formatted_query)  # type: ignore
            .paging(0, top_k)
            .scorer("BM25")
            .return_fields(*self.document_fields)
        )

        ft = self.client.ft(index.name)

        # The results are sorted by score (BM25) by default
        search_results = ft.search(query_obj)  # type: ignore
        return self.map_search_results_to_documents(index.name, search_results.docs)

    def search_source(self, name: str, query: str, top_k: int) -> list[Document]:
        index = self._get_index(name)

        vector_search_results = self.vector_based_search(index, query, top_k)

        text_search_results = self.full_text_search(index, query, top_k)

        return reciprocal_rank_fusion(
            [vector_search_results, text_search_results], top_k
        )

    def update_source_metadata(
        self,
        name: str,
        description: str | None,
        config: SourceConfig | None,
        timestamp: str,
    ) -> SourceOverview:
        metadata_key = self._get_metadata_key(name)

        if description is not None:
            self.client.hset(metadata_key, "description", description)

        config_dict: dict[str, Any] = {}

        if config is not None:
            config_items = config.model_dump().items()

            for key, value in config_items:
                if isinstance(value, list):
                    value = json.dumps(value)
                elif isinstance(value, bool):
                    value = int(value)  # 1 for True, 0 for False
                if value is None:
                    value = ""
                config_dict[f"{self.config_prefix}{key}"] = value

        self.client.hset(
            metadata_key,
            mapping={
                **config_dict,
                "updated_at": timestamp,
            },
        )

        return self.get_source(name)
