import re
import numpy as np
from typing import Any
from openai import OpenAI
from redisvl.index import SearchIndex  # type: ignore
from redisvl.schema import IndexSchema  # type: ignore
from redisvl.query import VectorQuery  # type: ignore
from redisvl.query.filter import Tag  # type: ignore
from redis.commands.search.query import Query

from src.config import settings
from src.document.schemas import Document
from src.redis import get_redis_client
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
        self.namespace = "vector_store"
        self.index_prefix = f"{self.namespace}:documents"
        index_schema = IndexSchema.from_dict(
            {
                "index": {"name": self.namespace, "prefix": self.index_prefix},
                **self.document_schema,
            }
        )
        self.index = SearchIndex(index_schema).set_client(self.client)  # type: ignore
        if not self.index.exists():
            self.index.create()

    def _get_source_key(self, name: str) -> str:
        return f"{self.index_prefix}:{name}"

    def _get_doc_key(self, source_name: str, doc_id: str) -> str:
        return f"{self.index_prefix}:{source_name}:{doc_id}"

    def _create_internal_doc_id(self, source_name: str, doc_id: str) -> str:
        return f"{source_name}:{doc_id}"

    def _extract_real_doc_id(self, source_name: str, key: str) -> str:
        return key.split(f"{source_name}:")[1]

    def add_source_documents(self, name: str, documents: list[Document]) -> list[str]:
        embeddings_data = self.embedding_client.create(
            input=[doc.content for doc in documents],
            model=self.embedding_model,
            dimensions=self.embedding_dimensions,
        ).data

        doc_embeddings = [embedding.embedding for embedding in embeddings_data]

        def create_doc_dict(doc: Document, embedding: list[float]) -> dict[str, Any]:
            internal_id = self._create_internal_doc_id(name, doc.id)
            doc_dict: dict[str, Any] = {
                "id": internal_id,
                "source": name,
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

        keys = self.index.load(id_field="id", data=data)  # type: ignore

        ids = [self._extract_real_doc_id(name, key) for key in keys]

        return ids

    def get_source_documents(
        self, name: str, limit: int | None, offset: int | None
    ) -> list[Document]:
        source_key = self._get_source_key(name)
        all_keys: list[str] = [key for key in self.client.scan_iter(f"{source_key}:*")]

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
                id=self._extract_real_doc_id(name, doc[0]),
                content=doc[1],
                title=doc[3],
                url=doc[2],
                created_at=doc[4],
            )
            for doc in docs
        ]

    def get_source_document_ids(self, name: str) -> list[str]:
        source_key = self._get_source_key(name)
        all_keys: list[str] = [key for key in self.client.scan_iter(f"{source_key}:*")]
        return [self._extract_real_doc_id(name, key) for key in all_keys]

    def get_document_count(self, name: str) -> int:
        source_key = self._get_source_key(name)
        count = 0
        for _ in self.client.scan_iter(f"{source_key}:*"):
            count += 1
        return count

    def delete_source(self, name: str) -> None:
        source_key = self._get_source_key(name)
        keys = [key for key in self.client.scan_iter(f"{source_key}:*")]
        self.index.drop_keys(keys)

    def delete_source_documents(self, name: str, doc_ids: list[str]) -> None:
        ids = [self._get_doc_key(name, doc_id) for doc_id in doc_ids]
        self.index.drop_keys(ids)

    def map_search_results_to_documents(
        self, source_name: str, search_results: list[dict[str, Any]]
    ) -> list[Document]:
        return [
            Document(
                id=self._extract_real_doc_id(source_name, doc["id"]),
                content=doc["content"],
                title=doc["title"],
                url=doc["url"],
                created_at=doc["created_at"],
            )
            for doc in search_results
        ]

    def vector_based_search(self, name: str, query: str, top_k: int) -> list[Document]:
        query_embedding = (
            self.embedding_client.create(
                input=query,
                model=self.embedding_model,
                dimensions=self.embedding_dimensions,
            )
            .data[0]
            .embedding
        )

        source_filter = Tag("source") == name  # type: ignore

        vector_query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=self.document_fields,
            num_results=top_k,
            filter_expression=source_filter,  # type: ignore
        )

        search_results = self.index.query(vector_query)
        return self.map_search_results_to_documents(name, search_results)

    def full_text_search(self, name: str, query: str, top_k: int) -> list[Document]:
        def escape_special_characters(text: str) -> str:
            special_chars = r'.,<>{}\[\]"\'\:;!@#$%^&*()\-\+=~'
            pattern = re.compile(f"([{re.escape(special_chars)}])")
            return pattern.sub(r"\\\1", text)

        escaped_terms = [escape_special_characters(term) for term in query.split()]
        formatted_query_terms = " | ".join(escaped_terms)
        formatted_query = f"@source:{{{name}}} {formatted_query_terms}"

        # TODO: Set verbatim to False?
        query_obj = (  # type: ignore
            Query(formatted_query)  # type: ignore
            .paging(0, top_k)
            .scorer("BM25")
            .return_fields(*self.document_fields)
        )

        ft = self.client.ft(f"{self.namespace}")
        search_results = ft.search(query_obj)  # type: ignore
        return self.map_search_results_to_documents(name, search_results.docs)

    def search_source(self, name: str, query: str, top_k: int) -> list[Document]:
        vector_search_results = self.vector_based_search(name, query, top_k)
        text_search_results = self.full_text_search(name, query, top_k)

        return reciprocal_rank_fusion(
            [vector_search_results, text_search_results], top_k
        )
