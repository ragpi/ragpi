from dataclasses import dataclass
from typing import Type, Annotated, Union, cast
from pydantic import Field

from src.connectors.base.config import BaseExtractorConfig
from src.connectors.extractor_type import ExtractorType
from src.connectors.sitemap.config import SitemapConfig
from src.connectors.github_issues.config import GithubIssuesConfig
from src.connectors.github_readme.config import GithubReadmeConfig
from src.connectors.base.extractor import BaseExtractor
from src.connectors.sitemap.extractor import SitemapExtractor
from src.connectors.github_issues.extractor import GithubIssuesExtractor
from src.connectors.github_readme.extractor import GithubReadmeExtractor

ExtractorConfig = Annotated[
    Union[SitemapConfig, GithubIssuesConfig, GithubReadmeConfig],
    Field(discriminator="type"),
]


@dataclass(frozen=True)
class ExtractorRegistryEntry:
    config_schema: Type[BaseExtractorConfig]
    extractor_class: Type[BaseExtractor]


ExtractorRegistryType = dict[ExtractorType, ExtractorRegistryEntry]

EXTRACTOR_REGISTRY: ExtractorRegistryType = {
    ExtractorType.SITEMAP: ExtractorRegistryEntry(
        config_schema=SitemapConfig,
        extractor_class=SitemapExtractor,
    ),
    ExtractorType.GITHUB_ISSUES: ExtractorRegistryEntry(
        config_schema=GithubIssuesConfig,
        extractor_class=GithubIssuesExtractor,
    ),
    ExtractorType.GITHUB_README: ExtractorRegistryEntry(
        config_schema=GithubReadmeConfig,
        extractor_class=GithubReadmeExtractor,
    ),
}

ConfigClassType = Type[Union[SitemapConfig, GithubIssuesConfig, GithubReadmeConfig]]


def get_extractor_config_schema(extractor_type: ExtractorType) -> ConfigClassType:
    registry_entry = EXTRACTOR_REGISTRY.get(extractor_type)
    if not registry_entry:
        raise ValueError(f"Unknown extractor type: {extractor_type}")
    return cast(ConfigClassType, registry_entry.config_schema)


def get_extractor_class(extractor_type: ExtractorType) -> Type[BaseExtractor]:
    registry_entry = EXTRACTOR_REGISTRY.get(extractor_type)
    if not registry_entry:
        raise ValueError(f"Unknown extractor type: {extractor_type}")
    return registry_entry.extractor_class
