from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Literal
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


class CollectionResponse(Collection):
    id: UUID
    num_pages: int
    num_documents: int


class SearchInput(BaseModel):
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
    num_pages: int
    include_pattern: str | None
    exclude_pattern: str | None


class CollectionDocument(BaseModel):
    id: str
    content: str
    source: str
    title: str
    header_1: str | None = None
    header_2: str | None = None
    header_3: str | None = None
