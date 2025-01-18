from dataclasses import dataclass
from typing import Type, Annotated, Union, cast
from pydantic import Field

from src.connectors.base.config import BaseConnectorConfig
from src.connectors.connector_type import ConnectorType
from src.connectors.sitemap.config import SitemapConfig
from src.connectors.github_issues.config import GithubIssuesConfig
from src.connectors.github_readme.config import GithubReadmeConfig
from src.connectors.base.connector import BaseConnector
from src.connectors.sitemap.connector import SitemapConnector
from src.connectors.github_issues.connector import GithubIssuesConnector
from src.connectors.github_readme.connector import GithubReadmeConnector

ConnectorConfig = Annotated[
    Union[SitemapConfig, GithubIssuesConfig, GithubReadmeConfig],
    Field(discriminator="type"),
]


@dataclass(frozen=True)
class ConnectorRegistryEntry:
    config_schema: Type[BaseConnectorConfig]
    connector_class: Type[BaseConnector]


ConnectorRegistryType = dict[ConnectorType, ConnectorRegistryEntry]

CONNECTOR_REGISTRY: ConnectorRegistryType = {
    ConnectorType.SITEMAP: ConnectorRegistryEntry(
        config_schema=SitemapConfig,
        connector_class=SitemapConnector,
    ),
    ConnectorType.GITHUB_ISSUES: ConnectorRegistryEntry(
        config_schema=GithubIssuesConfig,
        connector_class=GithubIssuesConnector,
    ),
    ConnectorType.GITHUB_README: ConnectorRegistryEntry(
        config_schema=GithubReadmeConfig,
        connector_class=GithubReadmeConnector,
    ),
}

ConfigClassType = Type[Union[SitemapConfig, GithubIssuesConfig, GithubReadmeConfig]]


def get_connector_config_schema(connector_type: ConnectorType) -> ConfigClassType:
    registry_entry = CONNECTOR_REGISTRY.get(connector_type)
    if not registry_entry:
        raise ValueError(f"Unknown connector type: {connector_type}")
    return cast(ConfigClassType, registry_entry.config_schema)


def get_connector_class(connector_type: ConnectorType) -> Type[BaseConnector]:
    registry_entry = CONNECTOR_REGISTRY.get(connector_type)
    if not registry_entry:
        raise ValueError(f"Unknown connector type: {connector_type}")
    return registry_entry.connector_class
