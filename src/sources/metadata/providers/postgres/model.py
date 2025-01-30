from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()


class SourceMetadataModel(Base):
    __tablename__ = "metadata"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    last_task_id: Mapped[str] = mapped_column(String, nullable=False)
    num_docs: Mapped[int] = mapped_column(Integer, default=0)
    connector: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        connector: str,
        created_at: str,
        updated_at: str,
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
