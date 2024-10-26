import uuid
from typing import NotRequired, Pattern, TypedDict
from crawlee.beautifulsoup_crawler import (
    BeautifulSoupCrawler,
    BeautifulSoupCrawlingContext,
)
from crawlee.configuration import Configuration
from crawlee.proxy_configuration import ProxyConfiguration
from crawlee._utils.globs import Glob
from crawlee.storages import RequestQueue
import html2text

from src.document.schemas import PageData


class CrawlerKwargs(TypedDict):
    max_requests_per_crawl: int | None
    configuration: Configuration
    request_provider: RequestQueue
    proxy_configuration: NotRequired[ProxyConfiguration]


class EnqueueKwargs(TypedDict):
    include: NotRequired[list[Pattern[str] | Glob]]
    exclude: NotRequired[list[Pattern[str] | Glob]]


UNWANTED_TAGS = [
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


def extract_page_data(context: BeautifulSoupCrawlingContext) -> PageData:
    page_id = context.request.id
    url = context.request.url
    title = (
        context.soup.title.string
        if context.soup.title and context.soup.title.string
        else context.request.url
    )

    main_content = context.soup.main or context.soup.body

    if main_content:
        for unwanted in main_content.find_all(UNWANTED_TAGS):
            unwanted.decompose()

        page_content = html2text.html2text(str(main_content))
    else:
        page_content = html2text.html2text(str(context.soup))

    return PageData(id=page_id, url=url, title=title, content=page_content)


class WebsiteCrawler:
    def __init__(self):
        self.collected_pages: list[PageData] = []

    async def crawl(
        self,
        start_url: str,
        page_limit: int | None = None,
        include_pattern: str | None = None,
        exclude_pattern: str | None = None,
        proxy_urls: list[str] | None = None,
    ) -> list[PageData]:
        request_queue = await RequestQueue.open(name=str(uuid.uuid4()))

        crawler_kwargs: CrawlerKwargs = {
            "max_requests_per_crawl": page_limit,
            "configuration": Configuration(persist_storage=False, purge_on_start=True),
            "request_provider": request_queue,
        }

        if proxy_urls:
            proxy_configuration = ProxyConfiguration(proxy_urls=proxy_urls)
            crawler_kwargs["proxy_configuration"] = proxy_configuration

        crawler = BeautifulSoupCrawler(**crawler_kwargs)

        @crawler.router.default_handler
        async def request_handler(context: BeautifulSoupCrawlingContext) -> None:  # type: ignore
            page_data = extract_page_data(context)
            self.collected_pages.append(page_data)

            enqueue_options: EnqueueKwargs = {}
            if include_pattern:
                enqueue_options["include"] = [Glob(include_pattern)]
            if exclude_pattern:
                enqueue_options["exclude"] = [Glob(exclude_pattern)]

            await context.enqueue_links(**enqueue_options)

        await crawler.run([start_url])

        await request_queue.drop()

        if not self.collected_pages:
            raise ValueError("No pages were collected during crawl")

        if page_limit and len(self.collected_pages) > page_limit:
            self.collected_pages = self.collected_pages[:page_limit]

        return self.collected_pages
