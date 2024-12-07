from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Union, Literal
import re

from src.config import settings


class SourceType(str, Enum):
    SITEMAP = "sitemap"
    GITHUB_ISSUES = "github_issues"


# Configs
class SitemapConfig(BaseModel):
    type: Literal[SourceType.SITEMAP]
    sitemap_url: str
    include_pattern: str | None = None
    exclude_pattern: str | None = None
    chunk_size: int = settings.CHUNK_SIZE
    chunk_overlap: int = settings.CHUNK_OVERLAP
    concurrent_requests: int = settings.CONCURRENT_REQUESTS


class GithubIssuesConfig(BaseModel):
    type: Literal[SourceType.GITHUB_ISSUES]
    repo_owner: str
    repo_name: str
    state: Literal["open", "closed"] | None = None
    include_labels: list[str] | None = None
    exclude_labels: list[str] | None = None
    max_age: int | None = None  # Days
    chunk_size: int = settings.CHUNK_SIZE
    chunk_overlap: int = settings.CHUNK_OVERLAP
    concurrent_requests: int = settings.CONCURRENT_REQUESTS


SourceConfig = Union[SitemapConfig, GithubIssuesConfig]


# Inputs
class SearchSourceInput(BaseModel):
    name: str
    query: str
    limit: int


# Outputs
class SourceOverview(BaseModel):
    id: str
    name: str
    description: str
    num_docs: int
    created_at: str
    updated_at: str
    config: SourceConfig


# Requests
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
    # TODO: Add description
    config: SourceConfig | None = None
    # TODO: Add re_index flag


class SearchSourceRequest(BaseModel):
    query: str
    limit: int = settings.RETRIEVAL_LIMIT


# Responses
class SourceTaskResponse(BaseModel):
    task_id: str
    source: SourceOverview
    message: str | None = None
