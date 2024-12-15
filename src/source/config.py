# TODO: Get rid of parses and handle in SourceMetadataManager?
# The SourceConfig classes need to be able to handle string inputs coming from redis.

from enum import Enum
import json
from pydantic import BaseModel, field_validator
from typing import Any, Union, Literal, cast

from src.config import settings


def parse_optional(value: Any):
    if value in (None, ""):
        return None
    return value


def parse_optional_list(value: Any):
    if value in (None, ""):
        return None
    if isinstance(value, list):
        return cast(list[Any], value)
    return json.loads(value)


def parse_bool(value: Any):
    if value == "0":
        return False
    if value == "1":
        return True
    return bool(value)


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
    include_pattern: str | None = None
    exclude_pattern: str | None = None
    concurrent_requests: int = settings.CONCURRENT_REQUESTS

    _parse_pattern = field_validator(
        "include_pattern", "exclude_pattern", mode="before"
    )(parse_optional)


class GithubIssuesConfig(BaseSourceConfig):
    type: Literal[SourceType.GITHUB_ISSUES]
    repo_owner: str
    repo_name: str
    state: Literal["all", "open", "closed"] = "all"
    include_labels: list[str] | None = None
    exclude_labels: list[str] | None = None
    max_age: int | None = None  # Days
    concurrent_requests: int = settings.CONCURRENT_REQUESTS

    _parse_labels = field_validator("include_labels", "exclude_labels", mode="before")(
        parse_optional_list
    )
    _parse_max_age = field_validator("max_age", mode="before")(parse_optional)


class GithubReadmeConfig(BaseSourceConfig):
    type: Literal[SourceType.GITHUB_README]
    repo_owner: str
    repo_name: str
    include_root: bool = True
    sub_dirs: list[str] | None = None
    ref: str | None = None

    _parse_sub_dirs = field_validator("sub_dirs", mode="before")(parse_optional_list)
    _parse_ref = field_validator("ref", mode="before")(parse_optional)
    _parse_include_root = field_validator("include_root", mode="before")(parse_bool)


SourceConfig = Union[SitemapConfig, GithubIssuesConfig, GithubReadmeConfig]

SOURCE_CONFIG_REGISTRY: dict[
    str, type[SitemapConfig] | type[GithubIssuesConfig] | type[GithubReadmeConfig]
] = {
    SourceType.SITEMAP: SitemapConfig,
    SourceType.GITHUB_ISSUES: GithubIssuesConfig,
    SourceType.GITHUB_README: GithubReadmeConfig,
}
