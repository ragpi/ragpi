from datetime import datetime
from typing import Any
from sqlalchemy import Computed, DateTime, String, Index
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from pgvector.sqlalchemy import Vector  # type: ignore
from sqlalchemy_utils import TSVectorType  # type: ignore

from src.config import get_settings  # type: ignore


settings = get_settings()

Base = declarative_base()


class DocumentStoreModel(Base):
    __tablename__ = settings.DOCUMENT_STORE_NAMESPACE

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    embedding: Mapped[Any] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSIONS), nullable=False
    )
    fts_vector: Mapped[Any] = mapped_column(
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

    def __init__(
        self,
        id: str,
        source: str,
        title: str,
        content: str,
        url: str,
        created_at: datetime,
        embedding: Any,
    ):
        self.id = id
        self.source = source
        self.title = title
        self.content = content
        self.url = url
        self.created_at = created_at
        self.embedding = embedding
