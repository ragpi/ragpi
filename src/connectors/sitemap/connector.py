import logging
from typing import AsyncGenerator
from src.common.schemas import Document
from src.config import Settings
from src.connectors.base.connector import BaseConnector
from src.connectors.common.chunker import chunk_markdown_page
from src.connectors.sitemap.config import SitemapConfig
from src.connectors.sitemap.crawler import SitemapCrawler

logger = logging.getLogger(__name__)


class SitemapConnector(BaseConnector):
    config: SitemapConfig

    def __init__(self, settings: Settings, config: SitemapConfig):
        super().__init__(settings, config)

    async def extract(self) -> AsyncGenerator[Document, None]:
        async with SitemapCrawler(
            concurrent_requests=self.settings.MAX_CONCURRENT_REQUESTS,
            user_agent=self.settings.USER_AGENT,
        ) as client:
            async for page in client.fetch_sitemap_pages(
                sitemap_url=self.config.sitemap_url,
                include_pattern=self.config.include_pattern,
                exclude_pattern=self.config.exclude_pattern,
            ):
                chunks = chunk_markdown_page(
                    page_data=page,
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap,
                    uuid_namespace=self.settings.DOCUMENT_UUID_NAMESPACE,
                )
                for chunk in chunks:
                    yield chunk
