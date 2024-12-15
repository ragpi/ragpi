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

from src.config import settings
from src.document_extractor.exceptions import SitemapClientException
from src.document_extractor.schemas import MarkdownPage

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

    if main_content:
        for unwanted in main_content.find_all(UNWANTED_TAGS):
            unwanted.decompose()
        markdown_content = html2text.html2text(str(main_content))
    else:
        markdown_content = html2text.html2text(str(soup))

    return MarkdownPage(url=url, title=title, content=markdown_content)


class SitemapClient:
    def __init__(self, concurrent_requests: int = settings.CONCURRENT_REQUESTS) -> None:
        self.user_agent = settings.USER_AGENT
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
                    logging.info(
                        f"No robots.txt found at {robots_url}. Allowing all URLs."
                    )
                    return ""
                else:
                    logging.warning(
                        f"Failed to fetch robots.txt from {robots_url}: {response.status}. Allowing all URLs."
                    )
                    return ""
        except Exception as e:
            logging.error(
                f"Error fetching robots.txt from {robots_url}: {e}. Allowing all URLs."
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
                raise SitemapClientException(f"Sitemap not found at {sitemap_url}")

            response.raise_for_status()

            sitemap_xml = await response.text()
            soup = BeautifulSoup(sitemap_xml, "xml")
            urls = [loc.text for loc in soup.find_all("loc")]
            return urls

    async def fetch_page(
        self, url: str, robots_parser: RobotFileParser
    ) -> MarkdownPage | None:
        if not robots_parser.can_fetch(self.user_agent, url):
            logging.warning(f"URL {url} is disallowed by robots.txt")
            return None

        max_retries = 5
        retry_count = 0
        backoff = 1  # 1 second

        while retry_count <= max_retries:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        return extract_markdown_page(url, content)
                    elif response.status == 404:
                        logging.error(f"Page not found at {url}")
                        return None
                    elif response.status == 429:
                        logging.warning(
                            f"Rate limit exceeded when fetching {url}. Retrying in {backoff} seconds..."
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        retry_count += 1
                    else:
                        response.raise_for_status()
            except Exception as e:
                logging.error(
                    f"Error fetching {url}: {e}. Retrying in {backoff} seconds..."
                )
                await asyncio.sleep(backoff)
                backoff *= 2
                retry_count += 1
        logging.error(f"Failed to fetch {url} after {max_retries} retries.")
        return None

    async def fetch_sitemap_pages(
        self,
        sitemap_url: str,
        include_pattern: str | None = None,
        exclude_pattern: str | None = None,
    ) -> AsyncGenerator[MarkdownPage, None]:
        logging.info(f"Fetching pages from sitemap: {sitemap_url}")

        urls = await self.parse_sitemap(sitemap_url)

        if not urls:
            raise SitemapClientException(
                f"No URLs found in the sitemap at {sitemap_url}"
            )

        if include_pattern:
            include_regex = re.compile(include_pattern)
            urls = [url for url in urls if include_regex.search(url)]

            if not urls:
                raise SitemapClientException(
                    f"No URLs from the sitemap matched the include pattern {include_pattern}"
                )

        if exclude_pattern:
            exclude_regex = re.compile(exclude_pattern)
            urls = [url for url in urls if not exclude_regex.search(url)]

            if not urls:
                raise SitemapClientException(
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
