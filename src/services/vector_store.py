import chromadb
from chromadb.types import Metadata, Vector
from openai import OpenAI

from src.schemas.collections import (
    CollectionDocument,
    CollectionResponse,
    CollectionMetadata,
)


class VectorStoreService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.embedding_function = OpenAI().embeddings

    # TODO: Refactor to add embedding function to create collection
    def create_collection(
        self,
        name: str,
        source: str,
        start_url: str,
        num_pages: int,
        include_pattern: str | None,
        exclude_pattern: str | None,
    ):

        metadata = CollectionMetadata(
            source=source,
            start_url=start_url,
            num_pages=num_pages,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
        ).model_dump(exclude_none=True)

        vector_collection = self.client.create_collection(
            name,
            metadata=metadata,
        )

        return vector_collection.id

    def add_documents(self, collection_name: str, documents: list[CollectionDocument]):
        BATCH_SIZE = 10000

        vector_collection = self.client.get_collection(collection_name)

        doc_ids: list[str] = []
        doc_contents: list[str] = []
        doc_metadatas: list[Metadata] = []

        for doc in documents:
            metadata = {
                "source": doc.source,
                "title": doc.title,
                # TODO: Add these only if exist
                "header_1": doc.header_1 or "",
                "header_2": doc.header_2 or "",
                "header_3": doc.header_3 or "",
            }
            doc_ids.append(str(doc.id))
            doc_metadatas.append(metadata)
            doc_contents.append(doc.content)

        embeddings_data = self.embedding_function.create(
            input=doc_contents, model="text-embedding-ada-002"
        ).data

        doc_embeddings: list[Vector] = [data.embedding for data in embeddings_data]

        for i in range(0, len(doc_ids), BATCH_SIZE):
            batch_ids = doc_ids[i : i + BATCH_SIZE]
            batch_contents = doc_contents[i : i + BATCH_SIZE]
            batch_metadatas = doc_metadatas[i : i + BATCH_SIZE]
            batch_embeddings = doc_embeddings[i : i + BATCH_SIZE]

            print(f"Adding {len(batch_ids)} documents to collection {collection_name}")

            vector_collection.add(  # type: ignore
                ids=batch_ids,
                documents=batch_contents,
                metadatas=batch_metadatas,
                embeddings=batch_embeddings,
            )

        return doc_ids

    def get_collection(self, collection_name: str):
        vector_collection = self.client.get_collection(collection_name)
        return CollectionResponse(
            id=vector_collection.id,
            name=vector_collection.name,
            start_url=vector_collection.metadata["start_url"],
            source=vector_collection.metadata["source"],
            include_pattern=vector_collection.metadata.get("include_pattern"),
            exclude_pattern=vector_collection.metadata.get("exclude_pattern"),
            num_pages=vector_collection.metadata["num_pages"],
            num_documents=vector_collection.count(),
        )

    def get_collection_documents(self, collection_name: str):
        vector_collection = self.client.get_collection(collection_name)
        return vector_collection.get(include=["metadatas", "documents"])

    def get_all_collections(self) -> list[CollectionResponse]:
        collections = self.client.list_collections()

        return [
            CollectionResponse(
                id=collection.id,
                name=collection.name,
                start_url=collection.metadata["start_url"],
                source=collection.metadata["source"],
                include_pattern=collection.metadata.get("include_pattern"),
                exclude_pattern=collection.metadata.get("exclude_pattern"),
                num_pages=collection.metadata["num_pages"],
                num_documents=collection.count(),
            )
            for collection in collections
        ]

    def delete_collection(self, collection_name: str):
        self.client.delete_collection(collection_name)

    def delete_collection_documents(self, collection_name: str):
        collection = self.client.get_collection(collection_name)

        doc_ids = collection.get(include=[])["ids"]

        if len(doc_ids) > 0:
            collection.delete(ids=doc_ids)

        return True

    def search_collection(self, collection_name: str, query: str):
        vector_collection = self.client.get_collection(collection_name)
        query_embedding = (
            self.embedding_function.create(input=query, model="text-embedding-ada-002")
            .data[0]
            .embedding
        )

        return vector_collection.query(  # type: ignore
            query_embeddings=[query_embedding],
            include=["metadatas", "documents"],
            n_results=3,
        )
