from typing import Literal
from pydantic import field_validator, HttpUrl

from src.connectors.base.config import BaseConnectorConfig
from src.connectors.connector_type import ConnectorType


class PdfConfig(BaseConnectorConfig):
    type: Literal[ConnectorType.PDF] = ConnectorType.PDF
    pdf_url: HttpUrl
    @field_validator("pdf_url")
    def validate_pdf_url(cls, url: str):
        if not url.lower().endswith(".pdf"):
            raise ValueError("URL must end with .pdf")
        return url