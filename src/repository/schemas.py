from pydantic import BaseModel, Field, field_validator
import re


class RepositoryConfig(BaseModel):
    sitemap_url: str
    include_pattern: str | None = None
    exclude_pattern: str | None = None
    chunk_size: int
    chunk_overlap: int


class RepositoryOverview(BaseModel):
    id: str
    name: str
    num_docs: int
    created_at: str
    updated_at: str
    config: RepositoryConfig


class RepositoryCreateInput(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    sitemap_url: str
    include_pattern: str | None = None
    exclude_pattern: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None

    @field_validator("name")
    def validate_name(cls, value: str):
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$", value):
            raise ValueError(
                "'name' must start and end with an alphanumeric character and contain only alphanumeric characters, underscores, or hyphens"
            )
        return value


class RepositoryUpdateInput(BaseModel):
    sitemap_url: str | None = None
    include_pattern: str | None = None
    exclude_pattern: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None


class RepositorySearchInput(BaseModel):
    query: str
    num_results: int | None = None


class RepositoryTaskResponse(BaseModel):
    task_id: str
    repository: RepositoryOverview
    message: str | None = None
