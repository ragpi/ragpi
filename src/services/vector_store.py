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

    def map_collection_documents(
        self,
        ids: list[str],
        metadatas: list[Metadata] | None,
        documents: list[str] | None,
    ) -> list[CollectionDocument]:
        if not ids or not metadatas or not documents:
            raise ValueError(
                "Invalid data: 'ids', 'metadatas', or 'documents' are missing."
            )

        if len(ids) != len(metadatas) or len(ids) != len(documents):
            raise ValueError(
                "Mismatched lengths of 'ids', 'metadatas', and 'documents'."
            )

        collection_documents: list[CollectionDocument] = []
        for doc_id, metadata, content in zip(ids, metadatas, documents):
            collection_doc = CollectionDocument(
                id=doc_id, content=content, metadata=dict(metadata)
            )
            collection_documents.append(collection_doc)

        return collection_documents

    def create_collection(
        self,
        name: str,
        source: str,
        start_url: str,
        num_pages: int,
        include_pattern: str | None,
        exclude_pattern: str | None,
        timestamp: str,
    ):

        metadata = CollectionMetadata(
            source=source,
            start_url=start_url,
            num_pages=num_pages,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            created_at=timestamp,
            updated_at=timestamp,
        ).model_dump(exclude_none=True)

        vector_collection = self.client.create_collection(
            name,
            metadata=metadata,
        )

        return vector_collection.id

    def add_documents(
        self, collection_name: str, documents: list[CollectionDocument], timestamp: str
    ) -> list[str]:
        if len(documents) == 0:
            return []

        BATCH_SIZE = 10000

        vector_collection = self.client.get_collection(collection_name)

        doc_ids: list[str] = []
        doc_contents: list[str] = []
        doc_metadatas: list[Metadata] = []

        for doc in documents:
            doc.metadata["created_at"] = timestamp

            doc_ids.append(doc.id)
            doc_metadatas.append(doc.metadata)
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
        try:
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
                created_at=vector_collection.metadata["created_at"],
                updated_at=vector_collection.metadata["updated_at"],
            )
        # TODO: How best to handle these exceptions? Log error and return generic message?
        except KeyError as e:
            raise ValueError(
                f"Missing required metadata field in collection '{collection_name}': {e}"
            ) from e
        except Exception as e:
            raise ValueError(
                f"Unexpected error getting collection '{collection_name}': {e}"
            ) from e

    def get_collection_documents(self, collection_name: str):
        vector_collection = self.client.get_collection(collection_name)
        collection_data = vector_collection.get(
            include=[IncludeEnum.metadatas, IncludeEnum.documents]
        )

        return self.map_collection_documents(
            collection_data["ids"],
            collection_data["metadatas"],
            collection_data["documents"],
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
                created_at=collection.metadata["created_at"],
                updated_at=collection.metadata["updated_at"],
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

        collection_data = vector_collection.query(  # type: ignore
            query_embeddings=[query_embedding],
            include=[IncludeEnum.metadatas, IncludeEnum.documents],
            n_results=10,
        )

        return self.map_collection_documents(
            collection_data["ids"][0],
            collection_data["metadatas"][0] if collection_data["metadatas"] else [],
            collection_data["documents"][0] if collection_data["documents"] else [],
        )

    def update_collection_timestamp(self, collection_name: str, timestamp: str):
        vector_collection = self.client.get_collection(collection_name)

        collection_metadata = vector_collection.metadata

        vector_collection.modify(
            metadata={**collection_metadata, "updated_at": timestamp}
        )

        return timestamp
