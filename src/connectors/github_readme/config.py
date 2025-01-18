from typing import Literal

from src.connectors.base.config import BaseConnectorConfig
from src.connectors.connector_type import ConnectorType


class GithubReadmeConfig(BaseConnectorConfig):
    type: Literal[ConnectorType.GITHUB_README]
    repo_owner: str
    repo_name: str
    include_root: bool = True
    sub_dirs: list[str] | None = None
    ref: str | None = None
