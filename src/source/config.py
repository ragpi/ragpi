from enum import Enum
import re
from pydantic import BaseModel, Field, field_validator
from typing import Annotated, Literal, Union

from src.config import get_settings

settings = get_settings()


def validate_regex(pattern: str | None) -> str | None:
    if pattern is None:
        return None
    try:
        re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}")
    return pattern


class SourceType(str, Enum):
    SITEMAP = "sitemap"
    GITHUB_ISSUES = "github_issues"
    GITHUB_README = "github_readme"


class BaseSourceConfig(BaseModel):
    type: str
    chunk_size: int = settings.DEFAULT_CHUNK_SIZE
    chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP


class SitemapConfig(BaseSourceConfig):
    type: Literal[SourceType.SITEMAP]
    sitemap_url: str
    include_pattern: str | None = None
    exclude_pattern: str | None = None

    _validate_regex = field_validator("include_pattern", "exclude_pattern")(
        validate_regex
    )


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


SourceConfig = Annotated[
    Union[SitemapConfig, GithubIssuesConfig, GithubReadmeConfig],
    Field(discriminator="type"),
]

SOURCE_CONFIG_MAP: dict[str, type[SourceConfig]] = {
    SourceType.SITEMAP: SitemapConfig,
    SourceType.GITHUB_ISSUES: GithubIssuesConfig,
    SourceType.GITHUB_README: GithubReadmeConfig,
}
