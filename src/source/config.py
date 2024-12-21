from enum import Enum
from pydantic import BaseModel
from typing import Union, Literal

from src.config import get_settings

settings = get_settings()


class SourceType(str, Enum):
    SITEMAP = "sitemap"
    GITHUB_ISSUES = "github_issues"
    GITHUB_README = "github_readme"


class BaseSourceConfig(BaseModel):
    chunk_size: int = settings.CHUNK_SIZE
    chunk_overlap: int = settings.CHUNK_OVERLAP


class SitemapConfig(BaseSourceConfig):
    type: Literal[SourceType.SITEMAP]
    sitemap_url: str
    include_pattern: str | None = None  # TODO: Validate?
    exclude_pattern: str | None = None


class GithubIssuesConfig(BaseSourceConfig):
    type: Literal[SourceType.GITHUB_ISSUES]
    repo_owner: str
    repo_name: str
    state: Literal["all", "open", "closed"] = "all"
    include_labels: list[str] | None = None
    exclude_labels: list[str] | None = None
    max_age: int | None = None  # Days


class GithubReadmeConfig(BaseSourceConfig):
    type: Literal[SourceType.GITHUB_README]
    repo_owner: str
    repo_name: str
    include_root: bool = True
    sub_dirs: list[str] | None = None
    ref: str | None = None


SourceConfig = Union[SitemapConfig, GithubIssuesConfig, GithubReadmeConfig]

SOURCE_CONFIG_REGISTRY: dict[
    str, type[SitemapConfig] | type[GithubIssuesConfig] | type[GithubReadmeConfig]
] = {
    SourceType.SITEMAP: SitemapConfig,
    SourceType.GITHUB_ISSUES: GithubIssuesConfig,
    SourceType.GITHUB_README: GithubReadmeConfig,
}
