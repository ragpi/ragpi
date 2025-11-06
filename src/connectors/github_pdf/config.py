from typing import Literal

from src.connectors.base.config import BaseConnectorConfig
from src.connectors.connector_type import ConnectorType


class GithubPdfConfig(BaseConnectorConfig):
    type: Literal[ConnectorType.GITHUB_PDF]
    repo_owner: str
    repo_name: str
    ref: str | None = None
    path_filter: str | None = None  # Optional: only index PDFs in specific path (e.g., "docs/")
