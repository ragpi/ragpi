from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Union, Literal
import re

from src.config import settings


class SourceType(str, Enum):
    SITEMAP = "sitemap"
    GITHUB_ISSUES = "github_issues"


class SitemapConfig(BaseModel):
    type: Literal[SourceType.SITEMAP]
    sitemap_url: str
    include_pattern: str | None = None
    exclude_pattern: str | None = None
    chunk_size: int = settings.CHUNK_SIZE
    chunk_overlap: int = settings.CHUNK_OVERLAP


class GithubIssuesConfig(BaseModel):
    type: Literal[SourceType.GITHUB_ISSUES]
    repo_url: str  # TODO: Update to owner and repo
    issue_state: Literal["open", "closed", "all"] = "open"
    labels: list[str] | None = None  # TODO: Update to include and exclude labels


RepositorySource = Union[SitemapConfig, GithubIssuesConfig]


class RepositoryOverview(BaseModel):
    id: str
    name: str
    num_docs: int
    created_at: str
    updated_at: str
    source: RepositorySource


class RepositoryCreateInput(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    source: RepositorySource

    @field_validator("name")
    def validate_name(cls, value: str):
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$", value):
            raise ValueError(
                "'name' must start and end with an alphanumeric character and contain only alphanumeric characters, underscores, or hyphens"
            )
        return value


class RepositoryUpdateInput(BaseModel):
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    source: RepositorySource | None = None


class RepositorySearchInput(BaseModel):
    query: str
    limit: int | None = None


class RepositoryTaskResponse(BaseModel):
    task_id: str
    repository: RepositoryOverview
    message: str | None = None
