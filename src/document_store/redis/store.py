from datetime import datetime
import re
import numpy as np
from typing import Any
from openai import OpenAI
from redisvl.index import SearchIndex  # type: ignore
from redisvl.schema import IndexSchema  # type: ignore
from redisvl.query import VectorQuery  # type: ignore
from redisvl.query.filter import Tag  # type: ignore
from redis.commands.search.query import Query

from src.common.redis import RedisClient
from src.document_store.schemas import Document
from src.document_store.base import DocumentStoreBackend
from src.document_store.redis.fields import (
    DOCUMENT_FIELDS,
    get_index_schema_fields,
)
from src.document_store.ranking import reciprocal_rank_fusion


class RedisDocumentStore(DocumentStoreBackend):
    def __init__(
        self,
        *,
        index_name: str,
        redis_client: RedisClient,
        openai_client: OpenAI,
        embedding_model: str,
        embedding_dimensions: int,
    ) -> None:
        self.client = redis_client
        self.embedding_client = openai_client.embeddings
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.index_schema_fields: dict[str, Any] = get_index_schema_fields(
            self.embedding_dimensions
        )
        self.document_fields = DOCUMENT_FIELDS
        self.index_name = index_name
        self.index_prefix = f"{self.index_name}:sources"
        index_schema = IndexSchema.from_dict(
            {
                "index": {"name": self.index_name, "prefix": self.index_prefix},
                **self.index_schema_fields,
            }
        )
        self.index = SearchIndex(index_schema).set_client(self.client)  # type: ignore
        if not self.index.exists():
            self.index.create()

    def _get_source_key(self, source_name: str) -> str:
        return f"{self.index_prefix}:{source_name}"

    def _get_doc_key(self, source_name: str, doc_id: str) -> str:
        return f"{self.index_prefix}:{source_name}:{doc_id}"

    def _create_internal_doc_id(self, source_name: str, doc_id: str) -> str:
        return f"{source_name}:{doc_id}"

    def _extract_real_doc_id(self, source_name: str, key: str) -> str:
        return key.split(f"{source_name}:")[1]

    def _map_document(self, source_name: str, doc: dict[str, str]):
        return Document(
            id=self._extract_real_doc_id(source_name, doc["id"]),
            content=doc["content"],
            title=doc["title"],
            url=doc["url"],
            created_at=datetime.fromisoformat(doc["created_at"]),
        )

    def add_documents(self, source_name: str, documents: list[Document]) -> None:
        embeddings_result = self.embedding_client.create(
            input=[doc.content for doc in documents],
            model=self.embedding_model,
            dimensions=self.embedding_dimensions,
        )

        data: list[dict[str, Any]] = [
            {
                "source": source_name,
                "id": self._create_internal_doc_id(source_name, doc.id),
                "content": doc.content,
                "title": doc.title,
                "url": doc.url,
                "created_at": doc.created_at.isoformat(),
                "embedding": np.array(
                    embedding_data.embedding, dtype=np.float32
                ).tobytes(),
            }
            for doc, embedding_data in zip(documents, embeddings_result.data)
        ]

        self.index.load(id_field="id", data=data)  # type: ignore

    def get_documents(
        self, source_name: str, limit: int, offset: int
    ) -> list[Document]:
        source_key = self._get_source_key(source_name)
        all_keys: list[str] = [key for key in self.client.scan_iter(f"{source_key}:*")]

        start = offset
        end = start + limit

        keys = all_keys[start:end]

        pipeline = self.client.pipeline()

        for key in keys:
            pipeline.hmget(
                key,
                *self.document_fields,
            )

        results = pipeline.execute()

        docs = [dict(zip(self.document_fields, doc_values)) for doc_values in results]

        return [self._map_document(source_name, doc) for doc in docs]

    def get_document_ids(self, source_name: str) -> list[str]:
        source_key = self._get_source_key(source_name)
        all_keys: list[str] = [key for key in self.client.scan_iter(f"{source_key}:*")]
        return [self._extract_real_doc_id(source_name, key) for key in all_keys]

    def delete_all_documents(self, source_name: str) -> None:
        source_key = self._get_source_key(source_name)
        keys = [key for key in self.client.scan_iter(f"{source_key}:*")]
        if keys:
            self.index.drop_keys(keys)

    def delete_documents(self, source_name: str, doc_ids: list[str]) -> None:
        keys = [self._get_doc_key(source_name, doc_id) for doc_id in doc_ids]
        if keys:
            self.index.drop_keys(keys)

    def semantic_search(
        self, source_name: str, query: str, top_k: int
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

        source_filter = Tag("source") == source_name  # type: ignore

        vector_query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=self.document_fields,
            num_results=top_k,
            filter_expression=source_filter,  # type: ignore
        )

        search_results = self.index.query(vector_query)
        return [self._map_document(source_name, doc) for doc in search_results]

    def full_text_search(
        self, source_name: str, query: str, top_k: int
    ) -> list[Document]:
        def escape_special_characters(text: str) -> str:
            special_chars = r'.,<>{}\[\]"\'\:;!@#$%^&*()\-\+=~'
            pattern = re.compile(f"([{re.escape(special_chars)}])")
            return pattern.sub(r"\\\1", text)

        escaped_terms = [escape_special_characters(term) for term in query.split()]
        formatted_query_terms = " | ".join(escaped_terms)
        formatted_source_name = escape_special_characters(source_name)
        formatted_query = f"@source:{{{formatted_source_name}}} {formatted_query_terms}"

        query_obj = (  # type: ignore
            Query(formatted_query)  # type: ignore
            .paging(0, top_k)
            .scorer("BM25")
            .return_fields(*self.document_fields)
        )

        ft = self.client.ft(f"{self.index_name}")
        search_results = ft.search(query_obj)  # type: ignore
        return [self._map_document(source_name, doc) for doc in search_results.docs]

    def hybrid_search(
        self, *, source_name: str, semantic_query: str, full_text_query: str, top_k: int
    ) -> list[Document]:
        semantic_results = self.semantic_search(source_name, semantic_query, top_k)
        text_results = self.full_text_search(source_name, full_text_query, top_k)
        return reciprocal_rank_fusion([semantic_results, text_results], top_k)
