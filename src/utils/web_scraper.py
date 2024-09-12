import uuid
from langchain_core.documents import Document
from crawlee.beautifulsoup_crawler import (
    BeautifulSoupCrawler,
    BeautifulSoupCrawlingContext,
)
from crawlee.configuration import Configuration
from crawlee._utils.globs import Glob
from crawlee.storages import RequestQueue
import html2text

from src.schemas.page_data import PageData
from src.utils.text_splitter import split_markdown_content


def process_url(context: BeautifulSoupCrawlingContext) -> PageData:
    id = context.request.id
    url = context.request.url
    title = (
        context.soup.title.string
        if context.soup.title and context.soup.title.string
        else context.request.url
    )
    html = context.soup.main if context.soup.main else context.soup.body
    page_content = html2text.html2text(str(html))

    return PageData(id=id, url=url, title=title, content=page_content)


async def scrape_website(
    start_url: str,
    max_pages: int | None,
    include_pattern: str | None,
    exclude_pattern: str | None,
) -> list[PageData]:

    request_queue = await RequestQueue.open(name=str(uuid.uuid4()))

    crawler = BeautifulSoupCrawler(
        max_requests_per_crawl=max_pages,
        configuration=Configuration(persist_storage=False, purge_on_start=True),
        request_provider=request_queue,
    )

    pages: list[PageData] = []

    @crawler.router.default_handler
    async def request_handler(context: BeautifulSoupCrawlingContext) -> None:  # type: ignore
        page_data = process_url(context)
        pages.append(page_data)

        enqueue_options = {}

        if include_pattern:
            enqueue_options["include"] = [Glob(include_pattern)]
        if exclude_pattern:
            enqueue_options["exclude"] = [Glob(exclude_pattern)]

        await context.enqueue_links(**enqueue_options)  # type: ignore

    await crawler.run([start_url])

    await request_queue.drop()

    if max_pages and len(pages) > max_pages:
        pages = pages[:max_pages]

    return pages


async def extract_docs_from_website(
    start_url: str,
    max_pages: int | None,
    include_pattern: str | None,
    exclude_pattern: str | None,
) -> tuple[list[Document], int]:
    pages = await scrape_website(
        start_url=start_url,
        max_pages=max_pages,
        include_pattern=include_pattern,
        exclude_pattern=exclude_pattern,
    )

    docs: list[Document] = []
    for page in pages:
        chunks = split_markdown_content(page)
        docs.extend(chunks)

    return docs, len(pages)
