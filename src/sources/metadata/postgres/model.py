from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

from src.config import get_settings


settings = get_settings()

Base = declarative_base()


class SourceMetadataModel(Base):
    __tablename__ = settings.SOURCE_METADATA_NAMESPACE

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    last_task_id: Mapped[str] = mapped_column(String, nullable=False)
    num_docs: Mapped[int] = mapped_column(Integer, default=0)
    connector: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        connector: str,
        created_at: datetime,
        updated_at: datetime,
        last_task_id: str = "",
        num_docs: int = 0,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.connector = connector
        self.created_at = created_at
        self.updated_at = updated_at
        self.last_task_id = last_task_id
        self.num_docs = num_docs
