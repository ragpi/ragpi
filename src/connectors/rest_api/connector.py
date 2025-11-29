from typing import AsyncGenerator

from src.config import Settings
from src.connectors.base.connector import BaseConnector
from src.connectors.common.schemas import ExtractedDocument
from src.connectors.rest_api.config import RestApiConfig
from src.connectors.rest_api.chunker import chunk_rest_api_document
from src.connectors.rest_api.fetcher import RestApiFetcher


class RestApiConnector(BaseConnector):
    """Connector for fetching and indexing data from REST API endpoints."""

    config: RestApiConfig

    def __init__(self, settings: Settings, config: RestApiConfig):
        super().__init__(settings, config)

    async def extract(self) -> AsyncGenerator[ExtractedDocument, None]:
        """
        Extract documents from a REST API endpoint.

        This method:
        1. Creates a fetcher to send HTTP requests to the configured endpoint
        2. Fetches documents from the API response
        3. Chunks each document according to configured chunk size
        4. Yields ExtractedDocument objects for indexing

        Yields:
            ExtractedDocument: Document chunks ready for indexing
        """
        fetcher = RestApiFetcher(
            config=self.config,
            user_agent=self.settings.USER_AGENT,
        )

        async for rest_api_doc in fetcher.fetch_documents():
            chunks = chunk_rest_api_document(
                rest_api_doc=rest_api_doc,
                chunk_size=self.settings.CHUNK_SIZE,
                chunk_overlap=self.settings.CHUNK_OVERLAP,
            )
            for chunk in chunks:
                yield chunk
