from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import numpy as np
from openai import OpenAI

from src.document_store.schemas import Document
from src.document_store.base import DocumentStoreBackend
from src.document_store.postgres.model import DocumentStoreModel, Base
from src.document_store.ranking import reciprocal_rank_fusion


class PostgresDocumentStore(DocumentStoreBackend):
    def __init__(
        self,
        *,
        database_url: str,
        openai_client: OpenAI,
        embedding_model: str,
        embedding_dimensions: int,
    ):
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.embedding_client = openai_client.embeddings
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.DocumentModel = DocumentStoreModel

        with self.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            Base.metadata.create_all(conn)

    def _map_document(self, doc: DocumentStoreModel) -> Document:
        return Document(
            id=doc.id,
            content=doc.content,
            title=doc.title,
            url=doc.url,
            created_at=doc.created_at,
        )

    def add_documents(self, source_name: str, documents: list[Document]) -> None:
        embeddings_result = self.embedding_client.create(
            input=[doc.content for doc in documents],
            model=self.embedding_model,
            dimensions=self.embedding_dimensions,
        )

        docs_to_add = [
            self.DocumentModel(
                id=doc.id,
                source=source_name,
                content=doc.content,
                title=doc.title,
                url=doc.url,
                created_at=doc.created_at,
                embedding=np.array(embedding_data.embedding, dtype=np.float32).tolist(),
            )
            for doc, embedding_data in zip(documents, embeddings_result.data)
        ]

        with self.Session() as session:
            try:
                session.bulk_save_objects(docs_to_add)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise

    def get_documents(
        self, source_name: str, limit: int, offset: int
    ) -> list[Document]:
        with self.Session() as session:
            results = (
                session.query(self.DocumentModel)
                .filter_by(source=source_name)
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [self._map_document(doc) for doc in results]

    def get_document_ids(self, source_name: str) -> list[str]:
        with self.Session() as session:
            results = (
                session.query(self.DocumentModel.id).filter_by(source=source_name).all()
            )
            return [row[0] for row in results]

    def delete_all_documents(self, source_name: str) -> None:
        with self.Session() as session:
            session.query(self.DocumentModel).filter_by(source=source_name).delete()
            session.commit()

    def delete_documents(self, source_name: str, doc_ids: list[str]) -> None:
        with self.Session() as session:
            session.query(self.DocumentModel).filter(
                self.DocumentModel.id.in_(doc_ids)
            ).delete(synchronize_session=False)
            session.commit()

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

        with self.Session() as session:
            results = (
                session.query(self.DocumentModel)
                .filter_by(source=source_name)
                .order_by(self.DocumentModel.embedding.cosine_distance(query_embedding))  # type: ignore
                .limit(top_k)
                .all()
            )
            return [self._map_document(doc) for doc in results]

    def full_text_search(
        self, source_name: str, query: str, top_k: int
    ) -> list[Document]:
        with self.Session() as session:
            ts_query = func.websearch_to_tsquery("english", query)
            results = (
                session.query(self.DocumentModel)
                .filter(
                    self.DocumentModel.source == source_name,
                    self.DocumentModel.fts_vector.op("@@")(ts_query),  # type: ignore
                )
                .order_by(func.ts_rank(self.DocumentModel.fts_vector, ts_query).desc())  # type: ignore
                .limit(top_k)
                .all()
            )
            return [self._map_document(doc) for doc in results]

    def hybrid_search(
        self, *, source_name: str, semantic_query: str, full_text_query: str, top_k: int
    ) -> list[Document]:
        semantic_results = self.semantic_search(source_name, semantic_query, top_k)
        text_results = self.full_text_search(source_name, full_text_query, top_k)
        return reciprocal_rank_fusion([semantic_results, text_results], top_k)
