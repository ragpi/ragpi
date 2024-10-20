from pydantic import BaseModel, Field, field_validator
from typing import Any
import re


class BaseRepository(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    start_url: str
    include_pattern: str | None = None
    exclude_pattern: str | None = None

    @field_validator("name")
    def validate_name(cls, value: str):
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$", value):
            raise ValueError(
                "'name' must start and end with an alphanumeric character and contain only alphanumeric characters, underscores, or hyphens"
            )
        return value


class RepositoryMetadata(BaseModel):
    start_url: str
    include_pattern: str | None = None
    exclude_pattern: str | None = None
    num_pages: int
    chunk_size: int
    chunk_overlap: int
    created_at: str
    updated_at: str


class RepositoryOverview(BaseRepository, RepositoryMetadata):
    id: str
    num_documents: int


class RepositoryCreateInput(BaseRepository):
    max_pages: int | None = 3
    proxy_urls: list[str] | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None


class RepositoryUpdateInput(BaseModel):
    proxy_urls: list[str] | None = None


class RepositorySearchInput(BaseModel):
    query: str
    # TODO: Fields to add: search_type, search_kwargs, etc.


class RepositoryTask(BaseModel):
    task_id: str
    status: str
    error: str | None = None


class RepositoryDocument(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any]
