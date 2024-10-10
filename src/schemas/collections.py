from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal
import re


class Collection(BaseModel):
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


class CollectionCreate(Collection):
    max_pages: int | None = 3
    proxy_urls: list[str] | None = None


class CollectionUpdate(BaseModel):
    proxy_urls: list[str] | None = None


# TODO: Add CollectionCreateResponse and CollectionUpdateResponse and include num pages scraped and num documents added/removed
class CollectionResponse(Collection):
    id: UUID
    num_pages: int
    num_documents: int
    created_at: str
    updated_at: str


class CollectionSearchInput(BaseModel):
    query: str
    # TODO: Fields to add: search_type, search_kwargs, etc.


class CollectionTask(BaseModel):
    task_id: str
    status: str
    error: str | None = None
    # collection: CollectionResponse | None = None


class CollectionMetadata(BaseModel):
    source: str
    start_url: str
    include_pattern: str | None
    exclude_pattern: str | None
    num_pages: int
    created_at: str
    updated_at: str


class CollectionDocument(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any]
