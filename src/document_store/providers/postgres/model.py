from typing import Any
from sqlalchemy import Column, Computed, String, Index
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector  # type: ignore
from sqlalchemy_utils import TSVectorType  # type: ignore

Base = declarative_base()

_model_registry: dict[str, Any] = {}


# TODO: Just use normal model without class and get embedding dimensions from settings directly
def create_document_model(table_name: str, embedding_dimensions: int):
    if table_name in _model_registry:
        return _model_registry[table_name]

    class DocumentModel(Base):
        __tablename__ = table_name

        # TODO: Change nullable to False for all columns
        id = Column(String, primary_key=True)
        source = Column(String, index=True)
        content = Column(String)
        url = Column(String)
        created_at = Column(String)  # TODO: Change to DateTime?
        title = Column(String)
        embedding = Column(Vector(embedding_dimensions))  # type: ignore
        fts_vector = Column(  # type: ignore
            TSVectorType("content", "title", regconfig="english"),
            Computed(
                "to_tsvector('english', title) || to_tsvector('english', content)",
                persisted=True,
            ),
        )

        __table_args__ = (
            Index(
                "embedding_idx",
                "embedding",
                postgresql_using="ivfflat",
                postgresql_with={"lists": 100},
                postgresql_ops={"embedding": "vector_cosine_ops"},
            ),
            Index(
                "fts_vector_idx",
                "fts_vector",
                postgresql_using="gin",
            ),
            {"extend_existing": True},
        )

    _model_registry[table_name] = DocumentModel
    return DocumentModel
