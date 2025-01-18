from typing import Literal

from src.connectors.base.config import BaseExtractorConfig
from src.connectors.extractor_type import ExtractorType


class GithubIssuesConfig(BaseExtractorConfig):
    type: Literal[ExtractorType.GITHUB_ISSUES]
    repo_owner: str
    repo_name: str
    state: Literal["all", "open", "closed"] = "all"
    include_labels: list[str] | None = None
    exclude_labels: list[str] | None = None
    max_age: int | None = None  # Days
