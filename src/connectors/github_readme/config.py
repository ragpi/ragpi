from typing import Literal

from src.connectors.base.config import BaseExtractorConfig
from src.connectors.extractor_type import ExtractorType


class GithubReadmeConfig(BaseExtractorConfig):
    type: Literal[ExtractorType.GITHUB_README]
    repo_owner: str
    repo_name: str
    include_root: bool = True
    sub_dirs: list[str] | None = None
    ref: str | None = None
