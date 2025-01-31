from datetime import datetime
from pydantic import BaseModel

from src.connectors.registry import ConnectorConfig


class SourceMetadata(BaseModel):
    id: str
    name: str
    description: str
    num_docs: int
    last_task_id: str
    created_at: datetime
    updated_at: datetime
    connector: ConnectorConfig


class MetadataUpdate(BaseModel):
    description: str | None = None
    last_task_id: str | None = None
    num_docs: int | None = None
    connector: ConnectorConfig | None = None
