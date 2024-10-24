from src.document.chunking import split_markdown_text
from src.document.schemas import Document
from src.document.web_scraper import scrape_website


async def extract_documents_from_website(
    start_url: str,
    max_pages: int | None,
    include_pattern: str | None,
    exclude_pattern: str | None,
    proxy_urls: list[str] | None,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list[Document], int]:
    pages = await scrape_website(
        start_url=start_url,
        max_pages=max_pages,
        include_pattern=include_pattern,
        exclude_pattern=exclude_pattern,
        proxy_urls=proxy_urls,
    )

    docs: list[Document] = []
    for page in pages:
        chunks = split_markdown_text(page, chunk_size, chunk_overlap)
        docs.extend(chunks)

    return docs, len(pages)
