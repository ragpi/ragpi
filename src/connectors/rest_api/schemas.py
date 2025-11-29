from typing import Any

from pydantic import BaseModel, Field


class RestApiDocument(BaseModel):
    """Internal model for documents fetched from a REST API."""

    url: str = Field(
        description="URL to the source document or API endpoint"
    )
    title: str = Field(
        description="Document title or identifier"
    )
    content: str = Field(
        description="The document content to be indexed"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from the API response"
    )
