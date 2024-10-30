from src.document.chunker import split_markdown_page
from src.document.schemas import Document
from src.document.sitemap_crawler import SitemapCrawler


class DocumentService:
    def __init__(self):
        self.crawler = SitemapCrawler()

    async def create_documents_from_website(
        self,
        sitemap_url: str,
        include_pattern: str | None,
        exclude_pattern: str | None,
        chunk_size: int,
        chunk_overlap: int,
    ) -> tuple[list[Document], int]:
        pages = self.crawler.crawl(
            sitemap_url=sitemap_url,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
        )

        docs: list[Document] = []
        for page in pages:
            chunks = split_markdown_page(page, chunk_size, chunk_overlap)
            docs.extend(chunks)

        return docs, len(pages)
