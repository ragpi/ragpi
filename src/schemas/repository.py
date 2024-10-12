from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal
import re


class Repository(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    source: Literal["static_website", "dynamic_website"] = "static_website"
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


class RepositoryCreate(Repository):
    max_pages: int | None = 3
    proxy_urls: list[str] | None = None


class RepositoryUpdate(BaseModel):
    proxy_urls: list[str] | None = None


# TODO: Add RepositoryCreateResponse and RepositoryUpdateResponse and include num pages scraped and num documents added/removed
class RepositoryResponse(Repository):
    id: UUID
    num_pages: int
    num_documents: int
    created_at: str
    updated_at: str


class RepositorySearchInput(BaseModel):
    query: str
    # TODO: Fields to add: search_type, search_kwargs, etc.


class RepositoryTask(BaseModel):
    task_id: str
    status: str
    error: str | None = None
    # repository: RepositoryResponse | None = None


class RepositoryMetadata(BaseModel):
    source: str
    start_url: str
    include_pattern: str | None
    exclude_pattern: str | None
    num_pages: int
    created_at: str
    updated_at: str


class RepositoryDocument(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any]
