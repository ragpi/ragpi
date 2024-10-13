from typing import Any
from langchain_openai import OpenAIEmbeddings
import numpy as np
from redis import Redis
from uuid import uuid4
from redisvl.index import AsyncSearchIndex  # type: ignore
from redisvl.schema import IndexSchema  # type: ignore
from redisvl.query import VectorQuery  # type: ignore

from src.schemas.repository import (
    RepositoryDocument,
    RepositoryMetadata,
    RepositoryResponse,
)
from src.services.vector_store.base import VectorStoreBase


class RedisVectorStore(VectorStoreBase):
    def __init__(self):
        self.client = Redis.from_url("redis://localhost:6379", decode_responses=True)
        self.embeddings_function = OpenAIEmbeddings(model="text-embedding-3-small")
        self.schema: dict[str, Any] = {
            "fields": [
                {"name": "id", "type": "tag"},
                {"name": "content", "type": "text"},
                {"name": "source", "type": "tag"},
                {"name": "created_at", "type": "tag"},
                {"name": "title", "type": "tag"},
                {"name": "header_1", "type": "tag"},
                {"name": "header_2", "type": "tag"},
                {"name": "header_3", "type": "tag"},
                {
                    "name": "embedding",
                    "type": "vector",
                    "attrs": {
                        "dims": 1536,
                        "distance_metric": "cosine",
                        "algorithm": "flat",
                        "datatype": "float32",
                    },
                },
            ],
        }

    async def get_index(self, name: str) -> AsyncSearchIndex:
        index_schema = IndexSchema.from_dict(
            {
                "index": {"name": name, "prefix": f"{name}:documents"},
                **self.schema,
            }
        )
        index = await AsyncSearchIndex(index_schema).set_client(self.client)  # type: ignore
        return index

    def _extract_id(self, name: str, key: str) -> str:
        return key.split(f"{name}:documents:")[1]

    async def create_repository(
        self, name: str, metadata: RepositoryMetadata | None = None
    ) -> str:
        index = await self.get_index(name)
        # TODO: Check if index exists before creating

        await index.create()

        metadata_key = f"{name}:metadata"
        id = str(uuid4())

        if metadata:
            self.client.hset(
                metadata_key,
                mapping={
                    "id": id,
                    "name": name,
                    "source": metadata.source,
                    "start_url": metadata.start_url,
                    "include_pattern": metadata.include_pattern or "",
                    "exclude_pattern": metadata.exclude_pattern or "",
                    "num_pages": metadata.num_pages,
                    "created_at": metadata.created_at,
                    "updated_at": metadata.updated_at,
                },
            )

        return id

    async def add_documents(
        self, name: str, documents: list[RepositoryDocument], timestamp: str
    ) -> list[str]:
        index = await self.get_index(name)

        doc_embeddings = self.embeddings_function.embed_documents(
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
                "source",
                "title",
                "header_1",
                "header_2",
                "header_3",
            ]:
                if key in doc.metadata:
                    doc_dict[key] = doc.metadata[key]
            return doc_dict

        # Combine each document with its corresponding embedding
        data = [
            create_doc_dict(doc, embedding)
            for doc, embedding in zip(documents, doc_embeddings)
        ]

        # Load the data into the index
        keys = await index.load(id_field="id", data=data)  # type: ignore

        return keys

    async def get_repository(self, name: str) -> RepositoryResponse:
        index = await self.get_index(name)

        index_info = await index.info()

        metadata_key = f"{name}:metadata"

        metadata = self.client.hgetall(metadata_key)

        return RepositoryResponse(
            id=metadata["id"],
            name=metadata["name"],
            source=metadata["source"],  # type: ignore
            start_url=metadata["start_url"],
            num_pages=int(metadata["num_pages"]),
            num_documents=index_info["num_docs"],
            include_pattern=metadata["include_pattern"],
            exclude_pattern=metadata["exclude_pattern"],
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
        )

    async def get_repository_documents(self, name: str) -> list[RepositoryDocument]:
        # Placeholder implementation
        pass

    async def get_all_repositories(self) -> list[RepositoryResponse]:
        # Placeholder implementation
        pass

    async def delete_repository(self, name: str) -> None:
        # Placeholder implementation
        pass

    async def delete_repository_documents(self, name: str) -> bool:
        # Placeholder implementation
        pass

    async def delete_documents(self, name: str, doc_ids: list[str]) -> None:
        # Placeholder implementation
        pass

    async def search_repository(
        self, name: str, query: str
    ) -> list[RepositoryDocument]:
        query_embedding = self.embeddings_function.embed_query(query)

        vector_query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=[
                "id",
                "content",
                "source",
                "title",
                "header_1",
                "header_2",
                "header_3",
                "created_at",
            ],
            num_results=10,
        )

        index = await self.get_index(name)

        search_results = await index.query(vector_query)  # type: ignore

        repository_documents = [
            RepositoryDocument(
                id=self._extract_id(name, doc["id"]),
                content=doc.get("content", ""),  # Provide a default if needed
                metadata={
                    "source": doc.get("source", ""),
                    "title": doc.get("title", ""),
                    "created_at": doc.get("created_at", ""),
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

    async def update_repository_timestamp(self, name: str, timestamp: str) -> str:
        # Placeholder implementation
        pass
