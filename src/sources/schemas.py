from pydantic import BaseModel, Field, field_validator
import re

from src.connectors.registry import ConnectorConfig


class SourceMetadata(BaseModel):
    id: str
    name: str
    description: str
    num_docs: int
    last_task_id: str
    created_at: str
    updated_at: str
    connector: ConnectorConfig


class MetadataUpdate(BaseModel):
    description: str | None = None
    last_task_id: str | None = None
    num_docs: int | None = None
    connector: ConnectorConfig | None = None


class CreateSourceRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: str
    connector: ConnectorConfig

    @field_validator("name")
    def validate_name(cls, value: str):
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$", value):
            raise ValueError(
                "'name' must start and end with an alphanumeric character and contain only alphanumeric characters, underscores, or hyphens"
            )
        return value


class UpdateSourceRequest(BaseModel):
    sync: bool = True
    description: str | None = None
    connector: ConnectorConfig | None = None


class SourceTask(BaseModel):
    task_id: str | None
    source: SourceMetadata
    message: str


class SyncSourceOutput(BaseModel):
    source: SourceMetadata
    docs_added: int
    docs_removed: int


class SearchSourceInput(BaseModel):
    name: str = Field(description="Source name")
    query: str = Field(description="Search query")
    top_k: int = Field(description="Number of documents to retrieve")
