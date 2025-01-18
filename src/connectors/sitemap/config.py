import re
from typing import Literal

from pydantic import field_validator

from src.connectors.base.config import BaseConnectorConfig
from src.connectors.connector_type import ConnectorType


def validate_regex(pattern: str | None) -> str | None:
    if pattern is None:
        return None
    try:
        re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}")
    return pattern


class SitemapConfig(BaseConnectorConfig):
    type: Literal[ConnectorType.SITEMAP]
    sitemap_url: str
    include_pattern: str | None = None
    exclude_pattern: str | None = None

    _validate_regex = field_validator("include_pattern", "exclude_pattern")(
        validate_regex
    )
