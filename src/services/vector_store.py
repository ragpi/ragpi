import chromadb
from chromadb.api.types import IncludeEnum, Metadata
from langchain_openai import OpenAIEmbeddings

from src.schemas.collections import (
    CollectionDocument,
    CollectionResponse,
    CollectionMetadata,
)


class VectorStoreService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.embeddings_function = OpenAIEmbeddings(model="text-embedding-3-small")

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

    def add_documents(
        self, collection_name: str, documents: list[CollectionDocument]
    ) -> list[str]:
        if len(documents) == 0:
            return []

        BATCH_SIZE = 10000

        vector_collection = self.client.get_collection(collection_name)

        doc_ids: list[str] = []
        doc_contents: list[str] = []
        doc_metadatas: list[Metadata] = []

        for doc in documents:
            metadata = {
                "source": doc.source,
                "title": doc.title,
            }

            if doc.header_1:
                metadata["header_1"] = doc.header_1
            if doc.header_2:
                metadata["header_2"] = doc.header_2
            if doc.header_3:
                metadata["header_3"] = doc.header_3

            doc_ids.append(doc.id)
            doc_metadatas.append(metadata)
            doc_contents.append(doc.content)

        doc_embeddings = self.embeddings_function.embed_documents(doc_contents)

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
                embeddings=batch_embeddings,  # type: ignore
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
        return vector_collection.get(
            include=[IncludeEnum.metadatas, IncludeEnum.documents]
        )

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

    def delete_documents(self, collection_name: str, doc_ids: list[str]):
        if len(doc_ids) == 0:
            return

        collection = self.client.get_collection(collection_name)
        collection.delete(ids=doc_ids)

    def search_collection(self, collection_name: str, query: str):
        vector_collection = self.client.get_collection(collection_name)

        query_embedding = self.embeddings_function.embed_query(query)

        return vector_collection.query(  # type: ignore
            query_embeddings=[query_embedding],
            include=[IncludeEnum.metadatas, IncludeEnum.documents],
            n_results=3,
        )
