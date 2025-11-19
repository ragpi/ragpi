from typing import AsyncGenerator

from src.config import Settings
from src.connectors.base.connector import BaseConnector
from src.connectors.common.schemas import ExtractedDocument
from src.connectors.restful.config import RestfulConfig
from src.connectors.restful.chunker import chunk_restful_document
from src.connectors.restful.fetcher import RestfulFetcher


class RestfulConnector(BaseConnector):
    """Connector for fetching and indexing data from RESTful API endpoints."""

    config: RestfulConfig

    def __init__(self, settings: Settings, config: RestfulConfig):
        super().__init__(settings, config)

    async def extract(self) -> AsyncGenerator[ExtractedDocument, None]:
        """
        Extract documents from a RESTful API endpoint.

        This method:
        1. Creates a fetcher to send HTTP requests to the configured endpoint
        2. Fetches documents from the API response
        3. Chunks each document according to configured chunk size
        4. Yields ExtractedDocument objects for indexing

        Yields:
            ExtractedDocument: Document chunks ready for indexing
        """
        fetcher = RestfulFetcher(
            config=self.config,
            user_agent=self.settings.USER_AGENT,
        )

        async for restful_doc in fetcher.fetch_documents():
            chunks = chunk_restful_document(
                restful_doc=restful_doc,
                chunk_size=self.settings.CHUNK_SIZE,
                chunk_overlap=self.settings.CHUNK_OVERLAP,
            )
            for chunk in chunks:
                yield chunk
