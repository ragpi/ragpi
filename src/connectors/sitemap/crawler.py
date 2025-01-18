import logging
from types import TracebackType
from typing import AsyncGenerator, Type
import asyncio
from aiohttp import ClientSession
from bs4 import BeautifulSoup
import re
import html2text
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

from src.connectors.exceptions import ConnectorException
from src.connectors.common.schemas import MarkdownPage


logger = logging.getLogger(__name__)

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


def extract_markdown_page(url: str, content: bytes) -> MarkdownPage:
    soup = BeautifulSoup(content, "html.parser")
    title = soup.title.string if soup.title and soup.title.string else url

    main_content = soup.main or soup.body

    content_to_process = main_content if main_content else soup
    for unwanted in content_to_process.find_all(UNWANTED_TAGS):
        unwanted.decompose()

    markdown_content = html2text.html2text(str(content_to_process))

    return MarkdownPage(url=url, title=title, content=markdown_content)


class SitemapCrawler:
    def __init__(self, *, concurrent_requests: int, user_agent: str):
        self.user_agent = user_agent
        self.session: ClientSession = ClientSession(
            headers={"User-Agent": self.user_agent}
        )
        self.concurrent_requests = concurrent_requests

    async def __aenter__(self):
        return self

    async def __aexit__(
        self, exc_type: Type[Exception], exc: Exception, tb: TracebackType
    ):
        if self.session:
            await self.session.close()

    async def fetch_robots_txt(self, base_url: str) -> str:
        robots_url = urljoin(base_url, "/robots.txt")

        try:
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 404:
                    logger.info(
                        f"No robots.txt found at {robots_url}. Allowing all URLs."
                    )
                    return ""
                else:
                    logger.warning(
                        f"Failed to fetch robots.txt from {robots_url}: {response.status}. Allowing all URLs."
                    )
                    return ""
        except Exception:
            logger.exception(
                f"Error fetching robots.txt from {robots_url}. Allowing all URLs."
            )
            return ""

    async def setup_robots_parser(self, sitemap_url: str) -> RobotFileParser:
        parsed_url = urlparse(sitemap_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        robots_parser = RobotFileParser()
        robots_content = await self.fetch_robots_txt(base_url)
        robots_parser.parse(robots_content.splitlines())
        return robots_parser

    async def parse_sitemap(self, sitemap_url: str) -> list[str]:
        async with self.session.get(sitemap_url) as response:
            if response.status == 404:
                raise ConnectorException(f"Sitemap not found at {sitemap_url}")

            response.raise_for_status()

            sitemap_xml = await response.text()
            soup = BeautifulSoup(sitemap_xml, "xml")
            urls = [loc.text for loc in soup.find_all("loc")]
            return urls

    async def fetch_page(
        self, url: str, robots_parser: RobotFileParser
    ) -> MarkdownPage | None:
        if not robots_parser.can_fetch(self.user_agent, url):
            logger.warning(f"URL {url} is disallowed by robots.txt")
            return None

        max_attempts = 5
        retry_count = 0
        backoff = 1  # 1 second

        while retry_count < max_attempts:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        return extract_markdown_page(url, content)
                    elif response.status == 404:
                        logger.error(f"Page not found at {url}")
                        return None
                    elif response.status == 429:
                        logger.warning(
                            f"Rate limit exceeded when fetching {url}. Retrying in {backoff} seconds..."
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        retry_count += 1
                    else:
                        response.raise_for_status()
            except Exception:
                logger.exception(
                    f"Error fetching {url}. Retrying in {backoff} seconds..."
                )
                await asyncio.sleep(backoff)
                backoff *= 2
                retry_count += 1
        logger.error(f"Failed to fetch {url} after {max_attempts} attempts.")
        return None

    async def fetch_sitemap_pages(
        self,
        sitemap_url: str,
        include_pattern: str | None = None,
        exclude_pattern: str | None = None,
    ) -> AsyncGenerator[MarkdownPage, None]:
        logger.info(f"Fetching pages from sitemap: {sitemap_url}")

        urls = await self.parse_sitemap(sitemap_url)

        if not urls:
            raise ConnectorException(f"No URLs found in the sitemap at {sitemap_url}")

        if include_pattern:
            include_regex = re.compile(include_pattern)
            urls = [url for url in urls if include_regex.search(url)]

            if not urls:
                raise ConnectorException(
                    f"No URLs from the sitemap matched the include pattern {include_pattern}"
                )

        if exclude_pattern:
            exclude_regex = re.compile(exclude_pattern)
            urls = [url for url in urls if not exclude_regex.search(url)]

            if not urls:
                raise ConnectorException(
                    f"All URLs from the sitemap matched the exclude pattern {exclude_pattern}"
                )

        robots_parser = await self.setup_robots_parser(sitemap_url)

        semaphore = asyncio.Semaphore(self.concurrent_requests)

        async def fetch_with_semaphore(url: str):
            async with semaphore:
                return await self.fetch_page(url, robots_parser)

        tasks = [asyncio.create_task(fetch_with_semaphore(url)) for url in urls]

        for task in asyncio.as_completed(tasks):
            markdown_page = await task
            if markdown_page:
                yield markdown_page
