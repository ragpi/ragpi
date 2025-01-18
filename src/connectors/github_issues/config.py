from typing import Literal

from src.connectors.base.config import BaseConnectorConfig
from src.connectors.connector_type import ConnectorType


class GithubIssuesConfig(BaseConnectorConfig):
    type: Literal[ConnectorType.GITHUB_ISSUES]
    repo_owner: str
    repo_name: str
    state: Literal["all", "open", "closed"] = "all"
    include_labels: list[str] | None = None
    exclude_labels: list[str] | None = None
    max_age: int | None = None  # Days
