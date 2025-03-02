from typing import Literal
from pydantic import field_validator, AnyUrl

from src.connectors.base.config import BaseConnectorConfig
from src.connectors.connector_type import ConnectorType


class PdfConfig(BaseConnectorConfig):
    type: Literal[ConnectorType.PDF] = ConnectorType.PDF
    pdf_url: str  

    @field_validator("pdf_url")
    def validate_pdf_url(cls, url: str) -> str: 
        try:
            parsed_url = AnyUrl(url) 
            if not parsed_url.path.lower().endswith(".pdf"):
                raise ValueError("URL must end with .pdf")
        except ValueError as e:
            raise ValueError(f"Invalid URL or not a PDF: {e}")
        return url 