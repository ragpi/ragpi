import logging
import uuid
from typing import TypedDict, NotRequired, Pattern
from crawlee.beautifulsoup_crawler import (
    BeautifulSoupCrawler,
    BeautifulSoupCrawlingContext,
)
from crawlee.configuration import Configuration
from crawlee.proxy_configuration import ProxyConfiguration
from crawlee._utils.globs import Glob
from crawlee.storages import RequestQueue
import html2text

from src.schemas.repository import RepositoryDocument
from src.schemas.page_data import PageData
from src.utils.text_splitter import split_markdown_content


class CrawlerKwargs(TypedDict):
    max_requests_per_crawl: int | None
    configuration: Configuration
    request_provider: RequestQueue
    proxy_configuration: NotRequired[ProxyConfiguration]


class EnqueueKwargs(TypedDict):
    include: NotRequired[list[Pattern[str] | Glob]]
    exclude: NotRequired[list[Pattern[str] | Glob]]


def process_page(context: BeautifulSoupCrawlingContext) -> PageData:
    id = context.request.id
    url = context.request.url
    title = (
        context.soup.title.string
        if context.soup.title and context.soup.title.string
        else context.request.url
    )

    main_content = context.soup.main or context.soup.body

    if main_content:
        for unwanted in main_content.find_all(
            [
                "nav",
                "header",
                "footer",
                "script",
                "style",
                "aside",
                "iframe",
                "noscript",
                "svg",
                "img",
                "form",
                "button",
                "input",
                "textarea",
                "select",
                "video",
                "audio",
            ]
        ):
            unwanted.decompose()

        page_content = html2text.html2text(str(main_content))
    else:
        page_content = html2text.html2text(str(context.soup))

    return PageData(id=id, url=url, title=title, content=page_content)


async def scrape_website(
    start_url: str,
    max_pages: int | None,
    include_pattern: str | None,
    exclude_pattern: str | None,
    proxy_urls: list[str] | None,
) -> list[PageData]:

    request_queue = await RequestQueue.open(name=str(uuid.uuid4()))

    crawler_kwargs: CrawlerKwargs = {
        "max_requests_per_crawl": max_pages,
        "configuration": Configuration(persist_storage=False, purge_on_start=True),
        "request_provider": request_queue,
    }

    if proxy_urls is not None:
        proxy_configuration = ProxyConfiguration(proxy_urls=proxy_urls)
        crawler_kwargs["proxy_configuration"] = proxy_configuration

    crawler = BeautifulSoupCrawler(**crawler_kwargs)

    pages: list[PageData] = []

    @crawler.router.default_handler
    async def request_handler(context: BeautifulSoupCrawlingContext) -> None:  # type: ignore
        page_data = process_page(context)
        pages.append(page_data)

        enqueue_options: EnqueueKwargs = {}

        if include_pattern is not None:
            enqueue_options["include"] = [Glob(include_pattern)]
        if exclude_pattern is not None:
            enqueue_options["exclude"] = [Glob(exclude_pattern)]

        await context.enqueue_links(**enqueue_options)

    await crawler.run([start_url])

    await request_queue.drop()

    if len(pages) == 0:
        logging.warning(f"No pages found on '{start_url}'")

    if max_pages and len(pages) > max_pages:
        pages = pages[:max_pages]

    return pages


async def extract_docs_from_website(
    start_url: str,
    max_pages: int | None,
    include_pattern: str | None,
    exclude_pattern: str | None,
    proxy_urls: list[str] | None,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list[RepositoryDocument], int]:
    pages = await scrape_website(
        start_url=start_url,
        max_pages=max_pages,
        include_pattern=include_pattern,
        exclude_pattern=exclude_pattern,
        proxy_urls=proxy_urls,
    )

    docs: list[RepositoryDocument] = []
    for page in pages:
        chunks = split_markdown_content(page, chunk_size, chunk_overlap)
        docs.extend(chunks)

    return docs, len(pages)
