from typing import Literal

from src.sources.common.schemas import BaseSourceConfig
from src.sources.types import SourceType


class GithubIssuesConfig(BaseSourceConfig):
    type: Literal[SourceType.GITHUB_ISSUES]
    repo_owner: str
    repo_name: str
    state: Literal["all", "open", "closed"] = "all"
    include_labels: list[str] | None = None
    exclude_labels: list[str] | None = None
    max_age: int | None = None  # Days
