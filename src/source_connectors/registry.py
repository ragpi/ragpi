from typing import Annotated, Union

from pydantic import Field

from src.source_connectors.github_issues.config import GithubIssuesConfig
from src.source_connectors.github_readme.config import GithubReadmeConfig
from src.source_connectors.sitemap.config import SitemapConfig
from src.source_connectors.source_type import SourceType


SourceConfig = Annotated[
    Union[SitemapConfig, GithubIssuesConfig, GithubReadmeConfig],
    Field(discriminator="type"),
]

SourceRegistryType = dict[SourceType, type[SourceConfig]]

SOURCE_REGISTRY: SourceRegistryType = {
    SourceType.SITEMAP: SitemapConfig,
    SourceType.GITHUB_ISSUES: GithubIssuesConfig,
    SourceType.GITHUB_README: GithubReadmeConfig,
}
