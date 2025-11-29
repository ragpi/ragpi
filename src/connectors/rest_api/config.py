from typing import Literal

from pydantic import Field, field_validator

from src.connectors.base.config import BaseConnectorConfig
from src.connectors.connector_type import ConnectorType


class RestApiConfig(BaseConnectorConfig):
    """Configuration for REST API connector.

    This connector sends HTTP requests to arbitrary cloud endpoints
    and indexes the returned JSON data.
    """

    type: Literal[ConnectorType.REST_API] = Field(
        description="Connector type identifier"
    )
    url: str = Field(
        description="The API endpoint URL to send requests to"
    )
    method: Literal["GET", "POST"] = Field(
        default="GET",
        description="HTTP method to use (GET or POST)"
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="Optional HTTP headers to include in the request"
    )
    body: dict[str, str] | None = Field(
        default=None,
        description="Optional request body for POST requests (JSON)"
    )
    json_path: str | None = Field(
        default=None,
        description="Optional JSON path to extract data from response (e.g., 'data.items')"
    )
    title_field: str = Field(
        default="title",
        description="Field name to use as document title (default: 'title')"
    )
    content_field: str = Field(
        default="content",
        description="Field name to use as document content (default: 'content')"
    )
    url_field: str | None = Field(
        default=None,
        description="Optional field name to use as document URL. If not provided, uses the API endpoint URL"
    )
    timeout: int = Field(
        default=300,
        description="Request timeout in seconds (default: 300 seconds / 5 minutes)"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """Validate that URL is properly formatted."""
        if not value.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return value

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: dict[str, str] | None, info) -> dict[str, str] | None:
        """Validate that body is only provided for POST requests."""
        if value is not None:
            method = info.data.get("method")
            if method == "GET":
                raise ValueError("Request body can only be specified for POST requests")
        return value

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, value: int) -> int:
        """Validate that timeout is a positive value."""
        if value <= 0:
            raise ValueError("Timeout must be a positive integer (seconds)")
        return value
