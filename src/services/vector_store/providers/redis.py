from typing import Any
from langchain_openai import OpenAIEmbeddings
import numpy as np
from redis import Redis
from uuid import uuid4
from redisvl.index import AsyncSearchIndex  # type: ignore
from redisvl.schema import IndexSchema  # type: ignore
from redisvl.query import VectorQuery  # type: ignore

from src.config import settings
from src.exceptions import RepositoryAlreadyExistsException, RepositoryNotFoundException
from src.schemas.repository import (
    RepositoryDocument,
    RepositoryMetadata,
    RepositoryOverview,
)
from src.services.vector_store.base import VectorStoreBase


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
        self.client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.embeddings_function = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL, dimensions=settings.EMBEDDING_DIMENSIONS
        )
        self.schema: dict[str, Any] = REPOSITORY_DOC_SCHEMA

    async def _get_index(
        self, name: str, should_exist: bool = True
    ) -> AsyncSearchIndex:
        index_schema = IndexSchema.from_dict(
            {
                "index": {"name": name, "prefix": f"{name}:documents"},
                **self.schema,
            }
        )
        index = await AsyncSearchIndex(index_schema).set_client(self.client)  # type: ignore

        if should_exist and not await index.exists():
            raise RepositoryNotFoundException(name)

        if not should_exist and await index.exists():
            raise RepositoryAlreadyExistsException(name)

        return index

    def _extract_doc_id(self, prefix: str, key: str) -> str:
        return key.split(f"{prefix}:")[1]

    def _get_doc_key(self, prefix: str, doc_id: str) -> str:
        return f"{prefix}:{doc_id}"

    async def create_repository(
        self, name: str, metadata: RepositoryMetadata, timestamp: str
    ) -> str:
        index = await self._get_index(name, False)

        await index.create()

        metadata_key = f"{name}:metadata"
        id = str(uuid4())

        self.client.hset(
            metadata_key,
            mapping={
                "id": id,
                "name": name,
                "start_url": metadata.start_url,
                "include_pattern": metadata.include_pattern or "",
                "exclude_pattern": metadata.exclude_pattern or "",
                "num_pages": metadata.num_pages,
                "chunk_size": metadata.chunk_size,
                "chunk_overlap": metadata.chunk_overlap,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )

        return id

    async def add_repository_documents(
        self, name: str, documents: list[RepositoryDocument], timestamp: str
    ) -> list[str]:
        index = await self._get_index(name)

        doc_embeddings = await self.embeddings_function.aembed_documents(
            [doc.content for doc in documents]
        )

        def create_doc_dict(
            doc: RepositoryDocument, embedding: list[float]
        ) -> dict[str, Any]:
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

        keys = await index.load(id_field="id", data=data)  # type: ignore

        ids = [self._extract_doc_id(index.prefix, key) for key in keys]

        return ids

    async def get_repository(self, name: str) -> RepositoryOverview:
        index = await self._get_index(name)

        index_info = await index.info()

        metadata_key = f"{name}:metadata"

        metadata = self.client.hgetall(metadata_key)

        return RepositoryOverview(
            id=metadata["id"],
            name=metadata["name"],
            start_url=metadata["start_url"],
            num_pages=int(metadata["num_pages"]),
            num_docs=index_info["num_docs"],
            include_pattern=metadata["include_pattern"] or None,
            exclude_pattern=metadata["exclude_pattern"] or None,
            chunk_size=int(metadata["chunk_size"]),
            chunk_overlap=int(metadata["chunk_overlap"]),
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
        )

    async def get_repository_documents(
        self, name: str, limit: int | None, offset: int | None
    ) -> list[RepositoryDocument]:
        await self._get_index(name)

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
            RepositoryDocument(
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

    async def get_repository_document_ids(self, name: str) -> list[str]:
        index = await self._get_index(name)

        all_keys: list[str] = []

        for key in self.client.scan_iter(f"{name}:documents:*"):
            all_keys.append(key)

        return [self._extract_doc_id(index.prefix, key) for key in all_keys]

    async def get_all_repositories(self) -> list[RepositoryOverview]:
        index = await self._get_index("")

        repo_names = await index.listall()

        return [await self.get_repository(name) for name in repo_names]

    async def delete_repository(self, name: str) -> None:
        index = await self._get_index(name)

        if not await index.exists():
            raise RepositoryNotFoundException(name)

        await index.delete()

        metadata_key = f"{name}:metadata"
        self.client.delete(metadata_key)

    async def delete_repository_documents(self, name: str, doc_ids: list[str]) -> None:
        index = await self._get_index(name)

        ids = [self._get_doc_key(index.prefix, doc_id) for doc_id in doc_ids]

        await index.drop_keys(ids)

    async def search_repository(
        self, name: str, query: str, num_results: int
    ) -> list[RepositoryDocument]:
        index = await self._get_index(name)

        query_embedding = await self.embeddings_function.aembed_query(query)

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

        search_results = await index.query(vector_query)

        repository_documents = [
            RepositoryDocument(
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

    async def update_repository_metadata(
        self, name: str, metadata: RepositoryMetadata, timestamp: str
    ) -> RepositoryOverview:
        metadata_key = f"{name}:metadata"

        self.client.hset(
            metadata_key,
            mapping={
                "start_url": metadata.start_url,
                "include_pattern": metadata.include_pattern or "",
                "exclude_pattern": metadata.exclude_pattern or "",
                "num_pages": metadata.num_pages,
                "chunk_size": metadata.chunk_size,
                "chunk_overlap": metadata.chunk_overlap,
                "updated_at": timestamp,
            },
        )

        return await self.get_repository(name)
