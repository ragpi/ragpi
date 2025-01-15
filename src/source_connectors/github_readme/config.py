from typing import Literal

from src.source_connectors.common.schemas import BaseSourceConfig
from src.source_connectors.source_type import SourceType


class GithubReadmeConfig(BaseSourceConfig):
    type: Literal[SourceType.GITHUB_README]
    repo_owner: str
    repo_name: str
    include_root: bool = True
    sub_dirs: list[str] | None = None
    ref: str | None = None
