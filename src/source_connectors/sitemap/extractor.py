import logging
from typing import AsyncGenerator
from src.common.schemas import Document
from src.source_connectors.common.chunker import chunk_markdown_page
from src.source_connectors.sitemap.config import SitemapConfig
from src.source_connectors.sitemap.crawler import SitemapCrawler

logger = logging.getLogger(__name__)


async def extract_documents_from_sitemap(
    *,
    source_config: SitemapConfig,
    concurrent_requests: int,
    user_agent: str,
    document_uuid_namespace: str,
) -> AsyncGenerator[Document, None]:
    async with SitemapCrawler(
        concurrent_requests=concurrent_requests,
        user_agent=user_agent,
    ) as client:
        async for page in client.fetch_sitemap_pages(
            sitemap_url=source_config.sitemap_url,
            include_pattern=source_config.include_pattern,
            exclude_pattern=source_config.exclude_pattern,
        ):
            chunks = chunk_markdown_page(
                page_data=page,
                chunk_size=source_config.chunk_size,
                chunk_overlap=source_config.chunk_overlap,
                uuid_namespace=document_uuid_namespace,
            )
            for chunk in chunks:
                yield chunk
