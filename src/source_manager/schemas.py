from enum import Enum
from pydantic import BaseModel, Field, field_validator
import re

from src.sources.registry import SourceConfig


class SourceStatus(str, Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceMetadata(BaseModel):
    id: str
    name: str
    description: str
    status: SourceStatus
    num_docs: int
    created_at: str
    updated_at: str
    config: SourceConfig


class CreateSourceRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: str
    config: SourceConfig

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
    config: SourceConfig | None = None


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
