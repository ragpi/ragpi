from typing import Any
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import numpy as np
from openai import OpenAI

from src.common.schemas import Document
from src.document_store.base import DocumentStoreService
from src.document_store.providers.postgres.model import create_document_model, Base
from src.document_store.ranking import reciprocal_rank_fusion


# TODO: Use with statement for session?
class PostgresDocumentStore(DocumentStoreService):
    def __init__(
        self,
        *,
        database_url: str,
        table_name: str,
        openai_client: OpenAI,
        embedding_model: str,
        embedding_dimensions: int,
    ):
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.embedding_client = openai_client.embeddings
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.DocumentModel = create_document_model(table_name, embedding_dimensions)

        with self.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            Base.metadata.create_all(conn)

    def _map_document(self, doc: Any) -> Document:
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

        session = self.Session()
        try:
            session.bulk_save_objects(docs_to_add)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def get_documents(
        self, source_name: str, limit: int, offset: int
    ) -> list[Document]:
        session = self.Session()
        try:
            results = (
                session.query(self.DocumentModel)
                .filter_by(source=source_name)
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [self._map_document(doc) for doc in results]
        finally:
            session.close()

    def get_document_ids(self, source_name: str) -> list[str]:
        session = self.Session()
        try:
            results = (
                session.query(self.DocumentModel.id).filter_by(source=source_name).all()
            )
            return [row[0] for row in results]
        finally:
            session.close()

    def delete_all_documents(self, source_name: str) -> None:
        session = self.Session()
        try:
            session.query(self.DocumentModel).filter_by(source=source_name).delete()
            session.commit()
        finally:
            session.close()

    def delete_documents(self, source_name: str, doc_ids: list[str]) -> None:
        session = self.Session()
        try:
            session.query(self.DocumentModel).filter(
                self.DocumentModel.id.in_(doc_ids)
            ).delete(synchronize_session=False)
            session.commit()
        finally:
            session.close()

    def vector_based_search(
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

        session = self.Session()
        try:
            results = (
                session.query(self.DocumentModel)
                .filter_by(source=source_name)
                .order_by(self.DocumentModel.embedding.cosine_distance(query_embedding))  # type: ignore
                .limit(top_k)
                .all()
            )
            return [self._map_document(doc) for doc in results]
        finally:
            session.close()

    def full_text_search(
        self, source_name: str, query: str, top_k: int
    ) -> list[Document]:
        session = self.Session()
        try:
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
        finally:
            session.close()

    def search_documents(
        self, source_name: str, query: str, top_k: int
    ) -> list[Document]:
        vector_results = self.vector_based_search(source_name, query, top_k)
        text_results = self.full_text_search(source_name, query, top_k)
        return reciprocal_rank_fusion([vector_results, text_results], top_k)
