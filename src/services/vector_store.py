import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from src.schemas.collections import CollectionResponse, CollectionMetadata


# This service will be more useful when dealing with multiple vector stores
class VectorStoreService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.embedding_function = OpenAIEmbeddings(model="text-embedding-3-large")

    def _get_collection_store(self, collection_name: str) -> Chroma:
        return Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embedding_function,
            persist_directory="./chroma_db",
            create_collection_if_not_exists=False,
        )

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
        ).model_dump()

        vector_collection = self.client.create_collection(
            name,
            metadata=metadata,  # type: ignore
        )

        return vector_collection.id

    async def add_documents(self, collection_name: str, documents: list[Document]):
        BATCH_SIZE = 10000  # Change depending on vector store

        collection_store = self._get_collection_store(collection_name)

        doc_ids: list[str] = []

        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i : i + BATCH_SIZE]
            batch_doc_ids = await collection_store.aadd_documents(batch)
            doc_ids.extend(batch_doc_ids)
            print(f"Added {len(batch)} documents to collection {collection_name}")

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
        collection_store = self._get_collection_store(collection_name)
        return collection_store.get(include=["metadatas", "documents"])

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

        collection.delete(ids=doc_ids)

        return True

    def search_collection(self, collection_name: str, query: str):
        collection_store = self._get_collection_store(collection_name)
        return collection_store.search(query, search_type="mmr", k=5)
