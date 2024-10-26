from src.document.chunker import split_markdown_page
from src.document.schemas import Document
from src.document.web_crawler import WebsiteCrawler


class DocumentService:
    def __init__(self):
        self.crawler = WebsiteCrawler()

    async def create_documents_from_website(
        self,
        start_url: str,
        page_limit: int | None,
        include_pattern: str | None,
        exclude_pattern: str | None,
        proxy_urls: list[str] | None,
        chunk_size: int,
        chunk_overlap: int,
    ) -> tuple[list[Document], int]:
        pages = await self.crawler.crawl(
            start_url=start_url,
            page_limit=page_limit,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            proxy_urls=proxy_urls,
        )

        docs: list[Document] = []
        for page in pages:
            chunks = split_markdown_page(page, chunk_size, chunk_overlap)
            docs.extend(chunks)

        return docs, len(pages)
