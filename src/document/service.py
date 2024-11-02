from typing import AsyncGenerator
from src.document.chunker import split_markdown_page
from src.document.schemas import Document
from src.document.sitemap_crawler import SitemapCrawler


class DocumentService:
    async def create_documents_from_website(
        self,
        sitemap_url: str,
        include_pattern: str | None,
        exclude_pattern: str | None,
        chunk_size: int,
        chunk_overlap: int,
    ) -> AsyncGenerator[Document, None]:
        async with SitemapCrawler() as crawler:
            async for page in crawler.crawl(
                sitemap_url=sitemap_url,
                include_pattern=include_pattern,
                exclude_pattern=exclude_pattern,
            ):
                chunks = split_markdown_page(page, chunk_size, chunk_overlap)
                for chunk in chunks:
                    yield chunk
